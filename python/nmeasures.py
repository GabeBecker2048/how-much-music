#!/usr/bin/env python3
"""Count the ways a single measure of music can be written or can sound.

Durations are measured on a grid of 96 units per whole note, the smallest grid
on which every allowed value is a whole number of units: a 16th is 6, a dotted
16th 9, a triplet eighth 8, and a 4/4 measure is 96.

A measure is a sequence of *blocks*. A block is either one ordinary note (or
rest), or one complete triplet group, whose interior is one of the rhythms
(v, v, v), (v, 2v), (2v, v) for its triplet value v. Every slot in a block
holds a pitch or a rest. By default there are no triplets (the main paper's
model); pass blocks=ALL_BLOCKS, or --triplets on the command line, for the
addendum's model.

All counts are exact: Python ints have arbitrary precision, and big results
are never converted to float.

Examples:
    python3 python/nmeasures.py
    python3 python/nmeasures.py --mode sounding
    python3 python/nmeasures.py --breakdown
    python3 python/nmeasures.py --triplets              # the addendum's model
    python3 python/nmeasures.py --time 6/8 --low C4 --high C5 --ties
"""
from __future__ import annotations

import argparse
import re
from functools import cache

GRID = 96  # units per whole note

# Ordinary note value -> length in 96ths of a whole note.
NOTE_VALUES: dict[str, int] = {
    "whole": 96,
    "dotted-half": 72,
    "half": 48,
    "dotted-quarter": 36,
    "quarter": 24,
    "dotted-eighth": 18,
    "eighth": 12,
    "dotted-16th": 9,
    "16th": 6,
}

# Triplet group -> its triplet note value v. The group spans 3v units:
# eighth-note triplets fill a quarter, quarter-note triplets a half,
# half-note triplets a whole note. (16th-note triplets are excluded: a
# triplet 16th is shorter than a 16th.)
TRIPLETS: dict[str, int] = {
    "eighth": 8,
    "quarter": 16,
    "half": 32,
}

LETTER_OFFSETS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

Block = tuple[int, ...]  # slot lengths of one block


def make_blocks(values=tuple(NOTE_VALUES), triplets=tuple(TRIPLETS)) -> tuple[Block, ...]:
    """All blocks for the chosen ordinary values and triplet types."""
    blocks: list[Block] = [(NOTE_VALUES[v],) for v in values]
    for name in triplets:
        v = TRIPLETS[name]
        blocks += [(v, v, v), (v, 2 * v), (2 * v, v)]
    return tuple(blocks)


# Main paper: ordinary and dotted values only (the default). Addendum: + triplets.
BASE_BLOCKS = make_blocks(triplets=())
ALL_BLOCKS = make_blocks()
NO_TRIPLETS = BASE_BLOCKS  # alias


# ---------------------------------------------------------------------------
# Measure and pitch helpers
# ---------------------------------------------------------------------------

def measure_units(beats: int, beat_value: int) -> int:
    """Length of one measure of `beats`/`beat_value` time, in 96ths."""
    if beats < 1:
        raise ValueError("beats must be a positive integer")
    if beat_value not in (1, 2, 4, 8, 16, 32):
        raise ValueError("beat value must be 1, 2, 4, 8, 16 or 32")
    return beats * GRID // beat_value


def parse_pitch(text: str) -> int:
    """'A0', 'C#4', 'Bb3', 'Fx2', 'C8' -> MIDI note number (C4 = 60)."""
    m = re.fullmatch(r"\s*([A-Ga-g])(#{1,2}|b{1,2}|x)?(-?\d+)\s*", text)
    if not m:
        raise ValueError(f"can't read pitch {text!r} (try A0, C4, F#5, Bb2)")
    letter, acc, octave = m.groups()
    shift = 0 if not acc else 2 if acc == "x" else len(acc) * (1 if acc[0] == "#" else -1)
    return 12 * (int(octave) + 1) + LETTER_OFFSETS[letter.upper()] + shift


