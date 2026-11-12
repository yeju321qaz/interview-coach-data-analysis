import sys,json,os
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
def main():
    stt=json.loads((BASE/'results/stt_summary.json').read_text(encoding='utf-8'));pair=json.loads((BASE/'results/intent_baseline_summary.json').read_text(encoding='utf-8'));download=json.loads((BASE/'model_download.json').read_text())
    rows='\n'.join(f"| tiny INT8 beam {1 if i==0 else 5} | {r['files']} | {r['provisional_micro_CER']:.2%} | {r['provisional_macro_CER']:.2%} | {r['decode_seconds']:.2f}초 | {r['overall_real_time_factor']:.4f} |" for i,r in enumerate(stt['summary']))
    text=f'''# 중간발표 통합 보고서 — 데이터·실제 실행·수집 계획

기준일: 2026-10-29. 기존 분석/재현 검증/수집 계획은 유지하며 최신 실행 결과를 추가했다. **48개 사람 검수는 보류**, 사람 완료 0개·신규 녹음 0개다. 모델 시험은 API 요금 없는 로컬 CPU에서만 수행했고 음성은 외부로 전송하지 않았다.

## 1. 현재 무엇이 끝났는가

| 영역 | 실제 수행 결과 | 상태·발표 시 해석 |
|---|---|---|
| 기존 분석 | JSON 원본 76,106개 중 분석 76,105개, 음성 1,198쌍·약 27.254시간 | 보유 데이터·분모 확인 완료 |
| 재현성 | 네 분석 재실행, 12개 산출물 중 11개 바이트 동일·1개 행순서 차이만 있음 | 기존 수치의 계산 재현 완료 |
| 품질 선별 | 자동 통과 후보 75,983개·검수 필요 122개 | 사람 품질 승인 아님 |
| 중복·분할 | 분할 간 정규화 동일 질문 87개 그룹 발견 | 실제 학습·평가 전에 질문군 분리 필요 |
| 사람 검수 | 275개·48개 표본과 입력 도구 준비 | 사용자 요청으로 보류, 실제 정답 없음 |
| STT 실행 | 아래 tiny 모델의 12파일 × 2개 디코딩 설정 실제 실행 | 미검수 전사 기준 임시 CER·오프라인 속도 |
| 질문 구분 기준선 | 질문 그룹 분리 후 어휘 모델 학습·테스트 | 원래 질문 쌍 구분 과제, 실제 이탈 성능 아님 |
| 수집·평가 설계 | 80건 시나리오·순서 균형·시간 라벨·분할 검사 코드 | 계획 완료, 녹음·의미 질문군 검수는 미완료 |
| STAR·성장 | 기존 규칙 결과와 평가 계획 보존 | 사람 STAR 정답·반복 연습 전후 데이터 없음 |

## 2. 새로 실제 수행한 무료 STT 시험

공개 다국어 모델 `{download['repo']}`의 고정 revision `{download['revision']}`을 사용했다. 모델 자산 {download['bytes']:,}바이트(약 78.2MB)를 별도 폴더에 내려받았다. 원본 WAV는 수정하지 않았다. CPU 4스레드·INT8·language=ko·temperature=0·VAD off로 두 beam 설정을 번갈아 먼저 실행했다. 1초 합성 무음으로 워밍업했고 모델 로딩·파일 읽기·워밍업은 디코딩 시간에서 제외했다. **모델은 하나이며 beam 1/5는 디코딩 설정 비교다.**

6개 보유 하위셋에서 2개씩 선택한 12개 WAV, 총 약 14.4732분을 같은 순서로 사용했다. CER 정규화는 NFC·소문자·공백/문장부호 제거이며 간투사는 삭제하지 않았다. 각 설정/파일당 1회 실행이다. 원본 전사는 사람이 청취 검수하지 않았으므로 아래 CER는 모두 **임시 참고치**다.

| 같은 tiny 모델 설정 | 파일 수 | 임시 micro CER | 임시 macro CER | 디코딩 합계 | 실시간율 RTF |
|---|---:|---:|---:|---:|---:|
{rows}

micro는 오류 문자 합/정답 문자 합, macro는 파일별 CER 평균이다. RTF는 디코딩 시간/음성 길이이며 작은 값이 빠른 오프라인 처리를 의미한다. 두 값 모두 실시간 서비스의 partial/final 지연시간이 아니다. 이 PC의 단일 실행이라 장비·재실행 변동에 대한 통계적 결론은 내리지 않는다. beam 5는 이번 표본에서 임시 CER가 낮고 시간이 더 들었다. 다른 STT 모델보다 우수하다는 뜻은 아니다.

실행 일부 시간에는 질문 쌍 기준선 분석도 같은 PC에서 진행했으므로 CPU 자원 경합이 처리시간에 영향을 줄 수 있다. 정밀 속도 벤치마크가 필요하면 다른 작업을 중단하고 설정별 반복 측정을 해야 한다.

![로컬 tiny 실제 실행 결과](results/stt_comparison.png)

AI Hub 전사의 독립 어절 ‘어/음’ 후보는 34개였고 두 설정 모두 문자 정렬에서 보존된 후보는 0개였다. 이 결과는 **자동 표기 후보의 정렬 참고치**이며, 실제 간투사 이벤트의 사람 정답 Recall/Precision이 아니다. 간투사 기반 유창성 기능에서는 전사 정규화·모델의 생략 여부를 별도 청취 검증해야 함을 보여 주는 점검 항목으로 사용한다.

시작 시 PyAV 19와 faster-whisper의 `metadata_errors` 인자 호환 문제가 발생했다. 원본을 바꾸거나 실패를 성공으로 처리하지 않고, 확인된 PCM16·16kHz WAV를 Python 표준 wave로 읽어 float32 배열로 전달해 실행했다. 실패 로그와 빈 시작 파일도 남겼다. 성공 결과는 `local_stt_predictions_run1.jsonl` 24행이며 `stt_summary.json`에 환경·실측 수치가 있다.

## 3. STT 후보 비교에서 아는 것과 모르는 것

| 후보 | 실제 확인한 기능 | 이 프로젝트 실제 측정 | 다음 조건 |
|---|---|---|---|
| 로컬 faster-whisper + tiny | CPU INT8 한국어 파일 전사 실행 | 위 12파일·2설정 임시 CER 및 처리시간 | 검수 정답·다른 모델·라이브 청크는 미검증 |
| Google Chirp 3 | 공식 ko-KR 및 스트리밍 지원 | 미실행·CER/간투사/지연 미측정 | 인증·과금·데이터 외부 전송 범위 확인 후 |
| Azure Speech | 공식 ko-KR·연속 스트림 인식 지원 | 미실행·CER/간투사/지연 미측정 | 인증·리전 단가·외부 전송 범위 확인 후 |

지원 기능은 [faster-whisper 공식 저장소](https://github.com/SYSTRAN/faster-whisper), [tiny 공개 파일](https://huggingface.co/Systran/faster-whisper-tiny/tree/main), [Google Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3), [Azure 언어 지원](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt)을 근거로 했다. 비용 확인 범위와 클라우드용 코드는 이전 단계 STT 계획에 보존했다. 이번 실제 유료 API 호출은 0건이며 모델 가중치 취득 후 추론도 오프라인으로 실행했다.

## 4. 질문 이탈 감지 구현 검토와 무료 기준선

현재 구현한 것은 ‘의미 이탈 모델’이 아니라 **TF-IDF 코사인+단어 포함 비율 → 로지스틱 회귀 → 경보 상태기계**의 작은 어휘 기준선이다. 질문 의도를 실제로 유지했는지의 정답은 없다.

- Training 답변 {pair['train_answers']:,}개에서 원래 질문/같은 규칙 유형의 다른 질문 쌍 {pair['train_pairs']:,}개를 만들었다.
- Validation에서 Training 전체와 정규화 질문이 겹치지 않는 고유 질문 800개를 골라 개발 {pair['dev_answers']}개·테스트 {pair['test_answers']}개로 분리했다. 테스트는 {pair['test_pairs']}쌍이고 분할 간 정규화 질문 중복은 0개다. 화자 독립성은 미확인이다.
- 어휘/모델은 Training 부분집합만 보고, 이진 쌍 판정 임계값 {pair['threshold_selected_on_dev']:.2f}는 개발에서 선택했다.
- **질문 쌍 구분** 테스트 AUC: 로지스틱 기준선 **{pair['test_pair_auc']:.4f}**, 코사인 단독 **{pair['test_cosine_auc']:.4f}**. 쌍 판정 F1은 {pair['test_pair_f1']:.4f}다. 추가 분류기가 코사인 단독보다 나아졌다는 근거는 이번 AUC에서 얻지 못했다.

이 과제는 원래 질문의 식별이며 원래 답변의 관련성도 사람이 검수하지 않았다. **실제 이탈 감지 AUC·Recall·오알림·알림 지연으로 발표하면 안 된다.** 기존 전체 코퍼스 TF-IDF AUC 0.969/문장 0.766과는 데이터·분할·부정 쌍이 달라 직접 우열 비교하지 않는다.

경보 코드의 출발값은 final 구간, 5어절 이상, 점수 0.2/0.8, 연속 2구간, cooldown 15초다. 불확실 구간은 알림을 억제한다. 이 값과 whole-answer 학습 점수의 구간 적용은 아직 검증되지 않았다. 실제 tiny 구간으로 오프라인 재생 로그를 만들었지만, 이는 사용자에게 알림을 보내거나 실시간 성능을 측정한 것이 아니다.

## 5. 서비스 구현 흐름과 데이터 연결

| 처리 단계 | 사용할 데이터·구현 | 현재 검증 범위 | 추가로 필요한 것 |
|---|---|---|---|
| 음성 수집 | PCM 프레임+도착 시각 | 보유 WAV 형식·길이 | 신규 마이크 환경·동의·실제 도착 로그 |
| VAD·STT·확정 | 온라인 VAD, partial/final 분리, 중복 제거 | 오프라인 침묵 분석·tiny 파일 전사 | 미래정보 없는 VAD·스트리밍 지연 시험 |
| 질문 핵심+누적 답변 | 요구 항목·최근 문맥·누적 요약 | 질문 유형 규칙·어휘 기준선 | 질문별 루브릭·의미 판단 모델·정답 |
| 이탈 알림 | 불확실 억제·연속 N구간·cooldown | 상태기계·오프라인 재생 | 이탈/복귀/알림 허용창 시간 라벨 |
| STAR·유창성 | 근거 구간·간투사·속도·쉼 | 규칙 통계·음향 특징 | 사람 STAR·간투사 정답 |
| 성장 리포트 | 동일 화자·질문 전후 비교 | 계획 | 자연 답변→피드백→재답변 녹음 |

## 6. 추가 수집 계획과 발표 범위

기존 80건 계획은 유지한다. 정상/지속 이탈/일시 이탈/STAR 누락 각각 20건이며 개발 32·검증 16·테스트 32건이다. 순서 균형·기억 효과 기록·연기/자연 이탈 구분·화자/질문군 분리 검토를 보존했다. 실제 녹음은 0건이고 테스트 유형별 8건은 작은 표본이다. 48개 검수는 보류하며 자동으로 완료 처리하지 않는다.

11월 6일 발표에는 **① 확보·재현 결과 ② 실제 무료 STT 시험과 한계 ③ 독립 질문군 기준선의 평가 과제 ④ 신규 시간 정답의 수집·평가 계획**을 제시할 수 있다. 실제 사용자 이탈 정확도·검수 완료 수·성장 효과·클라우드 성능은 아직 제시할 수 없다.

## 7. 웹사이트와 Claude Artifact

현재 웹사이트는 PC의 독립 HTML이며 원격 Claude Artifact와 자동 동기화하지 않는다. Artifact 원격 링크/원본이 없어 원격 상태는 확인하지 못했고, 원격 Artifact를 수정·게시하지 않았다. 전달용 `report/integrated_standalone.html`에는 그래프와 보고서를 포함해 상대경로 의존을 줄였다. 기존 Artifact 대화에서 이 파일과 본 보고서를 첨부해 해당 Artifact의 수정/새 버전을 요청할 수 있다. 기존 Artifact 종류·권한에 따라 직접 수정 대신 복사본이 될 수 있다. 자세한 절차와 전달 요청문은 `Claude_Artifact_반영안내.md`에 있다.

## 8. 생성·보존

기존 data·src·outputs·1/2단계 문서는 유지했다. 기존 웹사이트는 작업 전 `backup/index.html`에 보관하고 새 통합 현황·실행 결과·구현/Artifact 안내를 추가했다. 새 코드·모델·런타임·결과·로그는 `phase3_integrated_20261029/`에만 두었다. 원문 전사·예측 전문은 로컬 결과 파일에 있고 새 웹 섹션에는 집계만 표시한다. 실행 재현·파일 목록은 `README.md`에 정리한다.
'''
    (BASE/'통합_결과보고서.md').write_text(text,encoding='utf-8')
    (BASE/'web_content.md').write_text(text+'\n\n'+(BASE/'구현_및_평가범위.md').read_text(encoding='utf-8')+'\n\n'+(BASE/'Claude_Artifact_반영안내.md').read_text(encoding='utf-8'),encoding='utf-8')
    # Scientific/statistical chart using actual result files only.
    sys.path.insert(0,str(ROOT/'verification_20261029/packages'));os.environ['MPLCONFIGDIR']=str(BASE/'mplconfig')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10})
    preds=[json.loads(l) for l in (BASE/'results/local_stt_predictions_run1.jsonl').read_text(encoding='utf-8').splitlines()];ids=list(dict.fromkeys(r['id'] for r in preds))
    fig,axes=plt.subplots(1,2,figsize=(13,4.5),gridspec_kw={'width_ratios':[1,1.8]})
    bars=axes[0].bar(['beam 1','beam 5'],[100*r['provisional_micro_CER'] for r in stt['summary']],color=['#2a78d6','#e84b2c'])
    for b,r in zip(bars,stt['summary']):axes[0].text(b.get_x()+b.get_width()/2,b.get_height()+.7,f"{r['provisional_micro_CER']:.2%}",ha='center')
    axes[0].set_ylim(0,30);axes[0].set_ylabel('임시 micro CER (%)');axes[0].set_title('같은 tiny 모델의 디코딩 설정 비교')
    for beam,color in [(1,'#2a78d6'),(5,'#e84b2c')]:
        lookup={r['id']:100*r['provisional_CER']['CER'] for r in preds if r['beam_size']==beam};axes[1].plot(range(1,13),[lookup[i] for i in ids],'-o',label=f'beam {beam}',color=color)
    axes[1].set_xlabel('WAV 표본 번호');axes[1].set_ylabel('임시 파일별 CER (%)');axes[1].set_xticks(range(1,13));axes[1].set_title('같은 12파일에서의 편차');axes[1].legend()
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.text(.02,.025,'AI Hub 미검수 전사 기준 · 12개 편의표본 · 오프라인 CPU INT8 · 서로 다른 STT 모델의 우열/실시간 지연 아님',fontsize=10)
    fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(BASE/'results/stt_comparison.png',dpi=160);fig.savefig(BASE/'results/stt_comparison.svg')
    print('Actual-results report and chart created')
if __name__=='__main__':main()
