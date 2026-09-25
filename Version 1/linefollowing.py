import time
import states



motor_left = pc.MOTOR_LEFT
motor_right = pc.MOTOR_RIGHT
sensor_states = pc.get_line_sensor_states()
pc.set_camera_angle(0)

speed = 0.20
turn_speed = 0.1
turn_forward = 0.15

def setup():


def go_forward():
    # set motor speed
    pc.set_speed(motor_left, speed)
    pc.set_speed(motor_right, speed)
    
def stop():
    # set motor speed
    pc.set_speed(motor_left, 0)
    pc.set_speed(motor_right, 0)

def turn(direction):
    if(direction == states.Dir.LEFT):
        pc.set_speed(motor_left, turn_forward-turn_speed)
        pc.set_speed(motor_right, turn_forward+turn_speed)
    elif(direction == states.Dir.RIGHT):
        pc.set_speed(motor_left, turn_forward+turn_speed)
        pc.set_speed(motor_right, turn_forward-turn_speed)

def sensor_check():
    return pc.get_line_sensor_states()

def analyse_sensor(sensor_states):
    #STOP
    if(sensor_states[0] == sensor_states[1] == sensor_states[2] == sensor_states[3] == sensor_states[4]==0):
        #print(f"stop! crossing or start or goal?")
        return states.SENSORSTATE.WHITE
    elif(sensor_states[0] == sensor_states[1] == sensor_states[2] == sensor_states[3] == sensor_states[4]==1):
        #print(f"no line")
        return states.SENSORSTATE.BLACK
    #LEFT
    elif(sensor_states[0] == 1 or sensor_states[1] == 1 and sensor_states[2] == 0):
        #print(f"sensor_analyse_left = 1")
        return states.SENSORSTATE.LEFT
    #FORWARD
    elif((sensor_states[2] == 1)):
        #print(f"sensor_analyse_center = 1")
        return states.SENSORSTATE.FORWARD
    #RIGHT
    elif(sensor_states[3] == 1 or sensor_states[4] == 1 and sensor_states[2] == 0):
        #print(f"sensor_analyse_right = 1")
        return states.SENSORSTATE.RIGHT

def motor_setup(direction):
    if(direction == states.Dir.FORWARD):
        pc.set_motor_direction(motor_left, True)
        pc.set_motor_direction(motor_right, True)
    elif(direction == states.Dir.LEFT):
        pc.set_motor_direction(motor_left, False)
        pc.set_motor_direction(motor_right, True)
    elif(direction == states.Dir.RIGHT):
        pc.set_motor_direction(motor_left, True)
        pc.set_motor_direction(motor_right, False)
    elif(direction == states.Dir.BACKWARDS):
        pc.set_motor_direction(motor_left, False)
        pc.set_motor_direction(motor_right, False)


def crossing(update_time):
    print("CROSSING?")
    while (analyse_sensor(sensor_check()) != states.SENSORSTATE.WHITE) and (analyse_sensor(sensor_check()) != states.SENSORSTATE.FORWARD):
        go_forward()
        time.sleep(update_time)
        print(analyse_sensor(sensor_check()))
        
    if analyse_sensor(sensor_check()) == states.SENSORSTATE.WHITE:
        print(f"GOAL")
        return False
    else:
        print(f"CROSSING")
        return True


