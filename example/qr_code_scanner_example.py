from picamera2 import Picamera2
from pyzbar import pyzbar
from pyzbar.pyzbar import Decoded
from typing import List

# Initialize camera
RESOLUTION = (640, 480)  # 4:3 resolution (max 2592x1944)
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": RESOLUTION}))

# Set controls if required
# picam2.set_controls({"AwbEnable": False, "ExposureTime": 15000, "AnalogueGain": 8})

# Start the camera
picam2.start()

def capture_qr_codes() -> List[Decoded]:
    """Capture a frame and return any QR codes present."""
    frame = picam2.capture_array()
    qr_codes = pyzbar.decode(frame)
    return qr_codes

def process_qr_codes(qr_codes: List[Decoded]) -> None:
    """Process and print the data from the QR codes."""
    for qr_code in qr_codes:
        data = qr_code.data.decode("utf-8")
        print(f"Detected QR code: {data}")

while True:
    # Capture and process QR codes
    qr_codes = capture_qr_codes()
    if qr_codes is not None:
        process_qr_codes(qr_codes)