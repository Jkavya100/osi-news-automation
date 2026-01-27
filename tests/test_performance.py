"""
OSI News Automation System - Performance Tests
===============================================
Performance benchmarks for critical pipeline components.
Ensures operations complete within acceptable time limits.
"""

import pytest
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.scrapers.batch_scraper import scrape_news_batch
from src.trend_detection.trend_analyzer import detect_trends
from src.content_generation.article_generator import generate_article
from src.database.mongo_client import MongoDBClient
from src.api_integrations.social_media_poster import generate_social_posts


class TestScrapingPerformance:
    """Performance tests for news scraping."""
    
    def test_scrape_5_articles_performance(self):
        """Test scraping 5 articles completes quickly."""
        start = time.time()
        articles = scrape_news_batch(max_articles=5)
        duration = time.time() - start
        
        assert len(articles) > 0, "Should scrape articles"
        assert duration < 60, f"Scraping 5 articles should take <60s, took {duration:.1f}s"
        
        print(f"\n✅ Scraped {len(articles)} articles in {duration:.1f}s")
        print(f"   Average: {duration/len(articles):.1f}s per article")
    
    def test_scrape_10_articles_performance(self):
        """Test scraping 10 articles within time limit."""
        start = time.time()
        articles = scrape_news_batch(max_articles=10)
        duration = time.time() - start
        
        assert duration < 180, f"Scraping 10 articles should take <3min, took {duration:.1f}s"
        
        print(f"\n✅ Scraped {len(articles)} articles in {duration:.1f}s")
    
    def test_scraping_throughput(self):
        """Measure scraping throughput."""
        start = time.time()
        articles = scrape_news_batch(max_articles=10)
        duration = time.time() - start
        
        throughput = len(articles) / duration
        
        print(f"\n📊 Scraping Throughput:")
        print(f"   Articles: {len(articles)}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Throughput: {throughput:.2f} articles/second")
        
        assert throughput > 0.05, "Should scrape at least 1 article per 20 seconds"


class TestTrendDetectionPerformance:
    """Performance tests for trend detection."""
    
    def test_trend_detection_with_10_articles(self):
        """Test trend detection speed with 10 articles."""
        articles = scrape_news_batch(max_articles=10)
        
        start = time.time()
        trends = detect_trends(articles, top_n=3)
        duration = time.time() - start
        
        assert duration < 30, f"Trend detection should take <30s, took {duration:.1f}s"
        
        print(f"\n✅ Detected {len(trends)} trends in {duration:.1f}s")
    
    def test_trend_detection_with_20_articles(self):
        """Test trend detection speed with 20 articles."""
        articles = scrape_news_batch(max_articles=20)
        
        start = time.time()
        trends = detect_trends(articles, top_n=5)
        duration = time.time() - start
        
        assert duration < 60, f"Trend detection should take <60s, took {duration:.1f}s"
        
        print(f"\n✅ Detected {len(trends)} trends from {len(articles)} articles in {duration:.1f}s")
    
    def test_clustering_performance(self):
        """Measure clustering algorithm performance."""
        articles = scrape_news_batch(max_articles=15)
        
        start = time.time()
        trends = detect_trends(articles, top_n=3)
        duration = time.time() - start
        
        print(f"\n📊 Clustering Performance:")
        print(f"   Input articles: {len(articles)}")
        print(f"   Output trends: {len(trends)}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Speed: {len(articles)/duration:.2f} articles/second")


class TestArticleGenerationPerformance:
    """Performance tests for article generation."""
    
    def test_single_article_generation_speed(self):
        """Test generating a single article."""
        test_trend = {
            "topic": "Technology Innovation",
            "articles": [
                {
                    "heading": "AI Breakthrough",
                    "story": "Researchers announced a major advancement in artificial intelligence...",
                    "source_name": "TechCrunch",
                    "location": "San Francisco"
                },
                {
                    "heading": "New AI Model Released",
                    "story": "A new state-of-the-art AI model was released today...",
                    "source_name": "VentureBeat",
                    "location": "Silicon Valley"
                }
            ],
            "article_count": 2,
            "keywords": ["AI", "technology", "innovation"]
        }
        
        start = time.time()
        article = generate_article(test_trend, target_words=500)
        duration = time.time() - start
        
        assert article is not None, "Should generate article"
        assert duration < 60, f"Article generation should take <60s, took {duration:.1f}s"
        
        print(f"\n✅ Generated {article['word_count']} word article in {duration:.1f}s")
    
    def test_multiple_article_generation(self):
        """Test generating multiple articles."""
        # Get real trends
        articles = scrape_news_batch(max_articles=15)
        trends = detect_trends(articles, top_n=3)
        
        start = time.time()
        generated_count = 0
        
        for trend in trends:
            article = generate_article(trend, target_words=500)
            if article:
                generated_count += 1
        
        duration = time.time() - start
        
        print(f"\n📊 Multi-Article Generation:")
        print(f"   Trends processed: {len(trends)}")
        print(f"   Articles generated: {generated_count}")
        print(f"   Total duration: {duration:.1f}s")
        print(f"   Average per article: {duration/generated_count:.1f}s")
        
        assert duration < 180, f"Generating {generated_count} articles should take <3min"


