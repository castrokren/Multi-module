#!/usr/bin/env python3
"""
Check and install required Python dependencies.
Installs a comprehensive set of packages needed by the pipeline.
IMPROVED VERSION: Shows all output, handles failures clearly.
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

def upgrade_pip():
    """Ensure pip is up to date."""
    print("[*] Checking pip version...")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("[OK] pip is up to date")
        return True
    else:
        print("[WARN] Could not upgrade pip - proceeding anyway")
        print(result.stderr)
        return True  # Don't fail, pip might still work

def install_dependencies():
    """Install all required packages."""
    print(f"\n[*] Installing {len(REQUIRED_PACKAGES)} required packages...")
    print("[*] This may take a few minutes on first run...\n")

    # Install packages with output visible (removed -q flag)
    cmd = [sys.executable, "-m", "pip", "install"] + REQUIRED_PACKAGES
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "="*60)
        print("✓ SUCCESS: All dependencies installed successfully")
        print("="*60 + "\n")
        return True
    else:
        print("\n" + "="*60)
        print("✗ ERROR: Failed to install some dependencies")
        print("="*60)
        print("\nPossible causes:")
        print("  1. Check your internet connection")
        print("  2. Verify you have permission to install packages")
        print("  3. Check disk space is available")
        print("  4. Firewall/proxy might be blocking pip downloads")
        print("\nTo debug, run manually:")
        print(f"  pip install {' '.join(REQUIRED_PACKAGES[:3])}  # Test with first 3 packages\n")
        return False

def verify_packages():
    """Verify that key packages are actually installed."""
    print("\n[*] Verifying installation...")
    key_packages = ["flask", "pandas", "openpyxl", "requests"]

    for pkg in key_packages:
        result = subprocess.run(
            [sys.executable, "-c", f"import {pkg.replace('-', '_')}"],
            capture_output=True
        )
        if result.returncode == 0:
            print(f"  ✓ {pkg}")
        else:
            print(f"  ✗ {pkg} - MISSING")
            return False

    print("[OK] Key packages verified\n")
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PYTHON DEPENDENCY INSTALLER")
    print("="*60)

    # Step 1: Upgrade pip
    upgrade_pip()

    # Step 2: Install packages
    if not install_dependencies():
        sys.exit(1)

    # Step 3: Verify installation
    if not verify_packages():
        print("\n[ERROR] Some packages failed verification")
        sys.exit(1)

    print("[OK] Dependency installation complete and verified")
    sys.exit(0)
