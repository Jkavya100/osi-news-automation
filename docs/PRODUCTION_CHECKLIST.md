# Production Deployment Checklist

## 📋 Pre-Deployment

### Environment Setup
- [ ] Python 3.11.9 installed and in PATH
- [ ] MongoDB installed and running (`sc query MongoDB`)
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file configured with production values
- [ ] Output directories created:
  - [ ] `output/json/`
  - [ ] `output/images/`
  - [ ] `output/logs/`

### API Keys & Credentials
- [ ] Groq API key obtained from [console.groq.com](https://console.groq.com)
- [ ] Groq API key tested with sample request
- [ ] Hocalwire API key verified
- [ ] Hocalwire API endpoint tested
- [ ] MongoDB connection string tested
- [ ] All feature flags set appropriately for production

### Testing
- [ ] All unit tests passing: `pytest tests/ -v`
- [ ] Integration tests passing: `pytest tests/test_integration.py -v`
- [ ] Dry-run completed successfully: `python run_automation.py --mode dry-run`
- [ ] Database connectivity confirmed
- [ ] Scraping tested with 5-10 articles
- [ ] Article generation tested with real trends
- [ ] Hocalwire upload tested with 1 test article
- [ ] Health check script runs successfully: `python scripts/health_check.py`

---

## 🚀 Deployment Steps

### 1. Clone & Setup

```bash
# Navigate to deployment location
cd "C:\Users\Jain\Desktop\OSI News Automation System"

# Verify project structure
dir osi-news-automation

# Install dependencies
cd osi-news-automation
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy production configuration
copy config\production.env .env

# Edit with your actual credentials
notepad .env
```

**Required Changes in `.env`:**
- `GROQ_API_KEY` - Your actual Groq API key
- `MONGODB_DATABASE` - Set to `osi_news_production`
- `ENABLE_HOCALWIRE_UPLOAD` - Set to `true`
- `MAX_ARTICLES_PER_RUN` - Set to `50` for production

### 3. Initialize Database

```bash
# Initialize MongoDB collections and indexes
python src\database\initialize_db.py

# Verify database created
mongo
> show dbs
> use osi_news_production
> show collections
> exit
```

### 4. Test Pipeline

```bash
# First, dry run to test without uploads
python run_automation.py --mode dry-run

# Check output
dir output\json
type output\logs\automation_*.log

# Then, real run with 5 articles for testing
# Temporarily set MAX_ARTICLES_PER_RUN=5 in .env
python run_automation.py --mode once

# Verify articles uploaded to Hocalwire
# Check Hocalwire dashboard
```

### 5. Setup Automation

**Option A: Windows Task Scheduler (Recommended)**

```bash
# Run setup script
cd scripts
setup_windows_scheduler.bat

# Verify task created
schtasks /query /tn "OSI News Automation"
```

**Option B: Run Manually in Background**

```bash
# Start in background (keeps terminal open)
start /B python run_automation.py --mode scheduled
```

### 6. Verify First Run

- [ ] Check logs: `type output\logs\automation_*.log`
- [ ] Check generated articles: `dir output\json`
- [ ] Check Hocalwire dashboard for uploaded articles
- [ ] Verify no critical errors in logs
- [ ] Confirm articles appear on democracynewslive.com

---

## 📊 Monitoring Setup

### Daily Checks
- [ ] Review error logs for critical issues
- [ ] Check upload success rate (should be >90%)
- [ ] Verify article count (should get ~40-50 per run)
- [ ] Check disk space (logs and images)
- [ ] Run health check: `python scripts\health_check.py`

### Weekly Checks
- [ ] Review article quality and relevance
- [ ] Check for duplicate articles in database
- [ ] Monitor API usage and costs (Groq dashboard)
- [ ] Clean old logs (keep last 30 days)
- [ ] Review news sources for broken feeds

### Monthly Checks
- [ ] Review system performance metrics
- [ ] Update news sources if any are broken
- [ ] Backup MongoDB data: `mongodump --db osi_news_production`
- [ ] Update dependencies: `pip install -r requirements.txt --upgrade`
- [ ] Review and optimize pipeline settings

---

## 🔧 Troubleshooting

### Pipeline Not Running

**Symptoms**: No new articles, scheduled task not executing

**Solutions**:
1. Check Task Scheduler is active:
   ```bash
   schtasks /query /tn "OSI News Automation"
   ```

2. Verify Python path in scheduled task:
   ```bash
   schtasks /query /tn "OSI News Automation" /v
   ```

3. Check `.env` file exists in project root

4. Review logs for errors:
   ```bash
   type output\logs\automation_*.log | findstr /i "error"
   ```

### Low Article Count

**Symptoms**: Scraping returns <10 articles

**Solutions**:
1. Check news sources in `config/news_sources.yaml`
2. Verify internet connectivity
3. Check for rate limiting errors in logs
4. Disable problematic sources temporarily
5. Increase `MAX_ARTICLES_PER_SOURCE` in `.env`

### Upload Failures

**Symptoms**: Articles generated but not appearing on Hocalwire

**Solutions**:
1. Verify Hocalwire API key is correct
2. Check API endpoint URL matches Hocalwire docs
3. Review Hocalwire API logs/dashboard
4. Check internet connectivity
5. Test with single article upload
6. Verify JSON format matches Hocalwire requirements

### MongoDB Issues

**Symptoms**: Database connection errors

**Solutions**:
1. Verify MongoDB service is running:
   ```bash
   sc query MongoDB
   ```

2. Start MongoDB if stopped:
   ```bash
   net start MongoDB
   ```

3. Check connection string in `.env`

4. Ensure sufficient disk space

5. Review MongoDB logs:
   ```bash
   type "C:\Program Files\MongoDB\Server\7.0\log\mongod.log"
   ```

### High Memory Usage

**Symptoms**: System slows down, out of memory errors

**Solutions**:
1. Disable image generation: `ENABLE_IMAGE_GENERATION=false`
2. Reduce article count: `MAX_ARTICLES_PER_RUN=25`
3. Increase scraping interval: `SCRAPING_INTERVAL_HOURS=6`
4. Close other applications
5. Upgrade RAM if possible

---

## 🔄 Rollback Plan

If deployment fails:

1. **Stop Scheduled Task**:
   ```bash
   schtasks /delete /tn "OSI News Automation" /f
   ```

2. **Review Logs**:
   ```bash
   type output\logs\automation_*.log
   ```

3. **Identify Issue**:
   - Check error messages
   - Review configuration
   - Test components individually

4. **Fix Configuration**:
   - Update `.env` file
   - Fix news sources
   - Adjust feature flags

5. **Re-test**:
   ```bash
   python run_automation.py --mode dry-run
   ```

6. **Redeploy**:
   - Run setup script again
   - Verify first execution
   - Monitor for 24 hours

---

## ✅ Success Criteria

Pipeline is successful when:

- ✅ Runs every 3 hours automatically
- ✅ Scrapes 40-50 articles per run
- ✅ Detects 3-5 trends per run
- ✅ Generates comprehensive articles (800+ words each)
- ✅ Uploads to Hocalwire successfully (>90% success rate)
- ✅ No critical errors in logs
- ✅ Articles appear on democracynewslive.com dashboard
- ✅ Health check passes all tests
- ✅ System runs for 7 days without intervention

---

## 📞 Support

### Resources
- 📚 Documentation: `docs/`
- 🔧 Troubleshooting: `docs/DEPLOYMENT.md`
- ⚡ Quick Start: `docs/QUICKSTART.md`

### Contacts
- 📧 Technical Support: support@osinews.com
- 🐛 Bug Reports: GitHub Issues
- 💬 Community: Slack/Discord (if applicable)

---

## 📝 Post-Deployment Notes

### Completed By
- Name: _______________
- Date: _______________
- Time: _______________

### Deployment Details
- Environment: Production
- MongoDB Database: osi_news_production
- Scheduled Task: OSI News Automation
- First Run: _______________
- Articles Generated: _______________
- Upload Success Rate: _______________%

### Issues Encountered
_Document any issues and their resolutions:_

---

**OSI News Automation System v1.0**
*Production Deployment Checklist*
