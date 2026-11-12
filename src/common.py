"""분석 스크립트 공통 설정."""
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "data"
DOWNLOAD = Path.home() / "Downloads" / "129.채용면접 인터뷰 데이터" / "01-1.정식개방데이터"
OUT = PROJECT / "outputs"
OUT.mkdir(exist_ok=True)

# 라벨의 occupation 코드 → 폴더 이름의 직군
OCCUPATION = {
    "BM": "01.Management",
    "SM": "02.SalesMarketing",
    "PS": "03.PublicService",
    "RND": "04.RND",
    "ICT": "05.ICT",
    "ARD": "06.Design",
    "MM": "07.ProductionManufacturing",
}

# 출력이 cp949 콘솔에서 깨지지 않도록
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_json(raw: bytes):
    """라벨 json을 읽는다.

    반환: (dict 또는 None, 상태)
      "ok"     정상
      "ctrl"   문자열 안 제어문자 때문에 strict 파싱 실패 → 관대하게 읽음
      "broken" JSON 문법 자체가 깨짐 → None
    """
    text = raw.decode("utf-8-sig")
    try:
        return json.loads(text), "ok"
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(text, strict=False), "ctrl"
    except json.JSONDecodeError:
        return None, "broken"


def setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    return plt
