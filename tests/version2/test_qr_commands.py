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

    def test_handles_escaped_line_breaks_and_level_spacing(self):
        command = parse_qr_command(r"level 1\r\nright")
        self.assertEqual(command.direction, Direction.RIGHT)
        self.assertEqual(command.level, "level1")

    def test_rejects_substrings_and_unknown_values(self):
        for value in ("bright", "level1 left", "level3\nright", "left\nright", "goal"):
            self.assertIsNone(parse_qr_command(value))

    def test_scanner_rotates_positions(self):
        decoded_positions = []
        camera_angles = []
        scanner = QRScanner(lambda position: decoded_positions.append(position) or None,
                            camera_angles.append, settle_seconds=0, frames_per_position=1)
        scanner.start_scan(1)
        for _ in range(4):
            scanner.poll()
        self.assertEqual(decoded_positions, [-75, -50, -25, 0])
        self.assertEqual(camera_angles[:5], [-75, -50, -25, 0, 25])

    def test_scanner_performs_one_sweep_only(self):
        decoded_positions = []
        scanner = QRScanner(
            lambda position: decoded_positions.append(position) or None,
            settle_seconds=0,
            frames_per_position=1,
        )
        scanner.start_scan(1)
        for _ in range(len(scanner.POSITIONS) + 2):
            scanner.poll()
        self.assertEqual(decoded_positions, list(scanner.POSITIONS))
        self.assertTrue(scanner.scan_finished())

    def test_ready_sweep_moves_left_right_center(self):
        camera_angles = []
        scanner = QRScanner(lambda: None, camera_angles.append, settle_seconds=0)
        scanner.ready_sweep()
        self.assertEqual(camera_angles, [-75, 75, 0])
