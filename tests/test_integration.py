"""
OSI News Automation System - Integration Tests
===============================================
Comprehensive integration tests for the complete pipeline.
Tests scraping, trend detection, article generation, database operations,
and social media post generation.
"""

import pytest
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.scrapers.batch_scraper import scrape_news_batch
from src.trend_detection.trend_analyzer import detect_trends
from src.content_generation.article_generator import generate_article
from src.database.mongo_client import MongoDBClient
from src.api_integrations.social_media_poster import generate_social_posts
from src.translation.translator import translate_article


class TestScraperIntegration:
    """Integration tests for news scraping."""
    
    def test_scraper_returns_articles(self):
        """Test that scraper returns valid articles."""
        articles = scrape_news_batch(max_articles=5)
        
        assert len(articles) > 0, "Should scrape at least one article"
        assert isinstance(articles, list), "Should return a list"
        
    def test_article_structure(self):
        """Test that scraped articles have required fields."""
        articles = scrape_news_batch(max_articles=3)
        
        required_fields = ['heading', 'story', 'source_name', 'source_url']
        
        for article in articles:
            for field in required_fields:
                assert field in article, f"Article missing required field: {field}"
            
            # Validate content quality
            assert len(article['heading']) > 10, "Heading should be substantial"
            assert len(article['story']) > 100, "Story should be substantial"
            assert article['word_count'] > 50, "Should have word count"
    
    def test_article_metadata(self):
        """Test that articles have proper metadata."""
        articles = scrape_news_batch(max_articles=3)
        
        for article in articles:
            assert 'scraped_at' in article, "Should have timestamp"
            assert 'session_id' in article, "Should have session ID"
            assert 'source_region' in article, "Should have source region"


class TestTrendDetection:
    """Integration tests for trend detection."""
    
    def test_trend_detection_with_real_articles(self):
        """Test trend detection with scraped articles."""
        articles = scrape_news_batch(max_articles=10)
        trends = detect_trends(articles, top_n=3)
        
        assert len(trends) > 0, "Should detect at least one trend"
        assert len(trends) <= 3, "Should respect top_n limit"
    
    def test_trend_structure(self):
        """Test that trends have required fields."""
        articles = scrape_news_batch(max_articles=10)
        trends = detect_trends(articles, top_n=2)
        
        required_fields = ['topic', 'articles', 'article_count', 'keywords']
        
        for trend in trends:
            for field in required_fields:
                assert field in trend, f"Trend missing required field: {field}"
            
            assert len(trend['articles']) > 0, "Trend should have articles"
            assert trend['article_count'] == len(trend['articles']), "Count should match"
    
    def test_trend_with_mock_data(self):
        """Test trend detection with mock articles."""
        mock_articles = [
            {
                "heading": "Climate Summit Reaches Agreement",
                "story": "World leaders agreed on climate action...",
                "source_name": "BBC",
                "location": "Paris"
            },
            {
                "heading": "Climate Change Conference Concludes",
                "story": "The climate conference ended with new commitments...",
                "source_name": "Reuters",
                "location": "Paris"
            },
            {
                "heading": "Tech Giants Announce AI Partnership",
                "story": "Major tech companies formed AI alliance...",
                "source_name": "TechCrunch",
                "location": "San Francisco"
            }
        ]
        
        trends = detect_trends(mock_articles, top_n=2)
        
        assert len(trends) > 0, "Should detect trends from mock data"


