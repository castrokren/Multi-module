# Enhanced Adaptive Excel Processor Guide

## Overview
The Enhanced Adaptive Excel Processor is an intelligent version of your original Excel processor that learns and improves over time. It automatically discovers new keywords from your data and adds them to your classification system.

## Key Features

### 🧠 Self-Learning Capabilities
- **Automatic Keyword Discovery**: Extracts potential keywords from classified items
- **Smart Promotion**: Promotes frequently occurring keywords to your main keyword lists
- **Confidence Scoring**: Uses confidence-based learning to improve accuracy
- **Keyword Validation**: Validates keywords before promotion to prevent contamination

### 🛡️ Safety Features
- **Backup System**: Automatically backs up keyword files before updates
- **Test Mode**: Process files without making changes to keyword lists
- **Validation**: Rejects invalid keywords (model numbers, units, common words)
- **Conservative Defaults**: Uses safe settings by default

### 📊 Analytics & Monitoring
- **Learning Reports**: Detailed reports on learning progress
- **Candidate Tracking**: Monitor keywords ready for promotion
- **Analytics Dashboard**: Comprehensive learning analytics

## Quick Start

### 1. Basic Usage
```python
from adaptive_excel_processor import AdaptiveExcelProcessor

# Initialize with conservative settings
processor = AdaptiveExcelProcessor(
    hw_keywords_file="hardware_keywords.txt",
    sw_keywords_file="software_keywords.txt",
    output_dir=r"D:\SOM_in_labeled",
    learning_mode=True,
    min_occurrences=5  # Keywords must appear 5+ times to be promoted
)

# Process a file
processor.process_file("your_file.xlsx")
```

### 2. Safe Testing
```python
# Test without making changes to keyword files
processor.process_file("test_file.xlsx", test_mode=True)

# View learning report
print(processor.get_learning_report())
```

### 3. Integration with Existing Code
Replace your existing processor:
```python
# OLD
from excel_processor import ExcelProcessor
processor = ExcelProcessor(hw_file, sw_file, output_dir)

# NEW  
from adaptive_excel_processor import AdaptiveExcelProcessor
processor = AdaptiveExcelProcessor(hw_file, sw_file, output_dir, learning_mode=True)
```

## Configuration Options

### Learning Settings
- `learning_mode=True/False`: Enable/disable learning
- `min_occurrences=5`: Minimum times a keyword must appear before promotion
- `confidence_threshold=0.7`: Minimum confidence for keyword acceptance

### Safety Settings
- `test_mode=True`: Process without making changes
- `auto_promote=False`: Learn but don't promote keywords automatically

## Testing Your Setup

### 1. Run the Test Suite
```bash
python test_adaptive_processor.py
```

### 2. Use Integration Helper
```bash
python integrate_adaptive_processor.py
```

### 3. Compare with Original
The integration script will compare results between your original processor and the adaptive version to ensure compatibility.

## Learning Process

### How It Works
1. **Classification**: Items are classified using existing keywords
2. **Keyword Extraction**: New keywords are extracted from descriptions of classified items
3. **Confidence Scoring**: Keywords receive confidence scores based on context
4. **Validation**: Keywords are validated before promotion
5. **Promotion**: Valid keywords are promoted to main keyword lists

### What Gets Learned
✅ **Good Keywords**:
- Technical terms (spectrometer, analyzer, detector)
- Instrument types (microscope, balance, meter)
- Software terms (application, database, interface)

❌ **Rejected Keywords**:
- Model numbers (MDF-C2156VANC-PA)
- Measurements (26 CU.FT., 115V)
- Common words (system, device, equipment)
- Units (cu, ft, volts, watts)

## Monitoring Learning

### Learning Report Example
```
=== ADAPTIVE LEARNING REPORT ===
Generated: 2024-01-15 14:30:25

Current Keywords:
- Hardware: 245 keywords
- Software: 156 keywords

Learning Progress:
- Total classifications learned from: 1,247
- HW candidates: 23
- SW candidates: 8

Ready for Promotion (≥5 occurrences):
- HW: 3 candidates
- SW: 1 candidates

Top HW Candidates:
  - calorimeter: 7.2
  - viscometer: 6.8
  - tensiometer: 5.5
```

### Backup Files
Backups are automatically created in `#backup_logs/` directory:
- `hardware_keywords_backup_20240115_143025.txt`
- `software_keywords_backup_20240115_143025.txt`

## Troubleshooting

### Common Issues

**Q: Keywords aren't being promoted**
- Check `min_occurrences` setting (try lowering it)
- Ensure `learning_mode=True`
- Verify items are being classified correctly

**Q: Too many false positives**
- Increase `min_occurrences` threshold
- Review rejected keywords in logs
- Check confidence threshold settings

**Q: Learning seems slow**
- Process more files to increase keyword frequency
- Lower `min_occurrences` temporarily
- Check if items are matching existing keywords

### Log Files
- `test_adaptive_processor.log`: Test run logs
- `learning_log.json`: Learning data persistence
- `#backup_logs/`: Keyword file backups

## Best Practices

### 1. Start Conservative
```python
processor = AdaptiveExcelProcessor(
    min_occurrences=10,  # High threshold initially
    learning_mode=True
)
```

### 2. Test First
```python
# Always test before full deployment
processor.process_file("test_file.xlsx", test_mode=True)
```

### 3. Monitor Progress
```python
# Regular learning reports
print(processor.get_learning_report())
```

### 4. Backup Regularly
The system creates automatic backups, but you can also manually backup your keyword files.

## Migration from Original Processor

1. **Test Compatibility**: Run `integrate_adaptive_processor.py`
2. **Compare Results**: Ensure classifications match
3. **Start with Test Mode**: Use `test_mode=True` initially
4. **Gradual Rollout**: Process a few files, review results
5. **Full Deployment**: Enable learning once confident

## Support

- Check logs for detailed error messages
- Use test mode to diagnose issues
- Review learning reports for insights
- Compare with original processor results

The adaptive processor is designed to be safe and backward-compatible while providing powerful learning capabilities to improve your classification accuracy over time.
