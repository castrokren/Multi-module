#!/usr/bin/env python3
"""
Quick fix for stuck PDF processing
"""

import os
import sys
import time
import signal
from datetime import datetime

def find_last_pdfs(pdf_dir, count=10):
    """Find the last few PDFs that might be causing the hang."""
    print(f"🔍 Looking for the last {count} PDFs in {pdf_dir}")
    
    all_pdfs = []
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                all_pdfs.append(os.path.join(root, file))
    
    print(f"📂 Total PDFs found: {len(all_pdfs)}")
    
    # Get the last few PDFs
    last_pdfs = all_pdfs[-count:] if len(all_pdfs) >= count else all_pdfs
    
    print(f"🎯 Last {len(last_pdfs)} PDFs that might be causing the hang:")
    for i, pdf in enumerate(last_pdfs, 1):
        try:
            size = os.path.getsize(pdf) / (1024*1024)
            print(f"  {i}. {os.path.basename(pdf)} ({size:.1f} MB)")
        except:
            print(f"  {i}. {os.path.basename(pdf)} (size unknown)")
    
    return last_pdfs

def test_pdf_safety(pdf_path, timeout=5):
    """Quick test if a PDF is safe to process."""
    try:
        # Check file size
        size = os.path.getsize(pdf_path)
        if size > 50 * 1024 * 1024:  # 50MB
            return False, "Too large"
        if size == 0:
            return False, "Empty file"
        
        # Quick file read test
        with open(pdf_path, 'rb') as f:
            header = f.read(1024)
            if not header.startswith(b'%PDF'):
                return False, "Not a valid PDF"
        
        return True, "OK"
        
    except Exception as e:
        return False, str(e)

def create_safe_pdf_list(pdf_dir):
    """Create a list of safe PDFs by excluding problematic ones."""
    print("🛡️ Creating safe PDF list...")
    
    all_pdfs = []
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                all_pdfs.append(os.path.join(root, file))
    
    safe_pdfs = []
    problematic_pdfs = []
    
    for pdf in all_pdfs:
        is_safe, reason = test_pdf_safety(pdf)
        if is_safe:
            safe_pdfs.append(pdf)
        else:
            problematic_pdfs.append(pdf)
            print(f"⚠️ Excluding: {os.path.basename(pdf)} - {reason}")
    
    print(f"✅ Safe PDFs: {len(safe_pdfs)}")
    print(f"⚠️ Problematic PDFs: {len(problematic_pdfs)}")
    
    return safe_pdfs, problematic_pdfs

def modify_crossref_script():
    """Create a modified version of the crossref script with better error handling."""
    print("🔧 Creating modified crossref script...")
    
    # Read the original script
    with open('crossref_standalone_fast.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add better error handling for PDF processing
    modified_content = content.replace(
        'def extract_pdf_text_standalone(pdf_path, timeout_seconds=30):',
        '''def extract_pdf_text_standalone(pdf_path, timeout_seconds=15):
    """Standalone PDF text extraction function with better error handling."""
    try:
        # Quick safety check
        if not os.path.exists(pdf_path):
            return ""
        
        file_size = os.path.getsize(pdf_path)
        if file_size > 50 * 1024 * 1024 or file_size == 0:
            return ""
        
        # Quick PDF header check
        with open(pdf_path, 'rb') as f:
            header = f.read(1024)
            if not header.startswith(b'%PDF'):
                return ""
        
        # Rest of the function...'''
    )
    
    # Write modified script
    with open('crossref_standalone_fast_safe.py', 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("✅ Created crossref_standalone_fast_safe.py")

def main():
    print("🔧 PDF Processing Fix Tool")
    print("=" * 40)
    
    pdf_dir = "PDFs"
    if not os.path.exists(pdf_dir):
        print(f"❌ PDF directory not found: {pdf_dir}")
        return
    
    # Find the last few PDFs
    last_pdfs = find_last_pdfs(pdf_dir, 10)
    
    # Test each of the last PDFs
    print(f"\n🧪 Testing the last {len(last_pdfs)} PDFs:")
    for i, pdf in enumerate(last_pdfs, 1):
        is_safe, reason = test_pdf_safety(pdf)
        status = "✅ SAFE" if is_safe else "❌ PROBLEMATIC"
        print(f"  {i}. {status}: {os.path.basename(pdf)} - {reason}")
    
    # Create safe PDF list
    print(f"\n📋 Creating comprehensive safe PDF list...")
    safe_pdfs, problematic_pdfs = create_safe_pdf_list(pdf_dir)
    
    # Create modified script
    modify_crossref_script()
    
    print(f"\n💡 Recommendations:")
    print(f"   1. Use the modified script: crossref_standalone_fast_safe.py")
    print(f"   2. Consider removing {len(problematic_pdfs)} problematic PDFs")
    print(f"   3. Use low_cpu_mode=True for more stable processing")
    print(f"   4. Start from a later item if you have previous results")
    
    if problematic_pdfs:
        print(f"\n📝 Problematic PDFs to consider removing:")
        for pdf in problematic_pdfs[:5]:  # Show first 5
            print(f"   - {os.path.basename(pdf)}")
        if len(problematic_pdfs) > 5:
            print(f"   ... and {len(problematic_pdfs) - 5} more")

if __name__ == "__main__":
    main()
