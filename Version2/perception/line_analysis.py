from collections import deque
from typing import Iterable, Optional, Tuple
try:
    from ..models import Observation
except ImportError:
    from models import Observation

_POSITIONS = (-2.0, -1.0, 0.0, 1.0, 2.0)

def analyze_line(values: Iterable[object]) -> Observation:
    sensors = tuple(bool(value) for value in values)
    if len(sensors) != 5:
        raise ValueError("exactly five sensors are required")
    active = [p for p, on in zip(_POSITIONS, sensors) if on]
    # A wide black pattern is evaluated before normal steering.
    full_black = all(sensors)
    line_detected = bool(active) and not full_black
    position = sum(active) / len(active) if line_detected else None
    # X is deliberately strict: both edges and the centre must be active.
    x = line_detected and sensors[0] and sensors[2] and sensors[4]
    return Observation(sensors, line_detected, position, full_black, x)

class LineAnalyzer:
    """Adds temporal confirmation without sleeping or owning a clock."""
    def __init__(self, marker_samples: int = 2):
        self.marker_samples = max(1, marker_samples)
        self._x_history = deque(maxlen=self.marker_samples)
        self._line_history = deque(maxlen=3)

    def update(self, values: Iterable[object]) -> Observation:
        result = analyze_line(values)
        self._x_history.append(result.x_intersection)
        self._line_history.append(result.line_detected and not result.full_black)
        dot_pattern = (
            len(self._line_history) == 3
            and list(self._line_history) == [True, False, True]
        )
        if result.x_intersection and sum(self._x_history) == self.marker_samples:
            return Observation(
                result.sensors, result.line_detected, result.line_position,
                result.full_black, result.x_intersection, dot_pattern
            )
        return Observation(result.sensors, result.line_detected, result.line_position,
                           result.full_black, False, dot_pattern)
