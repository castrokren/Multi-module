"""
Centralized configuration management for the Excel folder monitor application.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Configuration manager with defaults and validation."""
    
    DEFAULT_CONFIG = {
        "watch_directory": "\\\\research-cifs.nyumc.org\\omero_dev\\kren\\SOM_in",
        "output_directory": "D:\\SOM_in_labeled",
        "hardware_keywords_file": "research_instrument_keywords.txt",  # Updated for three-category system
        "software_keywords_file": "software_keywords.txt",
        "non_instrument_keywords_file": "non_instrument_keywords.txt",  # NEW: Non-Instrument category
        "file_extensions": [".xls", ".xlsx"],
        "ignore_temp_files": True,
        "ignore_labeled_files": True,
        "service_name": "MonitorFolderSvc",
        "service_display_name": "Excel Folder Monitor Service",
        "service_description": "Monitors a folder and processes Excel files when added or changed.",
        "log_level": "INFO",
        "process_timeout": 30
    }
    
    def __init__(self, config_file="monitor_config.json"):
        self.config_file = Path(config_file)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        """Load configuration from file, create with defaults if not exists."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
            else:
                # Create default config file
                self.save()
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
            print("Using default configuration.")
    
    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values."""
        self.config.update(updates)
    
    def validate(self):
        """Validate current configuration."""
        errors = []
        
        # Check required directories
        watch_dir = Path(self.get("watch_directory"))
        if not watch_dir.exists():
            errors.append(f"Watch directory does not exist: {watch_dir}")
        
        # Check keyword files (relative to script directory)
        script_dir = Path(__file__).parent
        hw_file = script_dir / self.get("hardware_keywords_file")
        sw_file = script_dir / self.get("software_keywords_file")
        ni_file = script_dir / self.get("non_instrument_keywords_file", "non_instrument_keywords.txt")
        
        if not hw_file.exists():
            errors.append(f"Research Instrument keywords file not found: {hw_file}")
        if not sw_file.exists():
            errors.append(f"Software keywords file not found: {sw_file}")
        if not ni_file.exists():
            errors.append(f"Non-Instrument keywords file not found: {ni_file}")
        
        return errors
    
    @property
    def watch_directory(self):
        return Path(self.get("watch_directory"))
    
    @property
    def output_directory(self):
        return Path(self.get("output_directory"))
    
    @property
    def hardware_keywords_file(self):
        return Path(__file__).parent / self.get("hardware_keywords_file")
    
    @property
    def software_keywords_file(self):
        return Path(__file__).parent / self.get("software_keywords_file")
    
    @property
    def non_instrument_keywords_file(self):
        return Path(__file__).parent / self.get("non_instrument_keywords_file", "non_instrument_keywords.txt")
    
    @property
    def file_extensions(self):
        return self.get("file_extensions", [".xls", ".xlsx"])

# Global config instance
config = Config()

# Convenience functions for backward compatibility
def get_watch_dir():
    return str(config.watch_directory)

def get_script_path():
    # For backward compatibility - return the classify script path
    return str(Path(__file__).parent / "classify_and_clean_dynamic.py")

def get_output_dir():
    return str(config.output_directory)