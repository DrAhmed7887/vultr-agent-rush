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

// ---------- Year 6 skills ----------
const OPSIGN = { 1: "+", 2: "−", 3: "×", 4: "÷" };
const opApply = (op, x, y) => (op === 1 ? x + y : op === 2 ? x - y : op === 3 ? x * y : x / y);
const deg = (v) => (v < 0 ? `−${-v}` : String(v));
// a decimal from (digits, places); places can be negative (digits moved past the ones place)
function tensText(d, p) {
  if (p < 0) { d *= 10 ** -p; p = 0; }
  if (p === 0) return d.toLocaleString("en-GB");
  const s = String(d).padStart(p + 1, "0");
  return `${Number(s.slice(0, -p)).toLocaleString("en-GB")}.${s.slice(-p)}`;
}
// an answer from his code, only if it's a sensible (digits, places) pair
const tensOk = (o) => Array.isArray(o) && o.length === 2 && Number.isInteger(o[0]) && Number.isInteger(o[1]) && o[0] >= 0 && o[0] < 1e15 && Math.abs(o[1]) <= 12;
function tensTruth(d, p, z) { const q = p - z; return q >= 0 ? [d, q] : [d * 10 ** -q, 0]; }

function placeChart(args, hisOut) {
  const [d, p, z] = args;
  const rows = [[tensText(d, p), "num", ""]];
  const t = tensTruth(d, p, z), right = tensText(...t);
  if (tensOk(hisOut) && tensText(...hisOut) !== right) rows.push([tensText(...hisOut), "his", "Ahmes"]);
  rows.push([right, "true", `× ${(10 ** z).toLocaleString("en-GB")}`]);
  const split = (txt) => { const [i, f = ""] = txt.replace(/,/g, "").split("."); return [i, f]; };
  const intW = Math.max(...rows.map((r) => split(r[0])[0].length)), fracW = Math.max(...rows.map((r) => split(r[0])[1].length));
  // the short headings UK classrooms use: Th H T O . t h th
  const NAMES = ["O", "T", "H", "Th", "TTh", "HTh", "M"];
  const FR = ["t", "h", "th", "", "", ""];
  const head = [...Array(intW).keys()].reverse().map((i) => `<th>${NAMES[i] || ""}</th>`).join("") +
    (fracW ? `<th class="dot"></th>` + [...Array(fracW).keys()].map((i) => `<th>${FR[i] || ""}</th>`).join("") : "");
  const body = rows.map(([txt, kind, label]) => {
    const [i, f] = split(txt);
    const cells = i.padStart(intW, " ").split("").map((c) => `<td>${c.trim()}</td>`).join("") +
      (fracW ? `<td class="dot">${f ? "." : ""}</td>` + f.padEnd(fracW, " ").split("").map((c) => `<td>${c.trim()}</td>`).join("") : "");
    return `<tr class="pv-${kind}"><th class="pv-label">${esc(label)}</th>${cells}</tr>`;
  }).join("");
  const svg = `<table class="pv" aria-label="Place value chart"><thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody></table>`;
  const caption = `Every digit moves ${z} place${z > 1 ? "s" : ""} to the left: ${tensText(d, p)} × ${(10 ** z).toLocaleString("en-GB")} = ${right}.`;
  return { svg, caption, zoom: "" };
}

function compareBars(args) {
  const [t1, b1, t2, b2] = args;
  const v1 = t1 / b1, v2 = t2 / b2, maxV = Math.max(1, v1, v2);
  const W = 340, L = 60, R = W - 10, H = 30, unit = (R - L) / maxV;
  const bar = (t, b, y, label) => {
    let s = `<text x="${L - 10}" y="${y + H / 2 + 5}" text-anchor="end" class="fb-label">${label}</text>`;
    const wholes = Math.max(1, Math.ceil(t / b));
    for (let w = 0; w < wholes; w++) for (let i = 0; i < b; i++) {
      const on = w * b + i < t, sw = unit / b;
      s += `<rect x="${L + w * unit + i * sw}" y="${y}" width="${sw}" height="${H}" class="fb-cell ${on ? "fb-on fb-true" : "fb-off"}"/>`;
    }
    return s;
  };
  const svg = `<svg viewBox="0 0 ${W} 92" class="fb" role="img" aria-label="Two fraction bars">${bar(t1, b1, 8, `${t1}/${b1}`)}${bar(t2, b2, 52, `${t2}/${b2}`)}</svg>`;
  const eq = t1 * b2 === t2 * b1, big = t1 * b2 > t2 * b1 ? `${t1}/${b1}` : `${t2}/${b2}`;
  return { svg, caption: eq ? `${t1}/${b1} and ${t2}/${b2} fill exactly the same amount. They're equal.` : `${big} fills more of its bar, so ${big} is bigger.`, zoom: "" };
}

