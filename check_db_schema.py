import sqlite3

conn = sqlite3.connect('data/news_database.db')
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    
    # Get schema
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print("    Columns:")
    for col in columns:
        print(f"      {col[1]} ({col[2]})")
    
    # Get count
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"    Row count: {count}")
    print()

conn.close()
