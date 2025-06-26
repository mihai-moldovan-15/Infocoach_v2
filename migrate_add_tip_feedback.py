import sqlite3
import os

db_path = os.path.join('feedback', 'feedback.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Verifică dacă există coloana tip_feedback
c.execute("PRAGMA table_info(feedback)")
columns = [col[1] for col in c.fetchall()]
if 'tip_feedback' not in columns:
    c.execute("ALTER TABLE feedback ADD COLUMN tip_feedback TEXT")
    print("Coloana tip_feedback a fost adăugată cu succes.")
else:
    print("Coloana tip_feedback există deja.")

conn.commit()
conn.close() 