import csv, json
from pathlib import Path
BASE=Path(__file__).resolve().parent
OUT=BASE/'collection'
OUT.mkdir(exist_ok=True)

def csvfile(name,fields,rows=()):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

families=[
 ('갈등조정','팀 내 의견 충돌을 해결한 경험과 본인의 행동·결과를 설명해 주세요.'),
 ('일정지연','예상보다 일정이 늦어진 프로젝트를 회복시킨 경험과 결과를 설명해 주세요.'),
 ('실수수습','본인의 실수를 발견하고 수습한 경험에서 책임과 행동·결과를 설명해 주세요.'),
 ('새도구학습','새로운 도구를 배워 실제 문제에 적용한 경험과 결과를 설명해 주세요.'),
 ('자원부족','예산이나 인력이 부족한 상황에서 목표를 달성하려 한 경험을 설명해 주세요.'),
 ('역할변경','예상과 다른 역할을 맡았던 경험과 적응 행동·결과를 설명해 주세요.'),
 ('사용자관찰','사용자의 불편을 관찰하고 해결에 반영한 경험과 결과를 설명해 주세요.'),
 ('품질개선','작업물의 품질을 높이기 위해 본인이 바꾼 방법과 결과를 설명해 주세요.'),
 ('실패학습','기대한 결과를 얻지 못한 도전에서 본인이 한 일과 배운 점을 설명해 주세요.'),
 ('타인설득','반대 의견을 가진 사람을 설득하려 했던 실제 경험과 결과를 설명해 주세요.'),
 ('정보불확실','정보가 불충분한 상태에서 결정을 내린 경험과 판단·결과를 설명해 주세요.'),
 ('협력요청','혼자 해결하기 어려운 일을 도움을 요청해 진행한 경험과 결과를 설명해 주세요.'),
 ('윤리선택','편리한 방법과 원칙 사이에서 선택한 경험과 본인의 행동·결과를 설명해 주세요.'),
 ('우선순위','여러 마감이 겹쳤을 때 우선순위를 정한 경험과 결과를 설명해 주세요.'),
 ('의견수용','불편한 피드백을 받고 본인의 방식을 바꾼 경험과 결과를 설명해 주세요.'),
 ('장기목표','오랫동안 유지한 목표를 향해 본인이 실천한 행동과 결과를 설명해 주세요.'),
 ('발표대응','발표나 설명 중 예상치 못한 질문에 대응한 경험과 결과를 설명해 주세요.'),
 ('업무인계','다른 사람이 이어서 일할 수 있도록 지식을 전달한 경험과 결과를 설명해 주세요.'),
 ('새구성원','처음 만난 구성원이 팀에 적응하도록 도운 경험과 결과를 설명해 주세요.'),
 ('성과측정','수행한 활동의 효과를 직접 확인하거나 측정한 경험과 결과를 설명해 주세요.')]
types=['normal','sustained_drift','temporary_drift','star_missing']
instructions=['질문 요구에 맞는 실제 경험을 자유롭게 설명','중간부터 무관한 주제로 약 15초 이상 말하고 복귀하지 않기','중간에 2~5초 무관한 언급 후 핵심 답변으로 복귀','핵심 주제는 유지하되 본인 행동 또는 결과를 의도적으로 생략']
rows=[]
for i,(name,q) in enumerate(families,1):
    split='development' if i<=8 else 'validation' if i<=12 else 'test'
    # Rotate the four collection conditions; planned rows are not collected data.
    for order in range(4):
        j=(order+i-1)%4
        rows.append(dict(recording_id=f'PLAN_P{i:03d}_{j+1}',speaker_id=f'P{i:03d}',split=split,
            question_family_id=f'F{i:03d}',question_family_name=name,question=q,scenario_target=types[j],
            collection_order=order+1,scenario_instruction=instructions[j],status='未収集'.replace('未収集','미수집'),
            consent_record_id='',actual_scenario='',audio_path='',duration_s='',notes='질문군 의미 중복 검토 후 확정'))
