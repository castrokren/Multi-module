# Windows Service Installation Troubleshooting

## Current Issue: Service Not Visible in services.msc

### Root Cause
The service installation is failing silently, likely due to one of these reasons:
1. **Not running as Administrator**
2. **Incorrect credentials format or password**
3. **User account doesn't have "Log on as a service" rights**
4. **Python/pywin32 installation issues**

## Solutions (Try in Order)

### Solution 1: Install as LocalSystem (Recommended for Testing)

**Right-click Command Prompt → Run as Administrator**, then:

```cmd
cd C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify
python simple_W_service.py install
sc config MonitorFolderSvc start= auto
sc query MonitorFolderSvc
```

**OR use the helper script:**
1. Right-click `install_service_helper.bat`
2. Select "Run as administrator"

**Pros:**
- ✅ No password needed
- ✅ Works immediately
- ✅ Has full system access

**Cons:**
- ⚠️ Runs as SYSTEM (might have permission issues with network drives)

### Solution 2: Install with Your Current Account

If you need the service to run under your account (for network access):

1. **Right-click `install_service_with_credentials.bat`**
2. **Select "Run as administrator"**
3. **Enter credentials when prompted:**
   - Username: `nyumc\castrk05_adm` (your current account)
   - Password: Your actual password

### Solution 3: Grant "Log on as a service" Rights

If you get "logon failure" errors, you need to grant rights:

1. Press `Win + R`, type `secpol.msc`, press Enter
2. Navigate to: **Local Policies** → **User Rights Assignment**
3. Double-click **"Log on as a service"**
4. Click **"Add User or Group"**
5. Enter: `nyumc\castrk05` or `nyumc\castrk05_adm`
6. Click **OK**
7. **Restart** and try installing again

### Solution 4: Manual Installation via PowerShell

Run PowerShell as Administrator:

```powershell
cd "C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify"

# Remove any failed installation
python simple_W_service.py remove

# Install fresh
python simple_W_service.py install

# Verify installation
Get-Service MonitorFolderSvc

# If successful, start the service
Start-Service MonitorFolderSvc
```

## Verifying Installation Success

### Check if Service Exists:

```powershell
Get-Service MonitorFolderSvc
```

**Expected output if successful:**
```
Status   Name               DisplayName
------   ----               -----------
Stopped  MonitorFolderSvc   Excel Folder Monitor Service
```

**If service doesn't exist:**
```
Get-Service : Cannot find any service with service name 'MonitorFolderSvc'.
```

### Check in Services Manager:

1. Press `Win + R`
2. Type `services.msc`
3. Press Enter
4. Look for "Excel Folder Monitor Service"

### Check Registry:

```powershell
Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\MonitorFolderSvc" -ErrorAction SilentlyContinue
```

## Common Errors and Solutions

### Error: "The parameter is incorrect. (87)"
✅ **FIXED** - Use updated `simple_W_service.py`

### Error: "Access is denied"
- ❌ Not running as Administrator
- ✅ **Solution**: Right-click → Run as administrator

### Error: "Logon failure"
- ❌ Incorrect password or username format
- ❌ User doesn't have "Log on as a service" rights
- ✅ **Solution**: Use LocalSystem OR grant rights (see Solution 3)

### Error: Service installs but won't start
- ❌ Watch directory doesn't exist
- ❌ Missing keyword files
- ❌ Python dependencies not installed
- ✅ **Solution**: Check Event Viewer for detailed error

### Service not visible in services.msc
- ❌ Installation failed silently
- ❌ Not running as Administrator
- ✅ **Solution**: Use helper batch files with admin rights

## Checking Service Logs

After service starts (or fails to start):

1. Open **Event Viewer** (`eventvwr.msc`)
2. Navigate to: **Windows Logs** → **Application**
3. Filter current log by source: **MonitorFolderSvc** or **Python Service**
4. Look for error messages

## Quick Diagnostic Commands

Run these in **PowerShell as Administrator**:

```powershell
# Check if service exists
Get-Service MonitorFolderSvc -ErrorAction SilentlyContinue

# Check service configuration
sc qc MonitorFolderSvc

# Check current user
whoami

# Check admin rights
net session

# List all Python-related services
Get-Service | Where-Object {$_.DisplayName -like "*Python*" -or $_.DisplayName -like "*Monitor*"}

# Check if pywin32 is installed
python -c "import win32serviceutil; print('pywin32 OK')"
```

## Starting Over (Clean Install)

If nothing works, start fresh:

```cmd
:: Run as Administrator
cd C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify

:: Remove any traces
python simple_W_service.py remove

:: Verify pywin32
python -c "import win32serviceutil"

:: Install fresh as LocalSystem
python simple_W_service.py install

:: Set to auto-start
sc config MonitorFolderSvc start= auto

:: Start service
net start MonitorFolderSvc

:: Check status
sc query MonitorFolderSvc
```

## Network Drive Access

If your watch directory is a network path (`\\research-cifs.nyumc.org\...`):

**You MUST use a domain account**, not LocalSystem:

```cmd
python simple_W_service.py --username "nyumc\castrk05_adm" --password "YourPassword" --startup auto install
```

LocalSystem cannot access network drives.

## Testing Before Installing Service

Before installing as a service, test the script directly:

```cmd
# Test the processor
python -c "from excel_processor import ExcelProcessor; print('Processor OK')"

# Test the config
python -c "from config import config; print('Config OK'); print('Watch:', config.watch_directory)"

# Test adaptive processor
python -c "from adaptive_excel_processor import AdaptiveExcelProcessor; print('Adaptive OK')"

# Run the debug script
python debug_adaptive_processor.py
```

## Recommended Installation Method

For your setup with network drives:

1. ✅ Use `install_service_with_credentials.bat`
2. ✅ Run as Administrator
3. ✅ Use account: `nyumc\castrk05_adm`
4. ✅ Enter your actual password
5. ✅ Verify in services.msc
6. ✅ Start the service
7. ✅ Check Event Viewer for logs

## Support Checklist

If still having issues, check:
- [ ] Running Command Prompt as Administrator
- [ ] Correct Python path
- [ ] pywin32 installed: `pip install pywin32`
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Config file exists: `monitor_config.json`
- [ ] Keyword files exist
- [ ] Watch directory accessible
- [ ] Output directory writable

## Contact Information

If problems persist, gather this information:
1. Output of: `python simple_W_service.py install`
2. Output of: `sc query MonitorFolderSvc`
3. Event Viewer errors
4. Python version: `python --version`
5. Current user: `whoami`
