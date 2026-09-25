"""Optional PiCar adapter. Raspberry Pi dependencies are loaded only on construction."""
import importlib.util
from pathlib import Path

from ..models import MotorCommand

class PicarVehicle:
    def __init__(self):
        source = Path(__file__).resolve().parents[2] / "Version 1" / "picar.py"
        spec = importlib.util.spec_from_file_location("kostal_v1_picar", source)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"PiCar adapter not found at {source}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            self._picar = module.Picar()
        except Exception as exc:
            raise RuntimeError("PiCar hardware is unavailable") from exc

    def read_line_sensors(self):
        return self._picar.get_line_sensor_states()

    def set_motors(self, command: MotorCommand):
        # Direction is separate from PWM because PiCar speed rejects negatives.
        for motor, value in ((self._picar.MOTOR_LEFT, command.left),
                             (self._picar.MOTOR_RIGHT, command.right)):
            if value < 0:
                self._picar.set_motor_direction(motor, False)
            else:
                self._picar.set_motor_direction(motor, True)
            self._picar.set_speed(motor, abs(value))

    def set_camera_angle(self, angle):
        self._picar.set_camera_angle(angle)

    def cleanup(self):
        self._picar.exit()
