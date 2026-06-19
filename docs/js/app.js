import { formatEokwan, formatDate, colorGapHtml, plainGap, gapColor } from "./format.js";
import { getBuyRecommendation, getBubbleGrade, computeGapSeries } from "./metrics.js";
import { renderRealPriceChart, renderRangeChart } from "./charts.js";

const DATA_BASE = "data/";
const PERIODS = { "5": [5, 3, 1], "3": [3, 1], "1": [1] };

let INDEX = null;
const complexCache = {};

async function fetchComplex(complexNo) {
  if (complexCache[complexNo]) return complexCache[complexNo];
  const res = await fetch(`${DATA_BASE}complexes/${complexNo}.json`);
  if (!res.ok) throw new Error(`단지 데이터 로드 실패: ${complexNo}`);
  const data = await res.json();
  complexCache[complexNo] = data;
  return data;
}

// ---------- 드롭다운(시도→시군구→동→단지→평형) ----------
function uniq(arr) { return Array.from(new Set(arr)); }
function setOptions(sel, items, placeholder) {
  sel.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = ""; opt0.textContent = placeholder;
  sel.appendChild(opt0);
  for (const it of items) {
    const o = document.createElement("option");
    o.value = it; o.textContent = it;
    sel.appendChild(o);
  }
}

function regionsFor(sido, sigungu) {
  return INDEX.regions.filter(
    (r) => (!sido || r.sido === sido) && (!sigungu || r.sigungu === sigungu));
}

function initSelector(prefix) {
  const sido = document.getElementById(`sido_${prefix}`);
  const sigungu = document.getElementById(`sigungu_${prefix}`);
  const dong = document.getElementById(`dong_${prefix}`);
  const complex = document.getElementById(`complex_${prefix}`);
  const pyeong = document.getElementById(`pyeong_${prefix}`);

  setOptions(sido, uniq(INDEX.regions.map((r) => r.sido)), "시/도");
  [sigungu, dong, complex, pyeong].forEach((s) => setOptions(s, [], s.dataset.ph));

  sido.onchange = () => {
    setOptions(sigungu, uniq(regionsFor(sido.value).map((r) => r.sigungu)), "시/군/구");
    setOptions(dong, [], "읍/면/동"); setOptions(complex, [], "단지"); setOptions(pyeong, [], "평형");
  };
  sigungu.onchange = () => {
    setOptions(dong, uniq(regionsFor(sido.value, sigungu.value).map((r) => r.dong)), "읍/면/동");
    setOptions(complex, [], "단지"); setOptions(pyeong, [], "평형");
  };
  dong.onchange = () => {
    const region = INDEX.regions.find(
      (r) => r.sido === sido.value && r.sigungu === sigungu.value && r.dong === dong.value);
    const names = region ? region.complexes.map((c) => c.complexName) : [];
    setOptions(complex, names, "단지");
    setOptions(pyeong, [], "평형");
  };
  complex.onchange = () => {
    const region = INDEX.regions.find(
      (r) => r.sido === sido.value && r.sigungu === sigungu.value && r.dong === dong.value);
    const c = region && region.complexes.find((x) => x.complexName === complex.value);
    setOptions(pyeong, c ? c.pyeongs : [], "평형");
  };
}

function getSelection(prefix) {
  const sido = document.getElementById(`sido_${prefix}`).value;
  const sigungu = document.getElementById(`sigungu_${prefix}`).value;
  const dong = document.getElementById(`dong_${prefix}`).value;
  const complexName = document.getElementById(`complex_${prefix}`).value;
  const pyeong = document.getElementById(`pyeong_${prefix}`).value;
  if (!complexName || !pyeong) return null;
  const region = INDEX.regions.find(
    (r) => r.sido === sido && r.sigungu === sigungu && r.dong === dong);
  const c = region && region.complexes.find((x) => x.complexName === complexName);
  if (!c) return null;
  return { complexNo: c.complexNo, complexName, pyeong };
}

// ---------- 렌더링 ----------
function buildSeries(data, pyeong, allowed) {
  const p = data.byPyeong[pyeong];
  const deals = (p ? p.deals : []).filter((d) => allowed.includes(d.class));
  const buckets = {};
  for (const d of deals) {
    if (d.amount == null || !d.date) continue;
    const ym = d.date.split("-").slice(0, 2).join("-");
    (buckets[ym] = buckets[ym] || []).push(d.amount / 10000);
  }
  const monthly = Object.keys(buckets).sort().map((ym) => ({
    ym, eok: buckets[ym].reduce((a, b) => a + b, 0) / buckets[ym].length,
  }));
  return {
    label: `${data.complexName} ${pyeong}평`,
    monthly,
    deals: deals.map((d) => ({
      date: d.date, amount: d.amount, eok: d.amount / 10000,
      floor: d.floor, pyeongType: d.pyeongType, complexName: data.complexName,
    })),
  };
}

