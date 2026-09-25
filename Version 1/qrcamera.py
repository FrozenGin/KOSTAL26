import cv2
import time
import logging
from pyzbar import pyzbar
from picar import Picar


class QRCamera:
    """
    A class for QR code scanning using a servo-controlled camera.
    Rotates the camera left, center, right to scan for QR codes.
    """
    
    def __init__(self, picar_instance=None, offset=-20):
        """
        Initialize the QR camera scanner.
        
        Args:
            picar_instance (Picar): Existing Picar instance to use, or None to create new one
            offset (int): Servo calibration offset in degrees
        """
        self.offset = offset
        self.camera_instance = None
        self.picar_instance = picar_instance
        self.owns_picar = picar_instance is None  # Track if we created the picar instance
        
        # Initialize components
        if self.picar_instance is None:
            self._init_picar()
        else:
            logging.info("Using provided PiCar instance")
        self._init_camera()
    
    def _init_picar(self):
        """Initialize PiCar instance"""
        try:
            self.picar_instance = Picar()
            logging.info("PiCar initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing PiCar: {e}")
            self.picar_instance = None
    
    def _init_camera(self):
        """Initialize camera (Picamera2 or OpenCV fallback)"""
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            config = picam2.create_video_configuration(main={"size": (640, 480)})
            picam2.configure(config)
            picam2.start()
            self.camera_instance = picam2
            logging.info("Picamera2 initialized successfully")
        except ImportError:
            logging.error("Picamera2 not available, using OpenCV camera")
            self.camera_instance = cv2.VideoCapture(0)
        except Exception as e:
            logging.error(f"Error initializing Picamera2: {e}, falling back to OpenCV")
            self.camera_instance = cv2.VideoCapture(0)
    
    def _scan_for_qr_at_position(self, angle):
        """
        Scan for QR code at a specific camera angle.
        
        Args:
            angle (int): Camera angle in degrees
            
        Returns:
            str or None: QR code data if found, None otherwise
        """
        if self.picar_instance:
            self.picar_instance.set_camera_angle(angle)
            time.sleep(0.5)  # Wait for servo to move
        
        # Capture a frame for QR scanning
        if hasattr(self.camera_instance, 'capture_array'):
            # Picamera2
            frame = self.camera_instance.capture_array()
        else:
            # OpenCV VideoCapture
            ret, frame = self.camera_instance.read()
            if not ret:
                return None
        
        if frame is None:
            return None
        
        # Convert to grayscale for QR detection
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY if hasattr(self.camera_instance, 'capture_array') else cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
            
        # Detect QR codes
        qr_codes = pyzbar.decode(gray)
        
        if qr_codes:
            # Get the first QR code found
            qr_data = qr_codes[0].data.decode('utf-8')
            logging.info(f"QR code detected at angle {angle}°: {qr_data}")
            return qr_data
        
        return None
    
    def start_scan(self):
        """
        Perform the complete scanning sequence: left -> center -> right, up to 3 cycles.
        
        Returns:
            str: QR code data if found, or "no qr code detected" if not found
        """
        if not self.camera_instance:
            logging.error('Camera not available')
            return "no qr code detected"

        scan_positions = [-45 + self.offset, 0 + self.offset, 45 + self.offset]  # Left 45°, Center, Right 45°
        max_cycles = 3
        
        for cycle in range(max_cycles):
            logging.info(f"Starting scan cycle {cycle + 1}/{max_cycles}")
            
            for angle in scan_positions:
                logging.info(f"Scanning at {angle}° (cycle {cycle + 1})")
                qr_data = self._scan_for_qr_at_position(angle)
                
                if qr_data:
                    # QR code found, return camera to center position and return data
                    if self.picar_instance:
                        self.picar_instance.set_camera_angle(0 + self.offset)
                    
                    logging.info(f"QR code scan complete: {qr_data}")
                    return qr_data
            
            # Small delay between cycles
            time.sleep(0.1)
        
        # No QR code found after all cycles
        logging.warning("No QR code detected after 3 complete scan cycles")
        
        # Return camera to center position
        if self.picar_instance:
            self.picar_instance.set_camera_angle(0 + self.offset)
        
        return "no qr code detected"
    
    def cleanup(self):
        """Clean up camera and PiCar resources"""
        # Cleanup camera
        if self.camera_instance is not None:
            try:
                if hasattr(self.camera_instance, 'stop'):
                    self.camera_instance.stop()
                    logging.info("Camera stopped")
                elif hasattr(self.camera_instance, 'release'):
                    self.camera_instance.release()
                    logging.info("Camera released")
                
                # Give camera time to fully release
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error cleaning up camera: {e}")
            finally:
                self.camera_instance = None
        
        # Cleanup PiCar (only if we own it)
        if self.picar_instance is not None and self.owns_picar:
            try:
                self.picar_instance.set_camera_angle(0)  # Return to center
                self.picar_instance.exit()
                logging.info("PiCar cleaned up")
                
                # Give GPIO pins time to fully release
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error cleaning up PiCar: {e}")
            finally:
                self.picar_instance = None
        elif self.picar_instance is not None:
            # Return camera to center but don't exit the picar instance
            try:
                self.picar_instance.set_camera_angle(0)
                logging.info("Returned camera to center position")
            except Exception as e:
                logging.error(f"Error returning camera to center: {e}")
        
        logging.info("Cleanup!")
        
        # Force garbage collection to help release resources
        import gc
        gc.collect()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.cleanup()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Method 1: Let QRCamera create its own PiCar instance
    print("Method 1: QRCamera creates its own PiCar")
    with QRCamera() as qr_scanner:
        result = qr_scanner.start_scan()
        print(f"Scan result: {result}")
    
    print("\nMethod 2: Pass existing PiCar instance")
    # Method 2: Create PiCar separately and pass it to QRCamera
    picar = Picar()
    try:
        with QRCamera(picar_instance=picar) as qr_scanner:
            result = qr_scanner.start_scan()
            print(f"Scan result: {result}")
    finally:
        picar.exit()  # Clean up the picar instance manually