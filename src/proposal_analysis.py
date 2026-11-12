"""기획서(실시간 피드백 → 성장 리포트) 설계 결정을 뒷받침하는 추가 분석.

A. 전사 구간 확정: 침묵 기준(초)별로 답변이 몇 초짜리 구간으로 나뉘는지 (부록 B '전사 구간 확정')
B. STAR 요소: 경험형 질문 답변에서 상황·과제·행동·결과가 나오는 비율과 시점 (Task 3, 알림 타이밍)
C. 질문-답변 연관성: 문자 n-gram TF-IDF 유사도로 '자기 질문'과 '다른 질문'을 얼마나 구분하는지,
   답변이 진행되면서 질문과의 유사도가 어떻게 변하는지 (Task 1, 이탈 감지)
D. 전사문 표기 관례: 숫자·영문·간투사·반복(더듬음) 표기 (부록 B 'STT 비교'의 정답 텍스트로 쓸 때)
E. 합성 평가 세트: 기획서 부록 A의 4가지 유형(정상/지속 이탈/일시 언급 후 복귀/STAR 누락)을
   실제 답변 문장을 섞어 텍스트로 생성 → 녹음 전에 언어 모델 프롬프트·알림 규칙을 미리 시험

사용법: label_stats.py, audio_features.py, coach_features.py 실행 후 python src/proposal_analysis.py
출력: outputs/proposal_summary.txt, outputs/segments.csv, outputs/star.csv,
      outputs/synthetic_eval.jsonl, outputs/target_norms.csv, outputs/fig_proposal_*.png
"""
import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from scipy.stats import mannwhitneyu
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_features import FRAME, HOP, frame_db
from coach_features import sentences
from common import DATA, OUT, setup_matplotlib

RNG = np.random.default_rng(42)
THRESHOLDS = [0.3, 0.5, 0.7, 1.0, 1.5]  # 구간을 끊는 침묵 길이(초)

# STAR 요소: 문장 단위 키워드 규칙(근사치). 한 문장이 여러 요소에 걸릴 수 있다.
STAR = {
    "S": r"당시|그때|때였|시절|프로젝트에서|동아리|아르바이트|알바|인턴|학교에서|회사에서|팀에서|상황|문제가 (?:있|생|발생)|일이 있었|적이 있",
    "T": r"맡(?:았|게|은)|역할|담당|목표|해야 (?:했|하는|할)|과제|책임|임무",
    "A": r"(?:제가|저는|저희는|저도)[^.]{0,100}(?:했습니다|하였습니다|었습니다|였습니다|했고|했는데|했으며|하였고|노력|시도|제안|설득|대화|정리|분석|고안|만들|찾아|가르쳤|기울였)|노력했|노력을 기울|제안했|설득했|해결하기 위해|하기 위해서?",
    "R": r"결과|덕분에|성과|성공적|해결(?:되|됐|할 수 있|이 되)|배웠|깨달|깨닫|느꼈|되었던 것 같|달성|향상|개선(?:되|됐)|인정받|칭찬",
}


# ---------------------------------------------------------------- A. 구간 확정
def segment_stats(path):
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    x = x[:, 0]
    db = frame_db(x)
    p10, p90 = np.percentile(db, [10, 90])
    voiced = db > max(p90 - 30, p10 + 6)
    idx = np.where(voiced)[0]
    if len(idx) == 0:
        return []
    v = voiced[idx[0]:idx[-1] + 1]
    # 발화/무음 연속 구간 (run-length)
    change = np.flatnonzero(np.diff(v.astype(int))) + 1
    bounds = np.concatenate([[0], change, [len(v)]])
    runs = [(bool(v[s]), (e - s) * HOP / sr) for s, e in zip(bounds[:-1], bounds[1:])]
    rows = []
    for t in THRESHOLDS:
        segs, cur = [], 0.0
        for is_voice, dur in runs:
            if not is_voice and dur >= t:
                if cur > 0:
                    segs.append(cur)
                cur = 0.0
            else:
                cur += dur
        if cur > 0:
            segs.append(cur)
        total = sum(segs)
        rows += [{"file": Path(path).stem, "thr": t, "seg_s": s, "answer_speech_s": total} for s in segs]
    return rows


