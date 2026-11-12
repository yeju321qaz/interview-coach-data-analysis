# 라벨링 양식 사용법

`recording_plan_80.csv`는 미수집 80건의 할당표입니다. 녹음 완료를 뜻하지 않습니다. 20개 질문군의 의미 중복을 사람이 점검한 뒤 확정하세요.

`recordings.csv`에 실제 파일·동의·분할을 등록하고, `utterances.csv`에 시간 정렬 전사를 작성합니다. `relevance_segments.csv`에는 전체 답변을 관련/무관/불명확으로 끊김 없이 라벨링합니다. `drift_events.csv`에는 무관 구간의 이벤트·복귀·알림 허용창을 기록합니다. `star_labels.csv`에는 각 답변마다 S/T/A/R 4행을 기본으로 기록하고, 여러 근거 구간은 행을 추가합니다. 요소가 없으면 evidence 시간은 비워 둡니다.

모든 파일의 reviewer_id는 독립 평가자 구분용입니다. 원래 두 사람의 라벨을 덮어쓰지 않고 `adjudication.csv`에 합의 결과를 기록합니다. `system_events.csv`는 모델 실행 시 수집할 로그 양식입니다. event_type은 partial_stt/final_stt/segment_final/drift_alert/star_feedback 등으로 구분합니다.

측정 시각·분할·라벨 값과 평가는 상위 폴더의 수집_라벨링_평가계획.md를 따릅니다. 신규 녹음과 정답은 아직 없습니다.
