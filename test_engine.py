import unittest
from engine import analyze_match, fair_odds, expected_value

class EngineTests(unittest.TestCase):
    def test_over_under_complement(self):
        r = analyze_match(1.4, 1.1)
        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            self.assertAlmostEqual(r["over"][line] + r["under"][line], 1.0, places=8)

    def test_fair_odds(self):
        self.assertAlmostEqual(fair_odds(0.5), 2.0)

    def test_ev(self):
        self.assertAlmostEqual(expected_value(0.5, 2.2), 0.1)

if __name__ == "__main__":
    unittest.main()
