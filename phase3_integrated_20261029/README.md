# 중간발표 통합 결과와 재현 안내

기준일: 2026-10-29. 사람 검수 48개는 보류했다. 기존 데이터·분석·검증·수집 계획은 보존하고 무료 로컬 모델 실행과 통합 보고서를 추가했다.

## 먼저 볼 결과

- `../report/index.html`: 기존 분석부터 최신 실행까지 한 웹사이트에서 보는 기본 진입점.
- `../report/integrated_standalone.html`: 그래프와 이전 상세 보고서를 포함한 단일 HTML. 원격 Claude Artifact와 자동 동기화하지 않는다.
- `통합_결과보고서.md`: 실제 수행·임시 참고치·계획·미확보 정답을 구분한 보고서.
- `구현_및_평가범위.md`: STT 후보·질문 핵심 항목·온라인 VAD·경보 정책·데이터 매핑.
- `Claude_Artifact_반영안내.md`: 원격 상태의 확인 한계, 기존 Artifact 반영 순서와 전달 요청문.

## 실제 새로 실행한 것

1. 공개 다국어 `Systran/faster-whisper-tiny` 자산 78,203,619바이트를 이 폴더의 models/tiny에 내려받아 SHA-256을 기록했다. 고정 revision은 model_download.json에 있다. 런타임은 packages에 별도 설치했다.
2. 이전 단계의 동일 WAV 12개에 CPU INT8·4스레드·beam 1/5를 각각 1회 실행했다. 임시 micro CER 21.12%/14.30%, 디코딩 합 81.97초/137.40초다. 미검수 AI Hub 전사 기준이며 실제 라이브 지연·서로 다른 모델 비교가 아니다. 음성 외부 전송 및 유료 API 호출은 없었다.
3. 질문 그룹을 분리한 Training 2,000개·개발 400개·테스트 400개로 TF-IDF+작은 로지스틱 기준선을 실행했다. 테스트 800쌍의 원래 질문 구분 AUC는 0.9147, 코사인 단독은 0.9278이다. 실제 이탈 정답은 없어 이탈 감지 성능으로 해석하지 않는다.
4. final/최소 발화량/연속 구간/cooldown 상태기계를 만들고 tiny 전사 12파일·110구간을 오프라인 재생했다. would_alert는 가상 정책 출력이며 실제 사용자 알림·시간 정답 평가가 아니다.

정밀 속도 벤치마크는 아니다. 실제 실행 일부에 다른 분석도 같은 PC에서 진행돼 시간 경합이 있을 수 있다. 간투사 후보 점검도 사람 정답 Recall로 발표하지 않는다. 자세한 조건과 실패 후 수정 이력은 통합 보고서·로그에 남겼다.

## 근거 파일

| 파일 | 용도 |
|---|---|
| `results/local_stt_predictions_run1.jsonl` | 성공한 실제 전사 24행, 구간·시간·임시 CER·원문 예측. 로컬 전용 |
| `results/stt_summary.json` | 설정별 집계·버전·하드웨어·시간 조건 |
| `results/stt_comparison.png`, `.svg` | 실제 수치만으로 만든 발표 그래프 |
| `results/intent_baseline_summary.json` | 분할·표본·쌍 판정 결과·실제 이탈 미측정 표시 |
| `results/intent_pair_predictions.csv` | 테스트 쌍·점수, 로컬 전용 |
| `results/intent_guard.joblib` | 이번에 학습한 어휘 모델·작은 분류기. 신뢰할 수 없는 외부 joblib은 불러오지 않는다 |
| `results/offline_guard_replay.jsonl` | 실제 tiny 전사를 사용한 오프라인 가상 경보 로그 |
| `model_download.json` | 공개 모델 revision·파일 크기·해시 |
| `local_stt.log`, `intent_baseline.log` | 실제 실행 출력 |
| `local_stt_startup_failure.log`, 빈 `results/local_stt_predictions.jsonl` | PyAV 호환 실패 당시 기록. 성공 결과로 사용하지 않음 |
| `backup/index.html`, `before_hash.csv` | 통합 전 기존 웹사이트 보존 |

## 재현 명령

프로젝트 루트 PowerShell에서 아래 실행 환경을 사용했다. 가중치와 런타임은 이미 이 폴더에 있다. 원본 데이터·기존 outputs를 덮어쓰지 않는다.

```powershell
$verificationPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
# 같은 모델을 다시 시험할 때 새 run 이름으로 결과 보존
& $verificationPython phase3_integrated_20261029/run_local_stt.py --run-name repeat01
# 원래 실행한 기준선은 결과 존재 시 덮어쓰지 않고 중단
& $verificationPython phase3_integrated_20261029/run_intent_baseline.py
# 기존 실제 결과로 오프라인 재생·보고서/웹만 재생성
& $verificationPython phase3_integrated_20261029/replay_guard.py
& $verificationPython phase3_integrated_20261029/build_report.py
node phase3_integrated_20261029/build_web.mjs
```

run_intent_baseline.py의 새 실험을 하려면 기존 결과를 별도 보관한 실험 사본에서 실행한다. 기존 actual run 결과를 지우는 명령은 제공하지 않는다. 보고서는 최초 실제 실행 결과를 가리키며 repeat01 결과로 자동 교체하지 않는다. 새 환경에서 download_tiny.py를 실행하면 인터넷 다운로드가 발생하므로 기존 models가 있으면 다시 실행할 필요 없다. 주요 실행 패키지 버전은 stt_summary.json에 있다.

## 변경·보류

기존 수정 파일은 `report/index.html`이다. 기존 CSS·그래프 JavaScript와 분석/1·2단계 기록은 유지하고 최신 통합 섹션과 역사적 상태 안내를 추가했다. 새 전달 파일은 `report/integrated_standalone.html`이다. 기존 report/verification.html, phase2.html, review.html, 검수 CSV와 수집 계획은 수정하지 않았다.

48개 검수·신규 80건 녹음·사람 STAR/이탈 정답·다른 STT 모델/클라우드 실험·자연 반복 연습 데이터는 아직 없다. 이전 단계 문서의 ‘STT 미실행’은 당시 기록이며 상단 통합 섹션에 최신 실제 실행을 별도 표시했다. 원격 Claude Artifact는 열람·수정·업로드하지 않았다.
