#!/usr/bin/env python3
"""
Standalone Cross-reference Module
"""

import sys
import os
from pathlib import Path

# Ensure the module's own directory is in sys.path for local imports
# This is needed when the module is loaded via importlib.util.spec_from_file_location
# (which happens in pipeline.py) so that "from crossref_utils import ..." works
_MODULE_DIR = Path(__file__).parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

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

from crossref_utils import normalize_filename, deduplicate_matches

# Global stop flag for process termination
GLOBAL_STOP_FLAG = False

# Enhanced global stop manager with process awareness
class GlobalStopManager:
    _stop_flag = False
    _processes = []
    
    @classmethod
    def set_stop_flag(cls, value):
        cls._stop_flag = value
        if value:
            cls.terminate_all_processes()
    
    @classmethod
    def should_stop(cls):
        return cls._stop_flag
    
    @classmethod
    def register_process(cls, process):
        cls._processes.append(process)
    
    @classmethod
    def terminate_all_processes(cls):
        for process in cls._processes:
            try:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)
                    if process.is_alive():
                        process.kill()
            except:
                pass
        cls._processes.clear()

# Timeout wrapper for immediate testing
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

def process_pdfs_parallel_with_timeout(self, *args, **kwargs):
    """Wrapper with overall timeout for immediate testing."""
    if not IS_WINDOWS:
        import signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3600)  # 1-hour overall timeout
    
    try:
        return self.process_pdfs_with_recovery(*args, **kwargs)
    except TimeoutException:
        print("        ⏰ OVERALL TIMEOUT: Process took too long, terminating")
        return []
    finally:
        if not IS_WINDOWS:
            signal.alarm(0)  # Cancel alarm

# Emergency stop mechanism
def emergency_stop():
    """Emergency stop function that can be called to terminate all processes."""
    print("🚨 EMERGENCY STOP TRIGGERED")
    GlobalStopManager.set_stop_flag(True)
    import os
    import sys
    # Force terminate the process
    os._exit(1)

# Try to import psutil, but provide fallback if not available
PSUTIL_AVAILABLE = False
try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
    print("✅ psutil imported successfully - enhanced system monitoring available")
except (ImportError, ModuleNotFoundError):
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil not available - using fallback memory detection")
    print("💡 To install psutil: pip install psutil")
    print("💡 psutil provides better system resource monitoring for performance optimization")
except Exception as e:
    PSUTIL_AVAILABLE = False
    print(f"⚠️ psutil import failed: {e} - using fallback memory detection")
    print("💡 To install psutil: pip install psutil")
    print("💡 psutil provides better system resource monitoring for performance optimization")

# VV LOGGING: Add very verbose logging
def vv_log(message):
    """Minimal logging to avoid performance issues."""
    if "❌" in message or "ERROR" in message:
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

class TimeoutError(Exception):
    """Custom timeout exception."""
    pass

def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("PDF processing timed out")

# Check if we're on Windows (where SIGALRM is not available)
IS_WINDOWS = platform.system() == "Windows"

def process_single_pdf(args):
    """Standalone function to process a single PDF for multiprocessing."""
    pdf_path, search_keywords, description, threshold = args
    
    # Check global stop flag more frequently
    if GlobalStopManager.should_stop():
        return None
    
    try:
        # Extract text from PDF
        pdf_text = extract_pdf_text_standalone(pdf_path)
        
        if GlobalStopManager.should_stop():
            return None
        
        if not pdf_text:
            return None
        
        # Check global stop flag again
        if GlobalStopManager.should_stop():
            return None
        
        # Calculate match score with filename filtering
        score = calculate_match_score_standalone(search_keywords, pdf_text, description, threshold, pdf_path)
        
        if score >= threshold:
            return {
                'pdf_path': pdf_path,
                'score': score,
                'supplier': os.path.basename(os.path.dirname(pdf_path))
            }
        
        return None
        
    except Exception as e:
        return None

def extract_pdf_text_standalone(pdf_path, timeout_seconds=15):
    """Standalone PDF text extraction function for multiprocessing."""
    try:
        # Check if file exists and is readable
        if not os.path.exists(pdf_path):
            return ""
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > 50 * 1024 * 1024 or file_size == 0:
            return ""
        
        # Quick PDF header check to avoid hanging
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(1024)
                if not header.startswith(b'%PDF'):
                    return ""
        except:
            return ""
        
        # Suppress warnings more aggressively
        import warnings
        warnings.filterwarnings("ignore")
        
        import logging
        logging.getLogger('pdfplumber').setLevel(logging.ERROR)
        logging.getLogger('PyPDF2').setLevel(logging.ERROR)
        
        # Initialize text accumulator before any extraction attempts
        text = ""
        
        # Try PyPDF2 first
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                
                if reader.is_encrypted:
                    return ""
                
                max_pages = 5  # Further reduced for stability
                max_text_length = 5000  # Reduced text limit
                
                for page_num in range(min(len(reader.pages), max_pages)):
                    try:
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + " "
                            if len(text) > max_text_length:
                                break
                    except:
                        continue
                
                if text.strip():
                    return text.strip()
        except:
            pass
        
        # Try pdfplumber as fallback with same limits
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in range(min(len(pdf.pages), 3)):  # Further reduced
                    try:
                        page = pdf.pages[page_num]
                        page_text = page.extract_text() or ""
                        if not page_text:
                            try:
                                words = page.extract_words()
                                page_text = " ".join([word['text'] for word in words if 'text' in word])
                            except:
                                pass
                        
                        if page_text:
                            text += page_text + " "
                            if len(text) > 5000:
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

def calculate_match_score_standalone(keywords, pdf_text, description, threshold=30, pdf_path=""):
    """Standalone match score calculation for multiprocessing with filename filtering."""
    try:
        if not keywords or not pdf_text:
            return 0.0
        
        # Content quality filter - reject low-content PDFs
        if len(pdf_text.strip()) < 800:
            return 0.0
        
        pdf_text_lower = pdf_text.lower()
        description_lower = description.lower()
        filename_lower = os.path.basename(pdf_path).lower() if pdf_path else ""
        
        # Filename quality signals
        filename_penalty = 0.0
        filename_boost = 0.0
        
        # Negative signals (marketing/noise)
        negative_patterns = [
            'price', 'price-sheet', 'executive', 'summary', 'sustainability', 
            'checklist', 'faq', 'one-pager', 'updated', 'brochure', 'catalog',
            'flyer', 'poster', 'presentation', 'overview', 'intro'
        ]
        
        # Positive signals (technical docs)
        positive_patterns = [
            'manual', 'instructions', 'ifu', 'datasheet', 'spec', 'specification',
            'user-guide', 'user guide', 'installation', 'maintenance', 'service',
            'technical', 'protocol', 'procedure', 'guide', 'handbook'
        ]
        
        # Apply filename penalties/boosts
        for pattern in negative_patterns:
            if pattern in filename_lower:
                filename_penalty += 15  # Heavy penalty for marketing docs
                break
        
        for pattern in positive_patterns:
            if pattern in filename_lower:
                filename_boost += 10  # Boost for technical docs
                break
        
        # Keyword matching (60% of score)
        keyword_score = 0.0
        matched_keywords = []
        
        for keyword in keywords:
            if keyword in pdf_text_lower:
                matched_keywords.append(keyword)
        
        if keywords:
            keyword_score = (len(matched_keywords) / len(keywords)) * 60
        
        # Text similarity (25% of score) - increased sample size
        similarity_score = 0.0
        if description and pdf_text:
            max_text_length = 2000  # Increased from 500
            pdf_text_sample = pdf_text_lower[:max_text_length]
            similarity = SequenceMatcher(None, description_lower, pdf_text_sample).ratio()
            similarity_score = similarity * 25
        
        # Filename relevance (15% of score)
        filename_score = 0.0
        if filename_lower and description_lower:
            # Check if description keywords appear in filename
            desc_words = re.findall(r'\b\w+\b', description_lower)
            filename_matches = sum(1 for word in desc_words if len(word) > 3 and word in filename_lower)
            if desc_words:
                filename_score = (filename_matches / len(desc_words)) * 15
        
        # Total score with adjustments
        total_score = keyword_score + similarity_score + filename_score
        total_score = max(0, total_score - filename_penalty)  # Apply penalty
        total_score = min(100, total_score + filename_boost)  # Apply boost
        
        return total_score
        
    except:
        return 0.0

    # normalize_filename and deduplicate_matches are imported from crossref_utils at the top of this file.

class PDFSmartFilter:
    """Smart PDF filtering system to prioritize useful PDFs and filter out noise."""
    
    def __init__(self):
        # Pre-compile all patterns once — avoids re-compilation on every filename check
        _compile = lambda pats: [re.compile(p, re.IGNORECASE) for p in pats]

        # High priority patterns (instruction manuals, guides, etc.)
        self.high_priority_patterns = _compile([
            r'.*manual.*',
            r'.*instruction.*',
            r'.*guide.*',
            r'.*handbook.*',
            r'.*user.*guide.*',
            r'.*operation.*',
            r'.*setup.*',
            r'.*installation.*',
            r'.*configuration.*',
            r'.*reference.*',
            r'.*documentation.*',
        ])

        # Medium priority patterns (specs only, not datasheets)
        self.medium_priority_patterns = _compile([
            r'.*specification.*',
            r'.*spec.*sheet.*',
            r'.*technical.*data.*',
            r'.*product.*info.*',
        ])

        # Low priority / noise patterns (should be filtered out or deprioritised)
        self.noise_patterns = _compile([
            r'.*catalog.*drawing.*',
            r'.*\(catalog.*drawing\).*',
            r'.*catalog.*',
            r'.*drawing.*',
            r'.*dwg.*',
            r'.*cad.*',
            r'.*schematic.*',
            r'.*reprint.*',
            r'.*brochure.*',
            r'.*flyer.*',
            r'.*poster.*',
            r'.*advertisement.*',
            r'.*ad.*sheet.*',
            r'.*marketing.*',
            r'.*sales.*sheet.*',
            r'carrier\d+.*',
            r'.*part.*list.*',
            r'.*parts.*catalog.*',
            r'.*price.*list.*',
            r'.*order.*form.*',
            r'.*color.*code.*parts.*list.*',
            r'.*datasheet.*',
            r'.*self.*assessment.*',
        ])
    
    def classify_pdf(self, filename):
        """
        Classify PDF by filename and return (category, priority_score)
        Priority: 100=high, 50=medium, 10=low, 0=noise
        """
        # Patterns are pre-compiled with IGNORECASE — no need to lowercase filename
        for pattern in self.high_priority_patterns:
            if pattern.search(filename):
                return ("high_priority", 100)

        for pattern in self.medium_priority_patterns:
            if pattern.search(filename):
                return ("medium_priority", 50)

        for pattern in self.noise_patterns:
            if pattern.search(filename):
                return ("noise", 0)

        return ("unknown", 25)

    def get_priority_score(self, filename):
        """
        Calculate priority score for a filename based on content patterns.
        Positive scores = high priority (manual, instruction, guide, datasheet)
        Negative scores = low priority (invoice, receipt, order form)
        Zero/neutral = neither high nor low priority

        Returns: float score (negative, zero, or positive)
        """
        if not filename or not isinstance(filename, str):
            return 0.0

        filename_lower = filename.lower()

        # High priority patterns — return positive score
        high_priority_keywords = [
            'manual', 'instruction', 'guide', 'handbook', 'user guide',
            'operation', 'setup', 'installation', 'configuration',
            'reference', 'documentation', 'datasheet', 'specification',
            'spec sheet', 'technical data', 'product info'
        ]

        for keyword in high_priority_keywords:
            if keyword in filename_lower:
                return 50.0  # Positive score for high priority

        # Low priority patterns — return negative score
        low_priority_keywords = [
            'invoice', 'receipt', 'order', 'price list', 'catalog',
            'drawing', 'dwg', 'cad', 'schematic', 'reprint', 'brochure',
            'flyer', 'poster', 'advertisement', 'marketing', 'sales',
            'part list', 'color code'
        ]

        for keyword in low_priority_keywords:
            if keyword in filename_lower:
                return -50.0  # Negative score for low priority

        # Neutral/unknown filenames
        return 0.0

    def filter_and_prioritize_pdfs(self, pdf_files, max_pdfs_per_category=None):
        """
        Filter and prioritize PDF files.
        Returns: List of (filename, category, priority_score) sorted by priority
        """
        if max_pdfs_per_category is None:
            max_pdfs_per_category = {
                "high_priority": 5,    # Process up to 5 high priority PDFs
                "medium_priority": 3,  # Process up to 3 medium priority PDFs  
                "unknown": 2,          # Process up to 2 unknown PDFs
                "noise": 0             # Skip noise PDFs entirely
            }
        
        categorized_pdfs = []
        
        # Classify all PDFs
        for pdf_file in pdf_files:
            category, priority = self.classify_pdf(pdf_file)
            categorized_pdfs.append((pdf_file, category, priority))
        
        # Sort by priority (highest first)
        categorized_pdfs.sort(key=lambda x: x[2], reverse=True)
        
        # Apply limits per category
        category_counts = {}
        filtered_pdfs = []
        
        for pdf_file, category, priority in categorized_pdfs:
            if category not in category_counts:
                category_counts[category] = 0
            
            max_for_category = max_pdfs_per_category.get(category, 0)
            
            if category_counts[category] < max_for_category:
                filtered_pdfs.append((pdf_file, category, priority))
                category_counts[category] += 1
        
        return filtered_pdfs

