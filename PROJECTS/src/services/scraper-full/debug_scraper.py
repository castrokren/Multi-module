#!/usr/bin/env python3
"""
Debug version to test what's preventing the scraper from starting
"""

import sys
import traceback

def debug_imports():
    """Test all imports"""
    print("Testing imports...")
    
    try:
        import tkinter
        print("✅ tkinter imported")
    except Exception as e:
        print(f"❌ tkinter failed: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ pandas imported")
    except Exception as e:
        print(f"❌ pandas failed: {e}")
        return False
    
    try:
        import requests
        print("✅ requests imported")
    except Exception as e:
        print(f"❌ requests failed: {e}")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup imported")
    except Exception as e:
        print(f"❌ BeautifulSoup failed: {e}")
        return False
    
    return True

def debug_single_instance():
    """Test single instance check"""
    print("Testing single instance check...")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 12345))
        sock.close()
        print("✅ Single instance check passed")
        return True
    except OSError as e:
        print(f"❌ Single instance check failed: {e}")
        print("Another instance might be running, or port 12345 is in use")
        return False

def debug_gui():
    """Test GUI creation"""
    print("Testing GUI creation...")
    
    try:
        from tkinter import Tk
        root = Tk()
        root.title("Test Window")
        print("✅ GUI window created successfully")
        root.destroy()  # Close immediately
        return True
    except Exception as e:
        print(f"❌ GUI creation failed: {e}")
        traceback.print_exc()
        return False

def debug_main_import():
    """Test importing the main module"""
    print("Testing main module import...")
    
    try:
        # Add current directory to path
        import os
        sys.path.insert(0, os.getcwd())
        
        import pdf_crawler_gui_2
        print("✅ Main module imported successfully")
        return True
    except Exception as e:
        print(f"❌ Main module import failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("=== DEBUGGING PDF CRAWLER STARTUP ===")
    
    # Test each component
    if not debug_imports():
        print("❌ Import test failed - check your Python environment")
        return
    
    if not debug_single_instance():
        print("❌ Single instance test failed - try closing any running instances")
        return
    
    if not debug_gui():
        print("❌ GUI test failed - check your display/X11 setup")
        return
    
    if not debug_main_import():
        print("❌ Main module test failed - check for syntax errors")
        return
    
    print("\n✅ All tests passed! The scraper should be able to start.")
    print("Try running: python pdf_crawler_gui_2.py")
    
    # Try to actually start it
    print("\nAttempting to start the scraper...")
    try:
        import pdf_crawler_gui_2
        pdf_crawler_gui_2.main()
    except Exception as e:
        print(f"❌ Failed to start scraper: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
