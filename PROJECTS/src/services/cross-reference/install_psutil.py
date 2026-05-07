#!/usr/bin/env python3
"""
Install psutil for enhanced system monitoring
This script installs psutil which provides better CPU and memory detection
for optimal parallel processing performance.
"""

import subprocess
import sys
import os

def install_psutil():
    """Install psutil using pip."""
    print("🔧 Installing psutil for enhanced system monitoring...")
    print("💡 psutil provides better CPU and memory detection for optimal performance")
    print("")
    
    try:
        # Try to install psutil
        result = subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], 
                              capture_output=True, text=True, check=True)
        
        print("✅ psutil installed successfully!")
        print("")
        print("Benefits of psutil:")
        print("  - Accurate CPU count detection")
        print("  - Real-time memory usage monitoring")
        print("  - Better parallel processing optimization")
        print("  - Enhanced performance for large PDF processing")
        print("")
        print("You can now run crossref_standalone_fast.py with enhanced monitoring!")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install psutil: {e}")
        print(f"Error output: {e.stderr}")
        print("")
        print("💡 Alternative installation methods:")
        print("  1. Run: pip install psutil")
        print("  2. Run: python -m pip install psutil")
        print("  3. Download from: https://pypi.org/project/psutil/")
        print("")
        print("⚠️ The tool will still work without psutil, but with limited system monitoring")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error installing psutil: {e}")
        print("")
        print("💡 Alternative installation methods:")
        print("  1. Run: pip install psutil")
        print("  2. Run: python -m pip install psutil")
        print("  3. Download from: https://pypi.org/project/psutil/")
        print("")
        print("⚠️ The tool will still work without psutil, but with limited system monitoring")
        return False

def test_psutil():
    """Test if psutil is working correctly."""
    print("🧪 Testing psutil installation...")
    
    try:
        import psutil
        
        # Test CPU count
        cpu_count = psutil.cpu_count()
        print(f"✅ CPU count detected: {cpu_count}")
        
        # Test memory detection
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        print(f"✅ Memory detected: {memory_gb:.1f}GB")
        
        print("✅ psutil is working correctly!")
        return True
        
    except ImportError:
        print("❌ psutil not found - installation may have failed")
        return False
    except Exception as e:
        print(f"❌ psutil test failed: {e}")
        return False

def main():
    """Main function."""
    print("=== PSUTIL INSTALLATION SCRIPT ===")
    print("")
    
    # Check if psutil is already installed
    try:
        import psutil
        print("✅ psutil is already installed!")
        test_psutil()
        return
    except ImportError:
        pass
    
    # Install psutil
    if install_psutil():
        print("")
        test_psutil()
    
    print("")
    print("=== INSTALLATION COMPLETE ===")
    print("You can now run crossref_standalone_fast.py")
    print("The tool will automatically detect and use psutil if available")

if __name__ == "__main__":
    main() 