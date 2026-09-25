from dataclasses import dataclass
from typing import Callable, Optional
from .config import Config
from .control.line_controller import ProportionalLineController
from .models import Direction, MotorCommand, Observation, QRResultKind, StateId
from .perception.line_analysis import LineAnalyzer
from .perception.qr_commands import parse_qr_command

TERMINAL = {StateId.FINISHED, StateId.ERROR, StateId.STOPPED}

@dataclass
class Context:
    vehicle: object
    camera: object
    config: Config = Config()
    analyzer: LineAnalyzer = None
    controller: ProportionalLineController = None
    state: StateId = StateId.INIT
    entered_at: float = 0.0
    line_since: Optional[float] = None
    loss_since: Optional[float] = None
    last_direction: Direction = Direction.LEFT
    scan_id: int = 0
    saw_intersection_clear: bool = False
    error: Optional[str] = None

    def __post_init__(self):
        self.config.validate()
        self.analyzer = self.analyzer or LineAnalyzer()
        self.controller = self.controller or ProportionalLineController(self.config.follow_speed)

class StateMachine:
    def __init__(self, context: Context, clock: Callable[[], float] = None):
        self.context = context
        self.clock = clock
        self._start_line_seen = False
        self.transitions = []

    @property
    def state(self):
        return self.context.state

    def _transition(self, state: StateId, now: float, cause: str):
        if self.state == state:
            return
        self.transitions.append((self.state, state, cause))
        self.context.state = state
        self.context.entered_at = now
        self.context.line_since = self.context.loss_since = None
        self.context.saw_intersection_clear = False
        if state == StateId.SCAN_QR:
            self.context.scan_id += 1
            self.context.camera.start_scan(self.context.scan_id)
        elif state in TERMINAL:
            self.context.vehicle.set_motors(MotorCommand())

    def stop(self, cause="cancelled"):
        self._transition(StateId.STOPPED, self.context.entered_at, cause)

    def fail(self, cause: str, now: float):
        self.context.error = cause
        self._transition(StateId.ERROR, now, cause)

    def tick(self, observation: Observation, now: float, cancelled: bool = False) -> MotorCommand:
        c = self.context
        if cancelled and self.state not in TERMINAL:
            self._transition(StateId.STOPPED, now, "cancelled")
        if self.state in TERMINAL:
            command = MotorCommand()
            c.vehicle.set_motors(command)
            return command
        try:
            command = self._update(observation, now)
        except Exception as exc:
            self.fail(str(exc), now)
            command = MotorCommand()
        c.vehicle.set_motors(command)
        return command

    def _stable_line(self, observation, now):
        if observation.line_detected:
            self.context.line_since = self.context.line_since or now
            return now - self.context.line_since >= self.context.config.line_stable_seconds
        self.context.line_since = None
        return False

    def _update(self, o: Observation, now: float) -> MotorCommand:
        c, state = self.context, self.state
        elapsed = now - c.entered_at
        if state == StateId.INIT:
            self._transition(StateId.WAIT_START, now, "initialized")
            return MotorCommand()
        if state == StateId.WAIT_START:
            if o.full_black:
                self._start_line_seen = True
            elif self._start_line_seen:
                self._transition(StateId.START_EXIT, now, "start line left")
            return MotorCommand()
        if state == StateId.START_EXIT:
            if elapsed > c.config.start_timeout:
                self.fail("start exit timeout", now); return MotorCommand()
            if self._stable_line(o, now):
                self._transition(StateId.FOLLOW_LINE, now, "line stable")
                return MotorCommand()
            return MotorCommand(c.config.start_exit_speed, c.config.start_exit_speed)
        if state == StateId.FOLLOW_LINE:
            if o.x_intersection:
                self._transition(StateId.CHECK_MARKER, now, "confirmed X")
                return MotorCommand()
            if not o.line_detected:
                c.loss_since = c.loss_since or now
                if now - c.loss_since >= c.config.line_loss_timeout:
                    self._transition(StateId.RECOVER_LINE, now, "line lost")
                    return MotorCommand()
                return MotorCommand(c.config.follow_speed, c.config.follow_speed)
            c.loss_since = None
            if o.line_position is not None:
                c.last_direction = Direction.RIGHT if o.line_position > 0 else Direction.LEFT
            return c.controller.command(o.line_position)
        if state == StateId.CHECK_MARKER:
            if elapsed > c.config.marker_timeout:
                self.fail("marker check timeout", now)
            else:
                self._transition(StateId.SCAN_QR, now, "X requires QR")
            return MotorCommand()
        if state == StateId.SCAN_QR:
            if elapsed > c.config.scan_timeout:
                self.fail("QR scan timeout", now); return MotorCommand()
            kind, text = c.camera.poll()
            if kind == QRResultKind.ERROR:
                self.fail("QR camera error", now)
            elif kind == QRResultKind.FOUND:
                command = parse_qr_command(text)
                if command is None or (command.level is not None and command.level != c.config.target_level):
                    self.fail("invalid or non-target QR command", now)
                else:
                    c.last_direction = command.direction
                    self._transition(StateId.EXECUTE_MANEUVER, now, "QR command accepted")
            return MotorCommand()
        if state == StateId.EXECUTE_MANEUVER:
            if elapsed > c.config.maneuver_timeout:
                self.fail("maneuver timeout", now); return MotorCommand()
            if not o.x_intersection:
                c.saw_intersection_clear = True
            if c.saw_intersection_clear and self._stable_line(o, now):
                self._transition(StateId.FOLLOW_LINE, now, "target line stable")
                return MotorCommand()
            if c.last_direction == Direction.LEFT:
                return MotorCommand(-c.config.turn_speed, c.config.turn_speed)
            return MotorCommand(c.config.turn_speed, -c.config.turn_speed)
        if state == StateId.RECOVER_LINE:
            if elapsed > c.config.recovery_timeout:
                self.fail("line recovery timeout", now); return MotorCommand()
            if o.x_intersection:
                self._transition(StateId.CHECK_MARKER, now, "marker during recovery")
                return MotorCommand()
            if self._stable_line(o, now):
                self._transition(StateId.FOLLOW_LINE, now, "line recovered")
                return MotorCommand()
            s = c.config.follow_speed * .55
            return MotorCommand(-s, s) if c.last_direction == Direction.LEFT else MotorCommand(s, -s)
        raise RuntimeError(f"unhandled state {state}")

    def cleanup(self):
        self.context.vehicle.set_motors(MotorCommand())
        self.context.vehicle.cleanup()
