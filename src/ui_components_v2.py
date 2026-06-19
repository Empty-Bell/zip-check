import streamlit as st
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd
import plotly.express as px
from datetime import datetime
from src.data_loader import get_sigungu_options, get_dong_options, get_dropdown_options
from src.api_client import fetch_complex_list
import numpy as np
import plotly.graph_objects as go
import requests
import re
import os
from dotenv import load_dotenv
from src.config import DATA_PATHS

# 파일 경로 설정 부분 수정
real_price_path = DATA_PATHS["REAL_PRICE"]
output_path = DATA_PATHS["RESULT"]

# .env 파일 로드
load_dotenv()

# --- 헬퍼 함수 정의 ---
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
    """갭 지수에 따른 매수 추천 등급과 가이드 반환"""
    if pd.isnull(gap_index):
        return '', ''
    if gap_index >= 80:
        return '유의 🔴', "갭이 큰 상태입니다."
    elif gap_index >= 40:
        return '중립 🟡', "갭이 다소 있는 편 입니다."
    else:
        return '추천 🟢', "갭이 작은 상태입니다."

def get_bubble_grade(bubble_index):
    """버블지수에 따른 상태와 가이드 반환 (고객 요청 반영)"""
    if pd.isnull(bubble_index):
        return '', ''
    if bubble_index > 100:
        return '높음 🔴', '매물 가격대가 매우 높습니다.'
    elif bubble_index >= 80:
        return '주의 🟡', '매물 가격대가 다소 높습니다.'
    else:
        return '보통 🟢', '매물 가격대가 적정 수준입니다.'

