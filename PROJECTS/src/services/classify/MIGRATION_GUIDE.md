# Migration Guide: Two-Category → Three-Category System

This guide helps you migrate from the old two-category system (Hardware/Software) to the new three-category system (Research Instruments/Software/Non-Instruments).

## Quick Start (5 minutes)

1. **Open the UI**:
   ```bash
   python Updated_Monitor_UI.py
   ```

2. **Update the keyword files**:
   - Research Instrument Keywords: Browse to `research_instrument_keywords.txt`
   - Software Keywords: Browse to `software_keywords.txt`
   - Non-Instrument Keywords: Browse to `non_instrument_keywords.txt`

3. **Test the configuration**:
   - Click "Test Configuration"
   - Review the results in the log window
   - Check that classifications look correct

4. **Save the configuration**:
   - Click "Save Config"
   - This will update `monitor_config.json` with the new settings

5. **Done!** The system will now use the three-category classification.

## What Files Were Created

### New Keyword Files
- ✅ `research_instrument_keywords.txt` - 200+ research instrument keywords
- ✅ `software_keywords.txt` - 250+ software keywords (enhanced)
- ✅ `non_instrument_keywords.txt` - 200+ non-instrument keywords

### Updated Code Files
- ✅ `adaptive_excel_processor.py` - Now supports three categories
- ✅ `Updated_Monitor_UI.py` - New UI field for non-instrument keywords

### Documentation
- ✅ `THREE_CATEGORY_SYSTEM_README.md` - Full documentation
- ✅ `MIGRATION_GUIDE.md` - This file

### Preserved Files
- ⚠️ `hardware_keywords.txt` - Updated with deprecation notice (kept for compatibility)
- ✅ `software_keywords.txt` - Enhanced with your keywords

## Configuration File Changes

Your `monitor_config.json` will be updated with:

```json
{
  "watch_directory": "your/watch/directory",
  "output_directory": "your/output/directory",
  "hardware_keywords_file": "research_instrument_keywords.txt",
  "software_keywords_file": "software_keywords.txt",
  "non_instrument_keywords_file": "non_instrument_keywords.txt",
  "use_adaptive_processor": true,
  "learning_mode": true,
  "min_occurrences": "5",
  "confidence_threshold": "0.7"
}
```

## Backward Compatibility

### Old Scripts Still Work

If you have custom scripts that use the old two-category system:

```python
# This will still work (uses old hardware_keywords.txt)
from excel_processor import ExcelProcessor
processor = ExcelProcessor(
    hw_keywords_file="hardware_keywords.txt",
    sw_keywords_file="software_keywords.txt",
    output_dir="output"
)
```

### Migrating Old Scripts to Three Categories

Update your custom scripts to use the new system:

```python
# New three-category system
from adaptive_excel_processor import AdaptiveExcelProcessor

processor = AdaptiveExcelProcessor(
    hw_keywords_file="research_instrument_keywords.txt",
    sw_keywords_file="software_keywords.txt",
    ni_keywords_file="non_instrument_keywords.txt",  # NEW
    output_dir="output",
    learning_mode=True,
    min_occurrences=5
)

# Process a file
processor.process_file("input_file.xlsx")
```

## Classification Behavior Changes

### Before (Two Categories)
```
Item Description               Old Classification
-------------------------------------------------
"PCR Machine"                  → Instrument
"PCR Reagent Kit"              → Unknown
"PCR Machine Service"          → Unknown
"PCR Software License"         → Software
```

### After (Three Categories)
```
Item Description               New Classification
-------------------------------------------------
"PCR Machine"                  → Research Instrument
"PCR Reagent Kit"              → Non-Instrument
"PCR Machine Service"          → Non-Instrument
"PCR Software License"         → Software
```

## Expected Results After Migration

Based on your Excel analysis of 4,314 rows:

### Before Migration (estimated)
- Hardware/Instrument: ~700
- Software: ~120
- Unknown: ~3,494

### After Migration (expected)
- Research Instrument: ~700
- Software: ~120
- Non-Instrument: ~1,000-1,500
- Unknown: ~2,000-2,500

The "Unknown" count will decrease as:
1. The adaptive learning system discovers new keywords
2. You manually add keywords for your specific items
3. You optionally implement the vendor lookup enhancement you mentioned

## Testing Checklist

After migration, verify:

- [ ] UI shows three keyword file fields
- [ ] All three keyword files load without errors
- [ ] "Test Configuration" completes successfully
- [ ] Test results show three-category analytics
- [ ] Classifications appear in "TYPE" column correctly
- [ ] Learning log updates with all three categories
- [ ] Backup logs are created in `#backup_logs` subdirectory
- [ ] Config saves and loads correctly
- [ ] Adaptive learning promotes keywords for all three categories

## Troubleshooting

### "Research Instrument keywords file does not exist"

**Fix**: Make sure you're pointing to the new file:
- Browse to: `research_instrument_keywords.txt`
- Not: `hardware_keywords.txt`

### "Non-Instrument keywords file is required"

**Fix**: You must specify all three keyword files:
- Research Instrument Keywords: `research_instrument_keywords.txt`
- Software Keywords: `software_keywords.txt`  
- Non-Instrument Keywords: `non_instrument_keywords.txt`

### Items are misclassified

**Fix**: The classification logic uses this priority:
1. Research Instrument (highest priority)
2. Software
3. Non-Instrument
4. Unknown (no matches)

If an item matches multiple categories, it will be classified by the highest priority match. To change this behavior, edit the `classify_item` method in `adaptive_excel_processor.py`.

### Adaptive learning suggests wrong category

**Fix**: 
- Increase `min_occurrences` (try 10 instead of 5)
- Increase `confidence_threshold` (try 0.8 instead of 0.7)
- Manually review and reject bad suggestions

## Rollback Procedure (if needed)

If you need to rollback to the old system:

1. **In UI, set keyword files back to**:
   - Hardware Keywords: `hardware_keywords.txt`
   - Software Keywords: `software_keywords.txt`
   - Non-Instrument Keywords: Leave blank or point to an empty file

2. **Use the original processor**:
   - Uncheck "Use Adaptive Processor" in the UI
   - Or use `excel_processor.py` instead of `adaptive_excel_processor.py`

3. **Restore old config** (if you have a backup):
   - Copy your backed-up `monitor_config.json` over the current one

## Need Help?

- Review `THREE_CATEGORY_SYSTEM_README.md` for full documentation
- Check the learning report: Click "Learning Report" in the UI
- Review classification results in the output Excel files
- Check logs in the UI's log window for detailed information

---

**Migration Time**: ~5 minutes  
**Testing Time**: ~10 minutes  
**Total Time**: ~15 minutes

