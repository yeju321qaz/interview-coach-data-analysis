"""Descriptive analysis only: no predictive model, no drift ground truth.
Run with the existing verification_20261029/packages dependencies.
"""
import os, sys, json, hashlib, platform
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'verification_20261029/packages'), str(ROOT/'src')]
os.environ['MPLCONFIGDIR'] = str(BASE/'mplconfig')
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
import pandas as pd
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
from sklearn.feature_extraction.text import TfidfVectorizer
from audio_features import frame_db, HOP
from coach_features import sentences
from common import setup_matplotlib

def save(df, name):
    df.to_csv(BASE/(name+'.csv'), index=False, encoding='utf-8-sig')

def quant(x):
    a=np.asarray(x, dtype=float)
    return dict(zip(['p25','p50','p75','p90'], np.quantile(a,[.25,.5,.75,.9]))) if len(a) else dict.fromkeys(['p25','p50','p75','p90'],np.nan)

def audio_one(path):
    x,sr=sf.read(path, dtype='float64',always_2d=True)
    db=frame_db(x[:,0]); p10,p90=np.percentile(db,[10,90]); mask=db>max(p90-30,p10+6)
    ids=np.flatnonzero(mask)
    if not len(ids): return [],dict(file=path.stem,sr=sr,status='no_voice')
    first,last=ids[0],ids[-1]
    v=mask[first:last+1]
    b=np.r_[0,np.flatnonzero(np.diff(v.astype(int)))+1,len(v)]
    rows=[]
    for t in [.5,.7]:
        start=0; spans=[]
        for s,e in zip(b[:-1],b[1:]):
            if not v[s] and (e-s)*HOP/sr>=t:
                if s>start: spans.append((start,s))
                start=e
        if start<len(v):spans.append((start,len(v)))
        for i,(s,e) in enumerate(spans):
            a=(first+s)*HOP/sr; z=(first+e)*HOP/sr
            # Final segment can be confirmed only if enough observed silence follows.
            enough=(len(mask)*HOP/sr-z)>=t-1e-8
            rows.append(dict(file=path.stem,thr=t,idx=i,start_s=a,end_s=z,seg_s=z-a,
                             confirm_s=z+t if enough else np.nan,final=i==len(spans)-1,
                             confirmation_observed=enough))
    return rows,dict(file=path.stem,sr=sr,status='ok',duration_s=len(x)/sr)

def audio():
    paths=sorted((ROOT/'data').glob('*/01.원천데이터/*/ckmk_a_*.wav'))
    result=[];inventory=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,(rows,inv) in enumerate(pool.map(audio_one,paths)):
            result.extend(rows);inventory.append(inv)
            if i%200==0:print('audio',i,flush=True)
    seg=pd.DataFrame(result).sort_values(['file','thr','idx']); save(seg,'audio_segments')
    save(pd.DataFrame(inventory),'audio_inventory')
    old=pd.read_csv(ROOT/'outputs/segments.csv'); old=old[old.thr.isin([.5,.7])]
    keys=['file','thr']
    # Legacy multiprocessing order differs across files; within-file order is retained.
    old=old.assign(idx=old.groupby(keys).cumcount()).sort_values(keys+['idx'])
    check=old.merge(seg,on=keys+['idx'],suffixes=('_old','_new'),validate='one_to_one')
    assert len(check)==len(old)==len(seg)
    assert np.allclose(check.seg_s_old,check.seg_s_new,atol=1e-9)
    assert len(paths)==1198 and seg.file.nunique()==1198
    stats=[];counts=[]; windows=[]
    for t,g in seg.groupby('thr'):
        stats.append(dict(thr=t,n=len(g),answers=g.file.nunique(),**quant(g.seg_s)))
        c=g.groupby('file').size()
        counts.append(dict(thr=t,answers=len(c),total_segments=int(c.sum()),mean=c.mean(),**quant(c)))
        for file,a in g.groupby('file',sort=False):
            a=a.sort_values('idx').reset_index(drop=True)
            for k in [1,2,3]:
                for i in range(len(a)-k+1):
                    f=a.iloc[i]; l=a.iloc[i+k-1]
                    windows.append(dict(file=file,thr=t,k=k,start_idx=i,
                        content_sum_s=a.iloc[i:i+k].seg_s.sum(),span_s=l.end_s-f.start_s,
                        confirmation_wait_s=l.confirm_s-f.start_s,
                        from_answer_voice_start_s=l.confirm_s-a.iloc[0].start_s,
                        confirmation_observed=l.confirmation_observed))
    w=pd.DataFrame(windows);save(w,'consecutive_windows');save(pd.DataFrame(stats),'segment_summary');save(pd.DataFrame(counts),'segments_per_answer')
    ws=[]
    for (t,k),g in w.groupby(['thr','k']):
        for metric in ['content_sum_s','span_s','confirmation_wait_s']:
            ws.append(dict(thr=t,k=k,metric=metric,n=g[metric].notna().sum(),
                unavailable=g[metric].isna().sum(),**quant(g[metric].dropna())))
    save(pd.DataFrame(ws),'window_summary')
    return seg,pd.DataFrame(stats),pd.DataFrame(counts),pd.DataFrame(ws)

