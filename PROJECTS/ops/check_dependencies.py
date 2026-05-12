#!/usr/bin/env python3
"""
Check and install required Python dependencies.
Installs a comprehensive set of packages needed by the pipeline.
"""

import sys
import subprocess

# Comprehensive list of packages needed by the pipeline
REQUIRED_PACKAGES = [
    "flask",
    "flask-cors",
    "python-dotenv",
    "pyopenssl",
    "PyPDF2",
    "openpyxl",
    "pandas",
    "numpy",
    "requests",
    "beautifulsoup4",
    "lxml",
    "pillow",
    "pdfplumber",
    "pdfminer.six",
    "google-search-results",
    "playwright",
    "pydantic",
    "psutil",
    "pyyaml",
    "cryptography",
]

def install_dependencies():
    """Install all required packages."""
    print(f"Installing {len(REQUIRED_PACKAGES)} required packages...")
    print()

    cmd = [sys.executable, "-m", "pip", "install", "-q"] + REQUIRED_PACKAGES
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("✓ All dependencies installed successfully")
        return True
    else:
        print()
        print("✗ Failed to install some dependencies")
        print("  Check your internet connection and try again")
        return False

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)
