import sys
import os
import re
import threading
import time
import requests
import urllib.parse
from urllib.parse import urlparse, urljoin
from tkinter import Tk, Entry, Label, Text, Scrollbar, Button, END, filedialog, IntVar, Checkbutton, Frame, ttk, StringVar
from tkinter.ttk import Progressbar, Combobox, Treeview, Notebook
import pandas as pd
from bs4 import BeautifulSoup
import traceback
import socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
from difflib import SequenceMatcher
from PyPDF2 import PdfReader
import pdfplumber
from datetime import datetime
import psutil
import gc
import configparser
from dataclasses import dataclass

# Enhanced logging system
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_crawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def vv_log(message, level="info"):
    """Enhanced logging function with levels"""
    if level.lower() == "debug":
        logger.debug(message)
    elif level.lower() == "warning":
        logger.warning(message)
    elif level.lower() == "error":
        logger.error(message)
    else:
        logger.info(message)

vv_log("Starting application initialization...")

vv_log("All imports completed successfully")

# ---------------------------------------------------------------------------
# Verify that top-level imports succeeded (log only — no re-import needed)
# ---------------------------------------------------------------------------
for _mod_name, _obj in (
    ("pandas",        pd),
    ("BeautifulSoup", BeautifulSoup),
    ("PyPDF2",        PdfReader),
    ("pdfplumber",    pdfplumber),
    ("SequenceMatcher", SequenceMatcher),
    ("datetime",      datetime),
):
    vv_log(f"✅ {_mod_name} available")

# Memory monitoring functions
def monitor_memory():
    """Monitor current memory usage in MB"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    except Exception:
        return 0.0

def monitor_cpu():
    """Monitor current CPU usage percentage"""
    try:
        return psutil.cpu_percent(interval=0.1)
    except Exception:
        return 0.0

# Configuration management
@dataclass
class CrawlerConfig:
    max_concurrent: int = 3
    request_delay: float = 2.0
    page_timeout: int = 15
    max_pages_per_site: int = 50
    match_threshold: int = 60
    max_retries: int = 3
    backup_interval: int = 30  # minutes
    # PDF filtering settings
    max_pdf_size_mb: int = 100  # Increased from 50MB to 100MB
    min_pdf_size_bytes: int = 512  # Reduced from 1KB to 512 bytes
    min_text_length: int = 10  # Reduced from 50 to 10 characters
    strict_content_validation: bool = False  # Allow more file types
    
    @classmethod
    def from_file(cls, config_path="config.ini"):
        """Load configuration from file"""
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
        
        return cls(
            max_concurrent=config.getint('DEFAULT', 'max_concurrent', fallback=3),
            request_delay=config.getfloat('DEFAULT', 'request_delay', fallback=2.0),
            page_timeout=config.getint('DEFAULT', 'page_timeout', fallback=15),
            max_pages_per_site=config.getint('DEFAULT', 'max_pages_per_site', fallback=50),
            match_threshold=config.getint('DEFAULT', 'match_threshold', fallback=60),
            max_retries=config.getint('DEFAULT', 'max_retries', fallback=3),
            backup_interval=config.getint('DEFAULT', 'backup_interval', fallback=30),
            max_pdf_size_mb=config.getint('DEFAULT', 'max_pdf_size_mb', fallback=100),
            min_pdf_size_bytes=config.getint('DEFAULT', 'min_pdf_size_bytes', fallback=512),
            min_text_length=config.getint('DEFAULT', 'min_text_length', fallback=10),
            strict_content_validation=config.getboolean('DEFAULT', 'strict_content_validation', fallback=False)
        )
    
    def save_to_file(self, config_path="config.ini"):
        """Save configuration to file"""
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'max_concurrent': str(self.max_concurrent),
            'request_delay': str(self.request_delay),
            'page_timeout': str(self.page_timeout),
            'max_pages_per_site': str(self.max_pages_per_site),
            'match_threshold': str(self.match_threshold),
            'max_retries': str(self.max_retries),
            'backup_interval': str(self.backup_interval),
            'max_pdf_size_mb': str(self.max_pdf_size_mb),
            'min_pdf_size_bytes': str(self.min_pdf_size_bytes),
            'min_text_length': str(self.min_text_length),
            'strict_content_validation': str(self.strict_content_validation)
        }
        
        with open(config_path, 'w') as f:
            config.write(f)

# Rate-limited adapter for security and politeness
class RateLimitedAdapter(HTTPAdapter):
    """HTTP adapter with rate limiting to be respectful to websites"""
    def __init__(self, *args, **kwargs):
        self.last_request = 0
        self.min_interval = config.request_delay  # Minimum interval between requests
        super().__init__(*args, **kwargs)
    
    def send(self, request, **kwargs):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
        return super().send(request, **kwargs)

# Security and validation functions
def validate_url(url):
    """Validate URL for security"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        if not parsed.netloc:
            return False
        # Block localhost and private IPs for security
        if 'localhost' in parsed.netloc or '127.0.0.1' in parsed.netloc:
            return False
        return True
    except Exception:
        return False

