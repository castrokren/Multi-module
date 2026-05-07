#!/usr/bin/env python3
"""
Minimal version of the scraper to test basic functionality
"""

import sys
import os

def test_basic_functionality():
    """Test basic functionality without GUI"""
    print("=== MINIMAL SCRAPER TEST ===")
    
    # Test 1: Basic Python
    print("✅ Python is working")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    # Test 2: Required imports
    try:
        import pandas as pd
        print("✅ pandas imported")
    except ImportError as e:
        print(f"❌ pandas missing: {e}")
        return False
    
    try:
        import requests
        print("✅ requests imported")
    except ImportError as e:
        print(f"❌ requests missing: {e}")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup imported")
    except ImportError as e:
        print(f"❌ BeautifulSoup missing: {e}")
        return False
    
    try:
        import tkinter as tk
        print("✅ tkinter imported")
    except ImportError as e:
        print(f"❌ tkinter missing: {e}")
        return False
    
    # Test 3: File access
    try:
        files = os.listdir('.')
        pdf_files = [f for f in files if f.endswith('.py')]
        print(f"✅ Found {len(pdf_files)} Python files in directory")
        if 'pdf_crawler_gui_2.py' in files:
            print("✅ Main scraper file found")
        else:
            print("❌ Main scraper file not found")
    except Exception as e:
        print(f"❌ File access error: {e}")
    
    # Test 4: Try to import main scraper (without running it)
    try:
        # Temporarily redirect stdout to capture verbose logging
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            import pdf_crawler_gui_2
        
        output = f.getvalue()
        print("✅ Main scraper imported successfully")
        if output:
            print(f"Import output: {output[:200]}...")
    except Exception as e:
        print(f"❌ Main scraper import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n=== TEST RESULTS ===")
    print("✅ All basic tests passed!")
    print("The scraper should be able to run.")
    
    return True

def try_start_gui():
    """Try to start the GUI version"""
    print("\n=== ATTEMPTING GUI START ===")
    
    try:
        # Import without the verbose logging interfering
        import pdf_crawler_gui_2
        
        print("Starting GUI application...")
        pdf_crawler_gui_2.main()
        
    except KeyboardInterrupt:
        print("GUI closed by user")
    except Exception as e:
        print(f"❌ GUI failed to start: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if test_basic_functionality():
        response = input("\nDo you want to try starting the GUI? (y/n): ")
        if response.lower().startswith('y'):
            try_start_gui()
    else:
        print("❌ Basic tests failed. Please fix the issues above before running the scraper.")
