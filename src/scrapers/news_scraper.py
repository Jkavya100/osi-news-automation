"""
OSI News Automation System - News Scraper
==========================================
Robust single-article scraper using newspaper3k.
Extracts structured article data with error handling.
"""

from newspaper import Article, Config
from langdetect import detect, LangDetectException
from datetime import datetime
from loguru import logger
from typing import Dict, Optional, List
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ===========================================
# CONFIGURATION
# ===========================================

def get_scraper_config() -> Config:
    """
    Create and return a configured newspaper3k Config object.
    
    Returns:
        Config: Configured newspaper3k configuration.
    """
    config = Config()
    config.browser_user_agent = os.getenv("USER_AGENT", "RobinOSI-Bot/1.0")
    config.request_timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", 30))
    config.fetch_images = True
    config.memoize_articles = True
    config.language = 'en'
    config.number_threads = 1  # Single thread for single article
    
    return config


# ===========================================
# TEXT CLEANING UTILITIES
# ===========================================

def clean_text(text: str) -> str:
    """
    Clean article text by removing extra whitespace and formatting.
    
    Args:
        text: Raw article text.
        
    Returns:
        str: Cleaned text.
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove common artifacts
    text = re.sub(r'\[.*?\]', '', text)  # Remove [brackets]
    text = re.sub(r'Advertisement\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'ADVERTISEMENT\s*', '', text)
    text = re.sub(r'Continue reading.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Read more:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Also read:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Related:.*', '', text, flags=re.IGNORECASE)
    
    # Remove multiple periods
    text = re.sub(r'\.{2,}', '.', text)
    
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def clean_heading(heading: str) -> str:
    """
    Clean article heading.
    
    Args:
        heading: Raw article heading.
        
    Returns:
        str: Cleaned heading.
    """
    if not heading:
        return ""
    
    # Remove source name suffixes
    heading = re.sub(r'\s*[-|]\s*(BBC|CNN|Reuters|Guardian|Times).*$', '', heading, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    heading = re.sub(r'\s+', ' ', heading)
    
    return heading.strip()


# ===========================================
# LOCATION EXTRACTION
# ===========================================

# Common cities for location detection
MAJOR_CITIES = [
    # India
    'New Delhi', 'Delhi', 'Mumbai', 'Bengaluru', 'Bangalore', 'Chennai', 
    'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow',
    'Chandigarh', 'Bhopal', 'Patna', 'Kochi', 'Guwahati',
    
    # US
    'Washington', 'New York', 'Los Angeles', 'Chicago', 'Houston', 
    'San Francisco', 'Seattle', 'Boston', 'Atlanta', 'Miami',
    
    # UK
    'London', 'Manchester', 'Birmingham', 'Edinburgh', 'Glasgow', 'Belfast',
    
    # Europe
    'Paris', 'Berlin', 'Rome', 'Madrid', 'Brussels', 'Amsterdam',
    'Vienna', 'Zurich', 'Geneva', 'Stockholm', 'Oslo', 'Copenhagen',
    
    # Asia
    'Beijing', 'Shanghai', 'Hong Kong', 'Tokyo', 'Seoul', 'Singapore',
    'Bangkok', 'Jakarta', 'Kuala Lumpur', 'Manila', 'Hanoi',
    
    # Middle East
    'Dubai', 'Abu Dhabi', 'Riyadh', 'Doha', 'Tel Aviv', 'Jerusalem',
    'Cairo', 'Beirut', 'Amman', 'Baghdad', 'Tehran',
    
    # Other
    'Moscow', 'Sydney', 'Melbourne', 'Toronto', 'Ottawa', 'Brasilia',
    'Mexico City', 'Buenos Aires', 'Johannesburg', 'Nairobi', 'Lagos'
]

# Country mappings
COUNTRY_MAPPINGS = {
    'New Delhi': 'India', 'Delhi': 'India', 'Mumbai': 'India',
    'London': 'UK', 'Manchester': 'UK',
    'Washington': 'USA', 'New York': 'USA',
    'Beijing': 'China', 'Shanghai': 'China',
    'Tokyo': 'Japan', 'Seoul': 'South Korea',
    'Paris': 'France', 'Berlin': 'Germany',
    'Moscow': 'Russia', 'Dubai': 'UAE',
}


def extract_location(text: str, metadata: dict = None) -> str:
    """
    Extract location from article text or metadata.
    
    Uses multiple strategies:
    1. Check metadata for location field
    2. Look for dateline pattern (CITY, Date)
    3. Search for city mentions in first paragraph
    
    Args:
        text: Article text content.
        metadata: Article metadata dictionary.
        
    Returns:
        str: Extracted location or "Unknown".
    """
    metadata = metadata or {}
    
    # Strategy 1: Check metadata
    for key in ['location', 'geo', 'geo.placename', 'news_geo']:
        if key in metadata and metadata[key]:
            return str(metadata[key])
    
    # Strategy 2: Look for dateline pattern (CITY NAME, Date/Month)
    # Examples: "NEW DELHI, Jan 15", "WASHINGTON (Reuters)"
    dateline_patterns = [
        r'^([A-Z][A-Z\s]+),\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
        r'^([A-Z][A-Z\s]+)\s*\((?:Reuters|AP|AFP|PTI)\)',
        r'^([A-Z][A-Za-z\s]+):\s+',
        r'^([A-Z][A-Z]+)\s*[-–—]\s*',
    ]
    
    for pattern in dateline_patterns:
        match = re.search(pattern, text[:200])
        if match:
            location = match.group(1).strip().title()
            if len(location) > 2 and len(location) < 30:
                return location
    
    # Strategy 3: Search for city mentions in first paragraph
    first_para = text[:500] if text else ""
    
    for city in MAJOR_CITIES:
        # Match as whole word
        if re.search(r'\b' + re.escape(city) + r'\b', first_para, re.IGNORECASE):
            return city
    
    # Strategy 4: Check og:locale or similar metadata
    if 'og' in metadata:
        og = metadata['og']
        if isinstance(og, dict) and 'locale' in og:
            locale = og['locale']
            locale_map = {
                'en_IN': 'India', 'en_US': 'USA', 'en_GB': 'UK',
                'en_AU': 'Australia', 'fr_FR': 'France', 'de_DE': 'Germany'
            }
            if locale in locale_map:
                return locale_map[locale]
    
    return "Unknown"


# ===========================================
# ARTICLE VALIDATION
# ===========================================

def validate_article_data(article_data: Dict) -> tuple[bool, str]:
    """
    Validate that article data has all required fields and meets quality thresholds.
    
    Args:
        article_data: Dictionary containing article data.
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Required fields
    required_fields = ['heading', 'story', 'source_url']
    
    for field in required_fields:
        if field not in article_data or not article_data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate heading
    if len(article_data['heading']) < 10:
        return False, "Heading too short (< 10 chars)"
    
    if len(article_data['heading']) > 500:
        return False, "Heading too long (> 500 chars)"
    
    # Validate story length
    min_words = int(os.getenv("MIN_ARTICLE_WORDS", 50))
    word_count = len(article_data.get('story', '').split())
    
    if word_count < min_words:
        return False, f"Article too short ({word_count} words, minimum {min_words})"
    
    # Validate URL format
    url = article_data['source_url']
    if not url.startswith(('http://', 'https://')):
        return False, "Invalid URL format"
    
    return True, ""


