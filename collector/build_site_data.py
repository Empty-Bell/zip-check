"""수집 결과(CSV) → 정적 사이트용 JSON(docs/data/) 빌드.

산출물:
  docs/data/index.json                 지역 트리 + 단지/평형 목록 + 갱신일
  docs/data/complexes/<complexNo>.json 단지별 상세(기본정보/평형별 실거래·매물·통계)

프론트엔드는 선택한 단지 2개의 JSON만 fetch 합니다.
"""
import json
import math
from datetime import datetime

import pandas as pd

from collector.paths import DATA_PATHS, SITE_DATA_DIR


def _clean(v):
    """JSON 직렬화용: NaN/inf → None, numpy 타입 → 파이썬 기본형."""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if pd.isna(v) if not isinstance(v, (list, dict)) else False:
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def _pick(row, *candidates):
    """후보 컬럼명 중 존재하고 값이 있는 첫 번째를 반환(merge suffix 대응)."""
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return _clean(row[c])
    return None


def _to_num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _load_region_lookup():
    """cortarNo → (시/도, 시/군/구, 읍/면/동) 매핑."""
    df = pd.read_csv(DATA_PATHS["CORTAR"], encoding="utf-8-sig", dtype=str)
    lookup = {}
    for _, r in df.iterrows():
        lookup[str(r["cortarNo"]).strip()] = {
            "sido": r["시/도"], "sigungu": r["시/군/구"], "dong": r["읍/면/동"],
        }
    return lookup


def _complex_region(df_complex, region_lookup):
    """complexNo → region dict."""
    out = {}
    if df_complex is None:
        return out
    for _, r in df_complex.iterrows():
        cno = str(r["complexNo"]).strip()
        cortar = str(r.get("cortarNo", "")).strip()
        out[cno] = region_lookup.get(cortar, {"sido": "", "sigungu": "", "dong": ""})
    return out


def _build_basic(rows):
    """단지 기본정보(한 행 대표값)."""
    first = rows.iloc[0]
    return {
        "totalHouseholdCount": _to_num(_pick(first, "totalHouseholdCount")),
        "totalLeaseHouseholdCount": _to_num(_pick(first, "totalLeaseHouseholdCount")),
        "useApproveYmd": _pick(first, "useApproveYmd"),
        "totalDongCount": _to_num(_pick(first, "totalDongCount")),
        "highFloor": _to_num(_pick(first, "highFloor")),
        "parkingCountByHousehold": _to_num(_pick(first, "parkingCountByHousehold")),
        "batlRatio": _to_num(_pick(first, "batlRatio")),
        "btlRatio": _to_num(_pick(first, "btlRatio")),
        "schoolName": _pick(first, "schoolName"),
        "walkTime": _to_num(_pick(first, "walkTime")),
        "pyoengNames": _pick(first, "pyoengNames"),
        "dealCount": _to_num(_pick(first, "dealCount_y", "dealCount")),
        "saleRate": _pick(first, "매매매물출현율_y", "매매매물출현율"),
    }


def _build_listing(r):
    return {
        "price": _to_num(_pick(r, "dealOrWarrantPrc2")),
        "priceText": _pick(r, "dealOrWarrantPrc"),
        "floorInfo": _pick(r, "floorInfo"),
        "pyeongName": _pick(r, "pyeongName"),
        "area1": _to_num(_pick(r, "area1")),
        "area2": _to_num(_pick(r, "area2")),
        "direction": _pick(r, "direction"),
        "buildingName": _pick(r, "buildingName"),
        "confirmYmd": _pick(r, "articleConfirmYmd"),
        "sameAddrCnt": _to_num(_pick(r, "sameAddrCnt")),
        "householdCountByPyeong": _to_num(_pick(r, "householdCountByPyeong")),
        "typeDealCount": _to_num(_pick(r, "dealCount_x", "dealCount")),
        "typeSaleRate": _pick(r, "매매매물출현율_x", "매매매물출현율"),
        "bubble": _to_num(_pick(r, "bubble_score")),
        "maxGap": _pick(r, "real_max_5_gap"),
        "minGap": _pick(r, "real_min_5_gap"),
        "kbUpper": _to_num(_pick(r, "dealUpperPriceLimit")),
        "kbAvg": _to_num(_pick(r, "dealAveragePrice")),
        "kbLower": _to_num(_pick(r, "dealLowPriceLimit")),
        "leasePerDealRate": _pick(r, "leasePerDealRate"),
        "desc": _pick(r, "articleFeatureDesc"),
        "realtor": _pick(r, "realtorName"),
        "articleNo": _pick(r, "articleNo"),
    }