def sanitize_path(path):
    """Sanitize file paths to prevent directory traversal"""
    import os.path
    # Remove any path traversal attempts
    path = path.replace('..', '').replace('/', '_').replace('\\', '_')
    # Remove or replace dangerous characters
    dangerous_chars = '<>:"|?*'
    for char in dangerous_chars:
        path = path.replace(char, '_')
    return path

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file for integrity checking"""
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return None

# Load configuration
config = CrawlerConfig.from_file()

MAX_CONCURRENT = config.max_concurrent
PAGE_TIMEOUT = config.page_timeout
REQUEST_DELAY = config.request_delay
MAX_PAGES_PER_SITE = config.max_pages_per_site

def check_single_instance():
    """Check if another instance is already running."""
    vv_log("Checking for single instance...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 12345))
        sock.close()
        vv_log("✅ Single instance check passed")
        return True
    except OSError:
        vv_log("❌ Another instance is already running")
        return False

class PDFCrawlerEnhancedApp:
    def __init__(self, master):
        vv_log("Initializing PDFCrawlerEnhancedApp...")
        self.master = master
        master.title("PDF Crawler & Manager - Enhanced")
        master.geometry("1200x800")
        
        # Set up cleanup on window close
        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        vv_log("Creating notebook for tabs...")
        # Create notebook for tabs
        self.notebook = Notebook(master)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.crawler_frame = Frame(self.notebook)
        self.overview_frame = Frame(self.notebook)
        self.crossref_frame = Frame(self.notebook)
        self.cleanup_frame = Frame(self.notebook)
        
        self.notebook.add(self.crawler_frame, text="Crawler")
        self.notebook.add(self.overview_frame, text="Overview")
        self.notebook.add(self.crossref_frame, text="Cross-Reference")
        self.notebook.add(self.cleanup_frame, text="Cleanup")
        
        vv_log("Setting up tabs...")
        # Initialize components
        self.setup_crawler_tab()
        self.setup_overview_tab()
        self.setup_crossref_tab()
        self.setup_cleanup_tab()
        
        # --- Internal state ---
        self.running = False
        self.visited = set()
        vv_log("Creating session...")
        self.session = self.create_session()
        self.download_folder = None
        self.start_time = None
        self.timer_running = False
        self.page_count = 0
        self.pdf_count = 0
        
        # Enhanced PDF Manager state
        self.vendor_data = {}
        self.pdf_directory = None
        self.input_excel = None
        self.master_excel = None
        self.crossref_results = {}
        
        # Statistics tracking
        self.stats_vars = {}
        
        vv_log("✅ PDFCrawlerEnhancedApp initialization complete")

    def create_session(self):
        """Create a secure, rate-limited requests session with enhanced retry strategy."""
        vv_log("Creating secure requests session...")
        session = requests.Session()
        
        # Configure enhanced retry strategy
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=1.5,  # Increased backoff
            status_forcelist=[429, 500, 502, 503, 504, 522, 524],
            allowed_methods=["GET", "POST"],
            raise_on_status=False
        )
        
        # Use rate-limited adapter for security and politeness
        adapter = RateLimitedAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Enable SSL verification for security
        session.verify = True
        
        # Set security-conscious headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',  # Do Not Track
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
        
        vv_log("✅ Secure, rate-limited session created successfully")
        return session
    
    def optimize_memory(self):
        """Clear unused variables and force garbage collection"""
        try:
            if hasattr(self, 'session'):
                self.session.close()
            if hasattr(self, 'vendor_data'):
                self.vendor_data.clear()
            gc.collect()
            vv_log("✅ Memory optimization completed")
        except Exception as e:
            vv_log(f"⚠️ Memory optimization warning: {e}")
    
    def setup_stats_panel(self, parent_frame):
        """Set up real-time statistics panel"""
        try:
            stats_frame = ttk.LabelFrame(parent_frame, text="Real-time Statistics")
            stats_frame.pack(fill='x', padx=5, pady=5)
            
            self.stats_vars = {
                'memory_usage': StringVar(value="Memory: -- MB"),
                'cpu_usage': StringVar(value="CPU: --%"),
                'active_threads': StringVar(value="Threads: 0"),
                'queue_size': StringVar(value="Queue: 0")
            }
            
            for stat_var in self.stats_vars.values():
                label = ttk.Label(stats_frame, textvariable=stat_var)
                label.pack(side='left', padx=10)
            
            # Start stats updates
            self.update_stats()
            vv_log("✅ Statistics panel setup complete")
            
        except Exception as e:
            vv_log(f"❌ Failed to setup stats panel: {e}")
    
    def update_stats(self):
        """Update real-time statistics"""
        try:
            if hasattr(self, 'stats_vars') and self.stats_vars:
                self.stats_vars['memory_usage'].set(f"Memory: {monitor_memory():.1f} MB")
                self.stats_vars['cpu_usage'].set(f"CPU: {monitor_cpu():.1f}%")
                self.stats_vars['active_threads'].set(f"Threads: {threading.active_count()}")
                
                if hasattr(self, 'visited'):
                    self.stats_vars['queue_size'].set(f"Visited: {len(self.visited)}")
                
                if self.running:
                    self.master.after(2000, self.update_stats)
        except Exception as e:
            vv_log(f"⚠️ Stats update warning: {e}")

    def setup_crawler_tab(self):
        vv_log("Setting up crawler tab...")
        # --- Crawler UI setup ---
        Label(self.crawler_frame, text="Input Excel:").grid(row=0, column=0, sticky='e')
        self.input_path = Entry(self.crawler_frame, width=40)
        self.input_path.grid(row=0, column=1, padx=5, pady=5)
        Button(self.crawler_frame, text="Browse...", command=self.browse_input).grid(row=0, column=2)

        Label(self.crawler_frame, text="Master List Excel:").grid(row=1, column=0, sticky='e')
        self.master_path = Entry(self.crawler_frame, width=40)
        self.master_path.grid(row=1, column=1, padx=5, pady=5)
        Button(self.crawler_frame, text="Browse...", command=self.browse_master).grid(row=1, column=2)

        Label(self.crawler_frame, text="PDF Download Folder:").grid(row=2, column=0, sticky='e')
        self.pdf_folder_path = Entry(self.crawler_frame, width=40)
        self.pdf_folder_path.grid(row=2, column=1, padx=5, pady=5)
        Button(self.crawler_frame, text="Browse...", command=self.browse_pdf_folder).grid(row=2, column=2)
        Button(self.crawler_frame, text="Create Default", command=self.create_default_pdf_folder).grid(row=2, column=3)

        self.verbose_var = IntVar(value=0)
        Checkbutton(self.crawler_frame, text="Verbose", variable=self.verbose_var).grid(row=3, column=0)

        self.clean_output_var = IntVar(value=1)
        Checkbutton(self.crawler_frame, text="Clean Output (Matches Only)", variable=self.clean_output_var).grid(row=3, column=1)

        self.skip_scanned_var = IntVar(value=1)
        Checkbutton(self.crawler_frame, text="Skip Already Scanned Vendors", variable=self.skip_scanned_var).grid(row=3, column=2)

        Label(self.crawler_frame, text="Max Concurrent:").grid(row=3, column=3, sticky='e')
        self.max_concurrent_var = IntVar(value=2)  # Reduced from 3 to 2
        self.max_concurrent_combo = Combobox(self.crawler_frame, textvariable=self.max_concurrent_var, values=['1', '2', '3', '5'], width=10, state='readonly')
        self.max_concurrent_combo.grid(row=3, column=4, padx=5, pady=5, sticky='w')
        self.max_concurrent_combo.set(2)

        self.run_button = Button(self.crawler_frame, text="Run Scraping", command=self.on_run_clicked)
        self.run_button.grid(row=4, column=1)
        self.stop_button = Button(self.crawler_frame, text="Stop Scraping", command=self.on_stop_clicked, state='disabled')
        self.stop_button.grid(row=4, column=2)
        self.export_missing_button = Button(self.crawler_frame, text="Export Missing Suppliers", command=self.export_missing_suppliers, state='disabled')
        self.export_missing_button.grid(row=4, column=3)

        self.timer_label = Label(self.crawler_frame, text="Elapsed: 00:00:00")
        self.timer_label.grid(row=4, column=4)

        # Add statistics panel
        self.setup_stats_panel(self.crawler_frame)

        self.progress = Progressbar(self.crawler_frame, orient='horizontal', length=300, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=4, padx=5, pady=(0,5))

        self.log_area = Text(self.crawler_frame, height=15, width=80)
        scrollbar = Scrollbar(self.crawler_frame, command=self.log_area.yview)
        self.log_area.configure(yscrollcommand=scrollbar.set)
        self.log_area.grid(row=6, column=0, columnspan=3, padx=5, pady=5)
        scrollbar.grid(row=6, column=3, sticky='ns')

        # Configure grid weights
        self.crawler_frame.grid_rowconfigure(6, weight=1)
        self.crawler_frame.grid_columnconfigure(1, weight=1)
        vv_log("✅ Crawler tab setup complete")

    def setup_overview_tab(self):
        vv_log("Setting up overview tab...")
        # --- Overview UI setup ---
        Label(self.overview_frame, text="PDF Directory:").grid(row=0, column=0, sticky='e')
        self.overview_pdf_folder_path = Entry(self.overview_frame, width=50)
        self.overview_pdf_folder_path.grid(row=0, column=1, padx=5, pady=5)
        Button(self.overview_frame, text="Browse...", command=self.browse_overview_pdf_folder).grid(row=0, column=2)
        Button(self.overview_frame, text="Scan Directory", command=self.scan_overview_directory).grid(row=0, column=3)

        # Control buttons
        Button(self.overview_frame, text="Show All Vendors", command=self.show_all_vendors).grid(row=1, column=0, pady=5)
        Button(self.overview_frame, text="Show Vendors with PDFs", command=self.show_vendors_with_pdfs).grid(row=1, column=1, pady=5)
        Button(self.overview_frame, text="Show Empty Vendors", command=self.show_empty_vendors).grid(row=1, column=2, pady=5)
        Button(self.overview_frame, text="Export Summary", command=self.export_summary).grid(row=1, column=3, pady=5)

        # Treeview for vendor list
        Label(self.overview_frame, text="Vendor List:").grid(row=2, column=0, sticky='w', pady=(10,0))
        
        self.overview_tree = Treeview(self.overview_frame, columns=('Vendor', 'PDF Count', 'Total Size', 'Last Modified'), show='headings', height=15)
        self.overview_tree.heading('Vendor', text='Vendor Name')
        self.overview_tree.heading('PDF Count', text='PDF Count')
        self.overview_tree.heading('Total Size', text='Total Size')
        self.overview_tree.heading('Last Modified', text='Last Modified')
        self.overview_tree.column('Vendor', width=200)
        self.overview_tree.column('PDF Count', width=100)
        self.overview_tree.column('Total Size', width=100)
        self.overview_tree.column('Last Modified', width=150)
        self.overview_tree.grid(row=3, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')

        # Scrollbar for treeview
        tree_scrollbar = Scrollbar(self.overview_frame, orient='vertical', command=self.overview_tree.yview)
        tree_scrollbar.grid(row=3, column=5, sticky='ns')
        self.overview_tree.configure(yscrollcommand=tree_scrollbar.set)

        # Overview log area
        self.overview_log_area = Text(self.overview_frame, height=8, width=80)
        overview_log_scrollbar = Scrollbar(self.overview_frame, command=self.overview_log_area.yview)
        self.overview_log_area.configure(yscrollcommand=overview_log_scrollbar.set)
        self.overview_log_area.grid(row=4, column=0, columnspan=4, padx=5, pady=5)
        overview_log_scrollbar.grid(row=4, column=4, sticky='ns')

        # Configure grid weights
        self.overview_frame.grid_rowconfigure(3, weight=1)
        self.overview_frame.grid_columnconfigure(1, weight=1)
        vv_log("✅ Overview tab setup complete")

    def setup_crossref_tab(self):
        vv_log("Setting up cross-reference tab...")
        # --- Cross-Reference UI setup ---
        Label(self.crossref_frame, text="Input Excel:").grid(row=0, column=0, sticky='e')
        self.crossref_input_excel_path = Entry(self.crossref_frame, width=50)
        self.crossref_input_excel_path.grid(row=0, column=1, padx=5, pady=5)
        Button(self.crossref_frame, text="Browse...", command=self.browse_crossref_input_excel).grid(row=0, column=2)

        Label(self.crossref_frame, text="Master List Excel:").grid(row=1, column=0, sticky='e')
        self.crossref_master_excel_path = Entry(self.crossref_frame, width=50)
        self.crossref_master_excel_path.grid(row=1, column=1, padx=5, pady=5)
        Button(self.crossref_frame, text="Browse...", command=self.browse_crossref_master_excel).grid(row=1, column=2)

        # PDF Directory selection
        Label(self.crossref_frame, text="PDF Directory:").grid(row=2, column=0, sticky='e')
        self.crossref_pdf_directory_path = Entry(self.crossref_frame, width=50)
        self.crossref_pdf_directory_path.grid(row=2, column=1, padx=5, pady=5)
        Button(self.crossref_frame, text="Browse...", command=self.browse_crossref_pdf_directory).grid(row=2, column=2)

        # Cross-reference controls
        Label(self.crossref_frame, text="Match Threshold (%):").grid(row=3, column=0, sticky='e')
        self.match_threshold_var = IntVar(value=60)
        threshold_entry = Entry(self.crossref_frame, textvariable=self.match_threshold_var, width=5)
        threshold_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        Button(self.crossref_frame, text="Run Cross-Reference", command=self.run_cross_reference).grid(row=3, column=2)
        Button(self.crossref_frame, text="Export Results", command=self.export_crossref_results).grid(row=3, column=3)

        # Results treeview
        Label(self.crossref_frame, text="Cross-Reference Results:").grid(row=4, column=0, sticky='w', pady=(10,0))
        
        self.crossref_tree = Treeview(self.crossref_frame, columns=('Item', 'Supplier', 'Description', 'Matched PDFs', 'Match Score'), show='headings', height=15)
        self.crossref_tree.heading('Item', text='Item')
        self.crossref_tree.heading('Supplier', text='Supplier')
        self.crossref_tree.heading('Description', text='Description')
        self.crossref_tree.heading('Matched PDFs', text='Matched PDFs')
        self.crossref_tree.heading('Match Score', text='Match Score')
        self.crossref_tree.column('Item', width=150)
        self.crossref_tree.column('Supplier', width=150)
        self.crossref_tree.column('Description', width=200)
        self.crossref_tree.column('Matched PDFs', width=150)
        self.crossref_tree.column('Match Score', width=100)
        self.crossref_tree.grid(row=5, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')

        # Scrollbar for crossref treeview
        crossref_tree_scrollbar = Scrollbar(self.crossref_frame, orient='vertical', command=self.crossref_tree.yview)
        crossref_tree_scrollbar.grid(row=5, column=5, sticky='ns')
        self.crossref_tree.configure(yscrollcommand=crossref_tree_scrollbar.set)

        # Cross-reference log area
        self.crossref_log_area = Text(self.crossref_frame, height=8, width=80)
        crossref_log_scrollbar = Scrollbar(self.crossref_frame, command=self.crossref_log_area.yview)
        self.crossref_log_area.configure(yscrollcommand=crossref_log_scrollbar.set)
        self.crossref_log_area.grid(row=6, column=0, columnspan=4, padx=5, pady=5)
        crossref_log_scrollbar.grid(row=6, column=4, sticky='ns')

        # Configure grid weights
        self.crossref_frame.grid_rowconfigure(5, weight=1)
        self.crossref_frame.grid_columnconfigure(1, weight=1)
        vv_log("✅ Cross-reference tab setup complete")

    def setup_cleanup_tab(self):
        vv_log("Setting up cleanup tab...")
        # --- Cleanup UI setup ---
        Label(self.cleanup_frame, text="PDF Directory:").grid(row=0, column=0, sticky='e')
        self.cleanup_pdf_folder_path = Entry(self.cleanup_frame, width=50)
        self.cleanup_pdf_folder_path.grid(row=0, column=1, padx=5, pady=5)
        Button(self.cleanup_frame, text="Browse...", command=self.browse_cleanup_pdf_folder).grid(row=0, column=2)
        Button(self.cleanup_frame, text="Scan Directory", command=self.scan_cleanup_directory).grid(row=0, column=3)

        # Cleanup options
        Label(self.cleanup_frame, text="Cleanup Options:").grid(row=1, column=0, sticky='w', pady=(10,0))
        
        self.enable_cleanup_var = IntVar(value=0)
        Checkbutton(self.cleanup_frame, text="Enable Cleanup", variable=self.enable_cleanup_var).grid(row=2, column=0)
        
        Label(self.cleanup_frame, text="Cleanup Age (days):").grid(row=2, column=1, sticky='e')
        self.cleanup_age_var = IntVar(value=30)
        cleanup_age_entry = Entry(self.cleanup_frame, textvariable=self.cleanup_age_var, width=5)
        cleanup_age_entry.grid(row=2, column=2, padx=5, pady=5, sticky='w')
        
        Button(self.cleanup_frame, text="Preview Cleanup", command=self.preview_cleanup).grid(row=2, column=3)
        Button(self.cleanup_frame, text="Run Cleanup", command=self.run_cleanup).grid(row=2, column=4)

        # Cleanup treeview
        Label(self.cleanup_frame, text="Files to Cleanup:").grid(row=3, column=0, sticky='w', pady=(10,0))
        
        self.cleanup_tree = Treeview(self.cleanup_frame, columns=('Vendor', 'File', 'Size', 'Modified', 'Age'), show='headings', height=15)
        self.cleanup_tree.heading('Vendor', text='Vendor')
        self.cleanup_tree.heading('File', text='File')
        self.cleanup_tree.heading('Size', text='Size')
        self.cleanup_tree.heading('Modified', text='Modified')
        self.cleanup_tree.heading('Age', text='Age (days)')
        self.cleanup_tree.column('Vendor', width=150)
        self.cleanup_tree.column('File', width=200)
        self.cleanup_tree.column('Size', width=100)
        self.cleanup_tree.column('Modified', width=150)
        self.cleanup_tree.column('Age', width=100)
        self.cleanup_tree.grid(row=4, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')

        # Scrollbar for cleanup treeview
        cleanup_tree_scrollbar = Scrollbar(self.cleanup_frame, orient='vertical', command=self.cleanup_tree.yview)
        cleanup_tree_scrollbar.grid(row=4, column=5, sticky='ns')
        self.cleanup_tree.configure(yscrollcommand=cleanup_tree_scrollbar.set)

        # Cleanup log area
        self.cleanup_log_area = Text(self.cleanup_frame, height=8, width=80)
        cleanup_log_scrollbar = Scrollbar(self.cleanup_frame, command=self.cleanup_log_area.yview)
        self.cleanup_log_area.configure(yscrollcommand=cleanup_log_scrollbar.set)
        self.cleanup_log_area.grid(row=5, column=0, columnspan=4, padx=5, pady=5)
        cleanup_log_scrollbar.grid(row=5, column=4, sticky='ns')

        # Configure grid weights
        self.cleanup_frame.grid_rowconfigure(4, weight=1)
        self.cleanup_frame.grid_columnconfigure(1, weight=1)
        vv_log("✅ Cleanup tab setup complete")

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.input_path.delete(0, END)
            self.input_path.insert(0, path)

    def browse_master(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.master_path.delete(0, END)
            self.master_path.insert(0, path)

    def browse_pdf_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.pdf_folder_path.delete(0, END)
            self.pdf_folder_path.insert(0, path)

    def create_default_pdf_folder(self):
        default_path = os.path.join(os.getcwd(), "downloaded_pdfs")
        self.pdf_folder_path.delete(0, END)
        self.pdf_folder_path.insert(0, default_path)

    # --- Enhanced PDF Manager Methods ---
    def browse_overview_pdf_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.overview_pdf_folder_path.delete(0, END)
            self.overview_pdf_folder_path.insert(0, path)
            self.pdf_directory = path

    def browse_crossref_input_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.crossref_input_excel_path.delete(0, END)
            self.crossref_input_excel_path.insert(0, path)
            self.input_excel = path

    def browse_crossref_master_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.crossref_master_excel_path.delete(0, END)
            self.crossref_master_excel_path.insert(0, path)
            self.master_excel = path

    def browse_crossref_pdf_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.crossref_pdf_directory_path.delete(0, END)
            self.crossref_pdf_directory_path.insert(0, path)

    def browse_cleanup_pdf_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.cleanup_pdf_folder_path.delete(0, END)
            self.cleanup_pdf_folder_path.insert(0, path)

    def scan_overview_directory(self):
        """Scan the PDF directory and populate vendor data."""
        directory = self.overview_pdf_folder_path.get().strip()
        if not directory:
            self.log_overview("[ERROR] Please select a PDF directory first.")
            return
        
        if not os.path.exists(directory):
            self.log_overview(f"[ERROR] Directory does not exist: {directory}")
            return
        
        self.pdf_directory = directory
        self.vendor_data.clear()
        
        try:
            self.log_overview(f"[INFO] Scanning directory: {directory}")
            
            for item in os.listdir(directory):
                vendor_path = os.path.join(directory, item)
                if os.path.isdir(vendor_path):
                    pdf_count = 0
                    total_size = 0
                    last_modified = None
                    
                    try:
                        for file in os.listdir(vendor_path):
                            if file.lower().endswith('.pdf'):
                                pdf_count += 1
                                file_path = os.path.join(vendor_path, file)
                                file_size = os.path.getsize(file_path)
                                total_size += file_size
                                
                                file_mtime = os.path.getmtime(file_path)
                                if last_modified is None or file_mtime > last_modified:
                                    last_modified = file_mtime
                    except (PermissionError, OSError) as e:
                        self.log_overview(f"[WARNING] Cannot access vendor folder {vendor_path}: {e}")
                        continue
                    
                    self.vendor_data[item] = {
                        'pdf_count': pdf_count,
                        'total_size': total_size,
                        'last_modified': last_modified,
                        'path': vendor_path
                    }
            
            self.log_overview(f"[INFO] Found {len(self.vendor_data)} vendor directories")
            self.populate_overview_treeview()
            
        except Exception as e:
            self.log_overview(f"[ERROR] Failed to scan directory: {e}")

    def populate_overview_treeview(self, filter_type='all'):
        """Populate the overview treeview with vendor data."""
        # Clear existing items
        for item in self.overview_tree.get_children():
            self.overview_tree.delete(item)
        
        for vendor_name, data in self.vendor_data.items():
            # Apply filters
            if filter_type == 'with_pdfs' and data['pdf_count'] == 0:
                continue
            elif filter_type == 'empty' and data['pdf_count'] > 0:
                continue
            
            # Format data for display
            pdf_count = str(data['pdf_count'])
            total_size_mb = f"{data['total_size'] / (1024*1024):.1f} MB" if data['total_size'] > 0 else "0 MB"
            
            if data['last_modified']:
                last_modified = datetime.fromtimestamp(data['last_modified']).strftime('%Y-%m-%d %H:%M')
            else:
                last_modified = "N/A"
            
            self.overview_tree.insert('', 'end', values=(vendor_name, pdf_count, total_size_mb, last_modified))

    def show_all_vendors(self):
        """Show all vendors in the treeview."""
        if not self.vendor_data:
            self.log_overview("[INFO] No vendor data available. Please scan directory first.")
            return
        self.populate_overview_treeview('all')
        self.log_overview(f"[INFO] Showing all {len(self.vendor_data)} vendors")

    def show_vendors_with_pdfs(self):
        """Show only vendors that have PDFs."""
        if not self.vendor_data:
            self.log_overview("[INFO] No vendor data available. Please scan directory first.")
            return
        self.populate_overview_treeview('with_pdfs')
        count = sum(1 for data in self.vendor_data.values() if data['pdf_count'] > 0)
        self.log_overview(f"[INFO] Showing {count} vendors with PDFs")

    def show_empty_vendors(self):
        """Show only vendors that have no PDFs."""
        if not self.vendor_data:
            self.log_overview("[INFO] No vendor data available. Please scan directory first.")
            return
        self.populate_overview_treeview('empty')
        count = sum(1 for data in self.vendor_data.values() if data['pdf_count'] == 0)
        self.log_overview(f"[INFO] Showing {count} empty vendors")

    def export_summary(self):
        """Export vendor summary to Excel."""
        if not self.vendor_data:
            self.log_overview("[ERROR] No vendor data available. Please scan directory first.")
            return
        
        try:
            # Prepare data for export
            export_data = []
            for vendor_name, data in self.vendor_data.items():
                last_modified = datetime.fromtimestamp(data['last_modified']).strftime('%Y-%m-%d %H:%M') if data['last_modified'] else "N/A"
                
                export_data.append({
                    'Vendor Name': vendor_name,
                    'PDF Count': data['pdf_count'],
                    'Total Size (MB)': round(data['total_size'] / (1024*1024), 2),
                    'Last Modified': last_modified
                })
            
            # Create DataFrame and export
            df = pd.DataFrame(export_data)
            filename = f"pdf_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            
            self.log_overview(f"[SUCCESS] Exported summary to: {filename}")
            
        except Exception as e:
            self.log_overview(f"[ERROR] Failed to export summary: {e}")

    def run_cross_reference(self):
        """Run cross-reference analysis with improved supplier mapping and error handling."""
        self.log_crossref("=== STARTING IMPROVED CROSS-REFERENCE ANALYSIS ===")
        self.crossref_log_area.see(END)  # Scroll to bottom
        self.master.update()  # Force GUI update
        
        try:
            # Get file paths
            self.log_crossref("Getting file paths...")
            self.crossref_log_area.see(END)
            self.master.update()
            
            input_file = self.crossref_input_excel_path.get().strip()
            master_file = self.crossref_master_excel_path.get().strip()
            pdf_dir = self.crossref_pdf_directory_path.get().strip()
            threshold = self.match_threshold_var.get()
            
            self.log_crossref(f"Input file: {input_file}")
            self.log_crossref(f"Master file: {master_file}")
            self.log_crossref(f"PDF directory: {pdf_dir}")
            self.log_crossref(f"Threshold: {threshold}%")
            self.crossref_log_area.see(END)
            self.master.update()
            
            # Validate inputs
            if not all([input_file, master_file, pdf_dir]):
                self.log_crossref("❌ Missing required inputs", "error")
                return
            
            # Validate files exist
            if not os.path.exists(input_file):
                self.log_crossref(f"❌ Input file not found: {input_file}", "error")
                return
            
            if not os.path.exists(master_file):
                self.log_crossref(f"❌ Master file not found: {master_file}", "error")
                return
            
            if not os.path.exists(pdf_dir):
                self.log_crossref(f"❌ PDF directory not found: {pdf_dir}", "error")
                return
            
            self.log_crossref("✅ File validation passed")
            self.crossref_log_area.see(END)
            self.master.update()
            
            # Load Excel files
            self.log_crossref("Loading input Excel file...")
            self.crossref_log_area.see(END)
            self.master.update()
            
            try:
                input_df = pd.read_excel(input_file, engine='openpyxl')
                self.log_crossref(f"✅ Input file loaded: {len(input_df)} rows")
                self.log_crossref(f"Input columns: {list(input_df.columns)}")
                self.crossref_log_area.see(END)
                self.master.update()
                
                # Limit items for testing (can be adjusted)
                max_items = 10  # Process 10 items at a time
                if len(input_df) > max_items:
                    self.log_crossref(f"⚠️ Limiting to first {max_items} items for testing")
                    input_df = input_df.head(max_items)
                    self.crossref_log_area.see(END)
                    self.master.update()
                
            except Exception as e:
                self.log_crossref(f"❌ Failed to load input file: {e}", "error")
                return
            
            self.log_crossref("Loading master Excel file...")
            self.crossref_log_area.see(END)
            self.master.update()
            
            try:
                master_df = pd.read_excel(master_file, engine='openpyxl')
                self.log_crossref(f"✅ Master file loaded: {len(master_df)} rows")
                self.crossref_log_area.see(END)
                self.master.update()
            except Exception as e:
                self.log_crossref(f"❌ Failed to load master file: {e}", "error")
                return
            
            # Initialize supplier mapping
            supplier_mapping = {
                '10X GENOMICS INC': 'ILLUMINA INC',
                'ADVANCED CELL DIAGNOSTICS INC': 'APPLIED SCIENTIFIC INSTRUMENTATION INC',
                'AGILENT TECHNOLOGIES INC': 'AGILENT TECHNOLOGIES INC',
                'AKOYA BIOSCIENCES INC': 'akoya biosciences inc',
                'FISHER SCIENTIFIC': 'FISHER SCIENTIFIC COMPANY LLC',
                'EPPENDORF': 'EPPENDORF NORTH AMERICA INC',
                'FUJIFILM': 'FUJIFILM SONOSITE INC',
                'KARL STORZ': 'KARL STORZ ENDOSCOPY-AMERICA INC',
                'OLYMPUS': 'OLYMPUS AMERICA INC',
                'PHILIPS': 'PHILIPS MEDICAL CAPITAL LLC',
                'STRYKER': 'STRYKER SALES LLC',
                'ZEISS': 'carl zeiss meditec usa inc',
                'GE HEALTHCARE': 'GE HEALTHCARE',
                'MOLECULAR DEVICES': 'MOLECULAR DEVICES LLC',
                'LIFE TECHNOLOGIES': 'LIFE TECHNOLOGIES CORPORATION',
                'NORPIX': 'NORPIX INC',
                'NANOSONICS': 'NANOSONICS INC',
                'NANOSURF': 'NANOSURF INC',
                'NEW SCALE': 'NEW SCALE TECHNOLOGIES INC',
                'PARKS MEDICAL': 'PARKS MEDICAL ELECTRONICS INC',
                'SECOND OPINION': 'SECOND OPINION TELEMEDICINE SOLUTIONS',
                'DAVID KOPF': 'DAVID KOPF INSTRUMENTS',
                'ECKERT & ZIEGLER': 'ECKERT & ZIEGLER RADIOPHARMA INC',
                'LABORIE': 'LABORIE MEDICAL TECHNOLOGIES CORP',
                'BMF PRECISION': 'BMF PRECISION INC',
                'CARESTREAM': 'carestream health',
                'FUS': 'FUS INSTRUMENTS INC',
                'HEIDELBERG': 'HEIDELBERG ENGINEERING INC',
                'IMEC': 'IMEC VZW',
                'KEYENCE': 'Keyence Corporation of America',
                'FORMULATRIX': 'FORMULATRIX LLC',
                'EVERBANK': 'EVERBANK',
                'BIOMARK': 'biomark llc',
                'ALPHA MEDICAL': 'alpha medical equipment of ny inc'
            }
            
            # Count PDFs
            self.log_crossref("Counting PDF files...")
            self.crossref_log_area.see(END)
            self.master.update()
            
            pdf_count = 0
            supplier_folders = []
            try:
                for root, dirs, files in os.walk(pdf_dir):
                    pdfs_in_dir = [f for f in files if f.lower().endswith('.pdf')]
                    if pdfs_in_dir:
                        folder_name = os.path.basename(root)
                        supplier_folders.append(folder_name)
                        pdf_count += len(pdfs_in_dir)
                        self.log_crossref(f"  Found {len(pdfs_in_dir)} PDFs in {folder_name}")
                        self.crossref_log_area.see(END)
                        self.master.update()
                
                self.log_crossref(f"Total PDF files found: {pdf_count}")
                self.crossref_log_area.see(END)
                self.master.update()
            except Exception as e:
                self.log_crossref(f"❌ Error counting PDFs: {e}", "error")
                return
            
            # Process items
            self.log_crossref(f"Processing {len(input_df)} items against {pdf_count} PDFs...")
            self.crossref_log_area.see(END)
            self.master.update()
            
            total_items = len(input_df)
            items_with_matches = 0
            total_matches = 0
            self.crossref_results = {}  # Store results for export
            
            for idx, item_row in input_df.iterrows():
                progress = ((idx+1)/total_items*100)
                self.log_crossref(f"Processing item {idx+1}/{total_items} ({progress:.1f}%)")
                self.crossref_log_area.see(END)
                self.master.update()
                
                try:
                    # Get raw values
                    raw_item_code = item_row.get('Item Code', '')
                    raw_description = item_row.get('Item Description', '')
                    raw_category = item_row.get('Category', '')
                    raw_supplier_name = item_row.get('Supplier Name', '')
                    
                    # Convert to strings
                    item_code = str(raw_item_code) if raw_item_code is not None else ''
                    description = str(raw_description) if raw_description is not None else ''
                    category = str(raw_category) if raw_category is not None else ''
                    supplier_name = str(raw_supplier_name) if raw_supplier_name is not None else ''
                    
                    # Skip empty items
                    if not description.strip():
                        continue
                    
                    # Find matching PDFs using improved method
                    matches = self.find_matching_pdfs_improved(item_code, description, category, supplier_name, pdf_dir, master_df, threshold, supplier_mapping)
                    
                    if matches:
                        items_with_matches += 1
                        total_matches += len(matches)
                        self.log_crossref(f"✅ Item {item_code}: Found {len(matches)} matches")
                        
                        # Store results
                        self.crossref_results[item_code] = {
                            'description': description,
                            'category': category,
                            'matches': matches
                        }
                    else:
                        self.log_crossref(f"❌ Item {item_code}: No matches")
                    
                    self.crossref_log_area.see(END)
                    self.master.update()
                
                except Exception as e:
                    self.log_crossref(f"❌ Error processing item {item_code}: {e}", "error")
                    continue
            
            # Final summary
            self.log_crossref("=== CROSS-REFERENCE ANALYSIS COMPLETE ===")
            self.log_crossref(f"Total items processed: {total_items}")
            self.log_crossref(f"Items with matches: {items_with_matches}")
            self.log_crossref(f"Total matches found: {total_matches}")
            
            if total_items > 0:
                avg_matches = total_matches / total_items
                self.log_crossref(f"Average matches per item: {avg_matches:.1f}")
            
            self.log_crossref("✅ Cross-reference analysis completed successfully")
            self.crossref_log_area.see(END)
            self.master.update()
            
            # Create backup log for cross-reference operation
            pdf_dir = self.crossref_pdf_directory_path.get().strip()
            if pdf_dir and os.path.exists(pdf_dir):
                log_content = self.get_current_log_content(self.crossref_log_area)
                self.create_backup_log(pdf_dir, log_content, "crossreference")
            
            # Update results display
            self.populate_crossref_results()
            
        except Exception as e:
            self.log_crossref(f"❌ Cross-reference analysis failed: {e}", "error")
            traceback.print_exc()
            
            # Create backup log for error case
            pdf_dir = self.crossref_pdf_directory_path.get().strip()
            if pdf_dir and os.path.exists(pdf_dir):
                log_content = self.get_current_log_content(self.crossref_log_area)
                self.create_backup_log(pdf_dir, log_content, "crossreference_error")

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

    def find_matching_pdfs_improved(self, item_code, description, category, supplier_name, pdf_dir, master_df, threshold, supplier_mapping):
        """Find matching PDFs with improved supplier mapping and error handling."""
        matches = []
        
        try:
            # Extract keywords
            search_keywords = self.extract_keywords(description, category)
            
            if not search_keywords:
                return matches
            
            if not supplier_name:
                self.log_crossref(f"    ❌ No supplier name found for item")
                self.crossref_log_area.see(END)
                self.master.update()
                return matches
            
            self.log_crossref(f"    Looking for supplier: {supplier_name}")
            self.crossref_log_area.see(END)
            self.master.update()
            
            # Try to map the supplier name to a PDF folder
            pdf_folder_name = supplier_name
            if supplier_name in supplier_mapping:
                pdf_folder_name = supplier_mapping[supplier_name]
                self.log_crossref(f"    Mapped '{supplier_name}' to '{pdf_folder_name}'")
                self.crossref_log_area.see(END)
                self.master.update()
            
            # Check if supplier folder exists
            supplier_path = os.path.join(pdf_dir, pdf_folder_name)
            if not os.path.exists(supplier_path):
                self.log_crossref(f"    ❌ Supplier folder not found: {pdf_folder_name}")
                # Try to find a similar folder name
                available_folders = [d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]
                self.log_crossref(f"    Available folders: {available_folders[:5]}...")  # Show first 5
                self.crossref_log_area.see(END)
                self.master.update()
                return matches
            
            self.log_crossref(f"    ✅ Found supplier folder: {pdf_folder_name}")
            self.crossref_log_area.see(END)
            self.master.update()
            
            # Get PDF files in supplier folder
            pdf_files = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
            
            if not pdf_files:
                self.log_crossref(f"      ❌ No PDF files in {supplier_name}")
                self.crossref_log_area.see(END)
                self.master.update()
                return matches
            
            # Process all PDFs from this supplier
            self.log_crossref(f"      Processing ALL {len(pdf_files)} PDFs from {supplier_name}...")
            self.crossref_log_area.see(END)
            self.master.update()
            
            # Process each PDF
            for pdf_idx, pdf_file in enumerate(pdf_files):
                self.log_crossref(f"        PDF {pdf_idx + 1}/{len(pdf_files)}: {pdf_file}")
                self.crossref_log_area.see(END)
                self.master.update()
                
                try:
                    pdf_path = os.path.join(supplier_path, pdf_file)
                    
                    # Extract text from PDF
                    self.log_crossref(f"          Extracting text...")
                    self.crossref_log_area.see(END)
                    self.master.update()
                    
                    pdf_text = self.extract_pdf_text(pdf_path)
                    self.log_crossref(f"          Extracted {len(pdf_text)} characters")
                    self.crossref_log_area.see(END)
                    self.master.update()
                    
                    if not pdf_text:
                        self.log_crossref(f"          ❌ No text extracted")
                        self.crossref_log_area.see(END)
                        self.master.update()
                        continue
                    
                    # Calculate match score
                    self.log_crossref(f"          Calculating match score...")
                    self.crossref_log_area.see(END)
                    self.master.update()
                    
                    score = self.calculate_match_score(search_keywords, pdf_text, description)
                    self.log_crossref(f"          Score: {score:.1f}% (threshold: {threshold}%)")
                    self.crossref_log_area.see(END)
                    self.master.update()
                    
                    if score >= threshold:
                        self.log_crossref(f"          ✅ MATCH! Score {score:.1f}% >= {threshold}%")
                        matches.append({
                            'supplier': supplier_name,  # Keep original supplier name
                            'pdf_folder': pdf_folder_name,  # Add PDF folder name
                            'pdf_file': pdf_file,
                            'score': score,
                            'text': pdf_text[:200] + '...' if len(pdf_text) > 200 else pdf_text
                        })
                    else:
                        self.log_crossref(f"          ❌ No match (score {score:.1f}% < {threshold}%)")
                    
                    self.crossref_log_area.see(END)
                    self.master.update()
                
                except Exception as e:
                    self.log_crossref(f"          ❌ Error processing PDF {pdf_file}: {e}")
                    self.crossref_log_area.see(END)
                    self.master.update()
                    continue
            
            self.log_crossref(f"    Found {len(matches)} total matches")
            self.crossref_log_area.see(END)
            self.master.update()
            
        except Exception as e:
            self.log_crossref(f"❌ Error in find_matching_pdfs_improved: {e}")
            self.crossref_log_area.see(END)
            self.master.update()
        
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
        """Enhanced PDF text extraction with multiple fallback methods."""
        vv_log(f"          Extracting text from: {os.path.basename(pdf_path)}")
        
        methods = [
            self._extract_with_pypdf2,
            self._extract_with_pdfplumber,
        ]
        
        for method in methods:
            try:
                text = method(pdf_path)
                if text and len(text.strip()) > config.min_text_length:  # Configurable text threshold
                    return text
            except Exception as e:
                vv_log(f"          ⚠️ Method failed: {e}")
                continue
        
        vv_log("          ❌ All extraction methods failed")
        return ""
    
    def _extract_with_pypdf2(self, pdf_path, timeout_seconds=30):
        """Extract text using PyPDF2 with a hard timeout to prevent hangs."""
        vv_log("          Trying PyPDF2...")

        result_holder = [None]
        error_holder  = [None]

        def _worker():
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PdfReader(file)
                    text = "".join(
                        (page.extract_text() or "") + " "
                        for page in reader.pages
                    )
                result_holder[0] = text.strip()
            except FileNotFoundError:
                vv_log(f"          ❌ PDF file not found: {pdf_path}", "error")
            except PermissionError:
                vv_log(f"          ❌ Permission denied accessing: {pdf_path}", "error")
            except Exception as e:
                error_holder[0] = e

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        worker.join(timeout=timeout_seconds)

        if worker.is_alive():
            vv_log(f"          ⚠️ PyPDF2 timed out after {timeout_seconds}s — skipping", "warning")
            return ""

        if error_holder[0]:
            vv_log(f"          ❌ PyPDF2 extraction failed: {error_holder[0]}", "error")
            return ""

        text = result_holder[0] or ""
        if text:
            vv_log(f"          ✅ PyPDF2 extracted {len(text)} characters")
        return text
    
    def _extract_with_pdfplumber(self, pdf_path):
        """Extract text using pdfplumber"""
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
        return ""

    def calculate_match_score(self, keywords, pdf_text, description):
        """Enhanced match scoring algorithm with semantic similarity."""
        vv_log("          Calculating advanced match score...")
        
        try:
            if not keywords or not pdf_text:
                vv_log("          ❌ No keywords or PDF text available")
                return 0.0
            
            pdf_text_lower = pdf_text.lower()
            description_lower = description.lower()
            
            scores = {}
            
            # 1. Keyword frequency scoring (40%)
            keyword_score = self._calculate_keyword_frequency(keywords, pdf_text_lower)
            scores['keyword'] = keyword_score * 0.4
            vv_log(f"          Keyword score: {keyword_score:.1f}% -> {scores['keyword']:.1f}%")
            
            # 2. Semantic similarity (30%)
            semantic_score = self._calculate_semantic_similarity(description_lower, pdf_text_lower)
            scores['semantic'] = semantic_score * 0.3
            vv_log(f"          Semantic score: {semantic_score:.1f}% -> {scores['semantic']:.1f}%")
            
            # 3. Structural matching (20%)
            structural_score = self._check_structural_elements(description_lower, pdf_text_lower)
            scores['structural'] = structural_score * 0.2
            vv_log(f"          Structural score: {structural_score:.1f}% -> {scores['structural']:.1f}%")
            
            # 4. Metadata analysis (10%)
            metadata_score = self._analyze_metadata_similarity(description_lower, pdf_text_lower)
            scores['metadata'] = metadata_score * 0.1
            vv_log(f"          Metadata score: {metadata_score:.1f}% -> {scores['metadata']:.1f}%")
            
            total_score = sum(scores.values())
            
            # Boost scores for exact matches
            if self._has_exact_match(description_lower, pdf_text_lower):
                total_score = min(total_score * 1.3, 100.0)
                vv_log(f"          ✅ Exact match bonus applied!")
            
            final_score = min(total_score, 100.0)
            vv_log(f"          Final score: {final_score:.1f}%")
            
            return final_score
        
        except Exception as e:
            vv_log(f"          ❌ Error calculating match score: {e}")
            return 0.0
    
    def _calculate_keyword_frequency(self, keywords, pdf_text):
        """Calculate keyword frequency score"""
        matched_keywords = 0
        matched_keyword_list = []
        
        for keyword in keywords:
            if keyword in pdf_text:
                matched_keywords += 1
                matched_keyword_list.append(keyword)
        
        if keywords:
            score = (matched_keywords / len(keywords)) * 100
            vv_log(f"          Keywords: {matched_keywords}/{len(keywords)} matched: {matched_keyword_list}")
            return score
        return 0.0
    
    def _calculate_semantic_similarity(self, text1, text2):
        """Calculate semantic similarity using sequence matching"""
        try:
            # Use TF-IDF-like approach with sequence matcher
            similarity = SequenceMatcher(None, text1, text2[:2000]).ratio()
            return similarity * 100
        except Exception:
            return 0.0
    
    def _check_structural_elements(self, description, pdf_text):
        """Check for structural elements like model numbers, part numbers"""
        try:
            # Look for alphanumeric patterns that might be model/part numbers
            import re
            desc_patterns = re.findall(r'\b[A-Z0-9]{3,}\b', description.upper())
            pdf_patterns = re.findall(r'\b[A-Z0-9]{3,}\b', pdf_text.upper())
            
            if not desc_patterns:
                return 0.0
            
            matches = len(set(desc_patterns) & set(pdf_patterns))
            return (matches / len(desc_patterns)) * 100 if desc_patterns else 0.0
        except Exception:
            return 0.0
    
    def _analyze_metadata_similarity(self, description, pdf_text):
        """Analyze metadata-like similarity"""
        try:
            # Simple word overlap analysis
            desc_words = set(description.split())
            pdf_words = set(pdf_text[:1000].split())
            
            if not desc_words:
                return 0.0
            
            overlap = len(desc_words & pdf_words)
            return (overlap / len(desc_words)) * 100
        except Exception:
            return 0.0
    
    def _has_exact_match(self, description, pdf_text):
        """Check for exact phrase matches"""
        try:
            # Check if key phrases from description appear exactly in PDF
            key_phrases = [phrase.strip() for phrase in description.split(',')]
            for phrase in key_phrases:
                if len(phrase) > 5 and phrase in pdf_text:
                    return True
            return False
        except Exception:
            return False

    def export_crossref_results(self):
        """Export comprehensive cross-reference results with enhanced reporting."""
        try:
            if not hasattr(self, 'crossref_results') or not self.crossref_results:
                self.log_crossref("No cross-reference results to export.", "warning")
                return
            
            # Generate comprehensive report
            report_data = self._generate_comprehensive_report()
            
            # Export to multiple formats
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export detailed results to Excel
            self._export_report_excel(report_data, timestamp)
            
            # Export summary to JSON
            self._export_report_json(report_data, timestamp)
            
            # Export HTML report with charts
            self._export_report_html(report_data, timestamp)
            
            self.log_crossref(f"✅ Comprehensive reports exported with timestamp: {timestamp}")
            vv_log(f"✅ Comprehensive reports exported with timestamp: {timestamp}")
            
        except Exception as e:
            self.log_crossref(f"❌ Failed to export results: {str(e)}", "error")
            vv_log(f"❌ Failed to export results: {str(e)}")
            traceback.print_exc()
    
    def _generate_comprehensive_report(self):
        """Generate comprehensive analysis report"""
        report_data = {
            'summary': self._get_crawling_summary(),
            'vendor_analysis': self._get_vendor_analysis(),
            'match_analysis': self._get_match_analysis(),
            'performance_metrics': self._get_performance_metrics(),
            'recommendations': self._get_recommendations()
        }
        return report_data
    
    def _get_crawling_summary(self):
        """Get crawling summary statistics"""
        total_items = len(self.crossref_results) if hasattr(self, 'crossref_results') else 0
        items_with_matches = sum(1 for result in self.crossref_results.values() if result.get('matches')) if hasattr(self, 'crossref_results') else 0
        total_matches = sum(len(result.get('matches', [])) for result in self.crossref_results.values()) if hasattr(self, 'crossref_results') else 0
        
        return {
            'total_items_processed': total_items,
            'items_with_matches': items_with_matches,
            'items_without_matches': total_items - items_with_matches,
            'total_matches_found': total_matches,
            'average_matches_per_item': total_matches / total_items if total_items > 0 else 0,
            'match_rate_percentage': (items_with_matches / total_items * 100) if total_items > 0 else 0
        }
    
    def _get_vendor_analysis(self):
        """Get vendor-specific analysis"""
        vendor_stats = {}
        if hasattr(self, 'crossref_results'):
            for result in self.crossref_results.values():
                for match in result.get('matches', []):
                    supplier = match.get('supplier', 'Unknown')
                    if supplier not in vendor_stats:
                        vendor_stats[supplier] = {'matches': 0, 'avg_score': 0, 'scores': []}
                    vendor_stats[supplier]['matches'] += 1
                    vendor_stats[supplier]['scores'].append(match.get('score', 0))
            
            # Calculate averages
            for supplier, stats in vendor_stats.items():
                if stats['scores']:
                    stats['avg_score'] = sum(stats['scores']) / len(stats['scores'])
                    stats['max_score'] = max(stats['scores'])
                    stats['min_score'] = min(stats['scores'])
                del stats['scores']  # Remove raw scores from final report
        
        return vendor_stats
    
    def _get_match_analysis(self):
        """Get match quality analysis"""
        score_ranges = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '<60': 0}
        all_scores = []
        
        if hasattr(self, 'crossref_results'):
            for result in self.crossref_results.values():
                for match in result.get('matches', []):
                    score = match.get('score', 0)
                    all_scores.append(score)
                    
                    if score >= 90:
                        score_ranges['90-100'] += 1
                    elif score >= 80:
                        score_ranges['80-89'] += 1
                    elif score >= 70:
                        score_ranges['70-79'] += 1
                    elif score >= 60:
                        score_ranges['60-69'] += 1
                    else:
                        score_ranges['<60'] += 1
        
        return {
            'score_distribution': score_ranges,
            'average_score': sum(all_scores) / len(all_scores) if all_scores else 0,
            'highest_score': max(all_scores) if all_scores else 0,
            'lowest_score': min(all_scores) if all_scores else 0
        }
    
    def _get_performance_metrics(self):
        """Get performance metrics"""
        return {
            'memory_usage_mb': monitor_memory(),
            'cpu_usage_percent': monitor_cpu(),
            'active_threads': threading.active_count(),
            'processing_time': time.time() - (self.start_time if self.start_time else time.time())
        }
    
    def _get_recommendations(self):
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if hasattr(self, 'crossref_results'):
            summary = self._get_crawling_summary()
            match_analysis = self._get_match_analysis()
            
            if summary['match_rate_percentage'] < 50:
                recommendations.append("Low match rate detected. Consider reviewing keyword extraction or lowering match threshold.")
            
            if match_analysis['average_score'] < 70:
                recommendations.append("Average match scores are low. Consider improving PDF text extraction or match algorithms.")
            
            if summary['total_items_processed'] > 100 and summary['average_matches_per_item'] < 1:
                recommendations.append("Few matches per item. Consider expanding PDF collection or improving supplier mapping.")
        
        return recommendations
    
    def _export_report_excel(self, report_data, timestamp):
        """Export detailed Excel report"""
        # Create export data
        export_data = []
        
        for item_code, result in self.crossref_results.items():
            if result['matches']:
                # Sort matches by score
                sorted_matches = sorted(result['matches'], key=lambda x: x['score'], reverse=True)
                
                for match in sorted_matches:
                    export_data.append({
                        'Item Code': item_code,
                        'Description': result['description'],
                        'Category': result['category'],
                        'Supplier': match['supplier'],
                        'PDF Folder': match['pdf_folder'],
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
                    'PDF Folder': '',
                    'PDF File': '',
                    'Match Score (%)': 0.0,
                    'PDF Text Preview': ''
                })
        
        # Create DataFrame and export
        export_df = pd.DataFrame(export_data)
        output_file = f"crossref_detailed_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Detailed Results', index=False)
            
            # Add summary sheet
            summary_df = pd.DataFrame([report_data['summary']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add vendor analysis sheet
            if report_data['vendor_analysis']:
                vendor_df = pd.DataFrame.from_dict(report_data['vendor_analysis'], orient='index')
                vendor_df.to_excel(writer, sheet_name='Vendor Analysis')
        
        self.log_crossref(f"📊 Detailed Excel report: {output_file}")
    
    def _export_report_json(self, report_data, timestamp):
        """Export JSON summary report"""
        import json
        output_file = f"crossref_summary_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.log_crossref(f"📄 JSON summary report: {output_file}")
    
    def _export_report_html(self, report_data, timestamp):
        """Export interactive HTML report"""
        output_file = f"crossref_report_{timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PDF Crawler Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .recommendation {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>PDF Crawler Analysis Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Summary Statistics</h2>
                <div class="metric">Items Processed: {report_data['summary']['total_items_processed']}</div>
                <div class="metric">Match Rate: {report_data['summary']['match_rate_percentage']:.1f}%</div>
                <div class="metric">Total Matches: {report_data['summary']['total_matches_found']}</div>
                <div class="metric">Avg Score: {report_data['match_analysis']['average_score']:.1f}</div>
            </div>
            
            <h2>Recommendations</h2>
            {''.join(f'<div class="recommendation">• {rec}</div>' for rec in report_data['recommendations'])}
            
            <h2>Performance Metrics</h2>
            <div class="summary">
                <div class="metric">Memory: {report_data['performance_metrics']['memory_usage_mb']:.1f} MB</div>
                <div class="metric">CPU: {report_data['performance_metrics']['cpu_usage_percent']:.1f}%</div>
                <div class="metric">Processing Time: {report_data['performance_metrics']['processing_time']:.1f}s</div>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.log_crossref(f"🌐 HTML report: {output_file}")

    def scan_cleanup_directory(self):
        """Scan directory for files that can be cleaned up."""
        try:
            pdf_dir = self.cleanup_pdf_folder_path.get().strip()
            
            if not pdf_dir:
                self.log_cleanup("[ERROR] Please select a PDF directory.")
                return
            
            if not os.path.exists(pdf_dir):
                self.log_cleanup(f"[ERROR] Directory not found: {pdf_dir}")
                return
            
            # Clear previous results
            self.cleanup_tree.delete(*self.cleanup_tree.get_children())
            
            self.log_cleanup("[INFO] Scanning directory for cleanup candidates...")
            
            # Scan all PDF files
            cleanup_candidates = []
            current_time = datetime.now()
            
            for root, dirs, files in os.walk(pdf_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            # Get file stats
                            stat = os.stat(file_path)
                            modified_time = datetime.fromtimestamp(stat.st_mtime)
                            file_age = (current_time - modified_time).days
                            file_size = stat.st_size
                            
                            # Get vendor name from path
                            vendor = os.path.basename(os.path.dirname(file_path))
                            
                            cleanup_candidates.append({
                                'vendor': vendor,
                                'file': file,
                                'path': file_path,
                                'size': file_size,
                                'modified': modified_time,
                                'age': file_age
                            })
                            
                        except Exception as e:
                            continue
            
            # Store candidates for later use
            self.cleanup_candidates = cleanup_candidates
            
            self.log_cleanup(f"[INFO] Found {len(cleanup_candidates)} PDF files for analysis")
            
        except Exception as e:
            self.log_cleanup(f"[ERROR] Failed to scan directory: {str(e)}")

    def preview_cleanup(self):
        """Preview files that would be cleaned up."""
        try:
            if not hasattr(self, 'cleanup_candidates') or not self.cleanup_candidates:
                self.log_cleanup("[ERROR] Please scan directory first.")
                return
            
            age_threshold = self.cleanup_age_var.get()
            enabled = self.enable_cleanup_var.get()
            
            if not enabled:
                self.log_cleanup("[WARNING] Cleanup is not enabled. Enable it to see preview.")
                return
            
            # Clear previous results
            self.cleanup_tree.delete(*self.cleanup_tree.get_children())
            
            # Filter candidates by age
            files_to_cleanup = [c for c in self.cleanup_candidates if c['age'] >= age_threshold]
            
            if not files_to_cleanup:
                self.log_cleanup(f"[INFO] No files older than {age_threshold} days found.")
                return
            
            # Add to treeview
            total_size = 0
            for candidate in files_to_cleanup:
                size_mb = candidate['size'] / (1024 * 1024)
                total_size += candidate['size']
                
                self.cleanup_tree.insert('', 'end', values=(
                    candidate['vendor'],
                    candidate['file'],
                    f"{size_mb:.1f} MB",
                    candidate['modified'].strftime('%Y-%m-%d %H:%M'),
                    f"{candidate['age']} days"
                ))
            
            total_size_mb = total_size / (1024 * 1024)
            self.log_cleanup(f"[INFO] Preview: {len(files_to_cleanup)} files ({total_size_mb:.1f} MB) would be cleaned up")
            
        except Exception as e:
            self.log_cleanup(f"[ERROR] Failed to preview cleanup: {str(e)}")

    def run_cleanup(self):
        """Execute the cleanup operation."""
        try:
            if not hasattr(self, 'cleanup_candidates') or not self.cleanup_candidates:
                self.log_cleanup("[ERROR] Please scan directory first.")
                return
            
            age_threshold = self.cleanup_age_var.get()
            enabled = self.enable_cleanup_var.get()
            
            if not enabled:
                self.log_cleanup("[ERROR] Cleanup is not enabled. Enable it to run cleanup.")
                return
            
            # Filter candidates by age
            files_to_cleanup = [c for c in self.cleanup_candidates if c['age'] >= age_threshold]
            
            if not files_to_cleanup:
                self.log_cleanup(f"[INFO] No files older than {age_threshold} days found.")
                return
            
            # Confirm cleanup
            import tkinter.messagebox as messagebox
            result = messagebox.askyesno(
                "Confirm Cleanup",
                f"Are you sure you want to delete {len(files_to_cleanup)} files?\n"
                f"This action cannot be undone."
            )
            
            if not result:
                self.log_cleanup("[INFO] Cleanup cancelled by user.")
                return
            
            # Execute cleanup
            deleted_count = 0
            deleted_size = 0
            
            for candidate in files_to_cleanup:
                try:
                    deleted, error_message = self.safe_delete_file(candidate['path'])
                    if deleted:
                        deleted_count += 1
                        deleted_size += candidate['size']
                        self.log_cleanup(f"[INFO] Deleted: {candidate['file']} ({candidate['vendor']})")
                    else:
                        self.log_cleanup(f"[ERROR] Failed to delete {candidate['file']}: {error_message}")
                except Exception as e:
                    self.log_cleanup(f"[ERROR] Failed to delete {candidate['file']}: {str(e)}")
            
            deleted_size_mb = deleted_size / (1024 * 1024)
            self.log_cleanup(f"[SUCCESS] Cleanup complete! Deleted {deleted_count} files ({deleted_size_mb:.1f} MB)")
            
            # Create backup log for cleanup operation
            pdf_dir = self.cleanup_pdf_folder_path.get().strip()
            if pdf_dir and os.path.exists(pdf_dir):
                log_content = self.get_current_log_content(self.cleanup_log_area)
                self.create_backup_log(pdf_dir, log_content, "cleanup")
            
            # Refresh the treeview
            self.cleanup_tree.delete(*self.cleanup_tree.get_children())
            
        except Exception as e:
            self.log_cleanup(f"[ERROR] Failed to run cleanup: {str(e)}")
            
            # Create backup log for error case
            pdf_dir = self.cleanup_pdf_folder_path.get().strip()
            if pdf_dir and os.path.exists(pdf_dir):
                log_content = self.get_current_log_content(self.cleanup_log_area)
                self.create_backup_log(pdf_dir, log_content, "cleanup_error")

    def safe_delete_file(self, file_path, max_retries=3):
        """Delete file with Windows-friendly permission handling and retries."""
        last_error = None
        file_path = os.path.normpath(file_path)
        parent_dir = os.path.dirname(file_path)

        for attempt in range(max_retries):
            try:
                if not os.path.exists(file_path):
                    return True, None

                # Some downloaded files are read-only on Windows.
                try:
                    os.chmod(file_path, 0o666)
                except Exception:
                    pass
                try:
                    if parent_dir and os.path.exists(parent_dir):
                        os.chmod(parent_dir, 0o777)
                except Exception:
                    pass

                os.remove(file_path)
                return True, None

            except PermissionError as e:
                last_error = e
                try:
                    os.chmod(file_path, 0o666)
                except Exception:
                    pass
                try:
                    if parent_dir and os.path.exists(parent_dir):
                        os.chmod(parent_dir, 0o777)
                except Exception:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(0.2 * (attempt + 1))

            except OSError as e:
                last_error = e
                if getattr(e, "winerror", None) == 5 and attempt < max_retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                else:
                    break

            except Exception as e:
                last_error = e
                break

        # Final fallback: rename first, then delete renamed path.
        # This can succeed in cases where direct delete is denied but rename is still allowed.
        try:
            if os.path.exists(file_path):
                temp_name = f".delete_pending_{int(time.time() * 1000)}_{os.getpid()}.tmp"
                temp_path = os.path.join(parent_dir, temp_name)
                os.replace(file_path, temp_path)
                os.remove(temp_path)
                return True, None
        except Exception as e:
            last_error = e

        if last_error and getattr(last_error, "winerror", None) == 5:
            return False, f"{last_error} (file is locked or folder ACL denies delete)"
        return False, str(last_error) if last_error else "Unknown deletion error"

    def log(self, message, level="info"):
        """Log a message to the GUI log area with timestamp and level."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Clean output mode: only show important messages
        if self.clean_output_var.get() and level == "debug":
            return  # Skip debug messages in clean mode
        
        # In clean mode, only show: matches, downloads, errors, warnings, and important info
        if self.clean_output_var.get():
            important_keywords = [
                "match", "download", "error", "warning", "found", "completed", 
                "finished", "success", "failed", "skipping", "processing"
            ]
            if not any(keyword in message.lower() for keyword in important_keywords):
                return  # Skip non-important messages in clean mode
        
        self.log_area.insert(END, formatted_message + "\n")
        self.log_area.see(END)
        self.master.update_idletasks()

    def log_overview(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.overview_log_area.insert(END, f"[{timestamp}] {message}\n")
        self.overview_log_area.see(END)

    def log_crossref(self, message, tag=None):
        """Log message to cross-reference area with timestamp."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.crossref_log_area.insert(END, f"[{timestamp}] {message}\n", tag)
        self.crossref_log_area.see(END)

    def log_cleanup(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.cleanup_log_area.insert(END, f"[{timestamp}] {message}\n")
        self.cleanup_log_area.see(END)
        
    def create_backup_log(self, destination_folder, log_content, operation_type="general"):
        """Create backup logs in the destination folder's #backup_logs subdirectory."""
        try:
            if not destination_folder:
                return
            
            # Create #backup_logs subdirectory
            backup_logs_dir = os.path.join(destination_folder, "#backup_logs")
            os.makedirs(backup_logs_dir, exist_ok=True)
            
            # Generate log filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f"{operation_type}_log_{timestamp}.txt"
            log_path = os.path.join(backup_logs_dir, log_filename)
            
            # Write log content
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== {operation_type.upper()} LOG ===\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Destination Folder: {destination_folder}\n")
                f.write("=" * 50 + "\n\n")
                f.write(log_content)
            
            vv_log(f"✅ Backup log created: {log_path}")
            return log_path
            
        except Exception as e:
            vv_log(f"❌ Failed to create backup log: {e}")
            return None
    
    def get_current_log_content(self, log_area):
        """Get current content from a log area widget."""
        try:
            return log_area.get(1.0, END)
        except Exception as e:
            vv_log(f"❌ Failed to get log content: {e}")
            return ""

    def populate_crossref_results(self):
        """Populate the cross-reference results treeview with improved format."""
        try:
            # Clear existing items
            for item in self.crossref_tree.get_children():
                self.crossref_tree.delete(item)
            
            if not hasattr(self, 'crossref_results') or not self.crossref_results:
                return
            
            # Add results to treeview
            for item_code, result in self.crossref_results.items():
                if result['matches']:
                    # Sort matches by score
                    sorted_matches = sorted(result['matches'], key=lambda x: x['score'], reverse=True)
                    
                    for match in sorted_matches:
                        self.crossref_tree.insert('', 'end', values=(
                            item_code,
                            match['supplier'],
                            result['description'][:50] + '...' if len(result['description']) > 50 else result['description'],
                            f"{match['pdf_folder']}/{match['pdf_file']}",
                            f"{match['score']:.1f}%"
                        ))
                else:
                    # No matches
                    self.crossref_tree.insert('', 'end', values=(
                        item_code,
                        'No matches',
                        result['description'][:50] + '...' if len(result['description']) > 50 else result['description'],
                        '',
                        '0.0%'
                    ))
            
            vv_log(f"✅ Populated {len(self.crossref_results)} items in cross-reference results")
            
        except Exception as e:
            vv_log(f"❌ Error populating cross-reference results: {e}")
            self.log_crossref(f"Error populating results: {e}", "error")

    def on_run_clicked(self):
        """Handle run button click."""
        if self.running:
            return
        
        # Validate inputs
        input_file = self.input_path.get().strip()
        master_file = self.master_path.get().strip()
        pdf_folder = self.pdf_folder_path.get().strip()
        
        if not all([input_file, master_file, pdf_folder]):
            self.log("Please select all required files and folders.", "error")
            return
        
        if not os.path.exists(input_file):
            self.log(f"Input file not found: {input_file}", "error")
            return
        
        if not os.path.exists(master_file):
            self.log(f"Master file not found: {master_file}", "error")
            return
        
        if not os.path.exists(pdf_folder):
            try:
                os.makedirs(pdf_folder)
                self.log(f"Created PDF folder: {pdf_folder}", "info")
            except Exception as e:
                self.log(f"Failed to create PDF folder: {e}", "error")
                return
        
        # Start crawling
        self.running = True
        self.run_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.start_time = time.time()
        self.timer_running = True
        self.page_count = 0
        self.pdf_count = 0
        
        # Clear log
        self.log_area.delete(1.0, END)
        self.log("Starting PDF crawler...", "info")
        
        # Start timer
        self.update_timer()
        
        # Process in background thread
        threading.Thread(target=self.process_all, args=([(input_file, master_file, pdf_folder)],), daemon=True).start()

    def update_timer(self):
        """Update the timer display."""
        if self.timer_running and self.start_time:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.timer_label.config(text=f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            if self.running:
                self.master.after(1000, self.update_timer)
    
    def _read_excel_files(self, input_file, master_file):
        """Read and validate Excel files"""
        try:
            vv_log(f"Reading input file: {input_file}")
            df_input = pd.read_excel(input_file, engine='openpyxl')
            vv_log(f"✅ Input file loaded: {len(df_input)} rows")
            
            vv_log(f"Reading master file: {master_file}")
            df_master = pd.read_excel(master_file, engine='openpyxl')
            vv_log(f"✅ Master file loaded: {len(df_master)} rows")
            
            return df_input, df_master
            
        except FileNotFoundError as e:
            self.log(f"❌ Excel file not found: {e}", "error")
            return None, None
        except PermissionError as e:
            self.log(f"❌ Permission denied accessing Excel file: {e}", "error")
            return None, None
        except pd.errors.EmptyDataError:
            self.log("❌ Excel file is empty", "error")
            return None, None
        except Exception as e:
            self.log(f"❌ Error reading Excel files: {e}", "error")
            return None, None

    def process_all(self, args):
        """Process all vendors."""
        try:
            input_file, master_file, pdf_folder = args[0]
            self.download_folder = pdf_folder
            
            # Read Excel files
            self.log("Reading Excel files...", "info")
            df_input, df_master = self._read_excel_files(input_file, master_file)
            if df_input is None or df_master is None:
                return
            
            # Find relevant columns
            type_col = None
            supplier_col = None
            for col in df_input.columns:
                if 'type' in col.lower():
                    type_col = col
                elif 'supplier' in col.lower():
                    supplier_col = col
            
            if not type_col or not supplier_col:
                self.log("Could not find 'Type' and 'Supplier' columns in input file.", "error")
                return
            
            # Filter for 'Instrument' type
            instrument_data = df_input[df_input[type_col].str.strip().str.lower() == 'instrument']
            self.log(f"Found {len(instrument_data)} 'Instrument' entries", "info")
            
            # Merge with master list
            merged = instrument_data.merge(
                df_master[['Supplier Name', 'Website']], 
                on='Supplier Name', 
                how='left'
            )
            
            # Analyze the merge results
            suppliers_with_websites = merged[merged['Website'].notna() & (merged['Website'] != '')]
            suppliers_without_websites = merged[merged['Website'].isna() | (merged['Website'] == '')]
            suppliers_not_in_master = merged[merged['Website'].isna()]
            
            self.log(f"=== SUPPLIER ANALYSIS ===", "info")
            self.log(f"Total instrument suppliers in input: {len(merged)}", "info")
            self.log(f"Suppliers with websites (will be crawled): {len(suppliers_with_websites)}", "info")
            self.log(f"Suppliers not in master list: {len(suppliers_not_in_master)}", "warning")
            
            # Show suppliers not in master list and store them for export
            if len(suppliers_not_in_master) > 0:
                self.log("⚠️ SUPPLIERS NOT IN MASTER LIST:", "warning")
                not_in_master_list = suppliers_not_in_master['Supplier Name'].unique()
                
                # Store missing suppliers for later export
                self.missing_suppliers = []
                for supplier in not_in_master_list:
                    # Get additional info from input data
                    supplier_info = suppliers_not_in_master[suppliers_not_in_master['Supplier Name'] == supplier].iloc[0]
                    self.missing_suppliers.append({
                        'Supplier Name': supplier,
                        'Item Code': supplier_info.get('Item Code', ''),
                        'Item Description': supplier_info.get('Item Description', ''),
                        'Category': supplier_info.get('Category', ''),
                        'Status': 'Missing from Master List'
                    })
                
                for i, supplier in enumerate(not_in_master_list[:20]):  # Show first 20
                    self.log(f"  {i+1}. {supplier}", "warning")
                if len(not_in_master_list) > 20:
                    self.log(f"  ... and {len(not_in_master_list) - 20} more", "warning")
                self.log("These suppliers will be SKIPPED (no website info available)", "warning")
                self.log(f"📋 Missing suppliers list created with {len(self.missing_suppliers)} entries", "info")
                # Enable export button
                self.export_missing_button.config(state='normal')
            else:
                self.missing_suppliers = []
            
            # Show suppliers in master but without websites and store them
            suppliers_no_website = suppliers_without_websites[suppliers_without_websites['Website'].notna()]
            if len(suppliers_no_website) > 0:
                self.log(f"Suppliers in master list but without websites: {len(suppliers_no_website)}", "warning")
                
                # Store suppliers without websites for later export
                if not hasattr(self, 'missing_suppliers'):
                    self.missing_suppliers = []
                
                for _, supplier_info in suppliers_no_website.iterrows():
                    self.missing_suppliers.append({
                        'Supplier Name': supplier_info['Supplier Name'],
                        'Item Code': supplier_info.get('Item Code', ''),
                        'Item Description': supplier_info.get('Item Description', ''),
                        'Category': supplier_info.get('Category', ''),
                        'Status': 'In Master List but No Website'
                    })
                
                self.log(f"📋 Added {len(suppliers_no_website)} suppliers without websites to missing list", "info")
                # Enable export button if not already enabled
                if hasattr(self, 'missing_suppliers') and self.missing_suppliers:
                    self.export_missing_button.config(state='normal')
            
            # Create pairs for processing (only suppliers with websites)
            pairs = []
            for _, row in suppliers_with_websites.iterrows():
                supplier = row['Supplier Name']
                website = row['Website']
                pairs.append((supplier, website))
            
            self.log(f"=== CRAWLING PLAN ===", "info")
            self.log(f"Will crawl {len(pairs)} suppliers with websites", "info")
            
            if not pairs:
                self.log("No suppliers with valid websites found.", "warning")
                return
            
            # Set up progress bar
            self.progress['maximum'] = len(pairs)
            self.progress['value'] = 0
            
            # Process suppliers in batches to avoid overwhelming the system
            batch_size = 10  # Process 10 suppliers at a time
            max_concurrent = self.max_concurrent_var.get()
            
            self.log(f"Processing {len(pairs)} suppliers in batches of {batch_size} with {max_concurrent} concurrent threads", "info")
            
            completed_count = 0
            _count_lock = threading.Lock()   # protects completed_count across threads

            for batch_start in range(0, len(pairs), batch_size):
                if not self.running:
                    break

                batch_end = min(batch_start + batch_size, len(pairs))
                current_batch = pairs[batch_start:batch_end]

                self.log(f"Processing batch {batch_start//batch_size + 1}/{(len(pairs) + batch_size - 1)//batch_size}: suppliers {batch_start + 1}-{batch_end}", "info")

                # Process current batch with semaphore for concurrency control
                semaphore = threading.Semaphore(max_concurrent)
                batch_threads = []

                def crawl_vendor(supplier, url):
                    try:
                        semaphore.acquire()
                        self.crawl_site(supplier, url)
                    except Exception as e:
                        self.log(f"❌ Unexpected error crawling {supplier}: {e}", "error")
                    finally:
                        semaphore.release()
                        nonlocal completed_count
                        with _count_lock:
                            completed_count += 1
                            current = completed_count
                        self.progress['value'] = current
                        self.log(f"Completed {current}/{len(pairs)} suppliers", "info")

                # Start threads for current batch
                for supplier, url in current_batch:
                    if not self.running:
                        break
                    thread = threading.Thread(target=crawl_vendor, args=(supplier, url), daemon=True)
                    thread.start()
                    batch_threads.append(thread)

                # Wait for current batch to complete with timeout
                batch_timeout = 300  # 5 minutes per batch
                for thread in batch_threads:
                    thread.join(timeout=batch_timeout)
                    if thread.is_alive():
                        self.log(f"⚠️ Thread timeout - some suppliers in batch may still be processing", "warning")

                if self.running:
                    self.log(f"Batch {batch_start//batch_size + 1} completed", "info")
                    gc.collect()   # reclaim memory between batches
            
            if self.running:
                self.log(f"✅ Crawling completed! Visited {self.page_count} pages, downloaded {self.pdf_count} PDFs.", "success")
                
                # Create backup log for crawling operation
                if self.download_folder:
                    log_content = self.get_current_log_content(self.log_area)
                    self.create_backup_log(self.download_folder, log_content, "crawling")
            else:
                self.log("⏹️ Crawling stopped by user.", "warning")
                
                # Create backup log even if stopped
                if self.download_folder:
                    log_content = self.get_current_log_content(self.log_area)
                    self.create_backup_log(self.download_folder, log_content, "crawling_stopped")
                
        except Exception as e:
            self.log(f"❌ Error during processing: {e}", "error")
            if self.verbose_var.get():
                self.log(traceback.format_exc(), "error")
                
            # Create backup log for error case
            if hasattr(self, 'download_folder') and self.download_folder:
                log_content = self.get_current_log_content(self.log_area)
                self.create_backup_log(self.download_folder, log_content, "crawling_error")
        finally:
            self.running = False
            self.timer_running = False
            self.run_button.config(state='normal')
            self.stop_button.config(state='disabled')

    def crawl_site(self, supplier, url):
        """Crawl a single vendor site with intelligent crawling strategy."""
        if not self.running:
            return
        
        self.log(f"🌐 Starting intelligent crawl for {supplier}: {url}", "info")
        
        try:
            # Create vendor folder
            vendor_folder = os.path.join(self.download_folder, supplier)
            os.makedirs(vendor_folder, exist_ok=True)
            
            # Create a separate visited set for this supplier to avoid race conditions
            supplier_visited = set()
            
            # Try intelligent crawling first
            success = self._intelligent_crawling(url, supplier, vendor_folder, supplier_visited)
            
            if not success:
                # Fall back to traditional crawling
                self.log(f"🔍 Using traditional crawling for {supplier}", "info")
                self.crawl_url_recursive(url, vendor_folder, supplier, visited_set=supplier_visited)
            
            # Log completion
            self.log(f"✅ Finished crawling {supplier} (visited {len(supplier_visited)} pages)", "info")
            
        except Exception as e:
            self.log(f"❌ Failed to crawl {supplier}: {e}", "error")
    
    def _intelligent_crawling(self, url, supplier, vendor_folder, supplier_visited):
        """Use sitemap and robots.txt for efficient crawling"""
        try:
            # Check robots.txt first
            robots_url = urljoin(url, '/robots.txt')
            self.log(f"🤖 Checking robots.txt for {supplier}", "info")
            
            try:
                robots_response = self.session.get(robots_url, timeout=10)
                if robots_response.status_code == 200:
                    robots_content = robots_response.text
                    
                    # Parse sitemap if available
                    sitemap_urls = self._extract_sitemap_urls(robots_content, url)
                    
                    if sitemap_urls:
                        self.log(f"🎯 Found {len(sitemap_urls)} sitemaps for {supplier}", "info")
                        return self._crawl_via_sitemap(sitemap_urls, supplier, vendor_folder, supplier_visited)
                    else:
                        self.log(f"📄 No sitemaps found in robots.txt for {supplier}", "info")
                        
            except Exception as e:
                self.log(f"⚠️ Could not access robots.txt for {supplier}: {e}", "warning")
            
            return False  # Fall back to traditional crawling
            
        except Exception as e:
            self.log(f"⚠️ Intelligent crawling failed for {supplier}: {e}", "warning")
            return False
    
    def _extract_sitemap_urls(self, robots_content, base_url):
        """Extract sitemap URLs from robots.txt"""
        sitemap_urls = []
        for line in robots_content.split('\n'):
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemap_urls.append(urljoin(base_url, sitemap_url))
        return sitemap_urls
    
    def _crawl_via_sitemap(self, sitemap_urls, supplier, vendor_folder, supplier_visited):
        """Crawl using sitemap URLs"""
        try:
            pdf_urls = []
            
            for sitemap_url in sitemap_urls:
                if not self.running:
                    break
                    
                try:
                    self.log(f"📋 Processing sitemap: {sitemap_url}", "info")
                    response = self.session.get(sitemap_url, timeout=15)
                    response.raise_for_status()
                    
                    # Parse sitemap XML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, 'xml')
                    
                    # Find all URLs in sitemap
                    urls = []
                    for loc in soup.find_all('loc'):
                        if loc.text:
                            urls.append(loc.text.strip())
                    
                    # Filter for PDF URLs
                    for url in urls:
                        if url.lower().endswith('.pdf'):
                            pdf_urls.append(url)
                        elif len(supplier_visited) < MAX_PAGES_PER_SITE:
                            supplier_visited.add(url)
                    
                    self.log(f"📋 Found {len(urls)} URLs in sitemap, {len([u for u in urls if u.lower().endswith('.pdf')])} PDFs", "info")
                    
                except Exception as e:
                    self.log(f"⚠️ Failed to process sitemap {sitemap_url}: {e}", "warning")
                    continue
            
            # Download found PDFs
            for pdf_url in pdf_urls:
                if not self.running:
                    break
                self.download_pdf(pdf_url, vendor_folder, supplier)
            
            if pdf_urls:
                self.log(f"✅ Sitemap crawling found {len(pdf_urls)} PDFs for {supplier}", "info")
                return True
            else:
                self.log(f"📄 No PDFs found via sitemap for {supplier}", "info")
                return False
                
        except Exception as e:
            self.log(f"❌ Sitemap crawling failed for {supplier}: {e}", "error")
            return False

    def crawl_url_recursive(self, url, vendor_folder, supplier, visited_set=None, depth=0, max_depth=2):
        """Recursively crawl URLs to find PDFs with security validation."""
        if visited_set is None:
            visited_set = set()
            
        if not self.running or depth > max_depth or url in visited_set:
            return
        
        # Security validation
        if not validate_url(url):
            self.log(f"⚠️ Invalid or unsafe URL blocked: {url}", "warning")
            return
        
        if len(visited_set) >= MAX_PAGES_PER_SITE:
            self.log(f"⚠️ Reached page limit for {supplier}, stopping", "warning")
            return
        
        visited_set.add(url)
        self.page_count += 1
        
        try:
            # Add delay between requests
            time.sleep(REQUEST_DELAY)
            
            if self.verbose_var.get():
                self.log(f"📄 Visiting: {url} (depth {depth})", "info")
            
            # Fetch the page with timeout
            response = self.session.get(url, timeout=PAGE_TIMEOUT)
            response.raise_for_status()
            
            # Check if it's a PDF
            if url.lower().endswith('.pdf'):
                self.download_pdf(url, vendor_folder, supplier)
                return
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links
            pdf_links = []
            other_links = []
            
            for link in soup.find_all('a', href=True):
                if not self.running:
                    return
                
                href = link['href']
                full_url = urljoin(url, href)
                
                # Only follow links on the same domain
                if urlparse(full_url).netloc == urlparse(url).netloc:
                    if full_url.lower().endswith('.pdf'):
                        pdf_links.append(full_url)
                    elif depth < max_depth and full_url not in self.visited:
                        other_links.append(full_url)
            
            # Download PDFs first
            for pdf_url in pdf_links:
                if not self.running:
                    return
                self.download_pdf(pdf_url, vendor_folder, supplier)
            
            # Then follow other links (limit to prevent infinite crawling)
            for link_url in other_links[:10]:  # Limit to 10 links per page
                if not self.running:
                    return
                if link_url not in visited_set:
                    self.crawl_url_recursive(link_url, vendor_folder, supplier, visited_set, depth + 1, max_depth)
            
        except requests.exceptions.Timeout:
            self.log(f"⏰ Timeout crawling {url}", "warning")
        except requests.exceptions.RequestException as e:
            self.log(f"⚠️ Request failed for {url}: {e}", "warning")
        except Exception as e:
            self.log(f"❌ Failed to crawl {url}: {e}", "error")

    def download_pdf(self, pdf_url, vendor_folder, supplier):
        """Download a PDF file with security validation and integrity checking."""
        if not self.running:
            return
        
        try:
            # Security validation
            if not validate_url(pdf_url):
                self.log(f"⚠️ Invalid or unsafe PDF URL blocked: {pdf_url}", "warning")
                return
            
            # Get filename from URL
            filename = os.path.basename(urlparse(pdf_url).path)
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Enhanced filename sanitization
            filename = sanitize_path(filename)
            if not filename or len(filename) < 4:  # Minimum valid filename
                filename = f"document_{int(time.time())}.pdf"
            
            # Check if already downloaded
            file_path = os.path.join(vendor_folder, filename)
            if os.path.exists(file_path):
                if self.verbose_var.get():
                    self.log(f"📄 PDF already exists: {filename}", "info")
                return
            
            # Download the PDF with size limit (50MB max)
            response = self.session.get(pdf_url, timeout=PAGE_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Check content type and size
            content_type = response.headers.get('content-type', '').lower()
            content_length = response.headers.get('content-length')
            
            max_size_bytes = config.max_pdf_size_mb * 1024 * 1024
            if content_length and int(content_length) > max_size_bytes:
                self.log(f"⚠️ PDF too large, skipping: {pdf_url} ({int(content_length)/(1024*1024):.1f}MB > {config.max_pdf_size_mb}MB)", "warning")
                return
            
            if config.strict_content_validation and 'pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
                self.log(f"⚠️ Skipping non-PDF file: {pdf_url}", "warning")
                return
            
            # Download with size checking
            downloaded_size = 0
            max_size = max_size_bytes
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.running:
                        os.remove(file_path)  # Clean up partial download
                        return
                    
                    downloaded_size += len(chunk)
                    if downloaded_size > max_size:
                        os.remove(file_path)  # Clean up oversized file
                        self.log(f"⚠️ PDF too large during download, removed: {pdf_url}", "warning")
                        return
                    
                    f.write(chunk)
            
            # Verify the downloaded file
            if os.path.getsize(file_path) < config.min_pdf_size_bytes:
                os.remove(file_path)
                self.log(f"⚠️ Downloaded file too small, removed: {filename} ({os.path.getsize(file_path)} bytes < {config.min_pdf_size_bytes} bytes)", "warning")
                return
            
            # Calculate file hash for integrity
            file_hash = calculate_file_hash(file_path)
            if file_hash:
                vv_log(f"File hash: {file_hash[:16]}...")
            
            self.pdf_count += 1
            self.log(f"✅ Downloaded: {supplier}/{filename} ({os.path.getsize(file_path)/(1024*1024):.1f}MB)", "success")
            
        except requests.exceptions.Timeout:
            self.log(f"⏰ Timeout downloading {pdf_url}", "warning")
        except requests.exceptions.RequestException as e:
            self.log(f"⚠️ Failed to download {pdf_url}: {e}", "warning")
        except Exception as e:
            self.log(f"❌ Failed to download {pdf_url}: {e}", "error")
            # Clean up any partial file
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def sanitize_filename(self, filename):
        """Sanitize filename for safe saving."""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename

    def export_missing_suppliers(self):
        """Export missing suppliers list to Excel."""
        try:
            if not hasattr(self, 'missing_suppliers') or not self.missing_suppliers:
                self.log("No missing suppliers to export.", "warning")
                return
            
            # Create DataFrame from missing suppliers
            df = pd.DataFrame(self.missing_suppliers)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"missing_suppliers_{timestamp}.xlsx"
            
            # Export to Excel
            df.to_excel(filename, index=False, engine='openpyxl')
            
            self.log(f"✅ Missing suppliers exported to: {filename}", "success")
            self.log(f"📊 Exported {len(self.missing_suppliers)} missing suppliers", "info")
            
            # Show summary
            missing_count = len([s for s in self.missing_suppliers if s['Status'] == 'Missing from Master List'])
            no_website_count = len([s for s in self.missing_suppliers if s['Status'] == 'In Master List but No Website'])
            
            self.log(f"   - {missing_count} suppliers not in master list", "info")
            self.log(f"   - {no_website_count} suppliers in master list but no website", "info")
            
        except Exception as e:
            self.log(f"❌ Failed to export missing suppliers: {e}", "error")

    def on_stop_clicked(self):
        """Handle stop button click."""
        self.running = False
        self.timer_running = False
        self.log("⏹️ Stopping crawler...", "warning")

    def on_closing(self):
        """Clean up when the application is closed."""
        self.running = False
        self.timer_running = False
        
        # Perform memory optimization
        self.optimize_memory()
        
        # Save configuration
        try:
            config.save_to_file()
            vv_log("✅ Configuration saved")
        except Exception as e:
            vv_log(f"⚠️ Failed to save configuration: {e}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', 12345))
            sock.close()
        except OSError:
            pass
        
        vv_log("✅ Application cleanup completed")
        self.master.destroy()

def main():
    """Main function with very verbose logging."""
    vv_log("=== STARTING PDF CRAWLER APPLICATION ===")
    
    try:
        # Check for single instance
        vv_log("Checking for single instance...")
        if not check_single_instance():
            vv_log("❌ Another instance is already running")
            print("❌ Another instance of PDF Crawler is already running!")
            return
        
        vv_log("✅ Single instance check passed")
        
        # Create main window
        vv_log("Creating main window...")
        root = Tk()
        vv_log("✅ Main window created")
        
        # Create application
        vv_log("Creating application instance...")
        app = PDFCrawlerEnhancedApp(root)
        vv_log("✅ Application instance created")
        
        # Start main loop
        vv_log("Starting main event loop...")
        root.mainloop()
        vv_log("✅ Application closed successfully")
        
    except Exception as e:
        vv_log(f"❌ Application startup failed: {e}")
        traceback.print_exc()
        print(f"❌ Application startup failed: {e}")

if __name__ == "__main__":
    main()