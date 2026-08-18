# Windows Server Deployment Checklist

## Quick Start (5 minutes)

### Step 1: Configure Email (2 min)
```bash
# Copy template
copy ops\.env.example ops\.env

# Edit ops\.env with your email settings
# - SMTP_USERNAME: your email address
# - SMTP_PASSWORD: app-specific password (not your regular password)
# - ALERT_RECIPIENTS: who gets failure alerts
```

**Where to get app passwords**:
- **Office 365**: https://account.activedirectory.windowsazure.com/
- **Gmail**: https://myaccount.google.com/apppasswords

### Step 2: Install Dependencies (2 min)
```powershell
# Open PowerShell in project root
cd C:\Projects\Crawler\PROJECTS

# Create virtual environment (first time only)
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
pip install watchdog flask flask-cors python-dotenv
```

### Step 3: Start Services (1 min)
```
Double-click: ops\start_monitor.bat

Or from PowerShell:
cd C:\Projects\Crawler\PROJECTS
python ops\folder_monitor_service.py
python ops\dashboard.py
```

### Step 4: Verify (1 min)
- Open dashboard: http://localhost:5000
- Place a test Excel file in: `data\som-in\`
- Monitor should detect it within 10 seconds
- Pipeline should start automatically

---

## Complete Deployment Checklist

### Pre-Deployment
- [ ] Windows Server 2016+ or Windows 10 Pro
- [ ] Python 3.8+ installed
- [ ] Network access to supplier websites confirmed
- [ ] SMTP credentials obtained (Office 365 or Gmail)
- [ ] Dedicated service account created (optional)

### Configuration
- [ ] Copied `ops\.env.example` to `ops\.env`
- [ ] Updated `SMTP_SERVER` for your email provider
- [ ] Updated `SMTP_USERNAME` with your email
- [ ] Updated `SMTP_PASSWORD` with app-specific password
- [ ] Updated `ALERT_RECIPIENTS` with team emails
- [ ] Verified `.env` file has correct settings

### Installation
- [ ] Created virtual environment: `python -m venv venv`
- [ ] Activated virtual environment: `.\venv\Scripts\Activate.ps1`
- [ ] Installed requirements: `pip install -r requirements.txt`
- [ ] Installed monitoring packages: `pip install watchdog flask flask-cors python-dotenv`
- [ ] Verified Python packages: `python -c "import watchdog, flask"`

### Directory Setup
- [ ] Created `data\som-in\` (input folder)
- [ ] Created `data\som-in-labeled\` (output folder)
- [ ] Created `data\scraped-pdfs\` (PDF storage)
- [ ] Created `src\services\cross-reference\results\` (results folder)
- [ ] Verified 100+ GB free disk space for PDFs

### Service Testing
- [ ] Started `folder_monitor_service.py` without errors
- [ ] Started `dashboard.py` without errors
- [ ] Dashboard accessible at http://localhost:5000
- [ ] Email test passed: `python ops\test_email.py`
- [ ] Placed test Excel file in `data\som-in\`
- [ ] Verified monitor detected file within 10 seconds
- [ ] Verified pipeline started automatically

### Windows Task Scheduler Setup
- [ ] Created scheduled task "CrawlerPipelineMonitor"
- [ ] Set trigger: "At system startup"
- [ ] Set action: Run `ops\start_monitor.bat`
- [ ] Configured to restart on failure every 5 minutes
- [ ] Tested task: Right-click → Run

### Verification
- [ ] Reboot server
- [ ] Verify folder monitor started automatically
- [ ] Verify dashboard accessible after boot
- [ ] Check logs: `src\services\cross-reference\results\monitor_service.log`
- [ ] Verify pipeline completes successfully

### Documentation
- [ ] Created runbook for common issues
- [ ] Documented alert recipients and escalation
- [ ] Created backup schedule for results
- [ ] Documented log retention policy
- [ ] Added monitoring to server health checks

### Go-Live
- [ ] Team trained on dashboard usage
- [ ] Support contacted for escalation procedures
- [ ] Email distribution list created
- [ ] First production run completed successfully
- [ ] Results validated by research team
- [ ] Daily monitoring schedule established

---

## Daily Operations Checklist

### Morning (9:00 AM)
- [ ] Check dashboard: http://[server]:5000
- [ ] Review last night's pipeline run
- [ ] Check for any failure emails
- [ ] Verify input folder permissions

### Throughout Day
- [ ] Monitor new Excel file uploads
- [ ] Check dashboard for active runs
- [ ] Monitor available disk space
- [ ] Respond to any failure alerts

### End of Day (5:00 PM)
- [ ] Archive results files to backup location
- [ ] Review logs for any warnings
- [ ] Verify pipeline completed successfully
- [ ] Check disk usage trends

### Weekly
- [ ] Review all pipeline runs
- [ ] Check log file sizes (rotate if needed)
- [ ] Verify SMTP connectivity
- [ ] Review alert email volume
- [ ] Check supplier master list is current

### Monthly
- [ ] Archive old PDF folders to cheaper storage
- [ ] Review pipeline performance metrics
- [ ] Update supplier master list
- [ ] Clean old log files (>90 days)
- [ ] Run full system backup

---

## Troubleshooting Quick Reference

| Issue | Check | Fix |
|-------|-------|-----|
| Monitor not detecting files | File permissions, folder path | Verify `data\som-in` exists and is writable |
| Pipeline won't start | Logs, Python process | Check `monitor_service.log` for errors |
| Email alerts not sending | `.env` file, SMTP credentials | Run `python ops\test_email.py` |
| Dashboard not accessible | Port 5000, firewall | Check firewall rules, netstat -an \| findstr 5000 |
| Disk space low | `data\scraped-pdfs` size | Archive old PDFs, implement cleanup policy |
| Pipeline very slow | CPU/Network, supplier count | Increase concurrency, check network |
| Results file missing | Pipeline logs, last stage | Check if Stage 3 completed, review errors |

---

## Files Created

### Configuration
- `ops\.env` — Main configuration file (email, server settings)
- `ops\.env.example` — Template configuration

### Services
- `ops\folder_monitor_service.py` — Folder monitoring service
- `ops\dashboard.py` — Web dashboard (http://localhost:5000)
- `ops\email_alerter.py` — Email alerting module (integrated in monitor)

### Utilities
- `ops\start_monitor.bat` — Start services (double-click to run)
- `ops\stop_monitor.bat` — Stop services
- `ops\rotate_logs.ps1` — Log rotation script
- `ops\test_email.py` — Email configuration tester

### Documentation
- `ops\deployment_guide.md` — Complete deployment guide
- `ops\DEPLOYMENT_CHECKLIST.md` — This file

---

## Post-Deployment Monitoring

### Key Metrics to Track
- **Pipeline duration**: Should be 75-120 minutes (Stage 1 is bottleneck)
- **Match rate**: ~15-30% of items typically match to PDFs
- **Failure rate**: Should be <5% (1 failure per 20 runs)
- **Disk growth**: PDFs grow ~1-2 GB per week

### Alert Thresholds
- **High**: Pipeline > 3 hours (investigate network/concurrency)
- **Medium**: Disk < 10% free (archive old PDFs)
- **Low**: Failure rate > 10% (check supplier websites)

### Dashboard Metrics
- Active run status and progress
- Recent run history (last 30 runs)
- Success/failure ratio
- Estimated completion time
- Real-time log viewer

---

## Support Contacts

### For Issues With:
- **Pipeline logic**: Check `src/services/pipeline.py` and CONTEXT.md
- **Email setup**: Check `ops\.env` and run email test
- **Folder monitoring**: Check `ops\folder_monitor_service.py`
- **Dashboard**: Check `ops\dashboard.py` and port 5000
- **Windows Task Scheduler**: Windows documentation

### Resources
- [Deployment Guide](deployment_guide.md)
- [Pipeline Architecture](../PIPELINE_STRUCTURE.md)
- [Project Structure](../CLAUDE.md)
- [Status Report](../PIPELINE_STATUS_REPORT.md)

---

## Final Notes

✅ **You're ready to deploy when**:
1. Email configured and tested
2. Dependencies installed
3. Services start without errors
4. Test run completes successfully
5. Results file generated
6. Team trained on dashboard

🚀 **Go live by**:
1. Setting up Windows Task Scheduler
2. Starting services at boot
3. Training team on monitoring
4. Establishing alert escalation
5. Scheduling regular backups

📊 **Monitor daily**:
1. Check dashboard
2. Review failed runs
3. Verify disk space
4. Respond to alerts
5. Archive results

---

*Deployment Checklist v1.0 — Last updated 2026-05-12*
