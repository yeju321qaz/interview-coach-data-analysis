# 한국어 STT 후보와 비교 실험

조사 기준: 2026-10-29. 공식 문서에서 지원 기능과 과금 구조를 확인했다. **세 후보의 한국어 CER·간투사 보존율·지연시간은 모두 미측정**이다. 다른 언어·데이터·하드웨어의 WER를 이 프로젝트의 한국어 CER로 바꿔 쓰지 않았다.

## 1. 후보 3개

| 후보 | 한국어·스트리밍 | 환경 | 비용 | CER·간투사·지연 |
|---|---|---|---|---|
| faster-whisper + 다국어 Whisper 모델 | 한국어 `ko`; 기본 transcribe는 파일 단위. 별도 청크/중첩/확정 정책이 있어야 실시간화 | 로컬 CPU INT8 또는 NVIDIA GPU. 모델 파일·런타임 별도 필요 | 로컬 추론 API 과금 없음. 모델 다운로드·장비·전력 비용 별도 | 전부 미측정. 생성기 반환과 진짜 라이브 스트리밍을 혼동하지 않음 |
| Google Cloud Speech-to-Text V2 Chirp 3 | `ko-KR`; StreamingRecognize 지원 | 클라우드 프로젝트·결제·인증·지원 리전 필요. 제공 코드는 `us` 리전 | 공식 표의 기본 Standard 인식 구간은 USD 0.016/분. 실제 SKU·계약·기타 비용 실행 전 확인 | 전부 미측정. 간투사 보존 보장 없음 |
| Azure Speech Standard 실시간 인식 | `ko-KR`; Speech SDK 연속 인식/오디오 스트림 | Azure Speech 리소스·키·리전·SDK 필요. 여기서는 클라우드 경로만 구현 | 초 단위 과금. 조회한 공식 가격 페이지의 숫자가 `$-`로 표시돼 **정확한 유료 단가 확인 불가**. 선택 리전·계정에서 견적 확인 필요 | 전부 미측정. 서비스가 갱신될 수 있어 리소스·SDK·실행일 기록 |

