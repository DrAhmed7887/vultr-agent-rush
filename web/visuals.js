"use strict";
// Pictures that show WHY an answer is right or wrong, drawn from exact integers (no floats).
// Decimals: a number line, zoomed to the place where the two numbers first differ.
// Fractions: bars cut into equal parts, his answer next to the real one.

const SVGNS = "http://www.w3.org/2000/svg";
const pow10 = (n) => 10 ** n;
const decText = (whole, digits, places) => `${whole}.${String(digits).padStart(places, "0")}`;

function decimalLine(args, hisOut) {
  const [w1, d1, p1, w2, d2, p2] = args;
  const P = Math.max(p1, p2);
  const a = w1 * pow10(P) + d1 * pow10(P - p1);
  const b = w2 * pow10(P) + d2 * pow10(P - p2);
  const A = decText(w1, d1, p1), B = decText(w2, d2, p2);
  const truth = a > b ? 1 : b > a ? 2 : 0;
  // zoom: the first place (tenths = 1) where the two differ
  const sa = String(a).padStart(P + 1, "0"), sb = String(b).padStart(P + 1, "0");
  let k = 1;
  while (k <= P && sa[sa.length - P + k - 1] === sb[sb.length - P + k - 1]) k++;
  if (k > P) k = P;
  const unit = pow10(P - k + 1);
  const lo = Math.floor(Math.min(a, b) / unit) * unit;
  const W = 340, L = 20, R = W - 20, Y = 62;
  const x = (v) => L + ((v - lo) / unit) * (R - L);
  const fmt = (v) => (v / pow10(P)).toFixed(k).replace(/0+$/, "").replace(/\.$/, "") || "0";
  let ticks = "";
  for (let j = 0; j <= 10; j++) {
    const v = lo + (j * unit) / 10, big = j === 0 || j === 10 || j === 5;
    ticks += `<line x1="${x(v)}" y1="${Y - (big ? 9 : 5)}" x2="${x(v)}" y2="${Y + (big ? 9 : 5)}" class="nl-tick"/>`;
    if (j === 0 || j === 10) ticks += `<text x="${x(v)}" y="${Y + 28}" class="nl-end" text-anchor="middle">${fmt(v)}</text>`;
  }
  // side: "mid" centres the label; "left"/"right" push labels apart when the dots are close
  const dot = (v, label, who, side) => {
    const cls = who === "his" ? "nl-his" : who === "true" ? "nl-true" : "nl-pt";
    const anchor = side === "left" ? "end" : side === "right" ? "start" : "middle";
    const tx = x(v) + (side === "left" ? 4 : side === "right" ? -4 : 0);
    return `<g class="${cls}"><circle cx="${x(v)}" cy="${Y}" r="7"/>
      <line x1="${x(v)}" y1="${Y - 8}" x2="${tx}" y2="${Y - 20}" class="nl-lead"/>
      <text x="${tx}" y="${Y - 24}" text-anchor="${anchor}" class="nl-label">${label}</text></g>`;
  };
  let pts;
  if (a === b) pts = dot(a, `${A} = ${B}`, "true", "mid");
  else {
    const left = a < b ? [a, A, 1] : [b, B, 2], right = a < b ? [b, B, 2] : [a, A, 1];
    const tag = (n) => (n === hisOut && n !== truth ? "his" : n === truth ? "true" : "pt");
    const close = x(right[0]) - x(left[0]) < 70;
    pts = dot(left[0], left[1], tag(left[2]), close ? "left" : "mid") + dot(right[0], right[1], tag(right[2]), close ? "right" : "mid");
  }
  const zoom = k > 1 ? `Zoomed in between ${fmt(lo)} and ${fmt(lo + unit)}.` : "";
  const svg = `<svg viewBox="0 0 ${W} 100" class="nl" role="img" aria-label="Number line showing ${A} and ${B}">
    <line x1="${L}" y1="${Y}" x2="${R}" y2="${Y}" class="nl-axis"/>${ticks}${pts}</svg>`;
  const bigger = truth === 1 ? A : B;
  const caption = truth === 0
    ? `${A} and ${B} land on the same spot. They're equal: the extra zero doesn't change it.`
    : `${bigger} is further along the line, so ${bigger} is bigger.`;
  return { svg, caption, zoom, truth };
}

