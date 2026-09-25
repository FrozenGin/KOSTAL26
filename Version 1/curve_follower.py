"""
Advanced Curve Following Robot with State Machine Logic
A professional implementation for following curved tracks with dot markers

Features:
- State machine architecture for robust navigation
- PID-based smooth curve following
- Adaptive speed control for different curve radii
- Dot pattern detection and handling
- Integration with existing QR scanning system
"""

import time
import math
from enum import Enum
from typing import List, Tuple, Optional
import states
from picar import Picar


class CurveFollowerState(Enum):
    """States for the curve following state machine"""
    INIT = "initialization"
    WAITING_START = "waiting_for_start"
    LINE_FOLLOWING = "line_following"
    CURVE_DETECTION = "curve_detection"
    CURVE_FOLLOWING = "curve_following"
    DOT_DETECTION = "dot_detection"
    CROSSING_ANALYSIS = "crossing_analysis"
    QR_SCANNING = "qr_scanning"
    GOAL_REACHED = "goal_reached"
    ERROR_RECOVERY = "error_recovery"


class CurveType(Enum):
    """Types of curves detected"""
    STRAIGHT = "straight"
    GENTLE_LEFT = "gentle_left"
    GENTLE_RIGHT = "gentle_right"
    SHARP_LEFT = "sharp_left"
    SHARP_RIGHT = "sharp_right"


