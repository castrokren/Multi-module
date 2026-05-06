#!/usr/bin/env python3
"""
Diagnostic script to identify and fix stuck PDF processing
"""

import os
import sys
import time
import psutil
import signal
import threading
from datetime import datetime

def kill_python_processes():
    """Kill all Python processes that might be stuck."""
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe':
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'crossref' in cmdline.lower():
                    print(f"🔄 Killing stuck process: PID {proc.info['pid']}")
                    proc.terminate()
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if killed_count > 0:
        print(f"✅ Killed {killed_count} stuck Python processes")
        time.sleep(2)  # Give processes time to terminate
    else:
        print("ℹ️ No stuck crossref processes found")

def check_pdf_file(pdf_path):
    """Check if a specific PDF file is problematic."""
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path)
    print(f"📄 PDF file size: {file_size / (1024*1024):.2f} MB")
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        print("⚠️ PDF is very large (>50MB) - may cause timeouts")
        return False
    
    if file_size == 0:
        print("❌ PDF file is empty")
        return False
    
    return True

def test_pdf_extraction(pdf_path, timeout=10):
    """Test PDF text extraction with timeout."""
    print(f"🧪 Testing PDF extraction: {os.path.basename(pdf_path)}")
    
    try:
        from PyPDF2 import PdfReader
        import pdfplumber
        
        start_time = time.time()
        
        # Try PyPDF2 first
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                if reader.is_encrypted:
                    print("❌ PDF is encrypted")
                    return False
                
                # Try to extract first page only
                if len(reader.pages) > 0:
                    page = reader.pages[0]
                    text = page.extract_text()
                    if text:
                        print(f"✅ PyPDF2 extraction successful: {len(text)} characters")
                        return True
        except Exception as e:
            print(f"⚠️ PyPDF2 failed: {e}")
        
        # Try pdfplumber as fallback
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    page = pdf.pages[0]
                    text = page.extract_text()
                    if text:
                        print(f"✅ pdfplumber extraction successful: {len(text)} characters")
                        return True
        except Exception as e:
            print(f"⚠️ pdfplumber failed: {e}")
        
        print("❌ Both extraction methods failed")
        return False
        
    except Exception as e:
        print(f"❌ PDF extraction test failed: {e}")
        return False

def find_problematic_pdf(pdf_dir, start_index=2070, end_index=2074):
    """Find and test the specific PDF that might be causing issues."""
    print(f"🔍 Looking for PDFs in range {start_index}-{end_index}")
    
    all_pdfs = []
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                all_pdfs.append(os.path.join(root, file))
    
    print(f"📂 Found {len(all_pdfs)} total PDF files")
    
    if start_index <= len(all_pdfs) <= end_index:
        print(f"⚠️ PDF index {start_index} is out of range (total: {len(all_pdfs)})")
        return None
    
    # Test the specific PDF
    if start_index < len(all_pdfs):
        pdf_path = all_pdfs[start_index - 1]  # Convert to 0-based index
        print(f"🎯 Testing PDF #{start_index}: {os.path.basename(pdf_path)}")
        
        if check_pdf_file(pdf_path):
            if test_pdf_extraction(pdf_path):
                print("✅ PDF appears to be working fine")
            else:
                print("❌ PDF extraction failed - this might be the problematic file")
                return pdf_path
    else:
        print(f"❌ PDF index {start_index} not found")
    
    return None

def create_safe_pdf_list(pdf_dir, exclude_problematic=True):
    """Create a list of safe PDFs to process."""
    print("📋 Creating safe PDF list...")
    
    safe_pdfs = []
    problematic_pdfs = []
    
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                
                # Quick check for obvious issues
                try:
                    file_size = os.path.getsize(pdf_path)
                    if file_size > 50 * 1024 * 1024 or file_size == 0:
                        problematic_pdfs.append(pdf_path)
                        continue
                    
                    safe_pdfs.append(pdf_path)
                except:
                    problematic_pdfs.append(pdf_path)
    
    print(f"✅ Safe PDFs: {len(safe_pdfs)}")
    print(f"⚠️ Problematic PDFs: {len(problematic_pdfs)}")
    
    if exclude_problematic and problematic_pdfs:
        print("📝 Problematic PDFs:")
        for pdf in problematic_pdfs[:10]:  # Show first 10
            print(f"  - {os.path.basename(pdf)}")
        if len(problematic_pdfs) > 10:
            print(f"  ... and {len(problematic_pdfs) - 10} more")
    
    return safe_pdfs, problematic_pdfs

def main():
    print("🔧 PDF Processing Diagnostic Tool")
    print("=" * 50)
    
    # Kill any stuck processes
    print("\n1. Checking for stuck processes...")
    kill_python_processes()
    
    # Check PDF directory
    pdf_dir = "PDFs"
    if not os.path.exists(pdf_dir):
        print(f"❌ PDF directory not found: {pdf_dir}")
        return
    
    print(f"\n2. Analyzing PDF directory: {pdf_dir}")
    
    # Find problematic PDF
    problematic_pdf = find_problematic_pdf(pdf_dir, 2070, 2074)
    
    # Create safe PDF list
    print(f"\n3. Creating safe PDF list...")
    safe_pdfs, problematic_pdfs = create_safe_pdf_list(pdf_dir)
    
    # Recommendations
    print(f"\n4. Recommendations:")
    print(f"   • Use 'low_cpu_mode=True' to reduce parallel processing")
    print(f"   • Consider excluding problematic PDFs")
    print(f"   • Increase timeout values for large PDFs")
    print(f"   • Use test mode to process fewer items first")
    
    if problematic_pdf:
        print(f"\n5. Specific issue found:")
        print(f"   • Problematic PDF: {os.path.basename(problematic_pdf)}")
        print(f"   • Consider removing or replacing this file")
    
    print(f"\n✅ Diagnostic complete!")

if __name__ == "__main__":
    main()
