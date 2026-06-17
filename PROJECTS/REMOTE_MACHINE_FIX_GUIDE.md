# Remote Machine Fix Guide: CrossRef Import Error

## Problem
Pipeline Stage 3 (Cross-reference) fails with:
```
ERROR pipeline — Cannot import CrossReferenceEngine: No module named 'crossref_utils'
```

## Root Cause
When `crossref_standalone_fast.py` is loaded via `importlib.util.spec_from_file_location()` in the pipeline, Python can't find the local `crossref_utils.py` module because the module's directory is not in `sys.path`.

## Solution
Add sys.path setup to `crossref_standalone_fast.py` to ensure it can find its sibling module.

---

## Quick Apply (Recommended for Windows Remote Machine)

### Option 1: Run PowerShell Script (Easiest)

1. **Copy the fix script to your remote machine:**
   - File: `apply_crossref_fix.ps1`
   - Location: Copy to your Multi-module root or anywhere accessible

2. **Run the script (as Administrator):**
   ```powershell
   # Navigate to the script location and run:
   powershell -ExecutionPolicy Bypass -File apply_crossref_fix.ps1
   ```

3. **Expected output:**
   ```
   ✓ Backup created: ...
   ✓ Fix applied successfully!
   ```

---

### Option 2: Manual Edit (If script doesn't work)

**Edit:** `C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS\src\services\cross-reference\crossref_standalone_fast.py`

**Find** this section (around line 1-22):
```python
#!/usr/bin/env python3
"""
Standalone Cross-reference Module
"""

import sys
import os
import re
import time
...
from crossref_utils import normalize_filename, deduplicate_matches
```

**Replace with** this section:
```python
#!/usr/bin/env python3
"""
Standalone Cross-reference Module
"""

import sys
import os
from pathlib import Path

# Ensure the module's own directory is in sys.path for local imports
# This is needed when the module is loaded via importlib.util.spec_from_file_location
# (which happens in pipeline.py) so that "from crossref_utils import ..." works
_MODULE_DIR = Path(__file__).parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

import re
import time
...
from crossref_utils import normalize_filename, deduplicate_matches
```

**Key point:** The 11 lines of sys.path setup code must be added between `import os` and `import re`.

---

### Option 3: Git Update (If you prefer pulling)

If you have git set up on the remote machine:

```bash
cd C:\Users\castrk05_adm\Desktop\Multi-module
git pull origin main
```

---

## Verification

After applying the fix, verify it worked by checking the file:

```bash
# Should see the sys.path setup code around line 8-15
head -30 PROJECTS/src/services/cross-reference/crossref_standalone_fast.py
```

You should see:
```python
from pathlib import Path

# Ensure the module's own directory is in sys.path for local imports
_MODULE_DIR = Path(__file__).parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))
```

---

## Test the Pipeline

### Stage 3 Only (Quick Test)
```bash
cd C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS\src\services
python pipeline.py --only-crossref
```

Expected: Stage 3 should now run without the import error

### Full Pipeline (Complete Test)
```bash
cd C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS\src\services
python pipeline.py
```

Expected: All 5 stages should complete successfully

---

## If Still Failing

If you still get `ModuleNotFoundError` after applying the fix:

1. **Check the file was actually modified:**
   ```bash
   grep "Ensure the module's own directory" PROJECTS/src/services/cross-reference/crossref_standalone_fast.py
   ```
   Should return the comment line

2. **Verify imports are available:**
   ```bash
   python -c "from pathlib import Path; print('✓ pathlib available')"
   python -c "import crossref_utils; print('✓ crossref_utils found')" 
   ```

3. **Check Python path:**
   ```bash
   python -c "import sys; print('\\n'.join(sys.path))"
   ```

4. **Run diagnostic test:**
   ```bash
   python PROJECTS/src/services/cross-reference/simple_check.py
   ```

---

## Troubleshooting

### "Permission denied" when running script
- Run PowerShell as Administrator
- Or use manual edit instead

### "File not found" error
- Verify file path matches your installation
- Default: `C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS\src\services\cross-reference\crossref_standalone_fast.py`

### Pipeline still fails with different error
- The import is now fixed, but there may be other issues
- Check all prior stages (0-2) pass successfully
- Verify paths in `pipeline_config.json` are correct

---

## What This Fix Does

The fix adds 11 lines of Python code that:

1. Imports `pathlib.Path` (standard library, always available)
2. Gets the directory where the current module file is located
3. Adds that directory to Python's module search path (`sys.path`)
4. Ensures this happens BEFORE the local `crossref_utils` import

This allows the pipeline's dynamic import mechanism to work correctly while preserving the module's ability to find its own dependencies.

---

## Questions?

If you encounter issues:
1. Provide the exact error message from the pipeline
2. Share the output of: `python -c "import sys; import crossref_utils; print('OK')"`
3. Check that the fix code is actually in the file (search for "Ensure the module's own")
