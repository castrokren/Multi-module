@echo off
echo Processing Excel files from SMB share...
echo.
cd /d "C:\Projects\Crawler\PROJECTS\src\services\classify"
"C:\Users\castrk05_adm\AppData\Local\Programs\Python\Python313\python.exe" process_all_files.py
echo.
echo Processing complete! Press any key to exit.
pause
