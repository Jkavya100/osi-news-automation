"""
OSI News Automation System - Database Initialization Script
============================================================
Initializes MongoDB with required collections, indexes, validation schemas,
and test data. This script is idempotent - safe to run multiple times.
"""

from datetime import datetime, timedelta
from loguru import logger
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.database.mongo_client import MongoDBClient


# ===========================================
# VALIDATION SCHEMAS
# ===========================================

ARTICLES_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["heading", "story", "scraped_at"],
        "properties": {
            "heading": {
                "bsonType": "string",
                "description": "Article headline - required"
            },
            "story": {
                "bsonType": "string",
                "description": "Article content - required"
            },
            "source_url": {
                "bsonType": "string",
                "description": "Original source URL"
            },
            "scraped_at": {
                "bsonType": "date",
                "description": "Timestamp when scraped - required"
            },
            "session_id": {
                "bsonType": "string",
                "description": "Scraping session identifier"
            },
            "location": {
                "bsonType": "string",
                "description": "Geographic location/region"
            },
            "language": {
                "bsonType": "string",
                "description": "Article language code"
            },
            "embedding": {
                "bsonType": "array",
                "description": "Sentence embedding for duplicate detection"
            },
            "upload_status": {
                "bsonType": "string",
                "enum": ["pending", "uploaded", "failed", "skipped"],
                "description": "Upload status to Hocalwire"
            },
            "hocalwire_feed_id": {
                "bsonType": "string",
                "description": "Hocalwire feed ID after upload"
            }
        }
    }
}

TRENDS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["topic", "first_seen"],
        "properties": {
            "topic": {
                "bsonType": "string",
                "description": "Trend topic name - required"
            },
            "article_count": {
                "bsonType": "int",
                "description": "Number of related articles"
            },
            "first_seen": {
                "bsonType": "date",
                "description": "When trend was first detected - required"
            },
            "last_seen": {
                "bsonType": "date",
                "description": "When trend was last updated"
            },
            "keywords": {
                "bsonType": "array",
                "description": "Related keywords"
            },
            "related_articles": {
                "bsonType": "array",
                "description": "List of related article IDs"
            }
        }
    }
}

SESSIONS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["session_id", "started_at"],
        "properties": {
            "session_id": {
                "bsonType": "string",
                "description": "Unique session identifier - required"
            },
            "started_at": {
                "bsonType": "date",
                "description": "Session start time - required"
            },
            "ended_at": {
                "bsonType": "date",
                "description": "Session end time"
            },
            "status": {
                "bsonType": "string",
                "enum": ["running", "completed", "failed"],
                "description": "Session status"
            },
            "sources_scraped": {
                "bsonType": "array",
                "description": "List of sources scraped"
            },
            "articles_count": {
                "bsonType": "int",
                "description": "Total articles scraped"
            },
            "error_message": {
                "bsonType": "string",
                "description": "Error message if failed"
            }
        }
    }
}

UPLOAD_HISTORY_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["article_id", "uploaded_at"],
        "properties": {
            "article_id": {
                "bsonType": "objectId",
                "description": "Reference to article - required"
            },
            "uploaded_at": {
                "bsonType": "date",
                "description": "Upload timestamp - required"
            },
            "platform": {
                "bsonType": "string",
                "description": "Target platform (hocalwire, twitter, etc.)"
            },
            "status": {
                "bsonType": "string",
                "enum": ["success", "failed", "pending"],
                "description": "Upload status"
            },
            "response": {
                "bsonType": "object",
                "description": "API response data"
            },
            "error_message": {
                "bsonType": "string",
                "description": "Error message if failed"
            }
        }
    }
}


# ===========================================
# TEST DATA
# ===========================================