class CrossReferenceEngine:
    
    # Maximum number of PDF texts held in the in-process cache.
    # Each entry is typically 5–20 KB, so 300 entries ≈ 3–6 MB.
    _PDF_CACHE_MAX = 300

    def __init__(self):
        self.results = []
        self.parent_gui_processes = []  # Track child processes for cleanup
        self.pdf_filter = PDFSmartFilter()  # Initialize smart PDF filtering
        self._pdf_text_cache = {}          # path → extracted text (avoids re-reading same PDF)
        print("CrossReferenceEngine initialized with smart PDF filtering")
    
    def _get_fallback_memory_gb(self):
        """Get estimated memory in GB using fallback methods when psutil is not available."""
        try:
            # Try to get memory info from Windows-specific methods
            if platform.system() == "Windows":
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ("dwLength", wintypes.DWORD),
                            ("dwMemoryLoad", wintypes.DWORD),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                        ]
                    
                    memory_status = MEMORYSTATUSEX()
                    memory_status.dwLength = ctypes.sizeof(memory_status)
                    
                    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status)):
                        memory_gb = memory_status.ullTotalPhys / (1024**3)
                        print(f"        ✅ Windows memory detection: {memory_gb:.1f}GB")
                        return memory_gb
                except Exception as e:
                    print(f"        ⚠️ Windows memory detection failed: {e}")
            
            # Try to get memory info from /proc/meminfo on Linux
            elif platform.system() == "Linux":
                try:
                    with open('/proc/meminfo', 'r') as f:
                        for line in f:
                            if line.startswith('MemTotal:'):
                                memory_kb = int(line.split()[1])
                                memory_gb = memory_kb / (1024**2)
                                print(f"        ✅ Linux memory detection: {memory_gb:.1f}GB")
                                return memory_gb
                except Exception as e:
                    print(f"        ⚠️ Linux memory detection failed: {e}")
            
            # Try to get memory info from sysctl on macOS
            elif platform.system() == "Darwin":
                try:
                    import subprocess
                    result = subprocess.run(['sysctl', '-n', 'hw.memsize'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        memory_bytes = int(result.stdout.strip())
                        memory_gb = memory_bytes / (1024**3)
                        print(f"        ✅ macOS memory detection: {memory_gb:.1f}GB")
                        return memory_gb
                except Exception as e:
                    print(f"        ⚠️ macOS memory detection failed: {e}")
            
            # Fallback to conservative estimate based on CPU count
            try:
                cpu_count = multiprocessing.cpu_count()
                if cpu_count >= 16:
                    estimated_memory = 32.0  # High-end system
                elif cpu_count >= 8:
                    estimated_memory = 16.0  # Mid-range system
                elif cpu_count >= 4:
                    estimated_memory = 8.0   # Standard system
                else:
                    estimated_memory = 4.0   # Basic system
                
                print(f"        ⚠️ Using CPU-based memory estimation: {estimated_memory:.1f}GB")
                return estimated_memory
            except Exception as e:
                print(f"        ⚠️ CPU count detection failed: {e}")
                print(f"        💡 Using conservative default: 8.0GB")
                return 8.0
            
        except Exception as e:
            print(f"        ⚠️ All memory detection methods failed: {e}")
            print(f"        💡 Using conservative default: 8.0GB")
            return 8.0
    
    def run_cross_reference(self, input_file, master_file, pdf_dir, threshold=75, test_mode=False, clean_output=True):
        """Run cross-reference analysis with minimal logging and stop checking."""
        if not clean_output:
            print("=== STARTING CROSS-REFERENCE ANALYSIS ===")
            if test_mode:
                print("🧪 TEST MODE ENABLED - Processing limited items")
        
        try:
            # Validate inputs
            if not all([input_file, master_file, pdf_dir]):
                print("❌ Missing required inputs")
                return False
            
            # Validate files exist
            if not os.path.exists(input_file):
                print(f"❌ Input file not found: {input_file}")
                return False
            
            if not os.path.exists(master_file):
                print(f"❌ Master file not found: {master_file}")
                return False
            
            if not os.path.exists(pdf_dir):
                print(f"❌ PDF directory not found: {pdf_dir}")
                return False
            
            # Check PDF directory structure
            pdf_files_found = False
            total_pdf_files = 0
            supplier_count = 0
            
            for root, dirs, files in os.walk(pdf_dir):
                if root == pdf_dir:  # Top level - count supplier folders
                    supplier_count = len([d for d in dirs if os.path.isdir(os.path.join(pdf_dir, d))])
                
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files_found = True
                        total_pdf_files += 1
            
            if not pdf_files_found:
                print(f"❌ No PDF files found in directory: {pdf_dir}")
                if not clean_output:
                    print("Expected structure:")
                    print("  PDFs/")
                    print("  ├── Supplier1/")
                    print("  │   ├── document1.pdf")
                    print("  │   └── document2.pdf")
                    print("  └── Supplier2/")
                    print("      └── document3.pdf")
                return False
            
            if not clean_output:
                print(f"✅ Found {supplier_count} supplier folders with {total_pdf_files} PDF files")
                print("✅ File validation passed")
            
            # Load input file
            try:
                if not clean_output:
                    print(f"📂 Loading input file: {input_file}")
                input_df = pd.read_excel(input_file)
                if not clean_output:
                    print(f"✅ Input file loaded: {len(input_df)} rows")
                    print(f"📋 Input file columns: {list(input_df.columns)}")
                    
                    print("📄 First 3 rows of input file:")
                    for idx, row in input_df.head(3).iterrows():
                        print(f"  Row {idx}: {dict(row)}")
                    
            except Exception as e:
                print(f"❌ Failed to load input file: {e}")
                if not clean_output:
                    import traceback
                    print(f"❌ Traceback: {traceback.format_exc()}")
                return False
            
            # Load master file
            try:
                if not clean_output:
                    print(f"📂 Loading master file: {master_file}")
                master_df = pd.read_excel(master_file)
                if not clean_output:
                    print(f"✅ Master file loaded: {len(master_df)} rows")
                    print(f"📋 Master file columns: {list(master_df.columns)}")
                    
                    print("📄 First 3 rows of master file:")
                    for idx, row in master_df.head(3).iterrows():
                        print(f"  Row {idx}: {dict(row)}")
                    
            except Exception as e:
                print(f"❌ Failed to load master file: {e}")
                if not clean_output:
                    import traceback
                    print(f"❌ Traceback: {traceback.format_exc()}")
                return False
            
            # Validate required supplier column exists before processing
            supplier_col_names = ['Supplier Name', 'Supplier', 'Vendor', 'Company']
            if not any(col in input_df.columns for col in supplier_col_names):
                print(f"❌ No supplier column found in input file. Available columns: {list(input_df.columns)}")
                print(f"   Expected one of: {supplier_col_names}")
                return False

            # Process items
            total_items = len(input_df)
            items_with_matches = 0
            total_matches = 0
            skipped_items = 0
            processed_items = 0
            
            # SAFETY LIMIT: Only limit if extremely large to prevent memory issues
            if total_items > 1000:
                total_items = 1000
                print(f"🛡️ SAFETY LIMIT: Processing first {total_items} items to prevent memory issues")
                input_df = input_df.head(1000)  # Take first 1000 rows
            else:
                print(f"📊 Processing all {total_items} items")
            
            # Limit items in test mode
            if test_mode:
                total_items = min(total_items, 20)  # Process first 20 items in test mode
                input_df = input_df.head(20)  # Only take first 20 rows
                if not clean_output:
                    print(f"🧪 TEST MODE: Processing only first {total_items} items")
            
            print(f"Processing {total_items} items...")
            
            # Add timeout for the entire main loop
            import time
            main_loop_start = time.time()
            main_loop_timeout = 7200  # 2 hours maximum for main loop (for large datasets)
            
            for idx, row in input_df.iterrows():
                # Check main loop timeout
                if time.time() - main_loop_start > main_loop_timeout:
                    print(f"🚨 MAIN LOOP TIMEOUT: Exceeded {main_loop_timeout/60:.1f} minutes, stopping")
                    break
                
                # Check if analysis should be stopped
                if hasattr(self, 'stop_analysis') and self.stop_analysis:
                    print("🛑 Analysis stopped by user")
                    return False
                    
                processed_items += 1
                print(f"\n--- Processing item {processed_items}/{total_items} ---")
                
                try:
                    # Try different possible column names for item code/type
                    item_code = ''
                    for col_name in ['TYPE', 'Item Code', 'ItemCode', 'Code', 'ID', 'Item ID', 'Item_ID']:
                        if col_name in input_df.columns:
                            item_code = str(row.get(col_name, '')).strip()
                            print(f"  Found item code in column '{col_name}': {item_code}")
                            break
                    
                    # Try different possible column names for description
                    description = ''
                    for col_name in ['Item Description', 'Description', 'ItemDescription', 'Name', 'Title', 'Product Name']:
                        if col_name in input_df.columns:
                            description = str(row.get(col_name, '')).strip()
                            print(f"  Found description in column '{col_name}': {description}")
                            break
                    
                    # Try different possible column names for category
                    category = ''
                    for col_name in ['Category', 'Categories', 'Type', 'Product Type', 'Group']:
                        if col_name in input_df.columns:
                            category = str(row.get(col_name, '')).strip()
                            print(f"  Found category in column '{col_name}': {category}")
                            break
                    
                    # Check TYPE column for filtering
                    item_type = ''
                    type_col = None
                    for col_name in ['TYPE', 'Type', 'Item Type', 'Product Type']:
                        if col_name in input_df.columns:
                            type_col = col_name
                            item_type = str(row.get(col_name, '')).strip()
                            print(f"  Found item type in column '{col_name}': {item_type}")
                            break
                    
                    print(f"Processing item {idx+1}/{total_items}: {item_code}")
                    print(f"  Description: {description}")
                    print(f"  Category: {category}")
                    print(f"  Type: {item_type}")
                    
                    # Skip items marked as "Non-Instrument"
                    if item_type and item_type.lower() == 'non-instrument':
                        print(f"  ⏭️ Skipping - marked as Non-Instrument")
                        skipped_items += 1
                        continue
                    
                    # If no item code found, use the row index as identifier
                    if not item_code:
                        item_code = f"ITEM_{idx+1}"
                        print(f"  Using row index as identifier: {item_code}")
                    
                    if not description:
                        print(f"  ❌ Skipping - missing description")
                        continue
                    
                    print(f"  🔍 Starting PDF search for: {item_code}")
                    
                    # Find matches
                    matches = self.find_matching_pdfs(item_code, description, category, pdf_dir, master_df, threshold, input_df)
                    
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
                    import traceback
                    print(f"  Traceback: {traceback.format_exc()}")
                    continue
            
            # Summary
            if clean_output:
                self.show_clean_results_summary(items_with_matches, total_matches, processed_items, skipped_items)
            else:
                print("=== CROSS-REFERENCE ANALYSIS COMPLETE ===")
                print(f"Total items processed: {processed_items}")
                print(f"Items skipped (Non-Instrument): {skipped_items}")
                print(f"Items with matches: {items_with_matches}")
                print(f"Total matches found: {total_matches}")
                
                if items_with_matches > 0:
                    avg_matches = total_matches / items_with_matches
                    print(f"Average matches per item: {avg_matches:.1f}")
                
                print(f"Match threshold used: {threshold}%")
                print(f"Items with no matches: {processed_items - items_with_matches}")
                if processed_items - items_with_matches > 0:
                    print(f"Match rate: {(items_with_matches / processed_items) * 100:.1f}%")
                    print("💡 If no matches are found, check:")
                    print("  1. Supplier directory names match input file supplier names")
                    print("  2. PDF files contain the expected keywords")
                    print("  3. PDF text extraction is working properly")
                    print("  4. Keywords are being extracted correctly from descriptions")
            
            # FINAL CLEANUP - Critical for preventing hanging
            self.cleanup_processes()
            
            print("✅ Cross-reference analysis completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Cross-reference analysis failed: {e}")
            # Ensure cleanup even on failure
            self.cleanup_processes()
            return False

    def show_clean_results_summary(self, items_with_matches, total_matches, processed_items, skipped_items):
        """Display a clean summary of results showing only matches."""
        print("=" * 60)
        print("CROSS-REFERENCE RESULTS SUMMARY")
        print("=" * 60)
        
        if items_with_matches > 0:
            print(f"✅ Found {total_matches} matches for {items_with_matches} items")
            avg_matches = total_matches / items_with_matches
            print(f"📊 Average: {avg_matches:.1f} matches per item")
            
            # Show all matches in clean format
            print("\n📋 MATCH RESULTS:")
            total_pdfs = len(self.results)
            for i, result in enumerate(self.results, 1):
                # Extract filename from full path
                pdf_filename = os.path.basename(result['Matched PDF'])
                print(f"✅ MATCH! PDF {i}/{total_pdfs}: {pdf_filename} (Score: {result['Match Score']:.1f}%)")
        else:
            print("❌ No matches found")
            print("💡 Try lowering the threshold or checking your data")
        
        print(f"\n📈 Statistics:")
        print(f"  • Items processed: {processed_items}")
        print(f"  • Items with matches: {items_with_matches}")
        print(f"  • Items skipped: {skipped_items}")
        
        if processed_items > 0:
            match_rate = (items_with_matches / processed_items) * 100
            print(f"  • Match rate: {match_rate:.1f}%")
        
        print("=" * 60)

    def run_cross_reference_by_supplier(self, input_file, master_file, pdf_dir, threshold=60, test_mode=False, low_cpu_mode=False, clean_output=True):
        """Process suppliers one by one in alphabetical order - naturally completes when done."""
        print("=== STARTING SUPPLIER-BY-SUPPLIER CROSS-REFERENCE ANALYSIS ===")
        print("🎯 Processing each supplier directory in alphabetical order")
        print("🏁 Will naturally complete when all supplier directories are processed")
        
        if test_mode:
            print("🧪 TEST MODE ENABLED - Processing limited suppliers")
        
        try:
            # Validate inputs
            if not all([input_file, master_file, pdf_dir]):
                print("❌ Missing required inputs")
                return False
            
            # Validate files exist
            if not os.path.exists(input_file):
                print(f"❌ Input file not found: {input_file}")
                return False
            
            if not os.path.exists(master_file):
                print(f"❌ Master file not found: {master_file}")
                return False
            
            if not os.path.exists(pdf_dir):
                print(f"❌ PDF directory not found: {pdf_dir}")
                return False
            
            # Load input file
            try:
                input_df = pd.read_excel(input_file)
                print(f"✅ Loaded input file: {len(input_df)} items")
            except Exception as e:
                print(f"❌ Error loading input file: {e}")
                return False
            
            # Load master file
            try:
                master_df = pd.read_excel(master_file)
                print(f"✅ Loaded master file: {len(master_df)} suppliers")
            except Exception as e:
                print(f"❌ Error loading master file: {e}")
                return False
            
            # Get all supplier directories in alphabetical order
            supplier_directories = sorted([d for d in os.listdir(pdf_dir) 
                                         if os.path.isdir(os.path.join(pdf_dir, d))])
            
            print(f"📂 Found {len(supplier_directories)} supplier directories to process")
            print(f"📋 Suppliers: {supplier_directories[:10]}{'...' if len(supplier_directories) > 10 else ''}")
            print(f"🔄 Each supplier will be processed individually with progress indicators")
            
            if test_mode and len(supplier_directories) > 5:
                supplier_directories = supplier_directories[:5]
                print(f"🧪 TEST MODE: Limited to first {len(supplier_directories)} suppliers")
            
            # Initialize counters
            processed_suppliers = 0
            processed_items = 0
            total_matches = 0
            suppliers_with_matches = 0
            total_skipped_items = 0
            
            # Add timeout for the entire process
            import time
            start_time = time.time()
            max_total_time = 7200  # 2 hours maximum
            
            # Process each supplier directory
            for supplier_idx, supplier_dir in enumerate(supplier_directories, 1):
                # Check timeout
                if time.time() - start_time > max_total_time:
                    print(f"🚨 OVERALL TIMEOUT: Exceeded {max_total_time/60:.1f} minutes, stopping")
                    break
                
                # Check if analysis should be stopped
                if hasattr(self, 'stop_analysis') and self.stop_analysis:
                    print("🛑 Analysis stopped by user")
                    return False
                
                # Calculate progress and timing information
                progress_percentage = (supplier_idx / len(supplier_directories)) * 100
                elapsed_time = time.time() - start_time
                
                # Estimate remaining time based on current progress
                if supplier_idx > 1:  # Avoid division by zero
                    avg_time_per_supplier = elapsed_time / (supplier_idx - 1)
                    remaining_suppliers = len(supplier_directories) - supplier_idx + 1
                    estimated_remaining_time = avg_time_per_supplier * remaining_suppliers
                    eta_minutes = estimated_remaining_time / 60
                    eta_display = f" | ETA: {eta_minutes:.1f}m" if eta_minutes > 1 else f" | ETA: {estimated_remaining_time:.0f}s"
                else:
                    eta_display = ""
                
                print(f"\n{'='*80}")
                print(f"🏢 PROCESSING SUPPLIER {supplier_idx}/{len(supplier_directories)} ({progress_percentage:.1f}%)")
                print(f"📂 Supplier: {supplier_dir}")
                print(f"⏱️  Elapsed: {elapsed_time/60:.1f}m{eta_display}")
                print(f"{'='*80}")
                processed_suppliers += 1
                
                # Find all items in Excel that belong to this supplier
                all_supplier_items = input_df[input_df.apply(lambda row: any(
                    str(row.get(col, '')).lower().strip() == supplier_dir.lower().strip() 
                    for col in ['Supplier Name', 'Supplier', 'Company', 'Vendor', 'Manufacturer'] 
                    if col in input_df.columns
                ), axis=1)]
                
                # Filter out non-instruments and get final items to process
                supplier_items = self.find_items_for_supplier(input_df, supplier_dir)
                
                if len(all_supplier_items) > 0:
                    skipped_for_supplier = len(all_supplier_items) - len(supplier_items)
                    total_skipped_items += skipped_for_supplier
                
                if len(supplier_items) == 0:
                    if len(all_supplier_items) > 0:
                        print(f"  ⚠️ All {len(all_supplier_items)} items for supplier '{supplier_dir}' were Non-Instrument/Software, skipping...")
                    else:
                        print(f"  ⚠️ No items found for supplier '{supplier_dir}', skipping...")
                    continue
                
                # Get all PDFs for this supplier
                supplier_path = os.path.join(pdf_dir, supplier_dir)
                pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                
                if not pdf_files:
                    print(f"  ⚠️ No PDF files found for supplier '{supplier_dir}', skipping...")
                    continue
                
                print(f"  📄 Found {len(pdf_files)} PDF files for this supplier")
                
                # Apply smart PDF filtering to prioritize useful PDFs and filter out noise
                print(f"  🎯 Applying smart PDF filtering...")
                filtered_pdfs = self.pdf_filter.filter_and_prioritize_pdfs(pdf_files)
                
                if not filtered_pdfs:
                    print(f"  ❌ No PDFs passed smart filtering (all were noise), skipping supplier...")
                    continue
                
                # Show filtering results
                category_counts = {}
                for _, category, _ in filtered_pdfs:
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                print(f"  📊 Smart filtering results:")
                print(f"    Original PDFs: {len(pdf_files)}")
                print(f"    After filtering: {len(filtered_pdfs)}")
                print(f"    Filtered out: {len(pdf_files) - len(filtered_pdfs)} PDFs ({((len(pdf_files) - len(filtered_pdfs)) / len(pdf_files) * 100):.1f}%)")
                for category, count in category_counts.items():
                    print(f"    {category}: {count} PDFs")
                
                # Extract just the filenames for processing
                filtered_pdf_files = [pdf_file for pdf_file, _, _ in filtered_pdfs]
                
                # Process all items for this supplier against filtered PDFs
                supplier_matches = self.process_supplier_items(
                    supplier_items, supplier_dir, supplier_path, filtered_pdf_files, 
                    threshold, low_cpu_mode
                )
                
                processed_items += len(supplier_items)
                
                if supplier_matches > 0:
                    suppliers_with_matches += 1
                    total_matches += supplier_matches
                    print(f"  ✅ Supplier '{supplier_dir}': {supplier_matches} matches found from {len(supplier_items)} items")
                else:
                    print(f"  ❌ Supplier '{supplier_dir}': No matches found from {len(supplier_items)} items")
                
                # Display completion summary for this supplier
                current_time = time.time()
                total_elapsed = current_time - start_time
                if supplier_idx > 1:
                    supplier_time = total_elapsed / supplier_idx
                    print(f"  📊 Supplier completed (avg {supplier_time:.1f}s per supplier)")
                else:
                    print(f"  📊 Supplier completed")
                print(f"  📈 Overall progress: {processed_suppliers}/{len(supplier_directories)} suppliers, {total_matches} total matches")
                
                # Memory cleanup after each supplier
                import gc
                gc.collect()
            
            # Final cleanup and results
            self.cleanup_processes()
            
            total_time = time.time() - start_time
            print(f"\n🏁 SUPPLIER-BY-SUPPLIER ANALYSIS COMPLETE")
            print(f"⏱️ Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
            print(f"📊 Processed {processed_suppliers} suppliers")
            print(f"📊 Processed {processed_items} Instrument items")
            print(f"📊 Skipped {total_skipped_items} Non-Instrument/Software items")
            print(f"📊 Found {total_matches} total matches")
            print(f"📊 {suppliers_with_matches}/{processed_suppliers} suppliers had matches")
            
            if total_matches > 0:
                match_rate = (suppliers_with_matches / processed_suppliers) * 100 if processed_suppliers > 0 else 0
                print(f"📊 Supplier match rate: {match_rate:.1f}%")
                if processed_items > 0:
                    item_match_rate = (total_matches / processed_items) * 100
                    print(f"📊 Item match rate: {item_match_rate:.1f}% ({total_matches}/{processed_items} items found matches)")
            
            return True
            
        except Exception as e:
            print(f"❌ Supplier-by-supplier analysis failed: {e}")
            self.cleanup_processes()
            return False

    def find_items_for_supplier(self, input_df, supplier_dir):
        """Find all items in the Excel file that belong to a specific supplier and filter out non-instruments."""
        supplier_items = pd.DataFrame()
        
        for col_name in ['Supplier Name', 'Supplier', 'Company', 'Vendor', 'Manufacturer']:
            if col_name in input_df.columns:
                # Find items that match this supplier directory (case-insensitive, exact match)
                mask = input_df[col_name].astype(str).str.lower().str.strip() == supplier_dir.lower().strip()
                potential_items = input_df[mask]
                
                if len(potential_items) > 0:
                    supplier_items = potential_items
                    print(f"    📋 Found {len(supplier_items)} total items in column '{col_name}'")
                    break
        
        # Filter out Non-Instrument and Software items
        if not supplier_items.empty:
            original_count = len(supplier_items)
            
            # Find TYPE column for filtering
            type_col = None
            for col_name in ['TYPE', 'Type', 'Item Type', 'Product Type']:
                if col_name in supplier_items.columns:
                    type_col = col_name
                    break
            
            if type_col:
                # Filter to only include Instruments (exclude Non-Instrument and Software)
                before_filter = len(supplier_items)
                instrument_mask = ~supplier_items[type_col].astype(str).str.lower().str.strip().isin(['non-instrument', 'software'])
                supplier_items = supplier_items[instrument_mask]
                filtered_count = len(supplier_items)
                skipped_count = before_filter - filtered_count
                
                if skipped_count > 0:
                    print(f"    ⏭️ Filtered out {skipped_count} Non-Instrument/Software items")
                print(f"    🎯 Processing {filtered_count} Instrument items for this supplier")
            else:
                print(f"    ⚠️ No TYPE column found - processing all {len(supplier_items)} items")
        
        return supplier_items

    def process_supplier_items(self, supplier_items, supplier_dir, supplier_path, pdf_files, threshold, low_cpu_mode):
        """Process all items for a specific supplier against all PDFs in that supplier's directory."""
        supplier_matches = 0
        
        # Prepare PDF file paths for this supplier
        pdf_file_paths = [(os.path.join(supplier_path, pdf_file), supplier_dir) for pdf_file in pdf_files]
        
        for item_idx, (idx, row) in enumerate(supplier_items.iterrows(), 1):
            # Check if analysis should be stopped
            if hasattr(self, 'stop_analysis') and self.stop_analysis:
                print("      🛑 Analysis stopped by user")
                break
            
            # Extract item information
            item_code = self.extract_item_code(row, supplier_items.columns)
            description = self.extract_description(row, supplier_items.columns)
            category = self.extract_category(row, supplier_items.columns)
            
            # Extract TYPE information for filtering
            item_type = self.extract_type(row, supplier_items.columns)
            
            # Skip items marked as "Non-Instrument" or "Software" - only process "Instruments"
            if item_type and item_type.lower() in ['non-instrument', 'software']:
                print(f"      ⏭️ Item {item_idx}: Skipping {item_type} - {item_code}")
                continue
            
            if not description:
                print(f"      ⚠️ Item {item_idx}: No description found, skipping")
                continue
            
            item_progress = (item_idx / len(supplier_items)) * 100
            print(f"      🔍 Item {item_idx}/{len(supplier_items)} ({item_progress:.1f}%): {item_code} - {description[:50]}...")
            
            # Extract keywords for this item
            search_keywords = self.extract_keywords(description, category)
            if not search_keywords:
                print(f"      ⚠️ No keywords extracted for item {item_code}")
                continue
            
            # Process this item against all PDFs in this supplier's directory
            matches = self.process_pdfs_with_recovery(pdf_file_paths, search_keywords, description, threshold)
            
            if matches:
                supplier_matches += len(matches)
                print(f"      ✅ Item {item_code}: {len(matches)} matches found")
                
                # Add to results
                for match in matches:
                    self.results.append({
                        'Item Code': item_code,
                        'Description': description,
                        'Category': category,
                        'Matched PDF': match['pdf_path'],
                        'Match Score': match['score'],
                        'Supplier': supplier_dir
                    })
            else:
                print(f"      ❌ Item {item_code}: No matches found")
        
        return supplier_matches

    def extract_item_code(self, row, columns):
        """Extract item code from row using various possible column names."""
        for col_name in ['TYPE', 'Item Code', 'ItemCode', 'Code', 'ID', 'Item ID', 'Item_ID']:
            if col_name in columns:
                return str(row.get(col_name, '')).strip()
        return f"ITEM_{row.name}"  # Use row index as fallback

    def extract_description(self, row, columns):
        """Extract description from row using various possible column names."""
        for col_name in ['Item Description', 'Description', 'ItemDescription', 'Name', 'Title', 'Product Name']:
            if col_name in columns:
                desc = str(row.get(col_name, '')).strip()
                if desc and desc != 'nan':
                    return desc
        return ""

    def extract_category(self, row, columns):
        """Extract category from row using various possible column names."""
        for col_name in ['Category', 'Categories', 'Type', 'Product Type', 'Group']:
            if col_name in columns:
                cat = str(row.get(col_name, '')).strip()
                if cat and cat != 'nan':
                    return cat
        return ""

    def extract_type(self, row, columns):
        """Extract type from row using various possible column names."""
        for col_name in ['TYPE', 'Type', 'Item Type', 'Product Type']:
            if col_name in columns:
                type_val = str(row.get(col_name, '')).strip()
                if type_val and type_val != 'nan':
                    return type_val
        return ""

    def run_cross_reference_high_performance(self, input_file, master_file, pdf_dir, threshold=60, test_mode=False, low_cpu_mode=False, clean_output=True):
        """High-performance cross-reference analysis - now uses supplier-by-supplier approach."""
        return self.run_cross_reference_by_supplier(input_file, master_file, pdf_dir, threshold, test_mode, low_cpu_mode, clean_output)

    def find_matching_pdfs(self, item_code, description, category, pdf_dir, master_df, threshold, input_df=None):
        """Find matching PDFs by searching only in the specific supplier directory."""
        matches = []
        start_time = time.time()
        
        try:
            # This method is kept for compatibility but now uses supplier-by-supplier approach
            print(f"    🔍 Legacy method called for item: {item_code}")
            print(f"    💡 Consider using run_cross_reference_by_supplier for better performance")
            return matches
            
        except Exception as e:
            print(f"    ❌ Error in find_matching_pdfs: {e}")
            return matches

    def find_matching_pdfs_high_performance(self, item_code, description, category, pdf_dir, master_df, threshold, input_df=None, low_cpu_mode=False):
        """High-performance PDF matching using multiprocessing - now uses supplier-by-supplier approach."""
        try:
            # This method is kept for compatibility but now uses supplier-by-supplier approach
            print(f"    🔍 Legacy high-performance method called for item: {item_code}")
            print(f"    💡 Consider using run_cross_reference_by_supplier for better performance")
            return []
            
        except Exception as e:
            print(f"    ❌ Error in find_matching_pdfs_high_performance: {e}")
            return []

    def extract_keywords(self, description, category):
        """Extract keywords with optimized performance."""
        keywords = []
        
        try:
            # Add category keywords
            if category and str(category).strip():
                category_str = str(category).strip()
                category_keywords = category_str.lower().split()
                keywords.extend(category_keywords)
            
            # Add description keywords
            if description and str(description).strip():
                description_str = str(description).strip()
                # Simple keyword extraction
                desc_words = description_str.lower().split()
                keywords.extend(desc_words)
            
            return list(set(keywords))  # Remove duplicates
            
        except Exception as e:
            return []

    def process_pdfs_parallel(self, pdf_file_paths, search_keywords, description, threshold, low_cpu_mode=False):
        """
        Process PDFs with timeout protection and proper cleanup.
        """
        if not pdf_file_paths:
            print("❌ No PDF files to process")
            return []
        
        print(f"🔄 Processing {len(pdf_file_paths)} PDFs in parallel...")
        matches = []
        processed_count = 0
        
        try:
            # Use single worker for stability
            max_workers = 1
            
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_pdf = {}
                for pdf_path in pdf_file_paths:
                    future = executor.submit(
                        process_single_pdf,
                        pdf_path, search_keywords, description, threshold, low_cpu_mode
                    )
                    future_to_pdf[future] = pdf_path
                
                # Process results with timeout
                overall_timeout = 1800  # 30 minutes total
                for future in as_completed(future_to_pdf, timeout=overall_timeout):
                    pdf_path = future_to_pdf[future]
                    
                    try:
                        # Get result with timeout
                        result = future.result(timeout=60)  # 1 minute per PDF
                        if result:
                            matches.extend(result)
                        
                        processed_count += 1
                        
                        # Progress update and memory cleanup
                        if processed_count % 50 == 0:
                            print(f"📊 Processed {processed_count}/{len(pdf_file_paths)} PDFs")
                            import gc
                            gc.collect()
                        
                        # Check stop flag
                        if GlobalStopManager.should_stop():
                            print("🛑 Processing stopped by global flag")
                            break
                            
                    except TimeoutError:
                        print(f"⏰ Timeout processing {os.path.basename(pdf_path)}")
                    except Exception as e:
                        print(f"❌ Error processing {os.path.basename(pdf_path)}: {e}")
                
                # Explicit shutdown with cancellation of pending tasks
                executor.shutdown(wait=False, cancel_futures=True)
                
        except Exception as e:
            print(f"❌ Parallel processing failed: {e}")
            # Fallback to sequential processing
            return self.process_pdfs_sequential(pdf_file_paths, search_keywords, description, threshold, low_cpu_mode)
        
        finally:
            # Force cleanup
            import gc
            gc.collect()
        
        print(f"✅ Parallel processing complete: {len(matches)} matches found")
        return matches

    def find_matching_pdfs(self, item_code, description, category, pdf_dir, master_df, threshold, input_df=None):
        """Find matching PDFs by searching only in the specific supplier directory."""
        matches = []
        start_time = time.time()
        
        try:
            # Extract keywords from current item
            search_keywords = self.extract_keywords(description, category)
            
            if not search_keywords:
                print("    ❌ No keywords extracted")
                return matches
            
            # Find the specific supplier for this item
            current_supplier = None
            supplier_col = None
            
            if input_df is not None:
                # Find supplier column - prioritize 'Supplier Name'
                for col_name in ['Supplier Name', 'Supplier', 'Vendor', 'Company']:
                    if col_name in input_df.columns:
                        supplier_col = col_name
                        break
                
                if supplier_col:
                    # Find the current item's supplier by matching the item_code
                    try:
                        # Try to find the row by item_code or row index
                        if item_code.startswith('ITEM_'):
                            # Extract row index from ITEM_X format
                            row_idx = int(item_code.split('_')[1]) - 1
                            if 0 <= row_idx < len(input_df):
                                current_supplier = str(input_df.iloc[row_idx][supplier_col]).strip()
                        else:
                            # Try to find by item_code in any column
                            for col in input_df.columns:
                                if input_df[col].astype(str).str.contains(item_code, case=False, na=False).any():
                                    matching_rows = input_df[input_df[col].astype(str).str.contains(item_code, case=False, na=False)]
                                    if not matching_rows.empty:
                                        current_supplier = str(matching_rows.iloc[0][supplier_col]).strip()
                                        break
                    except Exception as e:
                        print(f"    Warning: Could not find supplier for item {item_code}: {e}")
                else:
                    print(f"    ❌ No supplier column found in input file. Available columns: {list(input_df.columns)}")
            else:
                print(f"    ❌ No input_df provided for supplier lookup")
            
            if not current_supplier or current_supplier == 'nan' or current_supplier == '':
                print(f"    ❌ No supplier found for item {item_code}, skipping")
                return matches
            
            print(f"    🎯 Looking for supplier directory: '{current_supplier}'")
            
            # Get all available supplier directories
            available_suppliers = [d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]
            print(f"    📂 Available supplier directories ({len(available_suppliers)}): {available_suppliers}")
            
            # Try to find a matching supplier directory with multiple strategies
            matching_supplier_dir = None
            
            # Strategy 1: Exact case-insensitive match
            for available_supplier in available_suppliers:
                if current_supplier.lower() == available_supplier.lower():
                    matching_supplier_dir = available_supplier
                    print(f"      ✅ Exact match found: '{current_supplier}' -> '{available_supplier}'")
                    break
            
            # Strategy 2: Partial matching (if exact match not found)
            if not matching_supplier_dir:
                for available_supplier in available_suppliers:
                    if current_supplier.lower() in available_supplier.lower() or available_supplier.lower() in current_supplier.lower():
                        matching_supplier_dir = available_supplier
                        print(f"      ⚠️ Using partial match: '{current_supplier}' -> '{available_supplier}'")
                        break
            
            # Strategy 3: Word-based matching (if still no match)
            if not matching_supplier_dir:
                current_words = set(current_supplier.lower().split())
                for available_supplier in available_suppliers:
                    available_words = set(available_supplier.lower().split())
                    # Check if at least 50% of words match
                    common_words = current_words.intersection(available_words)
                    if len(common_words) >= max(1, len(current_words) * 0.5):
                        matching_supplier_dir = available_supplier
                        print(f"      🔍 Using word-based match: '{current_supplier}' -> '{available_supplier}' (common words: {common_words})")
                        break
            
            # Strategy 4: Remove common suffixes/prefixes and try again
            if not matching_supplier_dir:
                # Remove common company suffixes
                suffixes_to_remove = [' inc', ' corp', ' ltd', ' llc', ' co', ' company', ' limited']
                prefixes_to_remove = ['the ']
                
                cleaned_current = current_supplier.lower()
                for suffix in suffixes_to_remove:
                    if cleaned_current.endswith(suffix):
                        cleaned_current = cleaned_current[:-len(suffix)].strip()
                        break
                
                for prefix in prefixes_to_remove:
                    if cleaned_current.startswith(prefix):
                        cleaned_current = cleaned_current[len(prefix):].strip()
                        break
                
                print(f"      🔧 Trying cleaned supplier name: '{cleaned_current}'")
                
                for available_supplier in available_suppliers:
                    cleaned_available = available_supplier.lower()
                    for suffix in suffixes_to_remove:
                        if cleaned_available.endswith(suffix):
                            cleaned_available = cleaned_available[:-len(suffix)].strip()
                            break
                    
                    for prefix in prefixes_to_remove:
                        if cleaned_available.startswith(prefix):
                            cleaned_available = cleaned_available[len(prefix):].strip()
                            break
                    
                    if cleaned_current == cleaned_available:
                        matching_supplier_dir = available_supplier
                        print(f"      ✅ Cleaned name match: '{current_supplier}' -> '{available_supplier}'")
                        break
            
            if not matching_supplier_dir:
                print(f"      ❌ No matching supplier directory found for '{current_supplier}'")
                print(f"      💡 Available directories: {available_suppliers}")
                
                # Show similarity scores for all available directories
                print(f"      🔍 Similarity analysis:")
                similarities = []
                for available_supplier in available_suppliers:
                    similarity = SequenceMatcher(None, current_supplier.lower(), available_supplier.lower()).ratio()
                    similarities.append((available_supplier, similarity))
                    print(f"        '{available_supplier}' -> {similarity:.3f}")
                
                # Sort by similarity and suggest the best match
                similarities.sort(key=lambda x: x[1], reverse=True)
                if similarities and similarities[0][1] > 0.3:  # If best match is >30% similar
                    best_match = similarities[0]
                    print(f"      💡 Suggested best match: '{best_match[0]}' (similarity: {best_match[1]:.3f})")
                    print(f"      ⚠️ Consider manually checking if this is the correct supplier directory")
                
                # FALLBACK: If no supplier directory found, search all directories
                print(f"      🔄 FALLBACK: Searching all PDF directories since no supplier match found")
                all_pdf_files = []
                for supplier_dir in available_suppliers:
                    supplier_path = os.path.join(pdf_dir, supplier_dir)
                    pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                    for pdf_file in pdf_files:
                        all_pdf_files.append((os.path.join(supplier_path, pdf_file), supplier_dir))
                
                print(f"      📂 FALLBACK: Will search {len(all_pdf_files)} PDF files across all directories")
                
                # Process all PDFs in fallback mode
                total_pdfs = len(all_pdf_files)
                fallback_matches = 0
                batch_size = 10
                
                for batch_start in range(0, total_pdfs, batch_size):
                    if hasattr(self, 'stop_analysis') and self.stop_analysis:
                        print("        🛑 Analysis stopped by user")
                        return matches
                        
                    batch_end = min(batch_start + batch_size, total_pdfs)
                    batch_pdfs = all_pdf_files[batch_start:batch_end]
                    
                    print(f"        Processing fallback batch {batch_start//batch_size + 1}/{(total_pdfs + batch_size - 1)//batch_size}: PDFs {batch_start + 1}-{batch_end}")
                    
                    for pdf_idx, (pdf_path, supplier_dir) in enumerate(batch_pdfs, batch_start + 1):
                        if hasattr(self, 'stop_analysis') and self.stop_analysis:
                            print("          🛑 Analysis stopped by user")
                            return matches
                            
                        pdf_start_time = time.time()
                        try:
                            pdf_file = os.path.basename(pdf_path)
                            print(f"          Analyzing fallback PDF {pdf_idx}/{total_pdfs}: {pdf_file} (from {supplier_dir})")
                            
                            # Extract text
                            pdf_text = self.extract_pdf_text(pdf_path)
                            
                            if not pdf_text:
                                print(f"            ❌ Could not extract text")
                                continue
                            
                            print(f"            ✅ Extracted {len(pdf_text)} characters")
                            
                            # Calculate match score
                            score = self.calculate_match_score(search_keywords, pdf_text, description, threshold)
                            print(f"            📊 Final Score: {score:.1f}% (threshold: {threshold}%)")
                            
                            if score >= threshold:
                                print(f"            ✅ FALLBACK MATCH! Score {score:.1f}% >= {threshold}%")
                                matches.append({
                                    'pdf_path': pdf_path,
                                    'score': score,
                                    'supplier': supplier_dir
                                })
                                fallback_matches += 1
                            else:
                                print(f"            ❌ Below threshold ({score:.1f}% < {threshold}%)")
                            
                            pdf_time = time.time() - pdf_start_time
                            print(f"            ⏱️ PDF processed in {pdf_time:.1f}s")
                                
                        except Exception as e:
                            print(f"            ❌ Error processing fallback PDF: {e}")
                            continue
                    
                    # Memory cleanup after each batch
                    import gc
                    gc.collect()
                    print(f"        🧹 Fallback batch completed, memory cleaned up")
                
                print(f"      📊 Fallback search completed: {fallback_matches} matches found")
                return matches
            
            print(f"      ✅ Found matching supplier directory: {matching_supplier_dir}")
            
            # Check if supplier exists in master file (optional check)
            supplier_found = True  # Skip master file check for now to focus on directory matching
            master_supplier_col = None
            
            # Find supplier column in master file
            for col in master_df.columns:
                if col == 'Supplier Name' or 'supplier' in col.lower() or 'name' in col.lower():
                    master_supplier_col = col
                    break
            
            if master_supplier_col:
                supplier_exists = master_df[master_supplier_col].astype(str).str.contains(matching_supplier_dir, case=False, na=False).any()
                if supplier_exists:
                    print(f"      ✅ Supplier found in master file column: {master_supplier_col}")
                else:
                    print(f"      ⚠️ Supplier '{matching_supplier_dir}' not found in master file, but continuing anyway")
            
            # Check if supplier directory exists
            supplier_path = os.path.join(pdf_dir, matching_supplier_dir)
            if not os.path.exists(supplier_path):
                print(f"      ❌ Supplier directory not found: {supplier_path}")
                return matches
            
            if not os.path.isdir(supplier_path):
                print(f"      ❌ Supplier path is not a directory: {supplier_path}")
                return matches
            
            print(f"      📂 Using supplier directory: {supplier_path}")
            
            # Get PDF files from this specific supplier directory only
            pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
            print(f"      Found {len(pdf_files)} PDF files in supplier directory")
            
            if not pdf_files:
                print(f"      ❌ No PDF files in supplier directory")
                return matches
            
            # Apply smart PDF filtering to prioritize useful PDFs and filter out noise
            print(f"      🎯 Applying smart PDF filtering...")
            filtered_pdfs = self.pdf_filter.filter_and_prioritize_pdfs(pdf_files)
            
            if not filtered_pdfs:
                print(f"      ❌ No PDFs passed smart filtering (all were noise)")
                return matches
            
            # Show filtering results
            category_counts = {}
            for _, category, _ in filtered_pdfs:
                category_counts[category] = category_counts.get(category, 0) + 1
            
            print(f"      📊 Smart filtering results:")
            print(f"        Original PDFs: {len(pdf_files)}")
            print(f"        After filtering: {len(filtered_pdfs)}")
            print(f"        Filtered out: {len(pdf_files) - len(filtered_pdfs)} PDFs ({((len(pdf_files) - len(filtered_pdfs)) / len(pdf_files) * 100):.1f}%)")
            for category, count in category_counts.items():
                print(f"        {category}: {count} PDFs")
            
            # Extract filenames and categories for processing
            pdf_files_with_categories = [(pdf_file, category, priority) for pdf_file, category, priority in filtered_pdfs]
            pdf_files = [pdf_file for pdf_file, _, _ in filtered_pdfs]
            
            # Process each PDF in batches for better memory management
            total_pdfs = len(pdf_files)
            supplier_matches = 0
            batch_size = 10  # Process 10 PDFs at a time
            
            for batch_start in range(0, total_pdfs, batch_size):
                # Check if analysis should be stopped
                if hasattr(self, 'stop_analysis') and self.stop_analysis:
                    print("        🛑 Analysis stopped by user")
                    return matches
                    
                batch_end = min(batch_start + batch_size, total_pdfs)
                batch_pdfs = pdf_files[batch_start:batch_end]
                batch_pdfs_with_categories = pdf_files_with_categories[batch_start:batch_end]
                
                print(f"        Processing batch {batch_start//batch_size + 1}/{(total_pdfs + batch_size - 1)//batch_size}: PDFs {batch_start + 1}-{batch_end}")
                
                for pdf_idx, (pdf_file, pdf_category, pdf_priority) in enumerate(batch_pdfs_with_categories, batch_start + 1):
                    # Check if analysis should be stopped
                    if hasattr(self, 'stop_analysis') and self.stop_analysis:
                        print("          🛑 Analysis stopped by user")
                        return matches
                        
                    pdf_start_time = time.time()
                    try:
                        pdf_path = os.path.join(supplier_path, pdf_file)
                        print(f"          Analyzing PDF {pdf_idx}/{total_pdfs}: {pdf_file} ({pdf_category})")
                        
                        # Extract text
                        pdf_text = self.extract_pdf_text(pdf_path)
                        
                        if not pdf_text:
                            print(f"            ❌ Could not extract text")
                            continue
                        
                        print(f"            ✅ Extracted {len(pdf_text)} characters")
                        
                        # Calculate match score with priority boost
                        base_score = self.calculate_match_score(search_keywords, pdf_text, description, threshold)
                        
                        # Apply priority boost based on PDF category
                        priority_boost = 0
                        if pdf_category == "high_priority":
                            priority_boost = 15  # +15 points for instruction manuals, guides
                        elif pdf_category == "medium_priority":
                            priority_boost = 5   # +5 points for datasheets
                        # unknown and noise get no boost (noise shouldn't reach here anyway)
                        
                        score = min(base_score + priority_boost, 100.0)
                        
                        if priority_boost > 0:
                            print(f"            📊 Base Score: {base_score:.1f}% + Priority Boost: +{priority_boost} = Final Score: {score:.1f}% (threshold: {threshold}%)")
                        else:
                            print(f"            📊 Final Score: {score:.1f}% (threshold: {threshold}%)")
                        
                        if score >= threshold:
                            print(f"            ✅ MATCH! Score {score:.1f}% >= {threshold}%")
                            matches.append({
                                'pdf_path': pdf_path,
                                'score': score,
                                'supplier': matching_supplier_dir
                            })
                            supplier_matches += 1
                        else:
                            print(f"            ❌ Below threshold ({score:.1f}% < {threshold}%)")
                        
                        pdf_time = time.time() - pdf_start_time
                        print(f"            ⏱️ PDF processed in {pdf_time:.1f}s")
                            
                    except Exception as e:
                        print(f"            ❌ Error processing PDF: {e}")
                        continue
                
                # Memory cleanup after each batch
                import gc
                gc.collect()
                print(f"        🧹 Batch completed, memory cleaned up")
            
            total_time = time.time() - start_time
            print(f"    ⏱️ Total processing time: {total_time:.1f}s")
            print(f"    📊 Processed {total_pdfs} PDFs from supplier '{matching_supplier_dir}'")
            print(f"    Total matches found: {len(matches)}")
            
            # Deduplicate matches by normalized filename
            if matches:
                original_count = len(matches)
                matches = deduplicate_matches(matches)
                if len(matches) < original_count:
                    print(f"    🔄 Deduplication: {original_count} -> {len(matches)} matches")
            
            return matches
            
        except Exception as e:
            print(f"    ❌ Error in find_matching_pdfs: {e}")
            return matches

    def find_matching_pdfs_high_performance(self, item_code, description, category, pdf_dir, master_df, threshold, input_df=None, low_cpu_mode=False):
        """High-performance PDF matching using multiprocessing."""
        matches = []
        start_time = time.time()
        
        try:
            # Extract keywords from current item
            search_keywords = self.extract_keywords(description, category)
            
            if not search_keywords:
                print("    ❌ No keywords extracted")
                return matches
            
            # Find the specific supplier for this item
            current_supplier = None
            supplier_col = None
            
            if input_df is not None:
                # Find supplier column - prioritize 'Supplier Name'
                for col_name in ['Supplier Name', 'Supplier', 'Vendor', 'Company']:
                    if col_name in input_df.columns:
                        supplier_col = col_name
                        break
                
                if supplier_col:
                    # Find the current item's supplier by matching the item_code
                    try:
                        # Try to find the row by item_code or row index
                        if item_code.startswith('ITEM_'):
                            # Extract row index from ITEM_X format
                            row_idx = int(item_code.split('_')[1]) - 1
                            if 0 <= row_idx < len(input_df):
                                current_supplier = str(input_df.iloc[row_idx][supplier_col]).strip()
                        else:
                            # Try to find by item_code in any column
                            for col in input_df.columns:
                                if input_df[col].astype(str).str.contains(item_code, case=False, na=False).any():
                                    matching_rows = input_df[input_df[col].astype(str).str.contains(item_code, case=False, na=False)]
                                    if not matching_rows.empty:
                                        current_supplier = str(matching_rows.iloc[0][supplier_col]).strip()
                                        break
                    except Exception as e:
                        print(f"    Warning: Could not find supplier for item {item_code}: {e}")
                else:
                    print(f"    ❌ No supplier column found in input file. Available columns: {list(input_df.columns)}")
            else:
                print(f"    ❌ No input_df provided for supplier lookup")
            
            if not current_supplier or current_supplier == 'nan' or current_supplier == '':
                print(f"    ❌ No supplier found for item {item_code}, skipping")
                return matches
            
            print(f"    🎯 Looking for supplier directory: '{current_supplier}'")
            
            # Get all available supplier directories
            available_suppliers = [d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]
            print(f"    📂 Available supplier directories ({len(available_suppliers)}): {available_suppliers}")
            
            # Try to find a matching supplier directory with multiple strategies
            matching_supplier_dir = None
            
            # Strategy 1: Exact case-insensitive match
            for available_supplier in available_suppliers:
                if current_supplier.lower() == available_supplier.lower():
                    matching_supplier_dir = available_supplier
                    print(f"      ✅ Exact match found: '{current_supplier}' -> '{available_supplier}'")
                    break
            
            # Strategy 2: Partial matching (if exact match not found)
            if not matching_supplier_dir:
                for available_supplier in available_suppliers:
                    if current_supplier.lower() in available_supplier.lower() or available_supplier.lower() in current_supplier.lower():
                        matching_supplier_dir = available_supplier
                        print(f"      ⚠️ Using partial match: '{current_supplier}' -> '{available_supplier}'")
                        break
            
            # Strategy 3: Word-based matching (if still no match)
            if not matching_supplier_dir:
                current_words = set(current_supplier.lower().split())
                for available_supplier in available_suppliers:
                    available_words = set(available_supplier.lower().split())
                    # Check if at least 50% of words match
                    common_words = current_words.intersection(available_words)
                    if len(common_words) >= max(1, len(current_words) * 0.5):
                        matching_supplier_dir = available_supplier
                        print(f"      🔍 Using word-based match: '{current_supplier}' -> '{available_supplier}' (common words: {common_words})")
                        break
            
            # Strategy 4: Remove common suffixes/prefixes and try again
            if not matching_supplier_dir:
                # Remove common company suffixes
                suffixes_to_remove = [' inc', ' corp', ' ltd', ' llc', ' co', ' company', ' limited']
                prefixes_to_remove = ['the ']
                
                cleaned_current = current_supplier.lower()
                for suffix in suffixes_to_remove:
                    if cleaned_current.endswith(suffix):
                        cleaned_current = cleaned_current[:-len(suffix)].strip()
                        break
                
                for prefix in prefixes_to_remove:
                    if cleaned_current.startswith(prefix):
                        cleaned_current = cleaned_current[len(prefix):].strip()
                        break
                
                print(f"      🔧 Trying cleaned supplier name: '{cleaned_current}'")
                
                for available_supplier in available_suppliers:
                    cleaned_available = available_supplier.lower()
                    for suffix in suffixes_to_remove:
                        if cleaned_available.endswith(suffix):
                            cleaned_available = cleaned_available[:-len(suffix)].strip()
                            break
                    
                    for prefix in prefixes_to_remove:
                        if cleaned_available.startswith(prefix):
                            cleaned_available = cleaned_available[len(prefix):].strip()
                            break
                    
                    if cleaned_current == cleaned_available:
                        matching_supplier_dir = available_supplier
                        print(f"      ✅ Cleaned name match: '{current_supplier}' -> '{available_supplier}'")
                        break
            
            if not matching_supplier_dir:
                print(f"      ❌ No matching supplier directory found for '{current_supplier}'")
                print(f"      🔄 FALLBACK: Searching all PDF directories since no supplier match found")
                
                # Collect all PDF files for fallback search
                all_pdf_files = []
                for supplier_dir in available_suppliers:
                    supplier_path = os.path.join(pdf_dir, supplier_dir)
                    pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                    for pdf_file in pdf_files:
                        all_pdf_files.append((os.path.join(supplier_path, pdf_file), supplier_dir))
                
                print(f"      📂 FALLBACK: Will search {len(all_pdf_files)} PDF files across all directories")
                
                # Use high-performance processing for fallback with recovery
                matches = self.process_pdfs_with_recovery(all_pdf_files, search_keywords, description, threshold)
                print(f"      📊 Fallback search completed: {len(matches)} matches found")
                return matches
            
            print(f"      ✅ Found matching supplier directory: {matching_supplier_dir}")
            
            # Check if supplier directory exists
            supplier_path = os.path.join(pdf_dir, matching_supplier_dir)
            if not os.path.exists(supplier_path) or not os.path.isdir(supplier_path):
                print(f"      ❌ Supplier directory not found or not a directory: {supplier_path}")
                return matches
            
            print(f"      📂 Using supplier directory: {supplier_path}")
            
            # Get PDF files from this specific supplier directory only
            pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
            print(f"      Found {len(pdf_files)} PDF files in supplier directory")
            
            if not pdf_files:
                print(f"      ❌ No PDF files in supplier directory")
                return matches
            
            # Apply smart PDF filtering to prioritize useful PDFs and filter out noise
            print(f"      🎯 Applying smart PDF filtering...")
            filtered_pdfs = self.pdf_filter.filter_and_prioritize_pdfs(pdf_files)
            
            if not filtered_pdfs:
                print(f"      ❌ No PDFs passed smart filtering (all were noise)")
                return matches
            
            # Show filtering results
            category_counts = {}
            for _, category, _ in filtered_pdfs:
                category_counts[category] = category_counts.get(category, 0) + 1
            
            print(f"      📊 Smart filtering results:")
            print(f"        Original PDFs: {len(pdf_files)}")
            print(f"        After filtering: {len(filtered_pdfs)}")
            print(f"        Filtered out: {len(pdf_files) - len(filtered_pdfs)} PDFs ({((len(pdf_files) - len(filtered_pdfs)) / len(pdf_files) * 100):.1f}%)")
            for category, count in category_counts.items():
                print(f"        {category}: {count} PDFs")
            
            # Extract just the filenames for processing
            filtered_pdf_files = [pdf_file for pdf_file, _, _ in filtered_pdfs]
            
            # Prepare PDF files for parallel processing
            pdf_file_paths = [(os.path.join(supplier_path, pdf_file), matching_supplier_dir) for pdf_file in filtered_pdf_files]
            
            # Use high-performance processing with recovery
            matches = self.process_pdfs_with_recovery(pdf_file_paths, search_keywords, description, threshold)
            
            total_time = time.time() - start_time
            print(f"    ⏱️ Total processing time: {total_time:.1f}s")
            print(f"    📊 Processed {len(filtered_pdf_files)} PDFs from supplier '{matching_supplier_dir}' (filtered from {len(pdf_files)} total)")
            print(f"    Total matches found: {len(matches)}")
            
            # Deduplicate matches by normalized filename
            if matches:
                original_count = len(matches)
                matches = deduplicate_matches(matches)
                if len(matches) < original_count:
                    print(f"    🔄 Deduplication: {original_count} -> {len(matches)} matches")
            
            return matches
            
        except Exception as e:
            print(f"    ❌ Error in find_matching_pdfs_high_performance: {e}")
            return matches

    def process_pdfs_parallel(self, pdf_file_paths, search_keywords, description, threshold, low_cpu_mode=False):
        """Process PDFs in parallel with proper cleanup."""
        matches = []
        
        if not pdf_file_paths:
            return matches
        
        processed_count = 0
        total_pdfs = len(pdf_file_paths)
        
        print(f"        📊 Processing {total_pdfs} PDFs for supplier")
        
        # Use a single worker for stability
        max_workers = 1
        
        try:
            # Use context manager for proper cleanup
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_args = {}
                for pdf_path, supplier_dir in pdf_file_paths:
                    future = executor.submit(process_single_pdf, 
                                           (pdf_path, search_keywords, description, threshold))
                    future_to_args[future] = (pdf_path, supplier_dir)
                
                # Process completed tasks with timeout
                for future in as_completed(future_to_args.keys()):
                    processed_count += 1
                    
                    # Check if we should stop
                    if hasattr(self, 'stop_analysis') and self.stop_analysis:
                        print("        🛑 Analysis stopped by user")
                        # Shutdown immediately without waiting
                        executor.shutdown(wait=False, cancel_futures=True)
                        return matches
                    
                    try:
                        # Add timeout to prevent hanging on individual PDFs
                        result = future.result(timeout=120)  # 2-minute timeout per PDF
                        
                        if result:
                            matches.append(result)
                            print(f"        ✅ MATCH! PDF {processed_count}/{total_pdfs}: {os.path.basename(result['pdf_path'])}")
                        else:
                            # Show progress every 10 PDFs or when complete
                            if processed_count % 10 == 0 or processed_count == total_pdfs:
                                print(f"        📊 Progress: {processed_count}/{total_pdfs} PDFs processed")
                                
                    except TimeoutError:
                        pdf_path, supplier_dir = future_to_args[future]
                        print(f"        ⏰ TIMEOUT: PDF {processed_count}/{total_pdfs} - {os.path.basename(pdf_path)}")
                        continue
                    except Exception as e:
                        print(f"        ⚠️ Error in PDF {processed_count}/{total_pdfs}: {e}")
                        continue
                
                # CRITICAL: Explicitly shutdown the executor when done
                executor.shutdown(wait=False, cancel_futures=True)
                print(f"        ✅ Completed processing {processed_count}/{total_pdfs} PDFs")
                
        except Exception as e:
            print(f"        ❌ Parallel processing error: {e}")
            # Fallback to sequential processing
            print("        🔄 Falling back to sequential processing...")
            return self.process_pdfs_sequential(pdf_file_paths, search_keywords, description, threshold)
        finally:
            # Force cleanup of any remaining processes
            try:
                import gc
                gc.collect()
                print("        🧹 Force cleanup completed")
            except:
                pass
        
        return matches

    def process_pdfs_sequential(self, pdf_file_paths, search_keywords, description, threshold):
        """Fallback sequential processing when parallel fails."""
        matches = []
        total_pdfs = len(pdf_file_paths)
        
        for i, (pdf_path, supplier_dir) in enumerate(pdf_file_paths, 1):
            if hasattr(self, 'stop_analysis') and self.stop_analysis:
                break
                
            print(f"        🔄 Sequential processing: PDF {i}/{total_pdfs}")
            
            try:
                result = process_single_pdf((pdf_path, search_keywords, description, threshold))
                if result:
                    matches.append(result)
                    print(f"        ✅ MATCH! PDF {i}/{total_pdfs}: {os.path.basename(result['pdf_path'])}")
                    
                # Progress update
                if i % 10 == 0 or i == total_pdfs:
                    print(f"        📊 Progress: {i}/{total_pdfs} PDFs processed")
                    
                # Memory cleanup every 50 PDFs
                if i % 50 == 0:
                    import gc
                    gc.collect()
                    
            except Exception as e:
                print(f"        ⚠️ Error in sequential processing PDF {i}: {e}")
                continue
                
        return matches

    def process_pdfs_with_recovery(self, pdf_file_paths, search_keywords, description, threshold):
        """Process PDFs with ULTRA-AGGRESSIVE timeout protection."""
        batch_size = 25  # Reduced batch size for stability
        matches = []
        total_pdfs = len(pdf_file_paths)
        
        # Test mode: limit to first 100 PDFs for testing
        if hasattr(self, 'test_mode') and self.test_mode:
            pdf_file_paths = pdf_file_paths[:100]
            total_pdfs = len(pdf_file_paths)
            print(f"        🧪 TEST MODE: Processing only first {total_pdfs} PDFs")
        else:
            print(f"        📊 Processing all {total_pdfs} PDFs")
        
        import time
        overall_start_time = time.time()
        max_total_time = 7200  # 2 hours maximum total time (for large datasets)
        
        print(f"        ⏰ REASONABLE TIMEOUT: {max_total_time/60:.1f} minutes maximum")
        
        for batch_start in range(0, total_pdfs, batch_size):
            # Check overall timeout
            if time.time() - overall_start_time > max_total_time:
                print(f"        ⏰ OVERALL TIMEOUT: Exceeded {max_total_time/60:.1f} minutes total time, stopping")
                break
                
            batch_end = min(batch_start + batch_size, total_pdfs)
            batch_files = pdf_file_paths[batch_start:batch_end]
            
            print(f"        Processing batch {(batch_start//batch_size)+1}/{(total_pdfs+batch_size-1)//batch_size}")
            
            # Process batch with timeout
            batch_start_time = time.time()
            batch_matches = self.process_pdfs_parallel(batch_files, search_keywords, description, threshold)
            
            # Check if batch took too long
            batch_time = time.time() - batch_start_time
            if batch_time > 600:  # 10 minutes per batch max (reasonable for large batches)
                print(f"        ⏰ Batch took {batch_time:.1f}s, this batch is taking too long")
                print(f"        ⚠️ Continuing with next batch...")
                continue
            
            matches.extend(batch_matches)
            
            # Force cleanup after each batch
            import gc
            gc.collect()
            print(f"        🧹 Batch completed, memory cleaned")
        
        return matches

    def extract_keywords(self, description, category):
        """Extract keywords with optimized performance."""
        keywords = []
        
        try:
            # Add category keywords
            if category and str(category).strip():
                category_str = str(category).strip()
                category_keywords = category_str.lower().split()
                keywords.extend(category_keywords)
            
            # Add description keywords
            if description and str(description).strip():
                description_str = str(description).strip()
                # Reduced common words list and minimum word length for better matching
                common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                words = re.findall(r'\b\w+\b', description_str.lower())
                description_keywords = [word for word in words if word not in common_words and len(word) > 1]
                keywords.extend(description_keywords)
            
            # Remove duplicates
            unique_keywords = list(set(keywords))
            
            # If we have too many keywords, prioritize longer ones
            if len(unique_keywords) > 20:
                unique_keywords.sort(key=len, reverse=True)
                unique_keywords = unique_keywords[:20]
            
            return unique_keywords
        
        except Exception as e:
            return []

    def extract_pdf_text(self, pdf_path, timeout_seconds=30):
        """Extract text from a PDF, caching the result for the lifetime of this engine.

        The same PDF may be read by many items that share a supplier directory.
        Caching avoids redundant disk I/O and library overhead for those repeated lookups.
        Cache is evicted (oldest-first) when it reaches _PDF_CACHE_MAX entries.
        """
        if pdf_path in self._pdf_text_cache:
            return self._pdf_text_cache[pdf_path]

        text = self._extract_pdf_text_uncached(pdf_path, timeout_seconds)

        # Store result (evict oldest entry when at capacity)
        if len(self._pdf_text_cache) >= self._PDF_CACHE_MAX:
            self._pdf_text_cache.pop(next(iter(self._pdf_text_cache)))
        self._pdf_text_cache[pdf_path] = text
        return text

    def _extract_pdf_text_uncached(self, pdf_path, timeout_seconds=30):
        """Internal PDF extraction — use extract_pdf_text() which adds caching."""
        try:
            # Check if file exists and is readable
            if not os.path.exists(pdf_path):
                print(f"    ❌ File not found: {os.path.basename(pdf_path)}")
                return ""
            
            # Check file size - skip very large files that might be corrupted
            file_size = os.path.getsize(pdf_path)
            if file_size > 50 * 1024 * 1024:  # Reduced from 100MB to 50MB limit
                print(f"    ⚠️ Skipping large file ({file_size/1024/1024:.1f}MB): {os.path.basename(pdf_path)}")
                return ""
            
            if file_size == 0:
                print(f"    ❌ Empty file: {os.path.basename(pdf_path)}")
                return ""
            
            # Additional checks for problematic files
            filename = os.path.basename(pdf_path).lower()
            if any(skip_word in filename for skip_word in ['novaseq', 'concordance', 'app-note']):
                print(f"    ⚠️ Skipping potentially problematic file: {os.path.basename(pdf_path)}")
                return ""
            
            # Suppress PDF library warnings and cache messages
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            
            import logging
            logging.getLogger('pdfplumber').setLevel(logging.ERROR)
            
            # Handle timeout differently for Windows vs Unix systems
            if IS_WINDOWS:
                # Windows doesn't support SIGALRM, so we'll use a simpler approach with additional safeguards
                try:
                    # Try PyPDF2 first with page limit
                    with open(pdf_path, 'rb') as file:
                        reader = PdfReader(file)
                        
                        # Check if PDF is encrypted
                        if reader.is_encrypted:
                            print(f"    🔒 Encrypted PDF (skipping): {os.path.basename(pdf_path)}")
                            return ""
                        
                        # Limit pages to prevent hanging on large files
                        max_pages = 20  # Reduced from 50
                        total_pages = len(reader.pages)
                        if total_pages > max_pages:
                            print(f"    ⚠️ Large PDF ({total_pages} pages), limiting to first {max_pages} pages: {os.path.basename(pdf_path)}")
                        
                        text = ""
                        pages_to_process = min(total_pages, max_pages)
                        
                        for page_num in range(pages_to_process):
                            try:
                                page = reader.pages[page_num]
                                page_text = page.extract_text()
                                if page_text:
                                    text += page_text + " "
                                    
                                    # Limit text length to prevent memory issues
                                    if len(text) > 20000:  # Reduced from 50000 to 20KB
                                        print(f"    ⚠️ Text limit reached, stopping extraction: {os.path.basename(pdf_path)}")
                                        break
                                        
                            except Exception as e:
                                print(f"    ⚠️ Error on page {page_num + 1}: {e}")
                                continue
                    
                    if text.strip():
                        return text.strip()
                    
                    # Try pdfplumber as fallback with same safeguards
                    try:
                        with pdfplumber.open(pdf_path) as pdf:
                            text = ""
                            pages_to_process = min(len(pdf.pages), max_pages)
                            
                            for page_num in range(pages_to_process):
                                try:
                                    page = pdf.pages[page_num]
                                    # Try different extraction methods
                                    page_text = ""
                                    
                                    # Method 1: Standard text extraction
                                    try:
                                        page_text = page.extract_text()
                                    except:
                                        pass
                                    
                                    # Method 2: Extract words if standard method fails
                                    if not page_text:
                                        try:
                                            words = page.extract_words()
                                            page_text = " ".join([word['text'] for word in words if 'text' in word])
                                        except:
                                            pass
                                    
                                    # Method 3: Extract tables if other methods fail
                                    if not page_text:
                                        try:
                                            tables = page.extract_tables()
                                            for table in tables:
                                                for row in table:
                                                    for cell in row:
                                                        if cell:
                                                            page_text += str(cell) + " "
                                        except:
                                            pass
                                    
                                    if page_text:
                                        text += page_text + " "
                                        
                                        # Limit text length to prevent memory issues
                                        if len(text) > 20000:  # Reduced from 50000 to 20KB
                                            print(f"    ⚠️ Text limit reached, stopping extraction: {os.path.basename(pdf_path)}")
                                            break
                                            
                                except Exception as e:
                                    print(f"    ⚠️ Error on page {page_num + 1} (pdfplumber): {e}")
                                    continue
                        
                        if text.strip():
                            return text.strip()
                    except Exception as e:
                        print(f"    ⚠️ pdfplumber failed: {e}")
                    
                    return ""
                    
                except Exception as e:
                    print(f"    ❌ Error extracting text from {os.path.basename(pdf_path)}: {e}")
                    return ""
            else:
                # Unix/Linux systems can use SIGALRM
                try:
                    # Set up timeout handler
                    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout_seconds)
                    
                    try:
                        # Try PyPDF2 first with page limit
                        with open(pdf_path, 'rb') as file:
                            reader = PdfReader(file)
                            
                            # Check if PDF is encrypted
                            if reader.is_encrypted:
                                print(f"    🔒 Encrypted PDF (skipping): {os.path.basename(pdf_path)}")
                                return ""
                            
                            # Limit pages to prevent hanging on large files
                            max_pages = 20  # Reduced from 50
                            total_pages = len(reader.pages)
                            if total_pages > max_pages:
                                print(f"    ⚠️ Large PDF ({total_pages} pages), limiting to first {max_pages} pages: {os.path.basename(pdf_path)}")
                            
                            text = ""
                            pages_to_process = min(total_pages, max_pages)
                            
                            for page_num in range(pages_to_process):
                                try:
                                    page = reader.pages[page_num]
                                    page_text = page.extract_text()
                                    if page_text:
                                        text += page_text + " "
                                        
                                        # Limit text length to prevent memory issues
                                        if len(text) > 20000:  # Reduced from 50000 to 20KB
                                            print(f"    ⚠️ Text limit reached, stopping extraction: {os.path.basename(pdf_path)}")
                                            break
                                            
                                except Exception as e:
                                    print(f"    ⚠️ Error on page {page_num + 1}: {e}")
                                    continue
                        
                        if text.strip():
                            return text.strip()
                        
                        # Try pdfplumber as fallback with same safeguards
                        try:
                            with pdfplumber.open(pdf_path) as pdf:
                                text = ""
                                pages_to_process = min(len(pdf.pages), max_pages)
                                
                                for page_num in range(pages_to_process):
                                    try:
                                        page = pdf.pages[page_num]
                                        # Try different extraction methods
                                        page_text = ""
                                        
                                        # Method 1: Standard text extraction
                                        try:
                                            page_text = page.extract_text()
                                        except:
                                            pass
                                        
                                        # Method 2: Extract words if standard method fails
                                        if not page_text:
                                            try:
                                                words = page.extract_words()
                                                page_text = " ".join([word['text'] for word in words if 'text' in word])
                                            except:
                                                pass
                                        
                                        # Method 3: Extract tables if other methods fail
                                        if not page_text:
                                            try:
                                                tables = page.extract_tables()
                                                for table in tables:
                                                    for row in table:
                                                        for cell in row:
                                                            if cell:
                                                                page_text += str(cell) + " "
                                            except:
                                                pass
                                        
                                        if page_text:
                                            text += page_text + " "
                                            
                                            # Limit text length to prevent memory issues
                                            if len(text) > 20000:  # Reduced from 50000 to 20KB
                                                print(f"    ⚠️ Text limit reached, stopping extraction: {os.path.basename(pdf_path)}")
                                                break
                                                
                                    except Exception as e:
                                        print(f"    ⚠️ Error on page {page_num + 1} (pdfplumber): {e}")
                                        continue
                                
                                if text.strip():
                                    return text.strip()
                        except Exception as e:
                            print(f"    ⚠️ pdfplumber failed: {e}")
                        
                        return ""
                        
                    finally:
                        # Restore original signal handler and cancel alarm
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, original_handler)
                
                except TimeoutError:
                    print(f"    ⏰ Timeout processing PDF: {os.path.basename(pdf_path)}")
                    return ""
                except Exception as e:
                    print(f"    ❌ Error extracting text from {os.path.basename(pdf_path)}: {e}")
                    return ""
        
        except Exception as e:
            print(f"    ❌ Error extracting text from {os.path.basename(pdf_path)}: {e}")
            return ""
        
        # If we get here, no text was extracted
        print(f"    ⚠️ No text could be extracted from {os.path.basename(pdf_path)}")
        return ""

    def calculate_match_score(self, keywords, pdf_text, description, threshold=30):
        """Calculate match score with minimal output."""
        try:
            if not keywords or not pdf_text:
                return 0.0
            
            pdf_text_lower = pdf_text.lower()
            description_lower = description.lower()
            
            # Keyword matching (70% of score)
            keyword_score = 0.0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in pdf_text_lower:
                    matched_keywords.append(keyword)
            
            if keywords:
                keyword_score = (len(matched_keywords) / len(keywords)) * 70
            
            # Text similarity (30% of score) - limit text length for performance
            similarity_score = 0.0
            if description and pdf_text:
                # Limit text length to improve performance
                max_text_length = 500  # Reduced from 1000
                pdf_text_sample = pdf_text_lower[:max_text_length]
                similarity = SequenceMatcher(None, description_lower, pdf_text_sample).ratio()
                similarity_score = similarity * 30
            
            # Total score
            total_score = keyword_score + similarity_score
            final_score = min(total_score, 100.0)
            
            return final_score
        
        except Exception as e:
            return 0.0

    def cleanup_processes(self):
        """Enhanced process cleanup to prevent hanging."""
        print("🧹 Cleaning up processes...")
        
        if hasattr(self, 'parent_gui_processes'):
            for process in self.parent_gui_processes[:]:  # Iterate over copy
                try:
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=1)  # Short timeout
                        if process.is_alive():
                            process.kill()
                            process.join(timeout=0.5)
                except Exception as e:
                    print(f"⚠️ Error cleaning up process: {e}")
                finally:
                    # Remove from list regardless of outcome
                    if process in self.parent_gui_processes:
                        self.parent_gui_processes.remove(process)
        
        # Additional system-level cleanup
        if PSUTIL_AVAILABLE:
            try:
                current_pid = os.getpid()
                parent = psutil.Process(current_pid)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                        child.wait(timeout=1)
                    except:
                        try:
                            child.kill()
                        except:
                            pass
            except Exception as e:
                print(f"⚠️ System cleanup warning: {e}")
        
        # Force garbage collection
        import gc
        gc.collect()
        print("✅ Process cleanup completed")

    def export_results(self, output_file=None):
        """Export cross-reference results to Excel with clean format."""
        try:
            if not self.results:
                print("[WARNING] No cross-reference results to export.")
                return False
            
            # Create clean export data with only match results
            export_data = []
            total_pdfs = len(self.results)  # Total number of matches found
            
            for i, result in enumerate(self.results, 1):
                # Extract filename from full path
                pdf_filename = os.path.basename(result['Matched PDF'])
                
                # Create clean result entry
                export_data.append({
                    'Match Result': f"✅ MATCH! PDF {i}/{total_pdfs}: {pdf_filename} (Score: {result['Match Score']:.1f}%)",
                    'Item Code': result['Item Code'],
                    'Description': result['Description'],
                    'Category': result['Category'],
                    'PDF File': pdf_filename,
                    'Match Score (%)': result['Match Score'],
                    'Supplier': result['Supplier']
                })
            
            # Create DataFrame from clean data
            try:
                export_df = pd.DataFrame(export_data)
            except Exception as e:
                print(f"[ERROR] Failed to create DataFrame: {e}")
                return False
            
            # Generate filename if not provided
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"crossref_results_{timestamp}.xlsx"
            
            # Save to Excel
            try:
                export_df.to_excel(output_file, index=False, engine='openpyxl')
                print(f"[SUCCESS] Cross-reference results exported to: {output_file}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to save Excel file: {e}")
                return False
            
        except Exception as e:
            print(f"[ERROR] Failed to export results: {str(e)}")
            return False

