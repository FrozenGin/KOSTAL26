from dataclasses import dataclass

TARGET_LEVEL = "level1"
ACCEPTED_LEVELS = ("level1","level2")

# Motor speed settings. Values are normalized to 0.0..1.0.
SPEED_FOLLOW_LINE = 0.141
SPEED_START_EXIT = 0.15
SPEED_QR_MARKER = 0.14
SPEED_MANEUVER_FORWARD = 0.14
SPEED_MANEUVER_TURN = 0.2
SPEED_RECOVERY = 0.14
SPEED_DOT = 0.08

@dataclass(frozen=True)
class Config:
    target_level: str = TARGET_LEVEL
    accepted_levels: tuple[str, ...] = ACCEPTED_LEVELS
    goal_black_lines: int = 3
    cycle_seconds: float = 0.02
    follow_speed: float = SPEED_FOLLOW_LINE
    max_correction_percent: float = 0.9
    start_exit_speed: float = SPEED_START_EXIT
    turn_speed: float = SPEED_MANEUVER_TURN
    maneuver_forward_speed: float = SPEED_MANEUVER_FORWARD
    maneuver_turn_speed: float = SPEED_MANEUVER_TURN
    qr_approach_speed: float = SPEED_QR_MARKER
    qr_approach_seconds: float = 0.75
    marker_center_tolerance: float = 0.5
    marker_rearm_seconds: float = 0.5
    line_stable_seconds: float = 0.15
    marker_stable_seconds: float = 0.08
    line_loss_timeout: float = 0.35
    start_timeout: float = 8.0
    marker_timeout: float = 10.0
    scan_timeout: float = 10.0
    maneuver_timeout: float = 6.0
    target_line_search_timeout: float = 12.0
    recovery_speed: float = SPEED_RECOVERY
    dot_speed: float = SPEED_DOT
    recovery_timeout: float = 4.0

    def validate(self) -> None:
        if self.target_level not in ("level1", "level2"):
            raise ValueError("target_level must be level1 or level2")
        if not self.accepted_levels or any(
            level not in ("level1", "level2") for level in self.accepted_levels
        ):
            raise ValueError("accepted_levels must contain level1 and/or level2")
        if self.goal_black_lines != 3:
            raise ValueError("goal_black_lines must be 3 for BLACK-WHITE-BLACK-WHITE-BLACK-WHITE")
        for name in ("cycle_seconds", "line_stable_seconds", "marker_stable_seconds",
                     "line_loss_timeout", "start_timeout", "marker_timeout",
                     "scan_timeout", "maneuver_timeout", "target_line_search_timeout",
                     "recovery_timeout", "marker_rearm_seconds"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("follow_speed", "start_exit_speed", "turn_speed",
                     "maneuver_forward_speed", "maneuver_turn_speed",
                     "qr_approach_speed", "recovery_speed", "dot_speed"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if not 0 <= self.max_correction_percent <= 1:
            raise ValueError("max_correction_percent must be between 0 and 1")
        if self.qr_approach_seconds < 0:
            raise ValueError("qr_approach_seconds must not be negative")
        if not 0 <= self.marker_center_tolerance <= 2:
            raise ValueError("marker_center_tolerance must be between 0 and 2")
