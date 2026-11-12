/*
 * n-measures core: count the ways one measure can be written / can sound.
 *
 * Lengths are on a grid of 96 units per whole note, the smallest grid on which
 * every allowed value is whole: 16th = 6, dotted 16th = 9, triplet eighth = 8,
 * and a 4/4 measure = 96. Results are BigInt, so they are exact at any size.
 *
 * A measure is a sequence of blocks. A block is one ordinary note (or rest),
 * or one complete triplet group whose interior is (v,v,v), (v,2v) or (2v,v)
 * for its triplet value v. A block is represented by its list of slot lengths.
 *
 * Works as a plain <script> (exposes window.NMeasures) and under CommonJS.
 */
(function (root) {
  "use strict";

  const GRID = 96;

  // Ordinary note values, length in 96ths of a whole note.
  const NOTE_VALUES = [
    { id: "whole", name: "whole",          units: 96 },
    { id: "dhalf", name: "dotted half",    units: 72 },
    { id: "half",  name: "half",           units: 48 },
    { id: "dqtr",  name: "dotted quarter", units: 36 },
    { id: "qtr",   name: "quarter",        units: 24 },
    { id: "d8th",  name: "dotted eighth",  units: 18 },
    { id: "8th",   name: "eighth",         units: 12 },
    { id: "d16th", name: "dotted 16th",    units: 9  },
    { id: "16th",  name: "16th",           units: 6  },
  ];

  // Triplet groups: triplet note value v; the group spans 3v.
  const TRIPLETS = [
    { id: "t8th",  name: "eighth-note triplets",  value: 8  },  // fills a quarter
    { id: "tqtr",  name: "quarter-note triplets", value: 16 },  // fills a half
    { id: "thalf", name: "half-note triplets",    value: 32 },  // fills a whole
  ];

  /** Blocks for the chosen ordinary lengths and triplet values. */
  function makeBlocks(noteUnits, tripletValues) {
    const blocks = noteUnits.map((d) => [d]);
    for (const v of tripletValues) blocks.push([v, v, v], [v, 2 * v], [2 * v, v]);
    return blocks;
  }

  // Main paper: ordinary and dotted values only (the default). Addendum: + triplets.
  const BASE_BLOCKS = makeBlocks(NOTE_VALUES.map((v) => v.units), []);
  const ALL_BLOCKS = makeBlocks(NOTE_VALUES.map((v) => v.units), TRIPLETS.map((t) => t.value));

  const sum = (xs) => xs.reduce((a, b) => a + b, 0);

  /** Length of one measure of a/b time, in 96ths. */
  function measureUnits(beats, beatValue) {
    if (!Number.isInteger(beats) || beats < 1) throw new Error("beats must be a positive integer");
    if (![1, 2, 4, 8, 16, 32].includes(beatValue)) throw new Error("beat value must be 1, 2, 4, 8, 16 or 32");
    return beats * (GRID / beatValue);
  }

  /**
   * Written measures, p symbols per slot (pitches + 1 for a rest):
   *   f(0) = 1,  f(t) = sum over blocks b with |b| <= t of p^(notes in b) * f(t - |b|)
   */
  function countWritten(length, p, blocks = BASE_BLOCKS) {
    const P = BigInt(p);
    const moves = blocks.map((b) => [sum(b), P ** BigInt(b.length)]);
    const f = [1n];
    for (let t = 1; t <= length; t++) {
      let s = 0n;
      for (const [span, w] of moves) if (span <= t) s += w * f[t - span];
      f.push(s);
    }
    return f[length];
  }

  /** r[n] = number of rhythms with exactly n notes; countWritten = sum r[n] p^n. */
  function rhythmsByNoteCount(length, blocks = BASE_BLOCKS) {
    const shapes = blocks.map((b) => [sum(b), b.length]);
    const rows = [[1n]];
    for (let t = 1; t <= length; t++) {
      const row = [];
      for (const [span, notes] of shapes) {
        if (span > t) continue;
        const prev = rows[t - span];
        for (let n = 0; n < prev.length; n++) {
          if (prev[n] === 0n) continue;
          row[n + notes] = (row[n + notes] || 0n) + prev[n];
        }
      }
      for (let n = 0; n < row.length; n++) if (row[n] === undefined) row[n] = 0n;
      rows.push(row);
    }
    return rows[length];
  }

  /**
   * Sounding measures (adjacent rests merge). A sound is written as a string
   * with one letter per grid unit: S = a note starts, C = it continues,
   * R = silence; it has k^(number of S) pitch choices. The possible strings
   * are exactly those some sequence of blocks can produce, which is a regular
   * language; we run its deterministic automaton (subset construction, built
   * lazily) and count weighted strings of length L. Same-sounding measures
   * give the same string, so nothing is double counted.
   */
  function countSounding(length, pitches, blocks = BASE_BLOCKS) {
    const K = BigInt(pitches);
    // Every way to fill every block, as a string.
    const strings = [];
    for (const b of blocks) {
      for (let mask = 0; mask < 1 << b.length; mask++) {
        let s = "";
        b.forEach((d, i) => { s += (mask >> i) & 1 ? "S" + "C".repeat(d - 1) : "R".repeat(d); });
        strings.push(s);
      }
    }
    // NFA states: 0 = block boundary; offset[i] + pos = inside string i at pos (pos >= 1).
    const offset = [];
    let next = 1;
    for (const s of strings) { offset.push(next - 1); next += s.length - 1; }
    const where = [];  // state id -> [string index, pos]
    strings.forEach((s, i) => { for (let pos = 1; pos < s.length; pos++) where[offset[i] + pos] = [i, pos]; });

    const stepState = (st, c, out) => {
      if (st === 0) {
        strings.forEach((s, i) => { if (s[0] === c) out.add(s.length === 1 ? 0 : offset[i] + 1); });
      } else {
        const [i, pos] = where[st];
        const s = strings[i];
        if (s[pos] === c) out.add(pos + 1 === s.length ? 0 : st + 1);
      }
    };
    const delta = new Map();  // "key|c" -> key of next subset ("" if dead)
    const members = new Map([["0", [0]]]);
    const go = (key, c) => {
      const k = key + "|" + c;
      if (!delta.has(k)) {
        const out = new Set();
        for (const st of members.get(key)) stepState(st, c, out);
        const list = [...out].sort((a, b) => a - b);
        const nk = list.join(",");
        if (nk && !members.has(nk)) members.set(nk, list);
        delta.set(k, nk);
      }
      return delta.get(k);
    };

    let layer = new Map([["0", 1n]]);
    for (let t = 0; t < length; t++) {
      const nextLayer = new Map();
      for (const [key, w] of layer) {
        for (const c of "SCR") {
          const nk = go(key, c);
          if (!nk) continue;
          nextLayer.set(nk, (nextLayer.get(nk) || 0n) + (c === "S" ? w * K : w));
        }
      }
      layer = nextLayer;
    }
    let total = 0n;
    for (const [key, w] of layer) if (members.get(key)[0] === 0) total += w;  // contains boundary state 0
    return total;
  }

  // ---- pitch helpers -------------------------------------------------------

  const LETTER_OFFSETS = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

  /** "A0", "C#4", "Bb3", "C8" -> MIDI number (C4 = 60). */
  function parsePitch(str) {
    const m = /^\s*([A-Ga-g])(#{1,2}|b{1,2}|x)?(-?\d+)\s*$/.exec(str);
    if (!m) throw new Error(`can't read pitch "${str}" (try A0, C4, F#5, Bb2)`);
    const acc = !m[2] ? 0 : m[2] === "x" ? 2 : m[2][0] === "#" ? m[2].length : -m[2].length;
    return 12 * (parseInt(m[3], 10) + 1) + LETTER_OFFSETS[m[1].toUpperCase()] + acc;
  }

  /** Distinct keys (sounding pitches) from lo to hi inclusive. */
  function keysInRange(lo, hi) {
    return Math.max(0, hi - lo + 1);
  }

  /** Distinct spellings (letter + accidental + octave) whose pitch is in range. */
  function spellingsInRange(lo, hi, maxAccidental) {
    let n = 0;
    for (let octave = -2; octave <= 10; octave++)
      for (const off of Object.values(LETTER_OFFSETS))
        for (let acc = -maxAccidental; acc <= maxAccidental; acc++) {
          const m = 12 * (octave + 1) + off + acc;
          if (m >= lo && m <= hi) n++;
        }
    return n;
  }

  // ---- presentation helpers -----------------------------------------------
  // Everything here works on the decimal string of the BigInt, so nothing is
  // ever converted to a floating-point Number (which would round past 2^53
  // and overflow to Infinity past ~1.8e308).

  /**
   * Split a BigInt into a rounded mantissa and exponent with `digits`
   * significant digits (round half-up, with carry: 9.9996 -> 1.000e+1).
   * Returns null if the number is short enough to print in full.
   */
  function sciParts(big, digits = 4) {
    const s = (big < 0n ? -big : big).toString();
    if (s.length <= digits) return null;
    let exponent = s.length - 1;
    let mantissa = BigInt(s.slice(0, digits)) + (s[digits] >= "5" ? 1n : 0n);
    if (mantissa.toString().length > digits) { mantissa /= 10n; exponent += 1; }
    const m = mantissa.toString();
    return { sign: big < 0n ? "-" : "", mantissa: `${m[0]}.${m.slice(1)}`, exponent };
  }

  /** Plain-text scientific notation: "4.100 × 10^31". */
  function scientific(big, digits = 4) {
    const p = sciParts(big, digits);
    return p ? `${p.sign}${p.mantissa} × 10^${p.exponent}` : big.toString();
  }

  /** HTML scientific notation: "4.100 × 10<sup>31</sup>". */
  function scientificHTML(big, digits = 4) {
    const p = sciParts(big, digits);
    return p ? `${p.sign}${p.mantissa} × 10<sup>${p.exponent}</sup>` : withCommas(big);
  }

  /** Exact integer with thousands separators. */
  function withCommas(big) {
    return big.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  /** part/total as a percentage rounded to 0.01, using integer arithmetic only. */
  function share(part, total) {
    if (total === 0n) return "0%";
    const hundredths = (part * 20000n + total) / (2n * total); // round half-up
    if (hundredths === 0n && part > 0n) return "<0.01%";
    return `${hundredths / 100n}.${(hundredths % 100n).toString().padStart(2, "0")}%`;
  }

  /** Approximate log10 of a BigInt, for prose like "about 10^31.6" only. */
  function log10(big) {
    const s = big.toString();
    return Math.log10(Number(s.slice(0, 16))) + (s.length - Math.min(16, s.length));
  }

  const api = {
    GRID, NOTE_VALUES, TRIPLETS, makeBlocks, BASE_BLOCKS, ALL_BLOCKS, measureUnits, rhythmsByNoteCount,
    countWritten, countSounding, parsePitch, keysInRange, spellingsInRange,
    sciParts, scientific, scientificHTML, withCommas, share, log10,
  };

  if (typeof module === "object" && module.exports) module.exports = api;
  else root.NMeasures = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