def keys_in_range(lo: int, hi: int) -> int:
    """Number of distinct sounding pitches (piano keys) from lo to hi inclusive."""
    return max(0, hi - lo + 1)


def spellings_in_range(lo: int, hi: int, max_accidental: int = 1) -> int:
    """Number of (letter, accidental, octave) spellings whose pitch lies in [lo, hi].

    max_accidental: 0 = naturals only, 1 = sharps/flats, 2 = also double sharps/flats.
    """
    count = 0
    for octave in range(-2, 11):
        for offset in LETTER_OFFSETS.values():
            for acc in range(-max_accidental, max_accidental + 1):
                if lo <= 12 * (octave + 1) + offset + acc <= hi:
                    count += 1
    return count


# ---------------------------------------------------------------------------
# Counting written measures (memoized recursion)
#
# Each count is a recursive function of the remaining length t, cached with
# functools.cache so every t is computed once. A cold call f(1536) would
# recurse hundreds of levels deep and can hit Python's recursion limit, so
# each function is "warmed" bottom-up: calling f(0), f(1), ..., f(length) in
# order means every call finds its sub-results cached and recurses at most
# one level.
# ---------------------------------------------------------------------------

def _warm(fn, length: int):
    for t in range(length + 1):
        fn(t)
    return fn(length)


def count_written(length: int, p: int, blocks=BASE_BLOCKS) -> int:
    """Ways to write a measure of `length` units with `p` symbols (pitches + 1 rest).

        f(0) = 1,   f(t) = sum over blocks b with |b| <= t of  p^(notes in b) * f(t - |b|)

    Without triplets every block is a single note and this is
    f(t) = p * sum_d f(t - d).
    """
    weighted = tuple((sum(b), p ** len(b)) for b in blocks)

    @cache
    def f(t: int) -> int:
        if t == 0:
            return 1
        return sum(w * f(t - span) for span, w in weighted if span <= t)

    return _warm(f, length)


def rhythms_by_note_count(length: int, blocks=BASE_BLOCKS) -> tuple[int, ...]:
    """r[n] = number of rhythms with exactly n notes; count_written == sum r[n] p^n."""
    shapes = tuple((sum(b), len(b)) for b in blocks)

    @cache
    def r(t: int) -> tuple[int, ...]:
        if t == 0:
            return (1,)
        out: list[int] = []
        for span, notes in shapes:
            if span > t:
                continue
            for n, c in enumerate(r(t - span)):
                if c:
                    while len(out) <= n + notes:
                        out.append(0)
                    out[n + notes] += c
        return tuple(out)

    return _warm(r, length)


def count_written_with_ties(length: int, pitches: int, blocks=BASE_BLOCKS) -> int:
    """Written measures where any note may be tied to the following note.

    A tie continues the previous pitched note, so after a pitched slot each
    note slot has pitches + 1 (rest) + 1 (tie) options; otherwise pitches + 1.
    State: whether the measure so far ends on a pitched note (P) or not (R).
    Each block acts as a 2x2 transfer matrix between these states.
    """
    def transfer(block: Block):
        # m[a][b]: ways to fill the block entering in state a, leaving in state b
        m = [[0, 0], [0, 0]]
        for start in (0, 1):  # 0 = R, 1 = P
            vec = [1 - start, start]
            for _ in block:
                vec = [vec[0] + vec[1],                                  # rest
                       pitches * (vec[0] + vec[1]) + vec[1]]             # new pitch, or tie
            m[start] = vec
        return sum(block), m

    mats = tuple(transfer(b) for b in blocks)

    @cache
    def state(t: int) -> tuple[int, int]:
        if t == 0:
            return (1, 0)
        r = p = 0
        for span, m in mats:
            if span <= t:
                pr, pp = state(t - span)
                r += pr * m[0][0] + pp * m[1][0]
                p += pr * m[0][1] + pp * m[1][1]
        return (r, p)

    return sum(_warm(state, length))


