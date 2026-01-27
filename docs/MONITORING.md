# Monitoring and Alerts Setup

## Overview

The OSI News Automation System includes automated monitoring with Slack alerts to notify you of any issues with the pipeline.

---

## Slack Alerts Setup

### 1. Create Slack Webhook

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter app name: `OSI News Monitor`
5. Select your workspace
6. Click **"Create App"**

### 2. Enable Incoming Webhooks

1. In your app settings, click **"Incoming Webhooks"**
2. Toggle **"Activate Incoming Webhooks"** to **On**
3. Click **"Add New Webhook to Workspace"**
4. Select the channel for alerts (e.g., `#osi-alerts`)
5. Click **"Allow"**
6. Copy the webhook URL (starts with `https://hooks.slack.com/services/...`)

### 3. Add to Environment

Add the webhook URL to your `.env` file:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 4. Test Alert

```bash
python scripts/monitor.py
```

You should see a message in your Slack channel if any issues are detected.

---

## Schedule Monitoring

### Windows Task Scheduler

Create a scheduled task to run the monitor every hour:

```bash
schtasks /create ^
    /tn "OSI Health Monitor" ^
    /tr "python C:\Users\Jain\Desktop\OSI News Automation System\osi-news-automation\scripts\monitor.py" ^
    /sc hourly ^
    /ru SYSTEM
```

### Verify Scheduled Task

```bash
schtasks /query /tn "OSI Health Monitor"
```

---

## Alert Conditions

Alerts are sent to Slack when:

### Critical Issues (🚨)
- Database connection fails
- Pipeline hasn't run in last 4 hours

### Warnings (⚠️)
- Less than 10 articles scraped in last 4 hours
- Upload success rate below 90%
- More than 10 errors in daily log
- Less than 5GB disk space remaining

---

## Monitoring Checks

The monitor performs the following checks:

| Check | Description | Threshold |
|-------|-------------|-----------|
| **Database Connection** | MongoDB connectivity | Must connect |
| **Recent Scraping** | Articles scraped recently | ≥10 in 4 hours |
| **Upload Success** | Hocalwire upload rate | ≥90% success |
| **Error Logs** | Errors in daily log | ≤10 errors/day |
| **Disk Space** | Available storage | ≥5GB free |
| **Pipeline Running** | Recent pipeline activity | Active in 4 hours |

---

## Daily Summary

Send a daily summary report at 9 AM:

```bash
schtasks /create ^
    /tn "OSI Daily Summary" ^
    /tr "python C:\Users\Jain\Desktop\OSI News Automation System\osi-news-automation\scripts\monitor.py --summary" ^
    /sc daily ^
    /st 09:00 ^
    /ru SYSTEM
```

The daily summary includes:
- Articles scraped (last 24 hours)
- Trends detected
- Articles generated
- Articles uploaded
- Success rate

---

## Dashboard Access

### MongoDB Compass (Local)

View database in real-time:

1. Download [MongoDB Compass](https://www.mongodb.com/products/compass)
2. Connect to: `mongodb://localhost:27017/`
3. Select database: `osi_news_production`
4. Browse collections: `articles`, `trends`, `scraping_sessions`

### Hocalwire Dashboard

View published articles:

- URL: [https://democracynewslive.com/dashboard](https://democracynewslive.com/dashboard)
- Login with your Hocalwire credentials
- Check feed status and article views

### Log Files

View detailed logs:

```bash
# Today's log
type output\logs\automation_2026-01-21.log

# Last 50 lines
powershell "Get-Content output\logs\automation_*.log -Tail 50"

# Search for errors
findstr /i "error" output\logs\automation_*.log
```

---

## Monitoring Best Practices

### Daily
- ✅ Check Slack for alerts
- ✅ Review daily summary
- ✅ Spot-check article quality

### Weekly
- ✅ Review full logs for patterns
- ✅ Check database size and performance
- ✅ Verify all news sources working
- ✅ Review upload success trends

### Monthly
- ✅ Analyze performance metrics
- ✅ Review and update alert thresholds
- ✅ Clean old logs (keep 30 days)
- ✅ Backup MongoDB data

---

## Troubleshooting Alerts

### "Low article count"

**Cause**: Fewer than 10 articles scraped in 4 hours

**Solutions**:
1. Check news sources in `config/news_sources.yaml`
2. Verify internet connectivity
3. Check for rate limiting in logs
4. Increase `MAX_ARTICLES_PER_SOURCE` temporarily

### "Upload success rate low"

**Cause**: Less than 90% of articles uploaded successfully

**Solutions**:
1. Check Hocalwire API key
2. Verify API endpoint URL
3. Review Hocalwire API logs
4. Check for SSL certificate issues
5. Test with single article upload

### "High error count in logs"

**Cause**: More than 10 errors in daily log

**Solutions**:
1. Review log file for error patterns
2. Check API quotas (Groq)
3. Verify all credentials in `.env`
4. Test components individually

### "Low disk space"

**Cause**: Less than 5GB free space

**Solutions**:
1. Clean old logs: `del output\logs\automation_*.log` (older than 30 days)
2. Clean old images: `del output\images\*.png` (if not needed)
3. Clean old JSON: `del output\json\*.json` (backup first)
4. Increase disk space

### "Database connection failed"

**Cause**: Cannot connect to MongoDB

**Solutions**:
1. Check MongoDB service: `sc query MongoDB`
2. Start MongoDB: `net start MongoDB`
3. Verify connection string in `.env`
4. Check MongoDB logs

### "No pipeline runs detected"

**Cause**: Pipeline hasn't run in 4 hours

**Solutions**:
1. Check scheduled task: `schtasks /query /tn "OSI News Automation"`
2. Run manually: `schtasks /run /tn "OSI News Automation"`
3. Check logs for errors
4. Verify `.env` file exists

---

## Custom Alerts

### Add Custom Check

Edit `scripts/monitor.py` and add your check:

```python
def check_custom_metric():
    """Check custom metric."""
    try:
        # Your check logic here
        if metric < threshold:
            return False, "Custom metric below threshold"
        return True, "Custom metric healthy"
    except Exception as e:
        return False, f"Custom check failed: {str(e)}"

# Add to checks dictionary
checks = {
    # ... existing checks ...
    "Custom Metric": check_custom_metric()
}
```

### Adjust Thresholds

Edit thresholds in `scripts/monitor.py`:

```python
# Article count threshold
if count < 10:  # Change to 5 for lower threshold
    return False, f"Low article count: {count}"

# Upload success rate threshold
if success_rate < 90:  # Change to 80 for lower threshold
    return False, f"Upload success rate low: {success_rate:.1f}%"
```

---

## Monitoring Metrics

Track these key metrics over time:

| Metric | Target | Alert If |
|--------|--------|----------|
| Articles/Run | 40-50 | <10 |
| Trends/Run | 3-5 | <1 |
| Upload Success | >95% | <90% |
| Pipeline Uptime | >99% | <95% |
| Avg Response Time | <2min | >5min |
| Error Rate | <1% | >5% |

---

## Support

For monitoring issues:
- 📧 Email: support@osinews.com
- 📚 Docs: `docs/DEPLOYMENT.md`
- 🔧 Health Check: `python scripts/health_check.py`

---

**OSI News Automation System v1.0**
*Monitoring and Alerts Guide*
