#
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'feedback.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

def print_table(cursor, rows):
    # Get column names
    col_names = [desc[0] for desc in cursor.description]
    # Calculate column widths
    widths = [len(name) for name in col_names]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    # Print header
    header = " | ".join(name.ljust(widths[i]) for i, name in enumerate(col_names))
    print(header)
    print("-+-".join('-' * w for w in widths))
    # Print rows
    for row in rows:
        print(" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)))

print("Scrie o comandă SQL (sau 'exit' pentru a ieși):")
while True:
    cmd = input("sqlite> ")
    if cmd.lower() in ("exit", "quit"):
        break
    if cmd.strip() == ".schema":
        try:
            for row in c.execute("SELECT sql FROM sqlite_master WHERE type='table'"):
                print(row[0])
        except Exception as e:
            print("Eroare:", e)
        continue
    try:
        c.execute(cmd)
        if c.description:  # Only if the command returns rows
            rows = c.fetchall()
            if rows:
                print_table(c, rows)
            else:
                print("(fără rezultate)")
        else:
            conn.commit()
    except Exception as e:
        print("Eroare:", e)

conn.close()