def relevance(audio_files):
    lab=pd.read_csv(ROOT/'outputs/labels.csv',keep_default_na=False)
    # Corpus weights only. This reuses the prior descriptive lexical method;
    # no classifier/semantic model fitting or prediction accuracy claims.
    vec=TfidfVectorizer(analyzer='char_wb',ngram_range=(2,3),min_df=5,sublinear_tf=True)
    print('corpus weighting',len(lab),flush=True)
    vec.fit(pd.concat([lab.q_text,lab.a_text]))
    allrows=[]
    for lo in range(0,len(lab),2000):
        chunk=lab.iloc[lo:lo+2000]; rows=[]
        for ri,r in chunk.iterrows():
            ss=sentences(r.a_text)
            for j,s in enumerate(ss):rows.append(dict(row=ri,id=r.id,file=Path(r.a_audio).stem,idx=j,n_sent=len(ss),chars=len(s),pos=(j+.5)/len(ss),text=s))
        d=pd.DataFrame(rows)
        S=vec.transform(d.text); Q=vec.transform(lab.loc[d.row,'q_text'])
        d['score']=np.asarray(S.multiply(Q).sum(axis=1)).ravel()
        allrows.append(d)
        if lo%10000==0:print('sentences',lo,flush=True)
    sd=pd.concat(allrows,ignore_index=True)
    sd['audio_subset']=sd.file.isin(audio_files)
    thresholds={str(p):float(sd.score.quantile(p)) for p in [.1,.25,.4]}
    # Do not export text publicly. Full sentence scores are local audit artifacts.
    save(sd,'sentence_scores_local')
    transitions=[];runs=[]; runstats=[];poss=[]
    for scope,d in [('all',sd),('audio1198',sd[sd.audio_subset])]:
        for p,cut in thresholds.items():
            nlow=0; nprev=0; nll=0; nhigh=0; nhl=0; rr=[]
            for file,g in d.groupby('file',sort=False):
                low=(g.score.to_numpy()<cut); nlow+=low.sum()
                nprev+=low[:-1].sum();nll+=(low[:-1]&low[1:]).sum()
                nhigh+=(~low[:-1]).sum();nhl+=((~low[:-1])&low[1:]).sum()
                b=np.r_[0,np.flatnonzero(np.diff(low.astype(int)))+1,len(low)]
                for s,e in zip(b[:-1],b[1:]):
                    if low[s]:
                        r=dict(scope=scope,quantile=float(p),cut=cut,file=file,start_idx=s,length=e-s,
                               returns_higher=e<len(low),starts_answer=s==0,ends_answer=e==len(low))
                        rr.append(r); runs.append(r)
            runstats.append(dict(scope=scope,quantile=float(p),cut=cut,sentences=len(d),answers=d.file.nunique(),
                low_sentences=int(nlow),low_share=nlow/len(d),runs=len(rr),
                runs_ge2=sum(r['length']>=2 for r in rr),runs_ge3=sum(r['length']>=3 for r in rr),
                returns_higher=sum(r['returns_higher'] for r in rr),**quant([r['length'] for r in rr])))
            transitions.append(dict(scope=scope,quantile=float(p),cut=cut,low_to_low=int(nll),previous_low=int(nprev),
                p_low_given_low=nll/nprev if nprev else np.nan,high_to_low=int(nhl),previous_high=int(nhigh),p_low_given_high=nhl/nhigh if nhigh else np.nan))
        z=d.copy();z['bin']=pd.cut(z.pos,[0,.2,.4,.6,.8,1],labels=['0–20%','20–40%','40–60%','60–80%','80–100%'])
        for b,g in z.groupby('bin',observed=True):poss.append(dict(scope=scope,position=str(b),n=len(g),mean=g.score.mean(),**quant(g.score)))
    save(pd.DataFrame(runs),'low_sentence_runs_local');save(pd.DataFrame(runstats),'relevance_summary');save(pd.DataFrame(transitions),'transitions');save(pd.DataFrame(poss),'position_summary')
    # Text-only policy: first alert per low sentence run, reset at first higher-score sentence.
    policy=[]
    rr=pd.DataFrame(runs)
    for (scope,p),g in rr.groupby(['scope','quantile']):
        denominator=sd.file.nunique() if scope=='all' else len(audio_files)
        for k in [1,2,3]:
            eligible=g[g.length>=k]
            policy.append(dict(scope=scope,quantile=p,k=k,alert_candidates=len(eligible),answers_with_candidate=eligible.file.nunique(),answers=denominator,
                               candidates_per_answer=len(eligible)/denominator,wait_unit='sentences; no measured seconds'))
    save(pd.DataFrame(policy),'sentence_policy_counts')
    return sd,thresholds

