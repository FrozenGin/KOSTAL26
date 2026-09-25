import unittest
from Version2.models import Direction
from Version2.perception.qr_commands import parse_qr_command
from Version2.hardware.qr_camera import QRScanner

class QRCommandTests(unittest.TestCase):
    def test_direction_and_two_line_forms(self):
        self.assertEqual(parse_qr_command(" RIGHT\r\n"), type(parse_qr_command("right"))(Direction.RIGHT))
        command = parse_qr_command("LEVEL2\r\nleft")
        self.assertEqual(command.direction, Direction.LEFT)
        self.assertEqual(command.level, "level2")

    def test_rejects_substrings_and_unknown_values(self):
        for value in ("bright", "level1 left", "level3\nright", "left\nright", "goal"):
            self.assertIsNone(parse_qr_command(value))

    def test_scanner_rotates_positions(self):
        positions = []
        scanner = QRScanner(lambda position: positions.append(position) or None,
                            positions.append)
        scanner.start_scan(1)
        for _ in range(4):
            scanner.poll()
        self.assertEqual(positions[:5], ["left", "left", "center", "center", "right"])