def get_test_articles():
    """Generate test articles for database seeding."""
    now = datetime.utcnow()
    
    return [
        {
            "heading": "Global Climate Summit Reaches Historic Agreement",
            "story": "World leaders at the Global Climate Summit have reached a historic agreement to reduce carbon emissions by 50% by 2030. The landmark deal involves commitments from over 190 countries and includes provisions for financial support to developing nations. Environmental groups have cautiously welcomed the agreement, while noting that implementation will be key to its success.",
            "source_url": "https://test.bbc.com/news/climate-summit-2026",
            "scraped_at": now - timedelta(hours=2),
            "session_id": "INIT_TEST_001",
            "location": "Global",
            "language": "en",
            "upload_status": "pending"
        },
        {
            "heading": "Tech Giants Announce AI Safety Partnership",
            "story": "Major technology companies including leading AI developers have announced a new partnership focused on AI safety and responsible development. The initiative will establish shared guidelines for AI development and include regular safety audits. Industry experts say this marks a significant step toward self-regulation in the AI sector.",
            "source_url": "https://test.reuters.com/tech/ai-safety-partnership",
            "scraped_at": now - timedelta(hours=4),
            "session_id": "INIT_TEST_001",
            "location": "United States",
            "language": "en",
            "upload_status": "pending"
        },
        {
            "heading": "India's Economy Shows Strong Growth in Q4",
            "story": "India's economy has recorded impressive growth of 7.2% in the fourth quarter, exceeding analyst expectations. The growth was driven by strong performance in the services sector and increased consumer spending. Government officials attribute the success to recent policy reforms and infrastructure investments.",
            "source_url": "https://test.thehindu.com/business/india-economy-q4",
            "scraped_at": now - timedelta(hours=6),
            "session_id": "INIT_TEST_001",
            "location": "India",
            "language": "en",
            "upload_status": "pending"
        },
        {
            "heading": "New Archaeological Discovery in Middle East",
            "story": "Archaeologists have uncovered a significant ancient site in the Middle East, dating back over 4,000 years. The discovery includes well-preserved artifacts and structures that provide new insights into early civilizations. Researchers say this find could reshape our understanding of ancient trade routes in the region.",
            "source_url": "https://test.aljazeera.com/archaeology-discovery",
            "scraped_at": now - timedelta(hours=8),
            "session_id": "INIT_TEST_001",
            "location": "Middle East",
            "language": "en",
            "upload_status": "pending"
        },
        {
            "heading": "European Union Announces New Digital Privacy Regulations",
            "story": "The European Union has unveiled comprehensive new digital privacy regulations that will affect how companies handle user data. The regulations include stricter consent requirements and significant penalties for non-compliance. Tech companies are already preparing to adapt their practices to meet the new standards, which take effect next year.",
            "source_url": "https://test.france24.com/eu-privacy-regulations",
            "scraped_at": now - timedelta(hours=10),
            "session_id": "INIT_TEST_001",
            "location": "Europe",
            "language": "en",
            "upload_status": "pending"
        }
    ]


def get_test_trends():
    """Generate test trends for database seeding."""
    now = datetime.utcnow()
    
    return [
        {
            "topic": "Climate Change Summit",
            "article_count": 15,
            "first_seen": now - timedelta(days=2),
            "last_seen": now,
            "keywords": ["climate", "summit", "emissions", "agreement", "environment"]
        },
        {
            "topic": "AI Safety",
            "article_count": 8,
            "first_seen": now - timedelta(days=1),
            "last_seen": now,
            "keywords": ["artificial intelligence", "safety", "regulation", "technology"]
        }
    ]


def get_test_session():
    """Generate test scraping session."""
    now = datetime.utcnow()
    
    return {
        "session_id": "INIT_TEST_001",
        "started_at": now - timedelta(hours=12),
        "ended_at": now - timedelta(hours=11),
        "status": "completed",
        "sources_scraped": ["BBC News", "Reuters", "The Hindu", "Al Jazeera", "France 24"],
        "articles_count": 5
    }


# ===========================================
# INITIALIZATION FUNCTIONS
# ===========================================

def create_collection_if_not_exists(database, name, schema=None):
    """Create a collection if it doesn't exist, optionally with validation."""
    existing_collections = database.list_collection_names()
    
    if name in existing_collections:
        print(f"  ℹ️  Collection '{name}' already exists")
        
        # Update validation schema if provided
        if schema:
            try:
                database.command("collMod", name, validator=schema)
                print(f"  ✅ Updated validation schema for '{name}'")
            except Exception as e:
                logger.debug(f"Could not update schema for {name}: {e}")
        
        return False
    
    # Create collection with validation
    if schema:
        database.create_collection(name, validator=schema)
    else:
        database.create_collection(name)
    
    print(f"  ✅ Created collection '{name}'")
    return True


def create_index_safe(collection, keys, **kwargs):
    """Create an index safely, handling conflicts with existing indexes."""
    try:
        collection.create_index(keys, **kwargs)
        return True
    except Exception as e:
        if "IndexKeySpecsConflict" in str(e) or "already exists" in str(e).lower():
            # Index exists with different options - drop and recreate
            try:
                # Get index name
                if isinstance(keys, str):
                    index_name = f"{keys}_1"
                elif isinstance(keys, list):
                    index_name = "_".join([f"{k}_{v}" for k, v in keys])
                else:
                    return False
                
                collection.drop_index(index_name)
                collection.create_index(keys, **kwargs)
                return True
            except Exception:
                # Just skip if we can't recreate
                return False
        return False


