# Instrument Labeling Manager

A comprehensive tool for managing instrument classifications in your scraper system. This tool allows you to easily label items as instruments, change existing classifications, and manage your data efficiently.

## Features

- **GUI Application**: Full-featured desktop interface for easy management
- **Command-Line Interface**: Quick operations via terminal
- **Search & Filter**: Find items quickly by code, description, or supplier
- **Batch Operations**: Change multiple items at once
- **Safe Backups**: Automatic backup creation before saving changes [[memory:4155247]]
- **Real-time Statistics**: See current instrument counts and changes
- **Export Functionality**: Export filtered selections to new files

## Quick Start

### GUI Application
```bash
python instrument_labeling_manager.py
```

### Command-Line Interface
```bash
# Show statistics
python instrument_labeler_cli.py --stats

# List all instruments
python instrument_labeler_cli.py --list Instrument

# Search for items
python instrument_labeler_cli.py --search "microscope"

# Change a single item
python instrument_labeler_cli.py --change "ITEM_001" "Non-Instrument"

# Batch change all items from a supplier
python instrument_labeler_cli.py --batch-supplier "ZEISS" "Instrument"
```

## GUI Application Usage

### Main Interface

The GUI provides several key areas:

1. **File Management**: Load, save, and manage Excel files
2. **Status & Statistics**: Real-time view of your data
3. **Search & Filter**: Find specific items quickly
4. **Item List**: Browse all items with color coding
5. **Details Panel**: View and edit individual items
6. **Activity Log**: Track all changes made

### Color Coding

- **Green**: Instruments
- **Red**: Non-Instruments  
- **Blue**: Software
- **Yellow**: Unlabeled items

### Basic Operations

1. **Load a File**: Click "Browse" to select your Excel file
2. **Search Items**: Type in the search box to find specific items
3. **Filter by Type**: Use the dropdown to show only certain types
4. **Change Item Type**: 
   - Double-click an item to view details
   - Select new type from dropdown
   - Click "Apply Change"
5. **Batch Operations**:
   - Select multiple items (Ctrl+click)
   - Use "Quick Actions" buttons
6. **Save Changes**: Click "Save" to write changes to file

## Command-Line Interface Usage

### Basic Commands

```bash
# Show help
python instrument_labeler_cli.py --help

# Show current statistics
python instrument_labeler_cli.py --stats

# List items (default: first 20)
python instrument_labeler_cli.py --list

# List only instruments
python instrument_labeler_cli.py --list Instrument

# List unlabeled items
python instrument_labeler_cli.py --list Unlabeled

# Search for items containing "pump"
python instrument_labeler_cli.py --search pump

# Change specific item type
python instrument_labeler_cli.py --change "PUMP_001" "Instrument"

# Batch change by supplier
python instrument_labeler_cli.py --batch-supplier "AGILENT" "Instrument"
```

### Interactive Mode

Run without arguments for interactive menu:
```bash
python instrument_labeler_cli.py
```

This provides a menu-driven interface for all operations.

## Data Structure

The tool works with Excel files containing these columns:

### Required Columns (automatically detected)
- **TYPE/Type/Item Type**: Current classification
- **Item Code/Code/ID**: Unique identifier
- **Item Description/Description**: Item description
- **Supplier Name/Supplier**: Supplier information

### Supported Classifications
- **Instrument**: Items that are instruments
- **Non-Instrument**: Items that are not instruments
- **Software**: Software items
- **Unlabeled**: Items without classification

## Examples

### Example 1: Label New Items as Instruments

**GUI Method:**
1. Load your Excel file
2. Filter by "Unlabeled" to see new items
3. Select items you want to label
4. Click "Mark as Instrument"
5. Save the file

**CLI Method:**
```bash
# List unlabeled items
python instrument_labeler_cli.py --list Unlabeled

# Change specific items
python instrument_labeler_cli.py --change "NEW_ITEM_001" "Instrument"
python instrument_labeler_cli.py --change "NEW_ITEM_002" "Instrument"
```

### Example 2: Change Instrument to Non-Instrument

**GUI Method:**
1. Search for the item by code or description
2. Double-click to view details
3. Change type to "Non-Instrument"
4. Click "Apply Change"

**CLI Method:**
```bash
# Find the item first
python instrument_labeler_cli.py --search "OLD_INSTRUMENT"

# Change it
python instrument_labeler_cli.py --change "OLD_INSTRUMENT_001" "Non-Instrument"
```

### Example 3: Batch Operations by Supplier

**Scenario**: Mark all ZEISS items as instruments

**GUI Method:**
1. Search for "ZEISS" in the search box
2. Click "Select All Visible"
3. Click "Mark as Instrument"

**CLI Method:**
```bash
python instrument_labeler_cli.py --batch-supplier "ZEISS" "Instrument"
```

### Example 4: Review and Clean Up Data

**Find items that might need attention:**
```bash
# Show current statistics
python instrument_labeler_cli.py --stats

# List unlabeled items
python instrument_labeler_cli.py --list Unlabeled --limit 50

# Search for potential instruments
python instrument_labeler_cli.py --search "analyzer"
python instrument_labeler_cli.py --search "microscope"
python instrument_labeler_cli.py --search "spectrometer"
```

## Safety Features

### Automatic Backups
- Backups are created in the `#backup_logs` directory [[memory:4155247]]
- Timestamped filenames prevent overwrites
- Original files are preserved before any changes

### Change Tracking
- All changes are logged with timestamps
- Activity log shows what was changed
- Statistics update in real-time

### Validation
- Column detection prevents errors
- Duplicate checking for batch operations
- Confirmation prompts for large changes

## Tips and Best Practices

1. **Start with Statistics**: Always check `--stats` first to understand your data
2. **Use Search Effectively**: Search by partial terms to find related items
3. **Batch Carefully**: Review items before batch operations
4. **Save Regularly**: Use "Save" frequently when making many changes
5. **Check Backups**: Verify backups are created in `#backup_logs`
6. **Test First**: Try operations on a copy of your data first

## Troubleshooting

### Common Issues

**"Missing required columns" error:**
- Check that your Excel file has TYPE, Item Code, and Description columns
- Column names are flexible (TYPE/Type/Item Type all work)

**"Item not found" error:**
- Use search to find the exact item code
- Try partial matches or description searches

**"Multiple items match" error:**
- Be more specific with item identifiers
- Use exact item codes when possible

**Save failures:**
- Check file permissions
- Ensure file isn't open in Excel
- Verify backup directory exists

### Getting Help

Run with `--help` for command-line options:
```bash
python instrument_labeler_cli.py --help
```

For GUI help, check the activity log for error messages and tips.

## Integration with Existing System

This tool works seamlessly with your existing scraper system:

- **Input Files**: Uses the same Excel format as your scrapers
- **Output Files**: Maintains compatibility with existing processing
- **Filtering**: The system already respects TYPE column values
- **Backups**: Follows your backup directory convention [[memory:4155247]]

The scrapers will automatically:
- Process items marked as "Instrument"
- Skip items marked as "Non-Instrument" 
- Handle "Software" items appropriately
- Ignore unlabeled items (depending on configuration)

## File Locations

- **Main GUI**: `instrument_labeling_manager.py`
- **CLI Tool**: `instrument_labeler_cli.py`
- **Default Input**: `NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx`
- **Backups**: `#backup_logs/` directory
- **Documentation**: `INSTRUMENT_LABELING_GUIDE.md`
