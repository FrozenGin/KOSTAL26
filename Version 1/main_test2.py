import time
import threading
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
turn_speed = 0.15
turn_forward = 0.1

# Threading variables for sensor monitoring
current_sensor_states = [0, 0, 0, 0, 0]
sensor_lock = threading.Lock()
sensor_thread_running = True

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
        pc.set_speed(motor_left, (-turn_forward-turn_speed))
        pc.set_speed(motor_right, (turn_forward+turn_speed))
    elif(direction == states.Dir.RIGHT):
        pc.set_speed(motor_left, (turn_forward+turn_speed))
        pc.set_speed(motor_right, (-turn_forward-turn_speed))
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

def sensor_monitoring_thread():
    global current_sensor_states, sensor_thread_running
    while sensor_thread_running:
        try:
            new_states = pc.get_line_sensor_states()
            with sensor_lock:
                current_sensor_states = new_states
            time.sleep(0.005)  # Read sensors every 5ms for responsiveness
        except Exception as e:
            print(f"Sensor monitoring error: {e}")
            time.sleep(0.01)

def get_threaded_sensor_states():
    """Get the latest sensor states from the monitoring thread"""
    with sensor_lock:
        return current_sensor_states.copy()

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
    current_sensor_analysis = analyse_sensor(get_threaded_sensor_states())
    while (current_sensor_analysis != states.SENSORSTATE.WHITE) and (current_sensor_analysis != states.SENSORSTATE.FORWARD):
        go_forward()
        time.sleep(update_time)
        current_sensor_analysis = analyse_sensor(get_threaded_sensor_states())
        print(current_sensor_analysis)
        
    if current_sensor_analysis == states.SENSORSTATE.WHITE:
        print(f"GOAL")
        return False
    else:
        print(f"CROSSING")
        return True

motor_setup(states.Dir.FORWARD)

# Start the sensor monitoring thread
sensor_thread = threading.Thread(target=sensor_monitoring_thread, daemon=True)
sensor_thread.start()
print("Sensor monitoring thread started")

while active:
    line_is = analyse_sensor(get_threaded_sensor_states())
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
        line_is = analyse_sensor(get_threaded_sensor_states())
    time.sleep(1)
    print("Entered Race Start.")
    # Race Start
    while(racing):
        line_is = analyse_sensor(get_threaded_sensor_states())

        while line_is != states.SENSORSTATE.WHITE and line_is != states.SENSORSTATE.BLACK:

            line_is = analyse_sensor(get_threaded_sensor_states())

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
        if "right" in result:
            print("RIGHT")
            turn(states.Dir.RIGHT)
            time.sleep(2)

        elif "level 1" in result: # or result == "level 2 left":
            print("LEFT1")
            turn(states.Dir.LEFT)
            time.sleep(2)

        elif "level 2" in result:
            print("LEFT2")
            turn(states.Dir.LEFT)
            time.sleep(2)

        elif result != 0:
            go_forward()
            time.sleep(1)
            line_is = analyse_sensor(get_threaded_sensor_states())
            if line_is == states.SENSORSTATE.WHITE:
                racing = False
                active = False
                print("Goal Reached.")
            

        time.sleep(update_time)

    # Clean up threads and resources
    sensor_thread_running = False
    print("Stopping sensor monitoring thread...")
    sensor_thread.join(timeout=1.0)  # Wait up to 1 second for thread to finish
    qr_scanner.cleanup() # clean up camera
    print("Program terminated successfully.")
