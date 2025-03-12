import os
from dotenv import load_dotenv
import requests
import streamlit as st

# .env 파일 로드
load_dotenv()

def get_headers():
    """공통 헤더 반환"""
    return {
        'accept': '*/*',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': os.getenv('AUTHORIZATION'),
        'user-agent': os.getenv('USER_AGENT'),
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

def get_cookies():
    """공통 쿠키 반환"""
    return {
        'NNB': os.getenv('NNB'),
        'ASID': os.getenv('ASID'),
        'NAC': os.getenv('NAC'),
        'landHomeFlashUseYn': 'Y',
    }

def fetch_complex_list(cortarNo: str) -> list:
    """아파트 단지 목록 조회"""
    url = "https://new.land.naver.com/api/regions/complexes"
    params = {
        'cortarNo': str(cortarNo),
        'realEstateType': 'APT:PRE:JGC:ABYG',
        'order': '',
    }
    
    try:
        response = requests.get(
            url, 
            params=params, 
            cookies=get_cookies(),
            headers=get_headers()
        )
        
        if response.status_code == 200:
            return response.json().get("complexList", [])
        else:
            st.error(f"API 호출 실패: 상태 코드 {response.status_code}")
            return []
            
    except Exception as e:
        st.error(f"API 호출 에러: {e}")
        return []
