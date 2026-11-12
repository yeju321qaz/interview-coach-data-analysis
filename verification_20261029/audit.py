"""Read-only raw-data audit; deterministic CSV review sampling. No original writes."""
import sys, os, json, re, hashlib, unicodedata, wave, time, ast
from pathlib import Path
from collections import Counter, defaultdict
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'verification_20261029'
sys.path.insert(0,str(BASE/'packages'))
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pandas as pd
from common import load_json
import label_stats as ls

def norm(s):
    return re.sub(r'[^가-힣a-z0-9]', '', unicodedata.normalize('NFC',str(s)).lower())

def save(df,name):
    # CSV fields remain plain data; neutralize spreadsheet formula prefixes.
    df=df.copy()
    for c in df.select_dtypes(include='object'):
        df[c]=df[c].map(lambda x: "'"+x if isinstance(x,str) and x.startswith(('=','+','-','@')) else x)
    df.to_csv(BASE/'review'/name,index=False,encoding='utf-8-sig')

def main():
    start=time.monotonic()
    # Parse only the constant, without importing legacy scipy-dependent module.
    tree=ast.parse((ROOT/'src/coach_features.py').read_text(encoding='utf-8'))
    patterns=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='QUESTION_TYPES' for t in n.targets))
    rows=[]; errors=[]; statuses=Counter(); files=Counter()
    for split,fid,raw in ls.iter_label_files():
        files[split]+=1
        try:
            d,status=load_json(raw)
            statuses[status]+=1
            if d is None:
                errors.append({'split':split,'id':fid,'stage':'JSON','reason':'broken'}); continue
            rows.append(ls.parse(d,split,fid,status))
        except Exception as e:
            errors.append({'split':split,'id':fid,'stage':'schema','reason':str(e)})
    df=pd.DataFrame(rows)
    print('Parsed',len(df),'errors',len(errors),flush=True)
    wavs=sorted((ROOT/'data').glob('*/01.원천데이터/*/*.wav'))
    wm=defaultdict(list); audio_rows=[]
    for w in wavs:
        wm[w.name].append(w)
        with wave.open(str(w),'rb') as a:
            audio_rows.append({'file':w.stem,'path':str(w.relative_to(ROOT)),'seconds':a.getnframes()/a.getframerate(),
                               'sr':a.getframerate(),'channels':a.getnchannels(),'sample_width':a.getsampwidth()})
    au=pd.DataFrame(audio_rows)
    df['question_id']=df.q_text.map(lambda s:'Q_'+hashlib.sha256(norm(s).encode()).hexdigest()[:16])
    df['q_norm']=df.q_text.map(norm); df['a_norm']=df.a_text.map(norm)
    df['pair_hash']=[hashlib.sha256((q+'|'+a).encode()).hexdigest() for q,a in zip(df.q_norm,df.a_norm)]
    df['duplicate_question_n']=df.groupby('q_norm').id.transform('size')
    df['duplicate_answer_n']=df.groupby('a_norm').id.transform('size')
    df['duplicate_pair_n']=df.groupby('pair_hash').id.transform('size')
    df['cross_split_question']=df.groupby('q_norm').split.transform('nunique')>1
    df['cross_split_answer']=df.groupby('a_norm').split.transform('nunique')>1
    df['cross_split_pair']=df.groupby('pair_hash').split.transform('nunique')>1
    df['question_audio_path']=df.q_audio.map(lambda s: '|'.join(str(w.relative_to(ROOT)) for w in wm[Path(s).name]))
    df['answer_audio_path']=df.a_audio.map(lambda s: '|'.join(str(w.relative_to(ROOT)) for w in wm[Path(s).name]))
    df['audio_pair_available']=df.question_audio_path.ne('') & df.answer_audio_path.ne('')
    df['audio_ambiguous']=[len(wm[Path(q).name])>1 or len(wm[Path(a).name])>1 for q,a in zip(df.q_audio,df.a_audio)]
    df['id_link_ok']=[Path(q).stem.replace('_q_','_d_',1)==i and Path(a).stem.replace('_a_','_d_',1)==i for q,a,i in zip(df.q_audio,df.a_audio,df.id)]
    flags=[]; states=[]; stars=[]; types=[]
    for r in df.itertuples():
        tt=[k for k,p in patterns.items() if re.search(p,r.q_text)]; types.append('|'.join(tt) or '미분류')
        history=bool(re.search(r'경험|했|있었|었던|였던|해결한|극복한',r.q_text))
        hypothetical=bool(re.search(r'만약|다면|시겠|가정',r.q_text))
        stars.append('적합 후보' if history and not hypothetical else '검수 필요' if history else '비적합 후보')
        f=[]
        if not r.q_norm or not r.a_norm: f.append('빈전사')
        if r.a_dur_s<=0 or r.q_dur_s<=0: f.append('비양수길이')
        if not r.id_link_ok: f.append('ID연결불일치')
        if r.json_status!='ok': f.append('관대한JSON파싱')
        if not r.text_is_nfc: f.append('NFC불일치')
        if r.a_words!=r.a_words_counted: f.append('어절수불일치')
        if r.q_norm==r.a_norm: f.append('질문답변동일')
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]',r.q_text+r.a_text): f.append('제어문자또는대체문자')
        if r.duplicate_pair_n>1: f.append('정규화QA중복')
        if r.duplicate_answer_n>1: f.append('정규화답변중복')
        if r.audio_ambiguous: f.append('음성파일명중복')
        flags.append('|'.join(f))
        states.append('제외 후보' if any(x in f for x in ['빈전사','비양수길이','ID연결불일치']) else '검수 필요' if f else '사용 가능 후보')
    df['rule_question_types']=types; df['star_suitability_candidate']=stars
    df['quality_flags']=flags; df['quality_status_candidate']=states
    df['human_review_status']='미검수'
    df['purpose_candidate']=np.where(df.audio_pair_available,'텍스트분석|STT평가후보|음향분석','텍스트분석|질문은행후보')
    def criteria(t):
        rules={'경험/성과':'맥락·본인역할·구체행동·결과','협업/갈등':'갈등맥락·본인행동·협력과정·결과','상황가정/대처':'문제이해·우선순위·대응근거','지원동기/입사후포부':'지원이유·직무연결·계획','직무/전문성':'개념정확성·적용근거·직무연결'}
        return '|'.join(v for k,v in rules.items() if k in t) or '질문핵심요구·근거·관련성'
    df['evaluation_items_candidate']=df.rule_question_types.map(criteria)
    counts=[]
    for typ,pat in patterns.items():
        m=df.q_text.str.contains(pat)
        counts.append({'rule_type':typ,'count':int(m.sum()),'share_all':float(m.mean()),'audio_pairs':int((m&df.audio_pair_available).sum()),
                       'star_candidate':int((m&df.star_suitability_candidate.eq('적합 후보')).sum()),
                       'usable_candidate':int((m&df.quality_status_candidate.eq('사용 가능 후보')).sum()),'review_required':int((m&df.quality_status_candidate.eq('검수 필요')).sum())})
    save(pd.DataFrame(counts),'question_type_counts.csv')
    selections=defaultdict(set)
    for typ in list(patterns)+['미분류']:
        sub=df[df.rule_question_types.str.split('|').map(lambda x:typ in x)]
        for audio,n in [(True,5),(False,15)]:
            s=sub[sub.audio_pair_available==audio]
            for idx in s.sample(min(n,len(s)),random_state=20261029).index: selections[idx].add(typ)
        # Fill sparse audio strata to 20 where possible.
        chosen=[i for i in selections if typ in selections[i]]
        rest=sub.drop(index=chosen,errors='ignore')
        for idx in rest.sample(min(max(0,20-len(chosen)),len(rest)),random_state=29).index: selections[idx].add(typ)
    edge=df[df.quality_flags.ne('')]
    for idx in edge.sample(min(30,len(edge)),random_state=29).index: selections[idx].add('품질문제')
    columns=['id','question_id','split','occupation','gender','age','experience','q_text','a_text','q_audio','a_audio','question_audio_path','answer_audio_path','audio_pair_available','rule_question_types','star_suitability_candidate','evaluation_items_candidate','purpose_candidate','quality_status_candidate','quality_flags','duplicate_question_n','duplicate_answer_n','duplicate_pair_n','cross_split_question','cross_split_answer','cross_split_pair','human_review_status']
    save(df[columns],'candidate_inventory.csv')
    sample=df.loc[sorted(selections),columns].copy()
    sample['sample_stratum']=['|'.join(sorted(selections[i])) for i in sample.index]
    for c in ['reviewer_id','human_question_type','human_star_applicable','question_answer_match','transcript_audio_match','human_quality_status','human_evaluation_items','evidence_notes','adjudicator_id','final_decision']:
        sample[c]=''
    save(sample,'manual_review.csv')
    save(pd.DataFrame(errors),'excluded_records.csv')
    save(au,'wav_headers.csv')
    for name,key in [('duplicate_questions','q_norm'),('duplicate_answers','a_norm'),('duplicate_pairs','pair_hash')]:
        sub=df[df.duplicated(key,keep=False)]
        save(sub[['id','split','question_id','q_text','a_text',key]],name+'.csv')
    syn=[json.loads(s) for s in (ROOT/'outputs/synthetic_eval.jsonl').read_text(encoding='utf-8').splitlines()]
    sources=Counter(x['source_id'] for x in syn)
    syn_splits=Counter(df.set_index('id').split.get(x['source_id'],'missing') for x in syn)
    duration_by_file=dict(zip(au.file,au.seconds)); differences=[]
    for r in df[df.audio_pair_available].itertuples():
        differences.extend([duration_by_file[Path(r.q_audio).stem]-r.q_dur_s,duration_by_file[Path(r.a_audio).stem]-r.a_dur_s])
    result={'source_files':dict(files),'parse_statuses':dict(statuses),'schema_success':len(df),'errors':errors,
      'split_analyzed':df.split.value_counts().to_dict(),'wav_count':len(wavs),'wav_hours':float(au.seconds.sum()/3600),
      'wav_format_counts':au.groupby(['sr','channels','sample_width']).size().to_dict().__str__(),
      'audio_pairs':int(df.audio_pair_available.sum()),'wav_duration_max_abs_diff':max(map(abs,differences)),
      'answer_median_seconds':float(df.a_dur_s.median()),'answer_hours_metadata':float(df.a_dur_s.sum()/3600),
      'unique_questions_raw':int(df.q_text.nunique()),'unique_questions_normalized':int(df.q_norm.nunique()),
      'id_duplicates':int(df.id.duplicated().sum()),'id_link_failures':int((~df.id_link_ok).sum()),
      'question_answer_equal':int(df.q_norm.eq(df.a_norm).sum()),
      'answer_duplicate_rows':int(df.a_norm.duplicated(keep=False).sum()),'answer_duplicate_groups':int(df.loc[df.a_norm.duplicated(keep=False),'a_norm'].nunique()),
      'pair_duplicate_rows':int(df.pair_hash.duplicated(keep=False).sum()),
      'cross_split_question_groups':int(df.loc[df.cross_split_question,'q_norm'].nunique()),'cross_split_question_rows':int(df.cross_split_question.sum()),
      'cross_split_answer_groups':int(df.loc[df.cross_split_answer,'a_norm'].nunique()),'cross_split_answer_rows':int(df.cross_split_answer.sum()),
      'cross_split_pair_groups':int(df.loc[df.cross_split_pair,'pair_hash'].nunique()),
      'quality_status_counts':df.quality_status_candidate.value_counts().to_dict(),
      'quality_flag_counts':dict(Counter(f for flags in df.quality_flags for f in flags.split('|') if f)),
      'star_suitability_counts':df.star_suitability_candidate.value_counts().to_dict(),
      'rule_unclassified':int(df.rule_question_types.eq('미분류').sum()),'rule_multilabel':int(df.rule_question_types.str.contains('|',regex=False).sum()),
      'manual_sample_rows':len(sample),'manual_sample_audio':int(sample.audio_pair_available.sum()),
      'synthetic_types':dict(Counter(x['type'] for x in syn)),'synthetic_source_reused_ids':sum(n>1 for n in sources.values()),'synthetic_source_splits':dict(syn_splits),
      'elapsed_seconds':time.monotonic()-start}
    (BASE/'audit_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
