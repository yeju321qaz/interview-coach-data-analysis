# 검수·STT·녹음 계획 보완 결과

기준일: 2026-10-29. 먼저 [RESULTS.md](RESULTS.md)를 보면 확보한 근거와 미실행 항목을 구분할 수 있다. **사람 검수 완료 0건, 신규 녹음 0건, STT 호출 0건**이다.

## 1. 바로 검수 시작하기

1. 프로젝트의 `report/review.html`을 브라우저로 연다. 기존 사이트의 ‘사람 검수·STT 비교 준비’ 섹션에서도 이동할 수 있다.
2. 검수자 ID를 R01처럼 입력하고 이 폴더의 `review/review_subset48.json`을 고른다.
3. 자동 후보를 펼치기 전에 질문 유형·STAR 적합성·관련성을 판단한다. 음성이 있으면 재생해 전사와 비교한다. 근거를 적고 명시적으로 완료 저장한다.
4. ‘전체 48행 결과 CSV 내보내기’로 보관한다. 미검수 행도 함께 저장되므로 전체가 완료됐다고 오해하지 않는다. 입력 변경은 완료 상태를 취소한다.
5. 두 번째 검수자는 별도 ID로 검수한다. 같은 브라우저의 저장소를 공유하지 않으려면 별도 프로필/브라우저를 사용한다. 내보낸 결과를 가져와 복원할 수 있다.

현재 샘플은 총 48개, 음성 연결 45개다. 유형별 배정은 `review/review_assignment.csv`, 전체 목록은 `review/review_subset48.csv`에 있다. CSV와 JSON 모두 실제 질문·답변을 포함한 로컬 검수 자료다. 공개 배포하지 않는다. 검수 HTML에는 원문을 내장하지 않았으며 네트워크 전송 기능도 없다. file URL의 로컬 저장은 브라우저마다 다를 수 있으므로 CSV 내보내기를 주 보관 수단으로 사용한다.

## 2. 결과 비교

프로젝트 루트 PowerShell에서 실행한다. 원본 CSV를 덮어쓰지 않고 새 결과 파일을 지정한다.

```powershell
$verificationPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
# 실제로 내보낸 R01/R02 경로로 바꾼 뒤 실행
& $verificationPython phase2_review_stt_20261029/review/compare_reviews.py --results 'review48_R01.csv' --other 'review48_R02.csv' --output 'review_comparison.json'
```

유형 완전일치와 유형별 Precision/Recall/F1은 해당 검수자의 판단 대비 기존 규칙 결과다. 두 검수자의 공통 완료 행에 대해 범주 일치율·Cohen κ와 불일치 재판정 CSV를 만든다. 합의 완료 전 최종 정확도라고 표현하지 않는다. 품질·STAR·관련성·음성 일치의 판정 기준은 검수자 두 명이 먼저 4~6개의 **개발 표본**으로 맞추고, 해당 표본을 최종 독립 정확도 평가에 포함할지 미리 정한다. 이 48개는 개발용 자료로 간주한다.

`review/current_review_status.json`은 미검수 CSV를 읽어 완료 0건, 일치율 null을 확인한 현재 상태다. `ui_fixture*`는 합성 UI 시험용이며 실제 검수 결과로 사용하지 않는다.

## 3. STT 실험

`STT_비교_실험계획.md`에 공식 문서·후보별 기능·비용 확인 범위·평가 절차·실행 예시를 담았다. `stt/manifest12.csv`는 WAV 12개(약 14.4732분)의 경로·해시·원본 전사와 빈 교정 전사다. `stt/filler_spans.csv`, `hyp_filler_audit.csv`는 빈 간투사 검수 양식이다.

```powershell
# 사전 점검만 실행: 전송·다운로드·모델 실행 없음
& $verificationPython phase2_review_stt_20261029/stt/experiment.py run --provider local
```

모델 실행 명령은 계획서에 따로 있다. Google/Azure는 유료 실행·외부 전송 승인 후 인증이 필요하고, faster-whisper는 별도 런타임과 기존 모델 폴더가 필요하다. `requirements_optional.txt`는 후속 별도 환경용 설치 목록이지 이 단계에서 검증한 고정 환경 명세가 아니다. 기본 실행은 어떤 모델도 내려받지 않는다. 실측 CER·간투사·지연 수치를 채운 결과 파일은 아직 없다.

## 4. 녹음 계획

