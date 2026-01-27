#!/usr/bin/env python3
"""
OSI News Automation System - Monitoring Script
===============================================
Monitors pipeline health and sends alerts to Slack when issues are detected.

Usage:
    python scripts/monitor.py
    
Schedule this to run hourly via Task Scheduler for continuous monitoring.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv()

from src.database.mongo_client import MongoDBClient


# ===========================================
# SLACK ALERTS
# ===========================================

def send_slack_alert(message: str, webhook_url: str = None, severity: str = "warning"):
    """
    Send alert to Slack.
    
    Args:
        message: Alert message to send.
        webhook_url: Slack webhook URL (optional, reads from env).
        severity: Alert severity - "info", "warning", or "critical".
    """
    if not webhook_url:
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        logger.warning("No Slack webhook configured, skipping alert")
        return False
    
    try:
        # Choose emoji based on severity
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨"
        }.get(severity, "⚠️")
        
        payload = {
            "text": f"{emoji} *OSI News Automation Alert*\n{message}",
            "username": "OSI Monitor",
            "icon_emoji": ":robot_face:"
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        logger.info("✅ Alert sent to Slack")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Slack alert: {e}")
        return False


# ===========================================
# HEALTH CHECKS
# ===========================================

def check_recent_scraping():
    """Check if articles were scraped recently."""
    try:
        db = MongoDBClient()
        if not db.connect():
            return False, "Database connection failed"
        
        # Check for articles in last 4 hours
        cutoff = datetime.utcnow() - timedelta(hours=4)
        recent = list(db.articles.find(
            {"scraped_at": {"$gte": cutoff.isoformat()}},
            {"_id": 1}
        ))
        
        count = len(recent)
        
        if count < 10:
            return False, f"Low article count: Only {count} articles in last 4 hours"
        
        return True, f"{count} articles scraped in last 4 hours"
    except Exception as e:
        return False, f"Scraping check failed: {str(e)}"


def check_upload_success_rate():
    """Check Hocalwire upload success rate."""
    try:
        db = MongoDBClient()
        db.connect()
        
        # Check articles uploaded in last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        total = db.articles.count_documents({
            "scraped_at": {"$gte": cutoff.isoformat()},
            "pipeline_stage": "generated"
        })
        
        uploaded = db.articles.count_documents({
            "scraped_at": {"$gte": cutoff.isoformat()},
            "upload_status": "uploaded"
        })
        
        if total == 0:
            return True, "No uploads attempted in last 24 hours"
        
        success_rate = (uploaded / total) * 100
        
        if success_rate < 90:
            return False, f"Upload success rate low: {success_rate:.1f}% ({uploaded}/{total})"
        
        return True, f"Upload success rate: {success_rate:.1f}% ({uploaded}/{total})"
    except Exception as e:
        return False, f"Upload check failed: {str(e)}"


def check_error_logs():
    """Check for excessive errors in logs."""
    try:
        log_file = Path(f"output/logs/automation_{datetime.now().strftime('%Y-%m-%d')}.log")
        
        if not log_file.exists():
            return True, "No log file for today (pipeline may not have run)"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        error_count = logs.count('ERROR')
        critical_count = logs.count('CRITICAL')
        
        if critical_count > 0:
            return False, f"Critical errors in logs: {critical_count} critical, {error_count} total errors"
        
        if error_count > 10:
            return False, f"High error count in logs: {error_count} errors today"
        
        return True, f"Error count acceptable: {error_count} errors today"
    except Exception as e:
        return False, f"Log check failed: {str(e)}"


def check_disk_space():
    """Check available disk space."""
    try:
        import shutil
        
        total, used, free = shutil.disk_usage(os.getcwd())
        free_gb = free // (2**30)
        
        if free_gb < 5:
            return False, f"Low disk space: {free_gb}GB remaining"
        elif free_gb < 10:
            return True, f"Disk space warning: {free_gb}GB remaining (monitor closely)"
        
        return True, f"Disk space healthy: {free_gb}GB free"
    except Exception as e:
        return False, f"Disk space check failed: {str(e)}"


def check_database_connection():
    """Check MongoDB connectivity."""
    try:
        db = MongoDBClient()
        if db.connect():
            return True, "Database connected"
        else:
            return False, "Database connection failed"
    except Exception as e:
        return False, f"Database check failed: {str(e)}"


def check_pipeline_running():
    """Check if pipeline is running on schedule."""
    try:
        db = MongoDBClient()
        db.connect()
        
        # Check for pipeline stats in last 4 hours
        cutoff = datetime.utcnow() - timedelta(hours=4)
        
        # Look for recent session IDs
        recent_sessions = db.articles.distinct("session_id", {
            "scraped_at": {"$gte": cutoff.isoformat()}
        })
        
        if not recent_sessions:
            return False, "No pipeline runs detected in last 4 hours"
        
        return True, f"Pipeline active: {len(recent_sessions)} sessions in last 4 hours"
    except Exception as e:
        return False, f"Pipeline check failed: {str(e)}"


# ===========================================
# MAIN MONITORING FUNCTION
# ===========================================

def check_pipeline_health():
    """
    Monitor pipeline health and send alerts if issues detected.
    
    Returns:
        int: Exit code (0 = healthy, 1 = warnings, 2 = critical)
    """
    logger.info("=" * 60)
    logger.info("🔍 OSI NEWS AUTOMATION - HEALTH MONITOR")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info("")
    
    issues = []
    warnings = []
    
    # Run all checks
    checks = {
        "Database Connection": check_database_connection(),
        "Recent Scraping": check_recent_scraping(),
        "Upload Success Rate": check_upload_success_rate(),
        "Error Logs": check_error_logs(),
        "Disk Space": check_disk_space(),
        "Pipeline Running": check_pipeline_running()
    }
    
    # Categorize results
    for check_name, (passed, message) in checks.items():
        if passed:
            logger.info(f"✅ {check_name}: {message}")
        else:
            logger.warning(f"❌ {check_name}: {message}")
            
            # Determine severity
            if check_name in ["Database Connection", "Pipeline Running"]:
                issues.append(f"🚨 *{check_name}*: {message}")
            else:
                warnings.append(f"⚠️ *{check_name}*: {message}")
    
    logger.info("")
    logger.info("=" * 60)
    
    # Send alerts if needed
    if issues:
        alert_message = "*Critical Issues Detected:*\n" + "\n".join(issues)
        if warnings:
            alert_message += "\n\n*Warnings:*\n" + "\n".join(warnings)
        
        send_slack_alert(alert_message, severity="critical")
        logger.error("🚨 Critical issues detected")
        logger.info("=" * 60)
        return 2
    
    elif warnings:
        alert_message = "*Warnings Detected:*\n" + "\n".join(warnings)
        send_slack_alert(alert_message, severity="warning")
        logger.warning("⚠️ Warnings detected")
        logger.info("=" * 60)
        return 1
    
    else:
        logger.info("✅ All systems healthy")
        logger.info("=" * 60)
        return 0


# ===========================================
# DAILY SUMMARY
# ===========================================

def send_daily_summary():
    """Send daily summary report to Slack."""
    try:
        db = MongoDBClient()
        db.connect()
        
        # Get stats for last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        articles_scraped = db.articles.count_documents({
            "scraped_at": {"$gte": cutoff.isoformat()}
        })
        
        articles_generated = db.articles.count_documents({
            "scraped_at": {"$gte": cutoff.isoformat()},
            "pipeline_stage": "generated"
        })
        
        articles_uploaded = db.articles.count_documents({
            "scraped_at": {"$gte": cutoff.isoformat()},
            "upload_status": "uploaded"
        })
        
        trends_detected = db.trends.count_documents({
            "detected_at": {"$gte": cutoff.isoformat()}
        })
        
        message = f"""*📊 Daily Summary Report*
Date: {datetime.now().strftime('%Y-%m-%d')}

*Pipeline Activity (Last 24 Hours):*
• Articles Scraped: {articles_scraped}
• Trends Detected: {trends_detected}
• Articles Generated: {articles_generated}
• Articles Uploaded: {articles_uploaded}

*Success Rate:* {(articles_uploaded/articles_generated*100) if articles_generated > 0 else 0:.1f}%
"""
        
        send_slack_alert(message, severity="info")
        logger.info("Daily summary sent")
        
    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OSI News Automation Monitor')
    parser.add_argument('--summary', action='store_true', help='Send daily summary')
    args = parser.parse_args()
    
    if args.summary:
        send_daily_summary()
    else:
        exit_code = check_pipeline_health()
        sys.exit(exit_code)
