"""
OSI News Automation System - RSS Feed Scraper
==============================================
Reliable alternative to web scraping using RSS feeds.
Most news sites provide RSS feeds which are more stable.
"""

import feedparser
from datetime import datetime
from loguru import logger
from typing import Dict, List, Optional
import time
import os
import sys
from dotenv import load_dotenv

# Add parent to path for imports when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from src.scrapers.news_scraper import scrape_single_article
except ImportError:
    # Fallback for direct execution
    from news_scraper import scrape_single_article

# Load environment variables
load_dotenv()


# ===========================================
# RSS FEED DEFINITIONS
# ===========================================

RSS_FEEDS = {
    "BBC News": {
        "feeds": [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
        ],
        "region": "UK",
        "language": "en"
    },
    "Reuters": {
        "feeds": [
            "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
        ],
        "region": "International",
        "language": "en"
    },
    "Al Jazeera": {
        "feeds": [
            "https://www.aljazeera.com/xml/rss/all.xml",
        ],
        "region": "Middle East",
        "language": "en"
    },
    "The Guardian": {
        "feeds": [
            "https://www.theguardian.com/world/rss",
            "https://www.theguardian.com/international/rss",
        ],
        "region": "UK",
        "language": "en"
    },
    "India Today": {
        "feeds": [
            "https://www.indiatoday.in/rss/home",
        ],
        "region": "India",
        "language": "en"
    },
    "The Hindu": {
        "feeds": [
            "https://www.thehindu.com/news/feeder/default.rss",
        ],
        "region": "India",
        "language": "en"
    },
    "NDTV": {
        "feeds": [
            "https://feeds.feedburner.com/ndtvnews-top-stories",
        ],
        "region": "India",
        "language": "en"
    },
    "France 24": {
        "feeds": [
            "https://www.france24.com/en/rss",
        ],
        "region": "France",
        "language": "en"
    },
    "Deutsche Welle": {
        "feeds": [
            "https://rss.dw.com/rdf/rss-en-all",
        ],
        "region": "Germany",
        "language": "en"
    },
    "Associated Press": {
        "feeds": [
            "https://rsshub.app/apnews/topics/apf-topnews",
        ],
        "region": "USA",
        "language": "en"
    }
}


# ===========================================
# RSS FEED PARSING
# ===========================================

def parse_rss_feed(feed_url: str, limit: int = 10) -> List[Dict]:
    """
    Parse an RSS feed and extract article entries.
    
    Args:
        feed_url: URL of the RSS feed.
        limit: Maximum number of entries to return.
        
    Returns:
        List of article entry dictionaries.
    """
    try:
        logger.debug(f"Parsing RSS feed: {feed_url}")
        
        feed = feedparser.parse(feed_url)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"RSS feed parsing issue: {feed.bozo_exception}")
        
        entries = []
        for entry in feed.entries[:limit]:
            article_entry = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "author": entry.get("author", ""),
            }
            
            if article_entry["link"]:
                entries.append(article_entry)
        
        logger.info(f"Found {len(entries)} entries from RSS feed")
        return entries
        
    except Exception as e:
        logger.error(f"Failed to parse RSS feed {feed_url}: {e}")
        return []


def get_articles_from_rss(
    source_name: str,
    limit: int = 10,
    scrape_full: bool = True,
    delay_seconds: float = 2.0
) -> List[Dict]:
    """
    Get articles from a news source's RSS feeds.
    
    Args:
        source_name: Name of the news source (must be in RSS_FEEDS).
        limit: Maximum articles per feed.
        scrape_full: If True, scrape full article content from URLs.
        delay_seconds: Delay between scraping requests.
        
    Returns:
        List of article dictionaries.
    """
    if source_name not in RSS_FEEDS:
        logger.error(f"Unknown source: {source_name}")
        return []
    
    source_config = RSS_FEEDS[source_name]
    all_articles = []
    
    for feed_url in source_config["feeds"]:
        entries = parse_rss_feed(feed_url, limit)
        
        for entry in entries:
            if scrape_full and entry["link"]:
                # Scrape full article content
                article = scrape_single_article(entry["link"], source_name)
                
                if article:
                    # Add source metadata
                    article["source_name"] = source_name
                    article["region"] = source_config.get("region", "Unknown")
                    all_articles.append(article)
                
                # Rate limiting
                time.sleep(delay_seconds)
            else:
                # Use RSS entry data only
                all_articles.append({
                    "heading": entry["title"],
                    "story": entry["summary"],
                    "source_url": entry["link"],
                    "source_name": source_name,
                    "publish_date": entry["published"],
                    "authors": [entry["author"]] if entry["author"] else [],
                    "location": source_config.get("region", "Unknown"),
                    "language": source_config.get("language", "en"),
                    "scraped_at": datetime.utcnow().isoformat(),
                    "word_count": len(entry["summary"].split())
                })
    
    logger.info(f"Retrieved {len(all_articles)} articles from {source_name}")
    return all_articles


def get_all_rss_urls(sources: List[str] = None, limit_per_source: int = 5) -> List[Dict]:
    """
    Get article URLs from multiple sources via RSS.
    
    Args:
        sources: List of source names. If None, uses all available sources.
        limit_per_source: Max articles per source.
        
    Returns:
        List of dicts with url and source_name.
    """
    if sources is None:
        sources = list(RSS_FEEDS.keys())
    
    all_urls = []
    
    for source_name in sources:
        if source_name not in RSS_FEEDS:
            continue
        
        source_config = RSS_FEEDS[source_name]
        
        for feed_url in source_config["feeds"]:
            entries = parse_rss_feed(feed_url, limit_per_source)
            
            for entry in entries:
                if entry["link"]:
                    all_urls.append({
                        "url": entry["link"],
                        "source_name": source_name,
                        "title": entry["title"],
                        "region": source_config.get("region", "Unknown")
                    })
    
    logger.info(f"Collected {len(all_urls)} URLs from {len(sources)} sources")
    return all_urls


# ===========================================
# TESTING
# ===========================================

def test_rss_feeds():
    """Test RSS feed parsing for all configured sources."""
    print("\n" + "="*60)
    print("🧪 RSS Feed Scraper Test")
    print("="*60)
    
    success_count = 0
    total_articles = 0
    
    for source_name in RSS_FEEDS:
        print(f"\n📰 Testing: {source_name}")
        print("-" * 40)
        
        source_config = RSS_FEEDS[source_name]
        
        for feed_url in source_config["feeds"][:1]:  # Test first feed only
            entries = parse_rss_feed(feed_url, limit=3)
            
            if entries:
                print(f"  ✅ Found {len(entries)} entries")
                for entry in entries[:2]:
                    print(f"     • {entry['title'][:50]}...")
                success_count += 1
                total_articles += len(entries)
            else:
                print(f"  ⚠️ No entries found")
    
    print("\n" + "="*60)
    print(f"Summary: {success_count}/{len(RSS_FEEDS)} sources working")
    print(f"Total articles found: {total_articles}")
    print("="*60 + "\n")
    
    return success_count, total_articles


if __name__ == "__main__":
    test_rss_feeds()