def simulation(seg,sd,thresholds):
    records=[];events=[]
    subset=sd[sd.audio_subset]; bytext={f:g.sort_values('idx') for f,g in subset.groupby('file')}
    for mapping in ['characters','equal_sentences']:
        for (t,file),a in seg.groupby(['thr','file'],sort=False):
            a=a.sort_values('idx').reset_index(drop=True); s=bytext[file]
            lengths=a.seg_s.to_numpy(); cumulative=np.r_[0,lengths.cumsum()]
            weights=s.chars.to_numpy(dtype=float) if mapping=='characters' else np.ones(len(s))
            text_edges=np.r_[0,np.cumsum(weights/weights.sum())*cumulative[-1]]
            overlap=np.maximum(0,np.minimum(cumulative[1:,None],text_edges[None,1:])-np.maximum(cumulative[:-1,None],text_edges[None,:-1]))
            for p,cut in thresholds.items():
                low=s.score.to_numpy()<cut
                frac=overlap[:,low].sum(axis=1)/lengths
                flags=frac>=.5
                b=np.r_[0,np.flatnonzero(np.diff(flags.astype(int)))+1,len(flags)]
                runs=[(start,end) for start,end in zip(b[:-1],b[1:]) if flags[start]]
                for kind,value in [('segments',1),('segments',2),('segments',3),('duration',5),('duration',10),('duration',15)]:
                    waits=[];unavailable=0
                    for start,end in runs:
                        if kind=='segments': j=start+value-1
                        else:j=start+np.searchsorted(np.cumsum(lengths[start:end]),value,side='left')
                        if j>=end:continue
                        if pd.isna(a.iloc[j].confirm_s):unavailable+=1;continue
                        wait=a.iloc[j].confirm_s-a.iloc[start].start_s
                        waits.append(wait)
                        events.append(dict(mapping=mapping,thr=t,quantile=float(p),policy=kind,value=value,file=file,
                            run_start_idx=start,trigger_idx=int(j),wait_s=wait,answer_time_s=a.iloc[j].confirm_s,
                            content_wait_s=lengths[start:j+1].sum()))
                    records.append(dict(mapping=mapping,thr=t,quantile=float(p),policy=kind,value=value,file=file,
                        alerts=len(waits),unconfirmed=unavailable,low_segments=int(flags.sum()),n_segments=len(a)))
    ev=pd.DataFrame(events);rec=pd.DataFrame(records); save(ev,'simulated_events_local');save(rec,'simulated_answer_counts_local')
    out=[]
    keys=['mapping','thr','quantile','policy','value']
    for key,g in rec.groupby(keys):
        e=ev
        for k,v in zip(keys,key):e=e[e[k]==v]
        out.append(dict(zip(keys,key))|dict(answers=len(g),alerts=int(g.alerts.sum()),answers_with_alert=int((g.alerts>0).sum()),
            alerts_per_answer=g.alerts.mean(),unconfirmed=int(g.unconfirmed.sum()),**quant(e.wait_s)))
    summary=pd.DataFrame(out);save(summary,'simulation_summary')
    return summary

