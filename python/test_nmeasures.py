"""Tests for nmeasures.py. Written by Claude Opus. Run:  python3 -m unittest discover python -v"""
import unittest

import nmeasures as nm

# 4/4 = 96 units. Addendum values (all nine note values + eighth/quarter/half triplets).
WRITTEN_4_4 = 221093563947910687084921771175534030      # p = 155 (sharp/flat spellings + rest)
SOUNDING_4_4 = 45104953235466120350740861079001         # k = 88 keys, rests merged
# Main paper values, without triplets (the default).
WRITTEN_4_4_NO_TRIPLETS = 207500798751709995948691861325549855
SOUNDING_4_4_NO_TRIPLETS = 40935886428964117905911001094097


class SmallCases(unittest.TestCase):
    """Values small enough to derive by hand."""

    B = ((2,), (3,), (4,))  # three single-note blocks of lengths 2, 3, 4

    def test_written_by_hand(self):
        for p in (1, 2, 5, 89):
            f = lambda t: nm.count_written(t, p, self.B)
            self.assertEqual(f(0), 1)
            self.assertEqual(f(1), 0)                 # nothing is 1 unit long
            self.assertEqual(f(2), p)
            self.assertEqual(f(3), p)
            self.assertEqual(f(4), p * p + p)         # 2+2, or 4
            self.assertEqual(f(5), 2 * p * p)         # 2+3 or 3+2

    def test_sounding_by_hand(self):
        # Length 4, one pitch: note-note (2+2), one 4-note, one 4-silence,
        # note+silence and silence+note (2+2): 5 sounds.
        self.assertEqual(nm.count_sounding(4, 1, self.B), 5)
        # Written with p = 2 there are 6 (two short rests count separately from one long one).
        self.assertEqual(nm.count_written(4, 2, self.B), 6)

    def test_triplet_group_by_hand(self):
        # A measure that is exactly one eighth-note triplet group (24 units), with no
        # ordinary values: rhythms (8,8,8), (8,16), (16,8) -> p^3 + 2p^2 written measures.
        B = nm.make_blocks(values=(), triplets=("eighth",))
        for p in (1, 2, 7):
            self.assertEqual(nm.count_written(24, p, B), p ** 3 + 2 * p ** 2)
        # Sounding, one pitch: 16 written fillings with p = 2, but 4 repeat a sound
        # once adjacent rests merge: (8,16) note+rest and rest+rest, and (16,8)
        # rest+note and rest+rest, all already made by (8,8,8). 12 distinct sounds.
        self.assertEqual(nm.count_written(24, 2, B), 16)
        self.assertEqual(nm.count_sounding(24, 1, B), 12)

    def test_ties_by_hand(self):
        # Two 16th slots (length 12 with only 16ths), k pitches:
        # without ties (k+1)^2; ties add k (second note tied to the first).
        B = nm.make_blocks(values=("16th",), triplets=())
        for k in (1, 3, 88):
            self.assertEqual(nm.count_written_with_ties(12, k, B), (k + 1) ** 2 + k)


class GoldenValues(unittest.TestCase):
    def test_rhythms_4_4(self):
        r = nm.rhythms_by_note_count(96, nm.ALL_BLOCKS)
        self.assertEqual(sum(r), 579888)
        self.assertEqual(r[1], 1)      # whole note
        self.assertEqual(r[2], 5)      # half+half, dotted half+quarter (2 orders), half-note triplet (2 rhythms)
        self.assertEqual(r[16], 1)     # sixteen 16ths
        self.assertEqual(sum(nm.rhythms_by_note_count(96, nm.NO_TRIPLETS)), 272163)

    def test_written_4_4(self):
        self.assertEqual(nm.count_written(96, 155, nm.ALL_BLOCKS), WRITTEN_4_4)
        self.assertEqual(nm.count_written(96, 89, nm.ALL_BLOCKS), 45178577727699065296231075510328)
        self.assertEqual(nm.count_written(96, 155, nm.NO_TRIPLETS), WRITTEN_4_4_NO_TRIPLETS)
        self.assertEqual(nm.count_written(96, 89, nm.NO_TRIPLETS), 41003729853837309412520859814931)

    def test_sounding(self):
        self.assertEqual(nm.count_sounding(96, 88, nm.ALL_BLOCKS), SOUNDING_4_4)
        self.assertEqual(nm.count_sounding(96, 88, nm.NO_TRIPLETS), SOUNDING_4_4_NO_TRIPLETS)
        self.assertEqual(nm.count_sounding(72, 13, nm.ALL_BLOCKS), 661819119352782)                       # 3/4, C4-C5
        self.assertEqual(nm.count_sounding(72, 13, nm.NO_TRIPLETS), 526326204749372)

    def test_defaults_are_main_paper_model(self):
        self.assertEqual(nm.count_written(96, 155), WRITTEN_4_4_NO_TRIPLETS)
        self.assertEqual(nm.count_sounding(96, 88), SOUNDING_4_4_NO_TRIPLETS)
        self.assertEqual(sum(nm.rhythms_by_note_count(96)), 272163)
        # Main-paper ties figures (32nd grid, scaled by 3): about 2.276e35 and 4.140e31.
        self.assertEqual(nm.format_sci(nm.count_written_with_ties(96, 154)), "2.276e35")
        self.assertEqual(nm.format_sci(nm.count_sounding(96, 88, ties=True)), "4.140e31")

    def test_ties(self):
        self.assertEqual(nm.count_written_with_ties(96, 154, nm.ALL_BLOCKS), 242453108064508343500417342866565970)
        self.assertEqual(nm.count_sounding(96, 88, nm.ALL_BLOCKS, ties=True), 45683385945671177564475274018657)

    def test_spellings(self):
        lo, hi = nm.parse_pitch("A0"), nm.parse_pitch("C8")
        self.assertEqual((lo, hi), (21, 108))
        self.assertEqual(nm.keys_in_range(lo, hi), 88)
        self.assertEqual(nm.spellings_in_range(lo, hi, 0), 52)
        self.assertEqual(nm.spellings_in_range(lo, hi, 1), 154)
        self.assertEqual(nm.spellings_in_range(lo, hi, 2), 257)


