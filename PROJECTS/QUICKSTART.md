# Pipeline Quick Start

## Installation (One-Click, 2 minutes)

**Just double-click:** `setup.bat`

That's it! The script will:
- Check Python
- Create virtual environment
- Install dependencies
- Generate HTTPS certificate
- Register with Windows auto-start
- Start services
- Open dashboard in browser

## First Run

1. **Wait** for setup to complete (~2 minutes)
2. **Browser warning** — Click "Proceed anyway" (self-signed certificate is normal)
3. **Dashboard** — You should see "Idle - Waiting for input file..."
4. **Done!** Pipeline is ready

## Daily Use

1. **Drop Excel files** into: `data\som-in\`
2. **Monitor detects** within 10 seconds
3. **Pipeline runs** automatically (75-120 minutes)
4. **Check dashboard** at: `https://localhost`
5. **Results file** created: `src/services/cross-reference/results/crossref_results_[timestamp].xlsx`

## Manual Controls

```
Start services:  start.bat
Stop services:   stop.bat
Dashboard:       https://localhost
Logs:           src/services/cross-reference/results/
```

## Troubleshooting

**Dashboard won't load?**
- Try: https://localhost (use HTTPS, not HTTP)
- Browser warning is normal, click "Proceed"

**Setup fails?**
- Python not installed: Download from https://www.python.org/
- Port 443 in use: Stop other services using port 443
- Review: `src/services/cross-reference/results/monitor_service.log`

**Pipeline won't start?**
- Check folder permissions: `data\som-in\`
- Check logs: `src/services/cross-reference/results/pipeline_*.log`
- Restart: `stop.bat` then `start.bat`

## Files Created During Setup

```
venv/                    — Python virtual environment
ops/cert.pem            — HTTPS certificate
ops/key.pem             — HTTPS private key
monitor_service.log     — Monitor activity log
pipeline_*.log          — Pipeline execution logs
crossref_results_*.xlsx — Final results (your output!)
```

## Service Auto-Start

After setup, the pipeline will **automatically start** on server reboot. No manual action needed.

---

That's all! Your pipeline is now fully deployed and operational.
