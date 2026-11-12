# 변경 내역 — 2026-10-29

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
