#!/usr/bin/env python3

"""
Run the actual pylele test but with build123d only and timeout protection
"""

import subprocess
import sys
import os
import time
from threading import Timer

class TimeoutException(Exception):
    pass

def timeout_handler():
    raise TimeoutException("Test execution timed out")

def run_test_with_timeout(test_command, timeout_seconds=120):
    """Run a test command with timeout protection"""
    timer = Timer(timeout_seconds, timeout_handler)
    timer.start()
    
    try:
        print(f"Running: {' '.join(test_command)}")
        start_time = time.time()
        
        # Run the command and capture output
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        timer.cancel()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Test completed in {duration:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        # Show key parts of output
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            # Look for key indicators
            for line in lines[-20:]:  # Last 20 lines
                if any(keyword in line.lower() for keyword in ['generation', 'done generating', 'rendering time', 'test passed', 'test failed', 'error', 'warning']):
                    print(f"  {line}")
        
        if result.stderr:
            print("STDERR (last 15 lines):")
            stderr_lines = result.stderr.strip().split('\n')
            for line in stderr_lines[-15:]:
                print(f"  {line}")
                
        return result.returncode == 0, result.stdout, result.stderr
        
    except TimeoutException:
        timer.cancel()
        print(f"TEST TIMED OUT after {timeout_seconds} seconds!")
        return False, "", "Test timed out"
    except Exception as e:
        timer.cancel()
        print(f"ERROR running test: {e}")
        return False, "", str(e)

def main():
    # Change to the pylele directory
    os.chdir('/home/marco/programming/pylele')
    
    # Test the specific test method that was hanging
    print("=" * 70)
    print("RUNNING PYLELE TEST WITH BUILD123D API ONLY")
    print("=" * 70)
    
    # Run the specific test method for all_assembly with build123d
    test_cmd = [sys.executable, "-m", "unittest", "pylele.test.PyleleTestMethods.test_all_assembly", "-v"]
    
    success, stdout, stderr = run_test_with_timeout(test_cmd, timeout_seconds=120)
    
    print("\n" + "=" * 70)
    print("FINAL RESULT:")
    print(f"Success: {success}")
    print("=" * 70)
    
    if not success:
        if "timed out" in stderr.lower():
            print("The test timed out - this confirms the hang issue")
        elif "error:" in stderr.lower() or "exception" in stderr.lower():
            print("The test failed with an error")
        else:
            print("The test failed for unknown reasons")
    else:
        print("The test passed successfully")

if __name__ == "__main__":
    main()
