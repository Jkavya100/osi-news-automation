from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['osi_news_automation']

# Check for articles in the generated_articles or synthesized_articles collection
print("Available collections:")
for collection_name in db.list_collection_names():
    count = db[collection_name].count_documents({})
    print(f"  - {collection_name}: {count} documents")

# Try different collection names
for coll_name in ['generated_articles', 'synthesized_articles', 'articles']:
    if coll_name in db.list_collection_names():
        coll = db[coll_name]
        print(f"\n{'='*80}")
        print(f"Collection: {coll_name}")
        print(f"{'='*80}")
        
        # Get recent articles
        recent = list(coll.find().sort([('$natural', -1)]).limit(5))
        
        for art in recent:
            print(f"\nID: {art.get('_id')}")
            print(f"Heading: {art.get('heading', art.get('title', 'N/A'))}")
            
            # Check for story type (new feature from enhanced prompt)
            if 'story_type' in art:
                print(f"Story Type (Enhanced): {art['story_type']}")
            
            # Check for enhanced metadata
            if 'model_used' in art:
                print(f"Model: {art['model_used']}")
            if 'word_count'in art:
                print(f"Word Count: {art['word_count']}")
            
            # Show timestamp fields
            for time_field in ['generated_at', 'created_at', 'timestamp', 'scraped_at']:
                if time_field in art:
                    print(f"{time_field}: {art[time_field]}")
                    break

client.close()
