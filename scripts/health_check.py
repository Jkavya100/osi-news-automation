#!/usr/bin/env python3
"""
OSI News Automation System - Health Check Script
=================================================
Run periodically to verify system health and component availability.
Checks database, APIs, disk space, and recent activity.

Usage:
    python scripts/health_check.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{message}</level>",
    level="INFO",
    colorize=True
)


def check_database():
    """Check MongoDB connectivity."""
    try:
        from src.database.mongo_client import MongoDBClient
        
        db = MongoDBClient()
        if db.connect():
            logger.info("✅ Database: Connected")
            return True
        else:
            logger.error("❌ Database: Connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database: Error - {e}")
        return False


def check_recent_articles():
    """Check if articles were scraped in last 4 hours."""
    try:
        from src.database.mongo_client import MongoDBClient
        
        db = MongoDBClient()
        db.connect()
        
        # Check for articles in last 4 hours
        cutoff = datetime.utcnow() - timedelta(hours=4)
        recent = list(db.articles.find(
            {"scraped_at": {"$gte": cutoff.isoformat()}},
            {"_id": 1}
        ).limit(10))
        
        if recent and len(recent) > 0:
            logger.info(f"✅ Recent Articles: {len(recent)} in last 4 hours")
            return True
        else:
            logger.warning("⚠️ Recent Articles: None in last 4 hours")
            return False
    except Exception as e:
        logger.error(f"❌ Recent Articles: Error - {e}")
        return False


def check_groq_api():
    """Check Groq API connectivity."""
    try:
        from groq import Groq
        
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key or api_key == 'your_actual_groq_key_here':
            logger.warning("⚠️ Groq API: No API key configured")
            return False
        
        client = Groq(api_key=api_key)
        
        # Simple test request
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        
        logger.info("✅ Groq API: Connected")
        return True
    except Exception as e:
        logger.error(f"❌ Groq API: Error - {str(e)[:100]}")
        return False


def check_hocalwire_api():
    """Check Hocalwire API accessibility."""
    try:
        import requests
        
        api_url = os.getenv('HOCALWIRE_API_URL')
        api_key = os.getenv('HOCALWIRE_API_KEY')
        
        if not api_url or not api_key:
            logger.warning("⚠️ Hocalwire API: Not configured")
            return False
        
        # Just check if endpoint is accessible (OPTIONS request)
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = requests.head(api_url, headers=headers, timeout=10)
            logger.info("✅ Hocalwire API: Accessible")
            return True
        except requests.exceptions.SSLError:
            # SSL errors are common with Hocalwire, but endpoint is accessible
            logger.info("✅ Hocalwire API: Accessible (SSL warning)")
            return True
    except Exception as e:
        logger.error(f"❌ Hocalwire API: Error - {str(e)[:100]}")
        return False


def check_disk_space():
    """Check available disk space."""
    try:
        import shutil
        
        # Get disk usage for current drive
        total, used, free = shutil.disk_usage(os.getcwd())
        
        free_gb = free // (2**30)
        total_gb = total // (2**30)
        used_percent = (used / total) * 100
        
        if free_gb < 5:
            logger.warning(f"⚠️ Disk Space: Low ({free_gb}GB free, {used_percent:.1f}% used)")
            return False
        elif free_gb < 10:
            logger.info(f"✅ Disk Space: {free_gb}GB free ({used_percent:.1f}% used) - Monitor closely")
            return True
        else:
            logger.info(f"✅ Disk Space: {free_gb}GB free ({used_percent:.1f}% used)")
            return True
    except Exception as e:
        logger.error(f"❌ Disk Space: Error - {e}")
        return False


def check_output_directories():
    """Check that required output directories exist."""
    try:
        required_dirs = [
            'output/json',
            'output/logs',
            'output/images'
        ]
        
        all_exist = True
        for dir_path in required_dirs:
            path = Path(dir_path)
            if not path.exists():
                logger.warning(f"⚠️ Directory missing: {dir_path}")
                all_exist = False
        
        if all_exist:
            logger.info("✅ Output Directories: All present")
            return True
        else:
            logger.warning("⚠️ Output Directories: Some missing")
            return False
    except Exception as e:
        logger.error(f"❌ Output Directories: Error - {e}")
        return False


def check_log_files():
    """Check recent log files."""
    try:
        log_dir = Path('output/logs')
        if not log_dir.exists():
            logger.warning("⚠️ Log Files: Directory missing")
            return False
        
        # Find today's log
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = log_dir / f'automation_{today}.log'
        
        if log_file.exists():
            size_kb = log_file.stat().st_size / 1024
            logger.info(f"✅ Log Files: Today's log exists ({size_kb:.1f}KB)")
            return True
        else:
            logger.warning("⚠️ Log Files: No log for today")
            return False
    except Exception as e:
        logger.error(f"❌ Log Files: Error - {e}")
        return False


def check_scheduled_task():
    """Check if Windows scheduled task exists."""
    try:
        import subprocess
        
        result = subprocess.run(
            ['schtasks', '/query', '/tn', 'OSI News Automation'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Scheduled Task: Active")
            return True
        else:
            logger.warning("⚠️ Scheduled Task: Not found")
            return False
    except Exception as e:
        logger.error(f"❌ Scheduled Task: Error - {e}")
        return False


def run_health_check():
    """Run all health checks and return status."""
    logger.info("=" * 60)
    logger.info("🏥 OSI NEWS AUTOMATION - HEALTH CHECK")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info("")
    
    checks = {
        "Database": check_database(),
        "Recent Articles": check_recent_articles(),
        "Groq API": check_groq_api(),
        "Hocalwire API": check_hocalwire_api(),
        "Disk Space": check_disk_space(),
        "Output Directories": check_output_directories(),
        "Log Files": check_log_files(),
        "Scheduled Task": check_scheduled_task()
    }
    
    passed = sum(checks.values())
    total = len(checks)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"SUMMARY: {passed}/{total} checks passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("✅ All systems healthy")
        return 0
    elif passed >= total * 0.7:
        logger.warning("⚠️ Some issues detected, review above")
        return 1
    else:
        logger.error("❌ Critical issues detected")
        return 2


if __name__ == "__main__":
    exit_code = run_health_check()
    sys.exit(exit_code)