class TestArticleGeneration:
    """Integration tests for article generation."""
    
    def test_article_generation_from_trend(self):
        """Test generating article from a trend."""
        # Create test trend
        test_articles = [
            {
                "heading": "Global Markets Rally on Economic Data",
                "story": "Stock markets around the world surged today...",
                "source_name": "Bloomberg",
                "location": "New York"
            },
            {
                "heading": "Economic Growth Exceeds Expectations",
                "story": "The economy grew faster than predicted...",
                "source_name": "Reuters",
                "location": "Washington"
            }
        ]
        
        test_trend = {
            "topic": "Economic Growth",
            "articles": test_articles,
            "article_count": 2,
            "keywords": ["economy", "growth", "markets"]
        }
        
        generated = generate_article(test_trend, target_words=500)
        
        assert generated is not None, "Should generate article"
        assert 'heading' in generated, "Should have heading"
        assert 'story' in generated, "Should have story"
        assert 'word_count' in generated, "Should have word count"
        assert generated['word_count'] >= 200, "Should meet minimum word count"
    
    def test_generated_article_structure(self):
        """Test that generated articles have proper structure."""
        test_trend = {
            "topic": "Technology Innovation",
            "articles": [
                {
                    "heading": "AI Breakthrough Announced",
                    "story": "Researchers announced a major AI advancement...",
                    "source_name": "Nature",
                    "location": "Cambridge"
                }
            ],
            "article_count": 1,
            "keywords": ["AI", "technology", "innovation"]
        }
        
        generated = generate_article(test_trend)
        
        # Check structure
        assert isinstance(generated['heading'], str), "Heading should be string"
        assert isinstance(generated['story'], str), "Story should be string"
        assert '##' in generated['story'], "Should have subheadings"


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    def db(self):
        """Create database connection."""
        db = MongoDBClient()
        connected = db.connect()
        assert connected, "Should connect to MongoDB"
        return db
    
    def test_save_and_retrieve_article(self, db):
        """Test saving and retrieving articles."""
        test_article = {
            "heading": "Integration Test Article",
            "story": "This is a test article for integration testing.",
            "source_name": "Test Source",
            "source_url": "https://test.com/article",
            "session_id": f"TEST_{datetime.now().timestamp()}",
            "scraped_at": datetime.utcnow().isoformat()
        }
        
        # Save article
        article_id = db.save_article(test_article)
        assert article_id is not None, "Should return article ID"
        
        # Retrieve article
        retrieved = db.articles.find_one({"_id": article_id})
        assert retrieved is not None, "Should retrieve article"
        assert retrieved['heading'] == test_article['heading']
    
    def test_duplicate_detection(self, db):
        """Test duplicate article detection."""
        unique_text = f"Unique test article {datetime.now().timestamp()}"
        
        # First save
        is_dup_before = db.check_duplicate(unique_text, similarity_threshold=0.85)
        assert is_dup_before == False, "Should not be duplicate initially"
        
        # Save article
        test_article = {
            "heading": "Duplicate Test",
            "story": unique_text,
            "session_id": "DUP_TEST"
        }
        db.save_article(test_article)
        
        # Check again
        is_dup_after = db.check_duplicate(unique_text, similarity_threshold=0.85)
        assert is_dup_after == True, "Should detect duplicate"
    
    def test_save_trend(self, db):
        """Test saving trends."""
        test_trend = {
            "topic": "Test Trend",
            "article_count": 5,
            "keywords": ["test", "trend"],
            "session_id": f"TREND_TEST_{datetime.now().timestamp()}"
        }
        
        trend_id = db.save_trend(test_trend)
        assert trend_id is not None, "Should save trend"


class TestSocialMediaIntegration:
    """Integration tests for social media post generation."""
    
    def test_generate_all_platform_posts(self):
        """Test generating posts for all platforms."""
        test_article = {
            "heading": "Breaking: Major Scientific Discovery Announced",
            "dateline": "GENEVA",
            "timestamp": datetime.now().strftime('%A, %B %d, %Y, %I:%M %p IST'),
            "source_count": 12,
            "story": "Scientists announced a breakthrough..."
        }
        
        posts = generate_social_posts(
            test_article,
            article_url="https://example.com/article/123"
        )
        
        # Check all platforms
        assert 'twitter' in posts, "Should have Twitter post"
        assert 'linkedin' in posts, "Should have LinkedIn post"
        assert 'instagram' in posts, "Should have Instagram post"
        assert 'facebook' in posts, "Should have Facebook post"
    
    def test_twitter_character_limit(self):
        """Test that Twitter posts respect 280 character limit."""
        # Create article with very long title
        test_article = {
            "heading": "A" * 200,  # Very long title
            "dateline": "NEW YORK",
            "timestamp": datetime.now().strftime('%A, %B %d, %Y, %I:%M %p IST'),
            "source_count": 10
        }
        
        posts = generate_social_posts(test_article, "https://example.com")
        
        assert len(posts['twitter']) <= 280, f"Twitter post too long: {len(posts['twitter'])} chars"
    
    def test_post_content_quality(self):
        """Test that posts contain required elements."""
        test_article = {
            "heading": "Test Article",
            "dateline": "LONDON",
            "timestamp": datetime.now().strftime('%A, %B %d, %Y, %I:%M %p IST'),
            "source_count": 8
        }
        
        posts = generate_social_posts(test_article, "https://example.com/test")
        
        # Twitter should have hashtags
        assert '#' in posts['twitter'], "Twitter should have hashtags"
        
        # LinkedIn should be professional
        assert 'comprehensive' in posts['linkedin'].lower() or 'analysis' in posts['linkedin'].lower()
        
        # Instagram should have emojis
        assert any(char in posts['instagram'] for char in ['📍', '🕒', '👉'])


