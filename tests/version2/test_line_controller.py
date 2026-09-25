import unittest

from Version2.control.line_controller import ProportionalLineController


class LineControllerTests(unittest.TestCase):
    def test_correction_uses_percentage_from_center(self):
        controller = ProportionalLineController(.25, .8)

        center = controller.command(0.0)
        half = controller.command(1.0)
        edge = controller.command(2.0)

        self.assertEqual((center.left, center.right), (.25, .25))
        self.assertAlmostEqual(half.left, .35)
        self.assertAlmostEqual(half.right, .15)
        self.assertAlmostEqual(edge.left, .45)
        self.assertAlmostEqual(edge.right, .05)
