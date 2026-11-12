"""라벨링 데이터(TL_/VL_ json 전체)의 통계와 품질 점검.

사용법: python src/label_stats.py
다운로드한 라벨 zip(TL_/VL_)을 직접 읽는다. 풀어둔 json 수만 개를 하나씩 여는 것보다 훨씬 빠르다
(Windows 백신 검사 때문에 24분 → 수 초). zip이 없으면 data/ 아래 풀어둔 json을 읽는다.
출력: outputs/labels.csv, outputs/label_summary.txt, outputs/fig_label_*.png
"""
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, DOWNLOAD, OUT, load_json, setup_matplotlib

FILLERS = {"어", "음", "아", "에", "그", "뭐", "좀", "막", "이제", "약간", "저기", "그니까"}
HANGUL = re.compile(r"[가-힣]")


def iter_label_files():
    """(split, id, bytes)를 차례로 내놓는다."""
    zips = sorted(DOWNLOAD.glob("*/02.라벨링데이터/*.zip"))
    if zips:
        for z in zips:
            split = z.parent.parent.name  # Training / Validation
            with zipfile.ZipFile(z) as zf:
                for name in zf.namelist():
                    if name.endswith(".json"):
                        yield split, Path(name).stem, zf.read(name)
    else:
        for path in sorted(DATA.glob("*/02.라벨링데이터/*/*.json")):
            yield path.parts[-4], path.stem, path.read_bytes()


def parse(d, split, file_id, status):
    ds, raw = d["dataSet"], d["rawDataInfo"]
    info, q, a = ds["info"], ds["question"], ds["answer"]
    a_text = a["raw"]["text"]
    a_tokens = [w.strip(".,?!") for w in a_text.split()]
    return {
        "split": split,
        "id": file_id,
        "occupation": info["occupation"],
        "gender": info["gender"],
        "age": info["ageRange"],
        "experience": info["experience"],
        "channel": info["channel"],
        "place": info["place"],
        "q_text": q["raw"]["text"],
        "q_words": q["raw"]["wordCount"],
        "a_text": a_text,
        "a_words": a["raw"]["wordCount"],
        "a_words_counted": len(a_text.split()),
        "a_hangul_chars": len(HANGUL.findall(a_text)),
        "a_filler_ratio": sum(t in FILLERS for t in a_tokens) / max(len(a_tokens), 1),
        "summary_words": a.get("summary", {}).get("wordCount"),
        "n_emotion": len(a["emotion"]),
        "emotions": "|".join(e["category"] for e in a["emotion"]),
        "n_intent": len(a["intent"]),
        "intents": "|".join(e["category"] for e in a["intent"]),
        "intent_text_empty": all(not e.get("text") for e in a["intent"]),
        "q_dur_s": raw["question"]["duration"] / 1000,
        "a_dur_s": raw["answer"]["duration"] / 1000,
        "q_bytes": raw["question"]["fileSize"],
        "a_bytes": raw["answer"]["fileSize"],
        "audio_fmt": f'{raw["answer"]["samplingRate"]}/{raw["answer"]["channelCount"]}ch/{raw["answer"]["samplingBit"]}bit',
        "q_audio": raw["question"]["audioPath"],
        "a_audio": raw["answer"]["audioPath"],
        "json_status": status,
        "text_is_nfc": unicodedata.normalize("NFC", a_text) == a_text,
    }


