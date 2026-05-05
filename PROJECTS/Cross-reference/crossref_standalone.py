#!/usr/bin/env python3
"""
Standalone Cross-reference Module
Extracted from pdf_crawler_combined_enhanced.py for independent testing and debugging.
"""

import sys
import os
import re
import time
import traceback
from datetime import datetime
from difflib import SequenceMatcher
from PyPDF2 import PdfReader
import pdfplumber
import pandas as pd

# VV LOGGING: Add very verbose logging
def vv_log(message):
    """Very verbose logging function"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[VV] {timestamp} - {message}")
    if sys.stdout is not None:
        sys.stdout.flush()  # Force immediate output

class CrossReferenceEngine:
    """Standalone Cross-reference engine for testing and debugging."""
    
    def __init__(self):
        vv_log("Initializing CrossReferenceEngine...")
        self.results = {}
        vv_log("✅ CrossReferenceEngine initialized")
    
    def run_cross_reference(self, input_file, master_file, pdf_dir, threshold=60):
        """Run cross-reference analysis with very verbose logging."""
        vv_log("=== STARTING CROSS-REFERENCE ANALYSIS ===")
        
        try:
            # Validate inputs
            vv_log("Validating inputs...")
            vv_log(f"Input file: {input_file}")
            vv_log(f"Master file: {master_file}")
            vv_log(f"PDF directory: {pdf_dir}")
            vv_log(f"Threshold: {threshold}%")
            
            if not all([input_file, master_file, pdf_dir]):
                vv_log("❌ Missing required inputs")
                return False
            
            # Validate files exist
            vv_log("Validating file existence...")
            if not os.path.exists(input_file):
                vv_log(f"❌ Input file not found: {input_file}")
                return False
            
            if not os.path.exists(master_file):
                vv_log(f"❌ Master file not found: {master_file}")
                return False
            
            if not os.path.exists(pdf_dir):
                vv_log(f"❌ PDF directory not found: {pdf_dir}")
                return False
            
            vv_log("✅ File validation passed")
            
            # Load Excel files
            vv_log("Loading input Excel file...")
            try:
                input_df = pd.read_excel(input_file, engine='openpyxl')
                vv_log(f"✅ Input file loaded: {len(input_df)} rows")
                vv_log(f"Input columns: {list(input_df.columns)}")
            except Exception as e:
                vv_log(f"❌ Failed to load input file: {e}")
                return False
            
            vv_log("Loading master Excel file...")
            try:
                master_df = pd.read_excel(master_file, engine='openpyxl')
                vv_log(f"✅ Master file loaded: {len(master_df)} rows")
                vv_log(f"Master columns: {list(master_df.columns)}")
            except Exception as e:
                vv_log(f"❌ Failed to load master file: {e}")
                return False
            
            # Check for supplier folders
            vv_log("Checking for supplier folders...")
            try:
                supplier_folders = [d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]
                vv_log(f"Found {len(supplier_folders)} supplier folders")
                
                if supplier_folders:
                    vv_log("Supplier folders:")
                    for folder in supplier_folders:
                        vv_log(f"  - {folder}")
                else:
                    vv_log("⚠️ No supplier folders found")
            except Exception as e:
                vv_log(f"❌ Error listing supplier folders: {e}")
                return False
            
            # Count PDFs
            vv_log("Counting PDF files...")
            pdf_files = []
            try:
                for root, dirs, files in os.walk(pdf_dir):
                    pdfs_in_dir = [f for f in files if f.lower().endswith('.pdf')]
                    if pdfs_in_dir:
                        vv_log(f"  Found {len(pdfs_in_dir)} PDFs in {os.path.basename(root)}")
                        pdf_files.extend(pdfs_in_dir)
                
                vv_log(f"Total PDF files found: {len(pdf_files)}")
            except Exception as e:
                vv_log(f"❌ Error counting PDFs: {e}")
                return False
            
            # Process items
            vv_log("Starting item processing...")
            
            total_items = len(input_df)
            items_with_matches = 0
            total_matches = 0
            
            vv_log(f"Processing {total_items} items...")
            
            for idx, item_row in input_df.iterrows():
                vv_log(f"Processing item {idx+1}/{total_items}")
                
                try:
                    item_code = str(item_row.get('Item Code', ''))
                    description = str(item_row.get('Description', ''))
                    category = str(item_row.get('Category', ''))
                    
                    vv_log(f"  Item: {item_code}")
                    vv_log(f"  Description: {description[:50]}...")
                    vv_log(f"  Category: {category}")
                    
                    # Find matching PDFs
                    vv_log("  Finding matching PDFs...")
                    matches = self.find_matching_pdfs(item_code, description, category, pdf_dir, master_df, threshold)
                    
                    if matches:
                        items_with_matches += 1
                        total_matches += len(matches)
                        vv_log(f"  ✅ Found {len(matches)} matches")
                        
                        # Store results
                        self.results[item_code] = {
                            'description': description,
                            'category': category,
                            'matches': matches
                        }
                    else:
                        vv_log(f"  ❌ No matches found")
                
                except Exception as e:
                    vv_log(f"  ❌ Error processing item {item_code}: {e}")
                    continue
            
            # Final summary
            vv_log("=== CROSS-REFERENCE ANALYSIS COMPLETE ===")
            vv_log(f"Total items processed: {total_items}")
            vv_log(f"Items with matches: {items_with_matches}")
            vv_log(f"Total matches found: {total_matches}")
            
            if total_items > 0:
                avg_matches = total_matches / total_items
                vv_log(f"Average matches per item: {avg_matches:.1f}")
            
            vv_log("✅ Cross-reference analysis completed successfully")
            return True
            
        except Exception as e:
            vv_log(f"❌ Cross-reference analysis failed: {e}")
            traceback.print_exc()
            return False

    def find_matching_pdfs(self, item_code, description, category, pdf_dir, master_df, threshold):
        """Find matching PDFs with very verbose logging."""
        vv_log(f"  === FINDING MATCHES FOR {item_code} ===")
        
        matches = []
        
        try:
            # Extract keywords
            vv_log("    Extracting keywords...")
            search_keywords = self.extract_keywords(description, category)
            vv_log(f"    Keywords: {search_keywords}")
            
            # Get supplier folders
            vv_log("    Getting supplier folders...")
            supplier_folders = [d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]
            vv_log(f"    Found {len(supplier_folders)} supplier folders")
            
            if not supplier_folders:
                vv_log("    ❌ No supplier folders found")
                return matches
            
            # Process each supplier folder
            for supplier_folder in supplier_folders:
                vv_log(f"    Processing supplier: {supplier_folder}")
                
                try:
                    supplier_path = os.path.join(pdf_dir, supplier_folder)
                    
                    # Check if supplier exists in master file
                    vv_log("      Checking master file...")
                    supplier_info = master_df[master_df['Supplier Name'] == supplier_folder]
                    if supplier_info.empty:
                        vv_log(f"      ❌ Supplier '{supplier_folder}' not in master file")
                        continue
                    
                    vv_log("      ✅ Supplier found in master file")
                    
                    # Get PDF files in supplier folder
                    vv_log("      Getting PDF files...")
                    pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                    vv_log(f"      Found {len(pdf_files)} PDF files")
                    
                    if not pdf_files:
                        vv_log("      ❌ No PDF files in supplier folder")
                        continue
                    
                    # Process each PDF
                    for pdf_file in pdf_files:
                        vv_log(f"        Analyzing PDF: {pdf_file}")
                        
                        try:
                            pdf_path = os.path.join(supplier_path, pdf_file)
                            
                            # Extract text from PDF
                            vv_log("          Extracting text...")
                            pdf_text = self.extract_pdf_text(pdf_path)
                            
                            if not pdf_text:
                                vv_log("          ❌ Could not extract text")
                                continue
                            
                            vv_log(f"          ✅ Extracted {len(pdf_text)} characters")
                            
                            # Calculate match score
                            vv_log("          Calculating match score...")
                            score = self.calculate_match_score(search_keywords, pdf_text, description)
                            vv_log(f"          Score: {score:.1f}% (threshold: {threshold}%)")
                            
                            if score >= threshold:
                                vv_log(f"          ✅ MATCH! Score {score:.1f}% >= {threshold}%")
                                matches.append({
                                    'supplier': supplier_folder,
                                    'pdf_file': pdf_file,
                                    'score': score,
                                    'text': pdf_text[:200] + '...' if len(pdf_text) > 200 else pdf_text
                                })
                            else:
                                vv_log(f"          ❌ No match (score {score:.1f}% < {threshold}%)")
                        
                        except Exception as e:
                            vv_log(f"          ❌ Error processing PDF {pdf_file}: {e}")
                            continue
                
                except Exception as e:
                    vv_log(f"    ❌ Error processing supplier {supplier_folder}: {e}")
                    continue
            
            vv_log(f"    === MATCHING COMPLETE FOR {item_code} ===")
            vv_log(f"    Found {len(matches)} matches")
            
        except Exception as e:
            vv_log(f"    ❌ Error in find_matching_pdfs: {e}")
            traceback.print_exc()
        
        return matches

    def extract_keywords(self, description, category):
        """Extract keywords with very verbose logging."""
        vv_log("      Extracting keywords...")
        
        keywords = []
        
        try:
            # Add category keywords
            if category:
                category_keywords = category.lower().split()
                keywords.extend(category_keywords)
                vv_log(f"        Category keywords: {category_keywords}")
            
            # Add description keywords
            if description:
                common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
                words = re.findall(r'\b\w+\b', description.lower())
                description_keywords = [word for word in words if word not in common_words and len(word) > 2]
                keywords.extend(description_keywords)
                vv_log(f"        Description keywords: {description_keywords}")
            
            # Remove duplicates
            unique_keywords = list(set(keywords))
            vv_log(f"        Total unique keywords: {len(unique_keywords)}")
            
            return unique_keywords
        
        except Exception as e:
            vv_log(f"        ❌ Error extracting keywords: {e}")
            return []

    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF with very verbose logging."""
        vv_log(f"          Extracting text from: {os.path.basename(pdf_path)}")
        
        try:
            # Try PyPDF2 first
            vv_log("          Trying PyPDF2...")
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + " "
            
            if text.strip():
                vv_log(f"          ✅ PyPDF2 extracted {len(text)} characters")
                return text.strip()
            
            # Try pdfplumber as fallback
            vv_log("          Trying pdfplumber...")
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + " "
            
            if text.strip():
                vv_log(f"          ✅ pdfplumber extracted {len(text)} characters")
                return text.strip()
            
            vv_log("          ❌ Could not extract text with either method")
            return ""
        
        except Exception as e:
            vv_log(f"          ❌ Error extracting text: {e}")
            return ""

    def calculate_match_score(self, keywords, pdf_text, description):
        """Calculate match score with very verbose logging."""
        vv_log("          Calculating match score...")
        
        try:
            if not keywords or not pdf_text:
                vv_log("          ❌ No keywords or PDF text available")
                return 0.0
            
            pdf_text_lower = pdf_text.lower()
            description_lower = description.lower()
            
            # Keyword matching (70% of score)
            vv_log("          Checking keyword matches...")
            keyword_score = 0.0
            matched_keywords = 0
            matched_keyword_list = []
            
            for keyword in keywords:
                if keyword in pdf_text_lower:
                    matched_keywords += 1
                    matched_keyword_list.append(keyword)
            
            if keywords:
                keyword_score = (matched_keywords / len(keywords)) * 70
                vv_log(f"          Keyword matching: {matched_keywords}/{len(keywords)} keywords found")
                if matched_keyword_list:
                    vv_log(f"          Matched keywords: {matched_keyword_list}")
                vv_log(f"          Keyword score: {keyword_score:.1f}%")
            
            # Text similarity (30% of score)
            vv_log("          Calculating text similarity...")
            similarity_score = 0.0
            if description and pdf_text:
                similarity = SequenceMatcher(None, description_lower, pdf_text_lower[:1000]).ratio()
                similarity_score = similarity * 30
                vv_log(f"          Text similarity: {similarity:.3f} -> {similarity_score:.1f}%")
            
            # Total score
            total_score = keyword_score + similarity_score
            final_score = min(total_score, 100.0)
            
            vv_log(f"          Total score: {keyword_score:.1f}% + {similarity_score:.1f}% = {final_score:.1f}%")
            
            return final_score
        
        except Exception as e:
            vv_log(f"          ❌ Error calculating match score: {e}")
            return 0.0

    def export_results(self, output_file=None):
        """Export cross-reference results to Excel."""
        try:
            if not self.results:
                vv_log("[WARNING] No cross-reference results to export.")
                return False
            
            # Create export data
            export_data = []
            
            for item_code, result in self.results.items():
                if result['matches']:
                    # Sort matches by score
                    sorted_matches = sorted(result['matches'], key=lambda x: x['score'], reverse=True)
                    
                    for match in sorted_matches:
                        export_data.append({
                            'Item Code': item_code,
                            'Description': result['description'],
                            'Category': result['category'],
                            'Supplier': match['supplier'],
                            'PDF File': match['pdf_file'],
                            'Match Score (%)': round(match['score'], 1),
                            'PDF Text Preview': match['text'][:200] + '...' if len(match['text']) > 200 else match['text']
                        })
                else:
                    # No matches
                    export_data.append({
                        'Item Code': item_code,
                        'Description': result['description'],
                        'Category': result['category'],
                        'Supplier': 'No matches',
                        'PDF File': '',
                        'Match Score (%)': 0.0,
                        'PDF Text Preview': ''
                    })
            
            # Create DataFrame and export
            export_df = pd.DataFrame(export_data)
            
            # Generate filename if not provided
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"crossref_results_{timestamp}.xlsx"
            
            # Save to Excel
            export_df.to_excel(output_file, index=False, engine='openpyxl')
            
            vv_log(f"[SUCCESS] Cross-reference results exported to: {output_file}")
            return True
            
        except Exception as e:
            vv_log(f"[ERROR] Failed to export results: {str(e)}")
            return False

