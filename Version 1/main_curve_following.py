"""
Enhanced Main Controller with Curve Following Integration
Integrates the professional curve follower with existing QR scanning functionality
"""

import time
from picar import Picar
from qrcamera import QRCamera
from curve_follower import create_curve_follower

def main():
    """Main execution function with enhanced curve following"""
    
    # Initialize hardware
    print("Initializing PiCar system...")
    pc = Picar()
    qr_scanner = QRCamera(pc)
    
    # Create curve follower instance
    print("Initializing curve follower...")
    curve_follower = create_curve_follower(pc)
    
    # Main execution flag
    active = True
    
    try:
        print("Starting curve following robot...")
        print("=" * 50)
        
        # Main control loop
        while active:
            # Update the curve follower state machine
            continue_running = curve_follower.update(qr_scanner)
            
            if not continue_running:
                print("Curve follower requested stop")
                break
            
            # Handle QR scanning state specifically
            if curve_follower.current_state.value == "qr_scanning":
                print("Performing QR scan...")
                
                # Perform QR scan
                try:
                    qr_result = qr_scanner.start_scan()
                    print(f"QR Scan result: {qr_result}")
                    
                    # Let curve follower handle the result
                    continue_running = curve_follower.handle_qr_result(qr_result)
                    
                    if not continue_running:
                        print("Goal reached via QR scan!")
                        break
                        
                except Exception as e:
                    print(f"QR scan error: {e}")
                    # Continue with line following if QR scan fails
                    curve_follower._change_state(curve_follower.CurveFollowerState.LINE_FOLLOWING)
            
            # Small delay to prevent excessive CPU usage
            time.sleep(curve_follower.update_interval)
        
        print("Mission completed successfully!")
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print("Cleaning up...")
        curve_follower.cleanup()
        qr_scanner.cleanup()
        print("Cleanup complete!")


if __name__ == "__main__":
    main()