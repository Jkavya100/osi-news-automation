import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from src.database.mongo_client import get_client

db = get_client()
db.connect()

total = db.articles.count_documents({})
print(f"Total articles in DB: {total}")

# Count by status
all_statuses = {}
for art in db.articles.find({}, {'upload_status': 1}):
    s = art.get('upload_status', 'unknown')
    all_statuses[s] = all_statuses.get(s, 0) + 1

print("Status breakdown:")
for s, c in all_statuses.items():
    print(f"  {s}: {c}")

# Show recent articles regardless of status
print("\nLast 5 articles (any status):")
for a in db.articles.find({}, {'heading': 1, 'upload_status': 1, 'hocalwire_feed_id': 1}).sort('_id', -1).limit(5):
    heading = str(a.get('heading', ''))[:60]
    status = a.get('upload_status', 'N/A')
    feed_id = a.get('hocalwire_feed_id', 'N/A')
    print(f"  [{status}] {heading}")
    print(f"           Feed ID: {feed_id}")
