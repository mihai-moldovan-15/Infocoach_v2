import sqlite3
import os

def migrate_messages():
    db_path = os.path.join('feedback', 'feedback.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()

    # Check if migration is needed
    c.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in c.fetchall()]
    if 'user_input' not in columns or 'ai_response' not in columns:
        print("No old messages to migrate.")
        conn.close()
        return

    # Fetch all old messages
    c.execute("SELECT id, conversation_id, user_input, ai_response, timestamp FROM messages WHERE (user_input IS NOT NULL AND user_input != '') OR (ai_response IS NOT NULL AND ai_response != '')")
    old_msgs = c.fetchall()
    print(f"Found {len(old_msgs)} old messages to migrate.")

    migrated = 0
    for msg in old_msgs:
        msg_id, conversation_id, user_input, ai_response, timestamp = msg
        if user_input:
            c.execute('''INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)''', (conversation_id, 'user', user_input, timestamp))
            migrated += 1
        if ai_response:
            c.execute('''INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)''', (conversation_id, 'assistant', ai_response, timestamp))
            migrated += 1
    conn.commit()
    print(f"Migrated {migrated} new messages.")
    conn.close()

if __name__ == "__main__":
    migrate_messages() 