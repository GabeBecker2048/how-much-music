/* Fills the result tables of the paper (index.html) and the addendum
 * (addendum.html) from counter.js, so the papers and the calculator always
 * show the same numbers. The static rows in the HTML are the fallback when
 * JavaScript is off. Which page we are on is read from <main data-model>. */
(function () {
  "use strict";
  const N = window.NMeasures;
  const main = document.querySelector("main[data-model]");
  if (!N || !main) return;
  const withTriplets = main.dataset.model === "triplets";

  const BASE = N.BASE_BLOCKS;  // ordinary and dotted values only
  const TRIP = N.ALL_BLOCKS;   // + eighth/quarter/half-note triplets
  const L = N.measureUnits(4, 4);
  const lo = N.parsePitch("A0"), hi = N.parsePitch("C8");
  const keys = N.keysInRange(lo, hi);
  const spell1 = N.spellingsInRange(lo, hi, 1);
  const spell2 = N.spellingsInRange(lo, hi, 2);

  const cell = (big) => (big < 100000000n ? N.withCommas(big) : "≈ " + N.scientificHTML(big));
  const bold = (html) => `<b>${html}</b>`;
  const totalRhythms = (B) => N.rhythmsByNoteCount(L, B).reduce((a, b) => a + b, 0n);

  // The model this page headlines.
  const B = withTriplets ? TRIP : BASE;
  const written = N.countWritten(L, spell1 + 1, B);
  const sounding = N.countSounding(L, keys, B);

  if (!withTriplets) {
    // Table 1: [label, p or k, count, headline?]
    const rows = [
      ["<b>Written</b> (♯/♭ spellings + rest)", spell1 + 1, written, true],
      [`<b>Sounding</b> (${keys} keys, rests merged)`, keys, sounding, true],
      ["Rhythms only", 1, totalRhythms(BASE), false],
      ["Written, also 𝄪/𝄫 spellings", spell2 + 1, N.countWritten(L, spell2 + 1, BASE), false],
      ["One symbol per key + rest (mixed)", keys + 1, N.countWritten(L, keys + 1, BASE), false],
    ];
    document.querySelector("#t-main tbody").innerHTML = rows
      .map(([label, p, v, head]) => `<tr><td>${label}</td><td>${p}</td><td>${head ? bold(cell(v)) : cell(v)}</td></tr>`)
      .join("");
  } else {
    // Table A2: [label, [without triplets, with triplets], headline?]
    const pair = (fn) => [fn(BASE), fn(TRIP)];
    const rows = [
      ["<b>Written</b> (♯/♭ spellings + rest, <i>p</i> = 155)", pair((b) => N.countWritten(L, spell1 + 1, b)), true],
      [`<b>Sounding</b> (${keys} keys, rests merged)`, pair((b) => N.countSounding(L, keys, b)), true],
      ["Rhythms only", pair(totalRhythms), false],
      [`Written, also 𝄪/𝄫 spellings (<i>p</i> = ${spell2 + 1})`, pair((b) => N.countWritten(L, spell2 + 1, b)), false],
      [`One symbol per key + rest (<i>p</i> = ${keys + 1})`, pair((b) => N.countWritten(L, keys + 1, b)), false],
    ];
    document.querySelector("#t-main tbody").innerHTML = rows
      .map(([label, [without, withT], head]) =>
        `<tr><td>${label}</td><td>${cell(without)}</td><td>${head ? bold(cell(withT)) : cell(withT)}</td></tr>`)
      .join("");
  }

  const ew = document.getElementById("exact-written");
  const es = document.getElementById("exact-sounding");
  if (ew) ew.textContent = N.withCommas(written);
  if (es) es.textContent = N.withCommas(sounding);

  // Breakdown by number of notes, p = 155.
  const rhythms = N.rhythmsByNoteCount(L, B);
  const P = BigInt(spell1 + 1);
  document.querySelector("#t-breakdown tbody").innerHTML = rhythms
    .map((r, n) => ({ n, r, ways: r * P ** BigInt(n) }))
    .filter((x) => x.r > 0n)
    .map((x) => `<tr><td>${x.n}</td><td>${N.withCommas(x.r)}</td><td>${N.scientificHTML(x.ways)}</td><td>${N.share(x.ways, written)}</td></tr>`)
    .join("") +
    `<tr class="total"><td><b>Total</b></td><td><b>${N.withCommas(totalRhythms(B))}</b></td><td><b>${N.scientificHTML(written)}</b></td><td><b>100.00%</b></td></tr>`;
})();
