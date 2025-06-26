import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'users.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    c.execute("PRAGMA table_info(user)")
    columns = [col[1] for col in c.fetchall()]

    if 'first_name' not in columns:
        c.execute("ALTER TABLE user ADD COLUMN first_name TEXT DEFAULT ''")
        print("Added first_name column.")
    if 'last_name' not in columns:
        c.execute("ALTER TABLE user ADD COLUMN last_name TEXT DEFAULT ''")
        print("Added last_name column.")
    if 'avatar' not in columns:
        c.execute("ALTER TABLE user ADD COLUMN avatar TEXT")
        print("Added avatar column.")

    conn.commit()
    print("Migration complete.")
except Exception as e:
    print("Migration error:", e)
finally:
    conn.close() 