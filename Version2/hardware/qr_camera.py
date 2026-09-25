import inspect
from typing import Callable, Optional
from ..models import QRResultKind

class QRScanner:
    """Non-blocking scan coordinator for left, center, and right camera views."""
    POSITIONS = ("left", "center", "right")
    def __init__(self, decoder: Callable, set_position: Optional[Callable] = None):
        self.decoder = decoder
        self._set_position = set_position
        self._pending = None
        self._position_index = 0

    def start_scan(self, scan_id: int):
        self._pending = scan_id
        self._position_index = 0
        self.set_position(self.POSITIONS[0])

    def set_position(self, position: str):
        if position not in self.POSITIONS:
            raise ValueError("invalid scan position")
        if self._set_position is not None:
            self._set_position(position)

    def poll(self):
        if self._pending is None:
            return QRResultKind.NOT_FOUND, None
        try:
            position = self.POSITIONS[self._position_index]
            try:
                accepts_position = len(inspect.signature(self.decoder).parameters) > 0
            except (TypeError, ValueError):
                accepts_position = False
            result = self.decoder(position) if accepts_position else self.decoder()
        except Exception:
            self._pending = None
            return QRResultKind.ERROR, None
        if result:
            self._pending = None
            return QRResultKind.FOUND, result
        self._position_index = (self._position_index + 1) % len(self.POSITIONS)
        self.set_position(self.POSITIONS[self._position_index])
        return QRResultKind.NOT_FOUND, None

    def cancel_scan(self, scan_id: int):
        if self._pending == scan_id:
            self._pending = None
