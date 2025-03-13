import streamlit as st
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd
import plotly.express as px
from datetime import datetime
from src.data_loader import get_sigungu_options, get_dong_options, get_dropdown_options, load_pyeong_data
from src.api_client import fetch_complex_list
import numpy as np
import plotly.graph_objects as go
import requests
import re
import os
from dotenv import load_dotenv
from src.config import DATA_PATHS

real_price_path = DATA_PATHS["REAL_PRICE"]
output_path = DATA_PATHS["RESULT"]

load_dotenv()

def to_number(val):
    if pd.isnull(val):
        return float('nan')
    s = str(val).replace(",", "").strip()
    try:
        return float(s)
    except:
        return float('nan')

def format_eokwan(val_in_manwon):
    num = to_number(val_in_manwon)
    if pd.isnull(num):
        return "-"
    v = int(round(num, 0))
    eok = v // 10000
    rem = v % 10000
    if eok > 0 and rem > 0:
        return f"{eok}억 {rem}"
    elif eok > 0:
        return f"{eok}억"
    elif rem > 0:
        return f"{rem}"
    else:
        return "-"

def format_date(ymd):
    if pd.isnull(ymd) or not isinstance(ymd, str):
        return "-"
    parts = ymd.replace("-", ".").replace("/", ".").split(".")
    if len(parts) == 3:
        return f"{parts[0]}.{parts[1].zfill(2)}.{parts[2].zfill(2)}"
    return ymd

def color_gap_html(val):
    if pd.isnull(val) or not isinstance(val, str):
        return ""
    val_str = val.strip()
    if val_str == "":
        return ""
    raw = val_str.replace("%", "")
    try:
        num = float(raw)
        if num > 0:
            return f'<span style="color:red;">▲{abs(num):.1f}%</span>'
        elif num < 0:
            return f'<span style="color:blue;">▼{abs(num):.1f}%</span>'
        else:
            return "0.0%"
    except:
        return val_str

def plain_gap(val):
    if pd.isnull(val) or not isinstance(val, str):
        return ""
    raw = val.replace("%", "").strip()
    try:
        num = float(raw)
        if num > 0:
            return f"▲{abs(num):.1f}%"
        elif num < 0:
            return f"▼{abs(num):.1f}%"
        else:
            return "0.0%"
    except:
        return val

def style_gap(cell_value):
    if isinstance(cell_value, str):
        if cell_value.startswith("▲"):
            return "color: red;"
        elif cell_value.startswith("▼"):
            return "color: blue;"
    return ""

def get_buy_recommendation(gap_index):
    if pd.isnull(gap_index):
        return '', ''
    if gap_index >= 80:
        return '유의 🔴', "갭이 큰 상태입니다."
    elif gap_index >= 40:
        return '중립 🟡', "갭이 다소 있는 편 입니다."
    else:
        return '추천 🟢', "갭이 작은 상태입니다."

def get_bubble_grade(bubble_index):
    if pd.isnull(bubble_index):
        return '', ''
    if bubble_index > 100:
        return '높음 🔴', '매물 가격대가 매우 높습니다.'
    elif bubble_index >= 80:
        return '주의 🟡', '매물 가격대가 다소 높습니다.'
    else:
        return '보통 🟢', '매물 가격대가 적정 수준입니다.'

@st.cache_data
def fetch_pyeong_list(complex_id: str) -> List[str]:
    url = f"https://new.land.naver.com/api/complexes/{complex_id}"
    cookies = {
        'NNB': os.getenv('NNB'),
        'ASID': os.getenv('ASID'),
        'NAC': os.getenv('NAC'),
        'landHomeFlashUseYn': 'Y',
        'page_uid': os.getenv('BUILDING_PAGE_UID'),
        'REALESTATE': os.getenv('BUILDING_REALESTATE'),
        'SRT30': os.getenv('BUILDING_SRT30'),
        'SRT5': os.getenv('BUILDING_SRT5'),
        'BUC': os.getenv('BUILDING_BUC')
    }
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en;q=0.9,ko-KR;q=0.8',
        'authorization': os.getenv('BUILDING_AUTHORIZATION'),
        'user-agent': os.getenv('USER_AGENT')
    }
    params = {"sameAddressGroup": "true"}
    try:
        response = requests.get(url, params=params, cookies=cookies, headers=headers)
        if response.status_code == 200:
            data = response.json()
            pyeong_list = [pyeong.get("pyeongName2", "") for pyeong in data.get("complexPyeongDetailList", [])]
            pyeong_list = [re.sub(r'[A-Za-z]+$', '', pyeong) for pyeong in pyeong_list if pyeong]
            return sorted(list(set(pyeong_list)))
        else:
            st.error(f"평형 데이터 조회 실패: 상태 코드 {response.status_code}")
            return []
    except Exception as e:
        st.error(f"평형 데이터 조회 중 오류: {e}")
        return []

