# n-measures

How many possible measures of music are there? This project counts them exactly.

For one measure of 4/4 on the 88 keys of a piano, with note values from 16th notes to whole notes (dotted included):

- it can be **written** in **207,500,798,751,709,995,948,691,861,325,549,855** ways (about 2.08 × 10³⁵), counting sharp/flat spellings and rests;
- it can **sound** in **40,935,886,428,964,117,905,911,001,094,097** distinct ways (about 4.09 × 10³¹), with each key counted once and adjacent rests merged.

Adding eighth-, quarter- and half-note triplets (the addendum) raises these to about 2.21 × 10³⁵ and 4.51 × 10³¹.

**Website:** https://gabebecker2048.github.io/n-measures/

- [Paper](https://gabebecker2048.github.io/n-measures/): the derivation, written like a math paper
- [Addendum](https://gabebecker2048.github.io/n-measures/addendum.html): the same count with triplets
- [Calculator](https://gabebecker2048.github.io/n-measures/calculator.html): any pitch range, time signature, set of note values and triplets
- [Story](https://gabebecker2048.github.io/n-measures/story.html): how the problem came about and how it was solved

## The idea in one line

Count in 32nd notes, so a 4/4 measure is 32 units and the note values are D = {2, 3, 4, 6, 8, 12, 16, 24, 32}. With p symbols (pitches + 1 for a rest):

```
f(0) = 1
f(t) = p · Σ_{d in D, d ≤ t} f(t − d)
```

The answer is f(32).

With triplets (the addendum), count in 96ths instead, and each complete triplet group with triplet value v ∈ {8, 16, 32} adds one term:

```
f(t) = p · Σ_{d in D, d ≤ t} f(t − d)  +  (p³ + 2p²) · Σ_{v in V, 3v ≤ t} f(t − 3v)
```

The sounding count with triplets uses a small finite automaton; see the addendum.

All arithmetic uses exact arbitrary-precision integers (JavaScript `BigInt`, Python `int`), so nothing rounds or overflows.

## Repository layout

| Path | What it is |
|---|---|
| `docs/` | The static website (GitHub Pages serves this folder) |
| `docs/counter.js` | The counting code used by the site |
| `python/nmeasures.py` | Python implementation and command-line tool |
| `python/test_nmeasures.py` | Tests |

## Python

No dependencies; Python 3.9+.

```
python3 python/nmeasures.py                       # 4/4, piano range, sharp/flat spellings, no triplets
python3 python/nmeasures.py --breakdown                # written count, by number of notes
python3 python/nmeasures.py --mode sounding            # sounding count
python3 python/nmeasures.py --triplets                # the addendum's model, with triplets
python3 python/nmeasures.py --ties                    # also allow ties
python3 python/nmeasures.py --time 6/8 --low C4 --high C5 --mode sounding
python3 python/nmeasures.py --help

python3 -m unittest discover python -v            # run the tests
```

## Running the site locally

```
python3 -m http.server -d docs 8000
```

Then open http://localhost:8000.

## Publishing

In the GitHub repository: **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/docs`**.
