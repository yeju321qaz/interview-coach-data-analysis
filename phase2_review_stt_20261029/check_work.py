import sys,csv,json,hashlib,importlib.util,tempfile,argparse,subprocess,contextlib,io
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    spec=importlib.util.spec_from_file_location('experiment',BASE/'stt/experiment.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    cases=[('가나다','가나다',0,0,0),('가나다','가라다',1,0,0),('가나다','가다',0,1,0),('가다','가나다',0,0,1),('','가',0,0,1)]
    for ref,hyp,s,d,i in cases:
        metrics,_=e.edit_alignment(ref,hyp);assert (metrics['S'],metrics['D'],metrics['I'])==(s,d,i)
    assert e.normalize(' Ａ, 어! A\n')=='ａ어a'
    assert e.normalize('가 나. A!')=='가나a'
    assert e.edit_alignment('어음','어음')[1]=={1:1,0:0}
    subset=read(BASE/'review/review_subset48.csv');source=read(ROOT/'verification_20261029/review/manual_review.csv')
    assert len(subset)==48 and len({r['id'] for r in subset})==48
    assert set(r['id'] for r in subset)<=set(r['id'] for r in source)
    assert all(r['human_review_status']=='미검수' and r['final_decision']=='' for r in subset)
    plan=read(BASE/'collection/recording_plan_80_v2.csv');original=read(ROOT/'verification_20261029/collection/recording_plan_80.csv');old={r['recording_id']:r for r in original}
    for r in plan:
        for field in ['recording_id','speaker_id','split','question_family_id','question','scenario_target','status']:assert r[field]==old[r['recording_id']][field]
    for split,nper in [('development',2),('validation',1),('test',2)]:
        for kind in ['normal','sustained_drift','temporary_drift','star_missing']:
            for pos in range(1,5):assert sum(r['split']==split and r['scenario_target']==kind and int(r['collection_order'])==pos for r in plan)==nper
    stt=read(BASE/'stt/manifest12.csv');assert len(stt)==12
    assert all(r['reference_status']=='unreviewed' and not r['reference_corrected'] for r in stt)
    gate=argparse.Namespace(manifest=str(BASE/'stt/manifest12.csv'),limit=1,provider='google',execute=True,max_minutes=15,output=str(BASE/'stt/never_created.jsonl'),allow_paid=False,data_permission_confirmed=False,model_dir=None)
    try:
        with contextlib.redirect_stdout(io.StringIO()):e.run(gate)
    except SystemExit as error:assert 'requires --allow-paid' in str(error)
    else:raise AssertionError('Cloud gate did not stop execution')
    assert not Path(gate.output).exists()
    with tempfile.TemporaryDirectory(dir=BASE) as temp:
        mapping=Path(temp)/'merged.csv';output=Path(temp)/'split.json'
        with mapping.open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=['question_family_id','semantic_family_id','reviewer_1','reviewer_2']);w.writeheader()
            w.writerows({'question_family_id':r,'semantic_family_id':'SAME_TEST_FAMILY','reviewer_1':'TEST_R1','reviewer_2':'TEST_R2'} for r in sorted({v['question_family_id'] for v in plan}))
        result=subprocess.run([sys.executable,str(BASE/'collection/validate_split.py'),'--family-map',str(mapping),'--output',str(output)],capture_output=True)
        assert result.returncode==1 and json.loads(output.read_text(encoding='utf-8'))['state']=='FAIL'
    checks=[]
    for r in read(BASE/'before_hashes.csv'):
        p=Path(r['Path'])
        with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
        checks.append({'path':str(p.relative_to(ROOT)),'unchanged':h.upper()==r['Hash']})
    # Except for the new section appended to index, previous deliverables remain intact.
    assert all(r['unchanged'] for r in checks if r['path']!='report\\index.html')
    original_site=(BASE/'backup/index.html').read_text(encoding='utf-8');site=(ROOT/'report/index.html').read_text(encoding='utf-8')
    assert original_site.split('<style>')[1].split('</style>')[0]==site.split('<style>')[1].split('</style>')[0]
    assert original_site.split('<script>')[1].split('</script>')[0]==site.split('<script>')[1].split('</script>')[0]
    result={'status':'PASS','review_subset_rows':48,'human_review_completed':0,'stt_samples':12,'stt_model_calls':0,'model_downloads':0,'CER_algorithm_tests':len(cases)+3,'cloud_execution_gate':'PASS','cross_split_semantic_leak_fixture':'REJECTED_AS_EXPECTED','plan_position_balance':'PASS','preservation':checks,'legacy_css_js_unchanged':True}
    (BASE/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
