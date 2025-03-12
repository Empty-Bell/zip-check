import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 세션 상태 초기화 (Streamlit 명령 아님)
if "app_state" not in st.session_state:
    st.session_state.app_state = {
        "analysis_done": False,
        "apt1_selected": False,
        "apt2_selected": False,
        "apt1_complex": None,
        "apt2_complex": None,
        "apt1_pyeong": None,
        "apt2_pyeong": None,
        "last_analysis_time": None,
        "error": None
    }

# 페이지 설정 (첫 번째 Streamlit 명령)
st.set_page_config(
    page_title="집착 - 아파트를 째려보다",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 이후 모듈 임포트
from data_loader import (
    load_region_mapping,
    load_analysis_data,
    get_dropdown_options,
    get_sigungu_options,
    get_dong_options,
    load_pyeong_data
)
from api_client import fetch_complex_list
from ui_components_v2 import render_sidebar, render_visualization
from styles import STREAMLIT_STYLE

# 스타일 적용
st.markdown(STREAMLIT_STYLE, unsafe_allow_html=True)

# 데이터 로드
region_df = load_region_mapping()

# 사이드바 렌더링 및 선택된 아파트 정보 가져오기
selected_complexes, df_filtered = render_sidebar(region_df)

# 메인 컨텐츠 영역
st.markdown(
    "<h1>🏠 <span style='color:red;'>집</span><span style='color:red;'>착</span> : "
    "원하는 <span style='color:red;'>집</span>에 정<span style='color:red;'>착</span>하는 그날까지</h1>",
    unsafe_allow_html=True
)
st.caption("내가 갈아타고 싶은 아파트의 실거래와 매물을 좀더 딥하게 째려보자!")

# 상태에 따른 화면 표시
if st.session_state.app_state["error"]:
    st.error(st.session_state.app_state["error"])
elif not st.session_state.app_state["analysis_done"]:
    st.info("아파트1과 아파트2를 선택하고 '분석 실행' 버튼을 눌러주세요.")
else:
    render_visualization(selected_complexes, df_filtered)

if __name__ == "__main__":
    pass