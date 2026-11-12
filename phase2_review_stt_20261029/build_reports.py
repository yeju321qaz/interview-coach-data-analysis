import json,csv,re
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
def main():
    s=json.loads((BASE/'selection_summary.json').read_text(encoding='utf-8'))
    table='| 선정 층 | 배정 수 |\n|---|---:|\n'+'\n'.join(f'| {k} | {v} |' for k,v in s['assignment'].items())
    summary=f'''# 2단계 작업 결과 — 검수 준비·STT 비교·녹음 계획 보완

기준일 2026-10-29. 기존 분석 수치와 원본·기존 검수 CSV·녹음 계획은 보존했다. 기존 웹사이트에는 별도 섹션만 추가했다. 이번 작업은 사람이 검수하거나 STT 모델을 실행한 작업이 아니다.

## 1. 사람 검수가 필요한 표본

기존 275행에서 **48행**을 선정했다. 12개 규칙 유형 기본 3행씩, 주요 4유형에 2행씩 추가, 미분류 4행이다. 복수 유형 행은 한 선정 층에만 배정했으며 자동 유형 전체는 유지했다. 청취 가능한 표본은 **45행**, 품질 플래그가 있는 표본은 2행이다. 음성 비교를 많이 할 수 있도록 음성 보유 행을 우선했다. 이는 유형별 초기 검수용 표본으로 모집단 오류율을 추정하는 비례 확률 표본이 아니다.

{table}

목록은 `review/review_subset48.csv`, 웹 입력용 원문은 `review/review_subset48.json`에 있다. 현재 사람 검수 완료는 **0/48**이다. 기존 자동 유형·STAR 후보를 정답으로 채우지 않았다.

## 2. 검수 화면

`report/review.html`을 열고 검수자 ID(R01 등)를 입력한 다음 `review/review_subset48.json`을 고른다. 사람은 질문 유형(복수), STAR 적합성, QA 관련성, 전사–음성 일치, 활용 품질, 근거를 입력한다. 원본 WAV가 있으면 화면에서 재생할 수 있고 완료 전에 청취 확인이 필요하다. 자동 결과는 기본 접힌 상태로 제공하며 독립 판정 후 펼쳐 비교한다.

완료 버튼을 명시적으로 누르고 필수 값이 있어야 ‘단일 검수 완료’다. 입력 변경 시 다시 작성 중으로 돌아간다. 입력은 검수자 ID별 브라우저 로컬 저장소에 임시 저장하며 CSV 내보내기·복원이 가능하다. 미작성 행도 미검수로 내보내고 한 사람의 판단을 두 사람 합의 정답으로 표시하지 않는다. R01/R02는 별도 ID·CSV로 검수하고 `review/compare_reviews.py`로 비교한다. 서로 다른 유형·STAR·관련성·전사 판정은 별도 재판정 파일로 보낸다.

CSV/HTML에 원문을 내장해 공개 배포하지 않도록 페이지는 사용자가 선택한 로컬 JSON만 읽는다. 서버로 데이터를 보내는 기능은 없다. 로컬 저장소에는 검수 결과·근거가 남으므로 공유 PC에서는 CSV 확보 후 해당 사이트 저장소를 정리한다. 음성 재생은 프로젝트 내 data 경로가 유지돼야 한다.

## 3. STT 비교와 실행 가능 여부

후보는 **faster-whisper(로컬 다국어 Whisper), Google Chirp 3, Azure Speech Standard**다. 자세한 기능·공식 출처·비용·실험 절차는 `STT_비교_실험계획.md`를 참조한다. **한국어 CER·간투사 보존율·응답 지연은 모두 미측정**이다.

보유 WAV 6개 하위셋에서 2개씩 **12개·{s['stt_minutes']:.4f}분**을 선정했다. 경로·해시·길이·AI Hub 전사와 빈 교정 전사 칸은 `stt/manifest12.csv`에 있다. 현재 정답 전사 12개 모두 청취 검수 전이다.

실행 코드는 기본 dry run으로 형식·해시만 검사한다. 로컬은 기존 모델 폴더만 허용하고 자동 다운로드를 막았다. 클라우드는 유료 실행 및 외부 전송 승인 플래그가 있어야 진행한다. 이번에 API 호출·STT 모델 다운로드·STT SDK 설치는 하지 않았다. SDK 호출 어댑터는 실제 공급사 응답을 아직 검증하지 않았으므로 승인 후 1파일 시험이 필요하다. CER 구현 검증은 합성 문자열 단위 검사이며 모델 성능 실험이 아니다.

## 4. 신규 녹음 계획 수정

`collection/recording_plan_80_v2.csv`는 기존 80행의 화자·질문·목표 유형·분할을 유지하고 순서·기록 항목을 보완한 별도 사본이다. Williams 4가지 순서로 유형별 등장 위치와 직전 유형을 균형화했다. 120초 목표 휴식·이전 답변 열람 금지·4회 종료 전 피드백 금지·실제 연습 횟수 기록을 제안했다. 기억 효과의 제거를 검증한 것은 아니다.

모든 행은 지시가 있는 시나리오로 표시했다. 실제 이벤트가 지시에 의한 것인지 우연히 발생했는지는 사람이 따로 기록한다. 정상 20행에서 자연 이탈을 관찰할 기회는 있으나 자연 이탈 데이터가 이미 생긴 것은 아니다. 성장 리포트의 자연 답변→피드백→재답변은 별도 후속 데이터가 필요하다.

계획 ID 기준 화자·질문군 분리는 통과했다. 그러나 의미 질문군의 두 사람 검수와 실제 화자 확인은 미완료다. 테스트는 32건·유형별 8건으로, 유형별 한 건이 12.5%p를 바꾼다. 개선 상세는 `녹음계획_보완.md`에 있다.

## 5. 확보·미확보 구분과 발표 범위

| 구분 | 현재 상태 | 11월 6일 발표에서 가능한 설명 |
|---|---|---|
| 기존 AI Hub 텍스트 | 분석 성공 76,105건, 자동 품질 통과 후보 75,983건 | 재현 검증된 보유량·자동 기준과 사람 정답의 차이 |
| 실제 보유 음성 | 1,198쌍·약 27.254시간 | 보유 범위·편향·STT 실험 후보 |
| 48개 소규모 검수 | 선정 완료, 사람 완료 0건 | 표본 설계·입력 화면·검수 절차. 정확도는 검수 이후에만 |
| STT 표본 12개 | 경로·형식·해시 확인, 전사 정답 미검수 | 비교 후보·실행 게이트·CER 평가 코드. 실측 성능 없음 |
| 신규 녹음 80개 | 계획만 있음, 실제 0건 | 배분·순서 통제·시간 라벨·분할 방법 |
| 자연 이탈·알림 시간 정답 | 미수집 | 연기 시나리오와 구분한 확보·평가 계획 |
| STAR 정답 | 사람 라벨 미확보 | 규칙 검출률과 정답 정확도 구분 |
| 성장 리포트 반복 연습 | 미수집 | 별도 전후 데이터 필요성 |

사용자 음성 → VAD/STT → 구간·전사·간투사 → 질문 핵심 항목+누적 답변 → 관련성·STAR·유창성 → 실시간 알림/종료 후 리포트의 흐름에서, 기존 WAV는 STT·음향 검증 후보이고 신규 시간 라벨은 이탈·적시 알림 검증에 필요하다. 질문 유형/STAR 적합성/QA 관련성의 텍스트 검수는 이 단계의 48개로 먼저 시작한다. 48개의 답변 단위 관련성 검수만으로 실시간 이탈 구간 정답을 확보한 것으로 간주하지 않는다.

## 6. 변경 파일과 보존

기존 수정 파일은 `report/index.html` 하나이며 새 섹션·목차 링크를 추가했다. 새 웹 파일은 `report/review.html`, `report/review_app.js`, `report/phase2.html`이다. 기존 report/verification.html, 분석 코드, outputs, 원본 data, 이전 275개 검수 CSV와 80행 계획은 보존했다. 변경 전 관련 파일 사본은 이 폴더의 `backup/`, 해시는 `before_hashes.csv`에 있다. 새 파일 전체 목록과 실행 명령은 `README.md`에 정리했다.
'''
    (BASE/'RESULTS.md').write_text(summary,encoding='utf-8')
    original=(BASE/'backup/index.html').read_text(encoding='utf-8')
    section='''
    <section id="phase2"><div class="sec-tag">11 · HUMAN REVIEW &amp; STT</div><h2>사람 검수와 STT 비교 준비</h2>
    <p>기존 275개 중 유형 균형 검수 <b>48개</b>(음성 연결 <b>45개</b>)를 선정했습니다. 사람 검수 완료는 아직 <b>0개</b>입니다. 아래 화면에서 직접 판정하고 결과를 CSV로 저장할 수 있습니다.</p>
    <div class="apply"><div class="t">검수 시작</div><p><a href="review.html">48개 표본 검수 화면 열기</a></p><p>검수자 ID 입력 후 <code>phase2_review_stt_20261029/review/review_subset48.json</code>을 선택하세요. 자동 결과는 접힌 상태이며 완료는 한 사람의 판단으로만 표시합니다.</p></div>
    <p>STT 비교용 WAV는 6개 하위셋에서 12개·약 14.47분을 선정했습니다. 로컬 faster-whisper, Google Chirp 3, Azure Speech를 비교할 코드를 준비했으며, <b>CER·간투사 보존·지연시간은 모두 미측정</b>입니다. 유료 API 호출과 모델 다운로드는 하지 않았습니다.</p>
    <p>신규 녹음은 기존 80건을 유지하며 순서 균형·기억 효과 기록·연기/자연 이탈 구분을 보완했습니다. 화자·질문군은 계획 ID 수준에서 분리했지만 의미 중복·실제 참여자는 추가 검수가 필요합니다.</p>
    <p><a href="phase2.html">2단계 결과·STT 공식 근거·녹음 계획 보완 보기</a> · <a href="../phase2_review_stt_20261029/README.md">파일 안내·실행 명령</a></p>
    <p class="small">원문은 사용자가 고른 로컬 파일에서만 읽습니다. 공개 배포용 원문 데이터는 포함하지 않았습니다. 신규 녹음·실제 모델 성능 측정은 미실행입니다.</p></section>
'''
    out=original.replace('  </main>',section+'  </main>').replace('<li><a href="#summary">핵심 결론</a></li>','<li><a href="#summary">핵심 결론</a></li>\n      <li><a href="#phase2">사람 검수·STT 비교 준비</a></li>')
    (ROOT/'report/index.html').write_text(out,encoding='utf-8')
    (BASE/'web_content.md').write_text(summary+'\n\n'+(BASE/'STT_비교_실험계획.md').read_text(encoding='utf-8')+'\n\n'+(BASE/'녹음계획_보완.md').read_text(encoding='utf-8'),encoding='utf-8')
    print('Phase 2 reports and website section generated')
if __name__=='__main__':main()
