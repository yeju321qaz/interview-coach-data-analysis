"""Editorial changes only: retain measured values and graph arrays, clarify scope."""
from pathlib import Path
import re,json
from ensure_report_document import ensure_document
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'presentation_revision_20261029'
REPLACEMENTS={
'연관성은 표면 유사도라 의미 수준의 이탈은 측정하지 못합니다. "단어 비교로는 안 된다"는 것만 보여 줍니다.':'기존 실험은 오프라인 질문 짝의 표면 유사도를 측정했습니다. 실제 의미 이탈 감지의 가능·불가능이나 정확도는 이 실험만으로 결론 낼 수 없습니다.',
'문장 하나만으로 자기 질문을 가려내는 정확도는 AUC 0.77에 그친다. 질문 단어는 답변 앞 20%에만 몰려 있다.':'문장 단위 오프라인 질문 짝 구분 AUC는 약 0.77이다. 실제 실시간 이탈 감지 정확도를 측정한 값이 아니다.',
"단어 비교로는 실시간 이탈을 판단할 수 없다. '질문 핵심 항목 + 언어 모델' 설계가 맞다.":"어휘 유사도만으로 실제 이탈 판단이 충분한지는 미검증이다. 질문 핵심 항목·문맥 기반 판단은 후속 검증할 구현안이다.",
"경험형 답변에서 '결과'는 보통 60% 지점(약 47초) 이후에 나온다. STAR 네 요소를 다 말하는 답변은 9%다.":"선별 답변 9,464건에서 STAR 네 요소의 규칙 기반 동시 검출률은 약 9%다. 결과 표현의 위치·약 47초는 문장 비율로 환산한 추정이다.",
'STAR 누락 알림은 답변 중반 이후에만 띄운다. 누락이 흔하니 리포트 기능의 가치가 크다.':'실제 STAR 완성률·누락률은 사람 검수 전이다. STAR는 종료 후 피드백을 우선 검토하며, 중간 알림 시점은 초기 설계 가설이다.',
'전사 구간 확정은 0.5~0.7초 + 최대 10~15초 강제 확정에서 시작한다.':'0.5~0.7초 침묵·최대 10~15초 확정은 초기 설계 가설이다. 실제 온라인 지연·오알림 평가 전이다.',
'단어 비교로는 실시간 이탈을 잡을 수 없다':'기존 실험: 오프라인 질문 짝 구분과 어휘 유사도',
'질문과 답변의 표면 유사도(문자 2~3-gram TF-IDF)로 "이 답변이 이 질문에 대한 것인지"를 얼마나 가려낼 수 있는지 측정했습니다.':'문자 2~3-gram TF-IDF로 원래 질문–답변 쌍과 섞은 질문–답변 쌍을 구분했습니다. AUC는 이 인위적 오프라인 과제의 순위 구분 지표이며 실시간 이탈 정확도나 알림 성능이 아닙니다.',
'AUC (무작위 질문 대비)':'질문 짝 구분 AUC (무작위 질문 대비)',
'AUC (같은 유형 질문 대비)':'질문 짝 구분 AUC (같은 유형 질문 대비)',
'답변 전체 (사후 분석)':'답변 전체 · 오프라인 질문 짝 구분',
'문장 하나 (실시간 상황)':'문장 단위 · 오프라인 질문 짝 구분',
'답변이 끝난 뒤에는 단어 비교만으로도 꽤 잘 맞힙니다. 기존 서비스가 사후 분석을 하는 이유입니다. 하지만 사람들은 답변 첫 부분에서 질문을 되풀이한 뒤 질문 단어를 거의 쓰지 않습니다. 그래서 <b>"질문 단어가 줄었다 = 이탈"로 판단하면 정상 답변 대부분에서 오알림이 납니다.</b>':'원래 질문 쌍을 구분한 결과만으로 실제 이탈 감지 성능이나 기존 서비스의 설계 이유를 결론 낼 수 없습니다. 질문 어휘가 답변 위치에 따라 달라지므로 <b>어휘 겹침 감소를 곧바로 이탈로 판단하면 오알림 위험이 있습니다. 실제 오알림률은 미측정입니다.</b>',
'알림 판단 입력에 <b>누적 답변 요약</b>을 반드시 넣는다. 최근 구간만 넣지 않는다.':'초기 구현 가설: 최근 확정 구간과 <b>누적 답변 문맥</b>을 함께 사용한다. 요약의 효과·오류는 별도 검증한다.',
'답변 시작 후 15~20초는 알림을 보류한다. 질문을 되풀이하거나 상황을 설명하는 구간이다.':'초기 설계 가설: 답변 시작 후 15~20초 알림 보류를 후보로 둔다. 적절한 보류 시간은 새 녹음으로 평가한다.',
"'결과'는 답변 후반에야 나온다":"STAR 규칙 검출 위치 · 실제 완성률과 구분",
'경험·협업형 질문 답변 9,464개에 문장 단위 키워드 규칙을 적용해, STAR 요소가 처음 등장하는 위치를 봤습니다.':'경험·협업형으로 선별한 답변 9,464개에 문장 키워드 규칙을 적용했습니다. 아래 9.0%는 이 표본에서 네 요소가 모두 규칙에 검출된 비율이며 사람이 검증한 STAR 완성률이 아닙니다. 위치와 초 수는 실제 음성 정렬이 아닌 문장 비율 환산입니다.',
'STAR 요소가 처음 등장하는 위치 (중앙값)':'STAR 요소의 규칙 첫 검출 위치 (문장 비율 중앙값)',
'0% = 답변 시작, 100% = 답변 끝. 괄호는 해당 요소가 등장한 답변 비율':'0% = 문장 배열 시작, 100% = 끝. 괄호는 규칙 검출 비율. 실제 음성 시각·사람 정답 아님',
'<td>네 요소 모두 등장</td>':'<td>네 요소 모두 규칙 검출 · 선별 9,464건</td>',
'<td>결과(R) 없음</td>':'<td>결과(R) 규칙 미검출</td>',
'<td>상황 문장이 절반 이상인데 결과 없음</td>':'<td>상황 규칙 검출 문장이 절반 이상이고 결과 규칙 미검출</td>',
'S → A → R 순서로 등장 (세 요소가 다 있는 답변 중)':'S → A → R 규칙 첫 검출 순서 (세 규칙 모두 검출된 답변 중)',
"<b>키워드 규칙은 신뢰도가 낮습니다</b> · '행동' 규칙 하나를 조정했더니 행동 등장 비율이 38.5%에서 61.5%로 23%p 바뀌었습니다. 비율은 경향을 보는 참고값입니다. 이 자체가 <b>STAR 판단은 언어 모델 + 팀 라벨 검증으로 해야 한다</b>는 근거입니다.":"<b>규칙 검출률은 사람 정답이 아닙니다</b> · 이전 보고서의 규칙 변경 전 38.5%→61.5%(23%p) 비교는 과거 코드가 없어 재현하지 못했습니다. 현재 규칙의 검출 결과만 재현했으며 실제 STAR 판단은 별도 사람 정답으로 평가해야 합니다.",
'STAR 누락 알림의 최소 조건 예: "답변 경과 50% 이상(또는 40초 이상) <b>그리고</b> 해당 요소가 연속 N구간 동안 없음"':'초기 설계 가설(미검증): 답변 경과 50% 또는 40초 이후·연속 N구간 미검출 조건. 이는 STAR 누락의 정답이나 검증된 알림 허용 시점이 아닙니다.',
"답변 시간 상한(예: 90초)을 정하면 '후반부'를 정의할 수 있어 알림 타이밍을 정하기 쉽다.":"답변 시간 상한(예: 90초)은 설계 후보입니다. 실제 답변 종료 시점·사용자 방해 정도를 수집해 피드백 시점을 검증해야 합니다.",
'STAR를 다 갖춘 답변이 드물다 → 답변 후 리포트에서 <b>빠진 요소 정리</b>가 핵심 가치다.':'규칙 미검출은 실제 요소 누락을 뜻하지 않습니다. <b>종료 후 구조 피드백</b>의 정확도와 유용성도 후속 평가 항목입니다.',
'침묵 0.5~0.7초에서 시작한다':'침묵 분할 통계와 초기 설계 가설',
'답변 음성 1,198개를 침묵 기준별로 나눠 구간 길이를 측정했습니다.':'답변 음성 1,198개를 오프라인 침묵 기준별로 나눠 구간 길이를 측정했습니다. 아래 분포는 재현된 통계이며 실제 온라인 알림 지연이나 최적 임계값 검증은 아닙니다.',
'1.0초 이상이면 답변당 판단 기회가 2번뿐이라 실시간성이 사라진다. 0.3초는 문장 중간에서 잘린다.':'침묵 기준이 길어질수록 이 표본의 구간 수가 줄고 구간 길이가 늘었습니다. 문장 절단·실시간성·알림 효용은 이 통계만으로 확정할 수 없습니다.',
'<b>0.5~0.7초 + 최대 10~15초 강제 확정</b>으로 시작한다. "연속 2구간 이탈 시 알림"이면 최소 지연은 약 7~11초 + 모델 응답 시간이다.':'<b>초기 설계 가설: 침묵 0.5~0.7초·최대 10~15초·연속 2구간</b>. 기존 약 7~11초 산술 예시는 실제 최소 지연을 보장하지 않습니다. STT 확정·문맥·통신·알림 표시까지 실제 로그로 측정해야 합니다.',
'답변 시작 후 15~20초는 알림 없음. STAR 누락 알림은 답변 경과 50% 이후':'초기 설계 가설(미검증): 시작 후 15~20초 보류·STAR 중간 피드백은 경과 50% 이후를 후보로 검토. 종료 후 피드백과 분리 평가',
'침묵 0.5~0.7초 + 최대 10~15초 강제 확정으로 시작, 팀 녹음으로 조정':'초기 설계 가설(미검증): 침묵 0.5~0.7초·최대 10~15초. 새 녹음의 지연·오알림으로 선택',
'STAR 누락 알림 가능 구간':'STAR 피드백 시점 가설 · 미검증',
'STAR 요소 첫 등장 위치 점 그래프':'STAR 규칙 첫 검출 위치 점 그래프 · 음성 시각 아님',
'등장한 답변 ${cov}%':'규칙에 검출된 답변 ${cov}%',
'처음 등장 위치 중앙값 ${pos}% (약 ${sec}초)':'규칙 첫 검출 위치 ${pos}% (문장 비율 환산 약 ${sec}초)',
'<td>공식 STT 성능</td>':'<td>기존 보고서가 인용한 출처 STT 성능 · 이번 직접 검증 아님</td>',
'<td>CER 12.55%, WER 3.57%</td>':'<td>CER 12.55%, WER 3.57% (기존 인용값·실험 조건 재검증 안 됨·이번 tiny 결과와 직접 비교 불가)</td>',
'전체 답변 TF-IDF AUC':'전체 답변 오프라인 질문 짝 구분 TF-IDF AUC',
'문장 TF-IDF AUC':'문장 단위 오프라인 질문 짝 구분 TF-IDF AUC',
'STAR 네 요소 9.0%':'선별 표본의 STAR 네 요소 규칙 검출률 9.0%',
'STAR 9.0%는 선별 9,464건의 규칙 검출률입니다.':'STAR 9.0%는 선별 9,464건의 규칙 검출률이며 사람이 확인한 실제 STAR 완성률이 아닙니다.',
'<b>CER·간투사 보존·지연시간은 모두 미측정</b>입니다. 유료 API 호출과 모델 다운로드는 하지 않았습니다.':'<b>이 2단계 작성 당시에는 모두 미측정</b>이었습니다. 현재는 상단에 tiny의 12파일 실험만 추가됐고 Google/Azure 실측 비교·실시간 지연은 미실행입니다.',
'세 후보의 한국어 CER·간투사 보존율·지연시간은 모두 미측정':'이전 2단계 작성 당시 세 후보는 모두 미측정. 최신 tiny의 로컬 임시 CER·오프라인 처리시간은 상단에 별도 표시하며 Google/Azure는 현재도 미실행',
'이번 작업은 사람이 검수하거나 STT 모델을 실행한 작업이 아니다.':'이전 2단계 작업 당시에는 사람 검수·STT 모델 실행을 하지 않았다. 최신 tiny 시험은 상단의 실제 실행 결과로 구분한다.',
}