def main():
    print("라벨 json 읽는 중...")
    rows, broken, n_ctrl = [], [], 0
    for split, file_id, raw in iter_label_files():
        d, status = load_json(raw)
        if d is None:
            broken.append(f"{split}/{file_id}")
            continue
        n_ctrl += status == "ctrl"
        rows.append(parse(d, split, file_id, status))
    df = pd.DataFrame(rows)
    # 파생 지표
    df["a_words_per_sec"] = df["a_words"] / df["a_dur_s"]
    df["a_syll_per_sec"] = df["a_hangul_chars"] / df["a_dur_s"]
    # 16kHz·16bit·mono → 초당 32,000바이트 + 헤더. 메타데이터끼리 일관성 확인용
    df["a_bytes_vs_dur"] = (df["a_bytes"] - 44) / 32000 - df["a_dur_s"]
    df.to_csv(OUT / "labels.csv", index=False, encoding="utf-8-sig")

    lines = []
    p = lines.append
    p(f"총 샘플(질문-답변 쌍): {len(df):,}  (Training {sum(df.split == 'Training'):,} / Validation {sum(df.split == 'Validation'):,})")
    p(f"음성 포맷 종류: {df.audio_fmt.value_counts().to_dict()}")
    p(f"channel/place 값: {df.channel.unique().tolist()} / {df.place.unique().tolist()}")
    p("")
    p("[분포]")
    for col in ["occupation", "gender", "age", "experience"]:
        vc = df[col].value_counts()
        p(f"- {col}: " + ", ".join(f"{k} {v:,} ({v / len(df):.1%})" for k, v in vc.items()))
    p("")
    p("[성별 x 경력 교차표]")
    p(pd.crosstab(df.gender, df.experience, margins=True).to_string())
    p("")
    p("[길이]")
    for col in ["q_dur_s", "a_dur_s", "a_words", "a_words_per_sec", "a_syll_per_sec", "a_filler_ratio"]:
        s = df[col].describe(percentiles=[0.01, 0.5, 0.99])
        p(f"- {col}: mean {s['mean']:.2f}, min {s['min']:.2f}, 1% {s['1%']:.2f}, median {s['50%']:.2f}, 99% {s['99%']:.2f}, max {s['max']:.2f}")
    p(f"- 답변 총 길이: {df.a_dur_s.sum() / 3600:,.1f}시간, 질문 총 길이: {df.q_dur_s.sum() / 3600:,.1f}시간")
    p(f"- 답변 30초 초과: {(df.a_dur_s > 30).mean():.1%}, 60초 초과: {(df.a_dur_s > 60).mean():.1%}  (Whisper 등은 30초 단위 입력)")
    p("")
    p("[그룹별 답변 길이·말하기 속도 중앙값]")
    p(df.groupby(["gender", "experience"])[["a_dur_s", "a_words", "a_syll_per_sec", "a_filler_ratio"]].median().round(2).to_string())
    p("")
    p("[감정/의도 라벨]")
    p(f"- 답변 감정 라벨 없음: {(df.n_emotion == 0).mean():.1%}")
    emo = Counter(e for s in df.emotions for e in s.split("|") if e)
    itt = Counter(e for s in df.intents for e in s.split("|") if e)
    p(f"- 감정 카테고리: {dict(emo.most_common())}")
    p(f"- 의도 카테고리: {dict(itt.most_common())}")
    p(f"- 의도 라벨은 있지만 근거 text가 비어 있는 샘플: {df.intent_text_empty.mean():.1%}")
    p("")
    p("[품질 점검]")
    p(f"- JSON 문법이 깨져 읽을 수 없는 파일(분석에서 제외): {len(broken)}개 {broken}")
    p(f"- 표준 JSON 파서로 안 읽히는 파일(문자열 안 제어문자, strict=False로 읽음): {n_ctrl}개")
    p(f"- NFC 정규화 안 된 텍스트(분해된 한글 자모 포함): {(~df.text_is_nfc).sum()}개")
    p(f"- wordCount와 실제 공백 단어 수 불일치: {(df.a_words != df.a_words_counted).sum()}개")
    p(f"- 빈 답변 텍스트: {(df.a_text.str.strip() == '').sum()}개")
    p(f"- fileSize로 계산한 길이와 duration 차이 > 0.5초: {(df.a_bytes_vs_dur.abs() > 0.5).sum()}개 (중앙값 {df.a_bytes_vs_dur.median():.3f}초)")
    p(f"- 같은 질문 텍스트 반복: 고유 질문 {df.q_text.nunique():,}개 / 전체 {len(df):,}개")
    p(f"- 같은 id 중복: {df.id.duplicated().sum()}개")
    p("- 가장 많이 반복되는 질문 Top 5:")
    for q, c in df.q_text.value_counts().head(5).items():
        p(f"    {c:>5}회  {q[:70]}")

    report = "\n".join(lines)
    print(report)
    (OUT / "label_summary.txt").write_text(report, encoding="utf-8")
    plot(df)
    print(f"\n저장: {OUT}")


def plot(df):
    plt = setup_matplotlib()

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    pd.crosstab(df.occupation, [df.gender, df.experience]).plot.bar(ax=axes[0], stacked=True)
    axes[0].set_title("직군 x 성별 x 경력 샘플 수")
    df.a_dur_s.clip(upper=180).hist(bins=60, ax=axes[1])
    axes[1].set_title("답변 길이(초, 180초 이상은 180에 합침)")
    axes[1].axvline(30, color="r", ls="--", label="30초")
    axes[1].legend()
    for (g, e), sub in df.groupby(["gender", "experience"]):
        sub.a_syll_per_sec.clip(0, 10).plot.kde(ax=axes[2], label=f"{g}/{e}")
    axes[2].set_title("말하기 속도(초당 음절)")
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(OUT / "fig_label_overview.png", dpi=120)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    pd.Series(Counter(e for s in df.emotions for e in s.split("|") if e)).sort_values().plot.barh(ax=axes[0])
    axes[0].set_title("답변 감정 라벨 수")
    pd.Series(Counter(e for s in df.intents for e in s.split("|") if e)).sort_values().plot.barh(ax=axes[1])
    axes[1].set_title("답변 의도 라벨 수")
    fig.tight_layout()
    fig.savefig(OUT / "fig_label_emotion_intent.png", dpi=120)


if __name__ == "__main__":
    main()
