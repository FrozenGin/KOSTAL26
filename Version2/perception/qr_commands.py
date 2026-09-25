from typing import Optional
from ..models import Direction, QRCommand

def parse_qr_command(text: str) -> Optional[QRCommand]:
    """Parse only the two documented QR formats; never use substring matching."""
    if not isinstance(text, str):
        return None
    lines = [line.strip().lower() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]
    if len(lines) == 1 and lines[0] in ("left", "right"):
        return QRCommand(Direction(lines[0]))
    if len(lines) == 2 and lines[0] in ("level1", "level2") and lines[1] in ("left", "right"):
        return QRCommand(Direction(lines[1]), lines[0])
    return None