def _build_stats(rows):
    first = rows.iloc[0]
    return {
        "max5": _to_num(_pick(first, "pyeong_max_5")),
        "avg5": _to_num(_pick(first, "pyeong_avg_5")),
        "min5": _to_num(_pick(first, "pyeong_min_5")),
        "maxDate": _pick(first, "pyeong_max_5_DT"),
        "minDate": _pick(first, "pyeong_min_5_DT"),
        "latestAmount": _to_num(_pick(first, "latestdealAmount")),
        "latestDate": _pick(first, "latestdealDate"),
        "latestFloor": _to_num(_pick(first, "latestdealFloor")),
    }


def _build_deals(df_real, complex_no, pyeong3):
    sub = df_real[(df_real["complexNo"] == complex_no) & (df_real["pyeongName3"] == pyeong3)]
    deals = []
    for _, r in sub.iterrows():
        amount = _to_num(_pick(r, "dealAmount"))
        deals.append({
            "date": _pick(r, "dealDate"),
            "amount": amount,
            "floor": _to_num(_pick(r, "floor")),
            "pyeongType": _pick(r, "pyeongName2"),
            "class": _to_num(_pick(r, "dealDateClass")),
        })
    return deals


def build():
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DATA_DIR / "complexes").mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATHS["RESULT"], encoding="utf-8-sig", dtype={"complexNo": str})
    df_real = pd.read_csv(DATA_PATHS["REAL_PRICE"], encoding="utf-8-sig", dtype={"complexNo": str})
    df_real["pyeongName3"] = df_real["pyeongName3"].astype(str)
    try:
        df_complex = pd.read_csv(DATA_PATHS["COMPLEX"], encoding="utf-8-sig", dtype={"complexNo": str})
    except FileNotFoundError:
        df_complex = None

    region_lookup = _load_region_lookup()
    complex_region = _complex_region(df_complex, region_lookup)

    df["complexNo"] = df["complexNo"].astype(str)
    df["pyeongName3"] = df["pyeongName3"].astype(str)

    regions_map = {}  # (sido,sigungu,dong) -> { cortar?, complexes: {} }
    updated_at = datetime.now().strftime("%Y-%m-%d")

    for complex_no, c_rows in df.groupby("complexNo"):
        complex_name = str(c_rows.iloc[0].get("complexName", "")).strip()
        sale_rows = c_rows[c_rows["tradeTypeName"] == "매매"] if "tradeTypeName" in c_rows else c_rows

        by_pyeong = {}
        pyeong_list = sorted([p for p in c_rows["pyeongName3"].dropna().unique() if p and p != "nan"])
        for pyeong3 in pyeong_list:
            p_sale = sale_rows[sale_rows["pyeongName3"] == pyeong3]
            p_any = c_rows[c_rows["pyeongName3"] == pyeong3]
            stats_src = p_sale if not p_sale.empty else p_any
            by_pyeong[pyeong3] = {
                "listings": [_build_listing(r) for _, r in p_sale.iterrows()],
                "stats": _build_stats(stats_src) if not stats_src.empty else {},
                "deals": _build_deals(df_real, complex_no, pyeong3),
            }

        region = complex_region.get(complex_no, {"sido": "", "sigungu": "", "dong": ""})
        complex_obj = {
            "complexNo": complex_no,
            "complexName": complex_name,
            "region": region,
            "basic": _build_basic(c_rows),
            "pyeongs": pyeong_list,
            "byPyeong": by_pyeong,
        }

        with open(SITE_DATA_DIR / "complexes" / f"{complex_no}.json", "w", encoding="utf-8") as f:
            json.dump(complex_obj, f, ensure_ascii=False, separators=(",", ":"))

        key = (region["sido"], region["sigungu"], region["dong"])
        node = regions_map.setdefault(key, [])
        node.append({"complexNo": complex_no, "complexName": complex_name, "pyeongs": pyeong_list})

    index = {
        "updatedAt": updated_at,
        "regions": [
            {"sido": k[0], "sigungu": k[1], "dong": k[2], "complexes": v}
            for k, v in sorted(regions_map.items())
        ],
    }
    with open(SITE_DATA_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    print(f"[build] index.json + 단지 {df['complexNo'].nunique()}개 JSON 생성 완료 → {SITE_DATA_DIR}")


if __name__ == "__main__":
    build()
