import os
from dotenv import load_dotenv
from datetime import datetime
import requests
import csv
import copy
import math
import re
from src.config import DATA_PATHS, DATA_DIR

# .env 파일 로드
load_dotenv()

# -------------------------------
# 모든 산출물의 업데이트 날짜 (시간까지)
# -------------------------------
updated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -------------------------------
# 기본 설정 (쿠키, 헤더 등)
# -------------------------------
BASE_COOKIES = {
    'NNB': os.getenv('NNB'),
    'ASID': os.getenv('ASID'),
    'NAC': os.getenv('NAC'),
    'landHomeFlashUseYn': 'Y',
    '_ga': 'GA1.1.737295237.1698157835',
}

BASE_HEADERS = {
    'accept': '*/*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'authorization': os.getenv('AUTHORIZATION'),
    'user-agent': os.getenv('USER_AGENT'),
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# -------------------------------
# Sell 데이터 요청용 설정
# -------------------------------
SELL_COOKIES = {
    'NNB': os.getenv('NNB'),
    'ASID': os.getenv('ASID'),
    'NAC': os.getenv('NAC'),
    'landHomeFlashUseYn': 'Y',
    'REALESTATE': os.getenv('SELL_REALESTATE'),
    '_fwb': os.getenv('SELL_FWB'),
    'SHOW_FIN_BADGE': os.getenv('SELL_SHOW_FIN_BADGE'),
    '_ga_0ZGH3YC3W6': os.getenv('SELL_GA_0ZGH3YC3W6'),
    '_ga': os.getenv('SELL_GA'),
}

SELL_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-GB,en;q=0.9,ko-KR;q=0.8',
    'authorization': os.getenv('SELL_AUTHORIZATION'),
    'user-agent': os.getenv('USER_AGENT'),
    'referer': os.getenv('SELL_REFERER'),
}

# -------------------------------
# 학교 정보 요청용 설정
# -------------------------------
SCHOOL_COOKIES = {
    'NNB': os.getenv('NNB'),
    'ASID': os.getenv('ASID'),
    'NAC': os.getenv('NAC'),
    'landHomeFlashUseYn': 'Y',
    'page_uid': os.getenv('SCHOOL_PAGE_UID'),
    'REALESTATE': os.getenv('SCHOOL_REALESTATE'),
    'SRT30': os.getenv('SCHOOL_SRT30'),
    'SRT5': os.getenv('SCHOOL_SRT5'),
    'BUC': os.getenv('SCHOOL_BUC'),
}

SCHOOL_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-GB,en;q=0.9,ko-KR;q=0.8',
    'authorization': os.getenv('SCHOOL_AUTHORIZATION'),
    'user-agent': os.getenv('USER_AGENT'),
}

# -------------------------------
# 동 정보 요청용 설정
# -------------------------------
DONG_COOKIES = {
    'NNB': os.getenv('NNB'),
    'ASID': os.getenv('ASID'),
    'NAC': os.getenv('NAC'),
    'landHomeFlashUseYn': 'Y',
    'page_uid': os.getenv('DONG_PAGE_UID'),
    'REALESTATE': os.getenv('DONG_REALESTATE'),
    'SRT30': os.getenv('DONG_SRT30'),
    'SRT5': os.getenv('DONG_SRT5'),
    'BUC': os.getenv('DONG_BUC'),
}

DONG_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-GB,en;q=0.9,ko-KR;q=0.8',
    'authorization': os.getenv('DONG_AUTHORIZATION'),
    'user-agent': os.getenv('USER_AGENT'),
}

COMMON_PARAMS = {
    'tradeType': 'A1',
    'year': '5',
    'priceChartChange': 'false',
    'type': 'chart',
}

def fetch_json(url, params, cookies, headers):
    """URL에 GET 요청 후 JSON 데이터를 반환합니다."""
    try:
        resp = requests.get(url, params=params, cookies=cookies, headers=headers)
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception as e:
                print(f"JSON decode error at {url}: {resp.text}")
                raise e
        else:
            print(f"URL 요청 실패 (상태코드 {resp.status_code}): {url}")
    except Exception as e:
        print(f"URL 요청 중 예외 발생: {url}, 예외: {e}")
    return None

def write_csv(filename, header, rows):
    from src.config import DATA_PATHS, DATA_DIR
    
    # 수정: filename을 문자열로 변환 후 replace()
    file_key = str(filename).replace('.csv', '').upper()
    if file_key in DATA_PATHS:
        filepath = DATA_PATHS[file_key]
    else:
        filepath = DATA_DIR / filename

    # 디렉토리가 없으면 생성
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        header_with_updated = header + ["downloadDate"]
        writer.writerow(header_with_updated)
        for row in rows:
            writer.writerow(row + [updated_date])

