from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

class StateId(str, Enum):
    INIT = "INIT"; WAIT_START = "WAIT_START"; START_EXIT = "START_EXIT"
    FOLLOW_LINE = "FOLLOW_LINE"; CHECK_MARKER = "CHECK_MARKER"; SCAN_QR = "SCAN_QR"
    EXECUTE_MANEUVER = "EXECUTE_MANEUVER"; RECOVER_LINE = "RECOVER_LINE"
    FINISHED = "FINISHED"; ERROR = "ERROR"; STOPPED = "STOPPED"

class Direction(str, Enum):
    LEFT = "left"
    RIGHT = "right"

class QRResultKind(str, Enum):
    FOUND = "found"; NOT_FOUND = "not_found"; ERROR = "error"

@dataclass(frozen=True)
class QRCommand:
    direction: Direction
    level: Optional[str] = None

@dataclass(frozen=True)
class Observation:
    sensors: Tuple[bool, bool, bool, bool, bool]
    line_detected: bool
    line_position: Optional[float]
    full_black: bool
    x_intersection: bool

@dataclass(frozen=True)
class MotorCommand:
    left: float = 0.0
    right: float = 0.0

    def __post_init__(self):
        if not (-1 <= self.left <= 1 and -1 <= self.right <= 1):
            raise ValueError("motor values must be in [-1, 1]")
