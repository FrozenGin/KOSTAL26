import unittest
from Version2.config import Config
from Version2.models import MotorCommand, QRResultKind, StateId
from Version2.perception.line_analysis import analyze_line
from Version2.state_machine import Context, StateMachine

class FakeVehicle:
    def __init__(self): self.commands = []
    def set_motors(self, command): self.commands.append(command)
    def cleanup(self): pass
    def read_line_sensors(self): return [False] * 5

class FakeCamera:
    def start_scan(self, scan_id): pass
    def cancel_scan(self, scan_id): pass
    def poll(self): return QRResultKind.FOUND, "right"

class StateMachineTests(unittest.TestCase):
    def setUp(self):
        config = Config(target_level="level1", line_stable_seconds=.1, line_loss_timeout=.1, marker_stable_seconds=.1,
                        start_timeout=1, marker_timeout=1, scan_timeout=1,
                        maneuver_timeout=1, recovery_timeout=.2)
        self.vehicle = FakeVehicle()
        self.machine = StateMachine(Context(self.vehicle, FakeCamera(), config))

    def tick(self, sensors, now):
        return self.machine.tick(analyze_line(sensors), now)

    def test_start_sequence_and_recovery(self):
        self.tick([True] * 5, 0)
        self.tick([True] * 5, .001)
        self.assertEqual(self.machine.state, StateId.WAIT_START)
        self.tick([False] * 5, .01)
        self.assertEqual(self.machine.state, StateId.START_EXIT)
        self.tick([False, False, True, False, False], .02)
        self.tick([False, False, True, False, False], .14)
        self.assertEqual(self.machine.state, StateId.FOLLOW_LINE)
        self.tick([False] * 5, .15)
        self.tick([False] * 5, .26)
        self.assertEqual(self.machine.state, StateId.RECOVER_LINE)

    def test_cancel_stops_from_active_state(self):
        self.tick([True] * 5, 0)
        self.machine.tick(analyze_line([False] * 5), .1, cancelled=True)
        self.assertEqual(self.machine.state, StateId.STOPPED)
        self.assertEqual(self.vehicle.commands[-1], MotorCommand())

    def test_full_black_scan_marker_stops_for_qr(self):
        self.tick([True] * 5, 0)
        self.tick([True] * 5, .01)
        self.tick([False, False, True, False, False], .1)
        self.tick([False, False, True, False, False], .3)
        self.tick([False, False, True, False, False], .45)
        self.assertEqual(self.machine.state, StateId.FOLLOW_LINE)
        self.tick([True] * 5, .46)
        self.assertEqual(self.machine.state, StateId.CHECK_MARKER)
        self.assertEqual(self.vehicle.commands[-1].left, self.machine.context.config.qr_approach_speed)
        self.assertEqual(self.vehicle.commands[-1].right, self.machine.context.config.qr_approach_speed)
        self.tick([True, False, False, False, False], .47)
        self.assertEqual(self.machine.state, StateId.CHECK_MARKER)
        self.tick([False, False, True, False, False], .48)
        self.tick([False, False, True, False, False], .64)
        self.assertEqual(self.machine.state, StateId.SCAN_QR)

    def test_qr_direction_is_used_even_when_level_differs(self):
        self.tick([True] * 5, 0)
        self.tick([True] * 5, .01)
        self.tick([False, False, True, False, False], .1)
        self.tick([False, False, True, False, False], .3)
        self.tick([False, False, True, False, False], .45)
        self.tick([True] * 5, .46)
        self.tick([False, False, True, False, False], .47)
        self.tick([False, False, True, False, False], .63)
        self.assertEqual(self.machine.state, StateId.SCAN_QR)
        self.machine.context.camera.poll = lambda: (QRResultKind.FOUND, "level2\nleft")
        self.tick([True] * 5, .74)
        self.assertEqual(self.machine.state, StateId.EXECUTE_MANEUVER)
        command = self.tick([False] * 5, .75)
        self.assertGreater(command.left, 0)
        self.assertGreater(command.right, 0)
        self.assertEqual(command.right, command.left)

    def test_black_white_black_white_black_finishes(self):
        self.tick([True] * 5, 0)
        self.tick([True] * 5, .01)
        self.tick([False, False, True, False, False], .1)
        self.tick([False, False, True, False, False], .3)
        self.tick([False, False, True, False, False], .45)
        self.tick([True] * 5, .46)
        self.tick([False] * 5, .47)
        self.tick([True] * 5, .48)
        self.tick([False] * 5, .49)
        self.tick([True] * 5, .50)
        self.assertEqual(self.machine.state, StateId.CHECK_MARKER)
        self.tick([False] * 5, .51)
        self.assertEqual(self.machine.state, StateId.FINISHED)
        self.assertEqual(self.vehicle.commands[-1], MotorCommand())
