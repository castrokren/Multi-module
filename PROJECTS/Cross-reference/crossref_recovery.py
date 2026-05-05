#!/usr/bin/env python3
"""
Recovery version of Cross-reference Module with better error handling
"""

import sys
import os
import re
import time
import traceback
import signal
import threading
import platform
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
from PyPDF2 import PdfReader
import pdfplumber
import pandas as pd

# Global stop flag for process termination
GLOBAL_STOP_FLAG = False

# Recovery settings
RECOVERY_MODE = True
START_FROM_ITEM = 2070  # Start from where it got stuck
MAX_RETRIES = 3
PDF_TIMEOUT = 15  # Reduced timeout
LOW_CPU_MODE = True  # Use single worker

def process_single_pdf_safe(args):
    """Safe version of PDF processing with better error handling."""
    pdf_path, search_keywords, description, threshold = args
    
    # Check global stop flag
    if GLOBAL_STOP_FLAG:
        return None
    
    try:
        # Quick file check
        if not os.path.exists(pdf_path):
            return None
        
        file_size = os.path.getsize(pdf_path)
        if file_size > 50 * 1024 * 1024 or file_size == 0:  # Skip large or empty files
            return None
        
        # Extract text from PDF with timeout
        pdf_text = extract_pdf_text_safe(pdf_path, timeout_seconds=PDF_TIMEOUT)
        
        if not pdf_text:
            return None
        
        # Check global stop flag again
        if GLOBAL_STOP_FLAG:
            return None
        
        # Calculate match score
        score = calculate_match_score_safe(search_keywords, pdf_text, description, threshold)
        
        if score >= threshold:
            return {
                'pdf_path': pdf_path,
                'score': score,
                'supplier': os.path.basename(os.path.dirname(pdf_path))
            }
        
        return None
        
    except Exception as e:
        print(f"        ⚠️ Error processing {os.path.basename(pdf_path)}: {str(e)[:100]}")
        return None

def extract_pdf_text_safe(pdf_path, timeout_seconds=15):
    """Safe PDF text extraction with reduced timeout."""
    try:
        # Check if file exists and is readable
        if not os.path.exists(pdf_path):
            return ""
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > 50 * 1024 * 1024 or file_size == 0:
            return ""
        
        # Suppress warnings
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        import logging
        logging.getLogger('pdfplumber').setLevel(logging.ERROR)
        
        # Try PyPDF2 first (faster)
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                
                if reader.is_encrypted:
                    return ""
                
                max_pages = 10  # Reduced from 20
                total_pages = len(reader.pages)
                pages_to_process = min(total_pages, max_pages)
                
                text = ""
                for page_num in range(pages_to_process):
                    try:
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + " "
                            if len(text) > 10000:  # Reduced from 20000
                                break
                    except:
                        continue
                
                if text.strip():
                    return text.strip()
        except:
            pass
        
        # Try pdfplumber as fallback (only first few pages)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                pages_to_process = min(len(pdf.pages), 5)  # Reduced from 20
                
                for page_num in range(pages_to_process):
                    try:
                        page = pdf.pages[page_num]
                        page_text = page.extract_text()
                        
                        if page_text:
                            text += page_text + " "
                            if len(text) > 10000:  # Reduced from 20000
                                break
                    except:
                        continue
                
                if text.strip():
                    return text.strip()
        except:
            pass
        
        return ""
        
    except:
        return ""

def calculate_match_score_safe(keywords, pdf_text, description, threshold=30):
    """Safe match score calculation."""
    try:
        if not keywords or not pdf_text:
            return 0.0
        
        pdf_text_lower = pdf_text.lower()
        description_lower = description.lower()
        
        # Calculate keyword matches
        keyword_matches = 0
        total_keywords = len(keywords)
        
        for keyword in keywords:
            if keyword.lower() in pdf_text_lower:
                keyword_matches += 1
        
        if total_keywords == 0:
            return 0.0
        
        keyword_score = (keyword_matches / total_keywords) * 50
        
        # Calculate description similarity
        similarity_score = SequenceMatcher(None, description_lower, pdf_text_lower).ratio() * 50
        
        total_score = keyword_score + similarity_score
        
        return min(total_score, 100.0)
        
    except:
        return 0.0

