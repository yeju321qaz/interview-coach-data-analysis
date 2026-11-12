"""Check arithmetic, policy invariants, and byte-for-byte preservation."""
import sys,json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'verification_20261029/packages'))
import pandas as pd
import numpy as np

def main():
    read=lambda n:pd.read_csv(BASE/(n+'.csv'))
    a=read('audio_segments'); inv=read('audio_inventory');s=read('sentence_scores_local');sim=read('simulation_summary');e=read('simulated_events_local')
    assert inv.file.nunique()==1198 and set(inv.sr)=={16000}
    wavs=list((ROOT/'data').glob('*/01.원천데이터/*/ckmk_q_*.wav'))
    assert len(wavs)==1198
    assert {p.stem.replace('ckmk_q_','ckmk_a_',1) for p in wavs}==set(inv.file)
    assert set(s[s.audio_subset].file)==set(inv.file)
    for (t,f),g in a.groupby(['thr','file']):
        assert (g.end_s>g.start_s).all()
        assert np.allclose(g.end_s-g.start_s,g.seg_s)
        assert np.allclose(g.confirm_s-g.end_s,t)
        assert np.all(g.start_s.to_numpy()[1:]-g.end_s.to_numpy()[:-1]>=t-1e-8)
    assert len(sim)==72 and (sim.answers==1198).all()
    assert (e.wait_s>=e.content_wait_s-1e-8).all()
    assert (e[e.policy=='duration'].content_wait_s>=e[e.policy=='duration'].value-1e-8).all()
    assert ((e[e.policy=='segments'].trigger_idx-e[e.policy=='segments'].run_start_idx+1)==e[e.policy=='segments'].value).all()
    for key,g in sim.groupby(['mapping','thr','quantile','policy']):
        g=g.sort_values('value'); assert (np.diff(g.alerts)<=0).all()
        assert (np.diff(g.answers_with_alert)<=0).all()
    # Recalculate summaries directly from event log.
    for _,r in sim.iterrows():
        z=e
        for k in ['mapping','thr','quantile','policy','value']:z=z[z[k]==r[k]]
        assert len(z)==r.alerts and z.file.nunique()==r.answers_with_alert
        assert np.isclose(z.wait_s.median(),r.p50)
    before=json.loads((BASE/'before_manifest.json').read_text(encoding='utf-8'))
    checks=[]
    for r in before:
        p=ROOT/r['path']; now=p.read_bytes()
        if r['path'].startswith('outputs/'):
            ok=hashlib.sha256(now).hexdigest()==r['sha256'];mode='unchanged bytes'
        elif p.suffix=='.html':
            removed=re.sub(b'<!-- alert-timing-20261102:start -->.*?<!-- alert-timing-20261102:end -->',b'',now,flags=re.S)
            ok=hashlib.sha256(removed).hexdigest()==r['sha256'];mode='only new section added'
        else:
            old=(BASE/'backup'/r['path']).read_bytes();ok=now.startswith(old);mode='original byte prefix preserved'
        checks.append(dict(path=r['path'],preserved=ok,mode=mode));assert ok,r['path']
    (BASE/'preservation_check.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    inputs=[]
    for p in [ROOT/'outputs/labels.csv',ROOT/'outputs/segments.csv',ROOT/'src/audio_features.py',ROOT/'src/coach_features.py',ROOT/'src/proposal_analysis.py']:
        inputs.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (BASE/'input_provenance.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
    # Only allow aggregates and figures in the published addition.
    public=ROOT/'public_interview_report/dist/alert-timing'
    assert not any('local' in p.name or p.suffix in ['.wav','.jsonl'] for p in public.iterdir())
    print(json.dumps(dict(paired_answers=1198,policy_combinations=len(sim),preservation_files=len(checks),all_passed=True)))

if __name__=='__main__': main()
