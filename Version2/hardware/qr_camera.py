import inspect
import time
from typing import Callable, Optional
try:
    from ..models import QRResultKind
except ImportError:
    from models import QRResultKind

class QRScanner:
    """Scan camera angles from -75 to 75 degrees in 25-degree steps."""
    POSITIONS = (-75, -50, -25, 0, 25, 50, 75)
    def __init__(self, decoder: Optional[Callable] = None,
                 set_position: Optional[Callable] = None,
                 settle_seconds: float = 0.25,
                 frames_per_position: int = 3):
        self._camera = None
        self._owns_camera = decoder is None
        self.decoder = decoder or self._create_decoder()
        self._set_position = set_position
        self._settle_seconds = settle_seconds
        self._frames_per_position = max(1, frames_per_position)
        self._frames_at_position = 0
        self._ready_at = 0.0
        self._pending = None
        self._scan_finished = False
        self._position_index = 0

    def _create_decoder(self) -> Callable:
        try:
            from picamera2 import Picamera2
            camera = Picamera2()
            camera.configure(camera.create_preview_configuration(main={"size": (640, 480)}))
            camera.start()
            self._camera = camera
        except ImportError:
            try:
                import cv2
                self._camera = cv2.VideoCapture(0)
            except ImportError as exc:
                raise RuntimeError("Picamera2 or OpenCV is required for QR scanning") from exc
        except Exception as exc:
            raise RuntimeError("could not initialize Picamera2") from exc
        return self._decode_camera_frame

    def _decode_camera_frame(self) -> Optional[str]:
        from pyzbar import pyzbar

        if hasattr(self._camera, "capture_array"):
            frame = self._camera.capture_array()
        else:
            ok, frame = self._camera.read()
            if not ok:
                return None
        if frame is None:
            return None
        codes = pyzbar.decode(frame)
        if not codes:
            return None
        return codes[0].data.decode("utf-8")

    def start_scan(self, scan_id: int):
        self._pending = scan_id
        self._scan_finished = False
        self._position_index = 0
        self._frames_at_position = 0
        self.set_position(self.POSITIONS[0])

    def ready_sweep(self):
        """Move the camera left, right, and back to center before the start."""
        for position in (-75, 75, 0):
            self.set_position(position)
            # Match the working example: make each ready position visible.
            if self._settle_seconds:
                time.sleep(max(0.5, self._settle_seconds))
        print("[QR] camera ready sweep complete", flush=True)

    def set_position(self, position: int):
        if position not in self.POSITIONS:
            raise ValueError("invalid scan position")
        if self._set_position is not None:
            self._set_position(position)
        self._ready_at = time.monotonic() + self._settle_seconds
        self._frames_at_position = 0
        print(f"[QR] camera position: {position} degrees", flush=True)

    def poll(self):
        if self._pending is None:
            return QRResultKind.NOT_FOUND, None
        if time.monotonic() < self._ready_at:
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
            print(f"[QR] code found at {position}: {result!r}", flush=True)
            return QRResultKind.FOUND, result
        self._frames_at_position += 1
        if self._frames_at_position >= self._frames_per_position:
            if self._position_index == len(self.POSITIONS) - 1:
                self._pending = None
                self._scan_finished = True
                print("[QR] scan sweep complete; no code found", flush=True)
                return QRResultKind.NOT_FOUND, None
            self._position_index = (self._position_index + 1) % len(self.POSITIONS)
            self.set_position(self.POSITIONS[self._position_index])
        return QRResultKind.NOT_FOUND, None

    def scan_finished(self) -> bool:
        return self._scan_finished

    def cancel_scan(self, scan_id: int):
        if self._pending == scan_id:
            self._pending = None

    def cleanup(self):
        if self._camera is not None:
            if hasattr(self._camera, "stop"):
                self._camera.stop()
            elif hasattr(self._camera, "release"):
                self._camera.release()
            self._camera = None