class Properties(unittest.TestCase):
    def test_polynomial_matches_recurrence(self):
        for length in (1, 8, 24, 48, 72, 96, 144):
            for blocks in (nm.ALL_BLOCKS, nm.NO_TRIPLETS):
                r = nm.rhythms_by_note_count(length, blocks)
                for p in (1, 2, 89, 155, 2 ** 88):
                    self.assertEqual(sum(c * p ** n for n, c in enumerate(r)),
                                     nm.count_written(length, p, blocks), (length, p))

    def test_ties_with_one_pitch_slot_reduces(self):
        # With 0 pitches there is nothing to tie: only all-rest measures remain.
        for length in (24, 48, 96):
            self.assertEqual(nm.count_written_with_ties(length, 0), nm.count_written(length, 1))

    def test_orderings(self):
        for length in range(1, 97, 5):
            s, w = nm.count_sounding(length, 88, nm.ALL_BLOCKS), nm.count_written(length, 89, nm.ALL_BLOCKS)
            self.assertLessEqual(s, w)                                                # merging only removes
            self.assertLessEqual(nm.count_sounding(length, 88, nm.NO_TRIPLETS), s)    # triplets only add
            self.assertLessEqual(s, nm.count_sounding(length, 88, nm.ALL_BLOCKS, ties=True))         # ties only add

    def test_long_measure_no_recursion_error(self):
        total = nm.count_written(1536, 89)                 # 16 whole notes
        self.assertGreater(len(str(total)), 500)
        nm.count_written_with_ties(1536, 88)
        nm.rhythms_by_note_count(768)
        nm.count_sounding(768, 88)

    def test_measure_units(self):
        self.assertEqual(nm.measure_units(4, 4), 96)
        self.assertEqual(nm.measure_units(6, 8), 72)
        self.assertEqual(nm.measure_units(7, 16), 42)
        self.assertEqual(nm.measure_units(3, 32), 9)
        with self.assertRaises(ValueError):
            nm.measure_units(4, 3)


class Formatting(unittest.TestCase):
    def test_format_sci(self):
        self.assertEqual(nm.format_sci(WRITTEN_4_4), "2.211e35")
        self.assertEqual(nm.format_sci(SOUNDING_4_4), "4.510e31")
        self.assertEqual(nm.format_sci(40996), "4.100e4")    # rounds, doesn't truncate
        self.assertEqual(nm.format_sci(40994), "4.099e4")
        self.assertEqual(nm.format_sci(99996), "1.000e5")    # carry
        self.assertEqual(nm.format_sci(1234), "1234")
        self.assertEqual(nm.format_sci(10 ** 500), "1.000e500")  # beyond float range

    def test_format_share(self):
        self.assertEqual(nm.format_share(1, 3), "33.33%")
        self.assertEqual(nm.format_share(2, 3), "66.67%")
        self.assertEqual(nm.format_share(1, 10 ** 9), "<0.01%")
        self.assertEqual(nm.format_share(5, 5), "100.00%")


if __name__ == "__main__":
    unittest.main()
