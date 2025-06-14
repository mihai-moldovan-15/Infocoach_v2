import sqlite3
import os

db_path = 'problems.db'
print(f'Checking database at: {os.path.abspath(db_path)}')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('SELECT id, name, statement, input_description, output_description, difficulty FROM problems')
    rows = cursor.fetchall()
    if not rows:
        print('No problems found in the database.')
    else:
        for row in rows:
            print(f'ID: {row[0]}')
            print(f'Name: {row[1]}')
            print(f'Statement: {row[2]}')
            print(f'Input Description: {row[3]}')
            print(f'Output Description: {row[4]}')
            print(f'Difficulty: {row[5]}')
            print('-' * 40)
except Exception as e:
    print(f'Error querying the database: {e}')
finally:
    conn.close() 