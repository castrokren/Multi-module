# Apply the crossref_utils import fix to crossref_standalone_fast.py
# This script adds sys.path setup to allow local module imports when
# the module is loaded via importlib.util.spec_from_file_location()

$file_path = "C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS\src\services\cross-reference\crossref_standalone_fast.py"

Write-Host "Applying crossref_utils import fix..."
Write-Host "File: $file_path"
Write-Host ""

if (!(Test-Path $file_path)) {
    Write-Host "ERROR: File not found at $file_path" -ForegroundColor Red
    exit 1
}

# Read the file
$content = Get-Content $file_path -Raw

# Check if fix is already applied
if ($content -match "Ensure the module's own directory is in sys.path") {
    Write-Host "Fix already applied!" -ForegroundColor Green
    exit 0
}

# Create the new import block as a here-string to preserve Python syntax
$new_import_block = @'
from pathlib import Path

# Ensure the module's own directory is in sys.path for local imports
# This is needed when the module is loaded via importlib.util.spec_from_file_location
# (which happens in pipeline.py) so that "from crossref_utils import ..." works
_MODULE_DIR = Path(__file__).parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

'@

# Apply the fix: find "import os" and add the new block after it
$fixed_content = $content -replace '(import os\r?\n)', "`$1$new_import_block"

# Backup original file
$backup_path = "$file_path.backup"
Copy-Item $file_path $backup_path
Write-Host "✓ Backup created: $backup_path" -ForegroundColor Green

# Write the fixed content
[System.IO.File]::WriteAllText($file_path, $fixed_content, [System.Text.Encoding]::UTF8)

Write-Host "✓ Fix applied successfully!" -ForegroundColor Green
Write-Host "The crossref_standalone_fast.py module can now find crossref_utils.py"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Test Stage 3 only: python pipeline.py --only-crossref"
Write-Host "2. If successful, run full pipeline: python pipeline.py"
Write-Host ""
Write-Host "To verify the fix was applied, check the file:"
Write-Host "  grep 'Ensure the module' PROJECTS\src\services\cross-reference\crossref_standalone_fast.py"
