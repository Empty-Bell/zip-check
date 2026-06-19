// 투자 지표 계산 (기존 Python 로직 포팅)

// 갭 지수 → 매수 추천 등급
export function getBuyRecommendation(gapIndex) {
  if (gapIndex === null || Number.isNaN(gapIndex)) return ["", ""];
  if (gapIndex >= 80) return ["유의 🔴", "갭이 큰 상태입니다."];
  if (gapIndex >= 40) return ["중립 🟡", "갭이 다소 있는 편 입니다."];
  return ["추천 🟢", "갭이 작은 상태입니다."];
}

// 버블 지수 → 등급
export function getBubbleGrade(bubbleIndex) {
  if (bubbleIndex === null || Number.isNaN(bubbleIndex)) return ["", ""];
  if (bubbleIndex > 100) return ["높음 🔴", "매물 가격대가 매우 높습니다."];
  if (bubbleIndex >= 80) return ["주의 🟡", "매물 가격대가 다소 높습니다."];
  return ["보통 🟢", "매물 가격대가 적정 수준입니다."];
}

function yearMonth(dateStr) {
  // "2025-09-01" → "2025-09"
  if (!dateStr) return null;
  const parts = String(dateStr).split("-");
  if (parts.length < 2) return null;
  return `${parts[0]}-${parts[1]}`;
}

// 한 단지-평형의 deals → {month: 평균 억} 맵
function monthlyMeanEok(deals) {
  const buckets = {};
  for (const d of deals) {
    if (d.amount === null || d.amount === undefined) continue;
    const ym = yearMonth(d.date);
    if (!ym) continue;
    (buckets[ym] = buckets[ym] || []).push(d.amount / 10000.0);
  }
  const out = {};
  for (const ym of Object.keys(buckets)) {
    const arr = buckets[ym];
    out[ym] = arr.reduce((a, b) => a + b, 0) / arr.length;
  }
  return out;
}

function ffillBfill(arr) {
  const out = arr.slice();
  // forward fill
  for (let i = 1; i < out.length; i++) {
    if (out[i] === null && out[i - 1] !== null) out[i] = out[i - 1];
  }
  // backward fill
  for (let i = out.length - 2; i >= 0; i--) {
    if (out[i] === null && out[i + 1] !== null) out[i] = out[i + 1];
  }
  return out;
}

// 두 단지-평형의 실거래로 월별 갭 시계열과 갭 지수를 계산
// 반환: { months[], gaps[], estimated[], gapIndex } 또는 null
export function computeGapSeries(dealsA, dealsB) {
  const mA = monthlyMeanEok(dealsA);
  const mB = monthlyMeanEok(dealsB);
  const months = Array.from(new Set([...Object.keys(mA), ...Object.keys(mB)])).sort();
  if (months.length === 0) return null;

  const rawA = months.map((m) => (m in mA ? mA[m] : null));
  const rawB = months.map((m) => (m in mB ? mB[m] : null));
  const a = ffillBfill(rawA);
  const b = ffillBfill(rawB);

  const gaps = [];
  const estimated = [];
  for (let i = 0; i < months.length; i++) {
    if (a[i] === null || b[i] === null) {
      gaps.push(null);
      estimated.push(true);
      continue;
    }
    gaps.push(Math.abs(a[i] - b[i]));
    // 직전 값과 동일하면(=채워진 값) 추정치로 표시
    const filledA = i === 0 ? true : a[i] !== a[i - 1];
    const filledB = i === 0 ? true : b[i] !== b[i - 1];
    estimated.push(!filledA || !filledB);
  }

  const realGaps = gaps.filter((g, i) => g !== null && !estimated[i]);
  const allReal = gaps.filter((g) => g !== null);
  const maxGap = Math.max(...(realGaps.length ? realGaps : allReal));
  const minGap = Math.min(...(realGaps.length ? realGaps : allReal));
  const latestGap = gaps[gaps.length - 1];

  let gapIndex = null;
  if (maxGap - minGap > 0 && latestGap !== null) {
    gapIndex = (1 - (maxGap - latestGap) / (maxGap - minGap)) * 100;
  } else if (latestGap !== null) {
    gapIndex = 0;
  }
  return { months, gaps, estimated, gapIndex };
}
