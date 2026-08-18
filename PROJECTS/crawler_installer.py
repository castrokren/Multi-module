#!/usr/bin/env python3
"""
CRAWLER PIPELINE DEPLOYMENT CONTROL CENTER
Professional installer & deployment management application

Beautiful, one-click deployment automation for the Crawler PDF processing pipeline.
Handles setup, scheduling, monitoring, and manual updates with a refined GUI.
"""

import sys
import os
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QCheckBox, QComboBox,
    QTabWidget, QFrame, QScrollArea, QDialog, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QRect
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPixmap, QPainter, QPen, QBrush,
    QLinearGradient, QIcon
)
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve


class StatusIndicator(QWidget):
    """Animated status indicator (dot) showing deployment status."""

    def __init__(self, status="idle"):
        super().__init__()
        self.status = status
        self.setFixedSize(20, 20)
        self.animation = QPropertyAnimation(self, b"geometry")

    def set_status(self, status: str):
        """Set status: 'idle' (gray), 'running' (blue), 'success' (green), 'error' (red)"""
        self.status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = {
            "idle": QColor("#9CA3AF"),
            "running": QColor("#3B82F6"),
            "success": QColor("#10B981"),
            "error": QColor("#EF4444"),
        }

        color = colors.get(self.status, QColor("#9CA3AF"))

        if self.status == "running":
            # Pulsing animation for running state
            painter.setOpacity(0.7 + 0.3 * (datetime.now().microsecond % 1000000) / 1000000)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 16, 16)


