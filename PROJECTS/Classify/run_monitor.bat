@echo off
echo Starting Excel Folder Monitor...
echo Watching directory: Y:\SOM_in
echo Script path: C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify\classify_and_clean_dynamic.py
echo.
echo Press Ctrl+C to stop monitoring
echo.

set WATCH_DIR=Y:\SOM_in
set SCRIPT_PATH=C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify\classify_and_clean_dynamic.py

python monitor_folder.py
