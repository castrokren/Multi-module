#!/usr/bin/env python3
"""
Simple test to check if the scraper can start
"""

print("Starting simple test...")

try:
    print("Testing basic imports...")
    import tkinter as tk
    print("tkinter OK")
    
    import pandas as pd
    print("pandas OK")
    
    import requests
    print("requests OK")
    
    print("All imports successful!")
    
    # Test GUI
    print("Testing GUI...")
    root = tk.Tk()
    root.title("Test")
    root.geometry("300x200")
    
    label = tk.Label(root, text="GUI Test - Close this window")
    label.pack(pady=50)
    
    # Auto-close after 2 seconds
    root.after(2000, root.destroy)
    
    print("GUI created, will auto-close in 2 seconds...")
    root.mainloop()
    print("GUI test completed!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("Simple test completed!")