# ---------------------------------------------------------------------------
# Counting sounding measures (automaton)
#
# A sound is fixed by when each note starts, how long it lasts, and its pitch.
# Write its rhythm as a string with one letter per grid unit:
#     S = a note starts here,  C = a note continues,  R = silence.
# The sound has k^(number of S) pitch choices. A string is possible exactly
# when some sequence of blocks (with each slot a note or a rest) produces it,
# so the possible strings form a regular language. Distinct sounds are counted
# by running the deterministic automaton for that language (built on the fly
# by the subset construction) and counting the weighted strings of length L.
# Two written measures that sound the same give the same string, so nothing
# is double counted.
# ---------------------------------------------------------------------------

class _SoundAutomaton:
    def __init__(self, blocks, ties: bool):
        # Every way to fill each block: (string, needs_previous_note, ends_on_note).
        strings = []
        for block in blocks:
            for mask in range(1 << len(block)):
                notes = [(mask >> i) & 1 for i in range(len(block))]
                options = [""]
                needs = [False]
                for i, (d, is_note) in enumerate(zip(block, notes)):
                    tie_ok = ties and is_note and (i == 0 or notes[i - 1])
                    new_opts, new_needs = [], []
                    for s, nd in zip(options, needs):
                        if is_note:
                            new_opts.append(s + "S" + "C" * (d - 1)); new_needs.append(nd)
                            if tie_ok:
                                new_opts.append(s + "C" * d); new_needs.append(nd or i == 0)
                        else:
                            new_opts.append(s + "R" * d); new_needs.append(nd)
                    options, needs = new_opts, new_needs
                for s, nd in zip(options, needs):
                    strings.append((s, nd, bool(notes[-1])))
        self.strings = strings
        self.start_free = frozenset([("start", 0)])
        self._delta: dict = {}

    def _step(self, state, c):
        if state[0] == "start":
            for i, (s, needs_note, ends_note) in enumerate(self.strings):
                if needs_note and not state[1]:
                    continue
                if s[0] == c:
                    yield ("start", int(ends_note)) if len(s) == 1 else (i, 1)
        else:
            i, pos = state
            s, _, ends_note = self.strings[i]
            if s[pos] == c:
                yield ("start", int(ends_note)) if pos + 1 == len(s) else (i, pos + 1)

    def delta(self, subset, c):
        key = (subset, c)
        if key not in self._delta:
            self._delta[key] = frozenset(x for st in subset for x in self._step(st, c))
        return self._delta[key]

    @staticmethod
    def accepting(subset) -> bool:
        return ("start", 0) in subset or ("start", 1) in subset


def count_sounding(length: int, pitches: int, blocks=BASE_BLOCKS, ties: bool = False) -> int:
    """Distinct sounding measures (adjacent rests merge; tied notes merge if ties=True).

        g(t, Q) = number of weighted strings of length t readable from DFA state Q
                = [t == 0 and Q accepting] + sum_c w(c) * g(t - 1, delta(Q, c))
    with w(S) = pitches and w(C) = w(R) = 1. The answer is g(length, start).
    """
    dfa = _SoundAutomaton(blocks, ties)
    weights = (("S", pitches), ("C", 1), ("R", 1))

    @cache
    def g(t: int, subset) -> int:
        if t == 0:
            return int(dfa.accepting(subset))
        total = 0
        for c, w in weights:
            nxt = dfa.delta(subset, c)
            if nxt:
                total += w * g(t - 1, nxt)
        return total

    # Warm bottom-up over every reachable (t, subset) to keep recursion shallow.
    layers = [{dfa.start_free}]
    for _ in range(length):
        layers.append({n for q in layers[-1] for c, _ in weights if (n := dfa.delta(q, c))})
    for t in range(length + 1):
        for q in layers[length - t]:
            g(t, q)
    return g(length, dfa.start_free)


# ---------------------------------------------------------------------------
# Formatting (string-based, so huge ints never touch float)
# ---------------------------------------------------------------------------

