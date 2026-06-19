// Plotly.js 차트 (기존 render_visualization 시각화 포팅)
import { formatEokwan, formatDate } from "./format.js";

const PALETTE = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"];

// 실거래가 추이: 월별 라인 + 일자별 마커 + 갭 바차트(보조축)
export function renderRealPriceChart(divId, series, gapSeries) {
  const traces = [];
  const colorMap = {};
  series.forEach((s, i) => (colorMap[s.label] = PALETTE[i % PALETTE.length]));

  // 갭 바차트 (보조 y축)
  if (gapSeries && series.length === 2) {
    const xs = gapSeries.months.map((m) => `${m}-01`);
    const realX = [], realY = [], estX = [], estY = [];
    gapSeries.months.forEach((m, i) => {
      if (gapSeries.gaps[i] === null) return;
      if (gapSeries.estimated[i]) { estX.push(`${m}-01`); estY.push(gapSeries.gaps[i]); }
      else { realX.push(`${m}-01`); realY.push(gapSeries.gaps[i]); }
    });
    if (realX.length) traces.push({
      type: "bar", x: realX, y: realY, name: "실거래가 갭", yaxis: "y2",
      marker: { color: "rgba(180,180,180,0.6)" },
      hovertemplate: "갭 금액: %{y:.1f}억<extra></extra>",
    });
    if (estX.length) traces.push({
      type: "bar", x: estX, y: estY, name: "실거래가 갭(추정)", yaxis: "y2",
      marker: { color: "rgba(180,180,180,0.2)" },
      hovertemplate: "갭 금액(추정): %{y:.1f}억<extra></extra>",
    });
  }

  // 월별 평균 라인
  for (const s of series) {
    if (!s.monthly.length) continue;
    traces.push({
      type: "scatter", mode: "lines", name: s.label,
      x: s.monthly.map((m) => `${m.ym}-01`),
      y: s.monthly.map((m) => m.eok),
      line: { color: colorMap[s.label] }, hoverinfo: "skip",
    });
  }

  // 일자별 실거래 마커
  for (const s of series) {
    if (!s.deals.length) continue;
    traces.push({
      type: "scatter", mode: "markers", showlegend: false,
      x: s.deals.map((d) => d.date),
      y: s.deals.map((d) => d.eok),
      marker: { size: 6, opacity: 0.3, color: colorMap[s.label] },
      text: s.deals.map((d) =>
        `${d.complexName}<br>${formatDate(d.date)}<br>${d.pyeongType || "-"} / ${
          d.floor != null ? d.floor + "층" : "-"
        }<br>${formatEokwan(d.amount)}`),
      hovertemplate: "%{text}<extra></extra>",
    });
  }

  const layout = {
    hovermode: "closest", autosize: true, bargap: 0.3,
    margin: { l: 20, r: 20, t: 40, b: 10 },
    xaxis: { tickformat: "'%y.%m월", hoverformat: "'%y.%m월" },
    yaxis: { tickformat: ".0f", ticksuffix: "억" },
    yaxis2: { overlaying: "y", side: "right", showgrid: false, tickformat: ".1f", ticksuffix: "억" },
    legend: { orientation: "h", x: 0.01, y: 1.15, bgcolor: "rgba(0,0,0,0)" },
  };
  Plotly.newPlot(divId, traces, layout, { responsive: true, displayModeBar: false });
}

// 매물 현황: 단지-평형별 전고저 레인지 + 호가 산점도 + 최신 실거래 별표
export function renderRangeChart(divId, combos) {
  const traces = [];
  const shapes = [];
  const tickvals = [], ticktext = [];
  let lastApt = null;

  combos.forEach((c, x) => {
    tickvals.push(x);
    ticktext.push(`${c.complexName} ${c.pyeong}평`);
    if (lastApt !== null && c.complexName !== lastApt) {
      shapes.push({
        type: "line", xref: "x", yref: "paper",
        x0: x - 0.5, x1: x - 0.5, y0: 0, y1: 1,
        line: { color: "gray", dash: "dot" },
      });
    }
    lastApt = c.complexName;

    // 전고저 세로 레인지
    if (c.min != null && c.max != null) {
      traces.push({
        type: "scatter", mode: "lines", showlegend: false,
        x: [x, x], y: [c.min, c.max], line: { color: "blue", width: 1 },
        hovertemplate: `최근 5년 전고점 : ${c.maxStr}<br>최근 5년 전저점 : ${c.minStr}<extra></extra>`,
      });
      traces.push({
        type: "scatter", mode: "lines", showlegend: false,
        x: [x - 0.1, x + 0.1], y: [c.max, c.max], line: { color: "blue", width: 1 },
        hovertemplate: `최근 5년 전고점 : ${c.maxStr}<extra></extra>`,
      });
      traces.push({
        type: "scatter", mode: "lines", showlegend: false,
        x: [x - 0.1, x + 0.1], y: [c.min, c.min], line: { color: "blue", width: 1 },
        hovertemplate: `최근 5년 전저점 : ${c.minStr}<extra></extra>`,
      });
    }

    // 호가 산점도
    if (c.listings.length) {
      traces.push({
        type: "scatter", mode: "markers", showlegend: false,
        x: c.listings.map(() => x),
        y: c.listings.map((l) => l.priceEok),
        marker: { size: 8, color: "red", opacity: 0.3 },
        customdata: c.listings.map((l) => [l.type, l.floor, l.priceText, l.gapHtml]),
        hovertemplate:
          "평형타입: %{customdata[0]}<br>층수: %{customdata[1]}<br>호가: %{customdata[2]}<br>전고점 갭: %{customdata[3]}<extra></extra>",
      });
    }

    // 최신 실거래 별표
    if (c.star != null && c.star > 0) {
      const floorStr = c.starFloor != null ? `(${c.starFloor}층)` : "";
      traces.push({
        type: "scatter", mode: "markers+text", showlegend: false,
        x: [x], y: [c.star],
        text: [`최신 실거래가<br>${formatEokwan(c.starAmount)}${floorStr}<br>${formatDate(c.starDate)}`],
        textposition: "middle right", textfont: { color: "black", size: 11 },
        marker: { symbol: "star", size: 15, color: "yellow", line: { color: "black", width: 1 } },
        hoverinfo: "none",
      });
    }
  });

  const layout = {
    hovermode: "closest", autosize: true, height: 500,
    margin: { l: 10, r: 10, t: 10, b: 10 }, shapes,
    xaxis: { range: [-0.5, combos.length - 0.5], tickmode: "array", tickvals, ticktext },
    yaxis: { ticksuffix: "억", zeroline: true },
  };
  Plotly.newPlot(divId, traces, layout, { responsive: true, displayModeBar: false });
}