지원 여부는 [faster-whisper 공식 저장소](https://github.com/SYSTRAN/faster-whisper), [Whisper 공식 저장소](https://github.com/openai/whisper), [Google Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3), [Azure 언어 지원](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt), [Azure 오디오 스트림](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-use-audio-input-streams)을 확인했다. 가격 출처는 [Google 가격](https://cloud.google.com/speech-to-text/pricing), [Azure 가격](https://azure.microsoft.com/en-us/pricing/details/speech/)이다. 클라우드 API의 계정별 실제 사용 가능 여부는 인증 호출 전까지 미확인이다.

## 2. 표본과 실행 전 조건

보유 답변 WAV 1,198개가 속한 6개 하위셋에서 길이 정렬의 약 25%·75% 위치를 하나씩 골라 **12개, 약 14.4732분**을 선정했다. `stt/manifest12.csv`에 경로·SHA-256·길이·음량·침묵·규칙 간투사 비율·질문·AI Hub 전사를 담았다. 원본을 복사·수정하지 않았다. 표본은 보유한 직군/성별/경력 조합을 고르게 확인하기 위한 소규모 편의표본이며 전체 한국어·지원자·잡음 환경을 대표하지 않는다. 화자 고유 ID를 몰라 12명이 서로 다른 사람이라고 보장하지 않는다.

원본 전사는 `source_reference`에 보존했고 `reference_corrected`, `reference_reviewer`, `reference_status`는 사람이 청취 후 작성한다. 현재 모두 `unreviewed`다. 청취 검수가 끝나면 status를 `human_verified`로 바꾸고 교정 전사를 입력한다. 원본 전사로 산출한 값은 임시 참고치로만 표시하고, 사람이 검수한 전사 기준 결과와 섞지 않는다.

기본 실행은 **dry run**으로 WAV 형식·해시·분량만 확인한다. API 전송·모델 불러오기·자동 다운로드는 하지 않는다. 현재 faster-whisper 패키지와 Whisper 모델은 로컬에서 발견되지 않았으며, 두 클라우드 SDK도 이 단계에서 설치·인증 시험하지 않았다. 실제 실행에는 다음 확인이 필요하다.

- 로컬: 별도 환경의 faster-whisper와 이미 내려받은 변환 모델 디렉터리. 모델 다운로드가 필요하면 크기·저장 위치를 먼저 확인한다. 코드에 자동 다운로드는 없다.
- Google/Azure: 공급사 키·프로젝트·리전·결제 설정, AI Hub 데이터의 외부 전송 허용 범위와 사용자의 유료 실행 승인. 인증정보는 환경변수로만 읽고 파일·보고서에 저장하지 않는다.
- Google 기본 단가를 단순 적용한 12개 1회 예상치는 약 **USD 0.232**다. 이는 실측 청구액이 아니며 재실행·반올림·계약·부가 서비스·세금 등을 포함한 최종 견적은 아니다. Azure 금액은 단가 확인 전 계산하지 않는다.

## 3. 제공 코드와 비교 조건

`stt/experiment.py`는 실제 호출용 어댑터와 공통 CER 평가기를 제공한다. SDK/모델의 실제 응답은 아직 시험하지 않았으므로 인증 후 1파일 smoke test부터 실행한다. 오류 시 멈추고 자동 재시도로 비용을 늘리지 않도록 했다. 출력 경로가 이미 존재하면 덮어쓰지 않는다.

| 경로 | 실제 실행 방식 | 기록하는 시간 | 해석 |
|---|---|---|---|
| local | WAV 전체, language=ko, beam=5, temperature=0, VAD off | 모델 로딩을 제외한 실제 디코딩 완료시간·실시간율 | 오프라인 기준선. 스트리밍 지연 아님 |
| google | WAV 헤더 제거한 PCM을 100ms씩 실제 시간에 맞춰 전송 | partial/final 수신시각, 공급사 final 구간 끝 대비 지연 | 네트워크·endpoint 확정 지연 포함한 오디오 재생 실험 |
| azure | 동일한 100ms PCM을 PushAudioInputStream으로 전송 | 인식 이벤트 시각·구간 끝·final 지연 | 마이크 수집 자체는 미포함. 실제 라이브 지연의 대리 실험 |

세 경로 모두 외부 질문 원문·정답 전사를 모델 힌트로 주지 않는다. Google/Azure의 내부 정규화·문장부호 정책과 로컬 Whisper의 설정은 동일하게 만들 수 없으므로 설정을 기록하고 결과 차이에 포함해 해석한다. 클라우드 모드의 wall/audio 비율에는 실제 재생 대기가 포함되므로 로컬 처리 속도와 직접 순위를 매기지 않는다. 지연은 구간별 값과 파일별 p50/p90을 보관하고, 음향적 발화 종료를 사람이 찍은 지연과 공급사 종료시각 기준 지연을 구분한다. 음성 끝 offset이 이상하면 음수 지연을 임의로 0으로 보정하지 말고 로그를 검사한다.

## 4. 평가 지표

CER은 양쪽 모두 NFC·영문 소문자화·공백 및 Unicode 문장부호 제거를 대칭 적용하고, 숫자/영문 발음을 임의 치환하지 않는다. 간투사도 삭제하지 않는다. `CER=(치환+삭제+삽입)/정답 문자 수`로 계산하며 micro(오류 합/문자 합)와 macro(파일별 평균)를 모두 제시한다. 빈 정답은 오류로 처리하고, 실패·누락·미검수 정답 파일 수를 숨기지 않는다. 다른 모델이 성공한 파일만 골라 비교하지 말고 동일한 12파일의 실행 상태와 공통 성공 집합을 함께 보고한다.

간투사 Recall은 청취로 확인한 실제 간투사 이벤트의 보존 비율이다. `filler_spans.csv`에 검수된 정답의 **정규화 후 0부터 시작하는 [ref_start,ref_end) 문자 위치**와 원문·검수자를 적는다. `normalize()`로 확인한 문자열에서 위치를 정한다. 평가기는 편집거리 정렬에서 해당 문자열 전체가 연속·동일하게 보존됐는지 센다. 반복하는 ‘어’의 정렬은 여러 최적해가 가능하므로 애매한 사례는 사람 확인이 필요하다. ‘그·좀·이제’는 의미어일 수 있어 규칙 토큰 수만으로 정답을 만들지 않는다.

간투사 Precision은 예측문에도 문맥 판정이 필요해 자동 산출하지 않는다. `hyp_filler_audit.csv`에 예측 간투사의 문맥 판정과 정답 이벤트 연결을 적어 별도 합산한다. 전체 예측 간투사를 빠짐없이 검수하기 전 분모가 불완전하므로 Precision을 공개하지 않는다. 현재 이 두 양식도 빈 상태이며 보존율을 작성하지 않았다.

## 5. 실행 명령

프로젝트 루트 PowerShell에서 `$verificationPython`을 기존 검증에 사용한 Python 경로로 지정한다.

```powershell
$verificationPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
# 안전한 사전 점검: API/모델 실행 없음
& $verificationPython phase2_review_stt_20261029/stt/experiment.py run --provider local
```

다음 명령은 **승인·환경 준비 후에만** 실행하는 예시이며 이번 작업에서는 실행하지 않았다. Google 인증은 SDK의 Application Default Credentials를 준비해야 한다. Azure는 `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, Google은 `GOOGLE_CLOUD_PROJECT` 환경변수가 필요하다.

```powershell
# 로컬 모델이 이미 존재할 때만
& $verificationPython phase2_review_stt_20261029/stt/experiment.py run --provider local --execute --model-dir 'D:/models/whisper-small-ct2' --limit 1 --output phase2_review_stt_20261029/stt/local_smoke.jsonl
# 승인된 유료·외부 전송 실험: 우선 1개만
& $verificationPython phase2_review_stt_20261029/stt/experiment.py run --provider google --execute --allow-paid --data-permission-confirmed --limit 1 --output phase2_review_stt_20261029/stt/google_smoke.jsonl
& $verificationPython phase2_review_stt_20261029/stt/experiment.py run --provider azure --execute --allow-paid --data-permission-confirmed --limit 1 --output phase2_review_stt_20261029/stt/azure_smoke.jsonl
# 청취 정답 완료 후, 각 모델의 결과를 별도 평가
& $verificationPython phase2_review_stt_20261029/stt/experiment.py score --predictions phase2_review_stt_20261029/stt/google_smoke.jsonl --reference-source verified --output phase2_review_stt_20261029/stt/google_scores.json
```

실제 데이터와 테스트용 문자열을 섞지 않는다. 모델 호출 없이 진행한 단위 검증은 CER 구현·실행 게이트·표본 해시 확인의 근거일 뿐, STT 성능 근거가 아니다. 간투사 보존 프롬프트·VAD 옵션·중첩 청크 정책 튜닝은 후속 개발에서 같은 개발 세트로만 비교하고 최종 테스트는 고정한다.
