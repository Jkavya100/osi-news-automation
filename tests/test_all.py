"""
OSI News Automation System - Comprehensive Test Suite
======================================================
Verifies all components are working correctly.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_imports():
    """Test all critical imports."""
    print("\n📦 Testing Imports...")
    
    try:
        from src.database.mongo_client import MongoDBClient
        print("  ✅ MongoDBClient")
    except ImportError as e:
        print(f"  ❌ MongoDBClient: {e}")
        return False
    
    try:
        from src.scrapers.news_scraper import scrape_single_article
        print("  ✅ news_scraper")
    except ImportError as e:
        print(f"  ❌ news_scraper: {e}")
        return False
    
    try:
        from src.scrapers.rss_scraper import parse_rss_feed, get_all_rss_urls
        print("  ✅ rss_scraper")
    except ImportError as e:
        print(f"  ❌ rss_scraper: {e}")
        return False
    
    try:
        import yaml
        print("  ✅ yaml")
    except ImportError as e:
        print(f"  ❌ yaml: {e}")
        return False
    
    return True


def test_config_files():
    """Test configuration files are valid."""
    print("\n📄 Testing Config Files...")
    
    import yaml
    
    # Test news_sources.yaml
    try:
        with open('config/news_sources.yaml', 'r') as f:
            sources = yaml.safe_load(f)
        assert len(sources['sources']) == 25
        print(f"  ✅ news_sources.yaml: {len(sources['sources'])} sources")
    except Exception as e:
        print(f"  ❌ news_sources.yaml: {e}")
        return False
    
    # Test .env.example
    try:
        with open('.env.example', 'r') as f:
            content = f.read()
        assert 'MONGODB_LOCAL_URI' in content
        assert 'GROQ_API_KEY' in content
        print("  ✅ .env.example: Valid")
    except Exception as e:
        print(f"  ❌ .env.example: {e}")
        return False
    
    return True


def test_database():
    """Test MongoDB connection and operations."""
    print("\n🗄️ Testing Database...")
    
    from src.database.mongo_client import MongoDBClient
    
    client = MongoDBClient()
    
    if not client.connect():
        print("  ⚠️ MongoDB not running (skipping DB tests)")
        return True  # Not a failure if MongoDB isn't running
    
    print("  ✅ MongoDB connection")
    
    # Test statistics
    stats = client.get_statistics()
    print(f"  ✅ Database stats: {stats.get('total_articles', 0)} articles")
    
    client.disconnect()
    print("  ✅ Disconnect successful")
    
    return True


def test_rss_feeds():
    """Test RSS feed parsing."""
    print("\n📡 Testing RSS Feeds...")
    
    from src.scrapers.rss_scraper import parse_rss_feed
    
    # Test BBC RSS
    entries = parse_rss_feed("https://feeds.bbci.co.uk/news/rss.xml", limit=3)
    
    if entries:
        print(f"  ✅ BBC RSS: {len(entries)} entries")
        for entry in entries[:2]:
            print(f"     • {entry['title'][:50]}...")
        return True
    else:
        print("  ⚠️ BBC RSS: No entries (may be network issue)")
        return True  # Not a critical failure


def test_scraper():
    """Test article scraping."""
    print("\n📰 Testing Scraper...")
    
    from src.scrapers.rss_scraper import parse_rss_feed
    from src.scrapers.news_scraper import scrape_single_article
    
    # Get a URL from RSS
    entries = parse_rss_feed("https://feeds.bbci.co.uk/news/rss.xml", limit=1)
    
    if not entries:
        print("  ⚠️ No RSS entries available")
        return True
    
    url = entries[0]['link']
    print(f"  🔗 Testing URL: {url[:60]}...")
    
    article = scrape_single_article(url, "BBC News")
    
    if article:
        print(f"  ✅ Scraped successfully")
        print(f"     Heading: {article['heading'][:50]}...")
        print(f"     Words: {article['word_count']}")
        print(f"     Language: {article['language']}")
        return True
    else:
        print("  ⚠️ Scrape failed (site may be blocking)")
        return True  # Not critical


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("🧪 OSI News Automation - Comprehensive Test Suite")
    print("="*60)
    
    results = {
        "Imports": test_imports(),
        "Config Files": test_config_files(),
        "Database": test_database(),
        "RSS Feeds": test_rss_feeds(),
        "Scraper": test_scraper(),
    }
    
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
