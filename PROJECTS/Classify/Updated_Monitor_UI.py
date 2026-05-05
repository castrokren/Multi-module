import sys
import os
import subprocess
import tkinter as tk
import threading
import json
import datetime
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Constants
DEFAULT_WINDOW_SIZE = "700x500"
LOG_HEIGHT = 10
LOG_WIDTH = 75
BUTTON_WIDTH = 10
SUPPORTED_ACTIONS = ['install', 'update', 'remove', 'start', 'stop', 'restart', 'debug']
CONFIG_FILE = 'service_config.json'
MONITOR_CONFIG_FILE = 'monitor_config.json'

def get_short_path(long_path):
    """Convert a long Windows path to short (8.3) path."""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, 260)
        return buf.value if result else long_path
    except (AttributeError, OSError):
        return long_path  # Fallback for non-Windows systems

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.tooltip = None
    
    def on_enter(self, event=None):
        try:
            x, y, _, _ = self.widget.bbox("insert")
        except:
            # Fallback for widgets that don't support bbox
            x, y = 25, 25
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="yellow")
        label.pack()
    
    def on_leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class ServiceGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Folder Monitor Service Manager")
        self.geometry(DEFAULT_WINDOW_SIZE)
        self._init_vars()
        self._build_ui()
        self._load_config()

    def _init_vars(self):
        # Service-related variables (old system)
        self.service_path_var = tk.StringVar(value=os.environ.get('SERVICE_SCRIPT', ''))
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.startup_var = tk.StringVar(value='manual')
        self.interactive_var = tk.BooleanVar()
        self.show_pass_var = tk.BooleanVar()
        
        # New simplified config variables
        self.watch_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.hw_keywords_var = tk.StringVar()
        self.sw_keywords_var = tk.StringVar()
        self.ni_keywords_var = tk.StringVar()  # Non-Instrument keywords
        
        # Adaptive processor variables
        self.use_adaptive_var = tk.BooleanVar(value=True)
        self.learning_mode_var = tk.BooleanVar(value=True)
        self.min_occurrences_var = tk.StringVar(value="5")
        self.confidence_threshold_var = tk.StringVar(value="0.7")
        
        self.status_var = tk.StringVar(value="Ready")
        self.action_buttons = []

    def _build_ui(self):
        # Add menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Config (Ctrl+S)", command=self._save_config)
        file_menu.add_command(label="Load Config (Ctrl+O)", command=self._load_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        
        padx = 5
        pady = 5
        
        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(7, weight=1)  # Updated for new layout
        
        # Service Configuration Section
        service_frame = tk.LabelFrame(self, text="Service Configuration", padx=10, pady=10)
        service_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        service_frame.grid_columnconfigure(1, weight=1)
        
        # Service script path
        tk.Label(service_frame, text="Service Script (.py):").grid(row=0, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(service_frame, textvariable=self.service_path_var, width=50).grid(row=0, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(service_frame, text="Browse", command=self._browse_service).grid(row=0, column=2, padx=padx, pady=pady)
        
        # Credentials
        tk.Label(service_frame, text="Run as User (domain\\user):").grid(row=1, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(service_frame, textvariable=self.user_var, width=30).grid(row=1, column=1, sticky='w', padx=padx, pady=pady)
        
        tk.Label(service_frame, text="Password:").grid(row=2, column=0, sticky='e', padx=padx, pady=pady)
        pass_entry = tk.Entry(service_frame, textvariable=self.pass_var, show="*", width=30)
        pass_entry.grid(row=2, column=1, sticky='w', padx=padx, pady=pady)
        
        # Show password checkbox
        show_pass_cb = tk.Checkbutton(service_frame, text="Show", variable=self.show_pass_var,
                                      command=lambda: self._toggle_password_visibility(pass_entry))
        show_pass_cb.grid(row=2, column=2, sticky='w', padx=padx, pady=pady)
        ToolTip(show_pass_cb, "Toggle password visibility")
        
        # Startup type and Interactive
        tk.Label(service_frame, text="Startup Type:").grid(row=3, column=0, sticky='e', padx=padx, pady=pady)
        tk.OptionMenu(service_frame, self.startup_var, 'manual','auto','disabled','delayed').grid(row=3, column=1, sticky='w', padx=padx, pady=pady)
        tk.Checkbutton(service_frame, text="Interactive", variable=self.interactive_var).grid(row=3, column=2, sticky='w', padx=padx, pady=pady)
        
        # Monitor Configuration Section
        monitor_frame = tk.LabelFrame(self, text="Monitor Configuration", padx=10, pady=10)
        monitor_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky='ew')
        monitor_frame.grid_columnconfigure(1, weight=1)
        
        # Watch directory
        tk.Label(monitor_frame, text="Watch Directory:").grid(row=0, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(monitor_frame, textvariable=self.watch_dir_var, width=50).grid(row=0, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(monitor_frame, text="Browse", command=self._browse_watch).grid(row=0, column=2, padx=padx, pady=pady)
        
        # Output directory
        tk.Label(monitor_frame, text="Output Directory:").grid(row=1, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(monitor_frame, textvariable=self.output_dir_var, width=50).grid(row=1, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(monitor_frame, text="Browse", command=self._browse_output).grid(row=1, column=2, padx=padx, pady=pady)
        
        # Research Instrument keywords file
        tk.Label(monitor_frame, text="Research Instrument Keywords:").grid(row=2, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(monitor_frame, textvariable=self.hw_keywords_var, width=50).grid(row=2, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(monitor_frame, text="Browse", command=self._browse_hw_keywords).grid(row=2, column=2, padx=padx, pady=pady)
        
        # Software keywords file
        tk.Label(monitor_frame, text="Software Keywords:").grid(row=3, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(monitor_frame, textvariable=self.sw_keywords_var, width=50).grid(row=3, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(monitor_frame, text="Browse", command=self._browse_sw_keywords).grid(row=3, column=2, padx=padx, pady=pady)
        
        # Non-Instrument keywords file
        tk.Label(monitor_frame, text="Non-Instrument Keywords:").grid(row=4, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(monitor_frame, textvariable=self.ni_keywords_var, width=50).grid(row=4, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(monitor_frame, text="Browse", command=self._browse_ni_keywords).grid(row=4, column=2, padx=padx, pady=pady)
        
        # Adaptive Processor Configuration Section
        adaptive_frame = tk.LabelFrame(monitor_frame, text="Adaptive Learning Settings", padx=5, pady=5)
        adaptive_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
        
        # Use adaptive processor checkbox
        adaptive_cb = tk.Checkbutton(adaptive_frame, text="Use Adaptive Processor", 
                                   variable=self.use_adaptive_var, command=self._toggle_adaptive_controls)
        adaptive_cb.grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        ToolTip(adaptive_cb, "Enable adaptive learning processor that improves over time")
        
        # Learning mode checkbox
        self.learning_cb = tk.Checkbutton(adaptive_frame, text="Enable Learning Mode", 
                                        variable=self.learning_mode_var, state='disabled')
        self.learning_cb.grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ToolTip(self.learning_cb, "Allow the processor to learn new keywords from your data")
        
        # Min occurrences
        tk.Label(adaptive_frame, text="Min Occurrences:").grid(row=1, column=1, sticky='e', padx=5, pady=2)
        min_occ_entry = tk.Entry(adaptive_frame, textvariable=self.min_occurrences_var, width=8, state='disabled')
        min_occ_entry.grid(row=1, column=2, sticky='w', padx=5, pady=2)
        ToolTip(min_occ_entry, "Minimum times a keyword must appear before being promoted")
        
        # Confidence threshold
        tk.Label(adaptive_frame, text="Confidence Threshold:").grid(row=2, column=1, sticky='e', padx=5, pady=2)
        conf_entry = tk.Entry(adaptive_frame, textvariable=self.confidence_threshold_var, width=8, state='disabled')
        conf_entry.grid(row=2, column=2, sticky='w', padx=5, pady=2)
        ToolTip(conf_entry, "Minimum confidence score for keyword acceptance (0.0-1.0)")
        
        # Store references for enabling/disabling
        self.adaptive_controls = [self.learning_cb, min_occ_entry, conf_entry]
        
        # Learning Report Button
        report_btn = tk.Button(adaptive_frame, text="Learning Report", command=self._show_learning_report, state='disabled')
        report_btn.grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ToolTip(report_btn, "View adaptive learning progress and statistics")
        self.learning_report_btn = report_btn
        
        # Test Configuration Button
        test_btn = tk.Button(monitor_frame, text="Test Configuration", command=self._test_config, bg='lightblue')
        test_btn.grid(row=6, column=1, pady=10)
        ToolTip(test_btn, "Test the monitor configuration without installing service. Uses first unprocessed Excel file found in watch directory.")
        
        # Log area with scrollbar
        log_frame = tk.Frame(self)
        log_frame.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky='nsew')
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=LOG_HEIGHT, width=LOG_WIDTH)
        scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Action buttons
        button_frame = tk.Frame(self)
        button_frame.grid(row=8, column=0, columnspan=3, padx=padx, pady=pady)
        
        # Tooltip descriptions for actions
        action_tooltips = {
            'install': 'Install the Windows service',
            'update': 'Update the service configuration',
            'remove': 'Remove the Windows service',
            'start': 'Start the service',
            'stop': 'Stop the service',
            'restart': 'Restart the service',
            'debug': 'Run service in debug mode'
        }
        
        for idx, act in enumerate(SUPPORTED_ACTIONS):
            btn = tk.Button(button_frame, text=act.title(), width=BUTTON_WIDTH, 
                          command=lambda a=act: self._run_cmd(a))
            btn.grid(row=idx//4, column=idx%4, padx=padx, pady=pady)
            self.action_buttons.append(btn)
            ToolTip(btn, action_tooltips.get(act, f"Execute {act} action"))
        
        # Config buttons
        config_frame = tk.Frame(self)
        config_frame.grid(row=9, column=0, columnspan=3, padx=padx, pady=pady)
        tk.Button(config_frame, text="Save Config", command=self._save_config).grid(row=0, column=0, padx=padx, pady=pady)
        tk.Button(config_frame, text="Load Config", command=self._load_config).grid(row=0, column=1, padx=padx, pady=pady)
        
        # Status bar
        status_bar = tk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=10, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        
        # Bind keyboard shortcuts
        self.bind('<Control-s>', lambda e: self._save_config())
        self.bind('<Control-o>', lambda e: self._load_config())
        self.bind('<F5>', lambda e: self._run_cmd('restart'))

    def _browse_service(self):
        path = filedialog.askopenfilename(
            title="Select Service Script",
            filetypes=[('Python Files','*.py')],
            initialdir=os.path.dirname(self.service_path_var.get()) if self.service_path_var.get() else os.getcwd()
        )
        if path:
            short = get_short_path(path)
            self.service_path_var.set(short)

    def _browse_watch(self):
        path = filedialog.askdirectory(title="Select Watch Directory")
        if path:
            self.watch_dir_var.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir_var.set(path)

    def _browse_hw_keywords(self):
        path = filedialog.askopenfilename(
            title="Select Hardware Keywords File",
            filetypes=[('Text Files','*.txt'), ('All Files','*.*')]
        )
        if path:
            self.hw_keywords_var.set(path)

    def _browse_sw_keywords(self):
        path = filedialog.askopenfilename(
            title="Select Software Keywords File",
            filetypes=[('Text Files','*.txt'), ('All Files','*.*')]
        )
        if path:
            self.sw_keywords_var.set(path)
    
    def _browse_ni_keywords(self):
        path = filedialog.askopenfilename(
            title="Select Non-Instrument Keywords File",
            filetypes=[('Text Files','*.txt'), ('All Files','*.*')]
        )
        if path:
            self.ni_keywords_var.set(path)

    def _validate_inputs(self):
        """Validate required inputs before running commands."""
        errors = []
        
        # Service script validation
        svc_path = self.service_path_var.get().strip()
        if not svc_path:
            errors.append("Service script path is required")
        elif not os.path.isfile(svc_path):
            errors.append("Service script file does not exist")
        
        # Monitor config validation
        watch_dir = self.watch_dir_var.get().strip()
        if not watch_dir:
            errors.append("Watch directory is required")
        elif not os.path.isdir(watch_dir):
            errors.append("Watch directory does not exist")
        
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            errors.append("Output directory is required")
        
        hw_file = self.hw_keywords_var.get().strip()
        if not hw_file:
            errors.append("Research Instrument keywords file is required")
        elif not os.path.isfile(hw_file):
            errors.append("Research Instrument keywords file does not exist")
        
        sw_file = self.sw_keywords_var.get().strip()
        if not sw_file:
            errors.append("Software keywords file is required")
        elif not os.path.isfile(sw_file):
            errors.append("Software keywords file does not exist")
        
        ni_file = self.ni_keywords_var.get().strip()
        if not ni_file:
            errors.append("Non-Instrument keywords file is required")
        elif not os.path.isfile(ni_file):
            errors.append("Non-Instrument keywords file does not exist")
        
        # Validate user format if provided
        user = self.user_var.get().strip()
        if user and '\\' not in user:
            errors.append("User should be in format 'domain\\username'")
        
        return errors

    def _test_config(self):
        """Test the monitor configuration by processing a sample file."""
        errors = self._validate_inputs()
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return
        
        self._log_message("Testing configuration...")
        
        # Create monitor config file
        self._save_monitor_config()
        
        # Look for test files in watch directory
        watch_dir = Path(self.watch_dir_var.get())
        all_files = list(watch_dir.glob("*.xlsx")) + list(watch_dir.glob("*.xls"))
        
        # Filter out already processed files
        test_files = [f for f in all_files if not f.stem.endswith('_labeled')]
        
        if not test_files:
            if all_files:
                self._log_message("No unprocessed files found for testing.")
                self._log_message("Available files are already processed (contain '_labeled' in name).")
                messagebox.showwarning("No Test Files", 
                    "No unprocessed Excel files found in watch directory.\n\n" +
                    "All files appear to be already processed (contain '_labeled' in name).\n" +
                    "Please use an unprocessed Excel file for testing.")
                return
            else:
                messagebox.showwarning("No Test Files", "No Excel files found in watch directory for testing.")
                return
        
        test_file = test_files[0]
        self._log_message(f"Testing with file: {test_file.name}")
        self._log_message(f"Found {len(test_files)} unprocessed files, using: {test_file.name}")
        
        try:
            # Choose processor based on adaptive setting
            if self.use_adaptive_var.get():
                # Use adaptive processor
                from adaptive_excel_processor import AdaptiveExcelProcessor
                
                processor = AdaptiveExcelProcessor(
                    hw_keywords_file=self.hw_keywords_var.get() or "research_instrument_keywords.txt",
                    sw_keywords_file=self.sw_keywords_var.get() or "software_keywords.txt",
                    ni_keywords_file=self.ni_keywords_var.get() or "non_instrument_keywords.txt",
                    output_dir=self.output_dir_var.get() or r"D:\SOM_in_labeled",
                    learning_mode=self.learning_mode_var.get(),
                    min_occurrences=int(self.min_occurrences_var.get()),
                    confidence_threshold=float(self.confidence_threshold_var.get())
                )
                
                self._log_message("Testing with Adaptive Processor (3-Category + Vendor System)...")
                self._log_message(f"Processor settings:")
                self._log_message(f"  - Research Instrument keywords file: {processor.hw_keywords_file}")
                self._log_message(f"  - Software keywords file: {processor.sw_keywords_file}")
                self._log_message(f"  - Non-Instrument keywords file: {processor.ni_keywords_file}")
                self._log_message(f"  - Output directory: {processor.output_dir}")
                self._log_message(f"  - Learning mode: {processor.learning_mode}")
                self._log_message(f"  - Min occurrences: {processor.min_occurrences}")
                self._log_message(f"  - Test file: {test_file}")
                self._log_message(f"  - Vendor classification: ENABLED (uses supplier column)")
                
                success = processor.process_file(test_file, test_mode=True)  # Safe test mode
                
                if success:
                    self._log_message("Adaptive processor test PASSED")
                    
                    # Show learning analytics
                    analytics = processor.generate_learning_analytics()
                    self._log_message(f"Learning Analytics:")
                    self._log_message(f"  - Research Instrument candidates: {analytics['hw_learning_rate']}")
                    self._log_message(f"  - Software candidates: {analytics['sw_learning_rate']}")
                    self._log_message(f"  - Non-Instrument candidates: {analytics['ni_learning_rate']}")
                    self._log_message(f"  - Ready for promotion (Instruments): {len(analytics['promotion_candidates']['hw'])}")
                    self._log_message(f"  - Ready for promotion (Software): {len(analytics['promotion_candidates']['sw'])}")
                    self._log_message(f"  - Ready for promotion (Non-Instruments): {len(analytics['promotion_candidates']['ni'])}")
                    
                    total_promotion = len(analytics['promotion_candidates']['hw']) + len(analytics['promotion_candidates']['sw']) + len(analytics['promotion_candidates']['ni'])
                    messagebox.showinfo("Test Success", 
                        "Adaptive processor test completed successfully!\n\n" +
                        f"Instrument Candidates: {analytics['hw_learning_rate']}\n" +
                        f"Software Candidates: {analytics['sw_learning_rate']}\n" +
                        f"Non-Instrument Candidates: {analytics['ni_learning_rate']}\n" +
                        f"Ready for Promotion: {total_promotion}")
                else:
                    self._log_message("Adaptive processor test FAILED")
                    self._log_message("Check the adaptive processor logs for detailed error information")
                    messagebox.showerror("Test Failed", "Adaptive processor test failed. Check log for details.")
            else:
                # Use original processor
                from excel_processor import ExcelProcessor
                
                # Try to use config system for proper path resolution
                try:
                    from config import config
                    hw_file = self.hw_keywords_var.get() or str(config.hardware_keywords_file)
                    sw_file = self.sw_keywords_var.get() or str(config.software_keywords_file)
                    output_dir = self.output_dir_var.get() or str(config.output_directory)
                except ImportError:
                    # Fallback if config module not available
                    hw_file = self.hw_keywords_var.get() or "hardware_keywords.txt"
                    sw_file = self.sw_keywords_var.get() or "software_keywords.txt"
                    output_dir = self.output_dir_var.get() or r"D:\SOM_in_labeled"
                
                processor = ExcelProcessor(
                    hw_keywords_file=hw_file,
                    sw_keywords_file=sw_file,
                    output_dir=output_dir
                )
                
                self._log_message("Testing with Original Processor...")
                success = processor.process_file(test_file)
                
                if success:
                    self._log_message("Original processor test PASSED")
                    messagebox.showinfo("Test Success", "Original processor test completed successfully!")
                else:
                    self._log_message("Original processor test FAILED")
                    messagebox.showerror("Test Failed", "Original processor test failed. Check log for details.")
                
        except ImportError as e:
            messagebox.showerror("Missing Modules", 
                               f"Cannot find required processor module: {e}\n\n" +
                               "Make sure you have the processor modules installed.")
        except ValueError as e:
            messagebox.showerror("Configuration Error", 
                               f"Invalid configuration values: {e}\n\n" +
                               "Please check your Min Occurrences and Confidence Threshold values.")
        except Exception as e:
            self._log_message(f"Test error: {e}")
            messagebox.showerror("Test Error", f"Error during test: {e}")

    def _save_monitor_config(self):
        """Save monitor configuration to the new config file."""
        config = {
            "watch_directory": self.watch_dir_var.get(),
            "output_directory": self.output_dir_var.get(),
            "hardware_keywords_file": self.hw_keywords_var.get(),
            "software_keywords_file": self.sw_keywords_var.get(),
            "non_instrument_keywords_file": self.ni_keywords_var.get(),
        }
        
        try:
            with open(MONITOR_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            self._log_message("Monitor configuration saved")
        except Exception as e:
            self._log_message(f"Error saving monitor config: {e}", "ERROR")

    def _log_message(self, message, level="INFO"):
        """Add timestamped message to log."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {level}: {message}\n"
        self.log_text.insert(tk.END, formatted_msg)
        self.log_text.see(tk.END)

    def _set_buttons_state(self, state):
        """Enable or disable all action buttons."""
        for btn in self.action_buttons:
            btn.config(state=state)

    def _toggle_password_visibility(self, entry):
        """Toggle password visibility."""
        entry.config(show="" if self.show_pass_var.get() else "*")
    
    def _toggle_adaptive_controls(self):
        """Enable/disable adaptive processor controls."""
        state = 'normal' if self.use_adaptive_var.get() else 'disabled'
        for control in self.adaptive_controls:
            control.config(state=state)
        self.learning_report_btn.config(state=state)
    
    def _show_learning_report(self):
        """Show adaptive learning report."""
        if not self.use_adaptive_var.get():
            messagebox.showwarning("Adaptive Processor Disabled", "Please enable adaptive processor to view learning report.")
            return
        
        try:
            from adaptive_excel_processor import AdaptiveExcelProcessor
            
            processor = AdaptiveExcelProcessor(
                hw_keywords_file=self.hw_keywords_var.get() or "research_instrument_keywords.txt",
                sw_keywords_file=self.sw_keywords_var.get() or "software_keywords.txt",
                ni_keywords_file=self.ni_keywords_var.get() or "non_instrument_keywords.txt",
                output_dir=self.output_dir_var.get() or r"D:\SOM_in_labeled",
                learning_mode=self.learning_mode_var.get(),
                min_occurrences=int(self.min_occurrences_var.get()),
                confidence_threshold=float(self.confidence_threshold_var.get())
            )
            
            # Load existing learning data
            processor.load_learning_log()
            
            # Generate and display report
            report = processor.get_learning_report()
            
            # Create a new window to display the report
            report_window = tk.Toplevel(self)
            report_window.title("Adaptive Learning Report")
            report_window.geometry("600x500")
            
            # Create text widget with scrollbar
            text_frame = tk.Frame(report_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 10))
            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget.insert(tk.END, report)
            text_widget.config(state=tk.DISABLED)
            
            # Add close button
            close_btn = tk.Button(report_window, text="Close", command=report_window.destroy)
            close_btn.pack(pady=5)
            
        except ImportError:
            messagebox.showerror("Missing Module", "Adaptive processor module not found. Please ensure adaptive_excel_processor.py is available.")
        except Exception as e:
            messagebox.showerror("Error", f"Error generating learning report: {e}")

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo("About", 
            "Folder Monitor Service Manager\n\n"
            "Enhanced with Adaptive Learning Processor\n"
            "Automatically improves classification accuracy over time\n\n"
            "Features:\n"
            "• Three-category classification (Research Instruments, Software, Non-Instruments)\n"
            "• Vendor-based classification (uses supplier column)\n"
            "• Adaptive learning processor\n"
            "• Automatic keyword discovery\n"
            "• Learning analytics and reports\n\n"
            "Classification Logic:\n"
            "• Vendor names (e.g., 'EMPIRE OFFICE INC' → Non-Instrument)\n"
            "• Description keywords (fallback)\n"
            "• Intelligent overlap handling\n\n"
            "Keyboard Shortcuts:\n"
            "Ctrl+S: Save Config\n"
            "Ctrl+O: Load Config\n"
            "F5: Restart Service")

    def _save_config(self):
        """Save current settings to config files."""
        # Save service config (old format for compatibility)
        service_config = {
            'service_path': self.service_path_var.get(),
            'startup_type': self.startup_var.get(),
            'interactive': self.interactive_var.get()
        }
        
        # Save monitor config (new format)
        monitor_config = {
            'watch_directory': self.watch_dir_var.get(),
            'output_directory': self.output_dir_var.get(),
            'hardware_keywords_file': self.hw_keywords_var.get(),
            'software_keywords_file': self.sw_keywords_var.get(),
            'non_instrument_keywords_file': self.ni_keywords_var.get(),
            'use_adaptive_processor': self.use_adaptive_var.get(),
            'learning_mode': self.learning_mode_var.get(),
            'min_occurrences': self.min_occurrences_var.get(),
            'confidence_threshold': self.confidence_threshold_var.get()
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(service_config, f, indent=2)
            with open(MONITOR_CONFIG_FILE, 'w') as f:
                json.dump(monitor_config, f, indent=2)
            
            self._log_message("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully")
        except Exception as e:
            self._log_message(f"Failed to save config: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def _load_config(self):
        """Load settings from config files."""
        try:
            # Load service config
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    service_config = json.load(f)
                
                service_path = service_config.get('service_path', '')
                if service_path and not os.path.isfile(service_path):
                    self._log_message(f"Warning: Service script not found: {service_path}", "WARN")
                
                self.service_path_var.set(service_path)
                self.startup_var.set(service_config.get('startup_type', 'manual'))
                self.interactive_var.set(service_config.get('interactive', False))
            
            # Load monitor config with defaults
            try:
                from config import config
                # Use defaults from the config system
                self.watch_dir_var.set(config.get('watch_directory', ''))
                self.output_dir_var.set(config.get('output_directory', ''))
                self.hw_keywords_var.set(str(config.hardware_keywords_file))
                self.sw_keywords_var.set(str(config.software_keywords_file))
                # Set default for non-instrument keywords if not in config
                self.ni_keywords_var.set(str(config.get('non_instrument_keywords_file', 'non_instrument_keywords.txt')))
                
                # Override with saved config if it exists
                if os.path.exists(MONITOR_CONFIG_FILE):
                    with open(MONITOR_CONFIG_FILE, 'r') as f:
                        monitor_config = json.load(f)
                    
                    self.watch_dir_var.set(monitor_config.get('watch_directory', self.watch_dir_var.get()))
                    self.output_dir_var.set(monitor_config.get('output_directory', self.output_dir_var.get()))
                    self.hw_keywords_var.set(monitor_config.get('hardware_keywords_file', self.hw_keywords_var.get()))
                    self.sw_keywords_var.set(monitor_config.get('software_keywords_file', self.sw_keywords_var.get()))
                    self.ni_keywords_var.set(monitor_config.get('non_instrument_keywords_file', self.ni_keywords_var.get()))
                    
                    # Load adaptive processor settings
                    self.use_adaptive_var.set(monitor_config.get('use_adaptive_processor', True))
                    self.learning_mode_var.set(monitor_config.get('learning_mode', True))
                    self.min_occurrences_var.set(monitor_config.get('min_occurrences', '5'))
                    self.confidence_threshold_var.set(monitor_config.get('confidence_threshold', '0.7'))
                    
                    # Update adaptive controls state
                    self._toggle_adaptive_controls()
                
            except ImportError:
                # Fallback if config module not available
                if os.path.exists(MONITOR_CONFIG_FILE):
                    with open(MONITOR_CONFIG_FILE, 'r') as f:
                        monitor_config = json.load(f)
                    
                    self.watch_dir_var.set(monitor_config.get('watch_directory', ''))
                    self.output_dir_var.set(monitor_config.get('output_directory', ''))
                    self.hw_keywords_var.set(monitor_config.get('hardware_keywords_file', ''))
                    self.sw_keywords_var.set(monitor_config.get('software_keywords_file', ''))
                    self.ni_keywords_var.set(monitor_config.get('non_instrument_keywords_file', ''))
                    
                    # Load adaptive processor settings (fallback)
                    self.use_adaptive_var.set(monitor_config.get('use_adaptive_processor', True))
                    self.learning_mode_var.set(monitor_config.get('learning_mode', True))
                    self.min_occurrences_var.set(monitor_config.get('min_occurrences', '5'))
                    self.confidence_threshold_var.set(monitor_config.get('confidence_threshold', '0.7'))
                    
                    # Update adaptive controls state
                    self._toggle_adaptive_controls()
            
            self._log_message("Configuration loaded successfully")
            
        except FileNotFoundError:
            self._log_message("No configuration file found, using defaults")
        except Exception as e:
            self._log_message(f"Failed to load config: {e}", "ERROR")

    def _run_cmd(self, action):
        """Run command in a separate thread."""
        errors = self._validate_inputs()
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return
        
        # Save monitor config before running service commands
        self._save_monitor_config()
        
        # Disable buttons and create progress bar
        self._set_buttons_state('disabled')
        progress = ttk.Progressbar(self, mode='indeterminate')
        progress.grid(row=11, column=0, columnspan=3, sticky='ew', padx=10, pady=2)
        progress.start()
        
        def run_in_thread():
            try:
                self._execute_command(action)
            finally:
                self.after(0, lambda: [
                    self._set_buttons_state('normal'),
                    progress.destroy()
                ])
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    def _execute_command(self, action):
        """Execute the actual command with improved error handling."""
        svc = self.service_path_var.get().strip()
        svc = get_short_path(svc)
        
        # Build options
        opts = []
        if action in ('install','update'):
            if self.user_var.get().strip():
                opts += ['--username', self.user_var.get().strip()]
            if self.pass_var.get().strip():
                opts += ['--password', self.pass_var.get().strip()]
            if self.startup_var.get():
                opts += ['--startup', self.startup_var.get()]
            if self.interactive_var.get():
                opts += ['--interactive']
        
        cmd = [sys.executable, svc] + opts + [action]
        
        def update_log_start():
            self.log_text.delete('1.0', tk.END)
            self._log_message(f"Running: {' '.join(cmd)}")
            self._log_message(f"Monitor config saved to: {MONITOR_CONFIG_FILE}")
        
        self.after(0, update_log_start)
        self.after(0, lambda: self.status_var.set(f"Executing {action}..."))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            self.after(0, lambda: self._log_message(result.stdout))
            self.after(0, lambda: self.status_var.set("Command completed successfully"))
            self.after(0, lambda: messagebox.showinfo("Success", "Command completed successfully. See log for details."))
        except subprocess.TimeoutExpired:
            self.after(0, lambda: self._log_message("Command timed out", "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed - timeout"))
            self.after(0, lambda: messagebox.showerror("Timeout", "Command timed out after 30 seconds"))
        except subprocess.CalledProcessError as e:
            detail = f"Return code: {e.returncode}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}"
            self.after(0, lambda: self._log_message(detail, "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed"))
            self.after(0, lambda: messagebox.showerror("Failed", "Error occurred. See log for details."))
        except Exception as e:
            self.after(0, lambda: self._log_message(f"Unexpected error: {e}", "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed"))
            self.after(0, lambda: messagebox.showerror("Error", f"Unexpected error: {e}"))
        finally:
            self.after(3000, lambda: self.status_var.set("Ready"))

if __name__ == '__main__':
    app = ServiceGUI()
    app.mainloop()