# 중간발표 준비: 재현 검증·데이터 선별 결과

검증 기준일: 2026-10-29. 기존 네 분석 전체를 실행했다. 기존 분석 코드와 outputs는 보존하고 결과를 이 폴더에 저장했다. 신규 녹음·사람 검수·실제 모델 평가를 수행한 것은 아니다.

## 먼저 볼 파일

| 파일 | 내용 |
|---|---|
| `재현_검증보고서.md` | 환경·주요 수치·산출물 대조·실행시간·한계 |
| `데이터_활용가능성.md` | 유형별 건수·실제 Q&A 표본·STAR 적합 후보·품질·중복 |
| `review/manual_review.csv` | 사람이 검수할 275행, 그중 음성 연결 60행 |
| `review/question_type_counts.csv` | 기존 규칙 12유형의 텍스트/음성/품질 분포 |
| `수집_라벨링_평가계획.md` | 네 시나리오·80/60개 설계·분할·라벨 기준·기능별 지표 |
| `collection/recording_plan_80.csv` | 미수집 80개 할당표, 질문군 의미 중복 검토 후 확정 |
| `collection/README.md` | 7종 빈 입력 양식 사용법 |
| `CHANGELOG.md` | 기존 웹사이트·문서의 정확한 수정 범위 |
| `fig_verified_overview.png`, `.svg` | 발표용 집계 그래프 |
| `../report/index.html` | 기존 디자인에 검증 섹션 추가 |
| `../report/verification.html` | 웹에서 보는 검증 보고서·수집 계획·기능별 평가 지표 |

## 근거 파일

- `reproduced/`: 네 분석의 재생성 결과. 기존 12개 비이미지 파일 중 11개 바이트 동일, segments.csv는 48,335행 정렬 후 값 동일. 기존 5개 PNG도 재생성했다.
- `audit_summary.json`: 원본 파싱·스키마·WAV 헤더·중복·후보 수 등 별도 감사 결과.
- `comparison.json`: 파일별 비교 판정과 수치 허용 오차 대조 결과.
- `environment.json`, `requirements_verified.txt`: 실행 환경과 의존성 버전.
- `timings.jsonl`, `*_features.log`, `label_stats.log`, `proposal_analysis.log`, `audit.log`: 실제 실행 기록. 버퍼링 때문에 실행 중 로그가 바로 갱신되지 않을 수 있다.
- `review/candidate_inventory.csv`: 분석 성공 76,105행 전체의 활용 후보 목록(약 124MB). 정답 확정 파일이 아니다.
- `review/duplicate_questions.csv`, `duplicate_answers.csv`, `duplicate_pairs.csv`: 정규화 기준 중복 목록. pair는 이번 검사에서 0행이다.
- `review/excluded_records.csv`: 파싱 불가 원본 1건. `review/wav_headers.csv`: WAV 2,396개 헤더.
- `backup/`, `backup_manifest.csv`: 기존 파일 사본·SHA-256. 대용량 원본은 복사하지 않았다. data 원본은 모든 작업에서 읽기만 했다.
- `web_check.json`, `index_desktop.png`, `index_mobile.png`, `verification_desktop.png`: 실제 Chrome 자동 표시 점검 결과·화면. JavaScript page error 0개, 기존 SVG 4개, 새 섹션 1개, 추가 이미지 로드 성공, 모바일 전체 가로 넘침 없음.
- `final_checks.json`: 백업 28개 해시·기존 코드/산출물 보존·275행 검수 자료·미수집 80개 계획·기존 CSS/JS 보존을 확인한 최종 점검 결과.

## 재현 방법 — PowerShell

프로젝트 루트에서 실행한다. **기존 src 스크립트를 직접 실행하면 기존 outputs를 덮어쓰므로 아래 래퍼를 사용한다.** 검증 폴더 내 재생성 파일은 갱신된다. 사람이 작성한 manual_review.csv는 먼저 새 이름으로 복사해 보관한다. 수집 양식은 전체 실행에 포함하지 않아 입력한 라벨을 덮어쓰지 않는다.

```powershell
# 이 PC에서 확인한 실행 환경 사용. 원본 데이터 다운로드·압축 해제는 필요 없음.
& .\verification_20261029\run.ps1
```

실행 정책 때문에 ps1이 제한되면 정책을 변경하는 대신 아래 Python 실행 파일로 명령을 직접 실행한다.

```powershell
$verificationPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $verificationPython verification_20261029/reproduce.py environment
& $verificationPython verification_20261029/reproduce.py label_stats
& $verificationPython verification_20261029/reproduce.py audio_features
& $verificationPython verification_20261029/reproduce.py coach_features
& $verificationPython verification_20261029/reproduce.py proposal_analysis
& $verificationPython verification_20261029/audit.py
& $verificationPython verification_20261029/compare.py
& $verificationPython verification_20261029/make_figure.py
& $verificationPython verification_20261029/build_reports.py
node verification_20261029/build_web.mjs
node verification_20261029/check_web.cjs
```

추가 패키지는 이미 `packages/`에 있다. 재설치가 필요한 다른 PC에서는 별도 환경에 requirements_verified.txt를 설치한다(인터넷과 다운로드 필요). 코드의 bundled Python/Node 경로는 PC 환경에 맞게 조정해야 한다. `build_web.mjs`의 marked와 `check_web.cjs`의 Playwright·Chrome 경로도 이 PC에서 확인한 경로다. `reproduce.py`는 현재 사용자 Downloads의 기존 AI Hub ZIP을 우선 읽고, 없으면 풀린 data JSON을 읽는 기존 방식을 따른다. 원본 ZIP과 추출 JSON의 바이트 전수 동일성은 검증하지 않았다.

## 발표에서 말할 수 있는 것

“로컬 원본 라벨 76,106건 중 76,105건을 분석했고 음성은 1,198쌍을 보유한다. 기존 네 분석의 핵심 결과를 재현했다. 자동 품질 통과 후보 75,983건과 검수 필요 122건을 분리했으며, 실제 정답은 별도 사람 검수가 필요하다. 독립적인 이탈·알림·STAR 평가를 위해 화자와 질문군을 분리한 신규 녹음 계획과 라벨 양식을 준비했다.”

현재 AUC를 실제 이탈 정확도로, STAR 9.0%를 좋은 답변 비율로, 자동 통과 후보를 사람 검수 완료 수로 발표하면 안 된다. 원문/음성은 AI Hub 이용 조건을 확인해 로컬 검수용으로 보관하고 공개 웹에는 추가하지 않았다.
