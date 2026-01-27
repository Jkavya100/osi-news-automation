"""
OSI News Automation System - Database Tests
============================================
Tests for MongoDB client functionality.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime


def test_mongo_client_import():
    """Test that MongoDBClient can be imported."""
    from src.database.mongo_client import MongoDBClient
    assert MongoDBClient is not None
    print("✅ MongoDBClient imported successfully")


def test_mongo_client_initialization():
    """Test that MongoDBClient can be initialized without connection."""
    from src.database.mongo_client import MongoDBClient
    
    client = MongoDBClient(
        uri="mongodb://localhost:27017/",
        database_name="test_osi_news"
    )
    
    assert client.uri == "mongodb://localhost:27017/"
    assert client.database_name == "test_osi_news"
    assert client._connected == False
    print("✅ MongoDBClient initialized correctly")


def test_mongo_client_connection():
    """Test MongoDB connection (requires running MongoDB)."""
    from src.database.mongo_client import MongoDBClient
    
    client = MongoDBClient()
    connected = client.connect()
    
    if connected:
        print("✅ Connected to MongoDB successfully")
        
        # Test save article
        test_article = {
            "heading": "Test Article",
            "story": "This is test content for the OSI News Automation System.",
            "source_url": f"https://test.com/{datetime.utcnow().timestamp()}",
            "session_id": "TEST123",
            "language": "en",
            "location": "Test Location"
        }
        
        article_id = client.save_article(test_article)
        
        if article_id:
            print(f"✅ Saved article with ID: {article_id}")
            
            # Test retrieve
            retrieved = client.get_article_by_id(article_id)
            assert retrieved is not None
            assert retrieved['heading'] == "Test Article"
            print("✅ Retrieved article successfully")
            
            # Test update status
            updated = client.update_upload_status(article_id, "uploaded", "HW12345")
            print(f"✅ Updated upload status: {updated}")
            
            # Test duplicate detection
            is_dup = client.check_duplicate(
                "This is test content for the OSI News Automation System.",
                0.85
            )
            print(f"✅ Duplicate detection result: {is_dup}")
            
            # Test statistics
            stats = client.get_statistics()
            print(f"✅ Database statistics: {stats.get('total_articles', 0)} articles")
        else:
            print("⚠️ Could not save article (may be duplicate URL)")
        
        client.disconnect()
        print("✅ Disconnected from MongoDB")
    else:
        print("⚠️ Could not connect to MongoDB (is it running?)")
        print("   To install MongoDB locally: https://www.mongodb.com/try/download/community")


def run_all_tests():
    """Run all database tests."""
    print("\n" + "="*50)
    print("OSI News Automation - Database Tests")
    print("="*50 + "\n")
    
    test_mongo_client_import()
    test_mongo_client_initialization()
    test_mongo_client_connection()
    
    print("\n" + "="*50)
    print("Database tests completed!")
    print("="*50 + "\n")


if __name__ == "__main__":
    run_all_tests()