def analyze_segments(p):
    wavs = sorted(str(w) for w in DATA.glob("*/01.원천데이터/*/ckmk_a_*.wav"))
    with Pool() as pool:
        rows = [r for rs in pool.imap_unordered(segment_stats, wavs, chunksize=8) for r in rs]
    seg = pd.DataFrame(rows)
    seg.to_csv(OUT / "segments.csv", index=False, encoding="utf-8-sig")
    g = seg.groupby("thr").seg_s
    per_ans = seg.groupby(["thr", "file"]).size().groupby("thr").median()
    tab = pd.DataFrame({
        "구간 길이 중앙값(초)": g.median(),
        "p90(초)": g.quantile(0.9),
        "10초 초과 비율": g.apply(lambda s: (s > 10).mean()),
        "15초 초과 비율": g.apply(lambda s: (s > 15).mean()),
        "답변당 구간 수(중앙값)": per_ans,
    })
    p("[A] 전사 구간 확정: 침묵 기준별 구간 길이 (음성 있는 답변 %d개)" % seg.file.nunique())
    p(tab.round(2).to_string())
    p("  → 침묵 기준이 길수록 구간이 길어져 판단 지연이 커지고, 짧을수록 문장이 잘린다.")
    p("    '연속 2구간 이탈 시 알림' 규칙이면 최소 지연 ≈ 구간 길이 중앙값 x 2 + 모델 응답 시간.")
    p("")
    return seg, tab


# ---------------------------------------------------------------- B. STAR
def analyze_star(df, p):
    exp_q = (df["qt_경험/성과"] | df["qt_협업/갈등"]) & df.q_text.str.contains(r"했|있었|경험|었던|였던")
    sub = df[exp_q].copy()
    rows = []
    for _, r in sub.iterrows():
        ss = sentences(r.a_text)
        n = len(ss)
        if n < 2:
            continue
        hit = {k: [i for i, s in enumerate(ss) if re.search(pat, s)] for k, pat in STAR.items()}
        row = {"id": r.id, "experience": r.experience, "n_sent": n, "a_dur_s": r.a_dur_s}
        for k, idx in hit.items():
            row[f"has_{k}"] = bool(idx)
            row[f"first_{k}"] = (idx[0] + 0.5) / n if idx else np.nan  # 답변 안에서의 상대 위치 0~1
            row[f"share_{k}"] = len(idx) / n
        rows.append(row)
    st = pd.DataFrame(rows)
    st.to_csv(OUT / "star.csv", index=False, encoding="utf-8-sig")
    p(f"[B] STAR 요소 (경험·협업형 질문 답변 {len(st):,}개, 키워드 규칙 근사)")
    for k, name in zip("STAR", ["상황", "과제/역할", "행동", "결과"]):
        p(f"- {name}({k}) 등장 {st[f'has_{k}'].mean():6.1%}   처음 등장 위치 중앙값 {st[f'first_{k}'].median():.0%} 지점"
          f" (≈ {(st[f'first_{k}'] * st.a_dur_s).median():.0f}초)")
    all4 = st[[f"has_{k}" for k in "STAR"]].all(axis=1)
    p(f"- 네 요소 모두 등장: {all4.mean():.1%}")
    p(f"- 행동(A) 없음: {(~st.has_A).mean():.1%},  결과(R) 없음: {(~st.has_R).mean():.1%}")
    p(f"- 상황 문장이 절반 이상인데 결과가 없음('상황 설명만 길다'): {((st.share_S >= 0.5) & ~st.has_R).mean():.1%}")
    order = st.dropna(subset=["first_S", "first_A", "first_R"])
    p(f"- S→A→R 순서로 처음 등장: {((order.first_S <= order.first_A) & (order.first_A <= order.first_R)).mean():.1%} (세 요소 모두 있는 답변 중)")
    p("  → 실시간 '행동이 아직 확인되지 않았어요' 알림은 답변 중반 이후에만 의미가 있다. 너무 이르면 정상 답변을 방해.")
    p("")
    return st


# ---------------------------------------------------------------- C. 연관성
def auc(pos, neg):
    return mannwhitneyu(pos, neg).statistic / (len(pos) * len(neg))


