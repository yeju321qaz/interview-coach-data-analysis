"""AI Hub 채용면접 인터뷰 데이터 zip을 data/ 아래로 압축 해제한다.

사용법: python src/extract.py [다운로드 폴더]
- zip 내부 경로가 '/'로 시작하므로 앞의 '/'를 제거하고 푼다.
- 끝까지 푼 폴더에는 .done 파일을 남기고, 다시 실행하면 그 폴더는 건너뛴다.
"""
import shutil
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = Path.home() / "Downloads" / "129.채용면접 인터뷰 데이터" / "01-1.정식개방데이터"
DST = PROJECT / "data"


def extract(zip_path: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    root = out.resolve()
    n = 0
    with zipfile.ZipFile(zip_path) as zf:
        for m in zf.infolist():
            if m.is_dir():
                continue
            rel = m.filename.replace("\\", "/").lstrip("/")
            target = (root / rel).resolve()
            if root not in target.parents:
                raise ValueError(f"zip 밖으로 나가는 경로: {m.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(m) as s, open(target, "wb") as d:
                shutil.copyfileobj(s, d)
            n += 1
    (out / ".done").touch()
    return n


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    zips = sorted(src.rglob("*.zip"))
    print(f"zip {len(zips)}개 발견: {src}")
    for i, z in enumerate(zips, 1):
        # 예: data/Validation/01.원천데이터/VS_01.Management_Female_Experienced/
        out = DST / z.parent.parent.name / z.parent.name / z.stem
        if (out / ".done").exists():
            continue
        n = extract(z, out)
        print(f"[{i}/{len(zips)}] {z.name}: {n}개 파일", flush=True)
    print("완료")


if __name__ == "__main__":
    main()
