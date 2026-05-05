import sys
import os
import subprocess
import tkinter as tk
import threading
import json
import datetime
from tkinter import filedialog, messagebox, ttk

# Constants
DEFAULT_WINDOW_SIZE = "700x500"
LOG_HEIGHT = 10
LOG_WIDTH = 75
BUTTON_WIDTH = 10
SUPPORTED_ACTIONS = ['install', 'update', 'remove', 'start', 'stop', 'restart', 'debug']
CONFIG_FILE = 'service_config.json'

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
        x, y, _, _ = self.widget.bbox("insert")
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
        # Initialize StringVars with environment defaults if available
        self.service_path_var = tk.StringVar(value=os.environ.get('SERVICE_SCRIPT', ''))
        self.classify_path_var = tk.StringVar(value=os.environ.get('SCRIPT_PATH', ''))
        self.watch_dir_var = tk.StringVar(value=os.environ.get('WATCH_DIR', ''))
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.startup_var = tk.StringVar(value='manual')
        self.interactive_var = tk.BooleanVar()
        self.show_pass_var = tk.BooleanVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Store button references for state management
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
        
        # Configure grid weights for better resizing
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        # Service script
        tk.Label(self, text="Service Script (.py):").grid(row=0, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(self, textvariable=self.service_path_var, width=50).grid(row=0, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(self, text="Browse", command=self._browse_service).grid(row=0, column=2, padx=padx, pady=pady)
        
        # Classification script
        tk.Label(self, text="Classification Script (.py):").grid(row=1, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(self, textvariable=self.classify_path_var, width=50).grid(row=1, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(self, text="Browse", command=self._browse_classify).grid(row=1, column=2, padx=padx, pady=pady)
        
        # Watch directory
        tk.Label(self, text="Watch Directory:").grid(row=2, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(self, textvariable=self.watch_dir_var, width=50).grid(row=2, column=1, padx=padx, pady=pady, sticky='ew')
        tk.Button(self, text="Browse", command=self._browse_watch).grid(row=2, column=2, padx=padx, pady=pady)
        
        # Credentials
        tk.Label(self, text="Run as User (domain\\user):").grid(row=3, column=0, sticky='e', padx=padx, pady=pady)
        tk.Entry(self, textvariable=self.user_var, width=30).grid(row=3, column=1, sticky='w', padx=padx, pady=pady)
        tk.Label(self, text="Password:").grid(row=3, column=1, sticky='e', padx=(300,5), pady=pady)
        pass_entry = tk.Entry(self, textvariable=self.pass_var, show="*", width=20)
        pass_entry.grid(row=3, column=2, padx=padx, pady=pady)
        
        # Show password checkbox
        show_pass_cb = tk.Checkbutton(self, text="Show", variable=self.show_pass_var,
                                      command=lambda: self._toggle_password_visibility(pass_entry))
        show_pass_cb.grid(row=3, column=2, sticky='e', padx=(150, 5), pady=pady)
        
        # Add tooltips
        ToolTip(show_pass_cb, "Toggle password visibility")
        
        # Startup type
        tk.Label(self, text="Startup Type:").grid(row=4, column=0, sticky='e', padx=padx, pady=pady)
        tk.OptionMenu(self, self.startup_var, 'manual','auto','disabled','delayed').grid(row=4, column=1, sticky='w', padx=padx, pady=pady)
        
        # Interactive
        tk.Checkbutton(self, text="Interactive", variable=self.interactive_var).grid(row=4, column=2, sticky='w', padx=padx, pady=pady)
        
        # Log area with scrollbar
        log_frame = tk.Frame(self)
        log_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky='nsew')
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=LOG_HEIGHT, width=LOG_WIDTH)
        scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Action buttons
        button_frame = tk.Frame(self)
        button_frame.grid(row=6, column=0, columnspan=3, padx=padx, pady=pady)
        
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
        
        # Save/Load config buttons
        config_frame = tk.Frame(self)
        config_frame.grid(row=7, column=0, columnspan=3, padx=padx, pady=pady)
        tk.Button(config_frame, text="Save Config", command=self._save_config).grid(row=0, column=0, padx=padx, pady=pady)
        tk.Button(config_frame, text="Load Config", command=self._load_config).grid(row=0, column=1, padx=padx, pady=pady)
        
        # Status bar
        status_bar = tk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=8, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        
        # Bind keyboard shortcuts
        self.bind('<Control-s>', lambda e: self._save_config())
        self.bind('<Control-o>', lambda e: self._load_config())
        self.bind('<F5>', lambda e: self._run_cmd('restart'))

    def _browse_service(self):
        path = filedialog.askopenfilename(filetypes=[('Python Files','*.py')])
        if path:
            short = get_short_path(path)
            self.service_path_var.set(short)

    def _browse_classify(self):
        path = filedialog.askopenfilename(filetypes=[('Python Files','*.py')])
        if path:
            short = get_short_path(path)
            self.classify_path_var.set(short)

    def _browse_watch(self):
        path = filedialog.askdirectory()
        if path:
            self.watch_dir_var.set(path)

    def _validate_inputs(self):
        """Validate required inputs before running commands."""
        errors = []
        
        svc_path = self.service_path_var.get().strip()
        if not svc_path:
            errors.append("Service script path is required")
        elif not os.path.isfile(svc_path):
            errors.append("Service script file does not exist")
        
        cls_path = self.classify_path_var.get().strip()
        if not cls_path:
            errors.append("Classification script path is required")
        elif not os.path.isfile(cls_path):
            errors.append("Classification script file does not exist")
        
        watch_dir = self.watch_dir_var.get().strip()
        if watch_dir and not os.path.isdir(watch_dir):
            errors.append("Watch directory does not exist")
        
        # Validate user format if provided
        user = self.user_var.get().strip()
        if user and '\\' not in user:
            errors.append("User should be in format 'domain\\username'")
        
        return errors

    def _log_message(self, message, level="INFO"):
        """Add timestamped message to log."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {level}: {message}\n"
        self.log_text.insert(tk.END, formatted_msg)
        self.log_text.see(tk.END)  # Auto-scroll to bottom

    def _set_buttons_state(self, state):
        """Enable or disable all action buttons."""
        for btn in self.action_buttons:
            btn.config(state=state)

    def _toggle_password_visibility(self, entry):
        """Toggle password visibility."""
        entry.config(show="" if self.show_pass_var.get() else "*")

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo("About", 
            "Folder Monitor Service Manager\n\n"
            "Keyboard Shortcuts:\n"
            "Ctrl+S: Save Config\n"
            "Ctrl+O: Load Config\n"
            "F5: Restart Service")

    def _save_config(self):
        """Save current settings to a config file."""
        config = {
            'service_path': self.service_path_var.get(),
            'classify_path': self.classify_path_var.get(),
            'watch_dir': self.watch_dir_var.get(),
            'startup_type': self.startup_var.get(),
            'interactive': self.interactive_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            self._log_message("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully")
        except Exception as e:
            self._log_message(f"Failed to save config: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def _load_config(self):
        """Load settings from config file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Validate loaded paths
            service_path = config.get('service_path', '')
            if service_path and not os.path.isfile(service_path):
                self._log_message(f"Warning: Service script not found: {service_path}", "WARN")
            
            classify_path = config.get('classify_path', '')
            if classify_path and not os.path.isfile(classify_path):
                self._log_message(f"Warning: Classification script not found: {classify_path}", "WARN")
            
            self.service_path_var.set(service_path)
            self.classify_path_var.set(classify_path)
            self.watch_dir_var.set(config.get('watch_dir', ''))
            self.startup_var.set(config.get('startup_type', 'manual'))
            self.interactive_var.set(config.get('interactive', False))
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
        
        # Disable buttons and create progress bar in main thread
        self._set_buttons_state('disabled')
        progress = ttk.Progressbar(self, mode='indeterminate')
        progress.grid(row=9, column=0, columnspan=3, sticky='ew', padx=10, pady=2)
        progress.start()
        
        def run_in_thread():
            try:
                self._execute_command(action)
            finally:
                # Re-enable buttons and cleanup in main thread
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
        cls = self.classify_path_var.get().strip()
        cls = get_short_path(cls)
        watch = self.watch_dir_var.get().strip()
        
        # Build options before the action
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
        
        # Final command: python svc + opts + action
        cmd = [sys.executable, svc] + opts + [action]
        
        # Set environment
        env = os.environ.copy()
        env['WATCH_DIR'] = watch
        env['SCRIPT_PATH'] = cls
        
        # Clear log and log command (combine these)
        def update_log_start():
            self.log_text.delete('1.0', tk.END)
            self._log_message(f"Running: {' '.join(cmd)}")
            self._log_message(f"Environment: WATCH_DIR={watch}, SCRIPT_PATH={cls}")
        
        self.after(0, update_log_start)
        self.after(0, lambda: self.status_var.set(f"Executing {action}..."))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, 
                                  check=True, timeout=30)  # Add timeout
            self.after(0, lambda: self._log_message(result.stdout))
            self.after(0, lambda: self.status_var.set("Command completed successfully"))
            self.after(0, lambda: messagebox.showinfo("Success", "Command completed successfully. See log for details."))
        except subprocess.TimeoutExpired:
            self.after(0, lambda: self._log_message("Command timed out", "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed - timeout"))
            self.after(0, lambda: messagebox.showerror("Timeout", "Command timed out after 30 seconds"))
        except subprocess.CalledProcessError as e:
            detail = f"Return code: {e.returncode}\nCommand: {' '.join(cmd)}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}"
            self.after(0, lambda: self._log_message(detail, "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed"))
            self.after(0, lambda: messagebox.showerror("Failed", "Error occurred. See log for details."))
        except FileNotFoundError:
            self.after(0, lambda: self._log_message("Python executable or script not found", "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed - file not found"))
            self.after(0, lambda: messagebox.showerror("File Error", "Required files not found"))
        except Exception as e:
            self.after(0, lambda: self._log_message(f"Unexpected error: {e}", "ERROR"))
            self.after(0, lambda: self.status_var.set("Command failed - unexpected error"))
            self.after(0, lambda: messagebox.showerror("Error", f"Unexpected error occurred: {e}"))
        finally:
            # Reset status after a delay
            self.after(3000, lambda: self.status_var.set("Ready"))

if __name__ == '__main__':
    app = ServiceGUI()
    app.mainloop()
