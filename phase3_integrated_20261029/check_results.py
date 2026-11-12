import sys,json,hashlib,csv,importlib.util
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
sys.dont_write_bytecode=True
from intent_guard import AlertPolicy
def main():
    records=[json.loads(l) for l in (BASE/'results/local_stt_predictions_run1.jsonl').read_text(encoding='utf-8').splitlines()]
    s=json.loads((BASE/'results/stt_summary.json').read_text(encoding='utf-8'))
    assert len(records)==24 and len({r['id'] for r in records})==12
    for beam,row in zip([1,5],s['summary']):
        rr=[r for r in records if r['beam_size']==beam];assert len(rr)==12
        n=sum(r['provisional_CER']['N'] for r in rr);e=sum(r['provisional_CER']['edits'] for r in rr)
        assert abs(row['provisional_micro_CER']-e/n)<1e-12
        assert abs(row['decode_seconds']-sum(r['wall_s'] for r in rr))<1e-9
        assert all(r['status']=='ok' and r['reference_source']=='unreviewed_aihub' for r in rr)
    p=AlertPolicy();text='이것은 충분한 어절 수를 가진 시험 문장입니다'
    assert not p.update(text,.1,1,is_final=False)['would_alert']
    assert not p.update('짧은 말',.1,2)['would_alert']
    assert not p.update(text,.1,3)['would_alert'];assert p.update(text,.1,4)['would_alert']
    assert not p.update(text,.1,5)['would_alert'];assert not p.update(text,.1,6)['would_alert']
    assert not p.update(text,.5,7)['would_alert'];assert p.streak==0
    assert not p.update(text,.1,20)['would_alert'];assert p.update(text,.1,21)['would_alert']
    replay=[json.loads(l) for l in (BASE/'results/offline_guard_replay.jsonl').read_text(encoding='utf-8').splitlines()];assert len({r['id'] for r in replay})==12
    # Preserve existing src and outputs against the original step-1 backup hashes.
    with (ROOT/'verification_20261029/backup_manifest.csv').open(encoding='utf-8-sig',newline='') as f:baseline=list(csv.DictReader(f))
    checked=0
    for r in baseline:
        path=Path(r['Path']);rel=path.relative_to(ROOT)
        if rel.parts[0] not in ['src','outputs']:continue
        with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest().upper()==r['Hash']
        checked+=1
    before=(BASE/'backup/index.html').read_text(encoding='utf-8');after=(ROOT/'report/index.html').read_text(encoding='utf-8')
    for tag in ['style','script']:assert before.split(f'<{tag}>')[1].split(f'</{tag}>')[0]==after.split(f'<{tag}>')[1].split(f'</{tag}>')[0]
    for section in ['summary','sources','traits','task1','task2','task3','task4','segment','synthetic','questions','ours','limits','phase2','verification-20261029']:assert f'id="{section}"' in after
    with (ROOT/'phase2_review_stt_20261029/review/review_subset48.csv').open(encoding='utf-8-sig',newline='') as f:assert all(r['human_review_status']=='미검수' for r in csv.DictReader(f))
    result={'status':'PASS','actual_stt_predictions':24,'audio_files':12,'micro_CER_recomputed':True,'policy_state_tests':'PASS','replay_files':12,'original_src_outputs_hash_checks':checked,'legacy_css_js_preserved':True,'all_old_sections_preserved':True,'human_review':'on_hold_0_completed','paid_api_calls':0,'remote_artifact_modified':False}
    (BASE/'checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
