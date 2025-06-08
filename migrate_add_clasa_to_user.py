import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'users.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    # Check if 'clasa' column exists
    c.execute("PRAGMA table_info(user)")
    columns = [col[1] for col in c.fetchall()]
    if 'clasa' not in columns:
        print("Adding 'clasa' column to user table...")
        c.execute('ALTER TABLE user ADD COLUMN clasa TEXT')
        conn.commit()
        print("Column added.")
        # Set all NULL clasa to '9'
        c.execute("UPDATE user SET clasa = '9' WHERE clasa IS NULL")
        conn.commit()
        print("Set all NULL clasa to '9'.")
    else:
        print("'clasa' column already exists.")
except Exception as e:
    print(f"Error during migration: {e}")
finally:
    conn.close()
    print("Done.") 