def main():
    """Main function for standalone testing."""
    vv_log("=== STANDALONE CROSS-REFERENCE TEST ===")
    
    # Test parameters - you can modify these
    input_file = "input.xlsx"  # Change to your input file
    master_file = "master.xlsx"  # Change to your master file
    pdf_dir = "Test files/PDFs"  # Change to your PDF directory
    threshold = 60
    
    vv_log("Test parameters:")
    vv_log(f"  Input file: {input_file}")
    vv_log(f"  Master file: {master_file}")
    vv_log(f"  PDF directory: {pdf_dir}")
    vv_log(f"  Threshold: {threshold}%")
    
    # Check if files exist
    if not os.path.exists(input_file):
        vv_log(f"❌ Input file not found: {input_file}")
        vv_log("Please create or specify the correct input file path")
        return
    
    if not os.path.exists(master_file):
        vv_log(f"❌ Master file not found: {master_file}")
        vv_log("Please create or specify the correct master file path")
        return
    
    if not os.path.exists(pdf_dir):
        vv_log(f"❌ PDF directory not found: {pdf_dir}")
        vv_log("Please create or specify the correct PDF directory path")
        return
    
    # Create engine and run test
    engine = CrossReferenceEngine()
    success = engine.run_cross_reference(input_file, master_file, pdf_dir, threshold)
    
    if success:
        vv_log("✅ Cross-reference test completed successfully")
        
        # Export results
        export_success = engine.export_results()
        if export_success:
            vv_log("✅ Results exported successfully")
        else:
            vv_log("❌ Failed to export results")
    else:
        vv_log("❌ Cross-reference test failed")

if __name__ == "__main__":
    main() 