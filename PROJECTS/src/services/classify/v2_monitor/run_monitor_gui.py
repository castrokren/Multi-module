#!/usr/bin/env python3
"""
GUI launcher for folder monitor configuration.
Entry point for v2_monitor configuration interface.

Usage:
    python run_monitor_gui.py
"""

from Updated_Monitor_UI import ServiceGUI

if __name__ == '__main__':
    app = ServiceGUI()
    app.mainloop()