def plots(seg,ws,sd,sim):
    plt=setup_matplotlib()
    fig,ax=plt.subplots(figsize=(9,5))
    for t,g in seg.groupby('thr'):
        x=np.sort(g.seg_s);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=f'침묵 {t}초 (n={len(x):,})')
    ax.set(xlabel='음성 구간 길이 (초)',ylabel='누적 비율',title='음성 구간 길이의 실제 분포');ax.set_xlim(0,40);ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(BASE/'01_segment_cdf.png',dpi=180);fig.savefig(BASE/'01_segment_cdf.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5))
    d=ws[ws.metric=='confirmation_wait_s']
    for t,g in d.groupby('thr'):
        x=g.k.to_numpy()+(-.06 if t==.5 else .06); y=g.p50.to_numpy()
        ax.errorbar(x,y,yerr=[y-g.p25.to_numpy(),g.p75.to_numpy()-y],fmt='o-',capsize=5,label=f'{t}초 기준: p25–p75')
        ax.scatter(x,g.p90,marker='x',s=65,label=f'{t}초 기준: p90')
    ax.set(xticks=[1,2,3],xlabel='연속 관측 구간 수',ylabel='첫 구간 시작 → 마지막 경계 확인 (초)',title='실제 연속 구간으로 계산한 관측 대기시간\n이탈 시작·처리 지연을 측정한 값이 아님');ax.legend(fontsize=9);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(BASE/'02_wait_windows.png',dpi=180);fig.savefig(BASE/'02_wait_windows.svg');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.8))
    d=pd.read_csv(BASE/'position_summary.csv');d=d[d.scope=='all']
    axs[0].plot(d.position,d['mean'],marker='o');axs[0].set(title='답변 위치별 어휘 유사도 평균',xlabel='문장 순서 기준 상대 위치',ylabel='TF-IDF 코사인 유사도')
    r=pd.read_csv(BASE/'relevance_summary.csv');r=r[(r.scope=='all')&(r['quantile']==.25)].iloc[0]
    axs[1].bar(['1개 이상','2개 이상','3개 이상'],[r.runs,r.runs_ge2,r.runs_ge3],color=['#2a78d6','#eb6834','#1baf7a'])
    axs[1].set(title='저유사도 연속 문장 묶음 수 (하위 25% 기준)',ylabel='묶음 수 · 실제 이탈 건수 아님')
    for ax in axs:ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(BASE/'03_relevance_patterns.png',dpi=180);fig.savefig(BASE/'03_relevance_patterns.svg');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,5))
    for mapping,style in [('characters','-'),('equal_sentences','--')]:
        for t,color in [(.5,'#2a78d6'),(.7,'#eb6834')]:
            d=sim[(sim.mapping==mapping)&(sim.thr==t)&(sim['quantile']==.25)&(sim.policy=='segments')].sort_values('value')
            label=f'{t}초 · '+('글자 수 배치' if mapping=='characters' else '문장 균등 배치')
            axs[0].plot(d.value,d.alerts_per_answer,style,marker='o',color=color,label=label)
            axs[1].plot(d.value,d.p50,style,marker='o',color=color,label=label)
    axs[0].set(ylabel='답변당 가상 알림 횟수',title='가정에 따른 알림 발생량')
    axs[1].set(ylabel='판단 대기시간 중앙값 (초)',title='알림이 발생한 경우에 한한 대기시간')
    for ax in axs:ax.set(xticks=[1,2,3],xlabel='연속 구간 정책');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('시간 정렬이 없는 전사를 가상 배치한 민감도 분석 · 실제 알림 성능 아님',fontsize=12)
    fig.tight_layout();fig.savefig(BASE/'04_simulated_policies.png',dpi=180);fig.savefig(BASE/'04_simulated_policies.svg');plt.close(fig)

def main():
    BASE.mkdir(exist_ok=True)
    seg,stats,counts,ws=audio()
    sd,thresholds=relevance(set(seg.file))
    sim=simulation(seg,sd,thresholds)
    plots(seg,ws,sd,sim)
    meta=dict(date='2026-11-02',python=sys.version,platform=platform.platform(),thresholds=thresholds,
        audio_answers=seg.file.nunique(),text_answers=sd.file.nunique(),sentences=len(sd),
        audio_sentences=int(sd.audio_subset.sum()),legacy_segments_match=True,
        limitations=['offline adaptive energy threshold uses whole file','no gold drift labels','no sentence/audio alignment','no STT or model inference delay'],
        versions={p:__import__('importlib.metadata',fromlist=['version']).version(p) for p in ['numpy','pandas','scipy','scikit-learn','soundfile','matplotlib']})
    (BASE/'analysis_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