def create_indexes(database):
    """Create indexes for all collections."""
    print("\n📊 Creating indexes...")
    
    # Articles indexes
    articles = database["articles"]
    create_index_safe(articles, "session_id")
    create_index_safe(articles, [("scraped_at", -1)])  # Descending for recent first
    create_index_safe(articles, "upload_status")
    create_index_safe(articles, "location")
    create_index_safe(articles, "source_url", unique=True, sparse=True)
    print("  ✅ Articles indexes created")
    
    # Trends indexes
    trends = database["trends"]
    create_index_safe(trends, "topic", unique=True)
    create_index_safe(trends, [("first_seen", -1)])
    create_index_safe(trends, [("last_seen", -1)])
    create_index_safe(trends, [("article_count", -1)])
    print("  ✅ Trends indexes created")
    
    # Sessions indexes
    sessions = database["scraping_sessions"]
    create_index_safe(sessions, "session_id", unique=True)
    create_index_safe(sessions, [("started_at", -1)])
    create_index_safe(sessions, "status")
    print("  ✅ Sessions indexes created")
    
    # Upload history indexes
    upload_history = database["upload_history"]
    create_index_safe(upload_history, "article_id")
    create_index_safe(upload_history, [("uploaded_at", -1)])
    create_index_safe(upload_history, "platform")
    create_index_safe(upload_history, "status")
    print("  ✅ Upload history indexes created")


def insert_test_data(database):
    """Insert test data into collections."""
    print("\n📝 Inserting test data...")
    
    # Check if test data already exists
    articles = database["articles"]
    existing_test = articles.find_one({"session_id": "INIT_TEST_001"})
    
    if existing_test:
        print("  ℹ️  Test data already exists (session INIT_TEST_001)")
        return
    
    # Insert test articles
    test_articles = get_test_articles()
    result = articles.insert_many(test_articles)
    print(f"  ✅ Inserted {len(result.inserted_ids)} test articles")
    
    # Insert test trends
    trends = database["trends"]
    test_trends = get_test_trends()
    for trend in test_trends:
        trends.update_one(
            {"topic": trend["topic"]},
            {"$set": trend},
            upsert=True
        )
    print(f"  ✅ Inserted {len(test_trends)} test trends")
    
    # Insert test session
    sessions = database["scraping_sessions"]
    test_session = get_test_session()
    sessions.update_one(
        {"session_id": test_session["session_id"]},
        {"$set": test_session},
        upsert=True
    )
    print("  ✅ Inserted test scraping session")


def print_database_stats(database):
    """Print current database statistics."""
    print("\n📈 Database Statistics:")
    print(f"  • Articles: {database['articles'].count_documents({})}")
    print(f"  • Trends: {database['trends'].count_documents({})}")
    print(f"  • Sessions: {database['scraping_sessions'].count_documents({})}")
    print(f"  • Upload History: {database['upload_history'].count_documents({})}")


def initialize_database():
    """
    Initialize MongoDB with collections, indexes, and test data.
    
    This function is idempotent - safe to run multiple times.
    
    Returns:
        bool: True if initialization successful, False otherwise.
    """
    print("\n" + "="*60)
    print("🚀 OSI News Automation - Database Initialization")
    print("="*60)
    
    try:
        # Connect to MongoDB
        print("\n🔌 Connecting to MongoDB...")
        db_client = MongoDBClient()
        
        if not db_client.connect():
            print("❌ Failed to connect to MongoDB")
            print("   Make sure MongoDB is running and accessible.")
            return False
        
        print(f"  ✅ Connected to database: {db_client.database_name}")
        
        # Get database reference
        database = db_client.client[db_client.database_name]
        
        # Create collections with validation schemas
        print("\n📁 Creating collections...")
        create_collection_if_not_exists(database, "articles", ARTICLES_SCHEMA)
        create_collection_if_not_exists(database, "trends", TRENDS_SCHEMA)
        create_collection_if_not_exists(database, "scraping_sessions", SESSIONS_SCHEMA)
        create_collection_if_not_exists(database, "upload_history", UPLOAD_HISTORY_SCHEMA)
        
        # Create indexes
        create_indexes(database)
        
        # Insert test data
        insert_test_data(database)
        
        # Print statistics
        print_database_stats(database)
        
        # Disconnect
        db_client.disconnect()
        
        print("\n" + "="*60)
        print("✅ Database initialization completed successfully!")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"\n❌ Initialization failed: {e}")
        return False


def reset_database():
    """
    Reset database by dropping all collections.
    USE WITH CAUTION - This will delete all data!
    """
    print("\n⚠️  WARNING: This will delete ALL data in the database!")
    confirm = input("Type 'RESET' to confirm: ")
    
    if confirm != "RESET":
        print("Reset cancelled.")
        return False
    
    try:
        db_client = MongoDBClient()
        if not db_client.connect():
            print("❌ Failed to connect to MongoDB")
            return False
        
        database = db_client.client[db_client.database_name]
        
        # Drop all collections
        for collection in ["articles", "trends", "scraping_sessions", "upload_history"]:
            database.drop_collection(collection)
            print(f"  🗑️  Dropped collection: {collection}")
        
        db_client.disconnect()
        print("\n✅ Database reset complete. Run initialize_database() to recreate.")
        return True
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


# ===========================================
# MAIN ENTRY POINT
# ===========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize OSI News Automation Database")
    parser.add_argument("--reset", action="store_true", help="Reset database (WARNING: deletes all data)")
    args = parser.parse_args()
    
    if args.reset:
        success = reset_database()
    else:
        success = initialize_database()
    
    sys.exit(0 if success else 1)
