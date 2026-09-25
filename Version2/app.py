import time
try:
    from .config import Config
    from .hardware.picar import PicarVehicle
    from .hardware.qr_camera import QRScanner
    from .state_machine import Context, StateMachine
except ImportError:
    from config import Config
    from picar_adapter import PicarVehicle
    from qr_camera import QRScanner
    from state_machine import Context, StateMachine

def run(vehicle, camera, config=Config(), clock=time.monotonic, cancelled=lambda: False):
    machine = StateMachine(Context(vehicle, camera, config), clock)
    try:
        while machine.state not in {machine.state.FINISHED, machine.state.ERROR, machine.state.STOPPED}:
            now = clock()
            observation = machine.context.analyzer.update(vehicle.read_line_sensors())
            machine.tick(observation, now, cancelled())
            delay = config.cycle_seconds - (clock() - now)
            if delay > 0:
                time.sleep(delay)
        return machine
    finally:
        machine.cleanup()

def main():
    try:
        vehicle = PicarVehicle()
        camera = QRScanner(set_position=vehicle.set_camera_angle)
        camera.ready_sweep()
        run(vehicle, camera)
    except RuntimeError as exc:
        print(f"V2 could not start: {exc}")
        print("Run this on the Raspberry Pi with the PiCar dependencies installed.")
        return 1
    return 0
