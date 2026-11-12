"""Check deliverable invariants and preservation; does not modify input data."""
import csv,json,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
def readcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    a=json.loads((BASE/'audit_summary.json').read_text(encoding='utf-8'))
    comparisons=json.loads((BASE/'comparison.json').read_text(encoding='utf-8'))
    sample=readcsv(BASE/'review/manual_review.csv')
    plan=readcsv(BASE/'collection/recording_plan_80.csv')
    assert sum(a['source_files'].values())==sum(a['parse_statuses'].values())==76106
    assert a['schema_success']==76105
    assert a['schema_success']+len(a['errors'])==76106
    assert sum(a['quality_status_counts'].values())==76105
    assert len(sample)==275 and len({r['id'] for r in sample})==275
    assert sum(r['audio_pair_available']=='True' for r in sample)==60
    assert all(r['human_review_status']=='미검수' and r['final_decision']=='' for r in sample)
    assert len(plan)==80 and len({r['speaker_id'] for r in plan})==20
    assert all(r['status']=='미수집' for r in plan)
    for field in ['speaker_id','question_family_id']:
        groups={}
        for r in plan: groups.setdefault(r[field],set()).add(r['split'])
        assert all(len(v)==1 for v in groups.values())
    for name in ['recordings','utterances','relevance_segments','drift_events','star_labels','system_events','adjudication']:
        assert len(readcsv(BASE/'collection'/f'{name}.csv'))==0
    assert len(comparisons)==12 and all(r['status'] in ['바이트 일치','수치·내용 일치(행순서/직렬화 차이)'] for r in comparisons)
    baseline=readcsv(BASE/'backup_manifest.csv')
    unchanged=[];modified=[]
    for r in baseline:
        p=Path(r['Path']); rel=p.relative_to(ROOT)
        assert sha(BASE/'backup'/rel)==r['Hash'].lower()
        if sha(p)==r['Hash'].lower():unchanged.append(str(rel))
        else:modified.append(str(rel))
    assert set(modified)=={'report\\index.html','데이터분석_보고서.md'}
    web=json.loads((BASE/'web_check.json').read_text(encoding='utf-8'))
    assert web['pageErrors']==[]
    # New section is unique; legacy JS and CSS remain byte-for-byte in decoded text.
    before=(BASE/'backup/report/index.html').read_text(encoding='utf-8')
    after=(ROOT/'report/index.html').read_text(encoding='utf-8')
    for tag in ['style','script']:
        assert before.split(f'<{tag}>')[1].split(f'</{tag}>')[0]==after.split(f'<{tag}>')[1].split(f'</{tag}>')[0]
    assert after.count('id="verification-20261029"')==1
    result={'status':'PASS','original_files_hash_unchanged':unchanged,'authorized_modified_originals':modified,
            'backup_hash_checks':len(baseline),'comparison_files':len(comparisons),'manual_review_rows':len(sample),'planned_uncollected_recordings':len(plan),
            'source_outputs_preserved':True,'legacy_css_js_preserved':True,'web_page_errors':web['pageErrors'],
            'limits':'data 원본의 전후 SHA-256 전수 비교는 하지 않았음. 모든 데이터 접근 코드는 읽기 전용이며 데이터 수정 명령은 실행하지 않았음. 의미·화자·전사 정답은 미검수.'}
    (BASE/'final_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='original_files_hash_unchanged'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