class TestDatabasePerformance:
    """Performance tests for database operations."""
    
    @pytest.fixture
    def db(self):
        """Create database connection."""
        db = MongoDBClient()
        db.connect()
        return db
    
    def test_bulk_insert_performance(self, db):
        """Test bulk inserting articles."""
        test_articles = [
            {
                "heading": f"Test Article {i}",
                "story": f"Test content {i}" * 100,
                "session_id": f"PERF_TEST_{time.time()}",
                "source_name": "Test Source"
            }
            for i in range(10)
        ]
        
        start = time.time()
        for article in test_articles:
            db.save_article(article)
        duration = time.time() - start
        
        print(f"\n📊 Bulk Insert Performance:")
        print(f"   Articles: {len(test_articles)}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Speed: {len(test_articles)/duration:.2f} articles/second")
        
        assert duration < 10, "Inserting 10 articles should take <10s"
    
    def test_duplicate_check_performance(self, db):
        """Test duplicate detection speed."""
        test_text = "This is a test article for duplicate detection performance testing."
        
        # Save an article first
        db.save_article({
            "heading": "Duplicate Test",
            "story": test_text,
            "session_id": f"DUP_PERF_{time.time()}"
        })
        
        # Measure duplicate check
        start = time.time()
        for _ in range(10):
            db.check_duplicate(test_text, similarity_threshold=0.85)
        duration = time.time() - start
        
        print(f"\n📊 Duplicate Check Performance:")
        print(f"   Checks: 10")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Speed: {10/duration:.2f} checks/second")
        
        assert duration < 5, "10 duplicate checks should take <5s"


class TestSocialMediaPerformance:
    """Performance tests for social media post generation."""
    
    def test_single_post_generation_speed(self):
        """Test generating posts for one article."""
        test_article = {
            "heading": "Breaking News: Major Event Occurs",
            "dateline": "NEW YORK",
            "timestamp": "Monday, January 21, 2026, 2:30 PM IST",
            "source_count": 10
        }
        
        start = time.time()
        posts = generate_social_posts(test_article, "https://example.com")
        duration = time.time() - start
        
        assert duration < 1, f"Generating posts should take <1s, took {duration:.3f}s"
        
        print(f"\n✅ Generated {len(posts)} platform posts in {duration:.3f}s")
    
    def test_bulk_post_generation(self):
        """Test generating posts for multiple articles."""
        test_articles = [
            {
                "heading": f"Article {i}",
                "dateline": "LONDON",
                "timestamp": "Monday, January 21, 2026, 2:30 PM IST",
                "source_count": 10
            }
            for i in range(10)
        ]
        
        start = time.time()
        all_posts = []
        for article in test_articles:
            posts = generate_social_posts(article, "https://example.com")
            all_posts.append(posts)
        duration = time.time() - start
        
        print(f"\n📊 Bulk Post Generation:")
        print(f"   Articles: {len(test_articles)}")
        print(f"   Total posts: {len(all_posts) * 4}")  # 4 platforms
        print(f"   Duration: {duration:.1f}s")
        print(f"   Speed: {len(all_posts)/duration:.2f} articles/second")
        
        assert duration < 5, "Generating posts for 10 articles should take <5s"


class TestEndToEndPerformance:
    """End-to-end performance tests."""
    
    def test_full_pipeline_performance(self):
        """Test complete pipeline execution time."""
        from run_automation import run_pipeline
        
        start = time.time()
        stats = run_pipeline(dry_run=True)
        duration = time.time() - start
        
        print(f"\n📊 Full Pipeline Performance:")
        print(f"   Articles scraped: {stats['articles_scraped']}")
        print(f"   Trends detected: {stats['trends_detected']}")
        print(f"   Articles generated: {stats['articles_generated']}")
        print(f"   Social posts: {stats['social_posts_generated']}")
        print(f"   Total duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        
        # Pipeline should complete in reasonable time
        # With 5 articles, should take <2 minutes
        max_duration = 120 if stats['articles_scraped'] <= 5 else 300
        
        assert duration < max_duration, f"Pipeline should complete in <{max_duration}s"
    
    def test_pipeline_scalability(self):
        """Test pipeline with different article counts."""
        from run_automation import run_pipeline
        import os
        
        # Test with small batch
        os.environ['MAX_ARTICLES_PER_RUN'] = '3'
        
        start = time.time()
        stats = run_pipeline(dry_run=True)
        duration = time.time() - start
        
        throughput = stats['articles_generated'] / duration if duration > 0 else 0
        
        print(f"\n📊 Pipeline Scalability:")
        print(f"   Input articles: {stats['articles_scraped']}")
        print(f"   Output articles: {stats['articles_generated']}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Throughput: {throughput:.4f} generated articles/second")


# ===========================================
# PERFORMANCE SUMMARY
# ===========================================

def test_performance_summary():
    """Generate performance summary report."""
    print("\n" + "="*60)
    print("📊 PERFORMANCE TEST SUMMARY")
    print("="*60)
    print("\nExpected Performance Benchmarks:")
    print("  • Scraping: <60s for 5 articles")
    print("  • Trend Detection: <30s for 10 articles")
    print("  • Article Generation: <60s per article")
    print("  • Social Posts: <1s per article")
    print("  • Full Pipeline: <2min for 5 articles")
    print("\n" + "="*60)


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
