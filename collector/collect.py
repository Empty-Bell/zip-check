"""배치 수집 진입점.

config.yaml에 등록된 동(cortarNo)들의 모든 단지를 수집하고,
지표를 계산한 뒤 정적 사이트용 JSON(docs/data/)을 빌드합니다.

GitHub Actions 또는 로컬에서 실행:
    python -m collector.collect
"""
import sys
import time

import yaml

from collector.paths import CONFIG_PATH
from collector import naver_api
from collector import transform
from collector import build_site_data


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_complex_ids(regions, delay=0.3):
    """등록된 동들의 cortarNo로 단지 목록을 조회해 complexNo 리스트를 만든다."""
    complex_ids = []
    for region in regions:
        cortar_no = str(region["cortarNo"]).strip()
        name = region.get("name", cortar_no)
        complexes = naver_api.fetch_complex_list(cortar_no)
        ids = [str(c["complexNo"]) for c in complexes if c.get("complexNo")]
        print(f"[collect] {name} ({cortar_no}): 단지 {len(ids)}개")
        complex_ids.extend(ids)
        time.sleep(delay)
    # 중복 제거(순서 유지)
    seen = set()
    unique_ids = [c for c in complex_ids if not (c in seen or seen.add(c))]
    return unique_ids


def main():
    config = load_config()
    regions = config.get("regions", [])
    delay = float(config.get("options", {}).get("request_delay_sec", 0.3))

    if not regions:
        print("[collect] config.yaml에 수집 대상 regions가 없습니다.")
        sys.exit(1)

    print(f"[collect] 대상 동 {len(regions)}개")
    complex_ids = resolve_complex_ids(regions, delay)
    if not complex_ids:
        print("[collect] 수집할 단지가 없습니다. 토큰 만료/네트워크를 확인하세요.")
        sys.exit(1)
    print(f"[collect] 총 단지 {len(complex_ids)}개 수집 시작")

    # Step 1: 네이버 API 수집 → CSV 생성
    naver_api.main_function(complex_ids)

    # Step 2: 매물 + 실거래 병합 및 지표 계산 → result.csv
    transform.main(complex_ids)

    # Step 3: 정적 사이트용 JSON 빌드 → docs/data/
    build_site_data.build()

    print("[collect] 완료")


if __name__ == "__main__":
    main()