`collection/recording_plan_80_v2.csv`는 기존 80건을 유지하고 회차 순서·기억 효과·실제 이탈 원인을 기록할 열을 추가한 버전이다. `녹음계획_보완.md`에 운영 방법과 자연 이탈·성장 데이터의 한계를 정리했다. 실제 참여자·의미 질문군 확인 전 ‘데이터 분리 완료’라고 표현하지 않는다.

```powershell
& $verificationPython phase2_review_stt_20261029/collection/validate_split.py
```

현재 결과는 `collection/split_check.json`의 **ID_LEVEL_PASS**다. `semantic_family_map.csv`는 아직 비어 있다. 20개 질문군 전체의 의미 검토와 검수자 2명을 기록한 뒤 `--family-map`으로 검사한다. 불완전한 매핑과 분할 간 연결요소는 통과시키지 않는다. 실제 수집 후 actual_speaker_id/actual_question_family_id를 채워 다시 실행한다.

## 5. 생성·수정 파일

| 구분 | 파일 |
|---|---|
| 기존 수정 | `report/index.html`: 새 섹션·목차 링크만 추가. 기존 CSS·JavaScript 보존 |
| 새 검수 웹 | `report/review.html`, `report/review_app.js` |
| 새 상세 웹 | `report/phase2.html` |
| 보고서 | `RESULTS.md`, `STT_비교_실험계획.md`, `녹음계획_보완.md`, 이 README |
| 검수 자료 | `review/review_subset48.csv`, `.json`, `review_assignment.csv`, `current_review_status.json` |
| 검수 집계 코드 | `review/compare_reviews.py` |
| STT 자료·코드 | `stt/manifest12.csv`, `experiment.py`, `preflight.json`, `requirements_optional.txt`, 빈 간투사 양식 2종 |
| 녹음 계획·검사 | `collection/recording_plan_80_v2.csv`, `validate_split.py`, `split_check.json`, 빈 `semantic_family_map.csv` |
| 보존 | `backup/`의 이전 사이트·상세 페이지·수집 계획·80행 표 사본, `before_hashes.csv` |
| 생성 코드 | `prepare.py`, `build_review.py`, `build_reports.py`, `build_web.mjs` |
| 검증 | `check_work.py`, `checks.json`, `check_ui.cjs`, `ui_check.json`, 화면 PNG 및 합성 UI fixture |

기존 `data/`, `src/`, `outputs/`, `verification_20261029/` 내용은 수정하지 않았다. 이전 단계 보고서/계획/검수 CSV는 새 자료와 함께 그대로 남아 있다. 1단계의 `run.ps1`을 다시 실행하면 1단계 사이트 빌더가 2단계 링크를 지울 수 있으므로, 이후에는 2단계 `build_reports.py`·`build_review.py`·`build_web.mjs`를 마지막에 실행해 복원한다. 사람이 작성한 결과는 생성용 subset CSV와 다른 파일명으로 보관한다.

## 6. 실행해 확인한 것과 미확인 항목

- 표본 48행이 기존 275행의 부분집합이고 중복 ID 없이 미검수 상태인지 검사했다.
- STT WAV 12개의 SHA-256과 PCM16·mono·16kHz 형식, 분량을 확인했다.
- CER의 동일/치환/삭제/삽입/빈 정답 처리와 한글 NFC·정규화 사례를 합성 문자열로 점검했다. 모델의 정확도를 측정한 검사가 아니다.
- 승인 플래그 없는 클라우드 실행 차단, 의미 질문군을 분할 간 강제로 합친 합성 검사에서 누수 차단을 확인했다.
- 브라우저 검증은 합성 입력으로 빈 완료 차단·저장·CSV 다운로드·복원·수정 시 완료 취소를 시험했다. 실제 48개에 완료 라벨을 입력하지 않았다.
- 실제 JSON을 불러와 로컬 WAV 메타데이터 접근과 미검수 0건 완료 상태를 확인했다. 데스크톱·모바일 화면과 기존 SVG 4개를 확인했다.
- 공급사 API, STT 모델 추론, 자연 이탈 발생, 사람 2인 합의, 실제 참여자 분리, 신규 녹음은 아직 검증하지 않았다.

환경 제약으로 샌드박스 Chrome 다운로드는 취소됐으나, 일반 권한의 로컬 Chrome에서 CSV 다운로드·복원까지 검증했다. 모델/원문을 외부로 전송하는 호출은 실행하지 않았다.
