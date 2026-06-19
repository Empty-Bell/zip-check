# GitHub Pages 정적 사이트 마이그레이션 설계 플랜

> Streamlit 앱 → **GitHub Actions 배치 수집 + GitHub Pages 정적 사이트** 전환 계획.
> 모든 단계는 **Claude(나)가 직접 수행**하며, 사용자는 의사결정과 지시만 합니다.
> 각 단계 끝의 **🟦 결정 필요** 항목은 진행 전 사용자 확인이 필요한 지점입니다.

## 확정된 설계 결정 (사용자 승인)

| 항목 | 결정 |
|------|------|
| 수집 범위 | **지역(동) 단위** — config에 등록한 읍/면/동의 모든 단지를 수집 |
| 토큰 인증 | **수동 갱신 + GitHub Actions Secrets** (+ 수집 실패 시 알림) |
| 프론트엔드 | **순수 HTML/JS + Plotly.js** (빌드 단계 없음) |
| 갱신 주기 | **매주 1회** 스케줄 + 수동 트리거 |

---

## 1. 목표 아키텍처

```
[GitHub Actions] 매주 cron
      │  Secrets에서 네이버 토큰 주입
      ▼
collector/ (Python 배치)
   config에 등록된 동 목록 순회
      → 네이버 API 수집 (단지/평형/매물/실거래/시세/동)
      → 지표 계산 (버블지수/갭/전고저점 등)
      → docs/data/*.json 빌드
      → 변경분 커밋 & 푸시
      ▼
[GitHub Pages] docs/ 정적 호스팅
   index.html + JS가 docs/data/*.json 을 fetch
      → 드롭다운(시도/시군구/동/단지/평형)
      → Plotly.js 차트 4종 렌더 (서버 불필요, 항상 떠 있음)
```

핵심 원리: **"수집(배치)"과 "표시(정적)"의 완전 분리.** 브라우저는 네이버를 직접
호출하지 않고, 미리 만들어 커밋된 JSON만 읽습니다. → CORS/토큰노출/세션만료
문제를 프론트에서 제거하고, 사이트는 접속이 없어도 닫히지 않습니다.

### 목표 디렉터리 구조

```
collector/
  ├─ collect.py          # 진입점: config → 수집 → 빌드 오케스트레이션
  ├─ naver_api.py        # 기존 naver_apt_v5 정리 (requests, 토큰, 타임아웃)
  ├─ transform.py        # 기존 sell_price_merge_v2 지표 계산 (st.* 제거)
  ├─ build_site_data.py  # 수집 결과 → docs/data/*.json 산출
  └─ config.yaml         # 수집 대상 동 목록(cortarNo) + 옵션
docs/                    # GitHub Pages 루트
  ├─ index.html
  ├─ css/style.css
  ├─ js/app.js           # 드롭다운/상태/데이터 로딩
  ├─ js/charts.js        # Plotly 차트 (실거래추이/매물현황)
  ├─ js/metrics.js       # 갭지수/버블등급 계산 (Python 로직 포팅)
  ├─ js/format.js        # 억/만 포맷, 갭 색상 (헬퍼 포팅)
  └─ data/               # 빌드 산출물 (Actions가 커밋)
      ├─ index.json                  # 지역트리+단지목록+갱신일
      └─ complexes/<complexNo>.json  # 단지별 상세
.github/workflows/collect.yml        # 스케줄+수동 트리거+실패알림
data/cortarNo.csv                    # (유지) 법정동 코드 매핑
```

### 데이터 스키마 (초안 — Phase 1에서 확정)

`docs/data/index.json`
```json
{
  "updatedAt": "2026-06-19",
  "regions": [
    { "sido": "서울특별시", "sigungu": "...", "dong": "...", "cortarNo": "...",
      "complexes": [ { "complexNo": "138183", "complexName": "...",
                       "pyeongs": ["24","33"] } ] }
  ]
}
```

`docs/data/complexes/<complexNo>.json`
```json
{
  "complexNo": "138183", "complexName": "...",
  "basic": { "세대수": ..., "사용승인": ..., "용적률": ..., "배정초교": ... },
  "byPyeong": {
    "33": {
      "deals": [ { "date": "2025-03-01", "amount": 135000, "floor": 12,
                   "pyeongType": "33A", "class": 1 } ],
      "listings": [ { "price": 140000, "floor": "12/20", "type": "33A",
                      "area1": 109, "area2": 84, "dir": "남향",
                      "bubble": 62, "maxGap": "-3.2%", "minGap": "12.1%",
                      "link": "https://new.land.naver.com/..." } ],
      "stats": { "max5": ..., "avg5": ..., "min5": ..., "maxDate": ..., "minDate": ... }
    }
  }
}
```

> 단지별 파일로 쪼개 **프론트가 선택한 2개 단지 JSON만 fetch**하도록 합니다(지역 단위
> 수집이라 전체를 한 파일에 담으면 무거워지므로). **갭지수는 두 단지의 실거래 시계열로
> 브라우저에서 계산** → 데이터를 작게 유지하고 N² 사전계산을 피합니다.

---

## 2. 단계별 실행 플랜