# ===========================================
# MAIN SCRAPING FUNCTION
# ===========================================

def scrape_single_article(url: str, source_name: str = "") -> Optional[Dict]:
    """
    Scrape a single news article using newspaper3k.
    
    Extracts:
    - heading (title)
    - story (full text, cleaned)
    - authors (list)
    - publish_date (ISO format)
    - top_image (URL)
    - source_url (original URL)
    - location (extracted from text/metadata)
    - language (auto-detected)
    
    Args:
        url: Article URL to scrape.
        source_name: Name of news source (for logging and metadata).
        
    Returns:
        Dictionary with article data or None if failed.
        
    Example:
        >>> article = scrape_single_article("https://bbc.com/news/article")
        >>> if article:
        ...     print(article['heading'])
    """
    if not url:
        logger.error("Empty URL provided")
        return None
    
    try:
        logger.debug(f"Scraping: {url}")
        
        # Configure newspaper3k
        config = get_scraper_config()
        
        # Create and download article
        article = Article(url, config=config)
        article.download()
        
        # Check if download succeeded
        if not article.html:
            logger.warning(f"Empty HTML response from: {url}")
            return None
        
        # Parse article
        article.parse()
        
        # Get basic text
        raw_text = article.text
        if not raw_text or len(raw_text.strip()) < 50:
            logger.warning(f"Insufficient content from: {url}")
            return None
        
        # Clean text
        story = clean_text(raw_text)
        heading = clean_heading(article.title)
        
        # Extract location
        metadata = article.meta_data if hasattr(article, 'meta_data') else {}
        location = extract_location(raw_text, metadata)
        
        # Detect language
        try:
            sample_text = story[:500] if len(story) > 500 else story
            language = detect(sample_text)
        except LangDetectException:
            language = 'en'
        except Exception:
            language = 'en'
        
        # Get publish date
        if article.publish_date:
            if hasattr(article.publish_date, 'isoformat'):
                publish_date = article.publish_date.isoformat()
            else:
                publish_date = str(article.publish_date)
        else:
            publish_date = datetime.utcnow().isoformat()
        
        # Get authors
        authors = article.authors if article.authors else []
        # Clean author names
        authors = [a.strip() for a in authors if a and len(a.strip()) > 1]
        
        # Structure data
        article_data = {
            "heading": heading,
            "story": story,
            "source_url": url,
            "source_name": source_name,
            "authors": authors,
            "publish_date": publish_date,
            "top_image": article.top_image or "",
            "location": location,
            "language": language,
            "scraped_at": datetime.utcnow().isoformat(),
            "word_count": len(story.split()),
            "meta_keywords": article.meta_keywords if hasattr(article, 'meta_keywords') else [],
            "meta_description": article.meta_description if hasattr(article, 'meta_description') else ""
        }
        
        # Validate article
        is_valid, error_msg = validate_article_data(article_data)
        if not is_valid:
            logger.warning(f"Validation failed for {url}: {error_msg}")
            return None
        
        logger.info(f"✅ Scraped: {heading[:50]}... ({article_data['word_count']} words)")
        return article_data
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ Failed to scrape {url}: [{error_type}] {str(e)}")
        return None


