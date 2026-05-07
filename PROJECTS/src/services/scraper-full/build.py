#!/usr/bin/env python3
"""
Build script for PDF Crawler GUI application
Supports multiple packaging options: PyInstaller, cx_Freeze, and setuptools
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Success!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    
    # Install playwright browsers
    if run_command([sys.executable, "-m", "playwright", "install", "chromium"], 
                   "Installing Playwright browsers"):
        print("✓ Playwright browsers installed")
    else:
        print("⚠ Warning: Playwright browsers installation failed")

def build_with_pyinstaller():
    """Build using PyInstaller"""
    print("\n=== Building with PyInstaller ===")
    
    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # Build with spec file
    if run_command([sys.executable, "-m", "PyInstaller", "pdf_crawler_gui_2.spec"], 
                   "Building executable with PyInstaller"):
        print("✓ PyInstaller build completed!")
        print(f"Executable location: {os.path.abspath('dist/PDF_Crawler_GUI.exe')}")
        return True
    return False

def build_with_cx_freeze():
    """Build using cx_Freeze"""
    print("\n=== Building with cx_Freeze ===")
    
    # Create setup script for cx_Freeze
    cx_setup = '''
from cx_Freeze import setup, Executable
import sys

build_exe_options = {
    "packages": [
        "tkinter", "pandas", "PyPDF2", "pdfplumber", "bs4", 
        "playwright", "requests", "asyncio", "threading"
    ],
    "excludes": [],
    "include_files": ["requirements.txt", "README me.txt", "*.xlsx"]
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="PDF_Crawler_GUI",
    version="2.0.0",
    description="PDF Crawler GUI Application",
    options={"build_exe": build_exe_options},
    executables=[Executable("pdf_crawler_gui_2.py", base=base)]
)
'''
    
    with open("cx_setup.py", "w") as f:
        f.write(cx_setup)
    
    if run_command([sys.executable, "cx_setup.py", "build"], 
                   "Building with cx_Freeze"):
        print("✓ cx_Freeze build completed!")
        return True
    return False

def build_with_setuptools():
    """Build using setuptools"""
    print("\n=== Building with setuptools ===")
    
    if run_command([sys.executable, "setup.py", "sdist", "bdist_wheel"], 
                   "Building package with setuptools"):
        print("✓ setuptools build completed!")
        return True
    return False

def main():
    """Main build function"""
    print("PDF Crawler GUI - Build Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("pdf_crawler_gui_2.py"):
        print("Error: pdf_crawler_gui_2.py not found in current directory")
        return
    
    # Install dependencies
    install_dependencies()
    
    # Ask user which build method to use
    print("\nChoose build method:")
    print("1. PyInstaller (recommended for standalone exe)")
    print("2. cx_Freeze (alternative exe builder)")
    print("3. setuptools (for distribution)")
    print("4. All methods")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    success = False
    
    if choice == "1":
        success = build_with_pyinstaller()
    elif choice == "2":
        success = build_with_cx_freeze()
    elif choice == "3":
        success = build_with_setuptools()
    elif choice == "4":
        success = (build_with_pyinstaller() and 
                  build_with_cx_freeze() and 
                  build_with_setuptools())
    else:
        print("Invalid choice. Using PyInstaller...")
        success = build_with_pyinstaller()
    
    if success:
        print("\n🎉 Build completed successfully!")
        print("\nNext steps:")
        print("1. Test the executable in the dist/ folder")
        print("2. Copy the executable to your desired location")
        print("3. Make sure to include any required data files")
    else:
        print("\n❌ Build failed. Check the error messages above.")

if __name__ == "__main__":
    main() 