class CrossReferenceRecovery:
    def __init__(self):
        self.results = []
        self.stop_analysis = False
        self.parent_gui_processes = []
    
    def run_cross_reference_recovery(self, input_file, master_file, pdf_dir, threshold=60, start_from_item=1):
        """Recovery version with better error handling."""
        print("=== STARTING CROSS-REFERENCE RECOVERY ANALYSIS ===")
        print(f"🔄 Recovery mode: Starting from item {start_from_item}")
        print(f"🐌 Low CPU mode: Using single worker for stability")
        
        try:
            # Validate inputs
            if not all([input_file, master_file, pdf_dir]):
                print("❌ Missing required inputs")
                return False
            
            # Load input file
            try:
                print(f"📂 Loading input file: {input_file}")
                input_df = pd.read_excel(input_file)
                print(f"✅ Input file loaded: {len(input_df)} rows")
            except Exception as e:
                print(f"❌ Failed to load input file: {e}")
                return False
            
            # Load master file
            try:
                print(f"📂 Loading master file: {master_file}")
                master_df = pd.read_excel(master_file)
                print(f"✅ Master file loaded: {len(master_df)} rows")
            except Exception as e:
                print(f"❌ Failed to load master file: {e}")
                return False
            
            # Process items starting from specified item
            total_items = len(input_df)
            items_with_matches = 0
            total_matches = 0
            processed_items = 0
            
            print(f"Processing {total_items} items (starting from item {start_from_item})...")
            
            for idx, row in input_df.iterrows():
                # Skip items before start_from_item
                if idx + 1 < start_from_item:
                    continue
                
                # Check if analysis should be stopped
                if self.stop_analysis:
                    print("🛑 Analysis stopped by user")
                    return False
                    
                processed_items += 1
                print(f"\n--- Processing item {idx+1}/{total_items} (Recovery: {processed_items}) ---")
                
                try:
                    # Extract item information
                    item_code = str(row.get('TYPE', f'ITEM_{idx+1}')).strip()
                    description = str(row.get('Item Description', '')).strip()
                    category = str(row.get('Category', '')).strip()
                    
                    if not description:
                        print(f"  ❌ Skipping - missing description")
                        continue
                    
                    print(f"  🔍 Processing: {item_code}")
                    print(f"  Description: {description[:100]}...")
                    
                    # Find matches using safe method
                    matches = self.find_matching_pdfs_safe(item_code, description, category, pdf_dir, master_df, threshold, input_df)
                    
                    if matches:
                        items_with_matches += 1
                        total_matches += len(matches)
                        print(f"  ✅ Found {len(matches)} matches")
                        
                        # Add to results
                        for match in matches:
                            self.results.append({
                                'Item Code': item_code,
                                'Description': description,
                                'Category': category,
                                'Matched PDF': match['pdf_path'],
                                'Match Score': match['score'],
                                'Supplier': match['supplier']
                            })
                    else:
                        print(f"  ❌ No matches found")
                        
                except Exception as e:
                    print(f"  ❌ Error processing item {item_code}: {e}")
                    continue
            
            # Summary
            print("\n=== RECOVERY ANALYSIS COMPLETE ===")
            print(f"Items processed: {processed_items}")
            print(f"Items with matches: {items_with_matches}")
            print(f"Total matches found: {total_matches}")
            
            return True
            
        except Exception as e:
            print(f"❌ Recovery analysis failed: {e}")
            return False
    
    def find_matching_pdfs_safe(self, item_code, description, category, pdf_dir, master_df, threshold, input_df=None):
        """Safe PDF matching with single worker."""
        matches = []
        
        try:
            # Extract keywords
            search_keywords = self.extract_keywords_safe(description, category)
            
            if not search_keywords:
                print("    ❌ No keywords extracted")
                return matches
            
            # Find supplier directory
            current_supplier = self.find_supplier_safe(item_code, input_df)
            
            if not current_supplier:
                print(f"    ❌ No supplier found for item {item_code}")
                return matches
            
            print(f"    🎯 Looking for supplier: '{current_supplier}'")
            
            # Get PDF files
            pdf_files = self.get_pdf_files_safe(pdf_dir, current_supplier)
            
            if not pdf_files:
                print(f"    ❌ No PDF files found")
                return matches
            
            print(f"    📂 Found {len(pdf_files)} PDF files")
            
            # Process PDFs sequentially (safer)
            processed_count = 0
            for pdf_path, supplier_dir in pdf_files:
                processed_count += 1
                
                if processed_count % 10 == 0:
                    print(f"    📊 Progress: {processed_count}/{len(pdf_files)} PDFs processed")
                
                try:
                    result = process_single_pdf_safe((pdf_path, search_keywords, description, threshold))
                    if result:
                        matches.append(result)
                        print(f"    ✅ MATCH! PDF {processed_count}/{len(pdf_files)}: {os.path.basename(result['pdf_path'])} (Score: {result['score']:.1f}%)")
                except Exception as e:
                    print(f"    ⚠️ Error processing PDF: {str(e)[:50]}")
                    continue
            
            print(f"    📊 Processing completed: {len(matches)} matches found")
            return matches
            
        except Exception as e:
            print(f"    ❌ Error in find_matching_pdfs_safe: {e}")
            return matches
    
    def extract_keywords_safe(self, description, category):
        """Safe keyword extraction."""
        try:
            keywords = []
            
            # Extract words from description
            if description:
                words = re.findall(r'\b\w+\b', description.lower())
                # Filter out common words and short words
                stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
                keywords.extend([word for word in words if len(word) > 2 and word not in stop_words])
            
            # Extract words from category
            if category:
                words = re.findall(r'\b\w+\b', category.lower())
                keywords.extend([word for word in words if len(word) > 2 and word not in stop_words])
            
            # Remove duplicates and limit
            keywords = list(set(keywords))[:20]  # Limit to 20 keywords
            
            return keywords
            
        except:
            return []
    
    def find_supplier_safe(self, item_code, input_df):
        """Safe supplier finding."""
        try:
            if input_df is None:
                return None
            
            # Find supplier column
            supplier_col = None
            for col_name in ['Supplier Name', 'Supplier', 'Vendor', 'Company']:
                if col_name in input_df.columns:
                    supplier_col = col_name
                    break
            
            if not supplier_col:
                return None
            
            # Find supplier by item code
            if item_code.startswith('ITEM_'):
                row_idx = int(item_code.split('_')[1]) - 1
                if 0 <= row_idx < len(input_df):
                    return str(input_df.iloc[row_idx][supplier_col]).strip()
            
            return None
            
        except:
            return None
    
    def get_pdf_files_safe(self, pdf_dir, supplier_name):
        """Safe PDF file collection."""
        try:
            pdf_files = []
            
            # Try to find supplier directory
            available_suppliers = [d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]
            
            matching_supplier = None
            for supplier in available_suppliers:
                if supplier_name.lower() in supplier.lower() or supplier.lower() in supplier_name.lower():
                    matching_supplier = supplier
                    break
            
            if matching_supplier:
                supplier_path = os.path.join(pdf_dir, matching_supplier)
                files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                pdf_files = [(os.path.join(supplier_path, f), matching_supplier) for f in files]
            else:
                # Fallback: search all directories
                for supplier in available_suppliers:
                    supplier_path = os.path.join(pdf_dir, supplier)
                    files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                    pdf_files.extend([(os.path.join(supplier_path, f), supplier) for f in files])
            
            return pdf_files
            
        except:
            return []

def main():
    """Main function for recovery mode."""
    print("🔄 Cross-Reference Recovery Tool")
    print("=" * 50)
    
    # Configuration
    input_file = "D:/SOM_in_labeled"
    master_file = "D:/Masterlist"
    pdf_dir = "D:/ScrapedPDFs"
    threshold = 60
    start_from_item = START_FROM_ITEM
    
    # Check if files exist
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return
    
    if not os.path.exists(master_file):
        print(f"❌ Master file not found: {master_file}")
        return
    
    if not os.path.exists(pdf_dir):
        print(f"❌ PDF directory not found: {pdf_dir}")
        return
    
    # Create recovery engine
    engine = CrossReferenceRecovery()
    
    # Run recovery analysis
    success = engine.run_cross_reference_recovery(input_file, master_file, pdf_dir, threshold, start_from_item)
    
    if success and engine.results:
        # Export results
        output_file = f"crossref_recovery_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df = pd.DataFrame(engine.results)
        df.to_excel(output_file, index=False)
        print(f"✅ Results exported to: {output_file}")
    else:
        print("❌ No results to export")

if __name__ == "__main__":
    main()