# ===========================================
# BATCH SCRAPING
# ===========================================

def scrape_multiple_articles(
    urls: List[str], 
    source_name: str = "",
    delay_seconds: float = 2.0
) -> List[Dict]:
    """
    Scrape multiple articles from a list of URLs.
    
    Args:
        urls: List of article URLs to scrape.
        source_name: Name of news source.
        delay_seconds: Delay between requests (for rate limiting).
        
    Returns:
        List of successfully scraped article dictionaries.
    """
    import time
    
    results = []
    total = len(urls)
    
    for i, url in enumerate(urls, 1):
        logger.info(f"Scraping article {i}/{total} from {source_name}")
        
        article = scrape_single_article(url, source_name)
        if article:
            results.append(article)
        
        # Rate limiting (skip delay on last article)
        if i < total and delay_seconds > 0:
            time.sleep(delay_seconds)
    
    logger.info(f"Scraped {len(results)}/{total} articles from {source_name}")
    return results


# ===========================================
# URL EXTRACTION FROM SOURCE
# ===========================================

def get_article_urls_from_source(source_url: str, limit: int = 10) -> List[str]:
    """
    Extract article URLs from a news source homepage.
    
    Uses newspaper3k's build functionality to find article links.
    
    Args:
        source_url: News source homepage URL (e.g., https://www.bbc.com).
        limit: Maximum number of URLs to return.
        
    Returns:
        List of article URLs.
    """
    from newspaper import build
    
    try:
        logger.info(f"Building source: {source_url}")
        
        config = get_scraper_config()
        config.memoize_articles = False  # Don't cache for fresh results
        
        source = build(source_url, config=config, memoize_articles=False)
        
        # Get article URLs
        urls = [a.url for a in source.articles if a.url]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        # Limit results
        result_urls = unique_urls[:limit]
        
        logger.info(f"Found {len(result_urls)} article URLs from {source_url}")
        return result_urls
        
    except Exception as e:
        logger.error(f"Failed to get URLs from {source_url}: {e}")
        return []


# ===========================================
# TESTING UTILITIES
# ===========================================

def test_scraper():
    """Test the scraper with a sample article."""
    print("\n" + "="*60)
    print("🧪 News Scraper Test")
    print("="*60)
    
    # Test URLs
    test_urls = [
        ("https://www.bbc.com/news", "BBC News"),
        ("https://www.reuters.com", "Reuters"),
    ]
    
    for source_url, source_name in test_urls:
        print(f"\n📰 Testing: {source_name}")
        print("-" * 40)
        
        # Get article URLs
        urls = get_article_urls_from_source(source_url, limit=2)
        
        if not urls:
            print(f"  ⚠️ No URLs found from {source_name}")
            continue
        
        # Scrape first article
        for url in urls[:1]:
            article = scrape_single_article(url, source_name)
            
            if article:
                print(f"  ✅ Success!")
                print(f"  📝 Heading: {article['heading'][:60]}...")
                print(f"  📊 Words: {article['word_count']}")
                print(f"  📍 Location: {article['location']}")
                print(f"  🌐 Language: {article['language']}")
            else:
                print(f"  ❌ Failed to scrape")
    
    print("\n" + "="*60)
    print("Test completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_scraper()
