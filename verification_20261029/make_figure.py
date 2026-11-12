from pathlib import Path
import sys,os,json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'packages'))
os.environ['MPLCONFIGDIR']=str(BASE/'mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
a=json.loads((BASE/'audit_summary.json').read_text(encoding='utf-8'))
c=pd.read_csv(BASE/'review/question_type_counts.csv').sort_values('count')
fig,axes=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1,1.4]})
labels=['원본 JSON','파싱·분석 성공','자동 품질 통과 후보','품질 검수 필요','로컬 음성 연결 쌍']
vals=[76106,76105,75983,122,1198]
axes[0].barh(range(5),vals,color=['#8a8e96','#2a78d6','#1baf7a','#e84b2c','#eda100'])
axes[0].set_yticks(range(5),labels);axes[0].invert_yaxis()
axes[0].set_xlim(0,95000)
for i,v in enumerate(vals): axes[0].text(v+1000,i,f'{v:,}',va='center')
axes[0].set_title('보유량과 자동 점검 — 서로 다른 분모',pad=18)
axes[0].set_xlabel('건 / 질문·답변 쌍')
axes[1].barh(c.rule_type,c['count'],color='#2a78d6')
for i,r in enumerate(c.itertuples()):axes[1].text(r.count+350,i,f'{r.count:,}',va='center')
axes[1].set_xlim(0,33000);axes[1].set_title('질문 유형 — 기존 규칙, 중복 허용',pad=18)
axes[1].set_xlabel('텍스트 답변 건수 (전체 76,105건)')
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
fig.suptitle('면접코치 데이터 검증 · 2026-10-29',fontsize=18,y=.98)
fig.text(.03,.025,'자동 통과는 사람 승인 아님 · 미분류 13,815건 · 음성 1,198쌍은 분석 76,105건의 부분집합',fontsize=11,color='#545861')
fig.tight_layout(rect=[0,.07,1,.94])
fig.savefig(BASE/'fig_verified_overview.png',dpi=160)
fig.savefig(BASE/'fig_verified_overview.svg')