def render_sidebar(region_df: pd.DataFrame) -> Tuple[List[str], pd.DataFrame]:
    selected_complexes = []
    df_filtered = pd.DataFrame()

    with st.sidebar:
        st.title("아파트 단지 선택")
        apt1_id, apt1_name = render_apt_selection("1", region_df)
        if apt1_id:
            selected_complexes.append(str(apt1_id))
            st.session_state.app_state["apt1_complex"] = str(apt1_id)
            st.session_state.app_state["apt1_selected"] = True
        apt2_id, apt2_name = render_apt_selection("2", region_df)
        if apt2_id:
            selected_complexes.append(str(apt2_id))
            st.session_state.app_state["apt2_complex"] = str(apt2_id)
            st.session_state.app_state["apt2_selected"] = True

        if st.session_state.app_state.get("apt1_selected") and st.session_state.app_state.get("apt2_selected"):
            if st.button("분석 실행", type="primary"):
                try:
                    from src.naver_apt_v5 import main_function as run_01
                    run_01(selected_complexes)
                    from src.sell_price_merge_v2 import main as run_03
                    run_03(selected_complexes)
                    st.success("분석이 완료되었습니다!")
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")

    if st.session_state.app_state.get("analysis_done") and selected_complexes:
        try:
            if not os.path.exists(output_path):
                st.error(f"결과 파일이 없습니다: {output_path}")
                st.stop()
            df_filtered = pd.read_csv(output_path, encoding='utf-8-sig')
            if "complexNo" not in df_filtered.columns:
                st.error("complexNo 컬럼이 없습니다")
                st.stop()
            df_filtered["complexNo"] = df_filtered["complexNo"].astype(str)
            df_filtered = df_filtered[df_filtered["complexNo"].isin(selected_complexes)]
            if df_filtered.empty:
                st.warning("선택된 단지에 대한 데이터가 없습니다")
                st.stop()
        except Exception as e:
            st.error(f"데이터 로드 중 오류 발생: {e}")
    return selected_complexes, df_filtered

