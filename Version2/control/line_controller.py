try:
    from ..models import MotorCommand
except ImportError:
    from models import MotorCommand

class ProportionalLineController:
    def __init__(self, base_speed: float = .25, max_correction_percent: float = .8):
        self.base_speed = base_speed
        self.max_correction_percent = max_correction_percent

    def command(self, position):
        if position is None:
            return MotorCommand()
        # Sensor positions range from -2 to +2. Convert the distance from center
        # to -100%..+100% before applying the configured correction percentage.
        distance_percent = max(-1.0, min(1.0, position / 2.0))
        correction = self.base_speed * self.max_correction_percent * distance_percent
        return MotorCommand(self.base_speed + correction, self.base_speed - correction)
