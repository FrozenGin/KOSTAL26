import time
import states
from picar import Picar
from qrcamera import QRCamera

pc = Picar()
qr_scanner = QRCamera(pc)

active : bool = True
racing : bool = True
notReady : bool = True
update_time = 0.01

motor_left = pc.MOTOR_LEFT
motor_right = pc.MOTOR_RIGHT
sensor_states = pc.get_line_sensor_states()
pc.set_camera_angle(0)

speed = 0.25
turn_speed = 0.1
turn_forward = 0.05

def go_forward():
    # set motor speed
    pc.set_speed(motor_left, speed)
    pc.set_speed(motor_right, speed)
    
def stop():
    # set motor speed
    pc.set_speed(motor_left, 0)
    pc.set_speed(motor_right, 0)

def hardturn(direction):
    if(direction == states.Dir.LEFT):
        pc.set_speed(motor_left, 1.2*(-turn_forward-turn_speed))
        pc.set_speed(motor_right, 1.2*(turn_forward+turn_speed))
    elif(direction == states.Dir.RIGHT):
        pc.set_speed(motor_left, 1.2*(turn_forward+turn_speed))
        pc.set_speed(motor_right, 1.2*(-turn_forward-turn_speed))
    time.sleep(0.5)

def turn(direction):
    if(direction == states.Dir.LEFT):
        pc.set_speed(motor_left, turn_forward-turn_speed)
        pc.set_speed(motor_right, turn_forward+turn_speed)
    elif(direction == states.Dir.RIGHT):
        pc.set_speed(motor_left, turn_forward+turn_speed)
        pc.set_speed(motor_right, turn_forward-turn_speed)
    time.sleep(0.1)

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
    elif(sensor_states[0] == 1 and sensor_states[1] == sensor_states[2] == sensor_states[3] == sensor_states[4] == 0):
        return states.SENSORSTATE.HARDLEFT
    elif(sensor_states[4] == 1 and sensor_states[0] == sensor_states[1] == sensor_states[2] == sensor_states[3] == 0):
        return states.SENSORSTATE.HARDRIGHT
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

motor_setup(states.Dir.FORWARD)

while active:
    line_is = analyse_sensor(sensor_check())
    # Start
    print("Entered Start Position.")
    while(notReady):
        #Startline 
        if(line_is == states.SENSORSTATE.BLACK):
            print("Waiting...")
            time.sleep(update_time)
        else:  
            print("Ready. Set.") 
            if(line_is == states.SENSORSTATE.WHITE):
                go_forward()
            else:
                print("GO!")
                notReady = False
        line_is = analyse_sensor(sensor_check())
    time.sleep(1)
    print("Entered Race Start.")
    # Race Start
    while(racing):
        line_is = analyse_sensor(sensor_check())

        while line_is != states.SENSORSTATE.WHITE and line_is != states.SENSORSTATE.BLACK:

            line_is = analyse_sensor(sensor_check())

            if(line_is == states.SENSORSTATE.LEFT):
                turn(states.Dir.LEFT)
            elif(line_is == states.SENSORSTATE.FORWARD):
                go_forward()
            elif(line_is == states.SENSORSTATE.RIGHT):
                turn(states.Dir.RIGHT)
            elif(line_is == states.SENSORSTATE.HARDRIGHT):
                hardturn(states.Dir.RIGHT)
            elif(line_is == states.SENSORSTATE.HARDLEFT):
                hardturn(states.Dir.LEFT)
            time.sleep(update_time)

        stop()
        result = qr_scanner.start_scan()
        print(f"Scan result: {result}")
 
        result = result.lower()
        '''
        if "right" == result:
            print("RIGHT")
            hardturn(states.Dir.RIGHT)
            time.sleep(2)

        elif "left" == result: # or result == "level 2 left":
            print("LEFT")
            hardturn(states.Dir.LEFT)
            time.sleep(2)
          
        elif "level 1" in result: # or result == "level 2 left":
            print("LEFT1")
            hardturn(states.Dir.LEFT)
            time.sleep(2)

        elif "level 2" in result:
            print("LEFT2")
            hardturn(states.Dir.LEFT)
            time.sleep(2)
        '''
        
        go_forward()
        time.sleep(1)
        line_is = analyse_sensor(sensor_check())
        if line_is == states.SENSORSTATE.WHITE:
            racing = False
            active = False
            print("Goal Reached.")
            

        time.sleep(update_time)

    qr_scanner.cleanup() # clean up camera
