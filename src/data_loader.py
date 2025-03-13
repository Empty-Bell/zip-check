import pandas as pd
import streamlit as st
import os
from typing import List, Optional, Dict, Tuple
from src.config import DATA_PATHS, BASE_DIR, DATA_DIR

@st.cache_data
def load_pyeong_data(complex_ids: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """평형 데이터 로딩 및 필터링"""
    try:
        df = pd.read_csv(DATA_PATHS["PYEONG"], encoding='utf-8-sig')
        if complex_ids:
            df = df[df['complexNo'].isin(complex_ids)]
        pyeong_dict = {}
        for complex_no, group in df.groupby('complexNo'):
            pyeong_dict[str(complex_no)] = sorted(group['pyeongName3'].unique().tolist())
        return pyeong_dict
    except Exception as e:
        st.error(f"평형 데이터 로드 중 오류: {e}")
        return {}

# 나머지 함수는 그대로 유지

@st.cache_data
def load_region_mapping() -> pd.DataFrame:
    """법정동 코드 데이터 로딩"""
    try:
        return pd.read_csv(DATA_PATHS["CORTAR"], encoding="utf-8-sig")
    except Exception as e:
        st.error(f"법정동 데이터 로드 중 오류: {e}")
        return pd.DataFrame()

@st.cache_data
def load_analysis_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """분석 결과 데이터 로딩"""
    try:
        df_result = pd.read_csv(DATA_PATHS["RESULT"], encoding='utf-8-sig')
        df_real = pd.read_csv(DATA_PATHS["REAL_PRICE"], encoding='utf-8-sig')
        return df_result, df_real
    except Exception as e:
        st.error(f"분석 데이터 로드 중 오류: {e}")
        return None, None

def get_dropdown_options(df: pd.DataFrame, column: str) -> List[str]:
    """드롭다운 옵션 목록 반환"""
    return sorted(df[column].dropna().unique())

def get_sigungu_options(df: pd.DataFrame, selected_sido: str) -> List[str]:
    """시군구 목록 반환"""
    if not selected_sido:
        return []
    return sorted(df[df["시/도"] == selected_sido]["시/군/구"].dropna().unique())

def get_dong_options(df: pd.DataFrame, selected_sido: str, selected_sigungu: str) -> List[str]:
    """읍면동 목록 반환"""
    if not selected_sido or not selected_sigungu:
        return []
    return sorted(df[
        (df["시/도"] == selected_sido) & 
        (df["시/군/구"] == selected_sigungu)
    ]["읍/면/동"].dropna().unique())
