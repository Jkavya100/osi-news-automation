import sqlite3
import json

conn = sqlite3.connect('data/news_database.db')
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check generated_articles table
print("\n" + "="*60)
print("Latest Generated Articles:")
print("="*60)

cursor.execute("""
    SELECT id, heading, word_count, topic, generated_at 
    FROM generated_articles 
    ORDER BY id DESC 
    LIMIT 3
""")

articles = cursor.fetchall()
for art in articles:
    print(f"\nID: {art[0]}")
    print(f"Heading: {art[1]}")
    print(f"Word Count: {art[2]}")
    print(f"Topic: {art[3]}")
    print(f"Generated: {art[4]}")
    print("-" * 60)

# Get full article content for the latest one
if articles:
    cursor.execute("SELECT * FROM generated_articles WHERE id = ?", (articles[0][0],))
    full_article = cursor.fetchone()
    
    # Get column names
    column_names = [description[0] for description in cursor.description]
    
    print("\n" + "="*60)
    print("FULL LATEST ARTICLE DETAILS:")
    print("="*60)
    for i, col_name in enumerate(column_names):
        value = full_article[i]
        if col_name in ['story', 'heading']:
            print(f"\n{col_name}:")
            print(value if value else "N/A")
        else:
            print(f"{col_name}: {value}")

conn.close()