def main():
    """Main function with simple GUI for file selection."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
        import threading
        import tkinter.ttk as ttk # Added for ProgressBar
        
        # Create simple GUI
        root = tk.Tk()
        root.title("Cross-Reference Standalone")
        root.geometry("800x600")
        
        # Handle window close - kill all processes
        def on_closing():
            nonlocal analysis_running, stop_analysis, current_processes
            if analysis_running:
                stop_analysis = True
                GlobalStopManager.set_stop_flag(True)
                analysis_running = False
                
                # Kill all child processes
                for process in current_processes:
                    try:
                        if process.is_alive():
                            process.terminate()
                            process.join(timeout=2)
                            if process.is_alive():
                                process.kill()
                    except:
                        pass
                
                # Force cleanup
                import gc
                gc.collect()
                
                print("🛑 All processes terminated due to window close")
            
            # Force terminate any remaining processes using psutil if available
            try:
                if PSUTIL_AVAILABLE:
                    current_pid = os.getpid()
                    parent = psutil.Process(current_pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                            child.wait(timeout=3)
                        except:
                            try:
                                child.kill()
                            except:
                                pass
            except:
                pass
            
            root.destroy()
            sys.exit(0)
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Variables with default values
        input_file_var = tk.StringVar(value="D:/SOM_in_labeled")
        master_file_var = tk.StringVar(value="D:/Masterlist")
        pdf_dir_var = tk.StringVar(value="D:/ScrapedPDFs")
        threshold_var = tk.IntVar(value=30)
        test_mode_var = tk.BooleanVar(value=False)
        high_performance_var = tk.BooleanVar(value=True)
        clean_output_var = tk.BooleanVar(value=True)  # Enable clean output by default
        
        # Analysis control
        analysis_running = False
        stop_analysis = False
        current_processes = []  # Track child processes for cleanup
        
        # GUI Layout
        tk.Label(root, text="Cross-Reference Standalone", font=("Arial", 16, "bold")).pack(pady=10)
        
        # File selection frame
        file_frame = tk.Frame(root)
        file_frame.pack(fill='x', padx=20, pady=5)
        
        # Input file selection
        tk.Label(file_frame, text="Input Excel File:").pack(anchor='w')
        input_frame = tk.Frame(file_frame)
        input_frame.pack(fill='x', pady=2)
        tk.Entry(input_frame, textvariable=input_file_var, width=60).pack(side='left')
        tk.Button(input_frame, text="Browse", command=lambda: input_file_var.set(filedialog.askopenfilename(initialdir="D:/SOM_in_labeled", filetypes=[("Excel files", "*.xlsx")]))).pack(side='right')
        
        # Master file selection
        tk.Label(file_frame, text="Master Excel File:").pack(anchor='w')
        master_frame = tk.Frame(file_frame)
        master_frame.pack(fill='x', pady=2)
        tk.Entry(master_frame, textvariable=master_file_var, width=60).pack(side='left')
        tk.Button(master_frame, text="Browse", command=lambda: master_file_var.set(filedialog.askopenfilename(initialdir="D:/Masterlist", filetypes=[("Excel files", "*.xlsx")]))).pack(side='right')
        
        # PDF directory selection
        tk.Label(file_frame, text="PDF Directory:").pack(anchor='w')
        pdf_frame = tk.Frame(file_frame)
        pdf_frame.pack(fill='x', pady=2)
        tk.Entry(pdf_frame, textvariable=pdf_dir_var, width=60).pack(side='left')
        tk.Button(pdf_frame, text="Browse", command=lambda: pdf_dir_var.set(filedialog.askdirectory(initialdir="D:/ScrapedPDFs"))).pack(side='right')
        
        # Threshold
        tk.Label(file_frame, text="Match Threshold (%):").pack(anchor='w')
        threshold_frame = tk.Frame(file_frame)
        threshold_frame.pack(fill='x', pady=2)
        tk.Entry(threshold_frame, textvariable=threshold_var, width=10).pack(side='left')
        
        # Test mode checkbox
        test_mode_frame = tk.Frame(file_frame)
        test_mode_frame.pack(fill='x', pady=2)
        tk.Checkbutton(test_mode_frame, variable=test_mode_var).pack(side='left')
        
        # High performance checkbox
        tk.Label(file_frame, text="Enable High Performance Mode:").pack(anchor='w')
        high_performance_frame = tk.Frame(file_frame)
        high_performance_frame.pack(fill='x', pady=2)
        tk.Checkbutton(high_performance_frame, variable=high_performance_var).pack(side='left')
        
        # Low CPU mode checkbox
        low_cpu_var = tk.BooleanVar(value=False)
        tk.Label(file_frame, text="Low CPU Mode (slower but uses less resources):").pack(anchor='w')
        low_cpu_frame = tk.Frame(file_frame)
        low_cpu_frame.pack(fill='x', pady=2)
        tk.Checkbutton(low_cpu_frame, variable=low_cpu_var).pack(side='left')
        
        # Clean output checkbox
        tk.Label(file_frame, text="Clean Output (Matches Only):").pack(anchor='w')
        clean_output_frame = tk.Frame(file_frame)
        clean_output_frame.pack(fill='x', pady=2)
        tk.Checkbutton(clean_output_frame, variable=clean_output_var).pack(side='left')
        
        # Output text area
        tk.Label(root, text="Analysis Output:", font=("Arial", 12, "bold")).pack(anchor='w', padx=20, pady=(10,5))
        output_text = scrolledtext.ScrolledText(root, height=15, width=80)
        output_text.pack(fill='both', expand=True, padx=20, pady=5)
        
        # Progress bar
        progress_frame = tk.Frame(root)
        progress_frame.pack(fill='x', padx=20, pady=5)
        progress_label = tk.Label(progress_frame, text="Ready", font=("Arial", 10))
        progress_label.pack(anchor='w')
        progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress_bar.pack(fill='x', pady=2)
        
        # Status label
        status_label = tk.Label(root, text="", font=("Arial", 9), fg="blue")
        status_label.pack(pady=2)
        
        # Control buttons frame
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)
        
        # Create a custom print function that writes to the text area with more frequent updates
        def gui_print(message):
            if 'stop_analysis' in locals() and stop_analysis:
                return
                
            output_text.insert(tk.END, message + "\n")
            output_text.see(tk.END)
            
            # Update status based on message content
            if "Processing item" in message:
                status_label.config(text="Processing items...", fg="blue")
            elif "Processing supplier" in message:
                status_label.config(text="Processing suppliers...", fg="blue")
            elif "Analyzing PDF" in message:
                status_label.config(text="Analyzing PDFs...", fg="blue")
            elif "✅ MATCH!" in message:
                status_label.config(text="Found matches!", fg="green")
            elif "❌ Error" in message:
                status_label.config(text="Error occurred", fg="red")
            elif "=== CROSS-REFERENCE ANALYSIS COMPLETE ===" in message:
                status_label.config(text="Analysis completed!", fg="green")
            elif "🛑 Analysis stopped" in message:
                status_label.config(text="Analysis stopped", fg="orange")
            
            # Force GUI update more frequently
            root.update_idletasks()
            root.update()
        
        # Define the analysis thread function at the main scope
        def run_analysis_thread(input_file, master_file, pdf_dir, threshold, test_mode, high_performance, low_cpu_mode, clean_output):
            nonlocal analysis_running, stop_analysis, current_processes
            try:
                gui_print("🔧 Analysis thread started")
                
                # Override print function
                import builtins
                original_print = builtins.print
                builtins.print = gui_print
                
                gui_print("🔧 Creating CrossReferenceEngine...")
                # Run analysis
                engine = CrossReferenceEngine()
                # Pass the stop_analysis attribute to the engine
                engine.stop_analysis = stop_analysis
                # Pass the process tracking list
                engine.parent_gui_processes = current_processes
                gui_print("🔧 Starting cross-reference analysis...")
                
                if high_performance:
                    gui_print("🚀 HIGH PERFORMANCE MODE ENABLED - Using parallel processing")
                    success = engine.run_cross_reference_high_performance(input_file, master_file, pdf_dir, threshold, test_mode, low_cpu_mode, clean_output)
                else:
                    gui_print("🐌 STANDARD MODE - Using sequential processing")
                    success = engine.run_cross_reference(input_file, master_file, pdf_dir, threshold, test_mode, clean_output)
                
                if not stop_analysis:
                    if success:
                        # Export results
                        export_success = engine.export_results()
                        if export_success:
                            messagebox.showinfo("Success", "Cross-reference analysis completed successfully!\nResults have been exported to Excel.")
                        else:
                            messagebox.showwarning("Warning", "Analysis completed but failed to export results.")
                    else:
                        messagebox.showerror("Error", "Cross-reference analysis failed.")
                else:
                    gui_print("🛑 Analysis was stopped by user")
                
                # Restore original print function
                builtins.print = original_print
                
            except Exception as e:
                gui_print(f"❌ Error: {e}")
                if not stop_analysis:
                    messagebox.showerror("Error", f"Analysis failed: {e}")
            finally:
                # Reset UI and cleanup processes
                analysis_running = False
                try:
                    engine.cleanup_processes()
                except:
                    pass
                current_processes.clear()
                progress_bar.stop()
                status_label.config(text="Ready", fg="black")
                run_button.config(state='normal')
                stop_button.config(state='disabled')
        
        # Stop button function
        def stop_analysis_func():
            nonlocal stop_analysis, analysis_running, current_processes
            if not analysis_running:
                messagebox.showwarning("Warning", "No analysis is currently running!")
                return
                
            stop_analysis = True
            GlobalStopManager.set_stop_flag(True)
            analysis_running = False
            
            # Kill all child processes
            for process in current_processes:
                try:
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=2)
                        if process.is_alive():
                            process.kill()
                except:
                    pass
            
            # Clear process list
            current_processes.clear()
            
            status_label.config(text="Stopping analysis...", fg="orange")
            progress_bar.stop()
            run_button.config(state='normal')
            stop_button.config(state='disabled')
            gui_print("🛑 Analysis stopped by user")
        
        # Run button
        def run_analysis():
            nonlocal analysis_running, stop_analysis
            if analysis_running:
                messagebox.showwarning("Warning", "Analysis is already running!")
                return
                
            # Clear output and reset UI
            output_text.delete(1.0, tk.END)
            progress_bar.start()
            status_label.config(text="Starting analysis...", fg="blue")
            analysis_running = True
            stop_analysis = False
            
            # Update button states
            run_button.config(state='disabled')
            stop_button.config(state='normal')
            
            input_file = input_file_var.get()
            master_file = master_file_var.get()
            pdf_dir = pdf_dir_var.get()
            threshold = threshold_var.get()
            test_mode = test_mode_var.get()
            high_performance = high_performance_var.get()
            
            if not all([input_file, master_file, pdf_dir]):
                messagebox.showerror("Error", "Please select all required files and directories.")
                progress_bar.stop()
                status_label.config(text="Ready", fg="black")
                analysis_running = False
                run_button.config(state='normal')
                stop_button.config(state='disabled')
                return
            
            # Add detailed validation feedback
            gui_print("=== STARTING ANALYSIS ===")
            gui_print(f"Input file: {input_file}")
            gui_print(f"Master file: {master_file}")
            gui_print(f"PDF directory: {pdf_dir}")
            gui_print(f"Threshold: {threshold}%")
            gui_print(f"Test Mode: {test_mode}")
            
            # Check if files exist
            if not os.path.exists(input_file):
                gui_print(f"❌ Input file not found: {input_file}")
                progress_bar.stop()
                status_label.config(text="Ready", fg="black")
                analysis_running = False
                run_button.config(state='normal')
                stop_button.config(state='disabled')
                return
            else:
                gui_print(f"✅ Input file exists: {os.path.getsize(input_file)} bytes")
            
            if not os.path.exists(master_file):
                gui_print(f"❌ Master file not found: {master_file}")
                progress_bar.stop()
                status_label.config(text="Ready", fg="black")
                analysis_running = False
                run_button.config(state='normal')
                stop_button.config(state='disabled')
                return
            else:
                gui_print(f"✅ Master file exists: {os.path.getsize(master_file)} bytes")
            
            if not os.path.exists(pdf_dir):
                gui_print(f"❌ PDF directory not found: {pdf_dir}")
                progress_bar.stop()
                status_label.config(text="Ready", fg="black")
                analysis_running = False
                run_button.config(state='normal')
                stop_button.config(state='disabled')
                return
            else:
                gui_print(f"✅ PDF directory exists")
                
                # Check PDF directory contents
                try:
                    pdf_contents = os.listdir(pdf_dir)
                    gui_print(f"📁 PDF directory contains: {pdf_contents}")
                    
                    # Count PDF files
                    pdf_files = [f for f in pdf_contents if f.lower().endswith('.pdf')]
                    gui_print(f"📄 Found {len(pdf_files)} PDF files directly in directory")
                    
                    # Check for supplier folders
                    supplier_folders = [d for d in pdf_contents if os.path.isdir(os.path.join(pdf_dir, d))]
                    gui_print(f"📂 Found {len(supplier_folders)} supplier folders: {supplier_folders}")
                    
                    if not supplier_folders:
                        gui_print("⚠️ No supplier folders found! Expected structure:")
                        gui_print("  PDFs/")
                        gui_print("  ├── Supplier1/")
                        gui_print("  │   ├── document1.pdf")
                        gui_print("  │   └── document2.pdf")
                        gui_print("  └── Supplier2/")
                        gui_print("      └── document3.pdf")
                        gui_print("")
                        gui_print("💡 TIP: Create supplier folders in your PDF directory")
                        gui_print("💡 TIP: Place PDF files inside supplier-named folders")
                        progress_bar.stop()
                        status_label.config(text="Ready", fg="black")
                        analysis_running = False
                        run_button.config(state='normal')
                        stop_button.config(state='disabled')
                        return
                    
                    # Check each supplier folder
                    total_pdfs = 0
                    for folder in supplier_folders:
                        folder_path = os.path.join(pdf_dir, folder)
                        folder_pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
                        gui_print(f"  📂 {folder}: {len(folder_pdfs)} PDF files")
                        total_pdfs += len(folder_pdfs)
                    
                    gui_print(f"📊 Total PDFs found: {total_pdfs}")
                    
                    if total_pdfs == 0:
                        gui_print("❌ No PDF files found in supplier folders!")
                        gui_print("💡 TIP: Add PDF files to your supplier folders")
                        progress_bar.stop()
                        status_label.config(text="Ready", fg="black")
                        analysis_running = False
                        run_button.config(state='normal')
                        stop_button.config(state='disabled')
                        return
                    
                    gui_print("✅ PDF directory validation completed successfully!")
                    gui_print("🚀 Starting cross-reference analysis...")
                    
                    # Start the analysis thread
                    low_cpu_mode = low_cpu_var.get()
                    thread = threading.Thread(target=run_analysis_thread, args=(input_file, master_file, pdf_dir, threshold, test_mode, high_performance, low_cpu_mode, clean_output_var.get()))
                    thread.daemon = True
                    thread.start()
                        
                except Exception as e:
                    gui_print(f"❌ Error reading PDF directory: {e}")
                    progress_bar.stop()
                    status_label.config(text="Ready", fg="black")
                    analysis_running = False
                    run_button.config(state='normal')
                    stop_button.config(state='disabled')
                    return
        
        # Create buttons
        run_button = tk.Button(button_frame, text="Run Cross-Reference Analysis", command=run_analysis, 
                              bg="green", fg="white", font=("Arial", 12, "bold"))
        run_button.pack(side='left', padx=5)
        
        stop_button = tk.Button(button_frame, text="Stop Analysis", command=stop_analysis_func,
                               bg="red", fg="white", font=("Arial", 12, "bold"), state='disabled')
        stop_button.pack(side='left', padx=5)
        
        # Save output button
        def save_output():
            try:
                output_content = output_text.get(1.0, tk.END)
                if not output_content.strip():
                    messagebox.showwarning("Warning", "No output to save!")
                    return
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_filename = f"analysis_output_{timestamp}.txt"
                
                filename = filedialog.asksaveasfilename(
                    initialdir="D:/SOM_in_labeled",
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile=default_filename
                )
                
                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(output_content)
                    messagebox.showinfo("Success", f"Output saved to: {filename}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save output: {e}")
        
        save_button = tk.Button(button_frame, text="Save Output", command=save_output,
                               bg="blue", fg="white", font=("Arial", 12, "bold"))
        save_button.pack(side='left', padx=5)
        
        # Test mode button
        def create_test_data():
            try:
                # Clear output area
                output_text.delete(1.0, tk.END)
                gui_print("🧪 Creating test data...")
                
                # Create test input file
                test_input_data = {
                    'Item Code': ['ITEM_001', 'ITEM_002', 'ITEM_003'],
                    'Item Description': ['Test Product 1', 'Test Product 2', 'Test Product 3'],
                    'Category': ['Electronics', 'Tools', 'Equipment'],
                    'Supplier Name': ['Test Supplier 1', 'Test Supplier 2', 'Test Supplier 1']
                }
                test_input_df = pd.DataFrame(test_input_data)
                test_input_file = "test_input.xlsx"
                test_input_df.to_excel(test_input_file, index=False)
                gui_print(f"✅ Created test input file: {test_input_file}")
                
                # Create test master file
                test_master_data = {
                    'Supplier Name': ['Test Supplier 1', 'Test Supplier 2'],
                    'Contact': ['contact1@test.com', 'contact2@test.com'],
                    'Address': ['123 Test St', '456 Test Ave']
                }
                test_master_df = pd.DataFrame(test_master_data)
                test_master_file = "test_master.xlsx"
                test_master_df.to_excel(test_master_file, index=False)
                gui_print(f"✅ Created test master file: {test_master_file}")
                
                # Create test PDF directory structure
                test_pdf_dir = "test_pdfs"
                if not os.path.exists(test_pdf_dir):
                    os.makedirs(test_pdf_dir)
                
                # Create supplier folders
                supplier1_dir = os.path.join(test_pdf_dir, "Test Supplier 1")
                supplier2_dir = os.path.join(test_pdf_dir, "Test Supplier 2")
                
                if not os.path.exists(supplier1_dir):
                    os.makedirs(supplier1_dir)
                if not os.path.exists(supplier2_dir):
                    os.makedirs(supplier2_dir)
                
                # Create dummy PDF files (text files with .pdf extension for testing)
                test_pdfs = [
                    (supplier1_dir, "product1_catalog.pdf"),
                    (supplier1_dir, "product1_specs.pdf"),
                    (supplier2_dir, "product2_catalog.pdf"),
                    (supplier2_dir, "product2_specs.pdf")
                ]
                
                for folder, filename in test_pdfs:
                    filepath = os.path.join(folder, filename)
                    with open(filepath, 'w') as f:
                        f.write(f"This is a test PDF file: {filename}\n")
                        f.write("Contains product information and specifications.\n")
                        f.write("Test Product 1 electronics equipment tools.\n")
                        f.write("Test Product 2 tools equipment electronics.\n")
                    gui_print(f"✅ Created test PDF: {filepath}")
                
                # Set the file paths in the GUI
                input_file_var.set(os.path.abspath(test_input_file))
                master_file_var.set(os.path.abspath(test_master_file))
                pdf_dir_var.set(os.path.abspath(test_pdf_dir))
                
                gui_print("✅ Test data created successfully!")
                gui_print("💡 You can now click 'Run Cross-Reference Analysis' to test the app")
                gui_print("💡 The test will process 3 items against 4 PDF files")
                
            except Exception as e:
                gui_print(f"❌ Error creating test data: {e}")
        
        test_button = tk.Button(button_frame, text="Create Test Data", command=create_test_data,
                               bg="orange", fg="white", font=("Arial", 12, "bold"))
        test_button.pack(side='left', padx=5)
        
        # Instructions
        instructions = """
