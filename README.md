# 집착 - 아파트를 째려보다

갈아타고 싶은 아파트의 실거래가·매물을 기존 보유 아파트와 비교해
적정 갈아타기 타이밍을 가늠하는 서비스입니다.

> 기존 Streamlit 버전을 **GitHub Actions 배치 수집 + GitHub Pages 정적 사이트**
> 구조로 재구축했습니다. 설계 배경은 [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md),
> 기존 코드 점검 내역은 [`AUDIT.md`](AUDIT.md) 참고.

## 구조

```
collector/   네이버 데이터 수집 + 지표 계산 + 정적 JSON 빌드 (Python 배치)
  config.yaml         수집 대상 동(cortarNo) 목록
  collect.py          진입점 (python -m collector.collect)
  naver_api.py        네이버 API 수집
  transform.py        매물+실거래 병합/지표 계산
  build_site_data.py  → docs/data/*.json 빌드
docs/        GitHub Pages 정적 사이트 (HTML/JS + Plotly.js)
  index.html, css/, js/
  data/               빌드 산출 JSON (Actions가 갱신·커밋)
.github/workflows/collect.yml   주간 수집 + 수동 트리거 + 실패 알림
```

핵심 원리: **수집(배치)과 표시(정적)의 분리.** 브라우저는 네이버를 직접 호출하지
않고, 미리 만들어 커밋된 JSON만 읽습니다. → 서버 없이 항상 떠 있는 정적 사이트.

## 운영 방법

### 1) 토큰 등록 (최초 1회 + 만료 시 갱신)
네이버 비공개 API는 브라우저 세션 토큰을 사용하며 **주기적으로 만료**됩니다.
`.env.example`의 항목들을 브라우저 개발자도구에서 추출해
저장소 **Settings → Secrets and variables → Actions** 에 등록하세요.

### 2) 수집 대상 동 추가/변경
`collector/config.yaml`의 `regions`에 동(cortarNo)을 추가합니다.
cortarNo는 `data/cortarNo.csv`에서 찾을 수 있습니다.
현재 대상: 수원시 영통구 이의동(4111710300), 하동(4111710400).

### 3) 데이터 갱신
- 자동: 매주 월요일 03:00 KST에 Actions가 수집 → `docs/data` 커밋.
- 수동: Actions 탭 → "데이터 수집 (주간)" → Run workflow.
- 수집 실패 시(주로 토큰 만료) 자동으로 알림 이슈가 생성됩니다.

### 4) GitHub Pages 게시
Settings → Pages → Source를 **배포 브랜치 / `/docs`** 폴더로 설정하세요.

## 로컬 개발

```bash
pip install -r requirements.txt

# 수집(.env에 토큰 필요): cp .env.example .env 후 값 입력
python -m collector.collect

# 정적 사이트 미리보기
python -m http.server --directory docs 8000   # → http://localhost:8000
```

## 데이터 출처
- 네이버 부동산 API
