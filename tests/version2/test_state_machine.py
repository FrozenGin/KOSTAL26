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
        config = Config(line_stable_seconds=.1, line_loss_timeout=.1, marker_stable_seconds=.1,
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
