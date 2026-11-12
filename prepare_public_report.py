"""Create a public static copy; never upload raw interview data or local tooling."""
from pathlib import Path
import re,json,hashlib
from ensure_report_document import ensure_document
ROOT=Path(__file__).resolve().parent
source=ensure_document((ROOT/'report/integrated_standalone.html').read_text(encoding='utf-8'))
original_hash=hashlib.sha256(source.encode()).hexdigest()
q=re.search(r'<section id="questions">.*?</section>',source,re.S)
if q:
    clean=re.sub(r'<div class="tbl"><table>.*?</table></div>','<p class="small">공개본에는 개별 원문 질문을 싣지 않았습니다. 유형별 집계와 분석 결과만 제공합니다.</p>',q.group(),flags=re.S)
    source=source[:q.start()]+clean+source[q.end():]
source=re.sub(r'C:(?:\\|/)[^<\n]+','[로컬 실행 환경 경로]',source)
source=re.sub(r'ckmk_[A-Za-z0-9_]+','[개별 데이터 ID 비공개]',source)
source=source.replace('<title>면접코치 데이터 분석</title>','<title>면접코치 데이터 분석 통합 보고서</title>')
banner='<div class="caution"><b>공개용 읽기 전용 보고서</b> · 데이터 집계·실행 결과·향후 계획을 제공합니다. 원본 음성·답변 전사·검수 CSV·모델 파일은 공개하지 않습니다. 검수 도구와 Python 실행은 로컬 전용입니다. 기준일 2026-10-29.</div>'
source=source.replace('<main>','<main>'+banner,1)
source=source.replace('48개 표본 검수 화면 열기','검수 도구 안내 (로컬 전용)').replace('검수 시작</div>','검수 도구 안내 · 현재 보류</div>')
source=source.replace('href="#phase2">검수 화면','href="#phase2">검수 도구 안내 (로컬 전용)')
source=source.replace('단일 HTML에는 기존 보고서의 질문 예시가 남아 있을 수 있으므로 외부 업로드 전 사용자가 데이터 이용 범위를 확인한다.','이 공개본에서는 기존 보고서의 개별 원문 질문 목록과 PC 전용 절대 경로를 제외했다.')
source=source.replace('단일 HTML 열기 / 전달용','통합 현황으로 이동')
out=ROOT/'public_interview_report/dist/index.html';out.write_text(source,encoding='utf-8')
assert '지금까지 협업을 하면서 가장 어려웠던 것과' not in source
assert 'C:\\Users\\user' not in source and 'C:/Users/user' not in source
assert not re.search(r'(?:src|href)="(?:file:|\.\./data)',source)
audit={'source':'report/integrated_standalone.html','source_sha256':original_hash,'published_files':['dist/index.html'],
       'individual_question_table_removed':True,'absolute_pc_paths_removed':True,'raw_audio_transcript_csv_models_included':False,'original_files_modified':False,
       'public_html_sha256':hashlib.sha256(source.encode()).hexdigest()}
(ROOT/'public_report_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print('Public report prepared; original files preserved')
if (ROOT/'team_summary_20261030').exists():
    from build_team_summary import main as build_summary
    build_summary(detail=source)
    audit['published_files']=['dist/index.html','dist/details.html']
    audit['public_html_sha256']=hashlib.sha256((ROOT/'public_interview_report/dist/index.html').read_bytes()).hexdigest()
    audit['detail_html_sha256']=hashlib.sha256((ROOT/'public_interview_report/dist/details.html').read_bytes()).hexdigest()
    (ROOT/'public_report_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