class CurveFollower:
    """
    Professional curve following implementation with state machine logic
    """
    
    def __init__(self, picar: Picar):
        self.pc = picar
        self.current_state = CurveFollowerState.INIT
        self.previous_state = None
        
        # Motor references
        self.motor_left = self.pc.MOTOR_LEFT
        self.motor_right = self.pc.MOTOR_RIGHT
        
        # PID Controller parameters for smooth following
        self.pid_kp = 0.8  # Proportional gain
        self.pid_ki = 0.1  # Integral gain
        self.pid_kd = 0.3  # Derivative gain
        self.pid_integral = 0.0
        self.pid_previous_error = 0.0
        
        # Speed configurations for different scenarios
        self.speeds = {
            'normal': 0.25,
            'curve_gentle': 0.20,
            'curve_sharp': 0.15,
            'dot_approach': 0.12,
            'crossing': 0.10
        }
        
        # Sensor thresholds and patterns
        self.sensor_history = []
        self.history_length = 5
        self.dot_detection_threshold = 3  # Number of consecutive dot patterns
        self.curve_detection_threshold = 2
        
        # State timing
        self.update_interval = 0.05  # 20Hz update rate
        self.state_entry_time = time.time()
        
        # Curve following variables
        self.current_curve_type = CurveType.STRAIGHT
        self.curve_confidence = 0
        self.last_valid_line_time = time.time()
        
        # Initialize motor directions
        self._setup_motors()
        
    def _setup_motors(self):
        """Initialize motor directions for forward movement"""
        self.pc.set_motor_direction(self.motor_left, True)
        self.pc.set_motor_direction(self.motor_right, True)
        
    def _get_sensor_data(self) -> List[bool]:
        """Get current sensor readings"""
        return self.pc.get_line_sensor_states()
    
    def _update_sensor_history(self, sensors: List[bool]):
        """Maintain a history of sensor readings for pattern analysis"""
        self.sensor_history.append(sensors.copy())
        if len(self.sensor_history) > self.history_length:
            self.sensor_history.pop(0)
    
    def _calculate_line_position(self, sensors: List[bool]) -> float:
        """
        Calculate line position relative to robot center
        Returns: -2.0 (far left) to +2.0 (far right), 0.0 = center
        """
        # Weighted position calculation
        weights = [-2.0, -1.0, 0.0, 1.0, 2.0]
        total_weight = 0.0
        weighted_sum = 0.0
        
        for i, sensor in enumerate(sensors):
            if sensor:  # Line detected
                weighted_sum += weights[i]
                total_weight += 1.0
        
        if total_weight > 0:
            return weighted_sum / total_weight
        return 0.0  # No line detected
    
    def _detect_curve_type(self, sensors: List[bool]) -> CurveType:
        """
        Detect the type of curve based on sensor patterns
        """
        # Count active sensors on each side
        left_sensors = sum(sensors[0:2])
        center_sensor = sensors[2]
        right_sensors = sum(sensors[3:5])
        
        # Pattern analysis for curve detection
        if center_sensor and left_sensors == 0 and right_sensors == 0:
            return CurveType.STRAIGHT
        elif left_sensors >= 2:
            return CurveType.SHARP_LEFT if left_sensors == 2 else CurveType.GENTLE_LEFT
        elif right_sensors >= 2:
            return CurveType.SHARP_RIGHT if right_sensors == 2 else CurveType.GENTLE_RIGHT
        elif left_sensors == 1 and center_sensor:
            return CurveType.GENTLE_LEFT
        elif right_sensors == 1 and center_sensor:
            return CurveType.GENTLE_RIGHT
        
        return CurveType.STRAIGHT
    
    def _is_dot_pattern(self, sensors: List[bool]) -> bool:
        """
        Detect if current sensor reading indicates dots on the track
        Dots typically show as intermittent line detection
        """
        if len(self.sensor_history) < 3:
            return False
            
        # Look for alternating patterns that suggest dots
        recent_readings = self.sensor_history[-3:]
        center_readings = [reading[2] for reading in recent_readings]
        
        # Check for dot-like intermittent pattern
        changes = sum(1 for i in range(1, len(center_readings)) 
                     if center_readings[i] != center_readings[i-1])
        
        return changes >= 2  # Multiple transitions suggest dots
    
    def _is_crossing(self, sensors: List[bool]) -> bool:
        """Detect crossing or intersection"""
        active_sensors = sum(sensors)
        return active_sensors >= 4  # Most sensors active = crossing
    
    def _is_all_white(self, sensors: List[bool]) -> bool:
        """Detect all white (no line)"""
        return not any(sensors)
    
    def _is_all_black(self, sensors: List[bool]) -> bool:
        """Detect all black (full line)"""
        return all(sensors)
    
    def _pid_control(self, line_position: float) -> Tuple[float, float]:
        """
        PID controller for smooth line following
        Returns: (left_speed_adjustment, right_speed_adjustment)
        """
        error = line_position  # Target is 0.0 (center)
        
        # PID calculations
        self.pid_integral += error * self.update_interval
        derivative = (error - self.pid_previous_error) / self.update_interval
        
        # Calculate PID output
        pid_output = (self.pid_kp * error + 
                     self.pid_ki * self.pid_integral + 
                     self.pid_kd * derivative)
        
        # Convert to motor speed adjustments
        base_speed = self.speeds['normal']
        max_adjustment = base_speed * 0.8
        
        # Limit PID output
        pid_output = max(-max_adjustment, min(max_adjustment, pid_output))
        
        # Calculate individual motor speeds
        left_speed = base_speed - pid_output
        right_speed = base_speed + pid_output
        
        # Ensure speeds are within valid range
        left_speed = max(0, min(1.0, left_speed))
        right_speed = max(0, min(1.0, right_speed))
        
        self.pid_previous_error = error
        return left_speed, right_speed
    
    def _move_motors(self, left_speed: float, right_speed: float):
        """Set motor speeds"""
        self.pc.set_speed(self.motor_left, left_speed)
        self.pc.set_speed(self.motor_right, right_speed)
    
    def _stop_motors(self):
        """Stop both motors"""
        self.pc.set_speed(self.motor_left, 0)
        self.pc.set_speed(self.motor_right, 0)
    
    def _curve_following_speeds(self, curve_type: CurveType) -> Tuple[float, float]:
        """
        Calculate motor speeds for different curve types
        """
        if curve_type == CurveType.GENTLE_LEFT:
            base_speed = self.speeds['curve_gentle']
            return base_speed * 0.7, base_speed
        elif curve_type == CurveType.GENTLE_RIGHT:
            base_speed = self.speeds['curve_gentle']
            return base_speed, base_speed * 0.7
        elif curve_type == CurveType.SHARP_LEFT:
            base_speed = self.speeds['curve_sharp']
            return base_speed * 0.5, base_speed
        elif curve_type == CurveType.SHARP_RIGHT:
            base_speed = self.speeds['curve_sharp']
            return base_speed, base_speed * 0.5
        else:  # STRAIGHT
            base_speed = self.speeds['normal']
            return base_speed, base_speed
    
    def _change_state(self, new_state: CurveFollowerState):
        """Change state with logging and timing"""
        if new_state != self.current_state:
            print(f"State: {self.current_state.value} -> {new_state.value}")
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_entry_time = time.time()
    
    def _time_in_state(self) -> float:
        """Get time spent in current state"""
        return time.time() - self.state_entry_time
    
    # State machine implementation
    def _handle_init(self, sensors: List[bool]) -> CurveFollowerState:
        """Initialize the system"""
        print("Initializing curve follower...")
        self.pc.set_camera_angle(0)
        self._stop_motors()
        return CurveFollowerState.WAITING_START
    
    def _handle_waiting_start(self, sensors: List[bool]) -> CurveFollowerState:
        """Wait for start signal"""
        if self._is_all_black(sensors):
            print("Waiting for start signal...")
            return CurveFollowerState.WAITING_START
        elif any(sensors):
            print("Start signal detected!")
            return CurveFollowerState.LINE_FOLLOWING
        return CurveFollowerState.WAITING_START
    
    def _handle_line_following(self, sensors: List[bool]) -> CurveFollowerState:
        """Main line following with PID control"""
        # Check for special conditions first
        if self._is_all_white(sensors):
            if self._time_in_state() > 1.0:  # Lost line for too long
                return CurveFollowerState.ERROR_RECOVERY
            return CurveFollowerState.LINE_FOLLOWING
        
        if self._is_crossing(sensors):
            return CurveFollowerState.CROSSING_ANALYSIS
        
        if self._is_dot_pattern(sensors):
            return CurveFollowerState.DOT_DETECTION
        
        # Detect curve
        curve_type = self._detect_curve_type(sensors)
        if curve_type != CurveType.STRAIGHT:
            self.current_curve_type = curve_type
            return CurveFollowerState.CURVE_DETECTION
        
        # Normal line following with PID
        line_position = self._calculate_line_position(sensors)
        left_speed, right_speed = self._pid_control(line_position)
        self._move_motors(left_speed, right_speed)
        
        return CurveFollowerState.LINE_FOLLOWING
    
    def _handle_curve_detection(self, sensors: List[bool]) -> CurveFollowerState:
        """Confirm curve detection before entering curve following"""
        curve_type = self._detect_curve_type(sensors)
        
        if curve_type == self.current_curve_type:
            self.curve_confidence += 1
            if self.curve_confidence >= self.curve_detection_threshold:
                print(f"Curve confirmed: {curve_type.value}")
                return CurveFollowerState.CURVE_FOLLOWING
        else:
            self.curve_confidence = 0
            if curve_type == CurveType.STRAIGHT:
                return CurveFollowerState.LINE_FOLLOWING
        
        # Continue with normal following while detecting
        line_position = self._calculate_line_position(sensors)
        left_speed, right_speed = self._pid_control(line_position)
        self._move_motors(left_speed, right_speed)
        
        return CurveFollowerState.CURVE_DETECTION
    
    def _handle_curve_following(self, sensors: List[bool]) -> CurveFollowerState:
        """Handle curve following with adaptive speeds"""
        # Check if still in curve
        curve_type = self._detect_curve_type(sensors)
        
        if curve_type == CurveType.STRAIGHT:
            print("Curve completed, returning to line following")
            self.curve_confidence = 0
            return CurveFollowerState.LINE_FOLLOWING
        
        # Check for special conditions
        if self._is_crossing(sensors):
            return CurveFollowerState.CROSSING_ANALYSIS
        
        if self._is_dot_pattern(sensors):
            return CurveFollowerState.DOT_DETECTION
        
        # Apply curve-specific speeds
        left_speed, right_speed = self._curve_following_speeds(self.current_curve_type)
        self._move_motors(left_speed, right_speed)
        
        return CurveFollowerState.CURVE_FOLLOWING
    
    def _handle_dot_detection(self, sensors: List[bool]) -> CurveFollowerState:
        """Handle dot patterns on the track"""
        print("Dot pattern detected")
        
        # Slow down for careful navigation
        base_speed = self.speeds['dot_approach']
        
        # Continue following the line at reduced speed
        if any(sensors):
            line_position = self._calculate_line_position(sensors)
            if abs(line_position) < 1.0:  # Still on track
                left_speed, right_speed = self._pid_control(line_position)
                # Scale down speeds
                left_speed *= 0.6
                right_speed *= 0.6
                self._move_motors(left_speed, right_speed)
        
        # Check if dots lead to crossing
        if self._is_crossing(sensors):
            return CurveFollowerState.CROSSING_ANALYSIS
        
        # Return to normal following after dots
        if not self._is_dot_pattern(sensors) and self._time_in_state() > 2.0:
            return CurveFollowerState.LINE_FOLLOWING
        
        return CurveFollowerState.DOT_DETECTION
    
    def _handle_crossing_analysis(self, sensors: List[bool]) -> CurveFollowerState:
        """Analyze crossing and prepare for QR scanning"""
        print("Crossing detected - stopping for QR scan")
        self._stop_motors()
        
        # Wait a moment for stability
        if self._time_in_state() > 0.5:
            return CurveFollowerState.QR_SCANNING
        
        return CurveFollowerState.CROSSING_ANALYSIS
    
    def _handle_qr_scanning(self, sensors: List[bool], qr_scanner) -> CurveFollowerState:
        """Handle QR code scanning at crossings"""
        # This will be called from the main loop with QR scanner
        # The main loop should handle the actual QR scanning
        return CurveFollowerState.QR_SCANNING
    
    def _handle_error_recovery(self, sensors: List[bool]) -> CurveFollowerState:
        """Recover when line is lost"""
        print("Line lost - attempting recovery")
        
        # Try to find the line by gentle turning
        recovery_time = self._time_in_state()
        
        if recovery_time < 1.0:
            # Try turning left first
            self._move_motors(0.1, 0.2)
        elif recovery_time < 2.0:
            # Try turning right
            self._move_motors(0.2, 0.1)
        else:
            # Move forward slowly
            self._move_motors(0.15, 0.15)
        
        # Check if line is found
        if any(sensors):
            print("Line recovered!")
            return CurveFollowerState.LINE_FOLLOWING
        
        # Timeout recovery
        if recovery_time > 5.0:
            print("Recovery timeout - stopping")
            return CurveFollowerState.GOAL_REACHED
        
        return CurveFollowerState.ERROR_RECOVERY
    
    def update(self, qr_scanner=None) -> bool:
        """
        Main update loop for the state machine
        Returns: True to continue, False to stop
        """
        sensors = self._get_sensor_data()
        self._update_sensor_history(sensors)
        
        # State machine dispatch
        if self.current_state == CurveFollowerState.INIT:
            next_state = self._handle_init(sensors)
        elif self.current_state == CurveFollowerState.WAITING_START:
            next_state = self._handle_waiting_start(sensors)
        elif self.current_state == CurveFollowerState.LINE_FOLLOWING:
            next_state = self._handle_line_following(sensors)
        elif self.current_state == CurveFollowerState.CURVE_DETECTION:
            next_state = self._handle_curve_detection(sensors)
        elif self.current_state == CurveFollowerState.CURVE_FOLLOWING:
            next_state = self._handle_curve_following(sensors)
        elif self.current_state == CurveFollowerState.DOT_DETECTION:
            next_state = self._handle_dot_detection(sensors)
        elif self.current_state == CurveFollowerState.CROSSING_ANALYSIS:
            next_state = self._handle_crossing_analysis(sensors)
        elif self.current_state == CurveFollowerState.QR_SCANNING:
            # This should be handled by the main loop
            next_state = CurveFollowerState.QR_SCANNING
        elif self.current_state == CurveFollowerState.ERROR_RECOVERY:
            next_state = self._handle_error_recovery(sensors)
        else:  # GOAL_REACHED
            self._stop_motors()
            return False
        
        self._change_state(next_state)
        return True
    
    def handle_qr_result(self, qr_result: str) -> bool:
        """
        Handle QR scan result and determine next action
        Returns: True to continue, False if goal reached
        """
        if not qr_result or qr_result == "0":
            # No QR or invalid - continue forward
            print("No valid QR code - continuing forward")
            self._move_motors(self.speeds['normal'], self.speeds['normal'])
            time.sleep(1.0)
            self._change_state(CurveFollowerState.LINE_FOLLOWING)
            return True
        
        qr_result = qr_result.lower()
        
        if "right" in qr_result:
            print("QR: Turn RIGHT")
            # Execute right turn
            self._move_motors(self.speeds['curve_sharp'], self.speeds['curve_sharp'] * 0.3)
            time.sleep(2.0)
            self._change_state(CurveFollowerState.LINE_FOLLOWING)
            return True
            
        elif "left" in qr_result:
            print("QR: Turn LEFT")
            # Execute left turn
            self._move_motors(self.speeds['curve_sharp'] * 0.3, self.speeds['curve_sharp'])
            time.sleep(2.0)
            self._change_state(CurveFollowerState.LINE_FOLLOWING)
            return True
            
        else:
            # Goal reached
            print("QR: Goal reached!")
            self._change_state(CurveFollowerState.GOAL_REACHED)
            return False
    
    def cleanup(self):
        """Clean up resources"""
        self._stop_motors()
        print("Curve follower cleanup complete")


def create_curve_follower(picar: Picar) -> CurveFollower:
    """Factory function to create a curve follower instance"""
    return CurveFollower(picar)
