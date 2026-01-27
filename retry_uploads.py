#!/usr/bin/env python3
"""
OSI News Automation System - Manual Retry Tool
==============================================
Standalone tool to manually retry failed uploads or check retry queue status.

Usage:
    python retry_uploads.py                    # Retry all failed uploads
    python retry_uploads.py --status           # View retry queue status
    python retry_uploads.py --dry-run          # Test without actual uploads
    python retry_uploads.py --article-id <id>  # Retry specific article
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from loguru import logger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv()

from src.database.mongo_client import get_client
from src.api_integrations.retry_failed_uploads import run_retry_queue
from src.api_integrations.hocalwire_uploader import upload_to_hocalwire


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
        colorize=True
    )


def show_retry_queue_status():
    """Display current retry queue status."""
    logger.info("="*80)
    logger.info("📊 RETRY QUEUE STATUS")
    logger.info("="*80)
    
    try:
        db = get_client()
        
        # Get failed articles grouped by status
        failed_pending = list(db.articles.find({"upload_status": "failed"}))
        retry_exhausted = list(db.articles.find({"upload_status": "retry_exhausted"}))
        
        logger.info(f"\n📋 Failed Uploads (Pending Retry): {len(failed_pending)}")
        
        if failed_pending:
            logger.info("\nTop 10 Failed Articles:")
            for i, article in enumerate(failed_pending[:10], 1):
                heading = article.get('heading', 'Unknown')[:60]
                retry_count = article.get('upload_retry_count', 0)
                last_retry = article.get('upload_last_retry')
                failure_reason = article.get('upload_failure_reason', 'Unknown')[:80]
                
                logger.info(f"\n{i}. {heading}")
                logger.info(f"   ID: {article['_id']}")
                logger.info(f"   Retries: {retry_count}")
                if last_retry:
                    logger.info(f"   Last Retry: {last_retry}")
                logger.info(f"   Reason: {failure_reason}")
        
        logger.info(f"\n⛔ Retry Exhausted: {len(retry_exhausted)}")
        
        if retry_exhausted:
            logger.info("\nArticles that exhausted retries:")
            for i, article in enumerate(retry_exhausted[:5], 1):
                heading = article.get('heading', 'Unknown')[:60]
                failure_reason = article.get('upload_failure_reason', 'Unknown')[:80]
                logger.info(f"{i}. {heading}")
                logger.info(f"   Reason: {failure_reason}")
        
        # Configuration info
        max_retries = int(os.getenv('MAX_GLOBAL_UPLOAD_RETRIES', 10))
        retry_interval = int(os.getenv('RETRY_INTERVAL_MINUTES', 30))
        
        logger.info(f"\n⚙️ Configuration:")
        logger.info(f"   Max Retries: {max_retries}")
        logger.info(f"   Retry Interval: {retry_interval} minutes")
        logger.info(f"   Retry Enabled: {os.getenv('RETRY_FAILED_UPLOADS_ENABLED', 'true')}")
        
        logger.info("\n" + "="*80)
        
    except Exception as e:
        logger.error(f"Error fetching retry queue status: {e}")
        import traceback
        logger.error(traceback.format_exc())


def retry_specific_article(article_id: str, dry_run: bool = False):
    """Retry a specific article by ID."""
    logger.info(f"🔄 Retrying article: {article_id}")
    
    try:
        db = get_client()
        
        # Get article from database
        try:
            article = db.get_article_by_id(ObjectId(article_id))
        except:
            article = db.get_article_by_id(article_id)
        
        if not article:
            logger.error(f"❌ Article not found: {article_id}")
            return False
        
        heading = article.get('heading', 'Unknown')
        status = article.get('upload_status', 'unknown')
        retry_count = article.get('upload_retry_count', 0)
        
        logger.info(f"📄 Article: {heading}")
        logger.info(f"   Current Status: {status}")
        logger.info(f"   Retry Count: {retry_count}")
        
        if dry_run:
            logger.warning("[DRY RUN] Would attempt upload")
            return True
        
        # Attempt upload
        image_url = article.get('image_url', '')
        success = upload_to_hocalwire(article, image_url=image_url, dry_run=False)
        
        if success:
            logger.success("✅ Upload successful!")
            return True
        else:
            logger.error("❌ Upload failed")
            return False
            
    except Exception as e:
        logger.error(f"Error retrying article: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Manual retry tool for failed Hocalwire uploads',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python retry_uploads.py                    # Retry all failed uploads
  python retry_uploads.py --status           # View retry queue status  
  python retry_uploads.py --dry-run          # Test without uploads
  python retry_uploads.py --article-id 123   # Retry specific article
        """
    )
    
    parser.add_argument('--status', action='store_true', help='Show retry queue status')
    parser.add_argument('--article-id', type=str, help='Retry specific article ID')
    parser.add_argument('--dry-run', action='store_true', help='Test mode (no actual uploads)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger.info("OSI News Automation - Failed Upload Retry Tool")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        if args.status:
            # Show status
            show_retry_queue_status()
            
        elif args.article_id:
            # Retry specific article
            success = retry_specific_article(args.article_id, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
            
        else:
            # Retry all failed uploads
            logger.info("Running retry queue for all failed uploads...\n")
            stats = run_retry_queue(dry_run=args.dry_run)
            
            # Exit with error code if there were errors
            if stats.get('errors'):
                sys.exit(1)
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.warning("\n🛑 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
