"""Offline only; no onset labels or real-time latency measurements."""
import sys,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'verification_20261029/packages'))
import joblib,csv
from intent_guard import features,AlertPolicy
def main():
    assert (BASE/'results/stt_summary.json').exists()
    fitted=joblib.load(BASE/'results/intent_guard.joblib');vec=fitted['vectorizer'];clf=fitted['classifier']
    with (ROOT/'phase2_review_stt_20261029/stt/manifest12.csv').open(encoding='utf-8-sig',newline='') as f:lookup={r['id']:r['question'] for r in csv.DictReader(f)}
    raw=[json.loads(l) for l in (BASE/'results/local_stt_predictions_run1.jsonl').read_text(encoding='utf-8').splitlines()]
    replay=[]
    for r in raw:
        if r['beam_size']!=5:continue
        policy=AlertPolicy()
        for seg in r['segments']:
            score=float(clf.predict_proba(features(vec,[lookup[r['id']]],[seg['text']]))[0,1])
            replay.append({'id':r['id'],'audio_end_s':seg['end_s'],'text':seg['text'],'pair_match_score':score,**policy.update(seg['text'],score,seg['end_s']),
                'scope':'offline ASR-segment replay, unvalidated lexical thresholds, no drift ground truth, no actual alert delivered'})
    (BASE/'results/offline_guard_replay.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in replay)+'\n',encoding='utf-8')
    print('Offline replay segments',len(replay),'files',len({r['id'] for r in replay}),'would-alert candidates',sum(r['would_alert'] for r in replay))
if __name__=='__main__':main()
