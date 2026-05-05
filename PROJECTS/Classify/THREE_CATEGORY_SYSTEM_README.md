# Three-Category Classification System

## Overview

The Excel file sorting system has been upgraded from a two-category system (Hardware/Software) to a **three-category system** based on your Excel classification analysis:

1. **Research Instruments** - Scientific instruments and measurement equipment
2. **Software** - Software licenses, subscriptions, and digital services
3. **Non-Instruments** - Consumables, accessories, parts, services, and other items

## What Changed

### New Keyword Files

Three new keyword files have been created based on your Excel analysis:

- **`research_instrument_keywords.txt`** - Replaces `hardware_keywords.txt`
  - Contains keywords for microscopes, spectrometers, centrifuges, PCR equipment, etc.
  - ~200+ research instrument keywords

- **`software_keywords.txt`** - Enhanced version
  - Contains software, license, subscription keywords
  - Scientific software (MATLAB, LabView, FlowJo, GraphPad, etc.)
  - ~250+ software-related keywords

- **`non_instrument_keywords.txt`** - NEW
  - Contains keywords for kits, reagents, consumables, accessories, parts, services
  - ~200+ non-instrument keywords

### Updated Classification Logic

The new classification system handles overlapping categories intelligently:

1. **Priority Order**: Research Instrument > Software > Non-Instrument
2. **Overlap Handling**:
   - Instrument + Software → Research Instrument (e.g., "microscope with imaging software")
   - Instrument + Non-Instrument → Checks for strong non-instrument signals (kit, reagent, service)
   - Software + Non-Instrument → Software (e.g., "software license renewal")
3. **No Match** → "Unknown" (requires manual review or additional keywords)

### Updated UI

The `Updated_Monitor_UI.py` now includes:

- **New field**: "Non-Instrument Keywords" file selector
- **Updated labels**: "Hardware Keywords" → "Research Instrument Keywords"
- **Enhanced testing**: Shows three-category analytics
- **Updated reports**: Learning reports include all three categories

### Updated Adaptive Processor

The `adaptive_excel_processor.py` now:

- Supports three-category learning and keyword promotion
- Tracks candidate keywords separately for each category
- Generates analytics for all three categories
- Creates backups in `#backup_logs` subfolder (as per your preference)

## How to Use

### First-Time Setup

1. **Load the new configuration**:
   - Open `Updated_Monitor_UI.py`
   - Use "Load Config" or manually set the keyword files:
     - Research Instrument Keywords: `research_instrument_keywords.txt`
     - Software Keywords: `software_keywords.txt`
     - Non-Instrument Keywords: `non_instrument_keywords.txt`

2. **Test the configuration**:
   - Click "Test Configuration" button
   - Review the classification results
   - Check the learning analytics for all three categories

3. **Save the configuration**:
   - Click "Save Config" to persist the settings

### Processing Files

The classification will now return one of these values:

- **"Research Instrument"** - Scientific instruments
- **"Software"** - Software and digital services
- **"Non-Instrument"** - Consumables, parts, services, etc.
- **"Unknown"** - No keyword match (may need manual review)

### Adaptive Learning

The adaptive learning system now learns keywords for all three categories:

- **Instrument candidates** - Potential new instrument keywords
- **Software candidates** - Potential new software keywords
- **Non-Instrument candidates** - Potential new non-instrument keywords

Each category's keywords are promoted independently when they meet the minimum occurrence and confidence thresholds.

## Example Classifications

### Research Instruments
- "Zeiss LSM 900 Confocal Microscope" → **Research Instrument**
- "Applied Biosystems 7500 Real-Time PCR System" → **Research Instrument**
- "Thermo Scientific Sorvall LYNX 6000 Centrifuge" → **Research Instrument**

### Software
- "MATLAB R2023a License Renewal" → **Software**
- "GraphPad Prism 10 Subscription" → **Software**
- "Adobe Creative Cloud Annual License" → **Software**

### Non-Instruments
- "Qiagen DNeasy Blood & Tissue Kit" → **Non-Instrument**
- "Eppendorf PCR Tube 0.2mL (1000 pcs)" → **Non-Instrument**
- "Equipment Installation and Calibration Service" → **Non-Instrument**
- "Nikon Microscope Replacement Bulb" → **Non-Instrument**

### Intelligent Overlap Handling
- "Microscope with ZEN Software Bundle" → **Research Instrument** (instrument takes priority)
- "Centrifuge Rotor Replacement Part" → **Non-Instrument** (strong non-instrument signal: "replacement part")
- "MATLAB License with Annual Support" → **Software** (software + service context)

## Benefits of the Three-Category System

1. **More Accurate Classification**
   - Separates consumables from instruments
   - Distinguishes services from equipment
   - Better handling of accessories and parts

2. **Better Data Organization**
   - Easier to track consumable spending vs. capital equipment
   - Separates software licenses from hardware
   - Clearer reporting and budgeting

3. **Improved Learning**
   - Learns appropriate keywords for each category
   - Reduces ambiguous classifications
   - Better handles edge cases

4. **Based on Real Data**
   - Keywords derived from your actual Excel file analysis
   - Reflects your specific research environment
   - Includes scientific software you actually use

## Maintenance

### Adding Keywords Manually

Edit the keyword files directly:

```txt
# research_instrument_keywords.txt
microscope
spectrometer
# Add new keywords here (one per line)
```

### Reviewing Unknown Items

Items classified as "Unknown" may need:
- Additional keywords added to one of the three files
- Manual review to determine the correct category
- Supplier/vendor lookup (as you suggested in your analysis)

### Backups

All keyword file updates create automatic backups in:
- `[output_directory]/#backup_logs/`
- Filename format: `[category]_keywords_backup_[timestamp].txt`

## Migration from Old System

The old `hardware_keywords.txt` is **not** automatically migrated. To migrate:

1. Review items currently classified as "Hardware"
2. Determine if they should be:
   - Research Instruments (actual equipment)
   - Non-Instruments (accessories, parts, consumables)
3. Add any missing keywords to the appropriate new file

## Troubleshooting

### Issue: Many items showing as "Unknown"

**Solution**: 
- Review the Unknown items
- Add relevant keywords to the appropriate category file
- Use the adaptive learning feature to discover new keywords

### Issue: Items classified incorrectly

**Solution**:
- Check for keyword conflicts between categories
- Add more specific keywords
- Use the classification logic priority to your advantage

### Issue: Adaptive learning suggesting wrong keywords

**Solution**:
- Increase the `min_occurrences` threshold
- Increase the `confidence_threshold` value
- Review and reject suggested keywords in the learning report

## Questions?

Refer to:
- `ADAPTIVE_PROCESSOR_GUIDE.md` - For adaptive learning details
- `SERVICE_INSTALLATION_GUIDE.md` - For service installation
- Your Excel analysis notes - For the original keyword research

---

**Created**: Based on your Excel classification analysis with 4,314 rows
**Keywords**: Research Instruments (200+), Software (250+), Non-Instruments (200+)
**Classification Approach**: Description-based with intelligent overlap handling

