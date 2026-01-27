# OSI News Automation System - Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Windows Deployment](#windows-deployment)
- [Configuration](#configuration)
- [Running the Pipeline](#running-the-pipeline)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements
- **OS**: Windows 10/11 or Windows Server 2019+
- **Python**: 3.11.9 or higher
- **MongoDB**: 4.4+ (local or remote)
- **RAM**: 8GB minimum (16GB recommended for image generation)
- **Storage**: 10GB free space minimum

### Required Software
1. **Python 3.11.9**
   - Download from [python.org](https://www.python.org/downloads/)
   - ✅ Add Python to PATH during installation

2. **MongoDB**
   - Download from [mongodb.com](https://www.mongodb.com/try/download/community)
   - Or use MongoDB Atlas (cloud)

3. **Git** (optional, for version control)
   - Download from [git-scm.com](https://git-scm.com/)

---

## Windows Deployment

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd "C:\Users\Jain\Desktop\OSI News Automation System\osi-news-automation"

# Install Python packages
pip install -r requirements.txt

# Verify installation
python -c "import torch; import transformers; print('✅ Dependencies installed')"
```

### Step 2: Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

**Required Configuration:**
- `MONGODB_URI` - MongoDB connection string
- `GROQ_API_KEY` - Groq API key for article generation
- `HOCALWIRE_API_KEY` - Hocalwire CMS API key
- `HOCALWIRE_API_URL` - Hocalwire API endpoint

**Optional Configuration:**
- `ENABLE_IMAGE_GENERATION` - Set to `true` for AI images
- `TRANSLATION_ENABLED` - Set to `true` for multi-language
- `MAX_ARTICLES_PER_RUN` - Number of articles to scrape (default: 50)

### Step 3: Test the Pipeline

```bash
# Run a dry-run test (no uploads)
python run_automation.py --mode dry-run

# Check output
dir output\json
dir output\logs
```

Expected output:
- ✅ Articles scraped
- ✅ Trends detected
- ✅ Articles generated
- ✅ Social posts created
- ✅ No errors in logs

### Step 4: Setup Automated Scheduling

**Option A: Windows Task Scheduler (Recommended)**

```bash
# Run the setup script
cd scripts
setup_windows_scheduler.bat
```

This creates a scheduled task that runs every 3 hours.

**Option B: Built-in Scheduler**

```bash
# Run with built-in scheduler
python run_automation.py --mode scheduled
```

> **Note**: This keeps a Python process running. Use Task Scheduler for production.

### Step 5: Verify Scheduled Task

```bash
# View task details
schtasks /query /tn "OSI News Automation" /v

# Run task manually to test
schtasks /run /tn "OSI News Automation"

# Check logs
type output\logs\automation_2026-01-21.log
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | Yes | - | MongoDB connection string |
| `GROQ_API_KEY` | Yes | - | Groq API key for LLM |
| `HOCALWIRE_API_KEY` | Yes | - | Hocalwire CMS API key |
| `HOCALWIRE_API_URL` | Yes | - | Hocalwire API endpoint |
| `MAX_ARTICLES_PER_RUN` | No | 50 | Articles to scrape per run |
| `SCRAPING_INTERVAL_HOURS` | No | 3 | Hours between runs |
| `ENABLE_IMAGE_GENERATION` | No | false | Enable AI image generation |
| `TRANSLATION_ENABLED` | No | false | Enable translation |
| `TARGET_LANGUAGES` | No | hi,es,fr,ar | Translation languages |

### News Sources

Edit `config/news_sources.yaml` to add/remove news sources:

```yaml
sources:
  - name: "BBC News"
    url: "https://www.bbc.com/news"
    rss_feed: "http://feeds.bbci.co.uk/news/rss.xml"
    region: "UK"
    priority: 1
```

---

## Running the Pipeline

### Manual Execution

```bash
# Run once
python run_automation.py --mode once

# Dry run (test without uploads)
python run_automation.py --mode dry-run

# Scheduled mode (runs every 3 hours)
python run_automation.py --mode scheduled
```

### Pipeline Steps

The pipeline executes in 7 steps:

1. **📰 Scrape Articles** - Fetch from RSS feeds and web scraping
2. **🔍 Detect Trends** - Cluster articles into trending topics
3. **✍️ Generate Articles** - Create comprehensive articles using LLM
4. **🎨 Create Images** - Generate AI images (if enabled)
5. **🌐 Translate** - Translate to multiple languages (if enabled)
6. **📤 Upload** - Upload to Hocalwire CMS
7. **📱 Social Posts** - Generate platform-specific social media posts

---

## Monitoring

### Log Files

Logs are stored in `output/logs/`:

```bash
# View today's log
type output\logs\automation_2026-01-21.log

# View last 50 lines
powershell "Get-Content output\logs\automation_2026-01-21.log -Tail 50"

# Search for errors
findstr /i "error" output\logs\automation_2026-01-21.log
```

### Output Files

Generated files in `output/json/`:

- `pipeline_stats_*.json` - Pipeline execution statistics
- `social_posts_*.json` - Generated social media posts
- `scraped_*.json` - Scraped articles (from frontend)

### Task Scheduler Monitoring

```bash
# View task status
schtasks /query /tn "OSI News Automation"

# View task history (GUI)
# 1. Open Task Scheduler (taskschd.msc)
# 2. Navigate to Task Scheduler Library
# 3. Find "OSI News Automation"
# 4. Click "History" tab
```

### Database Monitoring

```bash
# Connect to MongoDB
mongo

# View collections
use osi_news_automation
show collections

# Count articles
db.articles.count()

# View recent articles
db.articles.find().sort({scraped_at: -1}).limit(5)
```

---

## Troubleshooting

### Task Not Running

**Problem**: Scheduled task doesn't execute

**Solutions**:
1. Check Task Scheduler event log:
   - Open Event Viewer → Windows Logs → Application
   - Filter for "Task Scheduler"

2. Verify Python path:
   ```bash
   where python
   ```

3. Test task manually:
   ```bash
   schtasks /run /tn "OSI News Automation"
   ```

4. Check task configuration:
   ```bash
   schtasks /query /tn "OSI News Automation" /v
   ```

### Pipeline Errors

**Problem**: Pipeline fails with errors

**Solutions**:
1. Check log files:
   ```bash
   type output\logs\automation_*.log
   ```

2. Verify API keys:
   ```bash
   # Check .env file
   type .env | findstr "API_KEY"
   ```

3. Test components individually:
   ```bash
   # Test scraper
   python -c "from src.scrapers.batch_scraper import scrape_news_batch; print(len(scrape_news_batch(5)))"
   
   # Test database
   python -c "from src.database.mongo_client import MongoDBClient; db = MongoDBClient(); print(db.connect())"
   ```

4. Run in dry-run mode:
   ```bash
   python run_automation.py --mode dry-run
   ```

### MongoDB Connection Issues

**Problem**: Cannot connect to MongoDB

**Solutions**:
1. Verify MongoDB is running:
   ```bash
   # Check service
   sc query MongoDB
   
   # Start service if stopped
   net start MongoDB
   ```

2. Test connection:
   ```bash
   mongo --eval "db.version()"
   ```

3. Check connection string in `.env`:
   ```
   MONGODB_URI=mongodb://localhost:27017/osi_news_automation
   ```

### API Rate Limits

**Problem**: API rate limit exceeded

**Solutions**:
1. Reduce `MAX_ARTICLES_PER_RUN` in `.env`
2. Increase `SCRAPING_INTERVAL_HOURS`
3. Check API quotas in provider dashboards

### Image Generation Fails

**Problem**: Stable Diffusion initialization fails

**Solutions**:
1. Ensure sufficient RAM (16GB recommended)
2. Check GPU availability (CUDA)
3. Disable image generation temporarily:
   ```
   ENABLE_IMAGE_GENERATION=false
   ```

---

## Maintenance

### Daily Checks
- ✅ Review log files for errors
- ✅ Verify scheduled task ran successfully
- ✅ Check output files generated

### Weekly Tasks
- 🔄 Review pipeline statistics
- 🔄 Check database size and performance
- 🔄 Update news sources if needed

### Monthly Tasks
- 📦 Update dependencies: `pip install -r requirements.txt --upgrade`
- 🗑️ Clean old logs (older than 30 days)
- 📊 Review and optimize performance

### Backup Strategy

```bash
# Backup MongoDB
mongodump --db osi_news_automation --out backup\mongodb_backup

# Backup configuration
xcopy .env backup\.env /Y
xcopy config backup\config /E /Y

# Backup output
xcopy output backup\output /E /Y
```

### Updating the System

```bash
# Pull latest code (if using Git)
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Test before deploying
python run_automation.py --mode dry-run

# Restart scheduled task
schtasks /end /tn "OSI News Automation"
schtasks /run /tn "OSI News Automation"
```

---

## Stopping the Service

### Disable Scheduled Task

```bash
# Disable task (keeps configuration)
schtasks /change /tn "OSI News Automation" /disable

# Delete task completely
schtasks /delete /tn "OSI News Automation" /f
```

### Stop Running Pipeline

```bash
# If running in scheduled mode
# Press Ctrl+C in the terminal

# Or kill Python process
taskkill /IM python.exe /F
```

---

## Support

For issues or questions:
- 📧 Email: support@osinews.com
- 📚 Documentation: `docs/`
- 🐛 Issues: GitHub Issues (if applicable)

---

## License

OSI News Automation System © 2026
