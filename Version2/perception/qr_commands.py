from typing import Optional
try:
    from ..models import Direction, QRCommand
except ImportError:
    from models import Direction, QRCommand

def parse_qr_command(text: str) -> Optional[QRCommand]:
    """Parse only the two documented QR formats; never use substring matching."""
    if not isinstance(text, str):
        return None
    # QR readers may return real line breaks or the escaped characters literally.
    normalized = (text.replace("\\r\\n", "\n")
                      .replace("\\n", "\n")
                      .replace("\\r", "\n")
                      .replace("\r\n", "\n")
                      .replace("\r", "\n")
                      .replace("\x00", ""))
    lines = [line.strip().lower() for line in normalized.split("\n")]
    lines = [line for line in lines if line]
    if len(lines) == 1 and lines[0] in ("left", "right"):
        return QRCommand(Direction(lines[0]))
    if len(lines) == 2 and lines[1] in ("left", "right"):
        level = "".join(lines[0].split())
        if level in ("level1", "level2"):
            return QRCommand(Direction(lines[1]), level)
    return None
