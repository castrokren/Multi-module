# Windows Service Installation Guide

## Issue Fixed
Fixed error "The parameter is incorrect. (87)" by updating service class attributes to use static values instead of dynamic config values at class definition time.

## Updated Files
- `simple_W_service.py`: Fixed service attributes and added adaptive processor support

## How to Install the Service

### 1. Using the UI (Recommended)
1. Open `Updated_Monitor_UI.py`
2. Configure all required fields:
   - **Service Script**: Browse to `simple_W_service.py`
   - **Watch Directory**: Directory to monitor for Excel files
   - **Output Directory**: Where processed files will be saved
   - **Hardware Keywords**: `hardware_keywords.txt`
   - **Software Keywords**: `software_keywords.txt`
   - **Username**: `nyumc\castrk05` (or your domain\username)
   - **Password**: Your password
   - **Startup Type**: `auto` (recommended)
3. ✅ Check **Adaptive Processor** settings if you want to use learning features
4. Click **Install** button

### 2. Using Command Line (Administrator Required)

**Install Service:**
```cmd
python simple_W_service.py install
```

**Install with specific account:**
```cmd
python simple_W_service.py --username nyumc\castrk05 --password YourPassword --startup auto install
```

**Start Service:**
```cmd
python simple_W_service.py start
```

**Stop Service:**
```cmd
python simple_W_service.py stop
```

**Remove Service:**
```cmd
python simple_W_service.py remove
```

## Service Configuration

The service reads configuration from `monitor_config.json`. Make sure this file exists before starting the service.

### Standard Configuration
```json
{
  "watch_directory": "\\\\research-cifs.nyumc.org\\omero_dev\\kren\\SOM_in",
  "output_directory": "D:\\SOM_in_labeled",
  "hardware_keywords_file": "hardware_keywords.txt",
  "software_keywords_file": "software_keywords.txt"
}
```

### With Adaptive Processor
```json
{
  "watch_directory": "\\\\research-cifs.nyumc.org\\omero_dev\\kren\\SOM_in",
  "output_directory": "D:\\SOM_in_labeled",
  "hardware_keywords_file": "hardware_keywords.txt",
  "software_keywords_file": "software_keywords.txt",
  "use_adaptive_processor": true,
  "learning_mode": true,
  "min_occurrences": 5,
  "confidence_threshold": 0.7
}
```

## Service Features

### Standard Mode
- ✅ Monitors folder for new Excel files
- ✅ Processes files using keyword-based classification
- ✅ Saves processed files to output directory
- ✅ Logs all activities to Windows Event Log

### Adaptive Mode (New!)
- ✅ All standard features PLUS:
- ✅ Learns new keywords from processed files
- ✅ Automatically improves classification accuracy
- ✅ Backs up keyword files before updates
- ✅ Generates learning analytics

## Troubleshooting

### Error: "The parameter is incorrect. (87)"
✅ **FIXED** - Update to latest `simple_W_service.py`

### Error: "Access is denied"
- Run Command Prompt as Administrator
- Make sure the account has proper permissions

### Error: "Service won't start"
Check Windows Event Viewer:
1. Open Event Viewer
2. Navigate to: Windows Logs → Application
3. Look for events from "MonitorFolderSvc"

Common issues:
- Watch directory doesn't exist
- Keyword files not found
- Python dependencies missing

### Service starts but doesn't process files
1. Check that watch directory is correct
2. Verify keyword files exist
3. Make sure output directory is writable
4. Check Windows Event Log for errors

## Verifying Installation

### Check Service Status
```cmd
sc query MonitorFolderSvc
```

### View Service in Services Manager
1. Press `Win + R`
2. Type `services.msc`
3. Find "Excel Folder Monitor Service"

### Check Event Logs
1. Open Event Viewer
2. Navigate to Windows Logs → Application
3. Filter by source: "MonitorFolderSvc"

## Uninstalling

### Using UI
Click the **Remove** button in `Updated_Monitor_UI.py`

### Using Command Line
```cmd
python simple_W_service.py remove
```

## Best Practices

1. **Test First**: Use "Test Configuration" button before installing service
2. **Backup Keywords**: Keep backups of your keyword files (automatic in adaptive mode)
3. **Monitor Logs**: Regularly check Windows Event Logs for issues
4. **Start Manual**: For first install, use startup type "manual" to test
5. **Use Adaptive**: Enable adaptive processor for continuous improvement

## Adaptive Processor Benefits

When `use_adaptive_processor: true`:
- 📈 **Self-Improving**: Gets better over time
- 🛡️ **Safe**: Automatic backups before keyword updates
- 📊 **Transparent**: Learning reports show what's being learned
- ✅ **Validated**: Only high-quality keywords are promoted

## Support

If you encounter issues:
1. Check Windows Event Viewer for detailed error messages
2. Review `monitor_config.json` for correct paths
3. Verify all keyword files exist
4. Test with UI before installing service
5. Check that all Python dependencies are installed

## Dependencies

Make sure these are installed:
- Python 3.x
- pandas
- openpyxl (for .xlsx files)
- xlrd (for .xls files)
- watchdog
- pywin32

Install with:
```cmd
pip install pandas openpyxl xlrd watchdog pywin32
```

## Notes

- Service name: `MonitorFolderSvc`
- Display name: `Excel Folder Monitor Service`
- The service runs under the account you specify during installation
- Account must have permissions to read watch directory and write to output directory
- Network paths require proper credentials
