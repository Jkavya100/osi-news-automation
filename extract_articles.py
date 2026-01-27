from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['osi_news_automation']

# Get articles collection
articles_col = db['articles']

# Find articles that were generated today with our enhanced system
# These should have story type detection and better formatting
today = datetime.now().strftime('%Y-%m-%d')

# Get the 3 most recent articles
articles = list(articles_col.find().sort('_id', -1).limit(3))

print(f"Found {len(articles)} articles\n")

# Save each article to a separate markdown file
for i, article in enumerate(articles, 1):
    filename = f"enhanced_article_{i}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {article.get('heading', 'Untitled')}\n\n")
        
        # Check if this article was generated with the enhanced prompt
        # (it would have better structure)
        story = article.get('story', '')
        
        # Write the story
        f.write(story)
        
        # Add metadata
        f.write(f"\n\n---\n\n")
        f.write(f"## Article Metadata\n\n")
        f.write(f"- **ID:** {article.get('_id')}\n")
        f.write(f"- **Location:** {article.get('location', 'N/A')}\n")
        f.write(f"- **Language:** {article.get('language', 'N/A')}\n")
        f.write(f"- **Generated:** {article.get('scraped_at', 'N/A')}\n")
        
        if 'translations' in article and article['translations']:
            f.write(f"- **Translations:** {', '.join(article['translations'].keys())}\n")
    
    print(f"✅ Saved: {filename}")
    print(f"   Heading: {article.get('heading', 'N/A')[:60]}...")
    print(f"   Length: {len(str(article.get('story', '')))} characters\n")

client.close()
print("Done! Check the enhanced_article_*.md files.")
