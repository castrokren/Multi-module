#!/usr/bin/env python3
"""
Simple Command-Line Interface for Instrument Labeling
Quick operations for changing instrument classifications.
"""

import pandas as pd
import os
import sys
import argparse
from datetime import datetime
import shutil

from crossref_utils import find_required_columns

class InstrumentLabelerCLI:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.backup_dir = "#backup_logs"

        # Create backup directory
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        self.load_file()

    def load_file(self):
        """Load the Excel file."""
        try:
            self.df = pd.read_excel(self.file_path)
            print(f"✅ Loaded {len(self.df)} items from {self.file_path}")

            # Find required columns
            self.cols = find_required_columns(self.df)
            if not all(self.cols.values()):
                missing = [k for k, v in self.cols.items() if not v]
                print(f"❌ Missing required columns: {missing}")
                sys.exit(1)

        except Exception as e:
            print(f"❌ Error loading file: {e}")
            sys.exit(1)
    
    def show_stats(self):
        """Show current statistics."""
        if not self.cols['type_col']:
            print("❌ No TYPE column found")
            return
        
        type_counts = self.df[self.cols['type_col']].fillna('Unlabeled').value_counts()
        
        print("\n📊 CURRENT STATISTICS:")
        print(f"   Total items: {len(self.df)}")
        print(f"   Instruments: {type_counts.get('Instrument', 0)}")
        print(f"   Non-Instruments: {type_counts.get('Non-Instrument', 0)}")
        print(f"   Software: {type_counts.get('Software', 0)}")
        print(f"   Unlabeled: {type_counts.get('Unlabeled', 0)}")
    
    def search_items(self, search_term, item_type=None):
        """Search for items."""
        search_term = search_term.lower()
        
        # Create search mask
        search_mask = pd.Series([False] * len(self.df))
        
        # Search in multiple columns
        search_columns = [self.cols['code_col'], self.cols['desc_col'], self.cols['supplier_col']]
        for col in search_columns:
            if col and col in self.df.columns:
                search_mask |= self.df[col].astype(str).str.lower().str.contains(search_term, na=False)
        
        results = self.df[search_mask]
        
        # Filter by type if specified
        if item_type and self.cols['type_col']:
            if item_type.lower() == 'unlabeled':
                results = results[results[self.cols['type_col']].isna() | 
                                (results[self.cols['type_col']].astype(str).str.strip() == '')]
            else:
                results = results[results[self.cols['type_col']].astype(str).str.lower().str.strip() == item_type.lower()]
        
        return results
    
    def list_items(self, item_type=None, limit=20):
        """List items, optionally filtered by type."""
        df_to_show = self.df.copy()
        
        # Filter by type if specified
        if item_type and self.cols['type_col']:
            if item_type.lower() == 'unlabeled':
                df_to_show = df_to_show[df_to_show[self.cols['type_col']].isna() | 
                                      (df_to_show[self.cols['type_col']].astype(str).str.strip() == '')]
            else:
                df_to_show = df_to_show[df_to_show[self.cols['type_col']].astype(str).str.lower().str.strip() == item_type.lower()]
        
        if len(df_to_show) == 0:
            print("No items found matching criteria.")
            return
        
        print(f"\n📋 ITEMS ({len(df_to_show)} total, showing first {min(limit, len(df_to_show))}):")
        print("-" * 80)
        
        for idx, (_, row) in enumerate(df_to_show.head(limit).iterrows()):
            item_code = str(row.get(self.cols['code_col'], f'ITEM_{idx+1}')).strip()
            item_type = str(row.get(self.cols['type_col'], 'Unlabeled')).strip()
            description = str(row.get(self.cols['desc_col'], '')).strip()[:50]
            supplier = str(row.get(self.cols['supplier_col'], '')).strip()[:30]
            
            print(f"{idx+1:3d}. {item_code:<15} [{item_type:<15}] {description:<50} ({supplier})")
    
    def change_item_type(self, item_identifier, new_type):
        """Change the type of an item."""
        if not self.cols['type_col']:
            print("❌ No TYPE column found")
            return False
        
        # Find the item
        if self.cols['code_col']:
            mask = self.df[self.cols['code_col']].astype(str).str.strip().str.lower() == item_identifier.lower()
        else:
            # Try to find by description
            if self.cols['desc_col']:
                mask = self.df[self.cols['desc_col']].astype(str).str.lower().str.contains(item_identifier.lower(), na=False)
            else:
                print("❌ Cannot identify items without code or description column")
                return False
        
        if not mask.any():
            print(f"❌ Item not found: {item_identifier}")
            return False
        
        if mask.sum() > 1:
            print(f"⚠️ Multiple items match '{item_identifier}'. Please be more specific.")
            matching_items = self.df[mask]
            for idx, (_, row) in enumerate(matching_items.head(5).iterrows()):
                item_code = str(row.get(self.cols['code_col'], f'ITEM_{idx+1}')).strip()
                description = str(row.get(self.cols['desc_col'], '')).strip()[:50]
                print(f"   {idx+1}. {item_code} - {description}")
            return False
        
        # Get current type
        current_type = str(self.df.loc[mask, self.cols['type_col']].iloc[0]).strip()
        item_code = str(self.df.loc[mask, self.cols['code_col']].iloc[0]).strip() if self.cols['code_col'] else item_identifier
        
        if current_type == new_type:
            print(f"⚠️ Item {item_code} is already marked as {new_type}")
            return False
        
        # Make the change
        self.df.loc[mask, self.cols['type_col']] = new_type
        print(f"✅ Changed {item_code}: {current_type} → {new_type}")
        return True
    
    def batch_change_by_supplier(self, supplier_name, new_type):
        """Change all items from a supplier to a new type."""
        if not self.cols['supplier_col']:
            print("❌ No supplier column found")
            return 0
        
        # Find items from this supplier
        mask = self.df[self.cols['supplier_col']].astype(str).str.lower().str.contains(supplier_name.lower(), na=False)
        
        if not mask.any():
            print(f"❌ No items found for supplier: {supplier_name}")
            return 0
        
        matching_items = self.df[mask]
        print(f"Found {len(matching_items)} items from supplier '{supplier_name}'")
        
        # Confirm the change
        response = input(f"Change all {len(matching_items)} items to '{new_type}'? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return 0
        
        # Make the changes
        self.df.loc[mask, self.cols['type_col']] = new_type
        print(f"✅ Changed {len(matching_items)} items to {new_type}")
        return len(matching_items)
    
    def create_backup(self):
        """Create a backup of the current file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(self.file_path)
            name, ext = os.path.splitext(filename)
            backup_filename = f"{name}_backup_{timestamp}{ext}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            shutil.copy2(self.file_path, backup_path)
            print(f"📁 Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def save_changes(self):
        """Save changes to the file."""
        # Create backup first
        backup_path = self.create_backup()
        if not backup_path:
            response = input("Could not create backup. Continue saving anyway? (y/N): ")
            if response.lower() != 'y':
                print("Save cancelled.")
                return False
        
        try:
            self.df.to_excel(self.file_path, index=False)
            print(f"✅ Changes saved to {self.file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Instrument Labeling CLI Tool")
    parser.add_argument("file", nargs="?", default="NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
                       help="Excel file to process")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--list", metavar="TYPE", nargs="?", const="all",
                       help="List items (optionally filtered by type)")
    parser.add_argument("--search", metavar="TERM", help="Search for items")
    parser.add_argument("--change", nargs=2, metavar=("ITEM", "TYPE"),
                       help="Change item type (ITEM TYPE)")
    parser.add_argument("--batch-supplier", nargs=2, metavar=("SUPPLIER", "TYPE"),
                       help="Change all items from supplier to type")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of items shown")
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    # Initialize CLI
    cli = InstrumentLabelerCLI(args.file)
    
    changes_made = False
    
    # Execute commands
    if args.stats:
        cli.show_stats()
    
    if args.list:
        list_type = None if args.list == "all" else args.list
        cli.list_items(item_type=list_type, limit=args.limit)
    
    if args.search:
        results = cli.search_items(args.search)
        if len(results) > 0:
            print(f"\n🔍 SEARCH RESULTS for '{args.search}' ({len(results)} found):")
            print("-" * 80)
            for idx, (_, row) in enumerate(results.head(args.limit).iterrows()):
                item_code = str(row.get(cli.cols['code_col'], f'ITEM_{idx+1}')).strip()
                item_type = str(row.get(cli.cols['type_col'], 'Unlabeled')).strip()
                description = str(row.get(cli.cols['desc_col'], '')).strip()[:50]
                supplier = str(row.get(cli.cols['supplier_col'], '')).strip()[:30]
                
                print(f"{idx+1:3d}. {item_code:<15} [{item_type:<15}] {description:<50} ({supplier})")
        else:
            print(f"No items found matching '{args.search}'")
    
    if args.change:
        item_identifier, new_type = args.change
        if cli.change_item_type(item_identifier, new_type):
            changes_made = True
    
    if args.batch_supplier:
        supplier_name, new_type = args.batch_supplier
        changed_count = cli.batch_change_by_supplier(supplier_name, new_type)
        if changed_count > 0:
            changes_made = True
    
    # If no specific command was given, show interactive menu
    if not any([args.stats, args.list, args.search, args.change, args.batch_supplier]):
        print("\n🔧 INSTRUMENT LABELING CLI")
        print("=" * 40)
        cli.show_stats()
        
        while True:
            print("\nOptions:")
            print("1. List items")
            print("2. Search items")
            print("3. Change item type")
            print("4. Batch change by supplier")
            print("5. Show statistics")
            print("6. Save and exit")
            print("7. Exit without saving")
            
            choice = input("\nEnter choice (1-7): ").strip()
            
            if choice == "1":
                type_filter = input("Filter by type (Instrument/Non-Instrument/Software/Unlabeled/all): ").strip()
                list_type = None if type_filter.lower() == "all" else type_filter
                cli.list_items(item_type=list_type, limit=args.limit)
            
            elif choice == "2":
                search_term = input("Enter search term: ").strip()
                if search_term:
                    results = cli.search_items(search_term)
                    if len(results) > 0:
                        print(f"\n🔍 SEARCH RESULTS for '{search_term}' ({len(results)} found):")
                        print("-" * 80)
                        for idx, (_, row) in enumerate(results.head(args.limit).iterrows()):
                            item_code = str(row.get(cli.cols['code_col'], f'ITEM_{idx+1}')).strip()
                            item_type = str(row.get(cli.cols['type_col'], 'Unlabeled')).strip()
                            description = str(row.get(cli.cols['desc_col'], '')).strip()[:50]
                            supplier = str(row.get(cli.cols['supplier_col'], '')).strip()[:30]
                            
                            print(f"{idx+1:3d}. {item_code:<15} [{item_type:<15}] {description:<50} ({supplier})")
                    else:
                        print(f"No items found matching '{search_term}'")
            
            elif choice == "3":
                item_identifier = input("Enter item code or partial description: ").strip()
                new_type = input("Enter new type (Instrument/Non-Instrument/Software): ").strip()
                if item_identifier and new_type:
                    if cli.change_item_type(item_identifier, new_type):
                        changes_made = True
            
            elif choice == "4":
                supplier_name = input("Enter supplier name (partial match): ").strip()
                new_type = input("Enter new type (Instrument/Non-Instrument/Software): ").strip()
                if supplier_name and new_type:
                    changed_count = cli.batch_change_by_supplier(supplier_name, new_type)
                    if changed_count > 0:
                        changes_made = True
            
            elif choice == "5":
                cli.show_stats()
            
            elif choice == "6":
                if changes_made:
                    if cli.save_changes():
                        print("✅ Changes saved successfully!")
                    else:
                        print("❌ Failed to save changes")
                else:
                    print("No changes to save.")
                break
            
            elif choice == "7":
                if changes_made:
                    response = input("You have unsaved changes. Are you sure you want to exit? (y/N): ")
                    if response.lower() != 'y':
                        continue
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    # Save changes if any were made
    elif changes_made:
        response = input("\nSave changes? (Y/n): ")
        if response.lower() != 'n':
            cli.save_changes()

if __name__ == "__main__":
    main()
