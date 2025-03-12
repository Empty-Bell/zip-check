import pandas as pd
import numpy as np
import re

# 하드코딩된 경로를 config.py의 DATA_PATHS 사용하도록 수정
from src.config import DATA_PATHS

# 파일 경로 설정 부분 수정
sell_data_path = DATA_PATHS["SELL"]
real_price_path = DATA_PATHS["REAL_PRICE"]
complex_data_path = DATA_PATHS["COMPLEX"]
output_path = DATA_PATHS["RESULT"]

def main(complex_ids=None):
    """선택된 아파트 단지들의 매물과 실거래가 데이터를 병합하여 통계 계산"""
    if complex_ids is None:
        complex_ids = []

    try:
        # ========================
        # 2. 데이터 로드
        # ========================
        print("Loading sell_data.csv...")
        df_sell = pd.read_csv(sell_data_path, encoding='utf-8')
        print(f"sell_data.csv shape: {df_sell.shape}")
        print("Loading price_data.csv...")
        df_real = pd.read_csv(real_price_path, encoding='utf-8')
        print(f"price_data.csv shape: {df_real.shape}")

        # 선택된 단지만 필터링
        if complex_ids:
            df_sell['complexNo'] = df_sell['complexNo'].astype(str)
            df_real['complexNo'] = df_real['complexNo'].astype(str)
            df_sell = df_sell[df_sell['complexNo'].isin(complex_ids)]
            df_real = df_real[df_real['complexNo'].isin(complex_ids)]
            print(f"Filtered df_sell shape: {df_sell.shape}")
            print(f"Filtered df_real shape: {df_real.shape}")
            if df_sell.empty or df_real.empty:
                print("선택된 단지의 데이터가 없습니다.")
                return

        # ------------------------
        # 2-1. 문자열 전처리 및 파생변수 생성
        # ------------------------
        # pyeongName → pyeongName3 (예: '33F' → '33')
        def extract_pyeong(pyeong):
            if isinstance(pyeong, str):
                num_str = re.sub(r'[A-Za-z]+$', '', pyeong)  # 영문 제거
                return num_str if num_str else np.nan
            return str(pyeong) if pd.notnull(pyeong) else np.nan

        df_sell['pyeongName3'] = df_sell['pyeongName'].apply(extract_pyeong)
        df_real['pyeongName3'] = df_real['pyeongName3'].astype(str)  # 실거래와 일치

        # buildingName → buildingName2 (예: '101동' → 101)
        def extract_building_number(bname):
            if isinstance(bname, str):
                bname = bname.strip()
                num_str = bname[:-1] if bname.endswith("동") else bname
                try:
                    return int(num_str)
                except Exception:
                    return np.nan
            return bname

        df_sell['buildingName2'] = df_sell['buildingName'].apply(extract_building_number)

        # 문자열 컬럼 공백 제거
        df_sell['pyeongName'] = df_sell['pyeongName'].astype(str).str.strip()
        df_real['pyeongName2'] = df_real['pyeongName2'].astype(str).str.strip()

        # ------------------------
        # 2-2. 기타 형변환
        # ------------------------
        def convert_deal_price(price_str):
            if not isinstance(price_str, str):
                return np.nan
            price_str = price_str.strip()
            try:
                if '억' in price_str:
                    parts = price_str.split('억')
                    billion_part = int(parts[0].strip()) * 10000
                    if len(parts) > 1 and parts[1].strip():
                        thousand_part = int(parts[1].strip())
                        return billion_part + thousand_part
                    return billion_part
                else:
                    return int(price_str.replace(',', ''))
            except (ValueError, IndexError):
                return np.nan

        df_sell['dealOrWarrantPrc2'] = df_sell['dealOrWarrantPrc'].apply(convert_deal_price)

        # ========================
        # 3. 미리 계산할 열 생성
        # ========================
        df_real['dealAmount_numeric'] = pd.to_numeric(df_real['dealAmount'].astype(str).str.replace(',', ''), errors='coerce')
        df_real['dealDateClass_numeric'] = pd.to_numeric(df_real['dealDateClass'], errors='coerce')

        # ========================
        # 4. 통계 계산에 사용할 allowed 리스트 설정
        # ========================
        allowed_5 = [5, 3, 1]  # 최근 5년
        allowed_3 = [3, 1]     # 최근 3년
        allowed_1 = [1]        # 최근 1년

        # ========================
        # 5. 통계 계산 함수 정의
        # ========================
        def filter_by_dealDateClass(matched, allowed):
            return matched[matched['dealDateClass_numeric'].isin(allowed)]

        def compute_stats_pyeong(row, allowed, label):
            comp_no = row['complexNo']
            pyeong_val = row['pyeongName3']
            matched = df_real[(df_real['complexNo'] == comp_no) & (df_real['pyeongName3'] == pyeong_val)]
            filtered = filter_by_dealDateClass(matched, allowed)
            if filtered.empty:
                return pd.Series({
                    f'pyeong_max_{label}': np.nan, f'pyeong_max_{label}_DT': np.nan,
                    f'pyeong_avg_{label}': np.nan, f'pyeong_med_{label}': np.nan,  # 중위값 추가
                    f'pyeong_min_{label}': np.nan, f'pyeong_min_{label}_DT': np.nan
                })
            max_idx = filtered['dealAmount_numeric'].idxmax()
            max_price = filtered.loc[max_idx, 'dealAmount_numeric']
            max_date = filtered.loc[max_idx, 'dealDate'] if pd.notnull(max_price) else np.nan

            min_idx = filtered['dealAmount_numeric'].idxmin()
            min_price = filtered.loc[min_idx, 'dealAmount_numeric']
            min_date = filtered.loc[min_idx, 'dealDate'] if pd.notnull(min_price) else np.nan

            return pd.Series({
                f'pyeong_max_{label}': max_price, f'pyeong_max_{label}_DT': max_date,
                f'pyeong_avg_{label}': filtered['dealAmount_numeric'].mean(),
                f'pyeong_med_{label}': filtered['dealAmount_numeric'].median(),  # 중위값 추가
                f'pyeong_min_{label}': min_price, f'pyeong_min_{label}_DT': min_date
            })

        def compute_stats_pyeongtype(row, allowed, label):
            comp_no = row['complexNo']
            pyeong_val = row['pyeongName']
            matched = df_real[(df_real['complexNo'] == comp_no) & (df_real['pyeongName2'] == pyeong_val)]
            filtered = filter_by_dealDateClass(matched, allowed)
            if filtered.empty:
                return pd.Series({f'pyeongtype_max_{label}': np.nan, f'pyeongtype_avg_{label}': np.nan, f'pyeongtype_min_{label}': np.nan})
            return pd.Series({
                f'pyeongtype_max_{label}': filtered['dealAmount_numeric'].max(),
                f'pyeongtype_avg_{label}': filtered['dealAmount_numeric'].mean(),
                f'pyeongtype_min_{label}': filtered['dealAmount_numeric'].min()
            })

        # ========================
        # 6. 통계 계산
        # ========================
        print("Calculating statistics...")
        stats_pyeong_5 = df_sell.apply(lambda row: compute_stats_pyeong(row, allowed_5, 5), axis=1)
        stats_pyeong_3 = df_sell.apply(lambda row: compute_stats_pyeong(row, allowed_3, 3), axis=1)
        stats_pyeong_1 = df_sell.apply(lambda row: compute_stats_pyeong(row, allowed_1, 1), axis=1)

        stats_pyeongtype_5 = df_sell.apply(lambda row: compute_stats_pyeongtype(row, allowed_5, 5), axis=1)
        stats_pyeongtype_3 = df_sell.apply(lambda row: compute_stats_pyeongtype(row, allowed_3, 3), axis=1)
        stats_pyeongtype_1 = df_sell.apply(lambda row: compute_stats_pyeongtype(row, allowed_1, 1), axis=1)

        # 병합
        df_sell = pd.concat([
            df_sell, 
            stats_pyeong_5, stats_pyeong_3, stats_pyeong_1,
            stats_pyeongtype_5, stats_pyeongtype_3, stats_pyeongtype_1
        ], axis=1)

        # ========================
        # 7. complex_data.csv 병합
        # ========================
        print("Merging with complex_data.csv...")
        df_complex = pd.read_csv(complex_data_path, encoding='utf-8')
        df_complex['complexNo'] = df_complex['complexNo'].astype(str)
        columns_to_map = [
            "totalHouseholdCount", "totalLeaseHouseholdCount", "permanentLeaseHouseholdCount",
            "nationLeaseHouseholdCount", "civilLeaseHouseholdCount", "publicLeaseHouseholdCount",
            "longTermLeaseHouseholdCount", "etcLeaseHouseholdCount", "highFloor", "lowFloor",
            "useApproveYmd", "totalDongCount", "maxSupplyArea", "minSupplyArea", "dealCount",
            "rentCount", "leaseCount", "shortTermRentCount", "batlRatio", "btlRatio",
            "parkingPossibleCount", "parkingCountByHousehold", "constructionCompanyName",
            "pyoengNames", "매매매물출현율", "전세매물출현율", "월세매물출현율", "schoolName", "walkTime"
        ]
        df_sell = pd.merge(df_sell, df_complex[['complexNo'] + columns_to_map],
                          on='complexNo', how='left')

        # ========================
        # 8. 최신 거래 데이터 매핑
        # ========================
        print("Mapping latest deal data...")
        df_real['dealDate_dt'] = pd.to_datetime(df_real['dealDate'], errors='coerce')
        latest_idx = df_real.groupby(['complexNo', 'pyeongName3'])['dealDate_dt'].idxmax()
        df_latest = df_real.loc[latest_idx, ['complexNo', 'pyeongName3', 'dealDate', 'dealAmount', 'floor']].rename(
            columns={'dealDate': 'latestdealDate', 'dealAmount': 'latestdealAmount', 'floor': 'latestdealFloor'}
        )
        df_sell = pd.merge(df_sell, df_latest, on=['complexNo', 'pyeongName3'], how='left')
        print(f"After merging latest deal data, df_sell shape: {df_sell.shape}")

        # complex_data.csv 병합 후, 매물 중위값 계산 및 매핑 추가
        print("Calculating selling price statistics...")
        
        # 매물별 실거래 중위값 계산
        real_stats = df_real.groupby(['complexNo', 'pyeongName3']).agg({
            'dealAmount_numeric': 'median'  # 실거래 중위값
        }).reset_index()
        real_stats.columns = ['complexNo', 'pyeongName3', 'real_price_median']

        # 통계값들을 원본 데이터프레임에 매핑
        df_sell = pd.merge(
            df_sell,
            real_stats,
            on=['complexNo', 'pyeongName3'],
            how='left'
        )

        # bubble_score 계산
        print("Computing bubble scores...")
        # 매매 데이터만 필터링
        mask = df_sell['tradeTypeName'] == '매매'
        df_sell['bubble_score'] = np.nan

        # Case 1: dealOrWarrantPrc2 <= real_price_median
        mask_case1 = mask & (df_sell['dealOrWarrantPrc2'] <= df_sell['real_price_median'])
        case1_scores = (
            (df_sell.loc[mask_case1, 'dealOrWarrantPrc2'] - df_sell.loc[mask_case1, 'pyeong_min_5']) /
            (df_sell.loc[mask_case1, 'real_price_median'] - df_sell.loc[mask_case1, 'pyeong_min_5'])
        ) * 50
        df_sell.loc[mask_case1, 'bubble_score'] = np.maximum(case1_scores, 0)  # 음수는 0으로 처리

        # Case 2: dealOrWarrantPrc2 > real_price_median
        mask_case2 = mask & (df_sell['dealOrWarrantPrc2'] > df_sell['real_price_median'])
        case2_scores = 50 + (
            (df_sell.loc[mask_case2, 'dealOrWarrantPrc2'] - df_sell.loc[mask_case2, 'real_price_median']) /
            (df_sell.loc[mask_case2, 'pyeong_max_5'] - df_sell.loc[mask_case2, 'real_price_median'])
        ) * 50
        df_sell.loc[mask_case2, 'bubble_score'] = np.maximum(case2_scores, 0)  # 음수는 0으로 처리

        # ========================
        # 9. 계산된 값 추가 (매매만)
        print("Computing gaps...")
        mask = df_sell['tradeTypeName'] == '매매'
        df_sell['real_max_5_gap'] = ''
        df_sell['real_min_5_gap'] = ''
        df_sell['kb_upper_gap'] = ''
        df_sell['deal_min_gap'] = ''
        df_sell.loc[mask, 'real_max_5_gap'] = (
            (df_sell.loc[mask, 'dealOrWarrantPrc2'] / df_sell.loc[mask, 'pyeong_max_5']) - 1
        ) * 100
        df_sell.loc[mask, 'real_max_5_gap'] = df_sell.loc[mask, 'real_max_5_gap'].round(1).astype(str) + '%'
        df_sell.loc[mask, 'real_min_5_gap'] = (
            (df_sell.loc[mask, 'dealOrWarrantPrc2'] / df_sell.loc[mask, 'pyeong_min_5']) - 1
        ) * 100
        df_sell.loc[mask, 'real_min_5_gap'] = df_sell.loc[mask, 'real_min_5_gap'].round(1).astype(str) + '%'
        df_sell.loc[mask, 'kb_upper_gap'] = (
            (df_sell.loc[mask, 'dealOrWarrantPrc2'] / df_sell.loc[mask, 'dealUpperPriceLimit']) - 1
        ) * 100
        df_sell.loc[mask, 'kb_upper_gap'] = df_sell.loc[mask, 'kb_upper_gap'].round(1).astype(str) + '%'
        df_sell.loc[mask, 'deal_min_gap'] = (
            (df_sell.loc[mask, 'dealOrWarrantPrc2'] / df_sell.loc[mask, 'dealPriceMin2']) - 1
        ) * 100
        df_sell.loc[mask, 'deal_min_gap'] = df_sell.loc[mask, 'deal_min_gap'].round(1).astype(str) + '%'

        # ========================
        # 10. 결과 저장
        # ========================
        print(f"Saving to {output_path}...")
        df_sell.to_csv(output_path, index=False, encoding='utf-8-sig')
        print("저장 완료")

    except Exception as e:
        print(f"sell_price_merge.py 실행 중 오류: {e}")

if __name__ == "__main__":
    main(complex_ids=['138183', '136913'])  # 테스트용