function opsSteps(args, hisOut) {
  const [a, o1, b, o2, c, br] = args;
  const inner = br === 2 || (br === 0 && o2 >= 3 && o1 <= 2);
  const right = inner ? [`${b} ${OPSIGN[o2]} ${c} = ${opApply(o2, b, c)}`, `${a} ${OPSIGN[o1]} ${opApply(o2, b, c)} = ${opApply(o1, a, opApply(o2, b, c))}`]
    : [`${a} ${OPSIGN[o1]} ${b} = ${opApply(o1, a, b)}`, `${opApply(o1, a, b)} ${OPSIGN[o2]} ${c} = ${opApply(o2, opApply(o1, a, b), c)}`];
  const total = inner ? opApply(o1, a, opApply(o2, b, c)) : opApply(o2, opApply(o1, a, b), c);
  const ltr = [`${a} ${OPSIGN[o1]} ${b} = ${opApply(o1, a, b)}`, `${opApply(o1, a, b)} ${OPSIGN[o2]} ${c} = ${opApply(o2, opApply(o1, a, b), c)}`];
  const col = (title, steps, kind) => `<div class="ops-col ops-${kind}"><p class="ops-title">${title}</p><ol>${steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol></div>`;
  const hisWrong = typeof hisOut === "number" && hisOut !== total;
  const svg = `<div class="ops-cols">${hisWrong ? col("Ahmes went left to right", ltr, "his") : ""}${col("The right order", right, "true")}</div>`;
  const why = br === 2 ? "Brackets come first." : inner ? "Times and divide come before plus and take away." : "Here, going left to right is already the right order.";
  return { svg, caption: `${why} The answer is ${total}.`, zoom: "" };
}

function tempLine(args) {
  const [s, e] = args;
  const lo = Math.min(s, 0) - 1, hi = Math.max(e, 0) + 1, W = 340, L = 14, R = W - 14, Y = 70;
  const x = (v) => L + ((v - lo) / (hi - lo)) * (R - L);
  let ticks = "";
  for (let v = lo; v <= hi; v++) {
    const big = v === 0 || v % 5 === 0;
    ticks += `<line x1="${x(v)}" y1="${Y - (big ? 8 : 4)}" x2="${x(v)}" y2="${Y + (big ? 8 : 4)}" class="nl-tick"/>`;
    if (v === 0 || v === s || v === e) ticks += `<text x="${x(v)}" y="${Y + 26}" text-anchor="middle" class="nl-end">${deg(v)}</text>`;
  }
  const arc = (a, b, label) => {
    const mx = (x(a) + x(b)) / 2, h = Math.min(46, 12 + Math.abs(x(b) - x(a)) / 3);
    return `<path d="M${x(a)} ${Y - 8} Q${mx} ${Y - 8 - h * 2} ${x(b)} ${Y - 8}" class="t-arc"/><text x="${mx}" y="${Y - 12 - h}" text-anchor="middle" class="nl-label nl-true">${label}</text>`;
  };
  const across = s < 0 && e > 0;
  const jumps = across ? arc(s, 0, `${-s}`) + arc(0, e, `${e}`) : arc(s, e, `${e - s}`);
  const svg = `<svg viewBox="0 0 ${W} 104" class="nl" role="img" aria-label="Thermometer number line">
    <line x1="${L}" y1="${Y}" x2="${R}" y2="${Y}" class="nl-axis"/>${ticks}${jumps}</svg>`;
  const caption = across ? `From ${deg(s)} up to 0 is ${-s}. From 0 up to ${e} is ${e}. That's ${e - s} degrees altogether.`
    : `From ${deg(s)} up to ${deg(e)} is ${e - s} degrees.`;
  return { svg, caption, zoom: "" };
}

const VIEWS = {
  dec_compare: { proof: (a, o) => decimalLine(a, o) },
  frac_add: { proof: (a, o) => fractionBars(a, o) },
  tens: {
    proof: placeChart,
    problem: (a, o, ring) => {
      const [d, p, z] = a;
      const ans = tensOk(o) ? tensText(o[0], o[1]) : "?";
      return `<p class="q">Times it</p><p class="nums">${tensText(d, p)}<span class="or">×</span>${(10 ** z).toLocaleString("en-GB")}<span class="or">=</span><span class="num ${ring}">${ans}</span></p>`;
    },
  },
  frac_compare: {
    proof: compareBars,
    problem: (a, o, ring) => {
      const f = (t, b) => `<span class="frac"><span>${t}</span><span>${b}</span></span>`;
      const n = (t, b, i) => `<span class="num${o === i ? ` ${ring}` : ""}">${f(t, b)}</span>`;
      const mid = o === 0 ? `<span class="num ${ring}">=</span>` : `<span class="or">or</span>`;
      return `<p class="q">Which is bigger?</p><p class="nums">${n(a[0], a[1], 1)}${mid}${n(a[2], a[3], 2)}</p>`;
    },
  },
  ops: {
    proof: opsSteps,
    problem: (a, o, ring) => {
      const [x, o1, y, o2, z, br] = a;
      const t = br === 2 ? `${x} ${OPSIGN[o1]} (${y} ${OPSIGN[o2]} ${z})` : br === 1 ? `(${x} ${OPSIGN[o1]} ${y}) ${OPSIGN[o2]} ${z}` : `${x} ${OPSIGN[o1]} ${y} ${OPSIGN[o2]} ${z}`;
      return `<p class="q">Work it out</p><p class="nums ops-nums">${esc(t)}<span class="or">=</span><span class="num ${ring}">${typeof o === "number" ? o : "?"}</span></p>`;
    },
  },
  intervals: {
    proof: tempLine,
    problem: (a, o, ring) => `<p class="q">It was ${deg(a[0])}°C. Then it warmed up to ${deg(a[1])}°C. How many degrees did it go up?</p>
      <p class="nums"><span class="num ${ring}">${typeof o === "number" ? o : "?"}</span><span class="or">degrees</span></p>`,
  },
};

function proofForView(view, args, hisOut) { return VIEWS[view].proof(args, hisOut); }
function problemForView(view, args, hisOut, mark) {
  const ring = mark === "ok" ? "ring-ok" : mark === "bad" ? "ring-bad" : "ring-his";
  if (VIEWS[view].problem) return VIEWS[view].problem(args, hisOut, ring);
  return problemHTML(view === "dec_compare" ? "compare_decimals" : "add_fractions", args, hisOut, mark);
}
