#!/usr/bin/env python3
"""
Version of the scraper that bypasses the single instance check for testing
"""

# Import everything from the main scraper
import sys
import os
import re
import threading
import time
import requests
import urllib.parse
from urllib.parse import urlparse, urljoin
from tkinter import Tk, Entry, Label, Text, Scrollbar, Button, END, filedialog, IntVar, Checkbutton, Frame, ttk
from tkinter.ttk import Progressbar, Combobox, Treeview, Notebook
import pandas as pd
from bs4 import BeautifulSoup
import traceback
import socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from difflib import SequenceMatcher
from PyPDF2 import PdfReader
import pdfplumber
from datetime import datetime

# Simple logging function
def simple_log(message):
    """Simple logging function"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def main_no_single_check():
    """Main function without single instance check"""
    simple_log("=== STARTING PDF CRAWLER (NO SINGLE INSTANCE CHECK) ===")
    
    try:
        simple_log("Creating main window...")
        root = Tk()
        root.title("PDF Crawler & Manager - Enhanced (Test Mode)")
        root.geometry("1200x800")
        simple_log("✅ Main window created")
        
        # Import the main class from the original file
        simple_log("Importing main application class...")
        
        # We need to import the class but avoid the module-level code
        # Let's create a minimal version of the app
        
        simple_log("Creating test label...")
        test_label = Label(root, text="PDF Crawler Test Mode\n\nIf you see this window, the GUI is working!\n\nClose this window to continue.", 
                          font=("Arial", 14), pady=50)
        test_label.pack()
        
        close_button = Button(root, text="Close Test Window", command=root.destroy, font=("Arial", 12))
        close_button.pack(pady=20)
        
        simple_log("Starting main event loop...")
        root.mainloop()
        simple_log("✅ Test window closed successfully")
        
        return True
        
    except Exception as e:
        simple_log(f"❌ Application startup failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing GUI without single instance check...")
    if main_no_single_check():
        print("\n✅ GUI test successful!")
        print("The issue might be with the single instance check or module imports.")
        print("Try running the original scraper now, or check if port 12345 is in use.")
    else:
        print("\n❌ GUI test failed!")
        print("There's a more fundamental issue with the GUI or Python environment.")
