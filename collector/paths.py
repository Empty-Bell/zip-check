"""공통 경로 정의 (수집기 + 정적 데이터 빌드)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"               # 수집 중간산출(CSV, gitignore)
DOCS_DIR = BASE_DIR / "docs"               # GitHub Pages 루트
SITE_DATA_DIR = DOCS_DIR / "data"          # 정적 사이트가 읽는 JSON
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

# 수집 중간산출 CSV 경로
DATA_PATHS = {
    "CORTAR": DATA_DIR / "cortarNo.csv",
    "COMPLEX": DATA_DIR / "complex_data.csv",
    "PYEONG": DATA_DIR / "pyeong_data.csv",
    "SELL": DATA_DIR / "sell_data.csv",
    "RESULT": DATA_DIR / "result.csv",
    "REAL_PRICE": DATA_DIR / "price_data.csv",
    "DONG": DATA_DIR / "dong_data.csv",
    "PROVIDER": DATA_DIR / "provider_data.csv",
}
