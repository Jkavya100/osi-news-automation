"""
OSI News Automation System - Batch Scraper
===========================================
Scrapes articles from multiple configured news sources.
Supports both web scraping and RSS feed methods.
"""

import yaml
from bs4 import BeautifulSoup
import requests
from loguru import logger
from typing import List, Dict, Optional
import time
from random import uniform
import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.news_scraper import scrape_single_article
from src.scrapers.rss_scraper import parse_rss_feed


# ===========================================
# URL FILTERING
# ===========================================

# URL patterns to exclude (ads, videos, galleries, etc.)
EXCLUDED_URL_PATTERNS = [
    '/video/', '/videos/', '/gallery/', '/galleries/',
    '/live/', '/sport/', '/sports/',
    '/weather/', '/lottery/', '/games/',
    '/login', '/signup', '/subscribe',
    '/ads/', '/advertisement/',
    '.pdf', '.jpg', '.png', '.gif',
    'facebook.com', 'twitter.com', 'instagram.com',
    '/author/', '/tag/', '/category/',
]


def is_valid_article_url(url: str, source_url: str) -> bool:
    """
    Check if URL is likely a valid news article.
    
    Args:
        url: URL to check.
        source_url: Base URL of the source.
        
    Returns:
        bool: True if URL appears to be a valid article.
    """
    if not url:
        return False
    
    # Must be HTTP(S)
    if not url.startswith(('http://', 'https://')):
        return False
    
    # Must be from same domain (or subdomain)
    source_domain = urlparse(source_url).netloc.replace('www.', '')
    url_domain = urlparse(url).netloc.replace('www.', '')
    
    if source_domain not in url_domain and url_domain not in source_domain:
        return False
    
    # Check excluded patterns
    url_lower = url.lower()
    for pattern in EXCLUDED_URL_PATTERNS:
        if pattern in url_lower:
            return False
    
    # URL should have some path (not just homepage)
    path = urlparse(url).path
    if not path or path == '/':
        return False
    
    return True


def normalize_url(href: str, base_url: str) -> Optional[str]:
    """
    Convert relative URL to absolute URL.
    
    Args:
        href: Raw href from page.
        base_url: Base URL of the page.
        
    Returns:
        Absolute URL or None if invalid.
    """
    if not href:
        return None
    
    # Already absolute
    if href.startswith(('http://', 'https://')):
        return href
    
    # Protocol-relative
    if href.startswith('//'):
        return 'https:' + href
    
    # Relative URL
    return urljoin(base_url, href)


# ===========================================
# URL EXTRACTION
# ===========================================

