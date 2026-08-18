"""
Consolidated File Monitor v2.0
Unified watchdog-based folder monitoring with Excel processing.
"""

from .monitor import FileMonitor, ExcelFileHandler

__version__ = "2.0.0"
__all__ = ["FileMonitor", "ExcelFileHandler"]
