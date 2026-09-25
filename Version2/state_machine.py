from dataclasses import dataclass
from typing import Callable, Optional
try:
    from .config import Config
    from .control.line_controller import ProportionalLineController
    from .models import Direction, MotorCommand, Observation, QRResultKind, StateId
    from .perception.line_analysis import LineAnalyzer
    from .perception.qr_commands import parse_qr_command
except ImportError:
    from config import Config
    from line_controller import ProportionalLineController
    from models import Direction, MotorCommand, Observation, QRResultKind, StateId
    from line_analysis import LineAnalyzer
    from qr_commands import parse_qr_command

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
    black_line_count: int = 0
    black_marker_active: bool = False
    marker_left: bool = False
    white_gap_seen: bool = False
    goal_black_seen: bool = False
    straight_maneuver: bool = False
    qr_error_fallback: bool = False
    scan_marker_armed: bool = True
    marker_clear_since: Optional[float] = None
    error: Optional[str] = None

    def __post_init__(self):
        self.config.validate()
        self.analyzer = self.analyzer or LineAnalyzer()
        self.controller = self.controller or ProportionalLineController(
            self.config.follow_speed, self.config.max_correction_percent
        )

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
        previous = self.state
        self.transitions.append((self.state, state, cause))
        self.context.state = state
        self.context.entered_at = now
        self.context.line_since = self.context.loss_since = None
        self.context.saw_intersection_clear = False
        self.context.marker_left = False
        print(
            f"[STATE] {previous.value} -> {state.value} | {cause}",
            flush=True,
        )
        if state == StateId.SCAN_QR:
            self.context.scan_id += 1
            self.context.camera.start_scan(self.context.scan_id)
        elif state in TERMINAL:
            self.context.vehicle.set_motors(MotorCommand())

    def stop(self, cause="cancelled"):
        self._transition(StateId.STOPPED, self.context.entered_at, cause)

    def fail(self, cause: str, now: float):
        self.context.error = cause
        print(f"[ERROR] {cause}", flush=True)
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

    def _register_black_line(self, now: float) -> bool:
        c = self.context
        if c.black_marker_active:
            return False
        if c.black_line_count and not c.white_gap_seen:
            return False
        c.black_marker_active = True
        c.black_line_count += 1
        c.white_gap_seen = False
        print(
            f"[MARKER] black line {c.black_line_count}/{c.config.goal_black_lines}",
            flush=True,
        )
        if c.black_line_count >= c.config.goal_black_lines:
            c.goal_black_seen = True
        return False

    def _center_line_found(self, observation: Observation) -> bool:
        return (
            observation.line_detected
            and observation.line_position is not None
            and abs(observation.line_position)
            <= self.context.config.marker_center_tolerance
        )

    def _target_side_line_found(self, observation: Observation) -> bool:
        if not observation.line_detected or observation.line_position is None:
            return False
        if self.context.straight_maneuver:
            return abs(observation.line_position) <= self.context.config.marker_center_tolerance
        if self.context.last_direction == Direction.LEFT:
            return observation.line_position < 0
        return observation.line_position > 0

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
            if o.full_black:
                if not c.scan_marker_armed:
                    return MotorCommand(c.config.follow_speed, c.config.follow_speed)
                c.scan_marker_armed = False
                c.marker_left = False
                if self._register_black_line(now):
                    return MotorCommand()
                self._transition(StateId.CHECK_MARKER, now, "full-black QR marker")
                return MotorCommand(c.config.qr_approach_speed, c.config.qr_approach_speed)
            if o.dot_pattern:
                print("[DOT] short line interruption detected", flush=True)
                return MotorCommand(c.config.dot_speed, c.config.dot_speed)
            c.black_marker_active = False
            if not c.scan_marker_armed:
                c.marker_clear_since = c.marker_clear_since or now
                if now - c.marker_clear_since >= c.config.marker_rearm_seconds:
                    c.scan_marker_armed = True
                    c.marker_clear_since = None
                    print("[MARKER] next QR scan armed", flush=True)
            if not o.line_detected:
                c.loss_since = c.loss_since or now
                c.white_gap_seen = True
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
                return MotorCommand()
            if o.full_black:
                c.marker_left = False
                if self._register_black_line(now):
                    return MotorCommand()
                return MotorCommand(c.config.qr_approach_speed, c.config.qr_approach_speed)
            c.black_marker_active = False
            if not o.line_detected:
                if not c.marker_left:
                    c.marker_left = True
                    c.white_gap_seen = True
                    print("[MARKER] white gap reached", flush=True)
                    if c.goal_black_seen:
                        self._transition(
                            StateId.FINISHED,
                            now,
                            "BLACK-WHITE-BLACK-WHITE-BLACK-WHITE goal reached",
                        )
                        return MotorCommand()
            elif self._center_line_found(o):
                if self._stable_line(o, now):
                    print("[MARKER] centered line stable, starting QR scan", flush=True)
                    self._transition(StateId.SCAN_QR, now, "line found after black marker")
                    return MotorCommand()
            else:
                c.line_since = None
            return MotorCommand(c.config.qr_approach_speed, c.config.qr_approach_speed)
        if state == StateId.SCAN_QR:
            if elapsed > c.config.scan_timeout:
                self._continue_straight_after_qr_error(now, "QR scan timeout")
                return MotorCommand()
            kind, text = c.camera.poll()
            if kind == QRResultKind.ERROR:
                self._continue_straight_after_qr_error(now, "QR camera error")
            elif kind == QRResultKind.NOT_FOUND and getattr(c.camera, "scan_finished", lambda: False)():
                self._continue_straight_after_qr_error(
                    now, "QR not found after one scan sweep"
                )
            elif kind == QRResultKind.FOUND:
                command = parse_qr_command(text)
                if command is None:
                    self._continue_straight_after_qr_error(now, "invalid QR command")
                elif command.level is not None and command.level not in c.config.accepted_levels:
                    self._continue_straight_after_qr_error(
                        now, f"level {command.level} is disabled"
                    )
                else:
                    c.black_line_count = 0
                    c.white_gap_seen = False
                    c.goal_black_seen = False
                    c.black_marker_active = False
                    print("[MARKER] counter reset after QR scan", flush=True)
                    c.last_direction = command.direction
                    c.straight_maneuver = (
                        command.level is not None
                        and command.level != c.config.target_level
                    )
                    c.qr_error_fallback = False
                    level = command.level or "direction-only"
                    route_mode = "straight" if c.straight_maneuver else command.direction.value
                    print(
                        f"[QR] command accepted: level={level}, "
                        f"direction={command.direction.value}, mode={route_mode}",
                        flush=True,
                    )
                    self._transition(StateId.EXECUTE_MANEUVER, now, "QR direction accepted")
            return MotorCommand()
        if state == StateId.EXECUTE_MANEUVER:
            if elapsed > c.config.maneuver_timeout:
                self.fail("maneuver timeout", now); return MotorCommand()
            if not o.full_black:
                self._transition(StateId.FIND_TARGET_LINE, now, "marker left")
            return self._maneuver_command(c)
        if state == StateId.FIND_TARGET_LINE:
            if elapsed > c.config.target_line_search_timeout:
                self.fail("target line search timeout", now); return MotorCommand()
            if self._target_side_line_found(o) and self._stable_line(o, now):
                self._transition(StateId.FOLLOW_LINE, now, "target line stable")
                return MotorCommand()
            return self._maneuver_command(c)
        if state == StateId.RECOVER_LINE:
            if elapsed > c.config.recovery_timeout:
                self.fail("line recovery timeout", now); return MotorCommand()
            if o.full_black:
                if self._register_black_line(now):
                    return MotorCommand()
                self._transition(StateId.CHECK_MARKER, now, "marker during recovery")
                return MotorCommand()
            c.black_marker_active = False
            if self._stable_line(o, now):
                self._transition(StateId.FOLLOW_LINE, now, "line recovered")
                return MotorCommand()
            s = c.config.recovery_speed
            return MotorCommand(-s, s) if c.last_direction == Direction.LEFT else MotorCommand(s, -s)
        raise RuntimeError(f"unhandled state {state}")

    def _maneuver_command(self, context: Context) -> MotorCommand:
        if context.qr_error_fallback:
            return MotorCommand(
                context.config.qr_approach_speed,
                context.config.qr_approach_speed,
            )
        forward = context.config.maneuver_forward_speed
        if context.straight_maneuver:
            return MotorCommand(forward, forward)
        turn = context.config.maneuver_turn_speed
        if context.last_direction == Direction.LEFT:
            return MotorCommand(-turn, turn)
        return MotorCommand(turn, -turn)

    def _continue_straight_after_qr_error(self, now: float, reason: str) -> None:
        self.context.straight_maneuver = True
        self.context.qr_error_fallback = True
        print(f"[QR] {reason}; driving slowly to the next line", flush=True)
        self._transition(StateId.EXECUTE_MANEUVER, now, "QR error fallback")

    def cleanup(self):
        self.context.vehicle.set_motors(MotorCommand())
        if hasattr(self.context.camera, "cleanup"):
            self.context.camera.cleanup()
        self.context.vehicle.cleanup()