# --- 기존 함수들 ---
@st.cache_data
def fetch_pyeong_list(complex_id: str) -> List[str]:
    """네이버 부동산 API에서 단지별 평형 리스트를 가져옴"""
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
        response = requests.get(url, params=params, cookies=cookies, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pyeong_list = [pyeong.get("pyeongName2", "") for pyeong in data.get("complexPyeongDetailList", [])]
            # 영문 제거하여 pyeongName3 생성
            pyeong_list = [re.sub(r'[A-Za-z]+$', '', pyeong) for pyeong in pyeong_list if pyeong]
            return sorted(list(set(pyeong_list)))
        else:
            st.error(f"평형 데이터 조회 실패: 상태 코드 {response.status_code}")
            return []
    except Exception as e:
        st.error(f"평형 데이터 조회 중 오류: {e}")
        return []

def render_sidebar(region_df: pd.DataFrame) -> Tuple[List[str], pd.DataFrame]:
    """사이드바 렌더링"""
    selected_complexes = []
    df_filtered = pd.DataFrame()

    with st.sidebar:
        st.title("아파트 단지 선택")
        # 아파트 1 선택
        apt1_id, apt1_name = render_apt_selection("1", region_df)
        if apt1_id:
            selected_complexes.append(str(apt1_id))
            st.session_state.app_state["apt1_complex"] = str(apt1_id)
            st.session_state.app_state["apt1_selected"] = True
        # 아파트 2 선택
        apt2_id, apt2_name = render_apt_selection("2", region_df)
        if apt2_id:
            selected_complexes.append(str(apt2_id))
            st.session_state.app_state["apt2_complex"] = str(apt2_id)
            st.session_state.app_state["apt2_selected"] = True

        if st.session_state.app_state.get("apt1_selected") and st.session_state.app_state.get("apt2_selected"):
            if st.button("분석 실행", type="primary"):
                try:
                    # Step 1: naver_apt_v5를 통한 데이터 수집
                    with st.spinner("Step 1: 데이터 수집 중...💾"):
                        from src.naver_apt_v5 import main_function as run_01
                        run_01(selected_complexes)
                    st.success("Step 1 완료: 데이터 수집 완료")

                    # Step 2: sell_price_merge_v2를 통한 데이터 병합
                    with st.spinner("Step 2: 데이터 처리 중...⚙"):
                        from src.sell_price_merge_v2 import main as run_03
                        run_03(selected_complexes)
                    st.success("Step 2 완료: 데이터 병합 완료")

                    if not os.path.exists(output_path):
                        raise FileNotFoundError("결과 파일(result.csv)이 생성되지 않았습니다.")

                    st.session_state.app_state["analysis_done"] = True
                    st.session_state.app_state["error"] = None
                    st.session_state.app_state["last_analysis_time"] = datetime.now()
                    st.success("분석이 완료되었습니다!")
                except Exception as e:
                    st.session_state.app_state["analysis_done"] = False
                    st.session_state.app_state["error"] = str(e)
                    st.error(f"분석 중 오류 발생: {e}")

    if st.session_state.app_state.get("analysis_done") and selected_complexes:
        try:
            # 파일 존재 확인
            if not os.path.exists(output_path):
                st.error(f"결과 파일이 없습니다: {output_path}")
                st.stop()
                
            df_filtered = pd.read_csv(output_path, encoding='utf-8-sig')
                
            df_filtered["complexNo"] = df_filtered["complexNo"].astype(str)
            df_filtered = df_filtered[df_filtered["complexNo"].isin(selected_complexes)]
            
            if df_filtered.empty:
                st.warning("선택된 단지에 대한 데이터가 없습니다")
                st.stop()
                
        except Exception as e:
            st.error(f"데이터 로드 중 오류 발생: {e}")

    return selected_complexes, df_filtered

def render_apt_selection(prefix: str, region_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """아파트 선택 UI 컴포넌트"""
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
    # multiselect를 selectbox로 변경
    selected_pyeong = st.sidebar.selectbox(
        f"아파트{prefix} 평형 선택",
        [""] + pyeong_options,  # 빈 문자열을 추가하여 선택 해제 가능
        key=f"pyeong_{prefix}"
    )
    # 단일 값으로 저장 (리스트가 아님)
    st.session_state.app_state[f"apt{prefix}_pyeong"] = selected_pyeong if selected_pyeong else None
    return str(complex_options[selected_apt]), selected_apt

def render_visualization(selected_complexes: List[str], df_filtered: pd.DataFrame):
    """메인 시각화 컴포넌트"""
    try:
        df_real = pd.read_csv(real_price_path, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"price_data.csv 파일을 로드하는 중 오류 발생: {e}")
        return

    try:
        # 데이터 타입 변환 및 필터링 로직
        df_real["complexNo"] = df_real["complexNo"].astype(str)
        df_real["pyeongName3"] = df_real["pyeongName3"].astype(str)
        df_filtered["complexNo"] = df_filtered["complexNo"].astype(str)
        df_filtered["pyeongName3"] = df_filtered["pyeongName3"].astype(str)

        # 각 아파트의 선택된 평형과 단지 ID 가져오기
        selected_pyeong_apt1 = st.session_state.app_state.get("apt1_pyeong", None)
        selected_pyeong_apt2 = st.session_state.app_state.get("apt2_pyeong", None)
        apt1_complex = st.session_state.app_state.get("apt1_complex", None)
        apt2_complex = st.session_state.app_state.get("apt2_complex", None)

        # 필터링된 데이터프레임 리스트 초기화
        df_filtered_list = []
        df_real_filtered_list = []

        # 아파트1 필터링
        if apt1_complex and selected_pyeong_apt1:  # selected_pyeong_apt1이 None이 아닌 경우
            df_filtered_list.append(
                df_filtered[
                    (df_filtered["complexNo"] == apt1_complex) &
                    (df_filtered["pyeongName3"] == selected_pyeong_apt1)  # == 사용
                ]
            )
            df_real_filtered_list.append(
                df_real[
                    (df_real["complexNo"] == apt1_complex) &
                    (df_real["pyeongName3"] == selected_pyeong_apt1)  # == 사용
                ]
            )

        # 아파트2 필터링
        if apt2_complex and selected_pyeong_apt2:  # selected_pyeong_apt2가 None이 아닌 경우
            df_filtered_list.append(
                df_filtered[
                    (df_filtered["complexNo"] == apt2_complex) &
                    (df_filtered["pyeongName3"] == selected_pyeong_apt2)  # == 사용
                ]
            )
            df_real_filtered_list.append(
                df_real[
                    (df_real["complexNo"] == apt2_complex) &
                    (df_real["pyeongName3"] == selected_pyeong_apt2)  # == 사용
                ]
            )

        # 필터링된 결과 합치기
        df_filtered = pd.concat(df_filtered_list, ignore_index=True) if df_filtered_list else pd.DataFrame()
        df_real_filtered = pd.concat(df_real_filtered_list, ignore_index=True) if df_real_filtered_list else pd.DataFrame()

        # 데이터가 없는 경우 예외 처리
        if df_real_filtered.empty:
            st.warning("선택된 아파트-평형 쌍에 해당하는 데이터가 없습니다.")
            df_real_filtered = df_real[df_real["complexNo"].isin(selected_complexes)].copy()
            df_filtered = df_filtered[df_filtered["complexNo"].isin(selected_complexes)].copy()

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return

    # 갭 지수 계산을 여기서 먼저 수행
    gap_index = None
    gap_grade = None
    gap_guide = None
    
    # 두 아파트의 월별 평균 실거래가 격차 계산
    if df_real_filtered is not None and not df_real_filtered.empty:
        df_rp = df_real_filtered[df_real_filtered["dealDateClass"].isin([5, 3, 1])].copy()
        if not df_rp.empty:
            # 기존 계산 로직
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

                # 피벗 테이블 형태로 변환
                df_gap = df_monthly.pivot(
                    index='year_month',
                    columns='color_label',
                    values='dealAmount_eok'
                ).reset_index()
                
                # 각 아파트별로 직전 실거래가를 forward/backward fill로 채움
                df_gap[unique_labels[0]] = df_gap[unique_labels[0]].ffill().bfill()
                df_gap[unique_labels[1]] = df_gap[unique_labels[1]].ffill().bfill()
                
                if not df_gap.empty:
                    df_gap['price_gap'] = abs(df_gap[unique_labels[0]] - df_gap[unique_labels[1]])
                    df_gap['is_estimated'] = df_gap[unique_labels[0]].isna() | df_gap[unique_labels[1]].isna()
                    
                    # 실제 데이터에서 최대/최소 갭
                    real_gaps = df_gap.loc[~df_gap['is_estimated'], 'price_gap']
                    if not real_gaps.empty:
                        max_real_gap = real_gaps.max()
                        min_real_gap = real_gaps.min()
                        latest_gap = df_gap['price_gap'].iloc[-1]
                        
                        # 갭 지수 계산
                        if (max_real_gap - min_real_gap) > 0:
                            gap_index = ((1-(max_real_gap - latest_gap) / (max_real_gap - min_real_gap)) * 100)
                            gap_grade, gap_guide = get_buy_recommendation(gap_index)

    # 기본 정보 테이블 렌더링
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

    # 투자 지표 요약 섹션 (HTML 테이블로 수정)
    st.subheader("📌 투자 지표 요약")

    # 먼저, 커스텀 툴팁용 CSS를 삽입합니다.
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
        background: rgba(85, 85, 85, 0.7); /* #555 대신 90% 불투명으로 설정 */
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
            # 매매 데이터만 필터링
            df_metrics = df_filtered[df_filtered["tradeTypeName"] == "매매"].copy()
            if not df_metrics.empty:
                # bubble_score가 있는지 확인
                if 'bubble_score' not in df_metrics.columns:
                    st.error("bubble_score 컬럼이 df_metrics에 없습니다. 데이터 파일을 확인하세요.")
                    df_metrics['bubble_score'] = 50  # 기본값 설정

                # 아파트-평형별로 그룹화하여 bubble_score의 중위값 계산
                df_bubble = df_metrics.groupby(['complexNo', 'complexName', 'pyeongName3'])['bubble_score'].median().reset_index()
                df_bubble = df_bubble.groupby('complexName').agg({
                    'bubble_score': 'mean',
                    'pyeongName3': 'first'  # 평형 정보 추가
                }).reset_index()

                # 다중 줄 툴팁 텍스트 (줄바꿈은 \n 사용)
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

                # HTML 테이블 생성
                html_table = "<table style='border-collapse: collapse; width: 100%;'>"
                
                # 헤더 행 (전체 열 영역에 data-tooltip 적용)
                html_table += "<tr style='background-color: #f0f2f6; font-weight: bold; text-align: center;'>"
                html_table += "<th style='border: 1px solid #e0e0e0; padding: 8px; width: 34%;'>아파트</th>"
                html_table += f"<th style='border: 1px solid #e0e0e0; padding: 8px; width: 33%;' data-tooltip='{gap_tooltip_text}'>갭 지수</th>"
                html_table += f"<th style='border: 1px solid #e0e0e0; padding: 8px; width: 33%;' data-tooltip='{bubble_tooltip_text}'>버블 지수</th>"
                html_table += "</tr>"

                # 데이터 행 (두 개의 단지 행; 갭 지수는 두 행에 걸쳐 병합)
                if len(df_bubble) >= 2:  # 최소 두 개의 단지가 필요
                    # 첫 번째 단지
                    row1 = df_bubble.iloc[0]
                    bubble_score1 = int(round(row1['bubble_score'], 0))
                    bubble_grade1, bubble_guide1 = get_bubble_grade(bubble_score1)
                    bubble_cell1 = f"{bubble_score1}점 ({bubble_grade1})<br><span style='color: gray; font-size: 0.9em;'>{bubble_guide1}</span>"

                    # 두 번째 단지
                    row2 = df_bubble.iloc[1]
                    bubble_score2 = int(round(row2['bubble_score'], 0))
                    bubble_grade2, bubble_guide2 = get_bubble_grade(bubble_score2)
                    bubble_cell2 = f"{bubble_score2}점 ({bubble_grade2})<br><span style='color: gray; font-size: 0.9em;'>{bubble_guide2}</span>"

                    # 갭 지수 정보 (두 행에 걸쳐 표시)
                    if gap_index is not None:
                        gap_index_int = int(round(gap_index, 0))  # 소수점 제거 및 정수 변환
                        gap_grade, gap_guide = get_buy_recommendation(gap_index_int)
                        gap_cell = f"{gap_index_int}점 ({gap_grade})<br><span style='color: gray; font-size: 0.9em;'>{gap_guide}</span>"
                    else:
                        gap_cell = "-"

                    # 첫 번째 행 (아파트명 + 평형, 갭 지수(병합), 버블 지수)
                    html_table += "<tr style='text-align: center;'>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;'>{row1['complexName']}<br>{row1['pyeongName3']}평</td>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;' rowspan='2'>{gap_cell}</td>"
                    html_table += f"<td style='border: 1px solid #e0e0e0; padding: 8px;'>{bubble_cell1}</td>"
                    html_table += "</tr>"

                    # 두 번째 행 (아파트명 + 평형, 버블 지수)
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

    # 실거래가 추이 그래프 렌더링
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

            # 두 아파트의 월별 평균 실거래가 격차 계산
            if len(unique_labels) == 2:
                # 피벗 테이블 형태로 변환
                df_gap = df_monthly.pivot(
                    index='year_month',
                    columns='color_label',
                    values='dealAmount_eok'
                ).reset_index()
                
                # 각 아파트별로 직전 실거래가를 forward/backward fill로 채움
                df_gap[unique_labels[0]] = (
                    df_gap[unique_labels[0]]
                    .ffill()
                    .bfill()
                )
                df_gap[unique_labels[1]] = (
                    df_gap[unique_labels[1]]
                    .ffill()
                    .bfill()
                )
                
                if not df_gap.empty:
                    # 실거래가 격차 계산 (절대값)
                    df_gap['price_gap'] = abs(df_gap[unique_labels[0]] - df_gap[unique_labels[1]])
                    # 툴팁용 날짜 포맷
                    df_gap['tooltip_date'] = df_gap['year_month'].dt.strftime("'%y.%m월")
                    # 값이 채워진 것인지 표시
                    df_gap['is_filled_0'] = df_gap[unique_labels[0]].ne(df_gap[unique_labels[0]].shift())
                    df_gap['is_filled_1'] = df_gap[unique_labels[1]].ne(df_gap[unique_labels[1]].shift())
                    df_gap['is_estimated'] = (~df_gap['is_filled_0']) | (~df_gap['is_filled_1'])

            fig_line = go.Figure()
            fig_line.update_layout(hovermode="closest")

            # 실제 데이터와 추정치 데이터 처리 전에 갭 지수 계산
            if len(unique_labels) == 2 and not df_gap.empty:
                # 실제 데이터에서 최대/최소 갭
                real_gaps = df_gap.loc[~df_gap['is_estimated'], 'price_gap']
                max_real_gap = real_gaps.max()
                min_real_gap = real_gaps.min()
                # 가장 최근 갭 (추정치 포함)
                latest_gap = df_gap['price_gap'].iloc[-1]
                
                # 갭 지수 계산 ((1-(최대갭-최신갭)/(최대갭-최소갭))×100)
                gap_index = ((1-(max_real_gap - latest_gap) / (max_real_gap - min_real_gap)) * 100) if (max_real_gap - min_real_gap) > 0 else 0
                gap_grade, gap_guide = get_buy_recommendation(gap_index)

                mask_real = ~df_gap['is_estimated']
                mask_estimated = df_gap['is_estimated']

                # Bar 차트 추가 (이전 코드와 동일)
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
                    x=0.01,  # 왼쪽 여백에서의 위치
                    y=1.15,  # 그래프 위쪽으로 이동
                    orientation='h'  # 범례를 가로로 배열
                ),
                legend_title="",
                margin=dict(l=20, r=20, t=40, b=10),  # 상단 여백 증가
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

    # 매물 현황 플롯차트 렌더링 (실거래가표와 매물 리스트표 사이)
    st.subheader("📊 매물 현황")
    if not df_filtered[df_filtered["tradeTypeName"] == "매매"].empty:
        df_for_range = df_filtered[df_filtered["tradeTypeName"] == "매매"].copy()
        def draw_range_plot(df: pd.DataFrame):
            group_cols = ["complexName", "pyeongName3"]
            agg_dict = {
                "pyeong_max_5": "first",
                "pyeong_min_5": "first",
                "latestdealAmount": "first",
                "latestdealDate": "first",
                "pyeong_max_5_DT": "first",
                "pyeong_min_5_DT": "first",
                "latestdealFloor": "first",
            }
            df_group = df.groupby(group_cols, as_index=False).agg(agg_dict)
            df_group["max_val"] = df_group["pyeong_max_5"].apply(to_number) / 10000
            df_group["min_val"] = df_group["pyeong_min_5"].apply(to_number) / 10000
            df_group["latestdealAmount"] = df_group["latestdealAmount"].apply(to_number)
            df_group["star_val"] = df_group["latestdealAmount"].apply(to_number) / 10000
            df_group.sort_values(by=["complexName", "pyeongName3"], inplace=True)
            combos = list(df_group[["complexName", "pyeongName3"]].itertuples(index=False, name=None))
            x_mapping = {}
            current_x = 0
            last_apt = None
            apt_boundaries = []
            for (apt, pnum) in combos:
                if last_apt is not None and apt != last_apt:
                    apt_boundaries.append(current_x - 0.5)
                x_mapping[(apt, pnum)] = current_x
                current_x += 1
                last_apt = apt
            fig = go.Figure()
            for (apt, pnum) in combos:
                x_val = x_mapping[(apt, pnum)]
                row_g = df_group[(df_group["complexName"] == apt) & (df_group["pyeongName3"] == pnum)].iloc[0]
                minv = row_g["min_val"]
                maxv = row_g["max_val"]
                starv = row_g["star_val"]
                star_date = row_g["latestdealDate"]
                max_date_str = format_date(row_g["pyeong_max_5_DT"])
                min_date_str = format_date(row_g["pyeong_min_5_DT"])
                max_str = f"{format_eokwan(row_g['pyeong_max_5'])}({max_date_str})" if max_date_str != "-" else format_eokwan(row_g["pyeong_max_5"])
                min_str = f"{format_eokwan(row_g['pyeong_min_5'])}({min_date_str})" if min_date_str != "-" else format_eokwan(row_g["pyeong_min_5"])
                count_points = 20
                yvals = np.linspace(minv, maxv, count_points)
                xvals = [x_val]*count_points
                custom_line = [[max_str, min_str]]*count_points
                range_hover = (
                    "최근 5년 전고점 : %{customdata[0]}<br>"
                    "최근 5년 전저점 : %{customdata[1]}<extra></extra>"
                )
                fig.add_trace(go.Scatter(
                    x=xvals,
                    y=yvals,
                    mode="lines",
                    line=dict(color="blue", width=1),
                    customdata=custom_line,
                    hovertemplate=range_hover,
                    showlegend=False
                ))
                top_points = 5
                xvals_top = np.linspace(x_val-0.1, x_val+0.1, top_points)
                yvals_top = [maxv]*top_points
                top_data = [[max_str]]*top_points
                fig.add_trace(go.Scatter(
                    x=xvals_top,
                    y=yvals_top,
                    mode="lines",
                    line=dict(color="blue", width=1),
                    customdata=top_data,
                    hovertemplate="최근 5년 전고점 : %{customdata[0]}<extra></extra>",
                    showlegend=False
                ))
                bot_points = 5
                xvals_bot = np.linspace(x_val-0.1, x_val+0.1, bot_points)
                yvals_bot = [minv]*bot_points
                bot_data = [[min_str]]*bot_points
                fig.add_trace(go.Scatter(
                    x=xvals_bot,
                    y=yvals_bot,
                    mode="lines",
                    line=dict(color="blue", width=1),
                    customdata=bot_data,
                    hovertemplate="최근 5년 전저점 : %{customdata[0]}<extra></extra>",
                    showlegend=False
                ))
                df_points = df[(df["complexName"] == apt) & (df["pyeongName3"] == pnum)].copy()
                if not df_points.empty:
                    df_points["price_val"] = df_points["dealOrWarrantPrc2"].apply(to_number) / 10000
                    df_points["gap_html"] = df_points["real_max_5_gap"].apply(color_gap_html)
                    df_points["tooltip"] = df_points.apply(
                        lambda r: [
                            str(r["pyeongName"]),
                            str(r["floorInfo"]),
                            str(r["dealOrWarrantPrc"]),
                            r["gap_html"]
                        ],
                        axis=1
                    )
                    point_hover = (
                        "평형타입: %{customdata[0]}<br>"
                        "층수: %{customdata[1]}<br>"
                        "호가: %{customdata[2]}<br>"
                        "전고점 갭: %{customdata[3]}<extra></extra>"
                    )
                    fig.add_trace(go.Scatter(
                        x=[x_val]*len(df_points),
                        y=df_points["price_val"],
                        mode="markers",
                        marker=dict(size=8, color="red", opacity=0.3),
                        hovertemplate=point_hover,
                        customdata=df_points["tooltip"].tolist(),
                        showlegend=False
                    ))
                if not pd.isnull(starv) and starv > 0:
                    star_date_str = format_date(star_date)
                    star_val_str = format_eokwan(row_g["latestdealAmount"])
                    latestdealFloor = row_g["latestdealFloor"]
                    floor_str = f"({int(latestdealFloor)}층)" if pd.notnull(latestdealFloor) and str(latestdealFloor).strip() != "" else ""
                    label_text = f"최신 실거래가<br>{star_val_str}{floor_str}<br>{star_date_str}"
                    fig.add_trace(go.Scatter(
                        x=[x_val],
                        y=[starv],
                        mode="markers+text",
                        text=[label_text],
                        texttemplate="%{text}",
                        textposition="middle right",
                        textfont=dict(color="black", size=11),
                        marker_symbol="star",
                        marker_size=15,
                        marker_color="yellow",
                        marker_line_color="black",
                        marker_line_width=1,
                        opacity=1.0,
                        hoverinfo="none",
                        showlegend=False
                    ))
            shapes = []
            for boundary_x in apt_boundaries:
                shapes.append(dict(
                    type="line",
                    xref="x", yref="paper",
                    x0=boundary_x, x1=boundary_x,
                    y0=0, y1=1,
                    line=dict(color="gray", dash="dot")
                ))
            fig.update_layout(shapes=shapes)
            x_vals = [x_mapping[c] for c in combos]
            x_text = [f"{apt} {pnum}평" for (apt, pnum) in combos]
            fig.update_xaxes(
                range=[-0.5, len(combos)-0.5],
                tickmode="array",
                tickvals=x_vals,
                ticktext=x_text
            )
            fig.update_yaxes(
                ticksuffix="억",
                zeroline=True
            )
            fig.update_layout(
                hovermode="closest",
                margin=dict(l=10, r=10, t=10, b=10),
                autosize=True,
                height=500
            )
            return fig
        fig_range = draw_range_plot(df_for_range)
        st.plotly_chart(fig_range, use_container_width=True)
    
    # 매물 리스트 렌더링 (기존 코드와 동일)
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
        
            # 컬럼 순서 수정
            final_cols_list = [
                "아파트명", "거래유형", "층수", "호가", "평형타입",
                "공급면적(㎡)", "전용면적(㎡)", "방향", "동",
                "매물등록일", "동일매물등록수", "동일타입세대수", "동일타입매물수",
                "동일타입매물등록률", "실거래가 전고점 갭", "실거래가 전저점 갭",
                "KB시세(상위평균)", "KB시세(일반평균)", "KB시세(하위평균)", "KB시세 전세가율",
                "상세 설명", "중개사무소", "매물 링크"
            ]
            df_show_list = df_for_list[final_cols_list].copy()
        
            styler = df_show_list.style.map(style_gap, subset=["실거래가 전고점 갭", "실거래가 전저점 갭"])
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