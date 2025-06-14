import sqlite3

conn = sqlite3.connect('problems.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE problems ADD COLUMN example_input_name TEXT;")
except Exception as e:
    print("Coloana example_input_name există deja sau altă eroare:", e)

try:
    c.execute("ALTER TABLE problems ADD COLUMN example_output_name TEXT;")
except Exception as e:
    print("Coloana example_output_name există deja sau altă eroare:", e)

try:
    c.execute("ALTER TABLE problems ADD COLUMN subcategories TEXT;")
except Exception as e:
    print("Coloana subcategories există deja sau altă eroare:", e)

try:
    c.execute("ALTER TABLE problems ADD COLUMN time_limit TEXT;")
except Exception as e:
    print("Coloana time_limit există deja sau altă eroare:", e)

try:
    c.execute("ALTER TABLE problems ADD COLUMN memory_limit TEXT;")
except Exception as e:
    print("Coloana memory_limit există deja sau altă eroare:", e)

try:
    c.execute("ALTER TABLE problems ADD COLUMN author TEXT;")
except Exception as e:
    print("Coloana author există deja sau altă eroare:", e)

try:
    c.execute("ALTER TABLE problems ADD COLUMN source TEXT;")
except Exception as e:
    print("Coloana source există deja sau altă eroare:", e)

conn.commit()
conn.close()
print("Migrare finalizată.") 