"""면접 도우미 관점의 데이터 특성 분석.

- 질문 유형 분포 (질문은행 설계용)
- 답변 내용/구조 특성 (문장, 어미, 구조화 표현, 예시, 수치, 마무리 멘트, 질문 연관성)
- 답변 전달력 특성 (말하기 속도, 간투사, 쉼, 억양 변화) → 사용자 피드백 기준값(백분위)
- 신입 vs 경력 차이

사용법: label_stats.py, audio_features.py 실행 후 python src/coach_features.py
출력: outputs/coach_answers.csv, outputs/coach_norms.csv, outputs/coach_summary.txt, outputs/fig_coach_*.png
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, setup_matplotlib

# 질문 유형: 키워드 규칙 (한 질문이 여러 유형에 속할 수 있음)
QUESTION_TYPES = {
    "자기소개": r"자기소개|자기 소개|본인을? (?:간단히 |짧게 )?소개",
    "지원동기/입사후포부": r"지원 ?동기|지원하(?:게|신|시게)|지원한 이유|입사 ?후|입사하(?:게|면|신다면)|포부|우리 회사|저희 회사",
    "성격/장단점": r"장점|단점|강점|약점|성격|본인의 특징|경쟁력",
    "협업/갈등": r"협업|팀워크|팀 ?웍|팀원|동료|상사|갈등|의견 ?(?:충돌|차이|대립)|커뮤니케이션|소통|조직|단체",
    "경험/성과": r"경험|성과|성공|실패|어려웠|극복|해결했|노력한|도전|대외 ?활동|후회",
    "상황가정/대처": r"(?:한|된|있|없|생긴|주어진|다르|어긋|발생한)다면|어떻게 (?:하|대처|대응|행동)(?:하)?시겠|만약|대처|민원|손님|고객",
    "직무/전문성": r"직무|전공|기술|역량|자격|업무 ?(?:능력|지식)|전문|개념|차이를? 알|문서화|영어로",
    "업무태도/근무조건": r"업무량|출장|야근|근무|지역에서|버틸|이겨낼|자신이 있",
    "업무방식/성향": r"시간 ?관리|역할|편이(?:신|십|세)|스타일|공부|준비했|준비하",
    "시사/사회이슈": r"뉴스|이슈|사회 ?문제|논란|찬반|사건|시장|산업|전망|기업들|선진국|현대인|사회",
    "가치관/윤리": r"가치관|가치|덕목|윤리|원칙|신념|좋은 회사|의미|거짓말",
    "스트레스/자기관리": r"스트레스|자기 ?관리|건강|취미|여가|노년|재미",
}

STRUCTURE = r"첫째|첫 번째|둘째|두 번째|셋째|세 번째|먼저|우선|마지막으로|결론적으로|요약하면|정리하면|정리하자면"
EXAMPLE = r"예를 들(?:어|면|자면)|예컨대|실제로|구체적으로|일례로"
NUMBER = r"\d|퍼센트|프로|개월|년간|배 이상|명의"
CLOSING = r"(?:이상입니다|감사합니다)[.\s]*$"
FILLERS = {"어", "음", "아", "에", "그", "뭐", "좀", "막", "이제", "약간", "저기", "그니까"}
PARTICLES = "은는이가을를에의로도만과와께서요"


def sentences(text):
    return [s.strip() for s in re.split(r"[.?!]", text) if s.strip()]


def q_relevance(q, a):
    """질문의 내용어(2글자 이상, 끝 조사 제거)가 답변에 얼마나 나오는지. 형태소 분석 없는 거친 근사치."""
    words = {w.rstrip(PARTICLES) for w in q.split()}
    words = {w for w in words if len(w) >= 2}
    return sum(w in a for w in words) / len(words) if words else np.nan


def text_features(df):
    a = df.a_text
    sents = a.map(sentences)
    out = pd.DataFrame(index=df.index)
    out["n_sent"] = sents.map(len)
    out["sent_chars"] = sents.map(lambda ss: np.mean([len(s) for s in ss]) if ss else np.nan)
    out["formal_end_ratio"] = sents.map(lambda ss: np.mean([s.endswith(("니다", "니까")) for s in ss]) if ss else np.nan)
    out["yo_end_ratio"] = sents.map(lambda ss: np.mean([s.endswith("요") for s in ss]) if ss else np.nan)
    out["n_structure"] = a.str.count(STRUCTURE)
    out["has_example"] = a.str.contains(EXAMPLE)
    out["has_number"] = a.str.contains(NUMBER)
    out["has_closing"] = a.str.contains(CLOSING)
    out["self_ref_per100"] = a.str.count(r"저는|제가|저의|제 ") / df.a_words * 100
    out["filler_per_min"] = a.map(lambda t: sum(w.strip(".,?!") in FILLERS for w in t.split())) / df.a_dur_s * 60
    out["q_relevance"] = [q_relevance(q, x) for q, x in zip(df.q_text, a)]
    for name, pat in QUESTION_TYPES.items():
        out["qt_" + name] = df.q_text.str.contains(pat)
    return out


def main():
    lab = pd.read_csv(OUT / "labels.csv")
    df = pd.concat([lab, text_features(lab)], axis=1)
    qt_cols = [c for c in df if c.startswith("qt_")]
    df["q_type_n"] = df[qt_cols].sum(axis=1)

    # 음성 특성 붙이기 (원천데이터를 받은 Validation 일부 답변만)
    au = pd.read_csv(OUT / "audio_features.csv")
    au = au[au.kind == "answer"].rename(columns={"file": "a_file"})
    df["a_file"] = df.a_audio.str.split("/").str[-1].str[:-4]
    cols = ["a_file", "speech_s", "voiced_s", "silence_ratio", "pauses_per_min", "mean_pause_s", "max_pause_s", "f0_hz", "f0_std_st", "level_std_db"]
    df = df.merge(au[cols], on="a_file", how="left")
    df["speech_rate_sps"] = df.a_hangul_chars / df.speech_s  # 쉼 포함 말하기 속도 (초당 음절)
    df["artic_rate_sps"] = df.a_hangul_chars / df.voiced_s  # 쉼 제외 조음 속도
    df.to_csv(OUT / "coach_answers.csv", index=False, encoding="utf-8-sig")

    has_audio = df.speech_s.notna()
    lines = []
    p = lines.append
    p(f"분석 대상: 답변 {len(df):,}개 (텍스트 전체), 그중 음성 특성까지 있는 답변 {has_audio.sum():,}개")
    p("")

    p("[1] 질문 유형 (키워드 규칙, 중복 허용)")
    for c in qt_cols:
        p(f"- {c[3:]:<14} {df[c].mean():6.1%}")
    p(f"- 어떤 유형에도 안 걸림   {(df.q_type_n == 0).mean():6.1%}   / 2개 이상 유형   {(df.q_type_n >= 2).mean():.1%}")
    p(f"- 질문 길이: 중앙값 {df.q_words.median():.0f}어절, {df.q_dur_s.median():.1f}초")
    p("")

    p("[2] 답변 내용/구조 (전체 텍스트)")
    p(f"- 문장 수 중앙값 {df.n_sent.median():.0f}개, 문장 평균 길이 중앙값 {df.sent_chars.median():.0f}자")
    p(f"- '~니다/니까'로 끝나는 문장 비율 중앙값 {df.formal_end_ratio.median():.0%}, '~요' {df.yo_end_ratio.median():.0%}")
    p(f"- 구조화 표현(첫째/먼저/마지막으로/결론적으로 등) 1회 이상 사용: {(df.n_structure > 0).mean():.1%}")
    p(f"- 예시 표현(예를 들어/실제로/구체적으로) 사용: {df.has_example.mean():.1%}")
    p(f"- 수치 표현 사용: {df.has_number.mean():.1%}")
    p(f"- '이상입니다/감사합니다'로 마무리: {df.has_closing.mean():.1%}")
    p(f"- 질문 내용어가 답변에 다시 나오는 비율(연관성 근사) 중앙값: {df.q_relevance.median():.0%}")
    p("")

    norm_cols = {
        "a_dur_s": "답변 길이(초)",
        "a_words": "답변 어절 수",
        "a_syll_per_sec": "말하기 속도(전체 시간 기준, 음절/초)",
        "a_filler_ratio": "간투사 비율(어절 대비)",
        "filler_per_min": "간투사 분당 횟수",
        "n_sent": "문장 수",
        "sent_chars": "문장 평균 길이(자)",
        "q_relevance": "질문 연관성(근사)",
        "speech_rate_sps": "말하기 속도(앞뒤 무음 제외, 음절/초)",
        "artic_rate_sps": "조음 속도(쉼 제외, 음절/초)",
        "pauses_per_min": "0.5초 넘는 쉼 분당 횟수",
        "mean_pause_s": "쉼 평균 길이(초)",
        "max_pause_s": "가장 긴 쉼(초)",
        "silence_ratio": "무음 비율",
        "f0_std_st": "억양 변화폭(F0 표준편차, 반음)",
        "level_std_db": "음량 변화폭(dB)",
    }
    pct = [0.1, 0.25, 0.5, 0.75, 0.9]
    norms = df[list(norm_cols)].quantile(pct).T
    norms.columns = [f"p{int(q * 100)}" for q in pct]
    norms.insert(0, "n", df[list(norm_cols)].notna().sum())
    norms.insert(0, "지표", [norm_cols[c] for c in norms.index])
    norms.to_csv(OUT / "coach_norms.csv", encoding="utf-8-sig")
    p("[3] 피드백 기준값 (백분위) — 사용자 답변을 이 분포 위에 놓고 '상위 n%' 피드백 가능")
    p(norms.round(2).to_string())
    p("")

    p("[4] 신입 vs 경력 (중앙값, Mann-Whitney U 검정)")
    p(f"{'지표':<34}{'신입':>8}{'경력':>8}{'p값':>10}")
    for c, label in norm_cols.items():
        a = df.loc[df.experience == "NEW", c].dropna()
        b = df.loc[df.experience == "EXPERIENCED", c].dropna()
        if len(a) > 10 and len(b) > 10:
            pv = mannwhitneyu(a, b).pvalue
            p(f"{label:<34}{a.median():>8.2f}{b.median():>8.2f}{pv:>10.1e}{'  *' if pv < 0.001 else ''}")
    p("  (* p<0.001. 표본이 커서 작은 차이도 유의하게 나오므로 중앙값 차이 크기를 같이 볼 것)")
    p("")

    p("[5] 직군별 답변 특성 (중앙값)")
    occ = df.groupby("occupation").agg(
        n=("id", "size"),
        a_dur_s=("a_dur_s", "median"),
        syll_per_sec=("a_syll_per_sec", "median"),
        tech_intent=("intents", lambda s: s.fillna("").str.contains("technology").mean()),
        q_직무=("qt_직무/전문성", "mean"),
        q_상황가정=("qt_상황가정/대처", "mean"),
    )
    p(occ.round(2).to_string())

    report = "\n".join(lines)
    print(report)
    (OUT / "coach_summary.txt").write_text(report, encoding="utf-8")
    plot(df, qt_cols)
    print(f"\n저장: {OUT}")


def plot(df, qt_cols):
    plt = setup_matplotlib()
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))

    df[qt_cols].mean().rename(lambda c: c[3:]).sort_values().plot.barh(ax=axes[0, 0])
    axes[0, 0].set_title("질문 유형 비율 (중복 허용)")

    items = [
        ("a_syll_per_sec", "말하기 속도 (음절/초)", axes[0, 1]),
        ("filler_per_min", "간투사 분당 횟수", axes[0, 2]),
        ("pauses_per_min", "0.5초 넘는 쉼 분당 횟수 (음성 있는 답변)", axes[1, 0]),
        ("f0_std_st", "억양 변화폭 (반음, 작을수록 단조로움)", axes[1, 1]),
    ]
    for col, title, ax in items:
        s = df[col].dropna()
        s = s.clip(upper=s.quantile(0.995))
        ax.hist(s, bins=50, color="#4C78A8")
        for q, ls in [(0.1, ":"), (0.5, "-"), (0.9, ":")]:
            ax.axvline(s.quantile(q), color="#E45756", ls=ls, label=f"p{int(q * 100)} {s.quantile(q):.2f}")
        ax.set_title(title)
        ax.legend(fontsize=8)

    rates = pd.DataFrame({
        "구조화 표현": df.n_structure > 0,
        "예시 표현": df.has_example,
        "수치 표현": df.has_number,
        "마무리 멘트": df.has_closing,
    }).groupby(df.experience).mean().T
    rates.plot.bar(ax=axes[1, 2], rot=0)
    axes[1, 2].set_title("답변 구성 요소 사용 비율 (신입 vs 경력)")
    axes[1, 2].yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")

    fig.tight_layout()
    fig.savefig(OUT / "fig_coach_overview.png", dpi=120)


if __name__ == "__main__":
    main()
