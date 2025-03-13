import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent  # config.py의 상위 폴더로 변경
DATA_DIR = BASE_DIR / "data"

# Data paths
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

# UI Constants
UI_CONFIG = {
    "PAGE_TITLE": "집착 - 아파트를 째려보다",
    "PAGE_ICON": "🏠",
    "LAYOUT": "wide",
    "INITIAL_SIDEBAR_STATE": "expanded"
}