csvfile('recording_plan_80.csv',list(rows[0]),rows)
csvfile('recordings.csv',['recording_id','speaker_id','split','question_id','question_family_id','question_text','question_core_items','scenario_target','actual_scenario','source_audio_path','analysis_audio_path','original_sha256','analysis_sha256','sample_rate','n_samples','duration_s','device','environment','noise_condition','consent_record_id','transcript_version','label_version','status'])
csvfile('utterances.csv',['recording_id','utterance_id','start_s','end_s','start_sample','end_sample','verbatim_text','masked_text','normalized_text','filler_events','reviewer_id','uncertainty','notes'])
csvfile('relevance_segments.csv',['recording_id','segment_id','start_s','end_s','relevance_state','question_core_item','evidence_text','reviewer_id','confidence','uncertainty_start_s','uncertainty_end_s','notes'])
csvfile('drift_events.csv',['recording_id','event_id','drift_start_s','drift_end_s','returned','return_s','alert_required','earliest_alert_s','latest_alert_s','online_prefix_judgment','reviewer_id','evidence','confidence','adjudicated_by','label_version'])
csvfile('star_labels.csv',['recording_id','reviewer_id','question_star_applicable','element','presence','evidence_start_s','evidence_end_s','evidence_text','confidence','notes','adjudicated_by','label_version'])
csvfile('system_events.csv',['recording_id','run_id','model_version','prompt_hash','policy_id','event_type','audio_position_s','audio_frame_arrival_monotonic_ms','request_monotonic_ms','response_monotonic_ms','ui_visible_monotonic_ms','predicted_state','predicted_element','text','notes'])
csvfile('adjudication.csv',['recording_id','label_scope','label_id','reviewer_1_label','reviewer_2_label','final_label','adjudicator_id','reason','label_version'])
schema={
 'recording_id':'string; recordings.csv와 연결되는 고유키',
 'time_intervals':'float seconds; WAV 첫 샘플 기준 [start,end); 미상 null; 0<=start<end<=duration',
 'relevance_state':['on_topic','off_topic','uncertain'],
 'star_presence':['present','absent','uncertain','not_applicable'],
 'element':['S','T','A','R'],
 'alert_required':'true/false/uncertain; STAR 구조 피드백과 이탈 알림을 분리',
 'speaker_id':'가명; 실명 매핑은 별도 비공개 보관',
 'test_access':'최종 평가 전 개발자에게 정답·음성 비공개; 계획표만 공유',
 'status':'미수집/수집완료/독립라벨링/재판정/확정/제외',
 'note':'CSV는 빈 라벨링 양식이며 입력된 정답이나 실험 결과가 아니다. PLAN 행은 수집 할당이다.'}
(OUT/'schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# 라벨링 양식 사용법

`recording_plan_80.csv`는 미수집 80건의 할당표입니다. 녹음 완료를 뜻하지 않습니다. 20개 질문군의 의미 중복을 사람이 점검한 뒤 확정하세요.

`recordings.csv`에 실제 파일·동의·분할을 등록하고, `utterances.csv`에 시간 정렬 전사를 작성합니다. `relevance_segments.csv`에는 전체 답변을 관련/무관/불명확으로 끊김 없이 라벨링합니다. `drift_events.csv`에는 무관 구간의 이벤트·복귀·알림 허용창을 기록합니다. `star_labels.csv`에는 각 답변마다 S/T/A/R 4행을 기본으로 기록하고, 여러 근거 구간은 행을 추가합니다. 요소가 없으면 evidence 시간은 비워 둡니다.

모든 파일의 reviewer_id는 독립 평가자 구분용입니다. 원래 두 사람의 라벨을 덮어쓰지 않고 `adjudication.csv`에 합의 결과를 기록합니다. `system_events.csv`는 모델 실행 시 수집할 로그 양식입니다. event_type은 partial_stt/final_stt/segment_final/drift_alert/star_feedback 등으로 구분합니다.

측정 시각·분할·라벨 값과 평가는 상위 폴더의 수집_라벨링_평가계획.md를 따릅니다. 신규 녹음과 정답은 아직 없습니다.
''',encoding='utf-8')
print('Created collection plan and 7 blank CSV templates')
