import sqlite3
import os

def check_database():
    db_path = os.path.join('feedback', 'feedback.db')
    print(f"Checking database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("Error: Database file does not exist!")
        return
        
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    
    # Get list of all tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    
    print("\nFound tables:")
    for table in tables:
        table_name = table[0]
        print(f"\n=== {table_name} ===")
        
        # Get table schema
        c.execute(f"PRAGMA table_info({table_name});")
        columns = c.fetchall()
        
        print("Columns:")
        for col in columns:
            col_id, name, type_, notnull, default_value, pk = col
            print(f"  - {name} ({type_}){' PRIMARY KEY' if pk else ''}{' NOT NULL' if notnull else ''}{f' DEFAULT {default_value}' if default_value else ''}")
        
        # Get row count
        c.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = c.fetchone()[0]
        print(f"Total rows: {count}")
    
    conn.close()

if __name__ == "__main__":
    check_database() 