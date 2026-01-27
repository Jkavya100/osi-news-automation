from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['osi_news_automation']

# Get articles collection
articles_col = db['articles']

# Count total articles
total = articles_col.count_documents({})
print(f"\n{'='*80}")
print(f"TOTAL ARTICLES IN DATABASE: {total}")
print(f"{'='*80}\n")

# Get latest 3 articles
latest_articles = list(articles_col.find().sort('_id', -1).limit(3))

for i, article in enumerate(latest_articles, 1):
    print(f"\n{'='*80}")
    print(f"ARTICLE #{i}")
    print(f"{'='*80}")
    
    # Print all fields
    for key, value in article.items():
        if key == '_id':
            print(f"ID: {value}")
        elif key == 'story':
            # Truncate story
            story_preview = str(value)[:1000] + "..." if len(str(value)) > 1000 else str(value)
            print(f"\nSTORY:\n{'-'*80}\n{story_preview}\n{'-'*80}")
        elif key == 'translations':
            languages = list(value.keys()) if isinstance(value, dict) else []
            print(f"Translations: {', '.join(languages)}")
        elif isinstance(value, (list, tuple)):
            print(f"{key}: {', '.join(map(str, value)) if value else 'N/A'}")
        else:
            print(f"{key}: {value}")

client.close()
print(f"\n{'='*80}")
print("DONE!")
print(f"{'='*80}\n")