class TestTranslationIntegration:
    """Integration tests for translation service."""
    
    def test_translation_enabled_check(self):
        """Test translation service availability."""
        from src.translation.translator import is_translation_enabled
        
        # Should return boolean
        enabled = is_translation_enabled()
        assert isinstance(enabled, bool)
    
    def test_translate_article_structure(self):
        """Test that translated articles have proper structure."""
        if os.getenv('TRANSLATION_ENABLED', 'false').lower() != 'true':
            pytest.skip("Translation not enabled")
        
        test_article = {
            "heading": "Test Article for Translation",
            "story": "This is a test article that will be translated.",
            "language": "en"
        }
        
        translations = translate_article(test_article)
        
        # Should return dictionary of translations
        assert isinstance(translations, dict)
        
        # Each translation should have required fields
        for lang, translated in translations.items():
            assert 'heading' in translated
            assert 'story' in translated
            assert 'language' in translated
            assert translated['language'] == lang


class TestEndToEndPipeline:
    """End-to-end integration tests."""
    
    def test_full_pipeline_dry_run(self):
        """Test complete pipeline in dry-run mode."""
        from run_automation import run_pipeline
        
        try:
            stats = run_pipeline(dry_run=True)
            
            # Check statistics
            assert stats['articles_scraped'] > 0, "Should scrape articles"
            assert stats['trends_detected'] > 0, "Should detect trends"
            assert stats['articles_generated'] > 0, "Should generate articles"
            assert stats['social_posts_generated'] > 0, "Should generate social posts"
            assert len(stats['errors']) == 0, "Should have no errors"
            
            success = True
        except Exception as e:
            print(f"Pipeline error: {e}")
            success = False
        
        assert success, "Full pipeline should complete without errors"
    
    def test_pipeline_output_files(self):
        """Test that pipeline creates expected output files."""
        from run_automation import run_pipeline
        
        stats = run_pipeline(dry_run=True)
        session_id = stats['session_id']
        
        # Check for output files
        output_dir = Path("output/json")
        
        stats_file = output_dir / f"pipeline_stats_{session_id}.json"
        assert stats_file.exists(), "Should create stats file"
        
        social_file = output_dir / f"social_posts_{session_id}.json"
        assert social_file.exists(), "Should create social posts file"


class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_empty_article_list(self):
        """Test trend detection with empty article list."""
        trends = detect_trends([], top_n=5)
        assert trends == [], "Should return empty list for empty input"
    
    def test_invalid_trend_data(self):
        """Test article generation with invalid trend."""
        invalid_trend = {
            "topic": "Test",
            "articles": [],  # Empty articles
            "article_count": 0
        }
        
        # Should handle gracefully
        result = generate_article(invalid_trend)
        # May return None or empty, but shouldn't crash
        assert result is None or isinstance(result, dict)
    
    def test_database_connection_retry(self):
        """Test database connection with invalid URI."""
        db = MongoDBClient(uri="mongodb://invalid:27017/test")
        
        # Should fail gracefully
        connected = db.connect()
        assert connected == False, "Should return False for invalid connection"


# ===========================================
# TEST UTILITIES
# ===========================================

def test_environment_setup():
    """Test that environment is properly configured."""
    required_vars = ['MONGODB_URI', 'GROQ_API_KEY']
    
    for var in required_vars:
        value = os.getenv(var)
        assert value is not None, f"Environment variable {var} not set"
        assert len(value) > 0, f"Environment variable {var} is empty"


def test_output_directories_exist():
    """Test that required output directories exist."""
    required_dirs = [
        'output/json',
        'output/logs',
        'output/images'
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        assert path.exists(), f"Required directory missing: {dir_path}"


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
