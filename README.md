# interview-coach-data-analysis

AI 면접 코치 서비스 기획(「실시간 피드백에서 성장 리포트까지」)을 구체화하기 위해 AI Hub **채용면접 인터뷰 데이터**를 분석한 프로젝트입니다.

- 전체 분석 보고서: [데이터분석_보고서.md](데이터분석_보고서.md)
- 공개 웹 보고서: [PUBLIC_REPORT_URL.md](PUBLIC_REPORT_URL.md)

## 주요 결과

- 면접 질문·답변 음성 76,105쌍(답변 약 1,698시간) 분석
- 데이터에는 "좋은/나쁜 답변" 정답이 없음 → 이탈 감지 라벨은 직접 만들어야 함
- STAR 네 요소를 모두 말한 답변은 9%, '결과'는 보통 답변 60% 지점 이후에 등장
- 전사 구간 확정 기준: 침묵 0.5~0.7초 + 최대 10~15초 강제 확정 권장

## 폴더 구조

| 경로 | 내용 |
|---|---|
| `src/` | 핵심 분석 코드 (라벨 통계, 음향 특성, 코칭 지표, 기획 검증) |
| `outputs/` | 요약 통계(`*_summary.txt`, `*_norms.csv`)와 그림 |
| `report/` | HTML 보고서 (원문 질문표가 있는 통합본은 제외, `prepare_public_report.py`로 공개본 생성) |
| `verification_20261029/` | 재현·검증 |
| `phase2_review_stt_20261029/` | 검수·STT 비교 |
| `phase3_integrated_20261029/` | 질문 이탈 감지 프로토타입 통합 |
| `alert_timing_20261102/` | 실시간 알림 초기 정책 분석 |
| 그 밖의 날짜 폴더 | 보고서 문구·디자인 수정 기록 |

## 실행 방법

1. [AI Hub 채용면접 인터뷰 데이터](https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71592)를 승인받아 내려받습니다.
2. 다음 구조로 `data/` 아래에 넣습니다.
   ```
   data/
     Training/02.라벨링데이터/TL_*/
     Validation/01.원천데이터/VS_*/
     Validation/02.라벨링데이터/VL_*/
   ```
3. 패키지를 설치하고 실행합니다.
   ```
   pip install -r verification_20261029/requirements_verified.txt
   python src/label_stats.py
   python src/audio_features.py
   python src/coach_features.py
   python src/proposal_analysis.py
   ```

## 데이터 관련 안내

원본 데이터와 원본 전사문이 들어 있는 파생 파일(`labels.csv`, `coach_answers.csv` 등)은 AI Hub 이용정책에 따라 이 레포에 포함하지 않았습니다. 위 실행 방법으로 직접 다시 만들 수 있습니다.
