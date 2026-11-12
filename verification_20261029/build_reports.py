"""Build evidence-led Markdown reports and append a section to the backed-up site."""
import sys,json,re,hashlib,csv,html
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
sys.path.insert(0,str(BASE/'packages'))
import pandas as pd

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(v).replace('|',' / ').replace('\n',' ') for v in row)+' |' for row in rows])

def write(name,s): (BASE/name).write_text(s,encoding='utf-8')

def main():
    a=json.loads((BASE/'audit_summary.json').read_text(encoding='utf-8'))
    comparisons=json.loads((BASE/'comparison.json').read_text(encoding='utf-8'))
    timings=[json.loads(s) for s in (BASE/'timings.jsonl').read_text().splitlines()]
    env=json.loads((BASE/'environment.json').read_text())
    counts=pd.read_csv(BASE/'review/question_type_counts.csv')
    star=pd.read_csv(BASE/'reproduced/star.csv')
    segments=pd.read_csv(BASE/'reproduced/segments.csv')
    synthetic=[json.loads(s) for s in (BASE/'reproduced/synthetic_eval.jsonl').read_text(encoding='utf-8').splitlines()]
    all4=int(star[[f'has_{k}' for k in 'STAR']].all(axis=1).sum())
    proposal=(BASE/'reproduced/proposal_summary.txt').read_text(encoding='utf-8')
    full_auc=re.search(r'무작위 질문 대비 ([0-9.]+), 같은 유형 질문 대비 ([0-9.]+)',proposal).groups()
    sentence_auc=re.search(r'문장 하나만 보고 가려내는 AUC \(무작위 질문 대비\): ([0-9.]+)',proposal).group(1)
    comp_table=table(['산출물','대조 결과'],[(r['file'],r['status']) for r in comparisons])
    type_table=table(['규칙 유형','텍스트 건수','전체 대비','음성 연결 쌍','자동 품질 통과 후보','품질 검수 필요'],[(r.rule_type,f'{r.count:,}',f'{r.share_all:.2%}',r.audio_pairs,r.usable_candidate,r.review_required) for r in counts.itertuples()])
    core=table(['항목','기존 보고','재현/직접 점검','판정'],[
      ('원본 JSON 파일','76,106',sum(a['source_files'].values()),'일치; ZIP 원본 항목 기준. 폴더 목록 개수도 일치'),
      ('엄격 JSON 파싱 성공','분리 표기 없음',a['parse_statuses']['ok'],'나머지 5건은 strict=False, 1건은 파싱 불가'),
      ('실제 라벨 분석 대상','76,105',a['schema_success'],'일치; 의미·전사 품질 합격 수는 아님'),
      ('분석 Training/Validation','68,077 / 8,028','68,077 / 8,028','일치; 원본 Training은 68,078'),
      ('WAV 수·길이','2,396 / 약 27.3시간',f"{a['wav_count']:,} / {a['wav_hours']:.6f}시간",'일치; WAV 헤더와 음향 재실행'),
      ('음성 질문·답변 쌍','1,198',a['audio_pairs'],'일치; 76,105쌍 전체 WAV 보유 아님'),
      ('전체 라벨 답변 길이 중앙값','약 82초',f"{a['answer_median_seconds']:.2f}초",'일치; 음성 표본은 77.52초'),
      ('전체 라벨 답변 길이 합','약 1,698시간',f"{a['answer_hours_metadata']:.3f}시간",'메타데이터 합; 보유 WAV 시간과 다름'),
      ('전체 답변 TF-IDF AUC','0.969 / 같은 유형 0.934',f'{full_auc[0]} / 같은 유형 {full_auc[1]}','일치; 질문 짝 구분 실험'),
      ('문장 TF-IDF AUC','0.766',sentence_auc,'일치; 실제 이탈 감지 정답·시간 평가 없음'),
      ('STAR 네 요소 규칙 검출','9.0%',f'{all4:,}/{len(star):,} = {all4/len(star):.2%}','선별된 경험·협업형 답변에서만 계산'),
      ('0.5초 침묵 분할 중앙값','약 3.4초',f'{segments.loc[segments.thr.eq(.5),"seg_s"].median():.2f}초','실제 스트리밍 알림 지연 아님'),
      ('합성 세트','4유형 각 50, 총 200',len(synthetic),'원문 짜깁기 기반 자동 라벨; 정답 검수 미수행')])
    write('재현_검증보고서.md',f'''# 기존 분석 재현 검증 보고서

검증일: 2026-10-29. 대상은 현재 로컬 프로젝트다. 기존 `src/`와 `outputs/`는 수정하지 않았다. 코드·산출물·웹사이트·기존 보고서는 `backup/`에 복사했고, `backup_manifest.csv`로 코드·산출물·웹사이트의 SHA-256을 기록했다. 원본 데이터는 대용량이므로 복사하지 않고 읽기 전용으로 사용했다. 현재 폴더는 Git 저장소가 아니어서 커밋 이력은 없다.

## 1. 실행 환경과 보존 방법

실행 Python: `{env['executable']}` / {env['python'].splitlines()[0]}.
기본 `python`은 WindowsApps 경로에서 실패했고 `py -0p`는 등록된 Python이 없다고 보고했다. 별도 Python 3.12 실행 파일은 실행 가능했다. 필요한 추가 패키지는 검증 폴더의 `packages/`에만 설치했다. 예전 환경 명세가 없어 과거와 완전히 동일한 버전이라고 보장할 수 없다. 현재 버전은 `environment.json`과 `requirements_verified.txt`에 기록한다.

{table(['패키지','버전'],env['packages'].items())}

`reproduce.py`가 기존 모듈 import 전에 `common.OUT`을 `reproduced/`로 지정한다. 분석식은 변경하지 않았으며, 음성 병렬 작업자 수만 4개로 제한했다. 기존 스크립트를 직접 실행하면 원래 outputs를 덮어쓸 수 있으므로 반드시 래퍼로 실행한다. label_stats의 원래 동작대로 Downloads에 남아 있는 라벨 ZIP을 읽었으며, 음성은 data 폴더의 WAV를 읽었다. ZIP과 풀린 JSON의 개수는 일치하나 76,106개 개별 파일의 바이트 대조는 하지 않았다.

## 2. 주요 수치 검증

{core}

전체 JSON 76,106 = 엄격 파싱 76,100 + 관대한 파싱 5 + 실패 1이다. 분석 대상 76,105 = 엄격 파싱과 관대한 파싱의 합이며 이번 실행에서 스키마 처리도 성공했다. 실패 파일은 `Training/ckmk_d_ict_m_n_337139`이다. 수치가 정상 재현되었다는 사실과 데이터가 서비스 정답으로 신뢰할 만하다는 판단을 구분한다.

WAV 2,396개는 모두 16kHz·mono·16bit다. 라벨 길이와 WAV 헤더 길이의 최대 차이는 {a['wav_duration_max_abs_diff']:.6f}초다. 기존 ‘모두 일치’ 표현은 소수점 반올림 수준의 일치이며 엄밀한 동일값은 아니어서 웹사이트·기존 문서에 허용 오차를 명시했다. 파일명 ID 연결은 76,105행에서 일관됐지만 질문과 답변의 의미적 연결·음성과 전사 일치는 사람 청취 검수가 필요하다.

## 3. 저장 산출물과 재실행 산출물 비교

{comp_table}

CSV는 열/행 수와 내용을 대조했다. 바이트가 다르면 숫자 열은 절대·상대 허용 오차 각각 1e-9, 나머지는 문자열 비교했다. segments는 병렬 처리로 행 순서가 달라질 수 있어 모든 열로 정렬 후 비교한다. PNG는 버전·글꼴 영향 때문에 바이트 동일성을 통계 재현 판정으로 쓰지 않으며 재생성 여부를 확인한다. 세부 결과는 `comparison.json`에 있다.

## 4. 실행 범위와 비용

{table(['단계','이번 실행 소요(초)'],[(r['stage'],f"{r['seconds']:.2f}") for r in timings])}

별도 원본 감사·선별 실행은 {a['elapsed_seconds']:.2f}초였다. 위 시간은 이 PC의 이번 실행값이고 일반적인 실행시간 보장은 아니다. 네 기존 분석의 전체 계산을 실행했으므로 핵심 단계 미실행을 표본 결과로 대체하지 않았다. 외부 STT/LLM 호출, 음성 청취 검수, 실제 이탈·STAR 정답 평가, 신규 녹음은 실행하지 않았다.

## 5. 방법론적 한계와 기존 주장 정정

- TF-IDF는 전체 질문·답변으로 어휘/IDF를 맞추고 원래 짝과 무작위 짝을 비교한다. 독립 학습/평가가 아니고 실제 이탈 음성의 AUC도 아니다. 무작위 섞기에서 자기 자신이나 같은 질문이 들어갈 수 있다. 실시간 이탈 정확도 수치로 발표하면 안 된다.
- STAR는 경험/협업 규칙 및 과거 경험 표현으로 선별한 뒤 2문장 미만을 제외한 9,464건에 적용한다. ‘9.0%만 좋은 답변’이라고 해석할 수 없다. 키워드 위치를 문장 수로 나누고 답변 길이를 곱한 초 수는 실제 음성 시각이 아니다.
- 침묵 임계값은 각 파일 전체의 에너지 백분위로 산정한다. 이는 미래 음성을 사용하는 오프라인 계산이어서 그대로 온라인 지연 성능으로 일반화할 수 없다. 최대 10/15초 확정과 연속 N구간 규칙은 기존 코드에서 성능 검증되지 않았다.
- 음성은 Validation 6개 하위셋, 질문/답변 각 1,198개다. 표본 선정의 무작위 추출 근거가 없어 편의표본으로 취급한다. 34세 이하 신입 기준표도 텍스트 n=31,713, 음향 n=454로 분모가 다르다.
- 연령·경력의 인과적 영향은 통제하지 않았다. 기존 설명의 ‘상당 부분은 연령 차이’는 인과 결론이 아니다. p값과 분포 차이는 사용자 전달력의 좋고 나쁨 정답이 아니다.
- 기존 ‘STAR 행동 규칙 수정 전 38.5%→61.5%’는 이전 코드 버전이 없어 재현하지 못했다. 현재 규칙 검출률만 확인했다. STT별 간투사 삭제 여부·30초 입력 제약 역시 이번 실험에서 검증하지 않았다.
- 공식 소개는 라벨 구축량 84,134건을 기재한다. 로컬 76,106건을 AI Hub 전체 구축량이라고 말하지 않는다. 차이 8,028건의 부재 원인은 이번 조사에서 확정하지 않았다. 출처: [AI Hub](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71592), 2026-10-29 확인.

## 6. 재현 명령

프로젝트 루트 PowerShell에서 `verification_20261029/run.ps1`을 사용한다. 실행 환경 변경 시 `requirements_verified.txt`를 참고하되 기존 원본 분석은 직접 실행하지 않는다. 감사와 보고서 생성까지의 정확한 순서는 `README.md`에 정리했다. 검증 폴더에서 재실행하면 그 안의 생성물을 갱신하므로 사람이 입력한 검수·라벨 CSV는 먼저 별도 사본으로 보관한다.

## 7. 웹사이트 확인

기존 HTML·CSS·JavaScript를 유지하고 별도 검증 섹션과 상세 보고서 페이지를 추가했다. Chrome의 file URL에서 실제 렌더링을 점검했다. 기존 SVG 그래프 4개, 새 섹션 1개, 추가 이미지 로드, 상세 페이지 표 9개를 확인했고 JavaScript page error는 0개였다. 390px 모바일 화면의 document width도 390px로 전체 가로 넘침은 없었다. 데스크톱 화면을 직접 시각 확인했다. 결과와 화면은 `web_check.json` 및 `*_desktop.png`, `index_mobile.png`에 있다. 외부 공개·배포는 하지 않았다.
''')
    samples=pd.read_csv(BASE/'review/manual_review.csv').fillna('')
    sample_text=[]
    chosen=set()
    for typ in ['경험/성과','상황가정/대처','지원동기/입사후포부','직무/전문성']:
        r=samples[samples.rule_question_types.str.contains(typ,regex=False)&~samples.id.isin(chosen)].iloc[0]
        chosen.add(r.id)
        sample_text.append(f"### {typ} 규칙 표본\n\n- ID: `{r.id}`\n- 질문: {r.q_text}\n- 답변 발췌: {r.a_text[:260]}{'…' if len(r.a_text)>260 else ''}\n- 자동 유형: {r.rule_question_types}\n- STAR 적합성 후보: {r.star_suitability_candidate}\n- 사람 정답: 미검수. 질문 원문과 답변 전문은 manual_review.csv에서 확인한다.\n")
    write('데이터_활용가능성.md',f'''# 질문 유형별 실제 활용 가능성

## 1. 지금 확보한 데이터와 활용 범위

텍스트 분석 대상 {a['schema_success']:,}건과 로컬 음성 연결 {a['audio_pairs']:,}쌍을 구분한다. 음성은 질문은행·텍스트 관련성 실험의 필수 조건이 아니지만 STT/음향 평가에는 실제 WAV가 필요하다. 음성이 없다는 이유만으로 텍스트 행을 제외하지 않았다. 반대로 오디오 경로 메타데이터가 있다는 이유만으로 실제 파일이 있다고 판단하지 않았다.

## 2. 질문 유형 분포와 활용 후보

아래 유형은 기존 12개 키워드 규칙을 그대로 재실행한 **복수 라벨**이다. 합계가 100%가 되지 않는다. 미분류 {a['rule_unclassified']:,}건, 복수 유형 {a['rule_multilabel']:,}건이다. 자기소개 7건은 0건이 아니며, 기존 0.0%는 소수 첫째 자리 반올림이다.

{type_table}

경험/성과·협업 질문은 실제 과거 사건을 묻는지 확인한 뒤 STAR 검수 후보로 쓴다. 상황가정은 우선순위·대응 이유, 지원동기는 지원 이유·직무 연계, 직무형은 개념 정확성·적용 근거 중심으로 검수한다. 지원동기 규칙에 ‘우리 회사’, 직무 규칙에 ‘직무’만 포함돼도 걸리므로 실제 의미 유형과 다를 수 있다. 특히 직무형 규칙에는 상황가정 문제가 함께 들어간다. 유형별 수치는 정답 데이터 규모가 아닌 검수 대상 규모다.

## 3. STAR 적합성 구분

이번 추가 선별은 질문에 ‘경험/했/있었/었던/였던/해결한/극복한’이 있고 ‘만약/다면/시겠/가정’이 없으면 적합 후보, 과거형과 가정형이 함께 있으면 검수 필요, 나머지는 비적합 후보로 구분했다. 이 간단한 규칙은 후보 탐색용이며 사람이 재판정해야 한다. 기존 STAR 검출 분석의 9,464건과는 **다른 필터**다.

{table(['후보 판정','건수'],a['star_suitability_counts'].items())}

가정형·지원동기형·지식형에 STAR를 일괄 강제하지 않는다. 각 질문의 핵심 요구 항목을 `evaluation_items_candidate`에 제안했고, `human_evaluation_items`로 확정하도록 했다. 사람 검수가 끝난 STAR 적용 가능 데이터 규모는 아직 알 수 없다.

## 4. 연결·중복·전사 점검

- 라벨 ID 중복 {a['id_duplicates']}건, 질문·답변 파일명 ID 불일치 {a['id_link_failures']}건, 정규화 질문=답변 {a['question_answer_equal']}건.
- 고유 질문 원문 {a['unique_questions_raw']:,}개, 정규화 후 {a['unique_questions_normalized']:,}개. 정규화는 NFC·영문 소문자·한글 완성형/영문/숫자 외 문자 제거다. 의미 중복·바꿔 쓰기를 해결하지 않으며 띄어쓰기 제거로 서로 다른 표현이 합쳐질 수 있어 원문을 함께 보존했다.
- 정규화 답변 중복 {a['answer_duplicate_groups']}개 그룹 / {a['answer_duplicate_rows']}행, 정규화 QA 쌍 중복 {a['pair_duplicate_rows']}행. 중복 답변은 템플릿·짧은 공통 답변일 수 있어 삭제하지 않고 검수 대상으로 표시했다.
- Training/Validation에 걸친 정규화 질문 {a['cross_split_question_groups']}개 그룹 / {a['cross_split_question_rows']}행. 동일 답변 및 동일 QA 쌍의 분할 간 중복은 이번 정규화 기준에서 0개다. 이는 화자·의미 수준의 누수가 없다는 뜻이 아니다.
- WAV 헤더 읽기 {a['wav_count']:,}개 성공, 연결 {a['audio_pairs']:,}쌍. 최장 라벨 길이 오차 {a['wav_duration_max_abs_diff']:.6f}초. 의미 연결과 전사 정확도는 청취하지 않았으므로 미확인이다.
- 관대한 파싱 5건, NFC 불일치 3건, 어절 수 불일치 84건은 목록으로 남겼다. 간투사와 숫자·영문 표기, 반복 발화가 실제 음성과 맞는지는 검수 CSV의 청취 필드에 기록해야 한다.

합성 200개는 원본 source_id의 중복 사용은 {a['synthetic_source_reused_ids']}개이며 Training 182행·Validation 18행에서 나왔다. 삽입된 답변의 ID는 저장돼 있지 않아 삽입 출처 중복을 완전히 감사하지 못한다. `normal`은 사람이 정상으로 판단한 답변이 아니고, `star_missing`은 정규식 문장 삭제 결과다. 기존 합성은 개발용으로만 쓴다.

## 5. 사용 가능 / 검수 필요 / 제외 기준

| 단계 | 기준 | 이번 규모 | 해석 |
|---|---|---:|---|
| 사용 가능 후보 | 필수 전사·양수 길이·ID 연결이 정상이고 이번 품질 플래그 없음 | {a['quality_status_counts'].get('사용 가능 후보',0):,} | 텍스트 탐색 사용 후보. 유형·관련성·음성 전사 정답 확인 아님 |
| 품질 검수 필요 | 관대한 파싱, NFC/어절수 불일치, 정규화 답변·QA 중복, 제어/대체문자, 음성 이름 모호성 중 하나 이상 | {a['quality_status_counts'].get('검수 필요',0):,} | 수정·제외를 사람이 결정. 중복 플래그는 합산 시 겹칠 수 있음 |
| 제외 | 파싱/필수 스키마 실패 또는 빈 전사·비양수 길이·ID 연결 실패 | 1 | 파싱 불가 원본 1건. 원본을 삭제하지 않고 별도 제외 목록에 기록 |

미분류·복수 유형·STAR 적합성 불명확은 **과제별 라벨 검수 대상**이며 자동 품질 상태와 별개의 축이다. 최종 ‘사용 가능’은 목적에 맞는 질문 유형·QA 의미 연결·전사·권한 확인을 마친 뒤 사람이 승인한다. 오디오 전용 과제는 실제 음성 연결과 청취 확인을 추가 조건으로 둔다. 현재 사람 승인 완료 수는 0건이다.

## 6. 수동 검수 CSV 사용법

`review/manual_review.csv`는 고정 시드 20261029로 만든 {a['manual_sample_rows']}행이다. 각 규칙 유형과 미분류에서 최대 20개(가능하면 음성 5개 + 비음성 15개)를 뽑고 품질 플래그 표본 최대 30개를 추가했다. 자기소개는 7개 전부 포함했다. 같은 행이 여러 층에서 뽑히면 한 행으로 합쳤다. 음성 청취 가능 행은 {a['manual_sample_audio']}개다. **전체 비율을 추정하는 확률 표본이 아니며**, 이 표본의 오분류율을 전체에 그대로 일반화하지 않는다.

검수자는 `human_question_type`(복수 허용), `human_star_applicable`(yes/no/uncertain), `question_answer_match`, `transcript_audio_match`(match/mismatch/uncertain/not_available), `human_quality_status`, `human_evaluation_items`, `evidence_notes`를 채운다. 모델 후보를 가리고 독립적으로 라벨링할 때에는 CSV 사본에서 rule/candidate 열을 숨긴다. 라벨러 2인은 별도 사본에 작성하고 ID로 병합한다. 이 파일에는 실제 질문·답변 원문이 들어 있으므로 로컬 검수용으로 보관한다.

`candidate_inventory.csv`는 분석 성공 76,105행 전체의 후보 스키마이며 약 124MB다. 작은 검수 CSV부터 열 것을 권한다. 질문 ID는 정규화 질문 SHA-256 앞 16자리이며 동일 질문을 묶기 위한 키다. 화자 ID가 아니다. 원본 출처는 split+id와 q_audio/a_audio로 추적한다. CSV 수식 실행 방지를 위해 =,+,-,@로 시작하는 문자열에는 작은따옴표를 붙였다(예: 연령 코드 -34). 원본 전사는 원본 JSON에 보존돼 있다.

권장 정제 스키마는 `id, question_id, split, question_type(사람 확정), q_text, a_text, question_audio_path, answer_audio_path, evaluation_items(사람 확정), star_applicable(사람 확정), purpose, quality_status, quality_flags, reviewer_id, label_version`이다. 후보 열과 사람 확정 열을 구분하고, 신규 데이터에는 speaker_id와 question_family_id를 추가한다.

## 7. 실제 표본 예시 — 미검수

아래는 생성 문장이 아니라 로컬 데이터에서 추출한 원문 발췌다. 자동 분류가 맞다는 보장은 없고, 발췌를 완전한 답변으로 평가하면 안 된다. 공개 웹 추가 섹션에는 원문을 넣지 않았다.

{chr(10).join(sample_text)}
''')
    summary_html=''.join(f'<tr><td>{html.escape(r.rule_type)}</td><td>{r.count:,}</td><td>{r.share_all:.2%}</td><td>{r.audio_pairs:,}</td></tr>' for r in counts.itertuples())
    section=f'''\n    <section id="verification-20261029">
      <div class="sec-tag">10 · VERIFIED 2026-10-29</div>
      <h2>재현 검증과 다음 데이터 수집</h2>
      <p>기존 코드의 네 분석 단계를 별도 폴더에서 재실행했습니다. 원본 JSON <b>76,106건</b> 중 엄격 파싱 76,100건, 관대한 파싱 5건, 실패 1건이며 실제 분석 대상은 <b>76,105건</b>입니다. 보유 음성은 <b>1,198쌍·27.253752시간</b>입니다.</p>
      <div class="caution"><b>발표 시 구분</b> · AUC는 실제 이탈 감지 성능이 아닌 질문 짝 구분 실험입니다. STAR 9.0%는 선별 9,464건의 규칙 검출률입니다. STAR 초 수는 실제 음성 정렬이 아닌 추정 위치입니다. 자동 품질 통과는 사람 승인과 다릅니다.</div>
      <figure class="chart"><figcaption>확보 데이터와 자동 점검 결과</figcaption><img src="../verification_20261029/fig_verified_overview.png" alt="원본 76106건, 분석 76105건, 자동 통과 후보 75983건, 음성 연결 1198쌍 및 질문 유형별 규모" style="display:block;width:100%;height:auto"></figure>
      <div class="tbl"><table><tr><th>규칙 유형 (중복 허용)</th><th>텍스트</th><th>비율</th><th>음성 쌍</th></tr>{summary_html}</table></div>
      <p>자동 품질 통과 후보 <b>75,983건</b>, 품질 검수 필요 <b>122건</b>, 원본 파싱 제외 <b>1건</b>입니다. 수동 검수용 CSV는 275행(음성 연결 60행)이며 아직 사람이 확정한 정답은 없습니다. 분할 간 동일 정규화 질문 87개 그룹(372행)이 있어 질문군 단위 분리가 필요합니다.</p>
      <div class="apply"><div class="t">11월 6일 발표 준비</div><ul><li>기존 수치 재현 및 해석 범위 명시</li><li>유형·전사·QA 연결을 두 사람이 검수</li><li>권장 20명 × 4유형 = 80개 녹음: 개발 32 / 검증 16 / 테스트 32. 화자와 질문군 모두 분리</li></ul></div>
      <p><a href="verification.html">검증 보고서·수집 계획·기능별 평가 지표 보기</a> · <a href="../verification_20261029/README.md">실행 방법 및 파일 안내</a> · <a href="../verification_20261029/CHANGELOG.md">변경 내역</a></p>
      <p class="small">신규 녹음·STT API·실시간 정책 성능 실험은 미실행입니다. 기존 규칙 변경 전 수치와 팀 기획서 원본은 확인하지 못했습니다. 원문 검수 CSV는 로컬 팀 검수용입니다.</p>
    </section>\n'''
    original=(BASE/'backup/report/index.html').read_text(encoding='utf-8')
    updated=original.replace('라벨 <b>76,106건 전체</b>(Training 68,077 + Validation 8,028)','로컬 원본 라벨 <b>76,106건</b>(Training 68,078 + Validation 8,028; 파싱 후 76,105건)')
    updated=updated.replace('wav 길이와 라벨 duration 2,396개 모두 일치','wav 길이와 라벨 duration 2,396개 모두 차이 0.001초 이하')
    updated=updated.replace('답변 중앙값 82초, 99.3%가 30초 초과','전체 라벨 답변 중앙값 82.41초(보유 음성 표본 77.52초), 99.3%가 30초 초과')
    updated=updated.replace('<li><a href="#summary">핵심 결론</a></li>','<li><a href="#summary">핵심 결론</a></li>\n      <li><a href="#verification-20261029">재현 검증·수집 계획</a></li>')
    updated=updated.replace('  </main>',section+'  </main>')
    (ROOT/'report/index.html').write_text(updated,encoding='utf-8')
    oldmd=(BASE/'backup/데이터분석_보고서.md').read_text(encoding='utf-8')
    newmd=oldmd.replace('라벨 **76,106건 전체**(Training 68,077 + Validation 8,028)','로컬 원본 라벨 **76,106건**(Training 68,078 + Validation 8,028; 파싱 후 76,105건)')
    newmd=newmd.replace('wav 실제 길이와 라벨 duration이 2,396개 모두 일치','wav 실제 길이와 라벨 duration이 2,396개 모두 차이 0.001초 이하')
    newmd+='\n\n---\n\n## 2026-10-29 재현 검증 보충\n\n네 기존 분석을 별도 폴더에서 재실행했다. 원본·기존 outputs는 보존했다. 검증 결과와 해석상 한계는 [재현 검증 보고서](verification_20261029/재현_검증보고서.md), 신규 선별은 [데이터 활용 가능성](verification_20261029/데이터_활용가능성.md), 다음 실험은 [수집·평가 계획](verification_20261029/수집_라벨링_평가계획.md)을 참조한다. 기존 본문의 수치만으로 실제 이탈 감지 성능·STAR 정답률·온라인 알림 지연을 주장하지 않는다.\n'
    (ROOT/'데이터분석_보고서.md').write_text(newmd,encoding='utf-8')
    write('CHANGELOG.md','''# 변경 내역 — 2026-10-29

## 기존 파일 수정

- report/index.html: 기존 CSS·분석 본문·JavaScript 그래프를 유지하고 목차 링크 및 재현 검증 섹션을 추가했다. 추가 상세 페이지 report/verification.html은 기존 CSS를 재사용한다.
- report/index.html, 데이터분석_보고서.md: 원본 Training 68,078건과 파싱 후 Training 68,077건을 구분하도록 기존 합계 표현을 수정했다. 로컬 보유량을 전체 구축량과 구분했다.
- report/index.html, 데이터분석_보고서.md: WAV 길이 ‘모두 일치’를 ‘차이 0.001초 이하’로 정밀화했다.
- report/index.html: 82초는 전체 라벨 메타데이터 기준임을 명시하고 보유 음성 답변 중앙값 77.52초를 함께 표시했다.
- 데이터분석_보고서.md: 별도 검증 문서 링크와 해석 범위 보충을 추가했다.

## 보존·신규 생성

- src/, outputs/, data/: 수정·삭제하지 않았다. 재실행 결과는 verification_20261029/reproduced/에 저장했다.
- backup/: 기존 src·outputs·report·보고서 사본. backup_manifest.csv는 기존 코드·산출물·웹사이트 해시다. 대용량 원본 데이터는 복제하지 않았다.
- verification_20261029/: 재현 래퍼·감사 코드·로그·환경·비교 JSON·보고서·검수 CSV·수집/라벨링 양식·시각화·실행 안내를 추가했다.
- packages/: 현재 Python에 부족했던 재현 패키지를 프로젝트 내부 검증 폴더에 설치했다. 기존 Python 설치와 원본 분석 코드는 변경하지 않았다.

## 아직 하지 않은 일

사람 검수, 신규 녹음, STT/LLM API 실행, 화자 식별, 의미 중복 전수 검수, 실제 알림/STAR 정확도 평가는 수행하지 않았다. 수집 계획의 80행은 미수집 할당이며 정답 데이터가 아니다.
''')
    # Expose counts and plans, but never raw interview answers on the new HTML page.
    write('web_content.md',(BASE/'재현_검증보고서.md').read_text(encoding='utf-8')+'\n\n'+type_table+'\n\n'+(BASE/'수집_라벨링_평가계획.md').read_text(encoding='utf-8'))
    print('Reports, website section, and change log written')

if __name__=='__main__': main()
