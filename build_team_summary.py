"""Team-facing overview; existing detailed report remains a separate page."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parent
def main(detail=None):
    prior=ROOT/'team_summary_20261030/backup/public_index.html'
    if detail is None:
        latest=ROOT/'public_interview_report/dist/details.html'
        detail=(latest if latest.exists() else prior).read_text(encoding='utf-8')
    heading_changes={
        '면접코치 <em>데이터 확보·검증</em><br>실제 모델 시험과 추가 수집 계획':'면접코치 <em>데이터 분석</em>',
        '중간발표: 실제 수행과 계획을 구분하기':'분석·실험 현황 및 수집 계획',
        '1. 현재 무엇이 끝났는가':'1. 진행 현황',
        '3. STT 후보 비교에서 아는 것과 모르는 것':'3. STT 비교 결과 및 미검증 항목',
        '쓸 수 있는 데이터는 무엇인가':'데이터 확보 및 활용 범위',
        '기존 결과에서 달라진 해석':'기존 결과의 해석 수정',
        '1. 완료된 것과 부족한 것':'1. 완료 항목 및 보완 과제',
        '3. 구현할 데이터 처리 흐름':'3. 데이터 처리 흐름',
        '4. 이번에 실제 구현한 작은 기준선':'4. 질문 짝 구분 기준선',
        '현재 HTML은 원격 Artifact와 자동 동기화하지 않습니다':'로컬 HTML과 Claude Artifact의 관리 범위',
        '1. 지금 수정한 대상':'1. 수정 대상',
        '전사문 특성 · STT 비교 정답으로 쓸 때':'STT 비교용 전사 특성',
        '&quot;얼마나 좋아지는가&quot;는 우리 데이터로만 알 수 있다':'반복 연습 효과의 평가 조건',
        '"얼마나 좋아지는가"는 우리 데이터로만 알 수 있다':'반복 연습 효과의 평가 조건',
        '녹음 전에 텍스트로 먼저 튜닝한다':'합성 텍스트를 활용한 사전 시험',
        '실제 면접은 상황 가정형 질문이 가장 많다':'질문 유형별 분포',
        '우리 서비스의 데이터는 무엇이 다른가':'서비스 환경과 기존 데이터의 차이',
    }
    def noun_heading(match):
        return match.group(1)+heading_changes.get(match.group(2),match.group(2))+match.group(3)
    detail=re.sub(r'(<h[1-6][^>]*>)(.*?)(</h[1-6]>)',noun_heading,detail,flags=re.S)
    detail=re.sub(r'<title>.*?</title>','<title>면접코치 데이터 분석 · 상세 보고서</title>',detail,count=1,flags=re.S)
    css=re.search(r'<style>(.*?)</style>',detail,re.S).group(1)
    summary='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>면접코치 · 팀 공유용 핵심 정리</title><style>CSS</style></head><body>
<div class="wrap"><nav class="toc" aria-label="목차"><div class="label">면접코치 · 팀 공유</div><ol>
<li><a href="#data">1. 확보한 데이터</a></li><li><a href="#stt">2. 실제 시험 결과</a></li><li><a href="#how">3. 구현·검증 방식</a></li><li><a href="#plan">4. 더 모아야 할 데이터</a></li><li><a href="#next">5. 발표 전 할 일</a></li><li><a href="DETAIL">상세 통계·기존 보고서 ↗</a></li></ol></nav>
<main><header class="hero"><div class="eyebrow">Human-AI Interaction · 11월 6일 중간발표 준비</div><h1>면접코치 <em>지금까지 한 일과</em><br>앞으로 필요한 데이터</h1>
<p class="lede">면접 답변 데이터를 확보하고 기존 분석을 다시 확인했습니다. 무료 음성인식 시험도 진행했습니다. 이제 실제 질문 이탈을 평가할 녹음과 정답이 필요합니다.</p><div class="meta"><span><b>팀 공유 정리</b> 2026-10-30</span><span><b>분석·실험 기준</b> 2026-10-29</span></div></header>

<section id="data"><div class="sec-tag">01 · 확보·검증 완료</div><h2>분석할 데이터는 확보했습니다</h2>
<div class="tbl"><table><tr><th>확보한 것</th><th>규모</th><th>쓸 수 있는 곳</th></tr><tr><td>질문·답변 전사</td><td><b>76,105건</b></td><td>질문 유형·답변 특성 분석</td></tr><tr><td>실제 음성</td><td><b>1,198쌍 · 약 27.25시간</b></td><td>음성인식·말하기 특성 시험</td></tr><tr><td>자동 품질 기준 통과 후보</td><td><b>75,983건</b></td><td>목적에 맞는 추가 검수 후 활용</td></tr></table></div>
<p>출처는 AI Hub 「채용면접 인터뷰 데이터」입니다. 기존 분석을 다시 실행해 <b>12개 결과 파일의 내용이 일치</b>하는 것을 확인했습니다.</p>
<div class="caution"><b>구분할 점</b> · 자동 기준을 통과했다는 뜻이지, 사람이 확인한 좋은 답변이라는 뜻은 아닙니다. 실제 음성은 전체 전사 데이터의 일부입니다.</div></section>

<section id="stt"><div class="sec-tag">02 · 실제 실행 완료</div><h2>음성을 글로 바꾸는 시험을 했습니다</h2>
<p>무료 로컬 음성인식 모델 <b>Whisper tiny</b>로 음성 12개, 약 14.47분을 전사했습니다. 같은 모델의 두 설정을 비교했습니다.</p>
<div class="tbl"><table><tr><th>시험 설정</th><th>문자 오류 비율(CER)</th><th>전체 처리시간</th></tr><tr><td>설정 1</td><td>21.12%</td><td>약 82초</td></tr><tr><td>설정 2</td><td>14.30%</td><td>약 137초</td></tr></table></div>
<p>이번 표본에서는 설정 2의 오류 비율이 낮고 시간이 더 걸렸습니다. ‘어·음’ 같은 추임새가 빠질 수 있어 유창성 분석에는 추가 확인이 필요합니다.</p>
<p class="small">CER는 기준 전사와 비교한 문자 단위 오류 비율입니다. 사람이 검수하지 않은 AI Hub 전사 기준의 임시 결과이며, 실제 서비스의 정확도나 실시간 반응속도를 검증한 것은 아닙니다. Google·Azure 음성인식 비교는 아직 계획 단계입니다.</p></section>

<section id="how"><div class="sec-tag">03 · 구현·검증 방식</div><h2>서비스는 이렇게 작동하도록 준비합니다</h2>
<div class="apply"><div class="t">처리 흐름</div><p><b>면접 음성</b> → 글로 변환 → 질문의 핵심과 답변 비교 → 이탈이 지속되면 알림 → 답변 종료 후 구조·유창성 리포트</p></div>
<p>현재는 질문과 답변의 단어 관계를 비교하는 간단한 기준선과, 판단이 불확실하면 알림을 보류하는 규칙을 시험했습니다. <b>실제 이탈을 정확히 잡는지는 아직 검증하지 않았습니다.</b></p>
<p>질문과 다른 답변을 구분한 기존 수치를 실시간 이탈 감지 정확도로 쓰지 않습니다. STAR도 키워드로 살핀 탐색 결과이며, 사람이 확인한 답변 완성률은 아닙니다. 알림을 언제 띄울지도 검증 전 설계안입니다.</p></section>

<section id="plan"><div class="sec-tag">04 · 계획 완료 / 수집 전</div><h2>이탈 시점과 알림 정답은 직접 모아야 합니다</h2>
<p>기존 데이터에는 <b>언제 질문에서 벗어났고, 돌아왔으며, 언제 알림이 필요한지</b>에 대한 정답이 없습니다.</p>
<div class="tbl"><table><tr><th>녹음 유형</th><th>계획</th></tr><tr><td>질문에 맞게 답하는 경우</td><td>20건</td></tr><tr><td>다른 주제로 계속 벗어나는 경우</td><td>20건</td></tr><tr><td>잠깐 벗어났다가 돌아오는 경우</td><td>20건</td></tr><tr><td>경험 답변에서 STAR 요소를 빠뜨린 경우</td><td>20건</td></tr></table></div>
<p>총 <b>20명 × 4유형 = 80건</b>을 계획했습니다. 두 사람이 이탈·복귀·알림 시점과 STAR 근거를 표시하고, 의견이 다르면 다시 판정합니다. 개발·검증·최종 평가에 같은 사람이나 의미가 같은 질문이 섞이지 않도록 나눕니다.</p>
<p class="small">실제 녹음은 아직 0건입니다. 연기한 이탈과 자연스럽게 생긴 이탈을 구분합니다. 최종 평가 표본은 유형별 8건이라 큰 성능 결론을 내리기에는 작습니다. 연습 후 성장은 별도 전후 녹음이 필요합니다.</p></section>

<section id="next"><div class="sec-tag">05 · 팀에서 확인할 것</div><h2>중간발표에서는 이 세 가지를 설명하면 됩니다</h2>
<ol><li><b>무슨 데이터를 확보했는가:</b> 전사·음성 규모와 품질 점검, 기존 분석 재현 결과.</li><li><b>실제로 어디까지 해 봤는가:</b> 무료 tiny 전사 시험과 간단한 질문 비교 기준선. 실제 이탈 정확도는 미검증.</li><li><b>부족한 정답을 어떻게 만들 것인가:</b> 80건 녹음의 유형·분할·시간 라벨과 평가 방법.</li></ol>
<p>다음 실행을 위해 참여자·질문 배정과 의미 중복, 녹음·라벨링 담당을 정해야 합니다. 48개 사람 검수는 현재 보류 상태로 유지합니다.</p>
<p><a href="DETAIL"><b>근거가 필요할 때: 기존 그래프·상세 통계·전체 보고서 보기 →</b></a></p>
<p class="small">이 페이지는 기존 결과를 쉽게 요약한 것입니다. 새로운 실험이나 수치를 추가하지 않았으며 원문 음성·전사·개인별 검수 데이터는 공개하지 않습니다.</p></section>
</main></div></body></html>'''.replace('CSS',css,1)
    wording={
        '면접코치 · 팀 공유용 핵심 정리':'면접코치 데이터 분석',
        '면접코치 · 팀 공유':'면접코치 데이터 분석',
        '1. 확보한 데이터':'1. 데이터 확보 현황',
        '2. 실제 시험 결과':'2. STT 실험 결과',
        '3. 구현·검증 방식':'3. 구현 및 검증 방식',
        '4. 더 모아야 할 데이터':'4. 추가 데이터 수집 계획',
        '5. 발표 전 할 일':'5. 중간발표 핵심 내용',
        '면접코치 <em>지금까지 한 일과</em><br>앞으로 필요한 데이터':'면접코치 <em>데이터 분석</em>',
        'Human-AI Interaction · 11월 6일 중간발표 준비':'Human-AI Interaction · 중간발표',
        '면접 답변 데이터를 확보하고 기존 분석을 다시 확인했습니다. 무료 음성인식 시험도 진행했습니다. 이제 실제 질문 이탈을 평가할 녹음과 정답이 필요합니다.':'AI Hub 면접 데이터의 확보 현황, 분석 결과와 음성인식 시험, 추가 수집 계획을 정리했습니다.',
        '팀 공유 정리':'문서 정리',
        '분석할 데이터는 확보했습니다':'데이터 확보 및 품질 점검',
        '음성을 글로 바꾸는 시험을 했습니다':'STT 실험 결과',
        '서비스는 이렇게 작동하도록 준비합니다':'구현 및 검증 방식',
        '이탈 시점과 알림 정답은 직접 모아야 합니다':'추가 데이터 수집 계획',
        '중간발표에서는 이 세 가지를 설명하면 됩니다':'중간발표 핵심 내용',
        '01 · 확보·검증 완료':'01 · 데이터 현황',
        '02 · 실제 실행 완료':'02 · 실험 결과',
        '03 · 구현·검증 방식':'03 · 구현·검증',
        '04 · 계획 완료 / 수집 전':'04 · 수집 계획',
        '05 · 팀에서 확인할 것':'05 · 발표 내용',
        '<th>확보한 것</th>':'<th>데이터</th>',
        '<th>쓸 수 있는 곳</th>':'<th>활용 목적</th>',
        '<b>구분할 점</b> · 자동 기준을 통과했다는 뜻이지, 사람이 확인한 좋은 답변이라는 뜻은 아닙니다. 실제 음성은 전체 전사 데이터의 일부입니다.':'<b>해석상 유의사항</b> · 자동 품질 점검 결과이며 사람 검수는 미완료 상태입니다. 실제 음성은 전체 전사 데이터 중 일부만 확보했습니다.',
        '<b>무슨 데이터를 확보했는가:</b>':'<b>데이터 확보·검증:</b>',
        '<b>실제로 어디까지 해 봤는가:</b>':'<b>STT 시험·구현 현황:</b>',
        '<b>부족한 정답을 어떻게 만들 것인가:</b>':'<b>신규 데이터 수집·평가:</b>',
        '근거가 필요할 때: 기존 그래프·상세 통계·전체 보고서 보기 →':'상세 분석 보고서 · 그래프 및 통계 →',
        '이 페이지는 기존 결과를 쉽게 요약한 것입니다. 새로운 실험이나 수치를 추가하지 않았으며 원문 음성·전사·개인별 검수 데이터는 공개하지 않습니다.':'기존 분석 결과의 요약본입니다. 원문 음성·전사·개인별 검수 데이터는 공개하지 않습니다.',
    }
    for old,new in wording.items():summary=summary.replace(old,new)
    for name,link in [('public_interview_report/dist/index.html','details.html'),('report/team_summary.html','integrated_standalone.html')]:
        (ROOT/name).write_text(summary.replace('DETAIL',link),encoding='utf-8')
    (ROOT/'public_interview_report/dist/details.html').write_text(detail,encoding='utf-8')
    (ROOT/'team_summary_20261030/변경내용.md').write_text('''# 팀 공유용 요약 개편 — 2026-10-30

- 공개 사이트 첫 화면을 핵심 5개 섹션으로 축약했다: 데이터 확보, 실제 STT 시험, 쉬운 구현·검증 방식, 추가 수집, 발표 전 할 일.
- 코드·파일 경로·모델 학습 세부·AUC 및 STAR 규칙 수치는 첫 화면에서 빼고 상세 페이지에 보존했다.
- 기존 전체 공개 보고서를 details.html로 그대로 보존했으며 기존 그래프·통계는 삭제하지 않았다.
- 원래 로컬 report/index.html과 integrated_standalone.html은 유지하고, 로컬 요약은 report/team_summary.html로 별도 생성했다.
- 새 실험과 수치는 없으며 48개 검수 보류·신규 녹음 0건·Google/Azure 미실행을 유지했다.
''',encoding='utf-8')
    print('Team summary built; previous full public report preserved as details.html')
if __name__=='__main__':main()
