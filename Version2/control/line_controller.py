from ..models import MotorCommand

class ProportionalLineController:
    def __init__(self, base_speed: float = .25, gain: float = .18):
        self.base_speed, self.gain = base_speed, gain

    def command(self, position):
        if position is None:
            return MotorCommand()
        correction = max(-1.0, min(1.0, self.gain * position))
        return MotorCommand(self.base_speed + correction, self.base_speed - correction)
