from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent.parent
css=re.search(r'<style>(.*?)</style>',(ROOT/'report/index.html').read_text(encoding='utf-8'),re.S).group(1)
page='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>48개 표본 사람 검수 | 면접코치</title><style>CSS
.review{overflow-wrap:anywhere;max-width:1000px;margin:32px auto;padding:20px}label{display:block;margin:10px 0}input,select,textarea,button{font:inherit;max-width:100%;padding:7px;border:1px solid var(--line);border-radius:4px;background:var(--surface);color:var(--ink)}button{cursor:pointer}textarea{width:100%;min-height:90px}#types{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}#answer{white-space:pre-wrap;line-height:1.9}audio{width:100%}.actions{display:flex;flex-wrap:wrap;gap:10px;position:sticky;bottom:0;background:var(--bg);padding:12px 0}#message{color:var(--accent);min-height:1.5em}.controls{border:1px solid var(--line);padding:16px}summary{cursor:pointer}fieldset{border:1px solid var(--line);margin:16px 0}legend{font-weight:600}</style></head><body><main class="review">
<p><a href="index.html#phase2">기존 분석으로 돌아가기</a></p><h1>48개 표본 사람 검수</h1>
<p>자동 분류는 후보입니다. 먼저 독립적으로 판정하고 필요할 때 자동 결과를 펼쳐 비교하세요. 완료는 입력한 검수자 1인의 판단이며 최종 합의 정답이 아닙니다.</p>
<div class="controls"><label>검수자 ID <input id="reviewer" placeholder="예: R01" autocomplete="off"></label>
<label>① 로컬 검수 세트 JSON 불러오기 <input id="dataset_file" type="file" accept=".json"></label>
<p class="small">phase2_review_stt_20261029/review/review_subset48.json을 선택하세요. 질문·답변은 HTML에 내장하지 않고 직접 고른 파일에서만 읽습니다.</p>
<label>② 이전에 내보낸 본인 결과 복원 (선택) <input id="results_file" type="file" accept=".csv"></label>
<p class="small">입력 내용은 이 브라우저의 검수자별 로컬 저장소에 임시 저장됩니다. 파일/브라우저가 달라지면 복원되지 않을 수 있으므로 CSV를 내려받으세요. 공유 PC에서는 원문·입력이 남는 점에 유의하세요.</p></div>
<p id="progress" aria-live="polite">사람 검수 완료 0개 · 검수 세트를 불러오세요.</p><p id="message" role="status"></p>
<div id="workspace" hidden><h2 id="sample_id"></h2><p id="stratum"></p><p id="row_status"></p>
<h3>질문</h3><p id="question"></p><h3>답변 전문</h3><p id="answer"></p>
<h3>답변 음성</h3><audio id="audio" controls preload="none"></audio><p id="audio_note"></p>
<details id="automatic_details"><summary>자동 분류·STAR 후보 확인</summary><p id="automatic"></p></details>
<fieldset><legend>질문 유형 (복수 선택)</legend><div id="types"></div></fieldset>
<label>STAR 적용 적합성 <select id="human_star_applicable"><option value="">선택</option><option value="yes">적합: 실제 경험의 상황·역할·행동·결과 요구</option><option value="no">비적합: 가정·동기·지식 등</option><option value="uncertain">판단 보류</option></select></label>
<label>질문–답변 관련성 <select id="question_answer_match"><option value="">선택</option><option value="relevant">관련 있음</option><option value="partial">일부만 관련</option><option value="unrelated">관련 없음</option><option value="uncertain">판단 보류</option></select></label>
<label>전사–실제 음성 일치 <select id="transcript_audio_match"><option value="">선택</option><option value="match">대체로 일치</option><option value="mismatch">실질적 불일치</option><option value="uncertain">판단 보류</option><option value="not_available">음성 없음</option></select></label>
<label><input id="audio_listened" type="checkbox"> 실제 음성을 직접 들었습니다 (음성 보유 행 필수)</label>
<label>활용 품질 판정 <select id="human_quality_status"><option value="">선택</option><option value="usable">사용 가능</option><option value="review">추가 검수 필요</option><option value="exclude">제외 제안</option></select></label>
<label>판정 근거·불일치 구절 <textarea id="evidence_notes" placeholder="유형·STAR·관련성의 근거와 청취한 전사 오류를 적으세요."></textarea></label>
<div class="actions"><button id="prev">이전</button><button id="save_review">검수 완료로 저장</button><button id="next">다음</button></div></div>
<button id="export">전체 48행 결과 CSV 내보내기</button><p class="small">미작성 행도 ‘미검수’로 함께 내보냅니다. 작성 중인 행은 완료로 계산하지 않습니다. 검수자 2명은 각자 다른 ID와 CSV를 사용하세요.</p>
</main><script src="review_app.js"></script></body></html>'''.replace('CSS',css,1)
(ROOT/'report/review.html').write_text(page,encoding='utf-8')
print('Built local-only review.html')

