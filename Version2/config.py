from dataclasses import dataclass

TARGET_LEVEL = "level1"

@dataclass(frozen=True)
class Config:
    target_level: str = TARGET_LEVEL
    cycle_seconds: float = 0.02
    follow_speed: float = 0.25
    start_exit_speed: float = 0.12
    turn_speed: float = 0.22
    line_stable_seconds: float = 0.12
    marker_stable_seconds: float = 0.08
    line_loss_timeout: float = 0.35
    start_timeout: float = 8.0
    marker_timeout: float = 1.0
    scan_timeout: float = 3.0
    maneuver_timeout: float = 4.0
    recovery_timeout: float = 2.0

    def validate(self) -> None:
        if self.target_level not in ("level1", "level2"):
            raise ValueError("target_level must be level1 or level2")
        for name in ("cycle_seconds", "line_stable_seconds", "marker_stable_seconds",
                     "line_loss_timeout", "start_timeout", "marker_timeout",
                     "scan_timeout", "maneuver_timeout", "recovery_timeout"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("follow_speed", "start_exit_speed", "turn_speed"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
