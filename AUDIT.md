# 코드 점검 보고서 (Audit)

> 기존 Streamlit 기반 "집착 - 아파트를 째려보다" 코드를 종합 점검한 결과입니다.
> GitHub Pages(HTML 정적) 재구축에 앞서 현재 코드의 유효성과 위험 요소를 정리합니다.

---

## 0. 한 줄 요약

코드는 **문법적으로는 정상 동작 가능**하지만, **네이버 비공개 API의 만료성 세션 토큰에
전적으로 의존**하기 때문에 토큰이 만료되는 순간 데이터 수집이 실패하는 구조입니다.
이 구조는 **GitHub Pages(정적 호스팅)로 그대로 옮길 수 없습니다.** 정적 사이트는
서버사이드 스크래핑(`requests` 호출)을 실행할 수 없기 때문입니다.

---

## 1. 아키텍처 개요

```
app.py
 ├─ src/config.py            : 경로/상수 정의
 ├─ src/data_loader.py       : CSV 로딩 + 지역 드롭다운 옵션
 ├─ src/api_client.py        : 네이버 단지목록 조회
 ├─ src/naver_apt_v5.py      : (Step1) 네이버 API 크롤링 → CSV 생성
 ├─ src/sell_price_merge_v2.py : (Step2) 매물+실거래 병합/지표계산 → result.csv
 ├─ src/ui_components_v2.py  : 사이드바 + 시각화(Plotly)
 └─ src/styles.py            : CSS
```

데이터 흐름: 사용자가 아파트 2개를 선택 → "분석 실행" → Step1 크롤링으로
`complex/pyeong/sell/price/dong/provider` CSV 생성 → Step2 병합으로 `result.csv` 생성
→ 화면에 기본정보/투자지표/실거래추이/매물현황 렌더링.

---

## 2. 심각도별 발견 사항

### 🔴 Critical

| # | 항목 | 내용 | 조치 |
|---|------|------|------|
| C1 | 만료성 토큰 의존 | `.env`의 `AUTHORIZATION`/`NNB`/`ASID`/`NAC` 등 브라우저 세션 값으로 네이버 비공개 API를 호출. 토큰 만료 시 전체 수집 실패. **서비스가 주기적으로 깨지는 근본 원인.** | 구조적 한계 — 재구축 시 데이터 전략 재설계 필요(§5) |
| C2 | `.venv/` 가 git에 추적됨 | Windows용 `python.exe`/`pip*.exe` 바이너리와 Windows 절대경로가 박힌 `pyvenv.cfg`까지 커밋. `.gitignore`에 규칙이 있으나 이미 추적되던 파일이라 무시되지 않음. | **추적 해제 완료** (`git rm --cached .venv`) |

### 🟠 High

| # | 항목 | 내용 | 조치 |
|---|------|------|------|
| H1 | 예외 은폐 | `sell_price_merge_v2.main()`이 예외를 `st.write`로만 출력하고 삼킴 → 호출부는 성공으로 오인하고 `analysis_done=True` 설정 → 다음 단계에서 빈/오래된 데이터로 혼란. | **수정 완료** (예외를 `raise`로 전파, 호출부에서 `analysis_done=False` 처리) |
| H2 | 요청 타임아웃 없음 | `requests.get`(3곳)에 `timeout` 미지정 → 네이버 무응답 시 무한 대기로 앱 멈춤. | **수정 완료** (`timeout=10` 추가) |

### 🟡 Medium

| # | 항목 | 내용 | 조치 |
|---|------|------|------|
| M1 | 디버깅 코드 잔존 | 사이드바의 파일경로 출력 루프, `st.write("Loading...")`/`"Computing..."` 류 진행 로그, `st.write("스택 트레이스:", e.__traceback__)` 등. (git 로그의 `디버깅` 커밋들) | **정리 완료** |
| M2 | `Styler.applymap` deprecated | pandas 2.1+에서 폐기 예정 → `.map`으로 교체. | **수정 완료** |
| M3 | 미사용 의존성 | `requirements.txt`의 `selenium`, `webdriver_manager`가 코드에서 전혀 사용되지 않음. | **제거 완료** |
| M4 | 죽은 import | `load_pyeong_data`, `load_analysis_data`, `get_dropdown_options`(일부)·`UI_CONFIG` 등 import 후 미사용. | **정리 완료** |
| M5 | `.env.example` 부재 | 필요한 환경변수 29종이 문서화되지 않아, 새로 clone하면 무엇을 채워야 하는지 알 수 없음. | **추가 완료** |

