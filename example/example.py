import time
from picar import Picar

pc = Picar()

# read sensors
sensor_states = pc.get_line_sensor_states()
print(f"sensors: {sensor_states}")

# point camera left
pc.set_camera_angle(-75)
time.sleep(0.5)

# point camera right
pc.set_camera_angle(75)
time.sleep(0.5)

# point camera forwards
pc.set_camera_angle(0)
time.sleep(0.5)

# prepare motors to turn right
pc.set_motor_direction(pc.MOTOR_LEFT, True)
pc.set_motor_direction(pc.MOTOR_RIGHT, False)

# set motor speed
pc.set_speed(pc.MOTOR_LEFT, 0.4)
pc.set_speed(pc.MOTOR_RIGHT, 0.4)
time.sleep(0.8)

# prepare motors to turn left
pc.set_motor_direction(pc.MOTOR_LEFT, False)
pc.set_motor_direction(pc.MOTOR_RIGHT, True)

# set motor speed
pc.set_speed(pc.MOTOR_LEFT, 0.4)
pc.set_speed(pc.MOTOR_RIGHT, 0.4)
time.sleep(0.8)
