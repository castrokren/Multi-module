#!/usr/bin/env python3
"""
Quick Demo of Instrument Labeling Tools
Shows how to use both GUI and CLI tools for instrument management.
"""

import os
import sys

def main():
    print("🔧 INSTRUMENT LABELING TOOLS DEMO")
    print("=" * 50)
    
    # Check if files exist
    gui_tool = "instrument_labeling_manager.py"
    cli_tool = "instrument_labeler_cli.py"
    data_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
    
    print("\n📁 CHECKING FILES:")
    for file in [gui_tool, cli_tool, data_file]:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - NOT FOUND")
    
    print("\n🖥️  GUI APPLICATION:")
    print("   Launch with: python instrument_labeling_manager.py")
    print("   Features:")
    print("   • Full desktop interface")
    print("   • Search and filter items")
    print("   • Batch operations")
    print("   • Real-time statistics")
    print("   • Safe backup creation")
    
    print("\n⌨️  COMMAND-LINE INTERFACE:")
    print("   Quick commands:")
    print("   • Show stats:     python instrument_labeler_cli.py --stats")
    print("   • List items:     python instrument_labeler_cli.py --list")
    print("   • Search:         python instrument_labeler_cli.py --search 'microscope'")
    print("   • Change item:    python instrument_labeler_cli.py --change 'ITEM_001' 'Instrument'")
    print("   • Batch change:   python instrument_labeler_cli.py --batch-supplier 'ZEISS' 'Instrument'")
    print("   • Interactive:    python instrument_labeler_cli.py")
    
    print("\n📊 COMMON TASKS:")
    print("   1. Label new items as instruments:")
    print("      • GUI: Filter by 'Unlabeled', select items, click 'Mark as Instrument'")
    print("      • CLI: python instrument_labeler_cli.py --list Unlabeled")
    print("             python instrument_labeler_cli.py --change 'NEW_ITEM' 'Instrument'")
    
    print("\n   2. Change instrument to non-instrument:")
    print("      • GUI: Search for item, double-click, change type, apply")
    print("      • CLI: python instrument_labeler_cli.py --change 'OLD_ITEM' 'Non-Instrument'")
    
    print("\n   3. Batch operations by supplier:")
    print("      • GUI: Search supplier name, select all, use quick actions")
    print("      • CLI: python instrument_labeler_cli.py --batch-supplier 'SUPPLIER' 'Instrument'")
    
    print("\n🔒 SAFETY FEATURES:")
    print("   • Automatic backups in #backup_logs directory")
    print("   • Change tracking and logging")
    print("   • Confirmation prompts for batch operations")
    print("   • Data validation and error checking")
    
    print("\n📖 DOCUMENTATION:")
    print("   • Full guide: INSTRUMENT_LABELING_GUIDE.md")
    print("   • CLI help:   python instrument_labeler_cli.py --help")
    
    print("\n" + "=" * 50)
    
    # Interactive demo
    while True:
        print("\nWould you like to:")
        print("1. Launch GUI application")
        print("2. Run CLI stats")
        print("3. Show CLI help")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            if os.path.exists(gui_tool):
                print(f"Launching {gui_tool}...")
                os.system(f"python {gui_tool}")
            else:
                print(f"❌ {gui_tool} not found")
        
        elif choice == "2":
            if os.path.exists(cli_tool):
                print("Running CLI stats...")
                os.system(f"python {cli_tool} --stats")
            else:
                print(f"❌ {cli_tool} not found")
        
        elif choice == "3":
            if os.path.exists(cli_tool):
                print("Showing CLI help...")
                os.system(f"python {cli_tool} --help")
            else:
                print(f"❌ {cli_tool} not found")
        
        elif choice == "4":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