### ⚪ Low (관찰만 — 미수정)

| # | 항목 | 내용 |
|---|------|------|
| L1 | 광범위한 `bare except:` | `naver_apt_v5.py`/`ui_components_v2.py`에 다수. 의도된 무시이나 디버깅을 어렵게 함. 재구축 시 구체 예외로 한정 권장. |
| L2 | `idxmax`/`idxmin` 엣지 | `compute_stats_pyeong`에서 매칭 행이 있으나 `dealAmount_numeric`가 전부 NaN이면 `idxmax`가 예외. 실데이터에선 드묾. |
| L3 | 캐싱 staleness | `@st.cache_data`로 캐시된 일부 로더가 동적으로 재생성되는 CSV를 가릴 수 있음(현재 핵심 경로는 `pd.read_csv` 직접 호출이라 영향 적음). |
| L4 | 하드코딩된 referer 좌표 | `naver_apt_v5.py`의 provider 요청 referer에 특정 단지 좌표가 고정. 동작엔 무방. |

---

## 3. 이번 점검에서 적용한 변경

- `.venv/` git 추적 해제 (저장소에서 Windows 바이너리 제거)
- `requirements.txt`: 미사용 `selenium`, `webdriver_manager` 제거
- `requests.get` 3곳에 `timeout=10` 추가
- `Styler.applymap` → `Styler.map`
- `sell_price_merge_v2`: 진행 로그 제거 + 예외를 호출부로 전파
- `ui_components_v2` 사이드바: 디버깅용 파일경로 출력 블록 제거, 실패 시 상태 일관화
- 죽은 import 정리 (`app.py`, `ui_components_v2.py`)
- `.env.example` 추가 (필요 환경변수 29종 문서화)

> 코드 로직 자체(지표 계산식, 시각화)는 검증 데이터(`.env`/CSV)가 없어 런타임 실행 검증은
> 불가하여, **동작을 바꾸지 않는 안전한 개선**에 한정했습니다.

---

## 4. 재현/실행에 필요한 것 (현재 구조 기준)

1. `cp .env.example .env` 후 브라우저에서 추출한 네이버 세션 값 채우기
2. `pip install -r requirements.txt`
3. `streamlit run app.py`

토큰 만료 시 Step1 수집이 실패하므로, 실행 시점마다 세션 값 갱신이 필요합니다.

---

## 5. GitHub Pages 재구축을 위한 핵심 고려사항

GitHub Pages는 **정적 파일만** 제공합니다. 따라서 브라우저에서 직접 네이버 비공개 API를
호출하는 방식은 (1) CORS 차단, (2) 인증 토큰 노출, (3) 약관 위반 위험으로 부적합합니다.
재구축 시 **데이터 수집과 화면 표시를 분리**해야 합니다. 권장 방향:

- **수집(배치) ↔ 표시(정적) 분리**
  - GitHub Actions(스케줄)로 주기적으로 수집 스크립트를 실행해 `data/*.json`을 생성·커밋
  - 정적 HTML/JS는 커밋된 JSON만 `fetch`해서 차트(예: Plotly.js/Chart.js)로 렌더
- 이렇게 하면 사용자는 "닫히지 않는" 정적 페이지를 보고, 데이터는 백그라운드 배치로 갱신
- 단, 토큰 만료 문제는 여전하므로 Actions Secret로 관리하고 실패 알림을 두는 것이 안전

이 방향이 확정되면 별도 설계 문서로 단계별 마이그레이션 계획을 작성하겠습니다.