### Phase 0 — 수집기 분리 및 기반 정리
**내가 할 일**
- 기존 `src/naver_apt_v5.py`, `sell_price_merge_v2.py`를 `collector/`로 옮기고
  **Streamlit 의존(`st.*`) 전부 제거**, 순수 함수/CLI로 전환.
- 토큰/쿠키를 `.env`(로컬) 및 환경변수(Actions)에서 읽도록 통일, 타임아웃·재시도 적용.
- `collector/config.yaml` 신설: 수집 대상 동 목록(cortarNo)과 옵션을 선언적으로 관리.
- `python collector/collect.py` 로 로컬 1회 수집 → 기존 result와 동등 산출 검증.

**산출물**: 동작하는 CLI 수집기, config 샘플.
**검증**: 등록한 동 1~2개로 로컬 수집 성공, CSV/중간산출 정상.
**🟦 결정 필요**: 최초 수집 대상 동 목록(예: 어느 시/군/구의 어느 동들).

### Phase 1 — 정적 데이터 빌드(JSON)
**내가 할 일**
- `build_site_data.py` 작성: 수집 결과 → `index.json` + `complexes/*.json`.
- 위 스키마를 실데이터로 확정(필드명·단위·결측 처리), 용량 점검.

**산출물**: `docs/data/` 샘플 JSON 세트.
**검증**: JSON 유효성 + 단지/평형/실거래/매물/지표 값이 기존 화면과 일치.
**🟦 결정 필요**: 공개 저장소면 수집 데이터가 **공개**됩니다(네이버 출처). 공개 OK인지,
아니면 private 저장소로 둘지.

### Phase 2 — 프론트엔드(정적 사이트)
**내가 할 일**
- `docs/index.html` + JS 작성: 드롭다운(시도→시군구→동→단지→평형, index.json 기반),
  단지 2개+평형 선택, 선택 단지 JSON fetch.
- Plotly.js로 **실거래가 추이**(라인+갭 바차트), **매물 현황**(전고저 레인지+호가 산점도+
  최신실거래 별표) 재현. **기본정보 표**, **투자지표 요약(버블/갭 등급)** 재현.
- 포맷 헬퍼(억/만, 갭 색상/화살표, 등급)와 **갭지수 계산식**을 Python→JS 포팅.

**산출물**: 로컬에서 도는 정적 사이트.
**검증**: `python -m http.server`로 docs 서빙, 기존 Streamlit 화면과 시각/수치 대조.
**🟦 결정 필요**: 디자인 톤(기존 "집착" 레드 헤더 유지 여부), 모바일 레이아웃 우선순위.

### Phase 3 — 자동화(GitHub Actions + Pages)
**내가 할 일**
- `.github/workflows/collect.yml`: **매주 cron + `workflow_dispatch`(수동)**.
  Secrets에서 토큰 주입 → 수집 → JSON 빌드 → `docs/data` 변경분 커밋·푸시.
- **수집 실패 시 자동 이슈 생성**(토큰 만료 감지 메시지 포함)으로 알림.
- GitHub Pages를 `docs/` 폴더 소스로 설정(설정 방법 안내, 토글은 사용자 권한 필요할 수 있음).

**산출물**: 주간 자동 갱신 파이프라인, 라이브 URL.
**검증**: 수동 트리거 1회 실행 → 커밋/배포/사이트 반영 확인.
**🟦 결정 필요**: 토큰을 Secrets에 등록(사용자가 직접 값 입력). 등록할 Secret 키 목록은
내가 제공.

### Phase 4 — 마감
**내가 할 일**
- README 재작성(새 구조/운영법/토큰 갱신 절차).
- 기존 Streamlit 코드 처리(보존/`legacy/` 이동/삭제 중 택1).
- 운영 체크리스트(토큰 만료 대응, 동 추가 방법) 정리.

**🟦 결정 필요**: Streamlit 레거시 코드 **보존 vs 삭제**.

---

## 3. 리스크 및 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 토큰 만료 | 주간 수집 실패 → 데이터가 오래됨(사이트는 유지) | 실패 시 자동 이슈/알림 + 갱신 절차 문서화 |
| 네이버 차단/약관 | 수집 중단 위험 | 주 1회 저빈도, 요청 간 지연, User-Agent 일관 |
| 데이터 공개 노출 | 공개 저장소 시 수집데이터 노출 | Phase 1 결정으로 public/private 선택 |
| 토큰 유출 | 보안 사고 | 토큰은 **오직 Secrets/`.env`**, 코드·JSON에 절대 미포함 |
| JSON 용량 | 동 단위라 단지 多시 비대 | 단지별 파일 분할 + 필요분만 lazy fetch |

---

## 4. 진행 방식

- 위 Phase 순서대로 진행하며, 각 Phase는 **별도 커밋**으로 올리고 결과를 보고합니다.
- **🟦 결정 필요** 지점에서 멈추고 사용자 확인을 받은 뒤 다음으로 갑니다.
- 우선 **Phase 0의 결정 필요 항목(최초 수집 대상 동 목록)** 부터 정해 주시면 착수합니다.
