// 숫자/날짜/갭 포맷 헬퍼 (기존 Python ui_components 로직 포팅)

export function toNumber(val) {
  if (val === null || val === undefined || val === "") return NaN;
  const s = String(val).replace(/,/g, "").trim();
  const n = parseFloat(s);
  return Number.isNaN(n) ? NaN : n;
}

// 만원 단위 → "X억 Y" 표기
export function formatEokwan(manwon) {
  const num = toNumber(manwon);
  if (Number.isNaN(num)) return "-";
  const v = Math.round(num);
  const eok = Math.floor(v / 10000);
  const rem = v % 10000;
  if (eok > 0 && rem > 0) return `${eok}억 ${rem.toLocaleString()}`;
  if (eok > 0) return `${eok}억`;
  if (rem > 0) return `${rem.toLocaleString()}`;
  return "-";
}

export function formatDate(ymd) {
  if (!ymd || typeof ymd !== "string") return "-";
  const parts = ymd.replace(/[-/]/g, ".").split(".");
  if (parts.length === 3) {
    return `${parts[0]}.${parts[1].padStart(2, "0")}.${parts[2].padStart(2, "0")}`;
  }
  return ymd;
}

// 갭 문자열("12.1%") → 색상 화살표 HTML
export function colorGapHtml(val) {
  if (val === null || val === undefined || typeof val !== "string") return "";
  const raw = val.replace("%", "").trim();
  if (raw === "") return "";
  const num = parseFloat(raw);
  if (Number.isNaN(num)) return val;
  if (num > 0) return `<span style="color:red;">▲${Math.abs(num).toFixed(1)}%</span>`;
  if (num < 0) return `<span style="color:blue;">▼${Math.abs(num).toFixed(1)}%</span>`;
  return "0.0%";
}

// 갭 문자열 → 색상 없는 화살표 텍스트
export function plainGap(val) {
  if (val === null || val === undefined || typeof val !== "string") return "";
  const raw = val.replace("%", "").trim();
  const num = parseFloat(raw);
  if (Number.isNaN(num)) return val;
  if (num > 0) return `▲${Math.abs(num).toFixed(1)}%`;
  if (num < 0) return `▼${Math.abs(num).toFixed(1)}%`;
  return "0.0%";
}

export function gapColor(text) {
  if (typeof text !== "string") return "";
  if (text.startsWith("▲")) return "red";
  if (text.startsWith("▼")) return "blue";
  return "";
}
