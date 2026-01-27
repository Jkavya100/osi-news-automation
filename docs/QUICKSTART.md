# OSI News Automation - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
notepad .env  # Add your API keys
```

### 3. Test Pipeline
```bash
python run_automation.py --mode dry-run
```

### 4. Setup Automation
```bash
cd scripts
setup_windows_scheduler.bat
```

✅ **Done!** Pipeline will run every 3 hours automatically.

---

## 📋 Common Commands

### Run Pipeline
```bash
# Run once
python run_automation.py --mode once

# Test mode (no uploads)
python run_automation.py --mode dry-run

# Scheduled mode
python run_automation.py --mode scheduled
```

### Manage Scheduled Task
```bash
# View task
schtasks /query /tn "OSI News Automation"

# Run now
schtasks /run /tn "OSI News Automation"

# Disable
schtasks /change /tn "OSI News Automation" /disable

# Delete
schtasks /delete /tn "OSI News Automation" /f
```

### View Logs
```bash
# Today's log
type output\logs\automation_2026-01-21.log

# Last 50 lines
powershell "Get-Content output\logs\automation_2026-01-21.log -Tail 50"

# Search errors
findstr /i "error" output\logs\automation_*.log
```

### Check Output
```bash
# View generated files
dir output\json

# View pipeline stats
type output\json\pipeline_stats_*.json

# View social posts
type output\json\social_posts_*.json
```

---

## 🔧 Troubleshooting

### Task Not Running?
1. Check task status: `schtasks /query /tn "OSI News Automation"`
2. Run manually: `schtasks /run /tn "OSI News Automation"`
3. Check logs: `type output\logs\automation_*.log`

### Pipeline Errors?
1. Test components: `python run_automation.py --mode dry-run`
2. Check API keys in `.env`
3. Verify MongoDB is running: `sc query MongoDB`

### Need Help?
- 📚 Full guide: `docs/DEPLOYMENT.md`
- 📧 Support: support@osinews.com

---

## 📊 Expected Output

After each run, you'll find:
- ✅ Scraped articles in database
- ✅ Generated comprehensive articles
- ✅ Social media posts in `output/json/social_posts_*.json`
- ✅ Pipeline statistics in `output/json/pipeline_stats_*.json`
- ✅ Detailed logs in `output/logs/automation_*.log`

---

## 🎯 Next Steps

1. ✅ Customize news sources in `config/news_sources.yaml`
2. ✅ Adjust settings in `.env` (article count, languages, etc.)
3. ✅ Monitor first few runs via logs
4. ✅ Set up database backups
5. ✅ Configure alerts (email/Slack) for failures

---

**OSI News Automation System v1.0**