function deals5y(data, pyeong) {
  const p = data.byPyeong[pyeong];
  return (p ? p.deals : []).filter((d) => [5, 3, 1].includes(d.class));
}

function median(arr) {
  const a = arr.filter((x) => x != null).sort((x, y) => x - y);
  if (!a.length) return null;
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

function renderBasic(selected) {
  const headers = ["아파트명", "세대수(임대)", "사용승인", "동 수", "최고층수", "세대당 주차대수",
    "용적률", "건폐율", "배정 초교(도보)", "평형구성", "매물수", "매물등록률"];
  const rows = selected.map(({ data }) => {
    const b = data.basic;
    const hh = b.totalHouseholdCount != null
      ? `${Math.round(b.totalHouseholdCount).toLocaleString()}(${Math.round(b.totalLeaseHouseholdCount || 0).toLocaleString()})` : "";
    const school = b.schoolName ? `${b.schoolName}(${b.walkTime != null ? Math.round(b.walkTime) + "분" : "-"})` : "";
    return [data.complexName, hh, formatDate(b.useApproveYmd),
      b.totalDongCount != null ? Math.round(b.totalDongCount) : "",
      b.highFloor != null ? Math.round(b.highFloor) : "",
      b.parkingCountByHousehold != null ? b.parkingCountByHousehold.toFixed(2) : "",
      b.batlRatio != null ? `${Math.round(b.batlRatio)}%` : "",
      b.btlRatio != null ? `${Math.round(b.btlRatio)}%` : "",
      school, b.pyoengNames || "",
      b.dealCount != null ? Math.round(b.dealCount) : "", b.saleRate || ""];
  });
  return tableHtml(headers, rows);
}

function tableHtml(headers, rows, rawCols = []) {
  let h = "<table class='grid'><thead><tr>";
  for (const head of headers) h += `<th>${head}</th>`;
  h += "</tr></thead><tbody>";
  for (const row of rows) {
    h += "<tr>";
    row.forEach((cell, i) => {
      const c = rawCols.includes(i) ? cell : escapeHtml(String(cell ?? ""));
      h += `<td>${c}</td>`;
    });
    h += "</tr>";
  }
  return h + "</tbody></table>";
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
}

function renderMetrics(selected, gapIndex) {
  const bubbleCell = ({ data, pyeong }) => {
    const list = (data.byPyeong[pyeong]?.listings || []).map((l) => l.bubble);
    const med = median(list);
    if (med == null) return "-";
    const score = Math.round(med);
    const [grade, guide] = getBubbleGrade(score);
    return `${score}점 (${grade})<br><span class='muted'>${guide}</span>`;
  };
  let gapCell = "-";
  if (gapIndex != null) {
    const gi = Math.round(gapIndex);
    const [grade, guide] = getBuyRecommendation(gi);
    gapCell = `${gi}점 (${grade})<br><span class='muted'>${guide}</span>`;
  }
  const r1 = selected[0], r2 = selected[1];
  return `<table class='grid center'><thead><tr>
      <th>아파트</th><th>갭 지수</th><th>버블 지수</th></tr></thead><tbody>
    <tr><td>${r1.data.complexName}<br>${r1.pyeong}평</td>
        <td rowspan='2'>${gapCell}</td><td>${bubbleCell(r1)}</td></tr>
    <tr><td>${r2.data.complexName}<br>${r2.pyeong}평</td><td>${bubbleCell(r2)}</td></tr>
    </tbody></table>`;
}

function renderRealTable(series) {
  const all = [];
  for (const s of series) for (const d of s.deals) all.push({ ...d, name: s.label });
  all.sort((a, b) => (a.date < b.date ? 1 : -1));
  const rows = all.map((d) => [formatDate(d.date), d.complexName, d.pyeongType || "-",
    d.floor != null ? d.floor : "-", formatEokwan(d.amount)]);
  return tableHtml(["거래일", "아파트명", "평형타입", "층수", "실거래가"], rows);
}

function buildCombos(selected) {
  return selected.map(({ data, pyeong }) => {
    const p = data.byPyeong[pyeong] || {};
    const st = p.stats || {};
    const maxDate = st.maxDate ? `(${formatDate(st.maxDate)})` : "";
    const minDate = st.minDate ? `(${formatDate(st.minDate)})` : "";
    return {
      complexName: data.complexName, pyeong,
      min: st.min5 != null ? st.min5 / 10000 : null,
      max: st.max5 != null ? st.max5 / 10000 : null,
      star: st.latestAmount != null ? st.latestAmount / 10000 : null,
      starAmount: st.latestAmount, starDate: st.latestDate,
      starFloor: st.latestFloor != null ? Math.round(st.latestFloor) : null,
      maxStr: st.max5 != null ? `${formatEokwan(st.max5)}${maxDate}` : "-",
      minStr: st.min5 != null ? `${formatEokwan(st.min5)}${minDate}` : "-",
      listings: (p.listings || []).map((l) => ({
        priceEok: l.price != null ? l.price / 10000 : null,
        priceText: l.priceText || "-", type: l.pyeongName || "-",
        floor: l.floorInfo || "-", gapHtml: colorGapHtml(l.maxGap),
      })),
    };
  });
}

function renderListingTable(selected) {
  const headers = ["아파트명", "층수", "호가", "평형타입", "공급/전용(㎡)", "방향", "동",
    "매물등록일", "전고점 갭", "전저점 갭", "KB일반", "전세가율", "상세 설명", "중개사", "링크"];
  const rows = [];
  for (const { data, pyeong } of selected) {
    const list = (data.byPyeong[pyeong]?.listings || []).slice()
      .sort((a, b) => (a.price || 0) - (b.price || 0));
    for (const l of list) {
      const link = `https://new.land.naver.com/complexes/${data.complexNo}?articleNo=${l.articleNo}`;
      rows.push([
        data.complexName, l.floorInfo || "", formatEokwan(l.price), l.pyeongName || "",
        `${l.area1 != null ? Math.round(l.area1) : ""}/${l.area2 != null ? Math.round(l.area2) : ""}`,
        l.direction || "", l.buildingName || "", formatDate(l.confirmYmd),
        gapSpan(plainGap(l.maxGap)), gapSpan(plainGap(l.minGap)),
        formatEokwan(l.kbAvg), l.leasePerDealRate || "",
        l.desc || "", l.realtor || "",
        `<a href='${link}' target='_blank' rel='noopener'>🔗</a>`,
      ]);
    }
  }
  const rawCols = [8, 9, 14];
  return tableHtml(headers, rows, rawCols);
}

function gapSpan(text) {
  const color = gapColor(text);
  return color ? `<span style='color:${color}'>${text}</span>` : escapeHtml(text || "");
}

async function runAnalysis() {
  const out = document.getElementById("content");
  const s1 = getSelection("1"), s2 = getSelection("2");
  if (!s1 || !s2) {
    out.innerHTML = "<p class='info'>아파트 1과 아파트 2의 단지·평형을 모두 선택한 뒤 '분석 실행'을 눌러주세요.</p>";
    return;
  }
  out.innerHTML = "<p class='info'>불러오는 중…</p>";
  let d1, d2;
  try {
    [d1, d2] = await Promise.all([fetchComplex(s1.complexNo), fetchComplex(s2.complexNo)]);
  } catch (e) {
    out.innerHTML = `<p class='error'>${e.message}</p>`;
    return;
  }
  const selected = [{ data: d1, pyeong: s1.pyeong }, { data: d2, pyeong: s2.pyeong }];

  const summaryGap = computeGapSeries(deals5y(d1, s1.pyeong), deals5y(d2, s2.pyeong));
  const gapIndex = summaryGap ? summaryGap.gapIndex : null;

  out.innerHTML = `
    <section><h2>📄 기본 정보</h2>${renderBasic(selected)}</section>
    <section><h2>📌 투자 지표 요약</h2>${renderMetrics(selected, gapIndex)}</section>
    <section><h2>📈 실거래가 추이</h2>
      <div class="period">
        <label><input type="radio" name="period" value="5" checked> 최근 5년간</label>
        <label><input type="radio" name="period" value="3"> 최근 3년간</label>
        <label><input type="radio" name="period" value="1"> 최근 1년간</label>
      </div>
      <div id="chart_real"></div>
      <div id="real_table"></div>
    </section>
    <section><h2>📊 매물 현황</h2><div id="chart_range"></div>
      <div id="listing_table">${renderListingTable(selected)}</div>
    </section>`;

  const drawPeriod = (period) => {
    const allowed = PERIODS[period];
    const series = selected.map(({ data, pyeong }) => buildSeries(data, pyeong, allowed));
    const chartGap = computeGapSeries(
      series[0].deals.map((d) => ({ ...d, class: 1 })),
      series[1].deals.map((d) => ({ ...d, class: 1 })));
    renderRealPriceChart("chart_real", series, chartGap);
    document.getElementById("real_table").innerHTML = renderRealTable(series);
  };
  drawPeriod("5");
  document.querySelectorAll("input[name=period]").forEach((r) =>
    r.addEventListener("change", (e) => drawPeriod(e.target.value)));

  renderRangeChart("chart_range", buildCombos(selected));
}

async function main() {
  try {
    const res = await fetch(`${DATA_BASE}index.json`);
    if (!res.ok) throw new Error("no data");
    INDEX = await res.json();
  } catch (e) {
    document.getElementById("content").innerHTML =
      "<p class='info'>아직 수집된 데이터가 없습니다. 첫 데이터 수집(GitHub Actions)이 실행되면 표시됩니다.</p>";
    return;
  }
  document.getElementById("updated").textContent = `데이터 갱신: ${INDEX.updatedAt}`;
  initSelector("1");
  initSelector("2");
  document.getElementById("run").addEventListener("click", runAnalysis);
}

main();
