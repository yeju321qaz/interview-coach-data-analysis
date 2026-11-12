# 실시간 알림 시점: 추가 분석

목적은 최적 알림 시점의 발견이 아니라 초기 설계 후보의 비교다. 실제 이탈 정답과 문장·음성 시간 정렬은 없다.

## 결과

- `초기알림정책_분석보고서.md`: 기획서용 전체 설명·표·발표 문장.
- `../report/alert-timing/index.html`: 기존 보고서에 연결한 새 섹션.
- `01_`~`04_` PNG·SVG: 발표 그래프.
- `simulation_summary.csv`: 72개 가정 조합의 가상 정책 출력.
- `analysis_metadata.json`: 표본, 탐색 임계값, 환경.
- `preservation_check.json`: 기존 결과 불변 및 원본 HTML에 섹션만 추가했는지 검증.

## 재현 (PowerShell, 프로젝트 루트)

```powershell
& 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' alert_timing_20261102/analyze.py
& 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' alert_timing_20261102/build_report.py
& 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' alert_timing_20261102/verify.py
node alert_timing_20261102/check_web.cjs
```

외부 API·음성 전송·신규 모델 학습은 없다. 기존 `verification_20261029/packages`를 사용한다. 원본 데이터 및 `outputs`는 읽기만 한다.

## 주요 CSV 단위

| 파일 | 행 단위 | 시간·정책의 의미 |
| --- | --- | --- |
| audio_segments | 답변×침묵 기준×구간 | start/end/confirm은 WAV 기준 초. confirm=end+침묵 기준. seg_s는 긴 분할 무음을 제외한 길이 |
| consecutive_windows | 답변 내 겹치는 연속 k구간 창 | content_sum_s는 내용 길이 합; span_s는 내부 무음 포함; confirmation_wait_s는 마지막 경계 침묵 포함 |
| window_summary | 침묵 기준×k×시간 정의 | p25/50/75/90은 초. n은 창 수로 답변 수가 아님 |
| sentence_scores_local | 전사 문장 | score는 어휘 유사도, 관련성 확률이 아님; idx는 0부터 시작 |
| low_sentence_runs_local | 연속 저유사도 문장 묶음 | length는 문장 수; returns_higher는 뒤 문장이 기준 이상이라는 뜻 |
| sentence_policy_counts | 대상×점수 경계×문장 수 정책 | 문장 순서만의 가상 출력. 음성 구간 정책과 별개 |
| simulated_events_local | 가상 알림 사건 | wait_s는 가상 후보 묶음 첫 구간 시작부터 경계 확인까지. 실제 이탈 시작으로부터의 지연 아님 |
| simulation_summary | 배치 가정×침묵 기준×하위 분위×정책 | alerts는 가상 출력 횟수; p25/50/75/90은 출력이 있는 사건의 wait_s. value는 segments이면 개수, duration이면 내용 누적 초 |

`duration` 정책은 경계에서만 평가하며 긴 무음을 제외한 후보 구간 길이 합을 사용한다. 전체 경과시간 타이머는 별도 설계안이다. 가상 알림은 한 후보 묶음당 한 번이며 기준 이상 구간이 나오면 초기화한다. cooldown 및 최소 어절 수 조건은 적용하지 않았다. `unconfirmed`는 파일 끝 침묵 부족으로 확인할 수 없는 가상 기회 수다.

`*_local.csv`, 음성, 원문 문장과 개별 ID는 공개하지 않는다. 웹사이트에는 집계 CSV, 그래프와 설명만 복사한다. 보존 백업은 `backup`에 있다.
