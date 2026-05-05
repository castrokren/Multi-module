#!/usr/bin/env python3
"""
Instrument Labeling Manager
A comprehensive tool for managing instrument classifications in the scraper system.

Features:
- Label new items as instruments
- Change instruments to non-instruments and vice versa
- Search and filter items
- Batch operations
- Safe backup functionality
- Real-time data validation
"""

import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
import shutil
import threading
import time

class InstrumentLabelingManager:
    def __init__(self, master):
        self.master = master
        self.master.title("Instrument Labeling Manager")
        self.master.geometry("1200x800")
        
        # Data storage
        self.df = None
        self.original_df = None
        self.current_file = None
        self.changes_made = False
        
        # Create backup directory
        self.backup_dir = "#backup_logs"
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        self.setup_ui()
        self.load_default_file()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="File Management", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="Excel File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly")
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(file_frame, text="Reload", command=self.reload_file).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(file_frame, text="Save", command=self.save_file).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(file_frame, text="Save As", command=self.save_as_file).grid(row=0, column=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status & Statistics", padding="5")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="No file loaded")
        self.status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        # Search and filter frame
        search_frame = ttk.LabelFrame(main_frame, text="Search & Filter", padding="5")
        search_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        search_frame.columnconfigure(1, weight=1)
        search_frame.rowconfigure(4, weight=1)
        
        # Search controls
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Filter by type
        ttk.Label(search_frame, text="Filter by Type:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(search_frame, textvariable=self.filter_var, 
                                   values=["All", "Instrument", "Non-Instrument", "Software", "Unlabeled"])
        filter_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        filter_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Quick actions
        ttk.Label(search_frame, text="Quick Actions:").grid(row=2, column=0, sticky=tk.W, pady=(5, 5))
        action_frame = ttk.Frame(search_frame)
        action_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(5, 5))
        
        ttk.Button(action_frame, text="Mark as Instrument", 
                  command=lambda: self.change_selected_type("Instrument")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Mark as Non-Instrument", 
                  command=lambda: self.change_selected_type("Non-Instrument")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Mark as Software", 
                  command=lambda: self.change_selected_type("Software")).pack(side=tk.LEFT)
        
        # Batch operations
        ttk.Label(search_frame, text="Batch Operations:").grid(row=3, column=0, sticky=tk.W, pady=(5, 5))
        batch_frame = ttk.Frame(search_frame)
        batch_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(5, 5))
        
        ttk.Button(batch_frame, text="Select All Visible", 
                  command=self.select_all_visible).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(batch_frame, text="Clear Selection", 
                  command=self.clear_selection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(batch_frame, text="Export Selection", 
                  command=self.export_selection).pack(side=tk.LEFT)
        
        # Items list
        ttk.Label(search_frame, text="Items:").grid(row=4, column=0, sticky=(tk.W, tk.N), pady=(5, 0))
        
        # Treeview for items
        tree_frame = ttk.Frame(search_frame)
        tree_frame.grid(row=4, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Create treeview with scrollbars
        self.tree = ttk.Treeview(tree_frame, columns=("Type", "Description", "Supplier", "Category"), 
                                show="tree headings", selectmode="extended")
        
        # Configure columns
        self.tree.heading("#0", text="Item Code")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Supplier", text="Supplier")
        self.tree.heading("Category", text="Category")
        
        self.tree.column("#0", width=120, minwidth=80)
        self.tree.column("Type", width=100, minwidth=80)
        self.tree.column("Description", width=300, minwidth=200)
        self.tree.column("Supplier", width=150, minwidth=100)
        self.tree.column("Category", width=120, minwidth=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind double-click to edit
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        # Details panel
        details_frame = ttk.LabelFrame(main_frame, text="Item Details & Actions", padding="5")
        details_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_frame.columnconfigure(1, weight=1)
        details_frame.rowconfigure(6, weight=1)
        
        # Item details
        ttk.Label(details_frame, text="Item Code:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.detail_code_var = tk.StringVar()
        ttk.Label(details_frame, textvariable=self.detail_code_var, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(details_frame, text="Current Type:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.detail_type_var = tk.StringVar()
        self.detail_type_label = ttk.Label(details_frame, textvariable=self.detail_type_var, font=("Arial", 10, "bold"))
        self.detail_type_label.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(details_frame, text="Description:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.detail_desc_var = tk.StringVar()
        desc_label = ttk.Label(details_frame, textvariable=self.detail_desc_var, wraplength=300)
        desc_label.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(details_frame, text="Supplier:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.detail_supplier_var = tk.StringVar()
        ttk.Label(details_frame, textvariable=self.detail_supplier_var).grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        # Change type controls
        ttk.Label(details_frame, text="Change Type To:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        self.new_type_var = tk.StringVar(value="Instrument")
        type_combo = ttk.Combobox(details_frame, textvariable=self.new_type_var, 
                                 values=["Instrument", "Non-Instrument", "Software"])
        type_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(10, 5))
        
        ttk.Button(details_frame, text="Apply Change", 
                  command=self.apply_type_change).grid(row=5, column=0, columnspan=2, pady=(5, 10))
        
        # Log area
        ttk.Label(details_frame, text="Activity Log:").grid(row=6, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        log_frame = ttk.Frame(details_frame)
        log_frame.grid(row=6, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Clear log button
        ttk.Button(details_frame, text="Clear Log", 
                  command=self.clear_log).grid(row=7, column=1, sticky=tk.E, pady=(5, 0))
    
    def log_message(self, message, level="INFO"):
        """Add a message to the activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Color coding
        if level == "ERROR":
            self.log_text.tag_add("error", f"end-{len(log_entry)}c", "end-1c")
            self.log_text.tag_config("error", foreground="red")
        elif level == "SUCCESS":
            self.log_text.tag_add("success", f"end-{len(log_entry)}c", "end-1c")
            self.log_text.tag_config("success", foreground="green")
        elif level == "WARNING":
            self.log_text.tag_add("warning", f"end-{len(log_entry)}c", "end-1c")
            self.log_text.tag_config("warning", foreground="orange")
    
    def clear_log(self):
        """Clear the activity log."""
        self.log_text.delete(1.0, tk.END)
    
    def load_default_file(self):
        """Load the default input file if it exists."""
        default_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
        if os.path.exists(default_file):
            self.load_file(default_file)
    
    def browse_file(self):
        """Browse for an Excel file to load."""
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load an Excel file."""
        try:
            self.log_message(f"Loading file: {file_path}")
            
            # Read the Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = self.find_required_columns(df)
            if not all(required_columns.values()):
                missing = [k for k, v in required_columns.items() if not v]
                self.log_message(f"Missing required columns: {missing}", "ERROR")
                messagebox.showerror("Error", f"Missing required columns: {missing}")
                return
            
            # Store data
            self.df = df.copy()
            self.original_df = df.copy()
            self.current_file = file_path
            self.changes_made = False
            
            # Update UI
            self.file_path_var.set(file_path)
            self.update_status()
            self.refresh_tree()
            
            self.log_message(f"Successfully loaded {len(df)} items", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"Error loading file: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def find_required_columns(self, df):
        """Find required columns in the dataframe."""
        columns = df.columns.tolist()
        
        # Find TYPE column
        type_col = None
        for col in ['TYPE', 'Type', 'Item Type', 'Product Type']:
            if col in columns:
                type_col = col
                break
        
        # Find Item Code column
        code_col = None
        for col in ['Item Code', 'ItemCode', 'Code', 'ID', 'Item ID', 'Item_ID']:
            if col in columns:
                code_col = col
                break
        
        # Find Description column
        desc_col = None
        for col in ['Item Description', 'Description', 'ItemDescription', 'Name', 'Title', 'Product Name']:
            if col in columns:
                desc_col = col
                break
        
        # Find Supplier column
        supplier_col = None
        for col in ['Supplier Name', 'Supplier', 'Vendor', 'Company']:
            if col in columns:
                supplier_col = col
                break
        
        return {
            'type_col': type_col,
            'code_col': code_col,
            'desc_col': desc_col,
            'supplier_col': supplier_col
        }
    
    def update_status(self):
        """Update the status display."""
        if self.df is None:
            self.status_label.config(text="No file loaded")
            return
        
        # Get column mappings
        cols = self.find_required_columns(self.df)
        type_col = cols['type_col']
        
        total_items = len(self.df)
        
        if type_col:
            # Count by type
            type_counts = self.df[type_col].fillna('Unlabeled').value_counts()
            instruments = type_counts.get('Instrument', 0)
            non_instruments = type_counts.get('Non-Instrument', 0)
            software = type_counts.get('Software', 0)
            unlabeled = type_counts.get('Unlabeled', 0)
            
            status_text = (f"Total: {total_items} | Instruments: {instruments} | "
                          f"Non-Instruments: {non_instruments} | Software: {software} | "
                          f"Unlabeled: {unlabeled}")
        else:
            status_text = f"Total: {total_items} items (No TYPE column found)"
        
        if self.changes_made:
            status_text += " | ⚠️ UNSAVED CHANGES"
        
        self.status_label.config(text=status_text)
    
    def refresh_tree(self):
        """Refresh the items tree view."""
        if self.df is None:
            return
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get column mappings
        cols = self.find_required_columns(self.df)
        
        # Apply filters
        filtered_df = self.apply_filters()
        
        # Add items to tree
        for idx, row in filtered_df.iterrows():
            item_code = str(row.get(cols['code_col'], f'ITEM_{idx+1}')).strip()
            item_type = str(row.get(cols['type_col'], 'Unlabeled')).strip()
            description = str(row.get(cols['desc_col'], '')).strip()[:100]  # Truncate long descriptions
            supplier = str(row.get(cols['supplier_col'], '')).strip()
            category = str(row.get('Category', '')).strip()
            
            # Color coding based on type
            tags = []
            if item_type.lower() == 'instrument':
                tags.append('instrument')
            elif item_type.lower() == 'non-instrument':
                tags.append('non_instrument')
            elif item_type.lower() == 'software':
                tags.append('software')
            else:
                tags.append('unlabeled')
            
            self.tree.insert("", "end", text=item_code, 
                           values=(item_type, description, supplier, category),
                           tags=tags)
        
        # Configure tag colors
        self.tree.tag_configure('instrument', background='lightgreen')
        self.tree.tag_configure('non_instrument', background='lightcoral')
        self.tree.tag_configure('software', background='lightblue')
        self.tree.tag_configure('unlabeled', background='lightyellow')
    
    def apply_filters(self):
        """Apply search and filter criteria to the dataframe."""
        if self.df is None:
            return pd.DataFrame()
        
        filtered_df = self.df.copy()
        cols = self.find_required_columns(self.df)
        
        # Apply type filter
        filter_type = self.filter_var.get()
        if filter_type != "All" and cols['type_col']:
            if filter_type == "Unlabeled":
                filtered_df = filtered_df[filtered_df[cols['type_col']].isna() | 
                                        (filtered_df[cols['type_col']].astype(str).str.strip() == '')]
            else:
                filtered_df = filtered_df[filtered_df[cols['type_col']].astype(str).str.lower().str.strip() == filter_type.lower()]
        
        # Apply search filter
        search_term = self.search_var.get().lower().strip()
        if search_term:
            search_mask = pd.Series([False] * len(filtered_df))
            
            # Search in multiple columns
            search_columns = [cols['code_col'], cols['desc_col'], cols['supplier_col']]
            for col in search_columns:
                if col and col in filtered_df.columns:
                    search_mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)
            
            filtered_df = filtered_df[search_mask]
        
        return filtered_df
    
    def on_search_change(self, *args):
        """Handle search text change."""
        self.refresh_tree()
    
    def on_filter_change(self, event=None):
        """Handle filter change."""
        self.refresh_tree()
    
    def on_item_double_click(self, event):
        """Handle double-click on tree item."""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            item_code = self.tree.item(item, "text")
            self.show_item_details(item_code)
    
    def show_item_details(self, item_code):
        """Show details for the selected item."""
        if self.df is None:
            return
        
        cols = self.find_required_columns(self.df)
        
        # Find the item in the dataframe
        if cols['code_col']:
            item_row = self.df[self.df[cols['code_col']].astype(str).str.strip() == item_code]
        else:
            # If no code column, try to match by index
            try:
                idx = int(item_code.split('_')[1]) - 1
                item_row = self.df.iloc[[idx]]
            except:
                return
        
        if item_row.empty:
            return
        
        row = item_row.iloc[0]
        
        # Update detail fields
        self.detail_code_var.set(item_code)
        
        current_type = str(row.get(cols['type_col'], 'Unlabeled')).strip()
        self.detail_type_var.set(current_type)
        
        # Color code the type
        if current_type.lower() == 'instrument':
            self.detail_type_label.config(foreground='green')
        elif current_type.lower() == 'non-instrument':
            self.detail_type_label.config(foreground='red')
        elif current_type.lower() == 'software':
            self.detail_type_label.config(foreground='blue')
        else:
            self.detail_type_label.config(foreground='orange')
        
        description = str(row.get(cols['desc_col'], '')).strip()
        self.detail_desc_var.set(description)
        
        supplier = str(row.get(cols['supplier_col'], '')).strip()
        self.detail_supplier_var.set(supplier)
        
        # Set the new type combo to current type
        if current_type in ["Instrument", "Non-Instrument", "Software"]:
            self.new_type_var.set(current_type)
    
    def apply_type_change(self):
        """Apply type change to the selected item."""
        item_code = self.detail_code_var.get()
        new_type = self.new_type_var.get()
        
        if not item_code or not new_type:
            return
        
        self.change_item_type(item_code, new_type)
    
    def change_item_type(self, item_code, new_type):
        """Change the type of a specific item."""
        if self.df is None:
            return
        
        cols = self.find_required_columns(self.df)
        if not cols['type_col']:
            self.log_message("No TYPE column found in data", "ERROR")
            return
        
        # Find the item
        if cols['code_col']:
            mask = self.df[cols['code_col']].astype(str).str.strip() == item_code
        else:
            try:
                idx = int(item_code.split('_')[1]) - 1
                mask = self.df.index == idx
            except:
                self.log_message(f"Could not find item: {item_code}", "ERROR")
                return
        
        if not mask.any():
            self.log_message(f"Item not found: {item_code}", "ERROR")
            return
        
        # Get current type
        current_type = str(self.df.loc[mask, cols['type_col']].iloc[0]).strip()
        
        if current_type == new_type:
            self.log_message(f"Item {item_code} is already marked as {new_type}", "WARNING")
            return
        
        # Make the change
        self.df.loc[mask, cols['type_col']] = new_type
        self.changes_made = True
        
        # Log the change
        self.log_message(f"Changed {item_code}: {current_type} → {new_type}", "SUCCESS")
        
        # Update UI
        self.update_status()
        self.refresh_tree()
        self.show_item_details(item_code)  # Refresh details
    
    def change_selected_type(self, new_type):
        """Change type for all selected items."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select items to change.")
            return
        
        # Confirm batch change
        if len(selection) > 1:
            result = messagebox.askyesno("Confirm Batch Change", 
                                       f"Change {len(selection)} items to {new_type}?")
            if not result:
                return
        
        changed_count = 0
        for item in selection:
            item_code = self.tree.item(item, "text")
            try:
                self.change_item_type(item_code, new_type)
                changed_count += 1
            except Exception as e:
                self.log_message(f"Error changing {item_code}: {str(e)}", "ERROR")
        
        self.log_message(f"Batch operation completed: {changed_count} items changed to {new_type}", "SUCCESS")
    
    def select_all_visible(self):
        """Select all visible items in the tree."""
        items = self.tree.get_children()
        self.tree.selection_set(items)
        self.log_message(f"Selected {len(items)} visible items")
    
    def clear_selection(self):
        """Clear the current selection."""
        self.tree.selection_remove(self.tree.selection())
        self.log_message("Selection cleared")
    
    def export_selection(self):
        """Export selected items to a new Excel file."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select items to export.")
            return
        
        # Get selected item codes
        selected_codes = [self.tree.item(item, "text") for item in selection]
        
        # Filter dataframe
        cols = self.find_required_columns(self.df)
        if cols['code_col']:
            export_df = self.df[self.df[cols['code_col']].astype(str).str.strip().isin(selected_codes)]
        else:
            # Handle items without code column
            indices = []
            for code in selected_codes:
                try:
                    idx = int(code.split('_')[1]) - 1
                    indices.append(idx)
                except:
                    continue
            export_df = self.df.iloc[indices]
        
        # Save to file
        file_path = filedialog.asksaveasfilename(
            title="Export Selected Items",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                export_df.to_excel(file_path, index=False)
                self.log_message(f"Exported {len(export_df)} items to {file_path}", "SUCCESS")
                messagebox.showinfo("Success", f"Exported {len(export_df)} items successfully!")
            except Exception as e:
                self.log_message(f"Export failed: {str(e)}", "ERROR")
                messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def create_backup(self):
        """Create a backup of the current file."""
        if not self.current_file:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(self.current_file)
            name, ext = os.path.splitext(filename)
            backup_filename = f"{name}_backup_{timestamp}{ext}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            shutil.copy2(self.current_file, backup_path)
            self.log_message(f"Backup created: {backup_path}", "SUCCESS")
            return backup_path
            
        except Exception as e:
            self.log_message(f"Backup failed: {str(e)}", "ERROR")
            return None
    
    def save_file(self):
        """Save changes to the current file."""
        if not self.current_file or self.df is None:
            self.save_as_file()
            return
        
        if not self.changes_made:
            messagebox.showinfo("Info", "No changes to save.")
            return
        
        # Create backup first
        backup_path = self.create_backup()
        if not backup_path:
            result = messagebox.askyesno("Warning", 
                                       "Could not create backup. Continue saving anyway?")
            if not result:
                return
        
        try:
            self.df.to_excel(self.current_file, index=False)
            self.changes_made = False
            self.original_df = self.df.copy()
            self.update_status()
            self.log_message(f"File saved successfully: {self.current_file}", "SUCCESS")
            messagebox.showinfo("Success", "File saved successfully!")
            
        except Exception as e:
            self.log_message(f"Save failed: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
    
    def save_as_file(self):
        """Save the file with a new name."""
        if self.df is None:
            messagebox.showwarning("Warning", "No data to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.df.to_excel(file_path, index=False)
                self.current_file = file_path
                self.changes_made = False
                self.original_df = self.df.copy()
                self.file_path_var.set(file_path)
                self.update_status()
                self.log_message(f"File saved as: {file_path}", "SUCCESS")
                messagebox.showinfo("Success", "File saved successfully!")
                
            except Exception as e:
                self.log_message(f"Save failed: {str(e)}", "ERROR")
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
    
    def reload_file(self):
        """Reload the current file, discarding changes."""
        if not self.current_file:
            return
        
        if self.changes_made:
            result = messagebox.askyesno("Confirm Reload", 
                                       "This will discard all unsaved changes. Continue?")
            if not result:
                return
        
        self.load_file(self.current_file)

def main():
    """Main function to run the application."""
    root = tk.Tk()
    app = InstrumentLabelingManager(root)
    
    # Handle window closing
    def on_closing():
        if app.changes_made:
            result = messagebox.askyesnocancel("Unsaved Changes", 
                                             "You have unsaved changes. Save before closing?")
            if result is True:  # Yes - save
                app.save_file()
                root.destroy()
            elif result is False:  # No - don't save
                root.destroy()
            # Cancel - do nothing
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the application
    root.mainloop()

if __name__ == "__main__":
    main()
