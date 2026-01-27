"""
OSI News Automation System - Failed Upload Retry Service
=========================================================
Service to automatically retry failed Hocalwire uploads.
Runs periodically to re-attempt uploads that failed due to network issues.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from loguru import logger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

from src.database.mongo_client import get_client
from src.api_integrations.hocalwire_uploader import upload_to_hocalwire


def run_retry_queue(dry_run: bool = False) -> Dict:
    """
    Process the retry queue and attempt to re-upload failed articles.
    
    Args:
        dry_run: If True, log what would happen without actually uploading.
        
    Returns:
        dict: Statistics about the retry run.
    """
    # Get configuration from environment
    max_retries = int(os.getenv('MAX_GLOBAL_UPLOAD_RETRIES', 10))
    retry_interval_minutes = int(os.getenv('RETRY_INTERVAL_MINUTES', 30))
    batch_size = int(os.getenv('RETRY_BATCH_SIZE', 20))
    enabled = os.getenv('RETRY_FAILED_UPLOADS_ENABLED', 'true').lower() == 'true'
    
    stats = {
        'started_at': datetime.utcnow().isoformat(),
        'enabled': enabled,
        'dry_run': dry_run,
        'total_found': 0,
        'successful': 0,
        'failed': 0,
        'exhausted': 0,
        'errors': []
    }
    
    if not enabled:
        logger.info("⏭️ Retry queue disabled (RETRY_FAILED_UPLOADS_ENABLED=false)")
        return stats
    
    try:
        logger.info("="*80)
        logger.info("🔄 FAILED UPLOAD RETRY QUEUE")
        logger.info("="*80)
        logger.info(f"Max retries per article: {max_retries}")
        logger.info(f"Retry interval: {retry_interval_minutes} minutes")
        logger.info(f"Batch size: {batch_size}")
        if dry_run:
            logger.warning("DRY RUN MODE - No actual uploads will be performed")
        logger.info("")
        
        # Connect to database
        db = get_client()
        
        # Get failed uploads eligible for retry
        failed_articles = db.get_failed_uploads(
            max_retries=max_retries,
            min_retry_interval_minutes=retry_interval_minutes,
            limit=batch_size
        )
        
        stats['total_found'] = len(failed_articles)
        
        if not failed_articles:
            logger.info("✅ No failed uploads to retry")
            stats['completed_at'] = datetime.utcnow().isoformat()
            return stats
        
        logger.info(f"📋 Found {len(failed_articles)} articles to retry")
        logger.info("")
        
        # Process each failed article
        for i, article in enumerate(failed_articles, 1):
            heading = article.get('heading', 'Unknown')[:60]
            retry_count = article.get('upload_retry_count', 0)
            last_error = article.get('upload_failure_reason', 'Unknown')
            
            logger.info(f"🔄 Retrying {i}/{len(failed_articles)}: {heading}")
            logger.info(f"   Previous attempts: {retry_count}")
            logger.info(f"   Last error: {last_error[:100]}")
            
            if dry_run:
                logger.info("   [DRY RUN] Would attempt retry")
                stats['successful'] += 1
                continue
            
            try:
                # Get image URL if it exists
                image_url = article.get('image_url', '')
                
                # Attempt upload
                success = upload_to_hocalwire(
                    article,
                    image_url=image_url,
                    dry_run=False
                )
                
                if success:
                    logger.success(f"   ✅ Retry successful!")
                    stats['successful'] += 1
                else:
                    # Check if max retries reached
                    current_retry_count = article.get('upload_retry_count', 0) + 1
                    if current_retry_count >= max_retries:
                        logger.warning(f"   ❌ Max retries ({max_retries}) reached - marking as exhausted")
                        db.update_upload_status(
                            article['_id'],
                            'retry_exhausted',
                            failure_reason=f"Max retries reached ({max_retries})"
                        )
                        stats['exhausted'] += 1
                    else:
                        logger.warning(f"   ❌ Retry failed (attempt {current_retry_count}/{max_retries})")
                        stats['failed'] += 1
                        
            except Exception as e:
                logger.error(f"   ❌ Error during retry: {e}")
                stats['errors'].append(f"{heading}: {str(e)}")
                stats['failed'] += 1
            
            logger.info("")
        
        # Log summary
        logger.info("="*80)
        logger.info("📊 RETRY QUEUE SUMMARY")
        logger.info("="*80)
        logger.info(f"Total articles processed: {stats['total_found']}")
        logger.info(f"✅ Successful retries: {stats['successful']}")
        logger.info(f"❌ Failed retries: {stats['failed']}")
        logger.info(f"⛔ Retry exhausted: {stats['exhausted']}")
        if stats['errors']:
            logger.info(f"🚨 Errors: {len(stats['errors'])}")
        logger.info("="*80)
        
        stats['completed_at'] = datetime.utcnow().isoformat()
        return stats
        
    except Exception as e:
        logger.error(f"❌ Retry queue failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        stats['errors'].append(str(e))
        stats['completed_at'] = datetime.utcnow().isoformat()
        return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Retry failed Hocalwire uploads')
    parser.add_argument('--dry-run', action='store_true', help='Test mode (no actual uploads)')
    args = parser.parse_args()
    
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
        colorize=True
    )
    
    # Run retry queue
    stats = run_retry_queue(dry_run=args.dry_run)
    
    # Exit with appropriate code
    if stats['errors']:
        sys.exit(1)
    sys.exit(0)
