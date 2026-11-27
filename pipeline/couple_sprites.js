// Style C "bold geometric" couple (Srini picked C, 2026-11-26). Writes transparent PNG sprites:
//   pipeline/assets/characters/couple_c/<him|her>_<mood>.png   (600x810, figure in a 200x270 box at 3x)
// Usage: node pipeline/couple_sprites.js
const path = require('path'), fs = require('fs');
const { chromium } = require('playwright');
const INK = '#15100f', OR = '#e04a1a', TINT = '#fce2d4', CREAM = '#f9f5ef';
const P = (d, o = {}) => `<path d="${d}" fill="${o.f || 'none'}" stroke="${o.s || INK}" stroke-width="${o.w || 5}" stroke-linecap="round" stroke-linejoin="round"/>`;
const C = (x, y, r, o = {}) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${o.f || 'none'}" stroke="${o.s || 'none'}" stroke-width="${o.w || 0}"/>`;
function face(x, y, mood, w, talk = 0) {
  // talk 1|2: the same face with a half / fully open mouth, for lip-sync (happy and neutral only)
  const M = (d) => talk ? '' : d;
  const open = () => talk ? C(x, y + 28, 0, {}) + `<ellipse cx="${x}" cy="${y + 28}" rx="${talk === 1 ? 11 : 13}" ry="${talk === 1 ? 6 : 11}" fill="${INK}"/>` + (talk === 2 ? `<ellipse cx="${x}" cy="${y + 33}" rx="7" ry="4" fill="#e8806a"/>` : '') : '';
  let s = ''; const ex = 22, dot = (sx, dx = 0, dy = 0) => C(x + sx * ex + dx, y + dy, 5.5, { f: INK });
  const cheeks = () => C(x - ex - 6, y + 16, 7, { f: TINT }) + C(x + ex + 6, y + 16, 7, { f: TINT });
  if (mood === 'happy') {
    for (const sx of [-1, 1]) s += P(`M${x + sx * ex - 9},${y + 3} Q${x + sx * ex},${y - 9} ${x + sx * ex + 9},${y + 3}`, { w });
    s += P(`M${x - ex - 8},${y - 20} Q${x - ex},${y - 26} ${x - ex + 8},${y - 22}`, { w: w * .8 }) + P(`M${x + ex - 8},${y - 22} Q${x + ex},${y - 26} ${x + ex + 8},${y - 20}`, { w: w * .8 });
    s += M(P(`M${x - 16},${y + 22} Q${x},${y + 40} ${x + 16},${y + 22} Z`, { w, f: INK })) + open() + cheeks();
  } else if (mood === 'neutral') {
    s += dot(-1) + dot(1);
    s += M(P(`M${x - 12},${y + 26} Q${x},${y + 32} ${x + 12},${y + 26}`, { w })) + open();
  } else if (mood === 'worried') {
    for (const sx of [-1, 1]) s += dot(sx) + P(`M${x + sx * (ex + 10)},${y - 16} L${x + sx * (ex - 8)},${y - 24}`, { w: w * .8 });
    s += P(`M${x - 14},${y + 32} Q${x - 7},${y + 24} ${x},${y + 30} Q${x + 7},${y + 36} ${x + 14},${y + 28}`, { w });
    s += P(`M${x + ex + 22},${y - 30} q-5,8 0,12 q5,-4 0,-12`, { w: 3, f: '#bfe0f5', s: '#6aa8d0' });
  } else if (mood === 'sad') {
    for (const sx of [-1, 1]) s += dot(sx, 0, 2) + P(`M${x + sx * (ex + 10)},${y - 14} L${x + sx * (ex - 8)},${y - 22}`, { w: w * .8 });
    s += P(`M${x - 14},${y + 34} Q${x},${y + 22} ${x + 14},${y + 34}`, { w });
  } else if (mood === 'frustrated') {
    for (const sx of [-1, 1]) s += dot(sx, 0, 3) + P(`M${x + sx * (ex + 11)},${y - 24} L${x + sx * (ex - 9)},${y - 14}`, { w: w * .9 });
    s += P(`M${x - 15},${y + 34} Q${x},${y + 22} ${x + 15},${y + 34}`, { w });
    s += P(`M${x + ex + 20},${y - 44} l8,-10 M${x + ex + 30},${y - 34} l12,-4 M${x + ex + 26},${y - 40} l11,-9`, { w: 4, s: OR });
  } else { // confused
    s += dot(-1, 3) + dot(1, 3);
    s += P(`M${x - ex - 8},${y - 20} L${x - ex + 8},${y - 20}`, { w: w * .8 }) + P(`M${x + ex - 8},${y - 24} Q${x + ex},${y - 32} ${x + ex + 8},${y - 26}`, { w: w * .8 });
    s += P(`M${x - 12},${y + 28} L${x + 12},${y + 24}`, { w });
  }
  return s;
}
function fig(who, mood, talk = 0) {
  let s = '', w = 8;
  s += P(`M88,150 L88,176 M112,150 L112,176`, { w });                                       // neck
  s += P(`M38,262 L44,190 Q100,168 156,190 L162,262`, { w, s: who === 'her' ? OR : INK, f: CREAM });
  if (who === 'her') s += P(`M44,112 Q44,40 100,40 Q156,40 156,112 L156,176 L44,176Z`, { w, f: INK });
  s += C(100, 104, 52, { f: CREAM, s: INK, w });
  if (who === 'him') s += P(`M48,100 Q52,48 100,48 Q150,48 152,100 L128,76 L100,88 L72,76Z`, { w: w * .7, f: INK });
  else s += P(`M50,96 Q70,56 120,60 Q140,64 150,92 Q100,92 50,96Z`, { w: w * .7, f: INK });
  return s + face(100, 112, mood, 6, talk);
}
(async () => {
  const out = path.join(__dirname, 'assets', 'characters', 'couple_c'); fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 200, height: 270 }, deviceScaleFactor: 3 });
  for (const who of ['him', 'her']) for (const mood of ['happy', 'neutral', 'worried', 'sad', 'confused', 'frustrated']) {
    await p.setContent(`<html><body style="margin:0;background:transparent"><svg width="200" height="270" viewBox="0 -4 200 274">${fig(who, mood)}</svg></body></html>`);
    await p.screenshot({ path: path.join(out, `${who}_${mood}.png`), omitBackground: true });
  }
  for (const who of ['him', 'her']) for (const mood of ['happy', 'neutral']) for (const talk of [1, 2]) {   // lip-sync mouths
    await p.setContent(`<html><body style="margin:0;background:transparent"><svg width="200" height="270" viewBox="0 -4 200 274">${fig(who, mood, talk)}</svg></body></html>`);
    await p.screenshot({ path: path.join(out, `${who}_${mood}_m${talk}.png`), omitBackground: true });
  }
  await b.close();
})();