class DeploymentThread(QThread):
    """Background thread for deployment operations."""

    status_changed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, operation: str, project_root: str):
        super().__init__()
        self.operation = operation
        self.project_root = project_root

    def run(self):
        try:
            if self.operation == "setup":
                self._setup_deployment()
            elif self.operation == "update":
                self._manual_update()
            elif self.operation == "test":
                self._test_deployment()
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

    def _setup_deployment(self):
        """Run the PowerShell setup script."""
        self.log_message.emit("🔧 Setting up automatic deployment...")
        self.status_changed.emit("running")

        ps_script = Path(self.project_root) / "setup_deployment.ps1"

        if not ps_script.exists():
            self.finished.emit(False, "Setup script not found")
            return

        try:
            # Run PowerShell script
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)],
                capture_output=True,
                text=True,
                timeout=300
            )

            self.log_message.emit(result.stdout)
            if result.returncode == 0:
                self.log_message.emit("✅ Deployment setup complete!")
                self.status_changed.emit("success")
                self.finished.emit(True, "Deployment automation is now active")
            else:
                self.log_message.emit(f"❌ Setup failed: {result.stderr}")
                self.finished.emit(False, "Setup script failed")
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Setup timed out")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _manual_update(self):
        """Run manual update."""
        self.log_message.emit("📦 Checking for updates...")
        self.status_changed.emit("running")

        update_script = Path(self.project_root) / "update.bat"

        if not update_script.exists():
            self.finished.emit(False, "Update script not found")
            return

        try:
            result = subprocess.run(
                [str(update_script)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=600
            )

            self.log_message.emit(result.stdout)
            if result.returncode == 0:
                self.log_message.emit("✅ Update complete!")
                self.status_changed.emit("success")
                self.finished.emit(True, "Code updated successfully")
            else:
                self.log_message.emit(result.stderr)
                self.finished.emit(False, "Update failed")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _test_deployment(self):
        """Test deployment configuration."""
        self.log_message.emit("🧪 Testing deployment configuration...")
        self.status_changed.emit("running")

        try:
            # Check critical files exist
            checks = [
                (Path(self.project_root) / "update.bat", "Update script"),
                (Path(self.project_root) / "setup_deployment.ps1", "Setup script"),
                (Path(self.project_root) / "src/services/pipeline.py", "Pipeline script"),
            ]

            all_pass = True
            for path, name in checks:
                if path.exists():
                    self.log_message.emit(f"✅ {name}: OK")
                else:
                    self.log_message.emit(f"❌ {name}: NOT FOUND at {path}")
                    all_pass = False

            # Check git
            try:
                result = subprocess.run(
                    ["git", "status"],
                    capture_output=True,
                    cwd=Path(self.project_root).parent,
                    timeout=10
                )
                if result.returncode == 0:
                    self.log_message.emit("✅ Git repository: OK")
                else:
                    self.log_message.emit("⚠️ Git status check failed")
                    all_pass = False
            except:
                self.log_message.emit("⚠️ Git not found (will still work, but manual pulls needed)")

            if all_pass:
                self.log_message.emit("\n✅ All checks passed! System is ready.")
                self.status_changed.emit("success")
                self.finished.emit(True, "All systems operational")
            else:
                self.status_changed.emit("error")
                self.finished.emit(False, "Some checks failed - see logs")
        except Exception as e:
            self.finished.emit(False, str(e))


class ControlCenter(QMainWindow):
    """Main deployment control center application."""

    def __init__(self):
        super().__init__()
        self.project_root = Path(__file__).parent
        self.deployment_thread: Optional[DeploymentThread] = None
        self.init_ui()
        self.setWindowTitle("🚀 Crawler Pipeline Control Center")
        self.setWindowIcon(self.create_icon())
        self.resize(1000, 700)
        self.setStyleSheet(self.get_stylesheet())

    def create_icon(self) -> QIcon:
        """Create application icon (colored square)."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#3B82F6"))

        painter = QPainter(pixmap)
        painter.setFont(QFont("Arial", 32, QFont.Bold))
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "▶")
        painter.end()

        return QIcon(pixmap)

    def get_stylesheet(self) -> str:
        """Return comprehensive stylesheet for the application."""
        return """
        QMainWindow {
            background-color: #0F172A;
            color: #E2E8F0;
        }

        QLabel {
            color: #E2E8F0;
        }

        QPushButton {
            background-color: #3B82F6;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 13px;
        }

        QPushButton:hover {
            background-color: #2563EB;
        }

        QPushButton:pressed {
            background-color: #1D4ED8;
        }

        QPushButton:disabled {
            background-color: #6B7280;
            color: #9CA3AF;
        }

        QPushButton#successBtn {
            background-color: #10B981;
        }

        QPushButton#successBtn:hover {
            background-color: #059669;
        }

        QPushButton#dangerBtn {
            background-color: #EF4444;
        }

        QPushButton#dangerBtn:hover {
            background-color: #DC2626;
        }

        QTextEdit {
            background-color: #1E293B;
            color: #E2E8F0;
            border: 1px solid #334155;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 11px;
            padding: 10px;
        }

        QProgressBar {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 4px;
            height: 8px;
        }

        QProgressBar::chunk {
            background-color: #3B82F6;
            border-radius: 2px;
        }

        QTabWidget::pane {
            border: 1px solid #334155;
        }

        QTabBar::tab {
            background-color: #1E293B;
            color: #94A3B8;
            padding: 8px 16px;
            border: 1px solid #334155;
        }

        QTabBar::tab:selected {
            background-color: #0F172A;
            color: #3B82F6;
            border-bottom: 2px solid #3B82F6;
        }

        QFrame {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 6px;
        }
        """

    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header = self.create_header()
        main_layout.addLayout(header)

        # Status section
        status_frame = self.create_status_frame()
        main_layout.addLayout(status_frame)

        # Tabs for different sections
        tabs = QTabWidget()
        tabs.addTab(self.create_setup_tab(), "⚙️ Setup")
        tabs.addTab(self.create_monitor_tab(), "📊 Monitor")
        tabs.addTab(self.create_logs_tab(), "📋 Logs")
        main_layout.addWidget(tabs)

        # Footer
        footer = self.create_footer()
        main_layout.addLayout(footer)

    def create_header(self) -> QVBoxLayout:
        """Create the header section."""
        layout = QVBoxLayout()

        title = QLabel("🚀 Crawler Pipeline Control Center")
        title_font = QFont("Helvetica Neue", 24, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #3B82F6;")

        subtitle = QLabel("Automated deployment management for PDF processing pipeline")
        subtitle_font = QFont("Helvetica", 12)
        subtitle_font.setItalic(True)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: #94A3B8; margin-top: -5px;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        return layout

    def create_status_frame(self) -> QHBoxLayout:
        """Create the status summary frame."""
        layout = QHBoxLayout()

        # Git Status
        git_layout = QHBoxLayout()
        self.git_indicator = StatusIndicator("idle")
        git_label = QLabel("Git Repository")
        git_label.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.git_status = QLabel("Not checked")
        git_layout.addWidget(self.git_indicator)
        git_layout.addWidget(git_label)
        git_layout.addWidget(self.git_status)
        git_layout.addStretch()

        # Deployment Status
        deploy_layout = QHBoxLayout()
        self.deploy_indicator = StatusIndicator("idle")
        deploy_label = QLabel("Deployment Status")
        deploy_label.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.deploy_status = QLabel("Not configured")
        deploy_layout.addWidget(self.deploy_indicator)
        deploy_layout.addWidget(deploy_label)
        deploy_layout.addWidget(self.deploy_status)
        deploy_layout.addStretch()

        # Last Update
        update_layout = QHBoxLayout()
        self.update_indicator = StatusIndicator("idle")
        update_label = QLabel("Last Update")
        update_label.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.update_status = QLabel("Never")
        update_layout.addWidget(self.update_indicator)
        update_layout.addWidget(update_label)
        update_layout.addWidget(self.update_status)
        update_layout.addStretch()

        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.addLayout(git_layout)
        frame_layout.addLayout(deploy_layout)
        frame_layout.addLayout(update_layout)

        layout.addWidget(frame)
        return layout

    def create_setup_tab(self) -> QWidget:
        """Create the Setup tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Instructions
        instructions = QLabel(
            "🔧 SETUP DEPLOYMENT AUTOMATION\n\n"
            "One-click setup to enable automatic daily deployments.\n"
            "Your pipeline will update every day at 6:00 AM with the latest code.\n\n"
            "This will:\n"
            "• Create required directories\n"
            "• Register Windows Task Scheduler job\n"
            "• Enable automatic GitHub sync\n"
            "• Configure backup management"
        )
        instructions.setFont(QFont("Helvetica", 11))
        instructions.setStyleSheet("color: #CBD5E1; padding: 15px; background-color: #0F172A; border-left: 4px solid #3B82F6;")
        layout.addWidget(instructions)

        # Action buttons
        button_layout = QHBoxLayout()

        setup_btn = QPushButton("✅ Setup Deployment")
        setup_btn.setObjectName("successBtn")
        setup_btn.setFixedHeight(50)
        setup_btn.setFont(QFont("Helvetica", 12, QFont.Bold))
        setup_btn.clicked.connect(self.start_setup)
        button_layout.addWidget(setup_btn)

        test_btn = QPushButton("🧪 Test Configuration")
        test_btn.setFixedHeight(50)
        test_btn.setFont(QFont("Helvetica", 12, QFont.Bold))
        test_btn.clicked.connect(self.start_test)
        button_layout.addWidget(test_btn)

        layout.addLayout(button_layout)

        # Progress
        self.setup_progress = QProgressBar()
        self.setup_progress.setVisible(False)
        layout.addWidget(self.setup_progress)

        # Output
        self.setup_output = QTextEdit()
        self.setup_output.setReadOnly(True)
        self.setup_output.setPlaceholderText("Setup output will appear here...")
        layout.addWidget(self.setup_output)

        return widget

    def create_monitor_tab(self) -> QWidget:
        """Create the Monitor tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Status display
        status_label = QLabel("📊 DEPLOYMENT STATUS")
        status_label.setFont(QFont("Helvetica", 13, QFont.Bold))
        status_label.setStyleSheet("color: #3B82F6;")
        layout.addWidget(status_label)

        # Info grid
        info_layout = QVBoxLayout()

        self.next_run_label = QLabel("Next scheduled run: 6:00 AM (daily)")
        self.next_run_label.setFont(QFont("Helvetica", 11))
        info_layout.addWidget(self.next_run_label)

        self.last_run_label = QLabel("Last run: Never")
        self.last_run_label.setFont(QFont("Helvetica", 11))
        info_layout.addWidget(self.last_run_label)

        self.config_label = QLabel("Configuration: Checking...")
        self.config_label.setFont(QFont("Helvetica", 11))
        info_layout.addWidget(self.config_label)

        layout.addLayout(info_layout)

        # Manual update section
        update_label = QLabel("📦 MANUAL UPDATE")
        update_label.setFont(QFont("Helvetica", 13, QFont.Bold))
        update_label.setStyleSheet("color: #3B82F6; margin-top: 20px;")
        layout.addWidget(update_label)

        update_btn = QPushButton("🔄 Check for Updates Now")
        update_btn.setFixedHeight(40)
        update_btn.setFont(QFont("Helvetica", 11, QFont.Bold))
        update_btn.clicked.connect(self.start_update)
        layout.addWidget(update_btn)

        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        layout.addWidget(self.update_progress)

        layout.addStretch()

        return widget

    def create_logs_tab(self) -> QWidget:
        """Create the Logs tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Buttons
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh Logs")
        refresh_btn.setFixedWidth(150)
        refresh_btn.clicked.connect(self.refresh_logs)
        button_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑️ Clear Logs")
        clear_btn.setFixedWidth(150)
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self.clear_logs)
        button_layout.addWidget(clear_btn)

        open_btn = QPushButton("📁 Open Log File")
        open_btn.setFixedWidth(150)
        open_btn.clicked.connect(self.open_log_file)
        button_layout.addWidget(open_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setPlaceholderText("Deployment logs will appear here...\n\nLogs are stored at: logs/deployment.log")
        layout.addWidget(self.log_display)

        return widget

    def create_footer(self) -> QHBoxLayout:
        """Create the footer section."""
        layout = QHBoxLayout()

        footer_label = QLabel("v1.0 • Crawler Pipeline Deployment System • By Claude")
        footer_label.setFont(QFont("Helvetica", 9))
        footer_label.setStyleSheet("color: #64748B;")
        layout.addWidget(footer_label)

        layout.addStretch()

        help_btn = QPushButton("? Help")
        help_btn.setFixedWidth(80)
        help_btn.setFixedHeight(30)
        help_btn.clicked.connect(self.show_help)
        layout.addWidget(help_btn)

        return layout

    def start_setup(self):
        """Start the setup deployment thread."""
        if self.deployment_thread and self.deployment_thread.isRunning():
            QMessageBox.warning(self, "In Progress", "An operation is already running.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Setup",
            "This will set up automatic daily deployments.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.deployment_thread = DeploymentThread("setup", str(self.project_root))
        self.deployment_thread.log_message.connect(self.append_setup_log)
        self.deployment_thread.finished.connect(self.on_setup_finished)
        self.setup_progress.setVisible(True)
        self.setup_output.clear()
        self.deployment_thread.start()

    def start_update(self):
        """Start manual update thread."""
        if self.deployment_thread and self.deployment_thread.isRunning():
            QMessageBox.warning(self, "In Progress", "An operation is already running.")
            return

        self.deployment_thread = DeploymentThread("update", str(self.project_root))
        self.deployment_thread.log_message.connect(self.append_setup_log)
        self.deployment_thread.finished.connect(self.on_update_finished)
        self.setup_progress.setVisible(True)
        self.setup_output.clear()
        self.deployment_thread.start()

    def start_test(self):
        """Start test thread."""
        if self.deployment_thread and self.deployment_thread.isRunning():
            QMessageBox.warning(self, "In Progress", "An operation is already running.")
            return

        self.deployment_thread = DeploymentThread("test", str(self.project_root))
        self.deployment_thread.log_message.connect(self.append_setup_log)
        self.deployment_thread.finished.connect(self.on_test_finished)
        self.setup_progress.setVisible(True)
        self.setup_output.clear()
        self.deployment_thread.start()

    def append_setup_log(self, message: str):
        """Append message to setup log."""
        self.setup_output.append(message)

    def on_setup_finished(self, success: bool, message: str):
        """Handle setup completion."""
        self.setup_progress.setVisible(False)
        if success:
            QMessageBox.information(self, "Setup Complete", message)
            self.deploy_indicator.set_status("success")
            self.deploy_status.setText("✅ Active")
        else:
            QMessageBox.critical(self, "Setup Failed", message)
            self.deploy_indicator.set_status("error")
            self.deploy_status.setText("❌ Failed")

    def on_update_finished(self, success: bool, message: str):
        """Handle update completion."""
        self.setup_progress.setVisible(False)
        if success:
            QMessageBox.information(self, "Update Complete", message)
            self.update_indicator.set_status("success")
            self.update_status.setText(datetime.now().strftime("%Y-%m-%d %H:%M"))
        else:
            QMessageBox.critical(self, "Update Failed", message)
            self.update_indicator.set_status("error")

    def on_test_finished(self, success: bool, message: str):
        """Handle test completion."""
        self.setup_progress.setVisible(False)
        if success:
            QMessageBox.information(self, "Tests Passed", message)
        else:
            QMessageBox.warning(self, "Tests Failed", message)

    def refresh_logs(self):
        """Refresh the log display."""
        log_file = Path(self.project_root).parent / "logs" / "deployment.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                self.log_display.setText(f.read())
        else:
            self.log_display.setText("No logs found yet. Run a deployment to generate logs.")

    def clear_logs(self):
        """Clear the log file."""
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Clear all deployment logs?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            log_file = Path(self.project_root).parent / "logs" / "deployment.log"
            if log_file.exists():
                log_file.write_text("")
                self.log_display.clear()
                QMessageBox.information(self, "Success", "Logs cleared.")

    def open_log_file(self):
        """Open log file in default editor."""
        log_file = Path(self.project_root).parent / "logs" / "deployment.log"
        if log_file.exists():
            os.startfile(str(log_file))
        else:
            QMessageBox.information(self, "No Logs", "Log file not found.")

    def show_help(self):
        """Show help dialog."""
        help_text = """
CRAWLER PIPELINE CONTROL CENTER

1. SETUP: Click "Setup Deployment" to enable automatic daily updates at 6:00 AM

2. MONITOR: View deployment status and manually check for updates

3. LOGS: Review deployment activity and troubleshoot issues

Features:
• One-click automated setup
• Daily scheduled updates at 6:00 AM
• Manual update checking
• Automatic backups
• Comprehensive logging
• Production-ready deployment

Need help? See: DEPLOYMENT.md
        """
        QMessageBox.information(self, "Help", help_text)


def main():
    """Launch the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Crawler Pipeline Control Center")
    app.setApplicationVersion("1.0.0")

    window = ControlCenter()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
