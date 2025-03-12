import requests
import streamlit as st

def fetch_complex_list(cortarNo: str) -> list:
    """아파트 단지 목록 조회"""
    url = "https://new.land.naver.com/api/regions/complexes"
    cookies = {
        'NNB': 'C7GYEM4VLE3WK',
        'ASID': '3b0d2b430000018b621828fa00000065',
        'landHomeFlashUseYn': 'Y',
        '_fwb': '119q3FQCJEzWfKGKU2BUQo7.1702389509680',
        '_fwb': '119q3FQCJEzWfKGKU2BUQo7.1702389509680',
        '_ga_0ZGH3YC3W6': 'GS1.2.1707832253.1.1.1707832259.0.0.0',
        '_ga_8P4PY65YZ2': 'GS1.1.1707832266.1.1.1707832365.49.0.0',
        '_ga_GN4BHVX9DS': 'GS1.1.1707832266.1.1.1707832365.49.0.0',
        '_ga': 'GA1.1.737295237.1698157835',
        '_ga_451MFZ9CFM': 'GS1.1.1717924411.2.0.1717924411.0.0.0',
        'wcs_bt': '4f99b5681ce60:1733322484',
        'NAC': 'cerqCgAMWF7sA',
        'nhn.realestate.article.rlet_type_cd': 'A01',
        'nhn.realestate.article.trade_type_cd': '""',
        'nhn.realestate.article.ipaddress_city': '4100000000',
        'realestate.beta.lastclick.cortar': '4111700000',
        'nid_inf': '2104184356',
        'NID_JKL': 'j/h0g7DHTxfKw7gFYS9RPtGrX03n4Qc2sJhLcRhlqi0=',
        'NACT': '1',
        'page_uid': 'i87bKlqVOsVssl4bNGGssssstis-280092',
        'SRT30': '1740831650',
        'SRT5': '1740831650',
        'REALESTATE': 'Sat%20Mar%2001%202025%2021%3A23%3A36%20GMT%2B0900%20(Korean%20Standard%20Time)',
        'BUC': 'OQMPMmyyCKHg1Xj3EvxfZixgpflUvT9Wk9FuXFvCUPQ='
    }
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en;q=0.9,ko-KR;q=0.8,ko;q=0.7,en-US;q=0.6',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NDA4MzE4MTYsImV4cCI6MTc0MDg0MjYxNn0.8Z2wOtJgzMtsHGlHDWKiesKHUnAIPNtiGMC4SAS8FFA',
        'priority': 'u=1, i',
        'referer': 'https://new.land.naver.com/complexes/136913?ms=37.289152,127.0601845,17&a=APT:PRE:JGC:ABYG&e=RETAIL',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        # 'cookie': 'NNB=C7GYEM4VLE3WK; ASID=3b0d2b430000018b621828fa00000065; landHomeFlashUseYn=Y; _fwb=119q3FQCJEzWfKGKU2BUQo7.1702389509680; _fwb=119q3FQCJEzWfKGKU2BUQo7.1702389509680; _ga_0ZGH3YC3W6=GS1.2.1707832253.1.1.1707832259.0.0.0; _ga_8P4PY65YZ2=GS1.1.1707832266.1.1.1707832365.49.0.0; _ga_GN4BHVX9DS=GS1.1.1707832266.1.1.1707832365.49.0.0; _ga=GA1.1.737295237.1698157835; _ga_451MFZ9CFM=GS1.1.1717924411.2.0.1717924411.0.0.0; wcs_bt=4f99b5681ce60:1733322484; NAC=cerqCgAMWF7sA; nhn.realestate.article.rlet_type_cd=A01; nhn.realestate.article.trade_type_cd=""; nhn.realestate.article.ipaddress_city=4100000000; realestate.beta.lastclick.cortar=4111700000; nid_inf=2104184356; NID_JKL=j/h0g7DHTxfKw7gFYS9RPtGrX03n4Qc2sJhLcRhlqi0=; NACT=1; page_uid=i87bKlqVOsVssl4bNGGssssstis-280092; SRT30=1740831650; SRT5=1740831650; REALESTATE=Sat%20Mar%2001%202025%2021%3A23%3A36%20GMT%2B0900%20(Korean%20Standard%20Time); BUC=OQMPMmyyCKHg1Xj3EvxfZixgpflUvT9Wk9FuXFvCUPQ=',
    }
    params = {
        'cortarNo': str(cortarNo),  # 문자열로 변환 보장,
        'realEstateType': 'APT:PRE:JGC:ABYG',
        'order': '',
    }
    try:
        response = requests.get(url, params=params, cookies=cookies, headers=headers)
        if response.status_code == 200:
            return response.json().get("complexList", [])
        else:
            st.error(f"API 호출 실패: 상태 코드 {response.status_code}")
            return []
    except Exception as e:
        st.error(f"API 호출 에러: {e}")
        return []