def refine(s,root_page=False):
    if '<!-- presentation-refinement-v1 -->' in s:return s
    for old,new in REPLACEMENTS.items():s=s.replace(old,new)
    while '질문 짝 구분 질문 짝 구분' in s:s=s.replace('질문 짝 구분 질문 짝 구분','질문 짝 구분')
    # Give historic appendices a local, explicit interpretation boundary.
    for sid in ['task1','task3','segment']:
        marker=f'<section id="{sid}">'
        note={'task1':'이 절의 모든 AUC는 오프라인 질문 짝 구분 지표입니다. 실제 실시간 이탈 감지 정확도·알림 지연은 미측정입니다.',
              'task3':'이 절의 9.0% 및 요소별 비율은 선별 9,464개 답변의 키워드 규칙 결과입니다. 사람 정답 STAR 완성률·누락률이 아닙니다.',
              'segment':'구간 길이는 오프라인 측정 통계입니다. 침묵·최대 길이·알림 보류·STAR 중간 피드백 시간은 초기 설계 가설이며 최적값이 아닙니다.'}[sid]
        if marker in s and marker+'<p class="caution"' not in s:s=s.replace(marker,marker+f'<p class="caution"><b>해석 범위</b> · {note}</p>')
    if not root_page:return '<!-- presentation-refinement-v1 -->\n'+s
    s=s.replace('실제 면접 답변 <em>7.6만 건</em>이<br>우리 기획에 말해 주는 것','면접코치 <em>데이터 확보·검증</em><br>실제 모델 시험과 추가 수집 계획')
    s=s.replace('<b>분석일</b> 2026-10-14','<b>기존 분석</b> 2026-10-14 · <b>재현·실험·해석 정리</b> 2026-10-29')
    s=s.replace('정확도·서로 다른 모델의 우열·실시간 지연을 뜻하지 않습니다.','정확도·서로 다른 모델의 우열·실시간 지연을 뜻하지 않습니다.')
    s=re.sub(r'<section id="collection-brief">.*?</section>','',s,flags=re.S)
    s=re.sub(r'<section id="interpretation-changes">.*?</section>','',s,flags=re.S)
    collection='''<section id="collection-brief"><div class="sec-tag">발표 핵심 04 · COLLECTION PLAN</div><h2>신규 80건 수집 계획 · 아직 미수집</h2>
<p>20명 × 4유형 = 80건: 정상·지속 이탈·일시 이탈 후 복귀·STAR 누락 각각 20건을 계획했습니다. 개발 32·검증 16·테스트 32건이며 실제 녹음은 0건입니다.</p>
<p>이탈 시작·종료·복귀·알림 허용창·STAR 근거를 두 사람이 독립 라벨링하고 불일치는 재판정합니다. 화자와 의미 질문군을 함께 분리하며 계획 ID 검사 통과와 실제 분리 완료를 구분합니다. 테스트는 유형별 8건으로 작은 표본입니다.</p>
<div class="caution"><b>가설·미실행</b> · 침묵 0.5/0.7초, 최대 10/15초 확정, 시작 15~20초 보류, 연속 N구간·cooldown, STAR 중간 피드백 시점은 모두 초기 설계 가설입니다. 새 녹음으로 지연·오알림·방해 정도를 평가해야 합니다. 48개 사람 검수는 보류합니다.</div>
<p>동일 질문 순서·기억 효과 관리, 연기/자연 이탈 구분, 별도 성장 리포트용 반복 연습 데이터 필요성은 기존 계획대로 유지합니다.</p></section>'''
    change='''<section id="interpretation-changes"><div class="sec-tag">해석 수정 기록 · 수치 변경 없음</div><h2>기존 결과에서 달라진 해석</h2><div class="tbl"><table>
<tr><th>이전 표현</th><th>정리한 해석</th></tr><tr><td>AUC를 정확도·실시간 상황으로 표현</td><td>모든 AUC는 오프라인 질문 짝 구분 과제 지표. 실제 이탈·알림 성능 미측정</td></tr>
<tr><td>STAR를 모두 말한 답변 9%</td><td>선별 9,464건의 규칙 기반 동시 검출률 9.0%. 사람 검증 완성률 아님</td></tr>
<tr><td>STT 모두 미실행 또는 후보를 함께 비교한 듯한 표현</td><td>tiny 12파일 × 두 디코딩 설정만 실제 실행. Google/Azure 실측 비교 미실행</td></tr>
<tr><td>침묵·보류·STAR 시점을 검증된 정책처럼 표현</td><td>오프라인 구간 통계와 초기 설계 가설을 분리. 최적값·최소 지연 보장 아님</td></tr>
<tr><td>모델 지표가 먼저 강조됨</td><td>데이터 확보 → 품질·재현 검증 → 실제 tiny 시험 → 신규 수집 계획을 앞에 배치</td></tr></table></div>
<p>새 실험·재계산·새 수치는 추가하지 않았습니다. 기존 그래프·상세 통계는 아래 하위 섹션에 유지합니다.</p></section>'''
    main=re.search(r'<main>(.*?)</main>',s,re.S)
    if main:
        content=main.group(1);header=re.search(r'<header class="hero">.*?</header>',content,re.S)
        blocks=re.findall(r'<section id="([^"]+)">.*?</section>',content,re.S)
        sections={m.group(1):m.group(0) for m in re.finditer(r'<section id="([^"]+)">.*?</section>',content,re.S)}
        sections['collection-brief']=collection;sections['interpretation-changes']=change
        priority=['integrated','sources','verification-20261029','stt-local','collection-brief','interpretation-changes','intent-prototype']
        order=priority+[sid for sid in blocks if sid not in priority]
        body=(header.group() if header else '')+'\n'+''.join(sections[sid] for sid in order if sid in sections)
        s=s[:main.start(1)]+body+s[main.end(1):]
    toc=[('integrated','発表の要点'.replace('発表の要点','중간발표 통합 현황')),('sources','① 데이터 확보'),('verification-20261029','② 품질·재현 검증'),('stt-local','③ 실제 tiny STT 시험'),('collection-brief','④ 신규 수집 계획'),('interpretation-changes','해석 수정 기록'),('intent-prototype','질문 짝 기준선·구현 가설'),('summary','기존 분석 요약 · 상세'),('traits','데이터 분포·품질 통계'),('task1','기존 질문 짝 AUC·그래프'),('task2','유창성 상세 분포'),('task3','STAR 규칙 검출 상세'),('segment','침묵 분할 상세 통계'),('synthetic','합성 데이터 상세'),('questions','질문 유형 상세'),('ours','서비스 데이터와 차이'),('limits','한계·재현'),('artifact-sync','Claude Artifact 반영')]
    nav=''.join(f'<li><a href="#{sid}">{label}</a></li>' for sid,label in toc)
    s=re.sub(r'(<nav class="toc"[^>]*>.*?<ol>).*?(</ol>)',lambda m:m.group(1)+nav+m.group(2),s,count=1,flags=re.S)
    return '<!-- presentation-refinement-v1 -->\n'+s

def main():
    logs=[]
    for name in ['index.html','integrated_standalone.html','verification.html','phase2.html']:
        p=ROOT/'report'/name
        if not p.exists():continue
        before=p.read_text(encoding='utf-8');after=refine(before,name in ['index.html','integrated_standalone.html'])
        if name in ['index.html','integrated_standalone.html']:after=ensure_document(after)
        p.write_text(after,encoding='utf-8');logs.append({'file':str(p.relative_to(ROOT)),'changed':after!=before})
    (OUT/'editorial_changes.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Presentation wording and order updated; no experiments run')
if __name__=='__main__':main()