def format_sci(n: int, digits: int = 4) -> str:
    """Scientific notation with `digits` significant digits, rounded half-up.

    Works on the decimal string, so it is exact for ints of any size
    (float() would overflow above ~1.8e308).
    """
    if n < 0:
        return "-" + format_sci(-n, digits)
    s = str(n)
    if len(s) <= digits:
        return s
    exponent = len(s) - 1
    mantissa = int(s[:digits]) + (s[digits] >= "5")
    if mantissa == 10 ** digits:  # carry, e.g. 9.9996 -> 10.000
        mantissa //= 10
        exponent += 1
    m = str(mantissa)
    return f"{m[0]}.{m[1:]}e{exponent}"


def format_share(part: int, total: int) -> str:
    """Percentage rounded to 0.01 using integer arithmetic only."""
    if total == 0:
        return "0%"
    hundredths = (part * 10000 * 2 + total) // (2 * total)  # round half-up
    if hundredths == 0 and part > 0:
        return "<0.01%"
    return f"{hundredths // 100}.{hundredths % 100:02d}%"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Count the possible measures of music.")
    ap.add_argument("--low", default="A0", help="lowest pitch (default A0)")
    ap.add_argument("--high", default="C8", help="highest pitch (default C8)")
    ap.add_argument("--time", default="4/4", help="time signature a/b (default 4/4)")
    ap.add_argument("--mode", choices=("written", "sounding"), default="written",
                    help="written: spellings and rest groupings are distinct; "
                         "sounding: one symbol per key, adjacent rests merge")
    ap.add_argument("--accidentals", type=int, choices=(0, 1, 2), default=1,
                    help="spellings in written mode: 0 naturals, 1 sharps/flats, 2 doubles")
    ap.add_argument("--keys-only", action="store_true",
                    help="written mode: one symbol per key instead of per spelling")
    ap.add_argument("--values", nargs="+", choices=list(NOTE_VALUES), default=list(NOTE_VALUES),
                    help="allowed ordinary note values (default: all)")
    ap.add_argument("--triplets", nargs="*", choices=list(TRIPLETS), default=None, metavar="KIND",
                    help="allow triplet groups (see the addendum): --triplets alone allows "
                         "eighth, quarter and half; or name some of them. Default: none")
    ap.add_argument("--ties", action="store_true", help="allow ties between consecutive notes")
    ap.add_argument("--breakdown", action="store_true", help="show counts by number of notes")
    args = ap.parse_args(argv)

    beats, beat_value = (int(x) for x in args.time.split("/"))
    length = measure_units(beats, beat_value)
    lo, hi = parse_pitch(args.low), parse_pitch(args.high)
    triplets = () if args.triplets is None else (args.triplets or tuple(TRIPLETS))
    blocks = make_blocks(args.values, triplets)
    keys = keys_in_range(lo, hi)

    if args.mode == "written":
        symbols = keys if args.keys_only else spellings_in_range(lo, hi, args.accidentals)
        p = symbols + 1
        total = (count_written_with_ties(length, symbols, blocks) if args.ties
                 else count_written(length, p, blocks))
        what = f"{symbols} {'keys' if args.keys_only else 'spellings'} + 1 rest -> p = {p}"
    else:
        p = keys
        total = count_sounding(length, keys, blocks, ties=args.ties)
        what = f"{keys} keys, adjacent rests merged"

    trip = "triplets: " + ", ".join(triplets) if triplets else "no triplets"
    rhythms = rhythms_by_note_count(length, blocks)
    print(f"{args.time} measure, {args.low}-{args.high}, {args.mode}{', ties' if args.ties else ''}; {trip}")
    print(f"  {what}")
    print(f"  rhythms:  {sum(rhythms):,}")
    print(f"  measures: {format_sci(total)}  ({len(str(total))} digits)")
    print(f"  exact:    {total:,}")

    if args.breakdown and args.mode == "written" and not args.ties:
        print(f"\n  {'notes':>5}  {'rhythms':>10}  {'measures':>12}  {'share':>7}")
        for n, r in enumerate(rhythms):
            if r:
                ways = r * p ** n
                print(f"  {n:>5}  {r:>10,}  {format_sci(ways):>12}  {format_share(ways, total):>7}")


if __name__ == "__main__":
    main()