def convert_price(value):
    """가격 문자열을 정수로 변환 (예: '13억 5000' -> 135000).
       빈 문자열이면 빈 문자열을 반환합니다."""
    value = value.strip()
    if not value:
        return ""
    try:
        value = "".join(value.split())
        value = value.replace(",", "")
        if "억" in value:
            parts = value.split("억")
            left_part = parts[0].strip()
            right_part = parts[1].strip() if len(parts) > 1 else ""
            left_val = float(left_part) if left_part else 0
            right_val = float(right_part) if right_part else 0
            return int(left_val * 10000 + right_val)
        else:
            return int(value.strip())
    except Exception as e:
        print(f"가격 변환 에러 ('{value}'): {e}")
        return ""

def get_floor_type(floor_info):
    """층 정보를 분석하여 층 유형을 반환합니다."""
    if not floor_info:
        return ""
    if floor_info.startswith("'"):
        floor_info = floor_info[1:]
    parts = floor_info.split("/")
    if len(parts) != 2:
        return ""
    current_str = parts[0].strip()
    mapping = {"저": "저층", "중": "중층", "고": "고층"}
    if current_str in mapping:
        return mapping[current_str]
    try:
        current_floor = int(current_str)
        max_floor = int(parts[1].strip())
        if current_floor == max_floor:
            return "탑층"
        elif current_floor == 1:
            return "1층"
        else:
            x = round(max_floor / 3)
            if current_floor <= x:
                return "저층"
            elif current_floor <= math.ceil(2 * x):
                return "중층"
            else:
                return "고층"
    except:
        return ""

def fetch_real_price_data(complex_no, pyeong_no, cookies, headers):
    """네이버 부동산 UI와 유사하게 실거래 데이터를 수집합니다."""
    base_url = f'https://new.land.naver.com/api/complexes/{complex_no}/prices/real'
    transactions = []
    collected_keys = set()

    def parse_transactions(resp):
        new_list = []
        for month_block in resp.get("realPriceOnMonthList", []):
            for t in month_block.get("realPriceList", []):
                key = (t.get("tradeYear"), t.get("tradeMonth"), t.get("tradeDate"), t.get("dealPrice"), t.get("floor"))
                if key not in collected_keys:
                    collected_keys.add(key)
                    new_list.append(t)
        return new_list

    params = {
        "complexNo": complex_no,
        "tradeType": "A1",
        "year": "5",
        "priceChartChange": "false",
        "areaNo": pyeong_no,
        "type": "table"
    }
    resp_json = fetch_json(base_url, params=params, cookies=cookies, headers=headers)
    if not resp_json:
        return []
    new_data = parse_transactions(resp_json)
    transactions.extend(new_data)
    prev_added = resp_json.get("addedRowCount", "")
    if not resp_json.get("realPriceOnMonthList", []):
        return transactions

    while prev_added and str(prev_added).strip():
        params["addedRowCount"] = str(prev_added)
        resp_json2 = fetch_json(base_url, params=params, cookies=cookies, headers=headers)
        if not resp_json2:
            break
        new_data2 = parse_transactions(resp_json2)
        if not new_data2:
            break
        transactions.extend(new_data2)
        new_added = resp_json2.get("addedRowCount", "")
        if not new_added or new_added == prev_added:
            break
        prev_added = new_added
    return transactions

