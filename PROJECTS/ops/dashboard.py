#!/usr/bin/env python3
"""
Pipeline Status Dashboard with HTTPS
=====================================
Real-time monitoring dashboard on HTTPS port 443

Access: https://localhost (accept self-signed certificate warning)
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "src" / "services" / "cross-reference" / "results"
OPS_DIR = Path(__file__).resolve().parent

# HTML Template (Simplified)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pipeline Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            color: #f0883e;
            margin-bottom: 20px;
            font-size: 24px;
        }
        .status-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status-card.active {
            border-color: #1f6feb;
        }
        .card-title {
            font-size: 12px;
            text-transform: uppercase;
            color: #8b949e;
            margin-bottom: 10px;
        }
        .card-value {
            font-size: 18px;
            font-weight: 600;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
        }
        .badge-running {
            background: rgba(31, 111, 235, 0.2);
            color: #79c0ff;
        }
        .badge-success {
            background: rgba(35, 134, 54, 0.2);
            color: #3fb950;
        }
        .badge-failed {
            background: rgba(218, 54, 51, 0.2);
            color: #ff7b72;
        }
        .badge-idle {
            background: rgba(139, 148, 158, 0.2);
            color: #8b949e;
        }
        .runs-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .runs-table th {
            background: #161b22;
            padding: 10px;
            text-align: left;
            font-size: 11px;
            text-transform: uppercase;
            color: #8b949e;
            border-bottom: 1px solid #30363d;
        }
        .runs-table td {
            padding: 10px;
            border-bottom: 1px solid #30363d;
        }
        .runs-table tr:hover {
            background: #0d1117;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #30363d;
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: #1f6feb;
            width: 0%;
            transition: width 0.3s ease;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #30363d;
            color: #8b949e;
            font-size: 12px;
        }
        code {
            background: #161b22;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Pipeline Monitor</h1>

        <div class="status-card active" id="current-run">
            <div class="card-title">Current Status</div>
            <div class="card-value">
                <span class="status-badge badge-idle" id="status-badge">IDLE</span>
                <span id="status-text">Waiting for input file...</span>
            </div>
            <div id="status-details" style="margin-top: 10px; font-size: 13px; color: #8b949e;"></div>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
            </div>
        </div>

        <div class="status-card">
            <div class="card-title">Recent Runs (Last 5)</div>
            <table class="runs-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>File</th>
                        <th>Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="runs-tbody">
                    <tr><td colspan="4" style="text-align: center; color: #8b949e;">No runs yet</td></tr>
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p><strong>Folder Monitor:</strong> Watching <code>data/som-in/</code> for new Excel files</p>
            <p><strong>Results:</strong> <code>src/services/cross-reference/results/crossref_results_*.xlsx</code></p>
            <p><strong>Logs:</strong> <code>src/services/cross-reference/results/</code></p>
            <p style="margin-top: 10px;">Last updated: <span id="update-time">-</span></p>
        </div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                // Update current status
                const badge = document.getElementById('status-badge');
                const text = document.getElementById('status-text');
                const details = document.getElementById('status-details');

                if (data.current_run) {
                    badge.className = 'status-badge badge-running';
                    badge.textContent = 'RUNNING';
                    text.textContent = data.current_run.stage || 'Processing...';
                    details.innerHTML = `
                        <div>File: ${data.current_run.file}</div>
                        <div>Started: ${new Date(data.current_run.started).toLocaleString()}</div>
                        <div>Duration: ${data.current_run.duration}</div>
                    `;
                    document.getElementById('progress-fill').style.width = (data.current_run.progress || 0) + '%';
                } else {
                    badge.className = 'status-badge badge-idle';
                    badge.textContent = 'IDLE';
                    text.textContent = 'Waiting for input file...';
                    details.innerHTML = '';
                    document.getElementById('progress-fill').style.width = '0%';
                }

                // Update recent runs
                const tbody = document.getElementById('runs-tbody');
                if (data.recent_runs && data.recent_runs.length > 0) {
                    tbody.innerHTML = data.recent_runs.map(run => `
                        <tr>
                            <td>${new Date(run.time).toLocaleString()}</td>
                            <td style="font-size: 12px;">${run.file}</td>
                            <td>${run.duration}</td>
                            <td><span class="status-badge ${run.status === 'success' ? 'badge-success' : 'badge-failed'}">${run.status.toUpperCase()}</span></td>
                        </tr>
                    `).join('');
                }

                document.getElementById('update-time').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Update error:', error);
            }
        }

        // Update every 5 seconds
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    """Render dashboard."""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/status")
def api_status():
    """Get current pipeline status."""
    status = {
        "current_run": None,
        "recent_runs": []
    }

    if not LOGS_DIR.exists():
        return jsonify(status)

    # Check for running pipeline
    monitor_log = LOGS_DIR / "monitor_service.log"
    if monitor_log.exists():
        try:
            with open(monitor_log, "r", encoding="utf-8") as f:
                content = f.read()
                if "PIPELINE STARTED" in content or "RUN #" in content:
                    # Extract current run info
                    lines = content.split("\n")
                    for i, line in enumerate(reversed(lines)):
                        if "RUN #" in line or "PIPELINE STARTED" in line:
                            status["current_run"] = {
                                "stage": "Running...",
                                "file": "Processing",
                                "started": datetime.now().isoformat(),
                                "duration": "...",
                                "progress": 30
                            }
                            break
        except:
            pass

    # Get recent runs from pipeline logs
    log_files = sorted(LOGS_DIR.glob("pipeline_*.log"), reverse=True)[:5]

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

                # Extract info
                time_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)
                file_match = re.search(r"Input file:\s*(.+?)$", content, re.MULTILINE)
                duration_match = re.search(r"finished in ([\d.]+) s", content, re.IGNORECASE)

                run = {
                    "time": time_match.group(1) if time_match else "-",
                    "file": file_match.group(1).strip()[:30] if file_match else "-",
                    "duration": f"{int(float(duration_match.group(1))/60)}m" if duration_match else "-",
                    "status": "success" if "PIPELINE COMPLETE" in content and "FAILED" not in content else "failed"
                }

                status["recent_runs"].append(run)
        except:
            pass

    return jsonify(status)


if __name__ == "__main__":
    # Load HTTPS certificates
    cert_file = OPS_DIR / "cert.pem"
    key_file = OPS_DIR / "key.pem"

    # Check if certificates exist, if not create them
    if not cert_file.exists() or not key_file.exists():
        print("Generating self-signed HTTPS certificate...")
        try:
            import subprocess
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(key_file), "-out", str(cert_file),
                "-days", "365", "-nodes",
                "-subj", "/C=US/ST=State/L=City/O=Org/CN=localhost"
            ], check=True, capture_output=True)
            print("Certificate created successfully")
        except Exception as e:
            print(f"Warning: Could not create certificate: {e}")
            print("Dashboard will run without HTTPS")
            app.run(host="0.0.0.0", port=443, debug=False)
            exit(0)

    # Run with HTTPS
    try:
        app.run(
            host="0.0.0.0",
            port=443,
            ssl_context=(str(cert_file), str(key_file)),
            debug=False
        )
    except PermissionError:
        print("Error: Port 443 requires administrator privileges")
        print("Run the setup as Administrator")
        exit(1)
