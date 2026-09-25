"""Optional PiCar adapter. Raspberry Pi dependencies are loaded only on construction."""
try:
    from ..models import MotorCommand
except ImportError:
    from models import MotorCommand

class PicarVehicle:
    def __init__(self):
        try:
            # Same construction as the working example, but imported lazily.
            try:
                from ..picar import Picar
            except ImportError:
                from picar import Picar
            self._picar = Picar()
        except (ImportError, ModuleNotFoundError, RuntimeError) as exc:
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