Instructions:
1. Select your input Excel file (contains items to match)
2. Select your master Excel file (contains supplier information)  
3. Select your PDF directory (contains supplier folders with PDFs)
4. Set the match threshold (default: 30%)
5. Enable High Performance Mode for faster processing (recommended for large datasets)
7. Click "Run Cross-Reference Analysis"
8. Watch the output area for detailed progress information

Performance Tips:
- High Performance Mode uses parallel processing to utilize multiple CPU cores
- Recommended for processing thousands of PDFs
- Automatically adjusts worker count based on your system's CPU and RAM
- Can be 3-8x faster than standard mode depending on your hardware

Optional Enhancement:
- For better performance monitoring, install psutil: run 'install_psutil.bat' or 'python install_psutil.py'
- psutil provides accurate CPU and memory detection for optimal parallel processing
- The tool works without psutil but with enhanced detection when available
        """
        tk.Label(root, text=instructions, justify='left', font=("Arial", 9)).pack(pady=5)
        
        root.mainloop()
        
    except Exception as e:
        # Fallback to console if GUI fails
        print("=== STANDALONE CROSS-REFERENCE TEST ===")
        print(f"GUI failed to start: {e}")
        print("Please ensure you have the required files:")
        print("  - input.xlsx (input file)")
        print("  - master.xlsx (master file)")
        print("  - Test files/PDFs/ (PDF directory)")
        print("Then run the executable again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user (Ctrl+C)")
        sys.exit(0)
    except SystemExit:
        print("🛑 Application terminated")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Final cleanup - kill any remaining child processes
        try:
            if PSUTIL_AVAILABLE:
                current_pid = os.getpid()
                parent = psutil.Process(current_pid)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                        child.wait(timeout=1)
                    except:
                        try:
                            child.kill()
                        except:
                            pass
        except:
            pass 
