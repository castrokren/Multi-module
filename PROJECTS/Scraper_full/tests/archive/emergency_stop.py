#!/usr/bin/env python3
"""
EMERGENCY STOP SCRIPT
Use this to forcefully terminate any stuck Python processes.
"""

import os
import sys
import subprocess
import time

def emergency_stop():
    """Forcefully terminate all Python processes."""
    print("🚨 EMERGENCY STOP INITIATED")
    
    try:
        # Get all Python processes
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            pids = []
            
            for line in lines:
                if 'python.exe' in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            pids.append(pid)
                        except:
                            pass
            
            if pids:
                print(f"Found {len(pids)} Python processes: {pids}")
                
                for pid in pids:
                    try:
                        print(f"Killing process {pid}...")
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                     capture_output=True, shell=True)
                        time.sleep(1)
                    except Exception as e:
                        print(f"Failed to kill process {pid}: {e}")
                
                print("✅ Emergency stop completed")
            else:
                print("No Python processes found")
        else:
            print("Failed to get process list")
            
    except Exception as e:
        print(f"Error during emergency stop: {e}")
    
    # Also try to kill any remaining processes
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                      capture_output=True, shell=True)
        print("✅ Force killed all python.exe processes")
    except:
        pass

if __name__ == "__main__":
    emergency_stop()
