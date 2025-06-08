import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'users.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('Tables in users.db:')
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in c.fetchall()]
for table in tables:
    print(f'\n=== {table} ===')
    c.execute(f'PRAGMA table_info({table})')
    columns = c.fetchall()
    for col in columns:
        print(f'  - {col[1]} ({col[2]})')

conn.close() 