def render_apt_selection(prefix: str, region_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    st.sidebar.subheader(f"아파트{prefix} 지역 선택")
    sido_options = get_dropdown_options(region_df, "시/도")
    selected_sido = st.sidebar.selectbox(f"시/도({prefix})", [""] + sido_options, key=f"sido_{prefix}")
    if not selected_sido:
        return None, None
    sigungu_options = get_sigungu_options(region_df, selected_sido)
    selected_sigungu = st.sidebar.selectbox(f"시/군/구({prefix})", [""] + sigungu_options, key=f"sigungu_{prefix}")
    if not selected_sigungu:
        return None, None
    dong_options = get_dong_options(region_df, selected_sido, selected_sigungu)
    selected_dong = st.sidebar.selectbox(f"읍/면/동({prefix})", [""] + dong_options, key=f"dong_{prefix}")
    if not selected_dong:
        return None, None
    complexes = fetch_complex_list(str(region_df[
        (region_df["시/도"] == selected_sido) &
        (region_df["시/군/구"] == selected_sigungu) &
        (region_df["읍/면/동"] == selected_dong)
    ]["cortarNo"].iloc[0]))
    if not complexes:
        return None, None
    complex_options = {comp["complexName"]: comp["complexNo"] for comp in complexes}
    selected_apt = st.sidebar.selectbox(f"아파트{prefix} 단지 선택", [""] + list(complex_options.keys()), key=f"apt_{prefix}")
    if not selected_apt:
        return None, None
    pyeong_options = fetch_pyeong_list(str(complex_options[selected_apt]))
    selected_pyeong = st.sidebar.selectbox(
        f"아파트{prefix} 평형 선택",
        [""] + pyeong_options,
        key=f"pyeong_{prefix}"
    )
    st.session_state.app_state[f"apt{prefix}_pyeong"] = selected_pyeong if selected_pyeong else None
    return str(complex_options[selected_apt]), selected_apt

def render_visualization(selected_complexes: List[str], df_filtered: pd.DataFrame):
    try:
        df_real = pd.read_csv(real_price_path, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"price_data.csv 파일을 로드하는 중 오류 발생: {e}")
        return

    try:
        df_real["complexNo"] = df_real["complexNo"].astype(str)
        df_real["pyeongName3"] = df_real["pyeongName3"].astype(str)
        df_filtered["complexNo"] = df_filtered["complexNo"].astype(str)
        df_filtered["pyeongName3"] = df_filtered["pyeongName3"].astype(str)

        selected_pyeong_apt1 = st.session_state.app_state.get("apt1_pyeong", None)
        selected_pyeong_apt2 = st.session_state.app_state.get("apt2_pyeong", None)
        apt1_complex = st.session_state.app_state.get("apt1_complex", None)
        apt2_complex = st.session_state.app_state.get("apt2_complex", None)

        df_filtered_list = []
        df_real_filtered_list = []

        if apt1_complex and selected_pyeong_apt1:
            df_filtered_list.append(
                df_filtered[
                    (df_filtered["complexNo"] == apt1_complex) &
                    (df_filtered["pyeongName3"] == selected_pyeong_apt1)
                ]
            )
            df_real_filtered_list.append(
                df_real[
                    (df_real["complexNo"] == apt1_complex) &
                    (df_real["pyeongName3"] == selected_pyeong_apt1)
                ]
            )

        if apt2_complex and selected_pyeong_apt2:
            df_filtered_list.append(
                df_filtered[
                    (df_filtered["complexNo"] == apt2_complex) &
                    (df_filtered["pyeongName3"] == selected_pyeong_apt2)
                ]
            )
            df_real_filtered_list.append(
                df_real[
                    (df_real["complexNo"] == apt2_complex) &
                    (df_real["pyeongName3"] == selected_pyeong_apt2)
                ]
            )

        df_filtered = pd.concat(df_filtered_list, ignore_index=True) if df_filtered_list else pd.DataFrame()
        df_real_filtered = pd.concat(df_real_filtered_list, ignore_index=True) if df_real_filtered_list else pd.DataFrame()

        if df_real_filtered.empty:
            st.warning("선택된 아파트-평형 쌍에 해당하는 데이터가 없습니다.")
            df_real_filtered = df_real[df_real["complexNo"].isin(selected_complexes)].copy()
            df_filtered = df_filtered[df_filtered["complexNo"].isin(selected_complexes)].copy()

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return

    gap_index = None
    gap_grade = None
    gap_guide = None
    
    if df_real_filtered is not None and not df_real_filtered.empty:
        df_rp = df_real_filtered[df_real_filtered["dealDateClass"].isin([5, 3, 1])].copy()
        if not df_rp.empty:
            df_rp["dealAmount_numeric"] = pd.to_numeric(
                df_rp["dealAmount"].astype(str).str.replace(",", ""),
                errors="coerce"
            )
            df_rp["dealAmount_eok"] = df_rp["dealAmount_numeric"] / 10000.0
            df_rp["color_label"] = df_rp["complexName"].astype(str) + " " + df_rp["pyeongName3"].astype(str) + "평"
            
            unique_labels = df_rp["color_label"].unique()
            if len(unique_labels) == 2:
                df_rp["dealDate"] = pd.to_datetime(df_rp["dealDate"], errors="coerce")
                df_rp["year_month"] = df_rp["dealDate"].dt.to_period("M").dt.to_timestamp()
                df_monthly = df_rp.groupby(["complexName", "pyeongName3", "year_month"], as_index=False).agg({"dealAmount_eok": "mean"})
                df_monthly["color_label"] = df_monthly["complexName"].astype(str) + " " + df_monthly["pyeongName3"].astype(str) + "평"
                df_gap = df_monthly.pivot(
                    index='year_month',
                    columns='color_label',
                    values='dealAmount_eok'
                ).reset_index()
                df_gap[unique_labels[0]] = df_gap[unique_labels[0]].ffill().bfill()
                df_gap[unique_labels[1]] = df_gap[unique_labels[1]].ffill().bfill()
                
                if not df_gap.empty:
                    # tooltip_date 컬럼 추가
                    df_gap['tooltip_date'] = df_gap['year_month'].dt.strftime("'%y.%m월")
                    df_gap['price_gap'] = abs(df_gap[unique_labels[0]] - df_gap[unique_labels[1]])
                    df_gap['is_estimated'] = df_gap[unique_labels[0]].isna() | df_gap[unique_labels[1]].isna()
                    
                    real_gaps = df_gap.loc[~df_gap['is_estimated'], 'price_gap']
                    if not real_gaps.empty:
                        max_real_gap = real_gaps.max()
                        min_real_gap = real_gaps.min()
                        latest_gap = df_gap['price_gap'].iloc[-1]
                        if (max_real_gap - min_real_gap) > 0:
                            gap_index = ((1 - (max_real_gap - latest_gap) / (max_real_gap - min_real_gap)) * 100)
                            gap_grade, gap_guide = get_buy_recommendation(gap_index)

    st.subheader("📄 기본 정보")
    try:
        if df_filtered.empty:
            st.info("선택된 아파트 데이터가 없습니다.")
        else:
            df_basic = df_filtered.groupby("complexName", as_index=False).first()
            df_basic["세대수(임대)"] = df_basic.apply(
                lambda x: f"{int(x['totalHouseholdCount']):,}({int(x['totalLeaseHouseholdCount']):,})"
                          if pd.notnull(x['totalHouseholdCount']) and pd.notnull(x['totalLeaseHouseholdCount'])
                          else "",
                axis=1
            )
            df_basic["사용승인"] = df_basic["useApproveYmd"].apply(format_date)
            df_basic["동 수"] = df_basic["totalDongCount"].fillna(0).astype(int)
            df_basic["최고층수"] = df_basic["highFloor"].fillna(0).astype(int)
            df_basic["세대당 주차대수"] = df_basic["parkingCountByHousehold"].apply(
                lambda x: f"{float(x):.2f}" if pd.notnull(x) else ""
            )
            df_basic["용적률"] = df_basic["batlRatio"].apply(
                lambda x: f"{int(x)}%" if pd.notnull(x) else ""
            )
            df_basic["건폐율"] = df_basic["btlRatio"].apply(
                lambda x: f"{int(x)}%" if pd.notnull(x) else ""
            )
            df_basic["배정 초교(도보 소요시간)"] = df_basic.apply(
                lambda x: f"{x['schoolName']}({int(x['walkTime'])}분)"
                          if pd.notnull(x['schoolName']) and pd.notnull(x['walkTime']) else "",
                axis=1
            )
            df_basic["평형구성"] = df_basic["pyoengNames"].fillna("")
            df_basic["매물수"] = df_basic["dealCount_y"].fillna(0).astype(int)
            df_basic["매물등록률"] = df_basic["매매매물출현율_y"].fillna(0)
            display_cols = ["complexName", "세대수(임대)", "사용승인", "동 수", "최고층수",
                            "세대당 주차대수", "용적률", "건폐율", "배정 초교(도보 소요시간)",
                            "평형구성", "매물수", "매물등록률"]
            col_rename = {"complexName": "아파트명"}
            df_show = df_basic[display_cols].rename(columns=col_rename)
            st.table(df_show.style.set_table_styles([
                {"selector": "th", "props": [("background-color", "#f0f2f6"), ("font-weight", "bold")]}
            ]))
    except Exception as e:
        st.error(f"기본 정보 렌더링 중 오류: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader("📌 투자 지표 요약")
    st.markdown("""
    <style>
    th[data-tooltip] {
        position: relative;
    }
    th[data-tooltip]::after {
        content: attr(data-tooltip);
        white-space: pre-line;
        position: absolute;
        bottom: -120%;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(85, 85, 85, 0.7);
        color: #fff;
        padding: 8px;
        border-radius: 4px;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s;
        z-index: 100;
        width: 300px;
        text-align: left;
    }
    th[data-tooltip]:hover::after {
        opacity: 1;
        visibility: visible;
    }
    </style>
    """, unsafe_allow_html=True)

    try:
        if not df_filtered.empty:
            df_metrics = df_filtered[df_filtered["tradeTypeName"] == "매매"].copy()
            if not df_metrics.empty:
                if 'bubble_score' not in df_metrics.columns:
                    st.error("bubble_score 컬럼이 없습니다. 데이터 파일을 확인하세요.")
                    df_metrics['bubble_score'] = 50

                df_bubble = df_metrics.groupby(['complexNo', 'complexName', 'pyeongName3'])['bubble_score'].median().reset_index()
                df_bubble = df_bubble.groupby('complexName').agg({
                    'bubble_score': 'mean',
                    'pyeongName3': 'first'
                }).reset_index()

                gap_tooltip_text = (
                    "갭 지수: 두 아파트 간 실거래가 갭에 따른 매수 추천 등급\n"
                    "80점↑: 유의 🔴 - 매수 비추\n"
                    "40~80점: 중립 🟡 - 매수 신중\n"
                    "40점↓: 추천 🟢 - 매수 검토"
                )
                bubble_tooltip_text = (
                    "버블 지수 : 실거래가 대비 매물호가의 괴리에 따른 매수 추천 등급\n"
                    "100점↑: 높음 🔴 - 매수 비추\n"
                    "80~100점: 주의 🟡 - 매수 신중\n"
                    "80점↓: 보통 🟢 - 매수 검토"
                )

                html_table = "<table style='border-collapse: collapse; width: 100%;'>"
                html_table += "<tr style='background-color: #f0f2f6; font-weight: bold; text-align: center;'>"
                html_table += "<th style='border: 1px solid #e0e0e0; padding: 8px; width: 34%;'>아파트</th>"
                html_table += f"<th style='border: 1px solid #e0e0e0; padding: 8px; width: 33%;' data-tooltip='{gap_tooltip_text}'>갭 지수</th>"
                html_table += f"<th style='border: 1px solid #e0e0e0; padding: 8px; width: 33%;' data-tooltip='{bubble_tooltip_text}'>버블 지수</th>"
                html_table += "</tr>"

                if len(df_bubble) >= 2:
                    row1 = df_bubble.iloc[0]
                    bubble_score1 = int(round(row1['bubble_score'], 0))
                    bubble_grade1, bubble_guide1 = get_bubble_grade(bubble_score1)
                    bubble_cell1 = f"{bubble_score1}점 ({bubble_grade1})<br><span style='color: gray; font-size: 0.9em;'>{bubble_guide1}</span>"

                    row2 = df_bubble.iloc[1]
                    bubble_score2 = int(round(row2['bubble_score'], 0))
                    bubble_grade2, bubble_guide2 = get_bubble_grade(bubble_score2)
                    bubble_cell2 = f"{bubble_score2}점 ({bubble_grade2})<br><span style='color: gray; font-size: 0.9em;'>{bubble_guide2}</span>"

                    if gap_index is not None:
                        gap_index_int = int(round(gap_index, 0))
                        gap_grade, gap_guide = get_buy_recommendation(gap_index_int)
                        gap_cell = f"{gap_index_int}점 ({gap_grade})<br><span style='color: gray; font-size: 0.9em;'>{gap_guide}</span>"
                    else:
                        gap_cell = "-"

                    html_table += "<tr style='text-align: center;'>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;'>{row1['complexName']}<br>{row1['pyeongName3']}평</td>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;' rowspan='2'>{gap_cell}</td>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;'>{bubble_cell1}</td>"
                    html_table += "</tr>"

                    html_table += "<tr style='text-align: center;'>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;'>{row2['complexName']}<br>{row2['pyeongName3']}평</td>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;'>{bubble_cell2}</td>"
                    html_table += "</tr>"
                else:
                    st.warning("두 개 이상의 단지가 필요합니다.")

                html_table += "</table>"
                st.markdown(html_table, unsafe_allow_html=True)
            else:
                st.warning("매매 데이터가 없습니다.")
        else:
            st.warning("필터링된 데이터가 없습니다.")
    except Exception as e:
        st.error(f"투자 지표 요약 렌더링 중 오류: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader("📈 실거래가 추이")
    try:
        period_option = st.radio(
            "기간 선택",
            ("최근 5년간", "최근 3년간", "최근 1년간"),
            horizontal=True,
            label_visibility="collapsed"
        )
        if period_option == "최근 5년간":
            allowed = [5, 3, 1]
        elif period_option == "최근 3년간":
            allowed = [3, 1]
        else:
            allowed = [1]

        df_rp = df_real_filtered[df_real_filtered["dealDateClass"].isin(allowed)].copy()

        if not df_rp.empty:
            if "dealAmount_numeric" not in df_rp.columns:
                df_rp["dealAmount_numeric"] = pd.to_numeric(
                    df_rp["dealAmount"].astype(str).str.replace(",", ""),
                    errors="coerce"
                )
            if df_rp["dealDate"].dtype == object:
                df_rp["dealDate"] = pd.to_datetime(df_rp["dealDate"], errors="coerce")
            df_rp["dealAmount_eok"] = df_rp["dealAmount_numeric"] / 10000.0
            df_rp["color_label"] = df_rp["complexName"].astype(str) + " " + df_rp["pyeongName3"].astype(str) + "평"
            df_rp["year_month"] = df_rp["dealDate"].dt.to_period("M").dt.to_timestamp()
            df_monthly = df_rp.groupby(["complexName", "pyeongName3", "year_month"], as_index=False).agg({"dealAmount_numeric": "mean"})
            df_monthly["dealAmount_eok"] = df_monthly["dealAmount_numeric"] / 10000.0
            df_monthly["color_label"] = df_monthly["complexName"].astype(str) + " " + df_monthly["pyeongName3"].astype(str) + "평"

            colors = px.colors.qualitative.Set1
            unique_labels = df_rp["color_label"].unique()
            color_map = {label: colors[i % len(colors)] for i, label in enumerate(unique_labels)}

            if len(unique_labels) == 2:
                df_gap = df_monthly.pivot(
                    index='year_month',
                    columns='color_label',
                    values='dealAmount_eok'
                ).reset_index()
                df_gap[unique_labels[0]] = df_gap[unique_labels[0]].ffill().bfill()
                df_gap[unique_labels[1]] = df_gap[unique_labels[1]].ffill().bfill()
                
                if not df_gap.empty:
                    df_gap['tooltip_date'] = df_gap['year_month'].dt.strftime("'%y.%m월")
                    df_gap['price_gap'] = abs(df_gap[unique_labels[0]] - df_gap[unique_labels[1]])
                    df_gap['is_estimated'] = df_gap[unique_labels[0]].isna() | df_gap[unique_labels[1]].isna()
                    
                    real_gaps = df_gap.loc[~df_gap['is_estimated'], 'price_gap']
                    if not real_gaps.empty:
                        max_real_gap = real_gaps.max()
                        min_real_gap = real_gaps.min()
                        latest_gap = df_gap['price_gap'].iloc[-1]
                        if (max_real_gap - min_real_gap) > 0:
                            gap_index = ((1 - (max_real_gap - latest_gap) / (max_real_gap - min_real_gap)) * 100)
                            gap_grade, gap_guide = get_buy_recommendation(gap_index)

            fig_line = go.Figure()
            fig_line.update_layout(hovermode="closest")

            if len(unique_labels) == 2 and not df_gap.empty:
                real_gaps = df_gap.loc[~df_gap['is_estimated'], 'price_gap']
                max_real_gap = real_gaps.max()
                min_real_gap = real_gaps.min()
                latest_gap = df_gap['price_gap'].iloc[-1]
                
                gap_index = ((1 - (max_real_gap - latest_gap) / (max_real_gap - min_real_gap)) * 100) if (max_real_gap - min_real_gap) > 0 else 0
                gap_grade, gap_guide = get_buy_recommendation(gap_index)

                mask_real = ~df_gap['is_estimated']
                mask_estimated = df_gap['is_estimated']

                if mask_real.any():
                    fig_line.add_trace(go.Bar(
                        x=df_gap.loc[mask_real, 'year_month'],
                        y=df_gap.loc[mask_real, 'price_gap'],
                        name='실거래가 갭',
                        marker_color='rgba(180, 180, 180, 0.6)',
                        yaxis='y2',
                        hovertemplate='%{customdata[0]}<br>갭 금액: %{y:.1f}억<extra></extra>',
                        customdata=df_gap.loc[mask_real, ['tooltip_date']].values
                    ))

                    if mask_estimated.any():
                        fig_line.add_trace(go.Bar(
                            x=df_gap.loc[mask_estimated, 'year_month'],
                            y=df_gap.loc[mask_estimated, 'price_gap'],
                            name='실거래가 갭(추정)',
                            marker_color='rgba(180, 180, 180, 0.2)',
                            yaxis='y2',
                            hovertemplate='%{customdata[0]}<br>갭 금액(추정): %{y:.1f}억<extra></extra>',
                            customdata=df_gap.loc[mask_estimated, ['tooltip_date']].values
                        ))

            for label in unique_labels:
                monthly_sub = df_monthly[df_monthly["color_label"] == label].sort_values("year_month")
                if not monthly_sub.empty:
                    fig_line.add_trace(go.Scatter(
                        x=monthly_sub["year_month"],
                        y=monthly_sub["dealAmount_eok"],
                        mode="lines",
                        name=label,
                        hoverinfo="skip",
                        line=dict(color=color_map[label])
                    ))

            for label in unique_labels:
                daily_sub = df_rp[df_rp["color_label"] == label].sort_values("dealDate")
                def make_daily_tooltip(row):
                    deal_date_str = row["dealDate"].strftime("%Y.%m.%d") if not pd.isnull(row["dealDate"]) else "-"
                    floor_str = f"{int(row['floor'])}층" if not pd.isnull(row["floor"]) else "-"
                    price_str = format_eokwan(row["dealAmount_numeric"])
                    return f"{row['complexName']}<br>{deal_date_str}<br>{row['pyeongName2']} / {floor_str}<br>{price_str}"
                daily_sub["tooltip"] = daily_sub.apply(make_daily_tooltip, axis=1)
                if not daily_sub.empty:
                    fig_line.add_trace(go.Scatter(
                        x=daily_sub["dealDate"],
                        y=daily_sub["dealAmount_eok"],
                        mode="markers",
                        marker=dict(size=6, opacity=0.3, color=color_map[label]),
                        showlegend=False,
                        hovertemplate="%{text}<extra></extra>",
                        text=daily_sub["tooltip"]
                    ))

            fig_line.update_xaxes(tickformat="'%y.%m월", hoverformat="'%y.%m월")
            fig_line.update_yaxes(tickformat=".0f", ticksuffix="억")
            fig_line.update_layout(
                xaxis_title="",
                yaxis_title="",
                yaxis2=dict(
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    tickformat=".1f",
                    ticksuffix="억"
                ),
                legend=dict(
                    bgcolor='rgba(255,255,255,0)',
                    bordercolor='rgba(255,255,255,0)',
                    x=0.01,
                    y=1.15,
                    orientation='h'
                ),
                legend_title="",
                margin=dict(l=20, r=20, t=40, b=10),
                autosize=True,
                bargap=0.3
            )
            st.plotly_chart(fig_line, use_container_width=True)

            df_table = df_rp.copy()
            df_table["거래일"] = df_table["dealDate"].apply(lambda x: x.strftime("%Y.%m.%d") if not pd.isnull(x) else "-")
            df_table["아파트명"] = df_table["complexName"].fillna("-")
            df_table["평형타입"] = df_table["pyeongName2"].fillna("-")
            df_table["층수"] = df_table["floor"].apply(lambda x: str(int(x)) if pd.notnull(x) else "-")
            df_table["실거래가"] = df_table["dealAmount_numeric"].apply(format_eokwan)
            df_table.sort_values(by="dealDate", ascending=False, inplace=True)
            final_cols_table = ["거래일", "아파트명", "평형타입", "층수", "실거래가"]
            st.dataframe(df_table[final_cols_table], use_container_width=True)
    except Exception as e:
        st.error(f"실거래가 추이 렌더링 중 오류: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader("📊 매물 현황")
    try:
        if not df_filtered[df_filtered["tradeTypeName"] == "매매"].empty:
            df_for_list = df_filtered[df_filtered["tradeTypeName"] == "매매"].copy()
            df_for_list["price_numeric"] = pd.to_numeric(
                df_for_list["dealOrWarrantPrc2"].astype(str).str.replace(",", ""),
                errors="coerce"
            )
            df_for_list.sort_values("price_numeric", inplace=True)
            df_for_list["호가"] = df_for_list["price_numeric"].apply(format_eokwan)
            df_for_list["아파트명"] = df_for_list["complexName"]
            df_for_list["거래유형"] = df_for_list["tradeTypeName"]
            df_for_list["층수"] = df_for_list["floorInfo"].fillna("")
            df_for_list["평형타입"] = df_for_list["pyeongName"].fillna("")
            df_for_list["공급면적(㎡)"] = df_for_list["area1"].fillna(0).astype(int)
            df_for_list["전용면적(㎡)"] = df_for_list["area2"].fillna(0).astype(int)
            df_for_list["방향"] = df_for_list["direction"].fillna("")
            df_for_list["동"] = df_for_list["buildingName"].fillna("")
        
            def format_ymd_local(val):
                if pd.isnull(val):
                    return ""
                val_str = str(val).replace("-", ".").replace("/", ".")
                parts = val_str.split(".")
                if len(parts) == 3:
                    return f"{parts[0]}.{parts[1].zfill(2)}.{parts[2].zfill(2)}"
                return val_str
        
            df_for_list["매물등록일"] = df_for_list["articleConfirmYmd"].apply(format_ymd_local)
            df_for_list["동일매물등록수"] = df_for_list["sameAddrCnt"].fillna(0).astype(int)
            df_for_list["동일타입세대수"] = df_for_list["householdCountByPyeong"].fillna(0).astype(int)
            df_for_list["동일타입매물수"] = df_for_list["dealCount_x"].fillna(0).astype(int)
            df_for_list["동일타입매물등록률"] = df_for_list["매매매물출현율_x"]
        
            df_for_list["실거래가 전고점"] = df_for_list["pyeong_max_5"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "")
            df_for_list["실거래가 평균"] = df_for_list["pyeong_avg_5"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "")
            df_for_list["실거래가 전저점"] = df_for_list["pyeong_min_5"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "")
        
            df_for_list["실거래가 전고점 갭"] = df_for_list["real_max_5_gap"].apply(plain_gap)
            df_for_list["실거래가 전저점 갭"] = df_for_list["real_min_5_gap"].apply(plain_gap)
        
            df_for_list["KB시세(상위평균)"] = df_for_list["dealUpperPriceLimit"].apply(format_eokwan)
            df_for_list["KB시세(일반평균)"] = df_for_list["dealAveragePrice"].apply(format_eokwan)
            df_for_list["KB시세(하위평균)"] = df_for_list["dealLowPriceLimit"].apply(format_eokwan)
            df_for_list["KB시세 전세가율"] = df_for_list["leasePerDealRate"].fillna("")
        
            df_for_list["상세 설명"] = df_for_list["articleFeatureDesc"].fillna("")
            df_for_list["중개사무소"] = df_for_list["realtorName"].fillna("")
        
            def make_link(row):
                return f"https://new.land.naver.com/complexes/{row['complexNo']}?articleNo={row['articleNo']}"
            df_for_list["매물 링크"] = df_for_list.apply(make_link, axis=1)
        
            final_cols_list = [
                "아파트명", "거래유형", "층수", "호가", "평형타입",
                "공급면적(㎡)", "전용면적(㎡)", "방향", "동",
                "매물등록일", "동일매물등록수", "동일타입세대수", "동일타입매물수",
                "동일타입매물등록률", "실거래가 전고점 갭", "실거래가 전저점 갭",
                "KB시세(상위평균)", "KB시세(일반평균)", "KB시세(하위평균)", "KB시세 전세가율",
                "상세 설명", "중개사무소", "매물 링크"
            ]
            df_show_list = df_for_list[final_cols_list].copy()
            styler = df_show_list.style.applymap(style_gap, subset=["실거래가 전고점 갭", "실거래가 전저점 갭"])
            st.dataframe(
                styler,
                column_config={
                    "매물 링크": st.column_config.LinkColumn(
                        label="매물 링크",
                        display_text="🔗",
                        help="클릭하여 매물 페이지로 이동"
                    )
                },
                use_container_width=True
            )
    except Exception as e:
        st.error(f"매물 리스트 렌더링 중 오류: {e}")