function gcd(a, b) { a = Math.abs(a); b = Math.abs(b); while (b) [a, b] = [b, a % b]; return a || 1; }

function fractionBars(args, hisOut) {
  const [t1, b1, t2, b2] = args;
  let tt = t1 * b2 + t2 * b1, tb = b1 * b2;
  const g = gcd(tt, tb); tt /= g; tb /= g;
  const his = Array.isArray(hisOut) && hisOut.length === 2 && hisOut[1] > 0 ? hisOut : null;
  const rows = [[`${t1}/${b1}`, t1, b1, "part"], [`${t2}/${b2}`, t2, b2, "part"]];
  if (his && !(his[0] * tb === tt * his[1])) rows.push([`Ahmes: ${his[0]}/${his[1]}`, his[0], his[1], "his"]);
  rows.push([`Really: ${tt}/${tb}`, tt, tb, "true"]);
  const maxV = Math.max(1, ...rows.map((r) => r[1] / r[2]));
  const W = 340, L = 104, R = W - 12, H = 26, gap = 12;
  const unitW = (R - L) / maxV;
  let body = "";
  rows.forEach(([label, top, bottom, kind], i) => {
    const y = 8 + i * (H + gap);
    const wholes = Math.max(1, Math.ceil(top / bottom));
    body += `<text x="${L - 10}" y="${y + H / 2 + 5}" text-anchor="end" class="fb-label fb-${kind}">${label}</text>`;
    for (let w = 0; w < wholes; w++) {
      const segs = Math.min(bottom, 24), sw = unitW / segs;
      for (let s = 0; s < segs; s++) {
        const filled = w * bottom + s < top;
        body += `<rect x="${L + w * unitW + s * sw}" y="${y}" width="${sw}" height="${H}" class="fb-cell ${filled ? `fb-on fb-${kind}` : "fb-off"}"/>`;
      }
    }
  });
  const h = 8 + rows.length * (H + gap);
  const svg = `<svg viewBox="0 0 ${W} ${h}" class="fb" role="img" aria-label="Fraction bars">${body}</svg>`;
  let caption = `${t1}/${b1} + ${t2}/${b2} is really ${tt}/${tb}.`;
  if (his) {
    const hisV = his[0] / his[1], biggest = Math.max(t1 / b1, t2 / b2);
    if (his[0] * tb === tt * his[1]) caption = `${his[0]}/${his[1]} is the same amount as ${tt}/${tb}. He's right!`;
    else if (hisV < biggest) caption = `Look: Ahmes's ${his[0]}/${his[1]} is smaller than ${t1 / b1 >= t2 / b2 ? `${t1}/${b1}` : `${t2}/${b2}`} on its own. Adding can't make it smaller!`;
    else caption = `Ahmes's bar doesn't match. Really it's ${tt}/${tb}.`;
  }
  return { svg, caption, zoom: "" };
}

function proofFor(skill, args, hisOut) {
  return skill === "compare_decimals" ? decimalLine(args, hisOut) : fractionBars(args, hisOut);
}

// The problem as a big homework line, with his answer circled in teacher's red pen.
function problemHTML(skill, args, hisOut, mark) {
  const ring = mark === "ok" ? "ring-ok" : mark === "bad" ? "ring-bad" : "ring-his";
  if (skill === "compare_decimals") {
    const [w1, d1, p1, w2, d2, p2] = args;
    const A = decText(w1, d1, p1), B = decText(w2, d2, p2);
    const n = (txt, i) => `<span class="num${hisOut === i ? ` ${ring}` : ""}">${txt}</span>`;
    const eq = hisOut === 0 ? `<span class="num ${ring}">=</span>` : `<span class="or">or</span>`;
    return `<p class="q">Which is bigger?</p><p class="nums">${n(A, 1)}${eq}${n(B, 2)}</p>`;
  }
  const [t1, b1, t2, b2] = args;
  const f = (t, b) => `<span class="frac"><span>${t}</span><span>${b}</span></span>`;
  const ans = Array.isArray(hisOut) ? `<span class="num ${ring}">${f(hisOut[0], hisOut[1])}</span>` : `<span class="num ${ring}">?</span>`;
  return `<p class="q">Add them up</p><p class="nums">${f(t1, b1)}<span class="or">+</span>${f(t2, b2)}<span class="or">=</span>${ans}</p>`;
}
