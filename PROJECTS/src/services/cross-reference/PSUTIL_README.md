# PSUTIL Dependency for Enhanced System Monitoring

## Overview

The `crossref_standalone_fast.py` tool can work with or without the `psutil` library. However, installing `psutil` provides significant benefits for performance optimization.

## What is psutil?

`psutil` (Python System and Process Utilities) is a cross-platform library for retrieving information on running processes and system utilization (CPU, memory, disks, network, sensors) in Python.

## Benefits of Installing psutil

- **Accurate CPU Detection**: Provides real-time CPU count and usage information
- **Memory Monitoring**: Accurate RAM detection and usage monitoring
- **Performance Optimization**: Better parallel processing configuration
- **Enhanced Debugging**: More detailed system resource information
- **Cross-Platform Support**: Works on Windows, Linux, and macOS

## Installation Options

### Option 1: Automatic Installation (Recommended)

**Windows:**
```batch
install_psutil.bat
```

**All Platforms:**
```bash
python install_psutil.py
```

### Option 2: Manual Installation

**Using pip:**
```bash
pip install psutil
```

**Using Python:**
```bash
python -m pip install psutil
```

### Option 3: Download from PyPI

Visit: https://pypi.org/project/psutil/

## What Happens Without psutil?

If `psutil` is not installed, the tool will:

1. **Use Fallback Detection**: Implement platform-specific memory detection
2. **Conservative Estimates**: Use CPU count to estimate memory
3. **Still Work**: All functionality remains available
4. **Limited Monitoring**: Less detailed system resource information

## Fallback Detection Methods

When `psutil` is not available, the tool uses:

### Windows
- Windows API calls via `ctypes`
- `GlobalMemoryStatusEx` function

### Linux
- Reading `/proc/meminfo`
- Parsing memory information

### macOS
- `sysctl` command execution
- Hardware memory size detection

### Generic Fallback
- CPU count-based estimation
- Conservative memory estimates

## Error Handling

The tool includes comprehensive error handling:

- **Import Errors**: Graceful fallback to alternative methods
- **Detection Failures**: Conservative defaults
- **Platform Issues**: Cross-platform compatibility
- **Permission Issues**: Fallback to basic detection

## Performance Impact

### With psutil
- **Faster**: More accurate resource detection
- **Optimized**: Better parallel processing configuration
- **Detailed**: Real-time system monitoring
- **Recommended**: For production use

### Without psutil
- **Slower**: Conservative resource allocation
- **Basic**: Limited system monitoring
- **Functional**: All features work
- **Adequate**: For testing and basic use

## Troubleshooting

### Installation Issues

1. **Permission Denied**: Run as administrator (Windows) or use `sudo` (Linux/macOS)
2. **Network Issues**: Check internet connection for pip installation
3. **Python Version**: Ensure Python 3.6+ is installed
4. **Pip Issues**: Update pip: `python -m pip install --upgrade pip`

### Runtime Issues

1. **Import Errors**: psutil will be automatically disabled
2. **Detection Failures**: Fallback methods will be used
3. **Performance Issues**: Consider installing psutil for better optimization

## Verification

To verify psutil installation:

```python
python install_psutil.py
```

This will:
- Check if psutil is installed
- Install it if missing
- Test the installation
- Show system information

## Recommendations

### For Development/Testing
- psutil is optional
- Basic functionality works without it
- Good for initial testing

### For Production Use
- **Strongly recommended** to install psutil
- Better performance optimization
- More accurate resource detection
- Enhanced monitoring capabilities

### For Large Datasets
- **Required** for optimal performance
- Parallel processing optimization
- Memory management
- CPU utilization monitoring

## Support

If you encounter issues:

1. Check the error messages in the console output
2. Verify Python and pip versions
3. Try manual installation methods
4. Check system permissions
5. Review the fallback detection output

The tool is designed to work in all scenarios, with or without psutil, ensuring maximum compatibility and reliability. 