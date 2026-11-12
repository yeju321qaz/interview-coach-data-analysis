"""Independent question-group holdout experiment on original-vs-mismatched pairs.
No true drift labels; no accuracy claims about real-time off-topic speech.
"""
import sys,os,json,re,time,unicodedata
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'verification_20261029/packages'))
os.environ['OMP_NUM_THREADS']='1'
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,precision_recall_fscore_support
import joblib
from intent_guard import features,AlertPolicy
def norm(t):return re.sub(r'[^가-힣a-z0-9]','',unicodedata.normalize('NFC',t).lower())
def main():
    target=BASE/'results/intent_baseline_summary.json'
    if target.exists():raise SystemExit('Actual result exists; choose a new experiment folder')
    start=time.perf_counter();data=pd.read_csv(ROOT/'outputs/coach_answers.csv',usecols=lambda c:c in ['id','split','q_text','a_text'] or c.startswith('qt_'))
    data['qnorm']=data.q_text.map(norm);cols=[c for c in data if c.startswith('qt_')];data['type']=data[cols].idxmax(axis=1).where(data[cols].any(axis=1),'none')
    trainall=data[data.split=='Training'];train=trainall.sample(2000,random_state=29).copy()
    # Remove any validation question text that exists anywhere in Training.
    unseen=data[(data.split=='Validation')&~data.qnorm.isin(set(trainall.qnorm))].drop_duplicates('qnorm').sample(800,random_state=29)
    dev=unseen.iloc[:400].copy();test=unseen.iloc[400:].copy()
    assert not(set(train.qnorm)&set(dev.qnorm) or set(train.qnorm)&set(test.qnorm) or set(dev.qnorm)&set(test.qnorm))
    rng=np.random.default_rng(29)
    def pairs(frame):
        rows=[];skipped=0
        for r in frame.itertuples():
            candidates=frame[(frame['type']==r.type)&(frame.qnorm!=r.qnorm)]
            if candidates.empty:skipped+=1;continue
            other=candidates.iloc[int(rng.integers(len(candidates)))]
            rows.extend([{'id':r.id,'question_id':r.id,'question':r.q_text,'answer':r.a_text,'label':1},
                         {'id':r.id,'question_id':other.id,'question':other.q_text,'answer':r.a_text,'label':0}])
        return pd.DataFrame(rows),skipped
    tr,skiptr=pairs(train);dv,skipdv=pairs(dev);te,skipte=pairs(test)
    vec=TfidfVectorizer(analyzer='char_wb',ngram_range=(2,3),min_df=3,max_features=50000,sublinear_tf=True)
    vec.fit(pd.concat([train.q_text,train.a_text]))
    clf=LogisticRegression(random_state=29,max_iter=200).fit(features(vec,tr.question,tr.answer),tr.label)
    dp=clf.predict_proba(features(vec,dv.question,dv.answer))[:,1]
    candidates=[]
    for threshold in np.linspace(.05,.95,19):
        pp,rr,ff,_=precision_recall_fscore_support(dv.label,dp>=threshold,average='binary',zero_division=0);candidates.append((ff,threshold))
    _,threshold=max(candidates)
    tf=features(vec,te.question,te.answer);tp=clf.predict_proba(tf)[:,1];pr,rec,f1,_=precision_recall_fscore_support(te.label,tp>=threshold,average='binary',zero_division=0)
    joblib.dump({'vectorizer':vec,'classifier':clf,'pair_threshold_from_dev':threshold},BASE/'results/intent_guard.joblib')
    te.assign(pair_match_score=tp).to_csv(BASE/'results/intent_pair_predictions.csv',index=False,encoding='utf-8-sig')
    summary={'task':'Original question identity vs mismatched question from same keyword type; NOT true off-topic detection',
      'label_source':'automatically constructed pair identity; original answers not manually quality-verified',
      'train_answers':len(train),'dev_answers':len(dev),'test_answers':len(test),'train_pairs':len(tr),'dev_pairs':len(dv),'test_pairs':len(te),
      'skipped_no_same_type_alternative':{'train':skiptr,'dev':skipdv,'test':skipte},'question_group_overlap':0,'speaker_independence':'unknown_no_speaker_id',
      'vectorizer_fit':'Training subset only','negative_sampling':'same primary keyword type, different normalized question, same partition',
      'threshold_selected_on_dev':threshold,'test_pair_auc':float(roc_auc_score(te.label,tp)),'test_cosine_auc':float(roc_auc_score(te.label,tf[:,0])),
      'test_pair_precision':pr,'test_pair_recall':rec,'test_pair_f1':f1,'seconds':time.perf_counter()-start,
      'true_drift_precision_recall':None,'real_time_alert_latency':None,'no_api_calls':True}
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    # Replay actual tiny output as offline segments. No gold labels or live latency.
    source=BASE/'results/local_stt_predictions_run1.jsonl'
    if source.exists() and (BASE/'results/stt_summary.json').exists():
        raw=[json.loads(l) for l in source.read_text(encoding='utf-8').splitlines()]
        lookup=data.set_index('id').q_text.to_dict();replay=[]
        for r in raw:
            if r['beam_size']!=5:continue
            policy=AlertPolicy()
            for segment in r['segments']:
                score=float(clf.predict_proba(features(vec,[lookup[r['id']]],[segment['text']]))[0,1])
                replay.append({'id':r['id'],'audio_end_s':segment['end_s'],'text':segment['text'],'pair_match_score':score,**policy.update(segment['text'],score,segment['end_s']),
                               'scope':'offline ASR-segment replay; thresholds .2/.8 and N=2 are unvalidated proposals; not real-time or true drift evaluation'})
        (BASE/'results/offline_guard_replay.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in replay)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