def analyze_relevance(df, p):
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3), min_df=5, sublinear_tf=True)
    vec.fit(pd.concat([df.q_text, df.a_text]))
    Q = vec.transform(df.q_text)
    A = vec.transform(df.a_text)
    own = np.asarray(Q.multiply(A).sum(axis=1)).ravel()  # 정규화된 벡터라 내적 = 코사인 유사도
    perm = RNG.permutation(len(df))
    rand = np.asarray(Q[perm].multiply(A).sum(axis=1)).ravel()

    # 같은 질문 유형 안의 다른 질문(더 어려운 비교): 주 유형이 같은 다른 샘플
    qt_cols = [c for c in df if c.startswith("qt_")]
    main_type = df[qt_cols].idxmax(axis=1).where(df[qt_cols].any(axis=1), "none")
    same = np.empty(len(df), dtype=int)
    for t, idx in pd.Series(np.arange(len(df))).groupby(main_type.values):
        same[idx.values] = RNG.permutation(idx.values)
    same_sim = np.asarray(Q[same].multiply(A).sum(axis=1)).ravel()

    p("[C] 질문-답변 연관성 (문자 2~3-gram TF-IDF 코사인 유사도)")
    p(f"- 유사도 중앙값: 자기 질문 {np.median(own):.3f} / 무작위 다른 질문 {np.median(rand):.3f} / 같은 유형의 다른 질문 {np.median(same_sim):.3f}")
    p(f"- 답변 전체로 '자기 질문'을 가려내는 AUC: 무작위 질문 대비 {auc(own, rand):.3f}, 같은 유형 질문 대비 {auc(own, same_sim):.3f}")

    # 실시간 상황: 문장 하나(최근 발화)만 보고 판단할 때
    sub = df.sample(5000, random_state=0)
    s_rows = []
    for (_, r), other_q in zip(sub.iterrows(), df.q_text.sample(5000, random_state=1)):
        ss = sentences(r.a_text)
        for i, s in enumerate(ss):
            s_rows.append({"pos": (i + 0.5) / len(ss), "sent": s, "q": r.q_text, "other_q": other_q})
    sd = pd.DataFrame(s_rows)
    S = vec.transform(sd.sent)
    sd["sim_own"] = np.asarray(vec.transform(sd.q).multiply(S).sum(axis=1)).ravel()
    sd["sim_other"] = np.asarray(vec.transform(sd.other_q).multiply(S).sum(axis=1)).ravel()
    p(f"- 문장 하나만 보고 가려내는 AUC (무작위 질문 대비): {auc(sd.sim_own, sd.sim_other):.3f}  ← 실시간 판단이 어려운 이유")
    sd["pos_bin"] = pd.cut(sd.pos, [0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"])
    drift = sd.groupby("pos_bin", observed=True).sim_own.mean()
    p("- 답변 위치별 질문 유사도 평균: " + ", ".join(f"{k} {v:.3f}" for k, v in drift.items()))
    p("  → 답변 첫 부분에서 질문을 되풀이하고 뒤로 갈수록 질문 단어가 줄어든다. 단어 겹침이 줄었다고 이탈은 아니다.")
    p("    표면적 단어 비교만으로는 이탈 판단이 불가능 → 기획서대로 '질문 핵심 항목'과의 의미 비교(언어 모델)가 필요.")
    p("")
    return own, rand, same_sim, sd, drift


# ---------------------------------------------------------------- D. 전사 관례
def analyze_transcripts(df, p):
    a = df.a_text
    p("[D] 전사문 표기 관례 (STT 정답 텍스트로 쓸 때 정규화 기준)")
    p(f"- 아라비아 숫자 포함 답변: {a.str.contains(r'[0-9]').mean():.1%}  (예: '삼 년' 같은 한글 숫자 표기가 기본인지 확인 필요)")
    p(f"- 영문 알파벳 포함 답변: {a.str.contains(r'[A-Za-z]').mean():.2%}  (API, IT 같은 용어도 한글로 적혀 있음)")
    p(f"- 문장부호: 마침표 외 ?·, 거의 없음 → STT 결과의 문장부호는 비교 전에 제거해야 공정")
    rep = a.map(lambda t: re.search(r"(?:^|\s)(\S{1,3}) \1\S", t) is not None)
    p(f"- 단어 앞부분 반복(더듬음 흔적, 예: '많 많아질'): {rep.mean():.1%}")
    toks = a.str.split().explode().str.strip(".,?!")
    fillers = toks[toks.isin(["어", "음", "아", "에", "그", "뭐", "좀", "막", "이제", "약간", "저기"])].value_counts()
    p("- 간투사 표기 빈도: " + ", ".join(f"{k} {v:,}" for k, v in fillers.head(8).items()))
    p("  → 추임새가 전사에 보존돼 있어, STT 후보의 '추임새 보존 정도'를 이 데이터로 비교할 수 있다.")
    p(f"  → 단, 질문 전사에도 면접관 간투사가 남아 있음: 질문 중 '어 ' 포함 {df.q_text.str.contains(r'(?:^| )어 ').mean():.1%}")
    p("")


# ---------------------------------------------------------------- E. 합성 평가 세트
def build_synthetic(df, st, p, n_each=50):
    pool = df[(df["qt_경험/성과"] | df["qt_협업/갈등"]) & (df.n_sent >= 5)]
    others = df[(df["qt_직무/전문성"] | df["qt_시사/사회이슈"]) & ~df["qt_협업/갈등"] & (df.n_sent >= 4)]
    st_idx = st.set_index("id")
    out = []

    def pick_other():
        return sentences(others.a_text.iloc[RNG.integers(len(others))])

    for kind in ["normal", "sustained_drift", "temporary_drift", "star_missing"]:
        made = 0
        for _, r in pool.sample(frac=1, random_state={"normal": 1, "sustained_drift": 2, "temporary_drift": 3, "star_missing": 4}[kind]).iterrows():
            ss = sentences(r.a_text)
            if kind == "normal":
                sents, span = ss, None
            elif kind == "sustained_drift":
                k = max(2, int(len(ss) * 0.4))
                oth = pick_other()
                sents, span = ss[:k] + oth, [k, k + len(oth) - 1]
            elif kind == "temporary_drift":
                k = max(2, int(len(ss) * 0.4))
                oth = pick_other()[:2]
                sents, span = ss[:k] + oth + ss[k:], [k, k + len(oth) - 1]
            else:  # 상황·과제 문장만 남기고 행동·결과 문장 제거
                if r.id not in st_idx.index or not (st_idx.loc[r.id, "has_A"] or st_idx.loc[r.id, "has_R"]):
                    continue
                keep = [s for s in ss if not re.search(STAR["A"], s) and not re.search(STAR["R"], s)]
                if len(keep) < 3:
                    continue
                sents, span = keep, None
            out.append({
                "type": kind,
                "source_id": r.id,
                "question": r.q_text,
                "sentences": sents,
                "drift_sentence_span": span,  # 알림이 필요한 문장 구간(0부터, 양끝 포함). 일시 언급은 '알림 불필요'가 정답
                "expected_alert": kind in ("sustained_drift", "star_missing"),
            })
            made += 1
            if made >= n_each:
                break
    with open(OUT / "synthetic_eval.jsonl", "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    p(f"[E] 합성 평가 세트: {len(out)}개 (유형별 최대 {n_each}개) → outputs/synthetic_eval.jsonl")
    p("  - normal: 원래 답변 그대로 / sustained_drift: 40% 지점부터 직무·시사 질문의 답변으로 바뀜")
    p("  - temporary_drift: 40% 지점에 다른 답변 2문장 삽입 후 원래 답변으로 복귀 / star_missing: 행동·결과 문장 제거")
    p("  - 용도: 녹음 60개를 모으기 전에 언어 모델 프롬프트와 '연속 N구간' 알림 규칙을 텍스트로 먼저 튜닝")
    p("  - 한계: 문장 이어붙임이라 실제 이탈보다 경계가 뚜렷함(쉬운 문제). 최종 평가는 반드시 실제 녹음으로.")
    p("")


# ---------------------------------------------------------------- 기타
def analyze_misc(df, p):
    p("[F] 기타 설계 참고")
    near90 = df.a_dur_s.between(85, 95).mean()
    near120 = df.a_dur_s.between(115, 125).mean()
    p(f"- 답변 길이가 85~95초: {near90:.1%}, 115~125초: {near120:.1%}, 125초 초과: {(df.a_dur_s > 125).mean():.2%}")
    p("  → 녹음 시 90초/120초 상한이 있었던 것으로 보임. 서비스도 '답변 시간 상한'과 남은 시간 표시를 고려할 만함.")
    p(f"- 질문 길이 중앙값 {df.q_dur_s.median():.1f}초 (TTS로 읽어 줄 때 대기시간 기준)")
    p("- 질문은행 후보(유형별 가장 자주 쓰인 질문):")
    qt_cols = [c for c in df if c.startswith("qt_")]
    for c in qt_cols:
        top = df.loc[df[c], "q_text"].value_counts().head(2)
        for q, n in top.items():
            p(f"    [{c[3:]}] ({n}회) {q[:80]}")
    p("")


def target_norms(df, p):
    """기획서 타깃(대학생·취준생)에 가까운 34세 이하 신입만으로 피드백 기준값을 다시 계산."""
    t = df[(df.age == "-34") & (df.experience == "NEW")]
    cols = {
        "a_dur_s": "답변 길이(초)",
        "a_syll_per_sec": "말하기 속도(음절/초)",
        "filler_per_min": "간투사 분당 횟수",
        "sent_chars": "문장 평균 길이(자)",
        "pauses_per_min": "0.5초 넘는 쉼 분당 횟수",
        "max_pause_s": "가장 긴 쉼(초)",
        "f0_std_st": "억양 변화폭(반음)",
    }
    q = t[list(cols)].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).T
    q.columns = ["p10", "p25", "p50", "p75", "p90"]
    q.insert(0, "n", t[list(cols)].notna().sum())
    q.insert(0, "지표", [cols[c] for c in q.index])
    q.to_csv(OUT / "target_norms.csv", encoding="utf-8-sig")
    p(f"[G] 타깃층(34세 이하 신입, {len(t):,}건 = 전체의 {len(t) / len(df):.0%}) 피드백 기준값")
    p(q.round(2).to_string())
    p("- 연령대별 간투사 분당 횟수 중앙값: " + ", ".join(f"{k} {v:.2f}" for k, v in df.groupby("age").filler_per_min.median().items()))
    p("  → 신입/경력 차이처럼 보이던 것의 상당 부분은 연령 차이. 기준값은 타깃층으로 잡는다.")
    p("")


def plot(seg_tab, st, own, rand, same_sim, drift):
    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))

    ax = axes[0]
    ax.plot(seg_tab.index, seg_tab["구간 길이 중앙값(초)"], "o-", label="구간 길이 중앙값")
    ax.plot(seg_tab.index, seg_tab["p90(초)"], "o--", label="구간 길이 p90")
    ax.set_xlabel("구간을 끊는 침묵 길이(초)")
    ax.set_ylabel("초")
    ax.set_title("침묵 기준별 전사 구간 길이")
    ax.legend()

    ax = axes[1]
    names = {"S": "상황", "T": "과제/역할", "A": "행동", "R": "결과"}
    for k in "STAR":
        st[f"first_{k}"].dropna().plot.kde(ax=ax, label=f"{names[k]} ({st[f'has_{k}'].mean():.0%} 등장)", bw_method=0.3)
    ax.set_xlim(0, 1)
    ax.set_xlabel("답변 안에서 처음 등장한 위치 (0=시작, 1=끝)")
    ax.set_title("STAR 요소가 처음 등장하는 위치 (경험형 질문)")
    ax.legend(fontsize=8)

    ax = axes[2]
    bins = np.linspace(0, 0.5, 60)
    ax.hist(own, bins=bins, alpha=0.6, label="자기 질문")
    ax.hist(same_sim, bins=bins, alpha=0.6, label="같은 유형 다른 질문")
    ax.hist(rand, bins=bins, alpha=0.6, label="무작위 다른 질문")
    ax.set_title("답변과 질문의 표면 유사도 (TF-IDF)")
    ax.set_xlabel("코사인 유사도")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_proposal_overview.png", dpi=120)


def main():
    lines = []
    p = lines.append
    df = pd.read_csv(OUT / "coach_answers.csv")
    seg, seg_tab = analyze_segments(p)
    st = analyze_star(df, p)
    own, rand, same_sim, sd, drift = analyze_relevance(df, p)
    analyze_transcripts(df, p)
    build_synthetic(df, st, p)
    analyze_misc(df, p)
    target_norms(df, p)
    report = "\n".join(lines)
    print(report)
    (OUT / "proposal_summary.txt").write_text(report, encoding="utf-8")
    plot(seg_tab, st, own, rand, same_sim, drift)
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
