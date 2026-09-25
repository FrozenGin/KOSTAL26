import unittest
from Version2.perception.line_analysis import LineAnalyzer, analyze_line

class LineAnalysisTests(unittest.TestCase):
    def test_position_and_full_black(self):
        result = analyze_line([False, True, False, False, False])
        self.assertTrue(result.line_detected)
        self.assertEqual(result.line_position, -1)
        self.assertTrue(analyze_line([True] * 5).full_black)
        self.assertFalse(analyze_line([False] * 5).line_detected)

    def test_x_requires_confirmation(self):
        analyzer = LineAnalyzer(marker_samples=2)
        self.assertFalse(analyzer.update([True, False, True, False, True]).x_intersection)
        self.assertTrue(analyzer.update([True, False, True, False, True]).x_intersection)