def main_function(complex_ids=None):
    """매개변수로 받은 아파트 단지들의 데이터만 수집"""
    if complex_ids is None:
        complex_ids = [138183, 136913]  # 기본값 유지

    # -------------------------------
    # 데이터 저장용 리스트 생성
    # -------------------------------
    complex_data = []     # 단지 기본정보
    pyeong_data = []      # 평형(호) 정보
    price_data = []       # 차트용 가격 데이터
    provider_data = []    # 공급자별 가격 데이터

    # 단지 정보 필드
    complex_keys = [
        "complexNo", "complexName", "cortarNo", "realEstateTypeCode", "realEstateTypeName",
        "detailAddress", "roadAddress", "latitude", "longitude", "totalHouseholdCount",
        "totalLeaseHouseholdCount", "permanentLeaseHouseholdCount", "nationLeaseHouseholdCount",
        "civilLeaseHouseholdCount", "publicLeaseHouseholdCount", "longTermLeaseHouseholdCount",
        "etcLeaseHouseholdCount", "highFloor", "lowFloor", "useApproveYmd", "totalDongCount",
        "maxSupplyArea", "minSupplyArea", "dealCount", "rentCount", "leaseCount", "shortTermRentCount",
        "isBookmarked", "batlRatio", "btlRatio", "parkingPossibleCount", "parkingCountByHousehold",
        "constructionCompanyName", "heatMethodTypeCode", "heatFuelTypeCode", "pyoengNames",
        "address", "roadAddressPrefix", "roadZipCode"
    ]

    # 학교 정보 필드 (총 12개)
    school_keys = [
        "schoolName", "walkTime", "studentStatisticsBaseYmd", "studentCountPerTeacher",
        "studentCountPerClassroom", "maleStudentCount", "femaleStudentCount", "totalStudentCount",
        "averageStudentCountPerClassroomOnCity", "averageStudentCountPerTeacherOnCity",
        "averageStudentCountPerClassroomOnDivision", "averageStudentCountPerTeacherOnDivision"
    ]

    # -------------------------------
    # 단지별 데이터 처리
    # -------------------------------
    for complex_id in complex_ids:
        url_complex = f'https://new.land.naver.com/api/complexes/{complex_id}'
        complex_params = {"sameAddressGroup": "true"}
        data = fetch_json(url_complex, params=complex_params, cookies=BASE_COOKIES, headers=BASE_HEADERS)
        if data:
            complex_detail = data.get("complexDetail", {})
            uymd = complex_detail.get("useApproveYmd", "")
            if uymd and len(uymd) == 8:
                try:
                    uymd = datetime.strptime(uymd, "%Y%m%d").strftime("%Y-%m-%d")
                except:
                    pass
            complex_detail["useApproveYmd"] = uymd

            try:
                total_households = float(complex_detail.get("totalHouseholdCount", 0))
            except:
                total_households = 0
            try:
                deal_count = float(complex_detail.get("dealCount", 0))
            except:
                deal_count = 0
            try:
                rent_count = float(complex_detail.get("rentCount", 0))
            except:
                rent_count = 0
            try:
                lease_count = float(complex_detail.get("leaseCount", 0))
            except:
                lease_count = 0

            if total_households > 0:
                매매매물출현율 = f"{(deal_count / total_households) * 100:.1f}%"
                전세매물출현율 = f"{(rent_count / total_households) * 100:.1f}%"
                월세매물출현율 = f"{(lease_count / total_households) * 100:.1f}%"
            else:
                매매매물출현율 = ""
                전세매물출현율 = ""
                월세매물출현율 = ""

            pyoengNames = complex_detail.get("pyoengNames", "")
            if pyoengNames:
                parts = [p.strip() for p in pyoengNames.split(",")]
                if parts and not parts[-1].endswith("㎡"):
                    parts[-1] += "㎡"
                pyoengNames = ", ".join(parts)
            complex_detail["pyoengNames"] = pyoengNames

            # 학교 정보 요청
            school_url = f'https://new.land.naver.com/api/complexes/{complex_id}/schools'
            school_data = fetch_json(school_url, params={}, cookies=SCHOOL_COOKIES, headers=SCHOOL_HEADERS)
            if school_data and "schools" in school_data and len(school_data["schools"]) > 0:
                first_school = school_data["schools"][0]
                school_row = [first_school.get(k, "") for k in school_keys]
            else:
                school_row = ["" for _ in range(len(school_keys))]

            row = [complex_detail.get(k, "") for k in complex_keys]
            row.extend([매매매물출현율, 전세매물출현율, 월세매물출현율])
            row.extend(school_row)
            complex_data.append(row)

            # 평형(호) 데이터 처리
            for pyeong in data.get("complexPyeongDetailList", []):
                pyeong_no = pyeong.get("pyeongNo", "")
                stat = pyeong.get("articleStatistics", {})
                pyeong_data.append([
                    complex_id,
                    pyeong_no,
                    pyeong.get("supplyArea", ""),
                    pyeong.get("supplyPyeong", ""),
                    pyeong.get("pyeongName", ""),
                    pyeong.get("pyeongName2", ""),
                    pyeong.get("exclusiveArea", ""),
                    pyeong.get("exclusivePyeong", ""),
                    pyeong.get("exclusiveRate", ""),
                    pyeong.get("realEstateTypeCode", ""),
                    pyeong.get("householdCountByPyeong", ""),
                    stat.get("dealCount", ""),
                    stat.get("leaseCount", ""),
                    stat.get("rentCount", ""),
                    stat.get("shortTermRentCount", ""),
                    stat.get("dealPriceMin", ""),
                    stat.get("dealPriceMax", ""),
                    stat.get("dealPricePerSpaceMin", ""),
                    stat.get("dealPricePerSpaceMax", ""),
                    stat.get("dealPriceString", ""),
                    stat.get("dealPricePerSpaceString", ""),
                    stat.get("leasePriceString", ""),
                    stat.get("leasePricePerSpaceString", ""),
                    stat.get("leasePriceRateString", ""),
                    stat.get("rentPriceString", ""),
                    stat.get("rentDepositPriceMin", ""),
                    stat.get("rentPriceMin", ""),
                    stat.get("rentDepositPriceMax", ""),
                    stat.get("rentPriceMax", ""),
                    pyeong.get("roomCnt", ""),
                    pyeong.get("bathroomCnt", ""),
                    pyeong.get("averageMaintenanceCost", {}).get("averageTotalPrice", "")
                ])

                # **변경된 부분**: price_data 수집을 fetch_real_price_data 함수로 대체
                transactions = fetch_real_price_data(complex_id, pyeong_no, BASE_COOKIES, BASE_HEADERS)
                for t in transactions:
                    price_data.append([
                        complex_id,
                        pyeong_no,
                        t.get("tradeType", ""),
                        "5",  # 기존 year 값 유지
                        t.get("floor", ""),
                        f"{t.get('tradeYear', '')}-{str(t.get('tradeMonth', '')).zfill(2)}-{str(t.get('tradeDate', '')).zfill(2)}",
                        t.get("dealPrice", "")
                    ])

                # 공급자별 데이터 처리 (변경 없음)
                for prov in ['kbstar', 'kab']:
                    provider_params = {
                        'complexNo': str(complex_id),
                        'tradeType': '',
                        'year': '5',
                        'priceChartChange': 'false',
                        'areaNo': str(pyeong_no),
                        'provider': prov,
                        'type': 'table',
                    }
                    provider_headers = copy.deepcopy(BASE_HEADERS)
                    provider_headers['referer'] = (f'https://new.land.naver.com/complexes/{complex_id}?'
                                                   'ms=37.2890027,127.0591203,17&a=APT:PRE:ABYG:JGC&e=RETAIL')
                    provider_json = fetch_json(
                        f'https://new.land.naver.com/api/complexes/{complex_id}/prices',
                        params=provider_params, cookies=BASE_COOKIES, headers=provider_headers
                    )
                    if provider_json:
                        market_prices = provider_json.get("marketPrices", [])
                        if market_prices:
                            top_data = market_prices[0]
                            bymd = top_data.get("baseYearMonthDay", "")
                            if bymd and len(bymd) == 8:
                                try:
                                    bymd = datetime.strptime(bymd, "%Y%m%d").strftime("%Y-%m-%d")
                                except:
                                    pass
                            provider_data.append([
                                complex_id,
                                pyeong_no,
                                prov,
                                bymd,
                                top_data.get("dealUpperPriceLimit", ""),
                                top_data.get("dealAveragePrice", ""),
                                top_data.get("dealLowPriceLimit", ""),
                                top_data.get("dealAveragePriceChangeAmount", ""),
                                top_data.get("leaseUpperPriceLimit", ""),
                                top_data.get("leaseAveragePrice", ""),
                                top_data.get("leaseLowPriceLimit", ""),
                                top_data.get("leaseAveragePriceChangeAmount", ""),
                                top_data.get("rentLowPrice", ""),
                                top_data.get("deposit", ""),
                                top_data.get("rentUpperPrice", ""),
                                top_data.get("upperPriceLimit", ""),
                                top_data.get("averagePriceLimit", ""),
                                top_data.get("lowPriceLimit", ""),
                                top_data.get("priceChangeAmount", ""),
                                top_data.get("leasePerDealRate", "")
                            ])

    # =============================================================================
    # 매핑 딕셔너리 생성 및 insert_complex_name() 호출
    # =============================================================================
    complex_mapping = { str(row[0]).strip(): str(row[1]).strip() for row in complex_data if row[0] and row[1] }
    name_to_complexNo = { str(name).strip().lower(): comp_no for comp_no, name in complex_mapping.items() }

    def insert_complex_name(data_rows, key_index):
        new_rows = []
        for row in data_rows:
            comp_no = str(row[key_index]).strip()
            comp_name = complex_mapping.get(comp_no, "")
            new_row = row[:key_index+1] + [comp_name] + row[key_index+1:]
            new_rows.append(new_row)
        return new_rows

    # insert 단지명를 pyeong_data에 삽입 (key_index=0)
    pyeong_data = insert_complex_name(pyeong_data, 0)
    # 이제 pyeong_data의 각 행은 다음과 같이 구성됨:
    # 0: complexNo, 1: complexName, 2: pyeongNo, 3: supplyArea, 4: supplyPyeong,
    # 5: pyeongName, 6: pyeongName2, 7: exclusiveArea, 8: exclusivePyeong, 9: exclusiveRate,
    # 10: realEstateTypeCode, 11: householdCountByPyeong, 12: dealCount, 13: leaseCount,
    # 14: rentCount, 15: shortTermRentCount, 16: dealPriceMin, 17: dealPriceMax,
    # 18: dealPricePerSpaceMin, 19: dealPricePerSpaceMax, 20: dealPriceString,
    # 21: dealPricePerSpaceString, 22: leasePriceString, 23: leasePricePerSpaceString,
    # 24: leasePriceRateString, 25: rentPriceString, 26: rentDepositPriceMin,
    # 27: rentPriceMin, 28: rentDepositPriceMax, 29: rentPriceMax,
    # 30: roomCnt, 31: bathroomCnt, 32: averageTotalPrice

    # (A) sell_data 전용 매핑: (complexNo, pyeongName) -> pyeongName2
    # 여기서 pyeongName은 index 5, pyeongName2는 index 6
    pyeongName2_for_sell = {}
    for row in pyeong_data:
        c_no = str(row[0]).strip()
        pyeongName_val = str(row[5]).strip()   # pyeongName
        pyeongName2_val = str(row[6]).strip()    # 고유 평형값 (pyeongName2)
        key = (c_no, pyeongName_val)
        pyeongName2_for_sell[key] = pyeongName2_val

    # (B) price_data 및 provider_data 매핑: (complexNo, pyeongNo) -> (pyeongName, pyeongName2)
    pyeongNo_dict = {}
    for row in pyeong_data:
        c_no = str(row[0]).strip()
        p_no = str(row[2]).strip()
        p_name = str(row[5]).strip()    # pyeongName
        p_name2 = str(row[6]).strip()   # pyeongName2
        key = (c_no, p_no)
        pyeongNo_dict[key] = (p_name, p_name2)

    # ------------------------------------------------------------------
    # 변환값 계산 (평균 가격, 매매/전세/월세 매물 출현율 등)
    # ------------------------------------------------------------------
    # 기존 pyeong_data의 각 행은 길이 33이므로, 새 변환 값은 행의 맨 뒤에 추가
    for row in pyeong_data:
        # 위에서 설명한 인덱스: dealPriceMin은 index 16, dealPriceMax는 17, etc.
        dealPriceMin2 = convert_price(str(row[16]))
        dealPriceMax2 = convert_price(str(row[17]))
        rentDepositPriceMin2 = convert_price(str(row[26]))
        rentPriceMin2 = convert_price(str(row[27]))
        rentDepositPriceMax2 = convert_price(str(row[28]))
        rentPriceMax2 = convert_price(str(row[29]))
        
        try:
            hh = float(row[11] or 0)
        except:
            hh = 0
        if hh > 0:
            sale_occurrence = f"{(float(row[12] or 0) / hh) * 100:.1f}%"
            jeonse_occurrence = f"{(float(row[14] or 0) / hh) * 100:.1f}%"
            monthly_occurrence = f"{(float(row[15] or 0) / hh) * 100:.1f}%"
        else:
            sale_occurrence = ""
            jeonse_occurrence = ""
            monthly_occurrence = ""
        
        row.extend([
            dealPriceMin2, dealPriceMax2, rentDepositPriceMin2, rentPriceMin2, rentDepositPriceMax2, rentPriceMax2,
            sale_occurrence, jeonse_occurrence, monthly_occurrence
        ])
    # 이제 각 pyeong_data 행의 최종 길이는 33 + 9 = 42

    pyeong_header = [
        "complexNo", "complexName", "pyeongNo", "supplyArea", "supplyPyeong", "pyeongName", "pyeongName2",
        "exclusiveArea", "exclusivePyeong", "exclusiveRate", "realEstateTypeCode", "householdCountByPyeong",
        "dealCount", "leaseCount", "rentCount", "shortTermRentCount",
        "dealPriceMin", "dealPriceMax", "dealPricePerSpaceMin", "dealPricePerSpaceMax",
        "dealPriceString", "dealPricePerSpaceString", "leasePriceString", "leasePricePerSpaceString",
        "leasePriceRateString", "rentPriceString", "rentDepositPriceMin", "rentPriceMin",
        "rentDepositPriceMax", "rentPriceMax",
        "roomCnt", "bathroomCnt", "averageTotalPrice",
        "dealPriceMin2", "dealPriceMax2", "rentDepositPriceMin2", "rentPriceMin2", "rentDepositPriceMax2", "rentPriceMax2",
        "매매매물출현율", "전세매물출현율", "월세매물출현율"
    ]

    # =============================================================================
    # sell_data 처리
    # =============================================================================
    all_articles = []
    for complex_no in complex_ids:
        page = 1
        while True:
            sell_url = (
                f'https://new.land.naver.com/api/articles/complex/{complex_no}'
                f'?realEstateType=APT%3APRE%3AABYG%3AJGC&tradeType='
                f'&page={page}&complexNo={complex_no}&type=list&order=rank'
                f'&sameAddressGroup=true'
            )
            sell_json = fetch_json(sell_url, params={}, cookies=SELL_COOKIES, headers=SELL_HEADERS)
            if sell_json:
                articles = sell_json.get("articleList", [])
                if not articles:
                    break

                for article in articles:
                    art_name = str(article.get("articleName", "")).strip().lower()
                    comp_no = name_to_complexNo.get(art_name, "")
                    article["complexNo"] = comp_no
                    article["complexName"] = complex_mapping.get(comp_no, "")
                    if "areaName" in article:
                        area_val = str(article["areaName"]).strip()
                        key = (comp_no, area_val)
                        article["pyeongName"] = pyeongName2_for_sell.get(key, "")
                    else:
                        article["pyeongName"] = ""
                    # rentPrc 필드 추가 (없으면 빈 문자열)
                    article["rentPrc"] = article.get("rentPrc", "")
                all_articles.extend(articles)
                page += 1
            else:
                print(f"Sell 데이터 가져오기 실패: complex {complex_no}의 page {page}")
                break

    today = datetime.today().date()
    for article in all_articles:
        acymd = article.get('articleConfirmYmd', '')
        if acymd:
            try:
                if '-' in acymd:
                    confirm_date = datetime.strptime(acymd, '%Y-%m-%d').date()
                else:
                    confirm_date = datetime.strptime(acymd, '%Y%m%d').date()
                diff_days = (today - confirm_date).days
            except Exception as e:
                diff_days = ""
        else:
            diff_days = ""
        article['매물등록경과일'] = diff_days

    # ====================================================================
    # sell_data에 pyeong_data의 일부 데이터를 맵핑 (신규 필드 추가)
    # ====================================================================
    # sell_data에 맵핑할 필드 목록 (총 25개)
    pyeong_fields = [
        "householdCountByPyeong", "dealCount", "leaseCount", "rentCount", "shortTermRentCount",
        "roomCnt", "bathroomCnt", "averageTotalPrice",
        "dealPriceMin2", "dealPriceMax2", "dealPricePerSpaceMin", "dealPricePerSpaceMax",
        "dealPriceString", "dealPricePerSpaceString", "leasePriceString", "leasePricePerSpaceString",
        "leasePriceRateString", "rentPriceString", "rentDepositPriceMin2", "rentPriceMin2",
        "rentDepositPriceMax2", "rentPriceMax2", "매매매물출현율", "전세매물출현율", "월세매물출현율"
    ]

    # 매핑 키는 (complexNo, pyeongName2) → pyeongName2는 now index 6
    pyeong_mapping = {}
    for row in pyeong_data:
        key = (str(row[0]).strip(), str(row[6]).strip())
        pyeong_mapping[key] = {
             "householdCountByPyeong": row[11],
             "dealCount": row[12],
             "leaseCount": row[13],
             "rentCount": row[14],
             "shortTermRentCount": row[15],
             "roomCnt": row[30],
             "bathroomCnt": row[31],
             "averageTotalPrice": row[32],
             "dealPriceMin2": row[33],
             "dealPriceMax2": row[34],
             "dealPricePerSpaceMin": row[18],
             "dealPricePerSpaceMax": row[19],
             "dealPriceString": row[20],
             "dealPricePerSpaceString": row[21],
             "leasePriceString": row[22],
             "leasePricePerSpaceString": row[23],
             "leasePriceRateString": row[24],
             "rentPriceString": row[25],
             "rentDepositPriceMin2": row[35],
             "rentPriceMin2": row[36],
             "rentDepositPriceMax2": row[37],
             "rentPriceMax2": row[38],
             "매매매물출현율": row[39],
             "전세매물출현율": row[40],
             "월세매물출현율": row[41]
        }

    for article in all_articles:
        comp_no = str(article.get("complexNo", "")).strip()
        # sell_data의 article["pyeongName"]에는 이미 고유 평형값(pyeongName2)이 저장됨
        pyeong_unique = str(article.get("pyeongName", "")).strip()
        key = (comp_no, pyeong_unique)
        if key in pyeong_mapping:
            article.update(pyeong_mapping[key])
        else:
            for field in pyeong_fields:
                article[field] = ""

    # =============================================================================
    # sell_data에 provider_data의 'kbstar' 정보 추가하기
    # =============================================================================
    original_provider_data = provider_data.copy()

    provider_data_kbstar = [row for row in original_provider_data if str(row[2]).strip().lower() == 'kbstar']

    provider_kbstar_mapping = {}
    for row in provider_data_kbstar:
        comp_no = str(row[0]).strip()
        p_no = str(row[1]).strip()  # 원본에서 pyeong_no는 인덱스 1
        _, p_name2 = pyeongNo_dict.get((comp_no, p_no), ("", ""))
        key = (comp_no, p_name2)
        provider_kbstar_mapping[key] = {
             "provider": row[2],
             "baseYearMonthDay": row[3],
             "dealUpperPriceLimit": row[4],
             "dealAveragePrice": row[5],
             "dealLowPriceLimit": row[6],
             "dealAveragePriceChangeAmount": row[7],
             "leaseUpperPriceLimit": row[8],
             "leaseAveragePrice": row[9],
             "leaseLowPriceLimit": row[10],
             "leaseAveragePriceChangeAmount": row[11],
             "rentLowPrice": row[12],
             "deposit": row[13],
             "rentUpperPrice": row[14],
             "upperPriceLimit": row[15],
             "averagePriceLimit": row[16],
             "lowPriceLimit": row[17],
             "priceChangeAmount": row[18],
             "leasePerDealRate": row[19]
        }

    new_fields = [
        "provider", "baseYearMonthDay", "dealUpperPriceLimit", "dealAveragePrice",
        "dealLowPriceLimit", "dealAveragePriceChangeAmount", "leaseUpperPriceLimit",
        "leaseAveragePrice", "leaseLowPriceLimit", "leaseAveragePriceChangeAmount",
        "rentLowPrice", "deposit", "rentUpperPrice", "upperPriceLimit",
        "averagePriceLimit", "lowPriceLimit", "priceChangeAmount", "leasePerDealRate"
    ]

    for article in all_articles:
        comp_no = str(article.get("complexNo", "")).strip()
        pyeong_unique = str(article.get("pyeongName", "")).strip()
        key = (comp_no, pyeong_unique)
        if key in provider_kbstar_mapping:
            article.update(provider_kbstar_mapping[key])
        else:
            for field in new_fields:
                article[field] = ""

    # =============================================================================
    # sell_data CSV 파일 생성 (필드 순서 조정)
    # =============================================================================
    if all_articles:
        exclude_fields = {
            "articleStatus", "realEstateTypeCode", "realEstateTypeName", "articleRealEstateTypeCode", "tradeTypeCode",
            "verificationTypeCode",
            "representativeImgUrl", "representativeImgTypeCode",
            "representativeImgThumb", "siteImageCount", "sameAddrDirectCnt", "cpid", "cpPcArticleBridgeUrl",
            "cpPcArticleLinkUseAtArticleTitleYn", "cpPcArticleLinkUseAtCpNameYn", "cpMobileArticleUrl",
            "cpMobileArticleLinkUseAtArticleTitleYn", "cpMobileArticleLinkUseAtCpNameYn", "isLocationShow", "realtorId",
            "tradeCheckedByOwner", "isDirectTrade", "isInterest", "isComplex", "detailAddress", "detailAddressYn", "isVrExposed"
        }
        filtered_keys = [key for key in all_articles[0].keys() if key not in exclude_fields]
        
        if "articleName" in filtered_keys and "complexNo" in filtered_keys:
            filtered_keys.remove("complexNo")
            idx = filtered_keys.index("articleName")
            filtered_keys.insert(idx, "complexNo")
        if "areaName" in filtered_keys and "pyeongName" in filtered_keys:
            filtered_keys.remove("pyeongName")
            idx = filtered_keys.index("areaName")
            filtered_keys.insert(idx+1, "pyeongName")
        if "rentPrc" in filtered_keys:
            filtered_keys.remove("rentPrc")
        if "dealOrWarrantPrc" in filtered_keys:
            idx = filtered_keys.index("dealOrWarrantPrc")
            filtered_keys.insert(idx+1, "rentPrc")
        
        if "floorType" not in filtered_keys:
            filtered_keys.append("floorType")
        
        filtered_keys.append("downloadDate")
        
        for article in all_articles:
            if 'floorInfo' in article:
                # floorInfo를 가공하지 않고 원본 그대로 저장합니다.
                floor = str(article['floorInfo'])
                article['floorInfo'] = floor
                article['floorType'] = get_floor_type(floor)
            else:
                article['floorType'] = ""
            try:
                acymd = article.get('articleConfirmYmd', '')
                if acymd and len(acymd) == 8:
                    article['articleConfirmYmd'] = datetime.strptime(acymd, '%Y%m%d').strftime('%Y-%m-%d')
            except:
                pass
            article["downloadDate"] = updated_date
        sell_filename = DATA_PATHS.get("SELL", DATA_DIR / "sell_data.csv")
        with open(sell_filename, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=filtered_keys)
            writer.writeheader()
            for article in all_articles:
                writer.writerow({key: str(article.get(key, '')).replace(',', '') for key in filtered_keys})
        print(f"매물 정보 파일 생성 완료: {sell_filename}")
    else:
        print("No sell data retrieved.")

    # =============================================================================
    # price_data와 provider_data에 pyeongName, pyeongName2 추가
    # =============================================================================
    price_data = insert_complex_name(price_data, 0)
    new_price_data = []
    for row in price_data:
        c_no = str(row[0]).strip()
        p_no = str(row[2]).strip()
        pn, pn2 = pyeongNo_dict.get((c_no, p_no), ("", ""))
        new_row = row[:3] + [pn, pn2] + row[3:]
        new_price_data.append(new_row)
    price_data = new_price_data
    price_header = ["complexNo", "complexName", "pyeongNo", "pyeongName", "pyeongName2", "tradeType", "year", "floor", "date", "price"]
    # ----- 추가: 새 필드 생성 처리 -----
    # downloadDate는 updated_date 변수에 저장되어 있음. 날짜 부분만 사용 (YYYY-MM-DD)
    download_dt = datetime.strptime(updated_date, "%Y-%m-%d %H:%M:%S").date()

    # 각 price_data 행에 대해 새로운 필드들을 생성하여 추가
    for row in price_data:
        # 1. pyeongName3: pyeongName2에서 후행 알파벳 제거 (정규표현식 적용)
        #    (pyeongName2는 인덱스 4)
        pyeongName2 = row[4]
        pyeongName3 = re.sub(r'[A-Za-z]+$', '', pyeongName2).strip()
        
        # 2. dealDate: 'date' 필드의 값 그대로 (인덱스 8)
        dealDate = row[8].strip() if row[8] else ""
        
        # 3. dealAmount: 'price' 필드의 값을 숫자로 변환 (인덱스 9)
        dealAmount = convert_price(str(row[9]))
        
        # 4. dealDateClass: downloadDate와 dealDate 간의 차이를 연수로 계산 후 분류
        try:
            deal_dt = datetime.strptime(dealDate, "%Y-%m-%d").date()
            diff_days = (download_dt - deal_dt).days
            diff_years = diff_days / 365.25
            if diff_years <= 1:
                dealDateClass = "1"
            elif diff_years <= 3:
                dealDateClass = "3"
            elif diff_years <= 5:
                dealDateClass = "5"
            else:
                dealDateClass = ""
        except Exception:
            dealDateClass = ""
        
        # 새로운 필드들을 현재 행의 끝에 추가
        row.extend([pyeongName3, dealDate, str(dealAmount), dealDateClass])

    # 새로 추가한 필드명을 헤더에 포함
    price_header.extend(["pyeongName3", "dealDate", "dealAmount", "dealDateClass"])

    provider_data = insert_complex_name(provider_data, 0)
    new_provider_data = []
    for row in provider_data:
        c_no = str(row[0]).strip()
        p_no = str(row[2]).strip()
        pn, pn2 = pyeongNo_dict.get((c_no, p_no), ("", ""))
        new_row = row[:3] + [pn, pn2] + row[3:]
        new_provider_data.append(new_row)
    provider_data = new_provider_data
    provider_header = provider_data[0] and (["complexNo", "complexName", "pyeongNo", "pyeongName", "pyeongName2"] + 
                                             ["provider", "baseYearMonthDay", "dealUpperPriceLimit", "dealAveragePrice",
                                              "dealLowPriceLimit", "dealAveragePriceChangeAmount", "leaseUpperPriceLimit",
                                              "leaseAveragePrice", "leaseLowPriceLimit", "leaseAveragePriceChangeAmount",
                                              "rentLowPrice", "deposit", "rentUpperPrice", "upperPriceLimit",
                                              "averagePriceLimit", "lowPriceLimit", "priceChangeAmount", "leasePerDealRate"]) or []

    write_csv("complex_data.csv", complex_keys + ["매매매물출현율", "전세매물출현율", "월세매물출현율"] + school_keys, complex_data)
    write_csv("pyeong_data.csv", pyeong_header, pyeong_data)
    write_csv("price_data.csv", price_header, price_data)
    write_csv("provider_data.csv", provider_header, provider_data)

    print(f"기본 정보 파일 생성 완료: complex_data.csv")
    print(f"평형 정보 파일 생성 완료: pyeong_data.csv")
    print(f"실거래가 파일 생성 완료: price_data.csv")
    print(f"시세 파일 생성 완료: provider_data.csv")

    # =============================================================================
    # (추가) 동 데이터 수집 및 CSV 파일 생성
    # =============================================================================
    dong_data = []  # 최종 동 정보 저장 리스트

    def find_first_non_empty(records, key):
        for record in records:
            value = record.get(key, "")
            if value.strip() != "":
                return value
        return ""

    for complex_id in complex_ids:
        complex_name = complex_mapping.get(str(complex_id), "")
        consecutive_no_data = 0
        max_try = 50
        for dong_no in range(1, max_try + 1):
            url_dong = f'https://new.land.naver.com/api/complexes/{complex_id}/buildings/landprice'
            params = {
                'dongNo': str(dong_no),
                'complexNo': str(complex_id),
            }
            dong_json = fetch_json(url_dong, params=params, cookies=DONG_COOKIES, headers=DONG_HEADERS)
            if not dong_json:
                consecutive_no_data += 1
                if consecutive_no_data >= 3:
                    break
                continue
            landPriceTotal = dong_json.get("landPriceTotal", {})
            landPriceFloors = landPriceTotal.get("landPriceFloors", [])
            if not landPriceFloors:
                consecutive_no_data += 1
                if consecutive_no_data >= 3:
                    break
                continue
            consecutive_no_data = 0
            max_floor = -math.inf
            chosen_landPrices = None
            for floor_data in landPriceFloors:
                floor_val = floor_data.get("floor")
                if floor_val is not None:
                    try:
                        floor_val_int = int(floor_val)
                        if floor_val_int > max_floor:
                            max_floor = floor_val_int
                            chosen_landPrices = floor_data.get("landPrices", [])
                    except Exception as e:
                        pass
            if max_floor == -math.inf or not chosen_landPrices:
                continue
            hscpNo_val = find_first_non_empty(chosen_landPrices, "hscpNo")
            hscpNm_val = find_first_non_empty(chosen_landPrices, "hscpNm")
            dongNm_val = find_first_non_empty(chosen_landPrices, "dongNm")
            row = [hscpNo_val, hscpNm_val, str(dong_no), dongNm_val, max_floor]
            dong_data.append(row)
            
    write_csv("dong_data.csv", ["complexNo", "complexName", "dongNo", "dongNm", "max_floor"], dong_data)
    print(f"동 정보 파일 생성 완료: dong_data.csv")

if __name__ == "__main__":
    main_function()  # 직접 실행시 기본값으로 실행