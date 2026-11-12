"""원천데이터(VS_ wav)의 음향 특성 분석.

사용법: python src/audio_features.py
출력: outputs/audio_features.csv, outputs/audio_summary.txt, outputs/fig_audio_*.png
(label_stats.py를 먼저 돌려 outputs/labels.csv가 있으면 라벨 메타데이터와도 대조한다)
"""
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, OUT, setup_matplotlib

FRAME, HOP = 400, 160  # 16kHz 기준 25ms 창, 10ms 간격


def frame_db(x):
    n = 1 + max(0, (len(x) - FRAME) // HOP)
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[np.minimum(idx, len(x) - 1)]
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def estimate_f0(x, sr, db, thresh, max_frames=300):
    """에너지가 큰 유성음 구간에서 자기상관으로 기본주파수(F0)를 추정. 60~400Hz.

    반환: (F0 중앙값 Hz, F0 변동폭 = 반음(semitone) 단위 표준편차). 변동폭이 작을수록 억양이 단조롭다.
    """
    win = int(0.04 * sr)
    lo, hi = sr // 400, sr // 60
    loud = np.where(db > thresh + 10)[0]
    if len(loud) == 0:
        return np.nan, np.nan
    pick = loud[np.linspace(0, len(loud) - 1, min(max_frames, len(loud))).astype(int)]
    f0s = []
    for i in pick:
        seg = x[i * HOP:i * HOP + win]
        if len(seg) < win:
            continue
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[win - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        lag = lo + np.argmax(ac[lo:hi])
        if ac[lag] > 0.5:
            f0s.append(sr / lag)
    if len(f0s) < 10:
        return np.nan, np.nan
    f0s = np.array(f0s)
    med = np.median(f0s)
    semitones = 12 * np.log2(f0s / med)
    semitones = semitones[np.abs(semitones) < 12]  # 옥타브 오검출 제거
    return float(med), float(np.std(semitones))


def analyze(path):
    info = sf.info(path)
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    x = x[:, 0]
    name = Path(path).stem  # 예: ckmk_a_bm_f_e_15778
    parts = name.split("_")
    row = {
        "file": name,
        "subset": Path(path).parent.name,
        "kind": {"q": "question", "a": "answer"}.get(parts[1], parts[1]),
        "gender": {"f": "FEMALE", "m": "MALE"}.get(parts[3], parts[3]),
        "experience": {"e": "EXPERIENCED", "n": "NEW"}.get(parts[4], parts[4]),
        "sr": sr,
        "channels": info.channels,
        "subtype": info.subtype,
        "dur_s": len(x) / sr,
    }
    if len(x) < FRAME:
        return row | {"too_short": True}

    peak = np.max(np.abs(x))
    db = frame_db(x)
    p10, p90 = np.percentile(db, [10, 90])
    thresh = max(p90 - 30, p10 + 6)  # 이보다 작으면 무음으로 본다
    voiced = db > thresh
    v_idx = np.where(voiced)[0]
    lead = v_idx[0] * HOP / sr if len(v_idx) else row["dur_s"]
    trail = (len(db) - 1 - v_idx[-1]) * HOP / sr if len(v_idx) else row["dur_s"]

    # 발화 중간의 쉼(무음 연속 구간) 길이
    pauses = []
    if len(v_idx):
        inner = ~voiced[v_idx[0]:v_idx[-1] + 1]
        run = 0
        for s in inner:
            if s:
                run += 1
            elif run:
                pauses.append(run * HOP / sr)
                run = 0
    pauses = np.array(pauses)

    # 평균 파워 스펙트럼 → 유효 대역폭(99% 에너지 롤오프), 저역(<100Hz) 잡음 비율
    seg = x[: sr * 60]
    nfft = 1024
    n = len(seg) // nfft
    spec = np.mean(np.abs(np.fft.rfft(seg[: n * nfft].reshape(n, nfft) * np.hanning(nfft), axis=1)) ** 2, axis=0)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    spec_db = 10 * np.log10(spec + 1e-20)
    above = np.where(spec_db > spec_db.max() - 50)[0]

    f0_hz, f0_std_st = estimate_f0(x, sr, db, thresh)
    speech_s = (v_idx[-1] - v_idx[0] + 1) * HOP / sr if len(v_idx) else 0.0  # 앞뒤 무음 뺀 발화 구간

    return row | {
        "peak_dbfs": 20 * np.log10(peak + 1e-12),
        "rms_dbfs": 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12),
        "active_level_db": float(np.mean(db[voiced])) if voiced.any() else np.nan,
        "clip_ratio": float(np.mean(np.abs(x) >= 0.999)),
        "digital_zero_ratio": float(np.mean(x == 0)),
        "dc_offset": float(np.mean(x)),
        "noise_floor_db": p10,
        "snr_est_db": p90 - p10,
        "lead_sil_s": lead,
        "trail_sil_s": trail,
        "silence_ratio": float(1 - voiced.mean()),
        "n_pause_gt1s": int(np.sum(pauses > 1.0)),
        "max_pause_s": float(pauses.max()) if len(pauses) else 0.0,
        "bandwidth_hz": float(freqs[above[-1]]),  # 최대 대비 -50dB 이상 에너지가 남아 있는 최고 주파수
        "lowfreq_ratio": float(spec[freqs < 100].sum() / spec.sum()),
        "f0_hz": f0_hz,
        "f0_std_st": f0_std_st,
        "level_std_db": float(np.std(db[voiced])) if voiced.any() else np.nan,  # 말소리 크기 변화
        "speech_s": speech_s,
        "voiced_s": float(voiced.sum() * HOP / sr),
        "pauses_per_min": float(np.sum(pauses > 0.5) / max(speech_s, 1e-6) * 60),
        "mean_pause_s": float(pauses[pauses > 0.5].mean()) if np.any(pauses > 0.5) else 0.0,
    }


def main():
    wavs = sorted(str(p) for p in DATA.glob("*/01.원천데이터/*/*.wav"))
    print(f"wav {len(wavs)}개 분석 중...")
    with Pool() as pool:
        rows = []
        for i, r in enumerate(pool.imap_unordered(analyze, wavs, chunksize=8), 1):
            rows.append(r)
            if i % 200 == 0:
                print(f"  {i}/{len(wavs)}", flush=True)
    df = pd.DataFrame(rows).sort_values("file")

    # 라벨의 duration과 실제 wav 길이 대조
    labels_csv = OUT / "labels.csv"
    if labels_csv.exists():
        lab = pd.read_csv(labels_csv, usecols=["id", "q_audio", "a_audio", "q_dur_s", "a_dur_s", "occupation"])
        meta = pd.concat([
            lab.assign(file=lab.q_audio.str.split("/").str[-1].str[:-4], label_dur_s=lab.q_dur_s),
            lab.assign(file=lab.a_audio.str.split("/").str[-1].str[:-4], label_dur_s=lab.a_dur_s),
        ])[["file", "label_dur_s", "occupation"]]
        df = df.merge(meta, on="file", how="left")
        df["dur_diff_s"] = df.dur_s - df.label_dur_s
    df.to_csv(OUT / "audio_features.csv", index=False, encoding="utf-8-sig")

    lines = []
    p = lines.append
    p(f"분석한 wav: {len(df):,}개, 총 {df.dur_s.sum() / 3600:.1f}시간")
    p(f"포맷: sr {df.sr.value_counts().to_dict()}, 채널 {df.channels.value_counts().to_dict()}, {df.subtype.value_counts().to_dict()}")
    p(f"하위셋별 파일 수: {df.subset.value_counts().to_dict()}")
    p("")
    p("[질문/답변별 중앙값]")
    cols = ["dur_s", "rms_dbfs", "active_level_db", "snr_est_db", "lead_sil_s", "trail_sil_s", "silence_ratio", "max_pause_s", "bandwidth_hz"]
    p(df.groupby("kind")[cols].median().round(2).T.to_string())
    p("")
    p("[답변: 성별 x 경력 중앙값]")
    ans = df[df.kind == "answer"]
    p(ans.groupby(["gender", "experience"])[["f0_hz", "rms_dbfs", "snr_est_db", "silence_ratio", "n_pause_gt1s"]].median().round(2).to_string())
    p("")
    p("[주의가 필요한 파일]")
    p(f"- 클리핑(샘플 0.1% 이상이 최대값): {(df.clip_ratio > 0.001).sum()}개")
    p(f"- 음량 매우 작음(RMS < -40 dBFS): {(df.rms_dbfs < -40).sum()}개, 큼(> -12 dBFS): {(df.rms_dbfs > -12).sum()}개")
    p(f"- RMS 음량 범위: {df.rms_dbfs.min():.1f} ~ {df.rms_dbfs.max():.1f} dBFS (편차 {df.rms_dbfs.max() - df.rms_dbfs.min():.1f}dB)")
    p(f"- 추정 SNR 20dB 미만(잡음 많음): {(df.snr_est_db < 20).sum()}개")
    p(f"- 앞 무음 > 2초: {(df.lead_sil_s > 2).sum()}개, 뒤 무음 > 2초: {(df.trail_sil_s > 2).sum()}개")
    p(f"- 3초 이상 쉼이 있는 답변: {(ans.max_pause_s > 3).sum()}개 / {len(ans)}")
    p(f"- DC offset |평균| > 0.01: {(df.dc_offset.abs() > 0.01).sum()}개")
    p(f"- 유효 대역폭 분포: {df.bandwidth_hz.describe()[['min', '50%', 'max']].round(0).to_dict()} (Nyquist 8000Hz)")
    p(f"- 유효 대역폭 4kHz 미만(전화 음질/업샘플링 의심): {(df.bandwidth_hz < 4000).sum()}개")
    p(f"- 피크가 0dBFS(-0.1dB 이상) = 피크 정규화 의심: {(df.peak_dbfs > -0.1).sum()}개 ({(df.peak_dbfs > -0.1).mean():.0%})")
    p(f"- 디지털 무음(값이 정확히 0) 비율 5% 이상: 질문 {((df.kind == 'question') & (df.digital_zero_ratio > 0.05)).sum()}개, 답변 {((df.kind == 'answer') & (df.digital_zero_ratio > 0.05)).sum()}개")
    p(f"- 저역(<100Hz) 에너지 10% 이상(웅웅거림/험 의심): {(df.lowfreq_ratio > 0.1).sum()}개")
    if "dur_diff_s" in df:
        m = df.dur_diff_s.dropna()
        p(f"- 라벨에 매칭된 wav: {len(m)}/{len(df)} (매칭 안 됨 {df.label_dur_s.isna().sum()}개)")
        p(f"- wav 실제 길이 - 라벨 duration: 중앙값 {m.median():.2f}초, |차이|>1초 {(m.abs() > 1).sum()}개, 최대 {m.abs().max():.2f}초")
    pair = df.assign(pid=df.file.str.replace(r"_[qa]_", "_", regex=True)).groupby("pid").kind.nunique()
    p(f"- 질문/답변 짝이 다 있는 id: {(pair == 2).sum()}개, 한쪽만 있는 id: {(pair == 1).sum()}개")

    report = "\n".join(lines)
    print(report)
    (OUT / "audio_summary.txt").write_text(report, encoding="utf-8")
    plot(df)
    print(f"\n저장: {OUT}")


def plot(df):
    plt = setup_matplotlib()
    ans = df[df.kind == "answer"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    for (g, e), sub in ans.groupby(["gender", "experience"]):
        sub.f0_hz.dropna().plot.kde(ax=axes[0, 0], label=f"{g}/{e}")
    axes[0, 0].set_title("답변 기본주파수 F0 (Hz)")
    axes[0, 0].legend()
    short = df.subset.str.replace("VS_", "").str.replace("ProductionManufacturing", "Prod").str.replace("Management", "Mgmt")
    df.assign(subset=short).boxplot(column="rms_dbfs", by="subset", ax=axes[0, 1], rot=30, fontsize=8)
    axes[0, 1].set_title("하위셋별 RMS 음량 (dBFS)")
    df.snr_est_db.hist(bins=50, ax=axes[0, 2])
    axes[0, 2].set_title("추정 SNR (dB)")
    df.silence_ratio.hist(bins=50, ax=axes[1, 0])
    axes[1, 0].set_title("무음 비율")
    axes[1, 1].hist([df.lead_sil_s.clip(upper=5), df.trail_sil_s.clip(upper=5)], bins=40, label=["앞 무음", "뒤 무음"])
    axes[1, 1].set_title("앞/뒤 무음 길이 (초, 5초 이상 합침)")
    axes[1, 1].legend()
    df.bandwidth_hz.hist(bins=50, ax=axes[1, 2])
    axes[1, 2].set_title("유효 대역폭 (Hz, -50dB 기준)")
    axes[0, 1].set_xlabel("")
    fig.suptitle("")
    fig.tight_layout()
    fig.savefig(OUT / "fig_audio_overview.png", dpi=120)


if __name__ == "__main__":
    main()
