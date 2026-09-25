from gpiozero import Device
from gpiozero.pins.pigpio import PiGPIOFactory
Device.pin_factory = PiGPIOFactory()

from gpiozero import DigitalOutputDevice, DigitalInputDevice
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import atexit
from typing import List, Optional

class Picar:
    def __init__(self):
        # Initialize I2C bus
        self.i2c_bus = busio.I2C(SCL, SDA)
        # Initialize GPIO and PWM
        self.pwm = PCA9685(self.i2c_bus)
        # Initialize servo control
        self.servokit = ServoKit(channels=16)

        # Define GPIO pins for motors and sensors
        self.left_dir_a = DigitalOutputDevice(23)  # Left motor direction pin
        self.left_dir_b = DigitalOutputDevice(24)  # Left motor direction pin 
        self.right_dir_a = DigitalOutputDevice(27) # Right motor direction pin
        self.right_dir_b = DigitalOutputDevice(22) # Right motor direction pin

        self.ENA = 1  # Left motor speed PCA9685 port 1
        self.ENB = 0  # Right motor speed PCA9685 port 0

        self.sensors = [
            DigitalInputDevice(5, pull_up=True),  # No.1 sensor from far left
            DigitalInputDevice(6, pull_up=True),  # No.2 sensor from left
            DigitalInputDevice(13, pull_up=True), # Middle sensor
            DigitalInputDevice(19, pull_up=True), # No.2 sensor from right
            DigitalInputDevice(26, pull_up=True), # No.1 sensor from far right
        ]
        self.servo = 15 # camera servo

        self.MOTOR_LEFT = 0
        self.MOTOR_RIGHT = 1

        # Adjust for 25Hz
        self.pwm.frequency = 25
        self.servokit.servo[self.servo].set_pulse_width_range(min_pulse=650, max_pulse=2500)

        self.stop_motor(self.MOTOR_LEFT)
        self.stop_motor(self.MOTOR_RIGHT)
        self.set_camera_angle(0)
        atexit.register(self.exit)

    def exit(self) -> None:
        print("Cleanup!")
        self.set_camera_angle(None)
        self.set_speed(self.MOTOR_LEFT, 0)
        self.set_speed(self.MOTOR_RIGHT, 0)

    def set_speed(self, motor_idx: int, speed: float) -> None:
        speed = max(min(1.0, speed), 0)
        duty = int(speed * 0x7fff)
        if motor_idx == self.MOTOR_LEFT:
            self.pwm.channels[self.ENA].duty_cycle = duty
        elif motor_idx == self.MOTOR_RIGHT:
            self.pwm.channels[self.ENB].duty_cycle = duty

    def set_motor_direction(self, motor_idx: int, forward: bool) -> None:
        if motor_idx == self.MOTOR_LEFT:
            if forward:
                self.left_dir_a.off()
                self.left_dir_b.on()
            else:
                self.left_dir_b.off()
                self.left_dir_a.on()
        elif motor_idx == self.MOTOR_RIGHT:
            if forward:
                self.right_dir_a.off()
                self.right_dir_b.on()
            else:
                self.right_dir_b.off()
                self.right_dir_a.on()

    def stop_motor(self, motor_idx: int) -> None:
        self.set_speed(motor_idx, 0)
        if motor_idx == self.MOTOR_LEFT:
            self.left_dir_a.off()
            self.left_dir_b.off()
        elif motor_idx == self.MOTOR_RIGHT:
            self.right_dir_a.off()
            self.right_dir_b.off()

    def get_line_sensor_states(self) -> List[bool]:
        return [s.value for s in self.sensors]

    def set_camera_angle(self, angle: Optional[int]) -> None:
        if angle is not None:
            angle = max(-90, min(90, angle))
            angle = 90 - angle
        self.servokit.servo[self.servo].angle = angle