def extract_article_urls_from_page(source: Dict) -> List[str]:
    """
    Extract article URLs from a news source homepage using CSS selectors.
    
    Args:
        source: Source configuration dictionary from YAML.
        
    Returns:
        List of article URLs.
    """
    try:
        logger.debug(f"Extracting URLs from: {source['url']}")
        
        headers = {
            'User-Agent': os.getenv('USER_AGENT', 'RobinOSI-Bot/1.0'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        timeout = int(os.getenv('REQUEST_TIMEOUT_SECONDS', 30))
        response = requests.get(source['url'], headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        article_urls = []
        max_per_source = source.get('max_articles_per_source', 10)
        
        # Try configured selector first
        if 'selectors' in source and 'article_url' in source['selectors']:
            selector = source['selectors']['article_url']
            links = soup.select(selector)
            
            for link in links:
                href = link.get('href')
                url = normalize_url(href, source['url'])
                
                if url and is_valid_article_url(url, source['url']):
                    if url not in article_urls:
                        article_urls.append(url)
                        
                        if len(article_urls) >= max_per_source:
                            break
        
        # Fallback: Try common article link patterns
        if not article_urls:
            # Try finding links within article containers
            common_selectors = [
                'article a', 'h2 a', 'h3 a',
                '.article a', '.story a', '.news-item a',
                '[data-testid*="headline"] a', '[class*="headline"] a',
            ]
            
            for selector in common_selectors:
                try:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href')
                        url = normalize_url(href, source['url'])
                        
                        if url and is_valid_article_url(url, source['url']):
                            if url not in article_urls:
                                article_urls.append(url)
                                
                                if len(article_urls) >= max_per_source:
                                    break
                    
                    if article_urls:
                        break
                except Exception:
                    continue
        
        logger.info(f"Found {len(article_urls)} article URLs from {source['name']}")
        return article_urls
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching {source['name']}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {source['name']}: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to extract URLs from {source['name']}: {e}")
        return []


def extract_article_urls_from_rss(source: Dict) -> List[str]:
    """
    Extract article URLs from a news source's RSS feed.
    
    Args:
        source: Source configuration dictionary from YAML.
        
    Returns:
        List of article URLs.
    """
    urls = []
    max_per_source = source.get('max_articles_per_source', 10)
    
    if 'rss_feed' not in source:
        return []
    
    rss_url = source['rss_feed']
    entries = parse_rss_feed(rss_url, limit=max_per_source)
    
    for entry in entries:
        if entry.get('link'):
            urls.append(entry['link'])
    
    return urls


def extract_article_urls(source: Dict, prefer_rss: bool = True) -> List[str]:
    """
    Extract article URLs from a source using best available method.
    
    Args:
        source: Source configuration dictionary.
        prefer_rss: If True, try RSS first (more reliable).
        
    Returns:
        List of article URLs.
    """
    urls = []
    
    if prefer_rss and 'rss_feed' in source:
        # Try RSS first (more reliable)
        urls = extract_article_urls_from_rss(source)
        
        if urls:
            logger.debug(f"Using RSS for {source['name']}: {len(urls)} URLs")
            return urls
    
    # Fall back to page scraping
    urls = extract_article_urls_from_page(source)
    
    if urls:
        logger.debug(f"Using page scraping for {source['name']}: {len(urls)} URLs")
    
    return urls


# ===========================================
# BATCH SCRAPING
# ===========================================

def load_news_sources(config_path: str = 'config/news_sources.yaml') -> List[Dict]:
    """
    Load enabled news sources from configuration file.
    
    Args:
        config_path: Path to news_sources.yaml.
        
    Returns:
        List of enabled source configurations, sorted by priority.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Filter enabled sources
        sources = [s for s in config.get('sources', []) if s.get('enabled', True)]
        
        # Sort by priority (1 = highest)
        sources.sort(key=lambda x: x.get('priority', 5))
        
        logger.info(f"Loaded {len(sources)} enabled news sources")
        return sources
        
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return []


def scrape_news_batch(
    max_articles: int = 50,
    sources: List[Dict] = None,
    prefer_rss: bool = True,
    min_per_source: int = 2,
    max_per_source: int = 10,
    session_id: str = None
) -> List[Dict]:
    """
    Scrape articles from multiple news sources.
    
    Loads configured sources, extracts article URLs, and scrapes each article
    until max_articles is reached. Distributes across sources by priority.
    
    Args:
        max_articles: Maximum total articles to scrape.
        sources: List of source configs. If None, loads from YAML.
        prefer_rss: Prefer RSS feeds over page scraping.
        min_per_source: Minimum articles to try from each source.
        max_per_source: Maximum articles per source.
        session_id: Optional session ID to attach to articles.
        
    Returns:
        List of successfully scraped article dictionaries.
    """
    articles = []
    failed_urls = []
    
    # Generate session ID if not provided
    if not session_id:
        session_id = f"BATCH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Load sources if not provided
    if sources is None:
        sources = load_news_sources()
    
    if not sources:
        logger.error("No news sources configured")
        return []
    
    logger.info(f"🚀 Starting batch scrape from {len(sources)} sources...")
    logger.info(f"   Target: {max_articles} articles | Session: {session_id}")
    
    start_time = time.time()
    sources_scraped = 0
    
    for source in sources:
        if len(articles) >= max_articles:
            logger.info(f"Reached target of {max_articles} articles")
            break
        
        source_name = source.get('name', 'Unknown')
        logger.info(f"\n📰 Scraping: {source_name} (Priority: {source.get('priority', 5)})")
        
        try:
            # Get article URLs
            article_urls = extract_article_urls(source, prefer_rss=prefer_rss)
            
            if not article_urls:
                logger.warning(f"   No articles found from {source_name}")
                continue
            
            # Limit URLs per source
            article_urls = article_urls[:max_per_source]
            logger.info(f"   Found {len(article_urls)} article URLs")
            
            source_articles = 0
            rate_limit = source.get('rate_limit_delay', 2)
            
            for url in article_urls:
                if len(articles) >= max_articles:
                    break
                
                # Rate limiting with randomization
                delay = uniform(rate_limit, rate_limit + 1.5)
                time.sleep(delay)
                
                # Scrape article
                article_data = scrape_single_article(url, source_name)
                
                if article_data:
                    # Add metadata
                    article_data['source_region'] = source.get('region', 'Unknown')
                    article_data['session_id'] = session_id
                    article_data['priority'] = source.get('priority', 5)
                    
                    articles.append(article_data)
                    source_articles += 1
                    
                    logger.info(f"   ✅ [{len(articles)}/{max_articles}] {article_data['heading'][:50]}...")
                else:
                    failed_urls.append(url)
                
                # Check if we have minimum from this source
                if source_articles >= min_per_source and len(articles) >= max_articles * 0.5:
                    # Move to next source after getting minimum
                    break
            
            if source_articles > 0:
                sources_scraped += 1
                logger.info(f"   Scraped {source_articles} articles from {source_name}")
            
        except Exception as e:
            logger.error(f"Error processing {source_name}: {e}")
            continue
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 Batch Scrape Summary")
    logger.info("="*60)
    logger.info(f"   Articles scraped: {len(articles)}")
    logger.info(f"   Sources used: {sources_scraped}/{len(sources)}")
    logger.info(f"   Failed URLs: {len(failed_urls)}")
    logger.info(f"   Duration: {duration:.1f} seconds")
    logger.info(f"   Session ID: {session_id}")
    logger.info("="*60 + "\n")
    
    return articles


def scrape_specific_sources(
    source_names: List[str],
    max_articles: int = 50,
    prefer_rss: bool = True
) -> List[Dict]:
    """
    Scrape articles from specific named sources.
    
    Args:
        source_names: List of source names to scrape.
        max_articles: Maximum total articles.
        prefer_rss: Prefer RSS feeds.
        
    Returns:
        List of scraped articles.
    """
    all_sources = load_news_sources()
    
    # Filter to requested sources
    selected_sources = [
        s for s in all_sources 
        if s.get('name', '') in source_names
    ]
    
    if not selected_sources:
        logger.warning(f"None of the requested sources found: {source_names}")
        return []
    
    return scrape_news_batch(
        max_articles=max_articles,
        sources=selected_sources,
        prefer_rss=prefer_rss
    )


# ===========================================
# TESTING
# ===========================================

def test_batch_scraper():
    """Test batch scraping with a small number of articles."""
    print("\n" + "="*60)
    print("🧪 Batch Scraper Test")
    print("="*60)
    
    # Test with just 5 articles
    articles = scrape_news_batch(max_articles=5, prefer_rss=True)
    
    print(f"\n📰 Scraped {len(articles)} articles:")
    print("-" * 40)
    
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['heading'][:55]}...")
        print(f"   Source: {article.get('source_name', 'Unknown')}")
        print(f"   Words: {article.get('word_count', 0)}")
        print()
    
    print("="*60)
    if len(articles) > 0:
        print("✅ Batch scraper test passed!")
    else:
        print("⚠️ No articles scraped (network or source issues)")
    print("="*60 + "\n")
    
    return articles


if __name__ == "__main__":
    test_batch_scraper()
