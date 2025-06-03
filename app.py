from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import time
import re
import html
from models import db, User
from forms import LoginForm, RegistrationForm

# Load API key
load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' # Only keep the users database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = ''
login_manager.login_message_category = 'info'

# Initialize SQLAlchemy
db.init_app(app)

# Create database tables (only for users now)
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === Already created vector-stores (replace with actual IDs obtained at upload) ===
vector_stores = {
    "9": client.vector_stores.retrieve("vs_683acc055d98819186a2cd0fbf7c6ed4"),
    "10": client.vector_stores.retrieve("vs_68336c5facbc8191becf60fe5b02fa8e"),
    "11-12": client.vector_stores.retrieve("vs_68336c5f54748191bc3a4e9e632103a4")
}

# === AI instructions ===
with open(os.path.join(os.path.dirname(__file__), "instructions.txt"), encoding="utf-8") as f:
    base_instructions = f.read()

# === Create assistants at startup ===
assistants = {}
for clasa in vector_stores:
    assistants[clasa] = client.beta.assistants.create(
        instructions=base_instructions + f"\n\nElevul este în clasa a {clasa}-a. Ajustează explicațiile pentru acest nivel.",
        name=f"infocoach_clasa_{clasa}",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_stores[clasa].id]}},
        model="gpt-4o",
        temperature=0.3,
        top_p=0.8
    )

# === Initialize SQLite database (Feedback) ===
def init_db():
    os.makedirs('feedback', exist_ok=True)
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    
    # Feedback table
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            clasa TEXT,
            user_input TEXT,
            ai_response TEXT,
            feedback TEXT,
            feedback_text TEXT
        )
    ''')
    
    # Conversations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            clasa TEXT,
            start_time TEXT,
            is_active INTEGER DEFAULT 1,
            message_count INTEGER DEFAULT 0
        )
    ''')

    # Messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize feedback database
init_db()

# === Update: Add role and content to messages table if not present ===
def ensure_messages_schema():
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in c.fetchall()]
    if 'role' not in columns or 'content' not in columns:
        try:
            c.execute('ALTER TABLE messages ADD COLUMN role TEXT')
        except Exception:
            pass
        try:
            c.execute('ALTER TABLE messages ADD COLUMN content TEXT')
        except Exception:
            pass
        conn.commit()
    conn.close()

ensure_messages_schema()

# === Save user and assistant messages as separate rows ===
def save_message(conversation_id, user_input, ai_response):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # If conversation_id is None, create a new conversation
    if conversation_id is None:
        c.execute('''
            INSERT INTO conversations (user_id, clasa, start_time, is_active, message_count)
            VALUES (?, ?, ?, 1, 0)
        ''', (current_user.id, request.form.get('clasa', '9'), timestamp))
        conversation_id = c.lastrowid
    
    # Save user message
    c.execute('''
        INSERT INTO messages (conversation_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (conversation_id, 'user', user_input, timestamp))
    
    # Save assistant message
    c.execute('''
        INSERT INTO messages (conversation_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (conversation_id, 'assistant', ai_response, timestamp))
    
    # Increment message count
    c.execute('''
        UPDATE conversations 
        SET message_count = message_count + 1 
        WHERE id = ?
    ''', (conversation_id,))
    
    conn.commit()
    conn.close()
    return conversation_id

# === Get conversation history as a list of dicts with role/content ===
def get_conversation_history(conversation_id):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        SELECT role, content, timestamp
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC, id ASC
    ''', (conversation_id,))
    messages = [
        {'role': row[0], 'content': row[1], 'timestamp': row[2]}
        for row in c.fetchall()
    ]
    conn.close()
    return messages

# === Function for formatting C++ code blocks ===
def format_code_blocks(text):
    def replacer(match):
        code = html.escape(match.group(1))
        return f'<pre><code class="cpp">{code}</code></pre>'
    return re.sub(r'```cpp\s*([\s\S]*?)```', replacer, text)

# === Function for formatting steps, paragraphs, variables and bold ===
def format_steps_and_paragraphs(text):
    # Separate already formatted code blocks
    parts = re.split(r'(<pre><code class="cpp">[\s\S]*?<\/code><\/pre>)', text)
    formatted = []
    for part in parts:
        if part.startswith('<pre><code class="cpp">'):
            # Do not modify code blocks!
            formatted.append(part)
        else:
            # Apply regex ONLY on non-code text!
            lines = part.split('\n')
            in_list = False
            list_items = []
            new_lines = []
            for line in lines:
                # Treat H3 headers (Explicații:) specifically
                if line.strip().startswith('###'):
                    new_lines.append(line) # Leave header as is
                    continue # Skip to next line after header

                # Highlight bold text marked with **text**
                line = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", line)

                # Find and format ordered list items (if any)
                m = re.match(r'^\s*(\d+)\.\s+(.*)', line)
                if m:
                    # If not already in a list, start a new list
                    if not in_list:
                         in_list = True
                         if new_lines and not new_lines[-1].startswith('<p>') and not new_lines[-1].startswith('<ol>'):
                             pass

                    # Add current item to list
                    list_items.append(f"<li>{m.group(2).strip()}</li>")
                else:
                    # If we were in a list and current line is not a list item,
                    # end the list and add to new_lines
                    if in_list:
                        new_lines.append("<ol>" + "".join(list_items) + "</ol>")
                        list_items = []
                        in_list = False
                    
                    # Add non-list line as a paragraph, if not empty
                    if line.strip():
                        new_lines.append(f"<p>{line.strip()}</p>")

            # After loop, if ended with a list, add it
            if in_list:
                new_lines.append("<ol>" + "".join(list_items) + "</ol>")

            # Join processed lines for this part
            formatted.append('\n'.join(new_lines))
    
    # Join all parts (code and non-code) back together
    return ''.join(formatted)

# === Function for formatting words between backticks ===
def format_inline_code(text):
    # Check if text already contains formatted HTML
    if '<pre><code class="cpp">' in text:
        return text
        
    def replacer(match):
        code = html.escape(match.group(1))
        return f'<span style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace; color: #333;">{code}</span>'
    
    # Find all occurrences of text between backticks, including special characters
    pattern = r'`([^`]+?)`'
    
    # Split text into parts to avoid formatting in code blocks
    parts = re.split(r'(<pre><code class="cpp">[\s\S]*?<\/code><\/pre>)', text)
    formatted = []
    
    for part in parts:
        if part.startswith('<pre><code class="cpp">'):
            # Do not modify code blocks
            formatted.append(part)
        else:
            # Apply formatting for backticks in rest of text
            # Replace special characters temporarily to avoid conflicts
            temp_part = part.replace('#', '___HASH___')
            temp_part = re.sub(pattern, replacer, temp_part)
            # Restore special characters
            temp_part = temp_part.replace('___HASH___', '#')
            formatted.append(temp_part)
    
    return ''.join(formatted)

# === Route for login ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Autentificare reușită!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Nume de utilizator sau parolă incorectă', 'danger')
    return render_template('login.html', form=form)

# === Route for register ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Înregistrare reușită! Te rugăm să te autentifici.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# === Route for logout ===
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ai fost deconectat cu succes.', 'info')
    return redirect(url_for('index'))

# === Helper: Get all conversations for a user ===
def get_user_conversations(user_id):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        SELECT id, clasa, start_time, is_active, message_count
        FROM conversations
        WHERE user_id = ?
        ORDER BY start_time DESC
    ''', (user_id,))
    conversations = c.fetchall()
    conn.close()
    return conversations

# === Helper: Get or create a new conversation for a user and class ===
def get_or_create_conversation(user_id, clasa):
    # Return None to indicate no conversation exists yet
    return None

# === Route for creating a new conversation ===
@app.route('/new_conversation')
@login_required
def new_conversation():
    clasa = request.args.get('clasa', '9')
    conversation_id = get_or_create_conversation(current_user.id, clasa)
    return redirect(url_for('index', conversation_id=conversation_id))

# === Main route ===
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_input = ''
    output = ''
    clasa = '9'
    chat_history = []

    # Get all conversations for sidebar
    conversations = get_user_conversations(current_user.id)

    # Determine selected conversation
    conversation_id = request.args.get('conversation_id')
    if conversation_id:
        conversation_id = int(conversation_id)
        chat_history = get_conversation_history(conversation_id)
    else:
        conversation_id = None
        chat_history = []

    if chat_history:
        for msg in chat_history:
            if msg['role'] == 'assistant':
                formatted = format_code_blocks(msg['content'])
                formatted = format_steps_and_paragraphs(formatted)
                msg['content'] = formatted

    if request.method == 'POST':
        user_input = request.form.get('user_input', '')
        clasa = request.form.get('clasa', '9')
        # Use conversation_id from form if present
        form_conversation_id = request.form.get('conversation_id')
        if form_conversation_id:
            conversation_id = int(form_conversation_id)

        # Do not escape HTML for user input
        prompt_content = (
            f"{user_input}\n"
            "Te rog să folosești cât mai mult informațiile din resursele disponibile."
        )

        assistant = assistants[clasa]

        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt_content)

        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

        while run.status not in ["completed", "failed"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread.id)

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for m in reversed(messages.data):
                if m.role == "assistant":
                    output = m.content[0].text.value
                    
                    # Filter out references like 【4:0†source】
                    output = re.sub(r'[【\[]\d+:\d+†[^\]】]+[】\]]', '', output)
                    
                    # Format the output for HTML display
                    formatted_output = format_code_blocks(output)
                    formatted_output = format_steps_and_paragraphs(formatted_output)

                    # Save message to database and get the conversation_id
                    conversation_id = save_message(conversation_id, user_input, output)

                    # Get updated chat history
                    chat_history = get_conversation_history(conversation_id)

                    # Render the assistant message fragment and return it
                    return render_template('assistant_message.html', 
                                        output=formatted_output,
                                        user_input=user_input, 
                                        clasa=clasa,
                                        conversation_id=conversation_id)

        # If the run failed or no assistant message was found
        return "A apărut o problemă la generarea răspunsului asistentului.", 500

    # For GET requests, render the full index page with initial (or last) data
    return render_template('index.html', 
                         user_input=user_input, 
                         output=output, 
                         clasa=clasa,
                         chat_history=chat_history,
                         conversations=conversations,
                         selected_conversation_id=conversation_id)

# === Route for chat API ===
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    user_input = request.form.get('user_input', '')
    clasa = request.form.get('clasa', '9')
    conversation_id = request.form.get('conversation_id')
    if conversation_id:
        conversation_id = int(conversation_id)

    if not user_input:
        return jsonify({'error': 'Lipsește input-ul utilizatorului'}), 400

    # Do not escape HTML for user input
    prompt_content = (
        f"{user_input}\n"
        "Te rog să folosești cât mai mult informațiile din resursele disponibile."
    )

    assistant = assistants[clasa]

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt_content)

    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

    while run.status not in ["completed", "failed"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread.id)

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for m in reversed(messages.data):
            if m.role == "assistant":
                output = m.content[0].text.value
                
                # Filter out references like 【4:0†source】
                output = re.sub(r'[【\[]\d+:\d+†[^\]】]+[】\]]', '', output)
                
                # Format the output for HTML display
                formatted_output = format_code_blocks(output)
                formatted_output = format_steps_and_paragraphs(formatted_output)

                # Save message to database and get the conversation_id
                conversation_id = save_message(conversation_id, user_input, output)

                return jsonify({
                    'success': True,
                    'response': formatted_output,
                    'conversation_id': conversation_id
                })

    return jsonify({'error': 'A apărut o problemă la generarea răspunsului asistentului.'}), 500

# === Route for saving feedback ===
@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    try:
        # Get data based on content type
        if request.content_type == 'application/x-www-form-urlencoded':
            data = request.form
        else:
            data = request.get_json() or request.form

        # Get and validate required fields
        user_input = data.get('user_input', '').strip()
        ai_response = data.get('ai_response', '').strip()
        clasa = data.get('clasa', '').strip()
        fb = data.get('feedback', '').strip()
        feedback_text = data.get('feedback_text', '').strip()        
        app.logger.info(f"Received feedback request - Clasa: {clasa}, Feedback: {fb}, Text: {feedback_text}")
        
        # Validate inputs
        if not user_input:
            app.logger.warning("Missing user input")
            return jsonify({'error': 'Lipsește input-ul utilizatorului'}), 400
        if not ai_response:
            app.logger.warning("Missing AI response")
            return jsonify({'error': 'Lipsește răspunsul asistentului'}), 400
        if not fb:
            app.logger.warning("Missing feedback")
            return jsonify({'error': 'Lipsește feedback-ul'}), 400
            
        # Sanitize inputs
        user_input = html.escape(user_input)
        # Nu mai escapăm HTML pentru răspunsul AI, îl salvăm așa cum este
        clasa = html.escape(clasa)
        fb = html.escape(fb)
        feedback_text = html.escape(feedback_text)
        
        # Ensure feedback directory exists
        feedback_dir = os.path.join(os.path.dirname(__file__), 'feedback')
        os.makedirs(feedback_dir, exist_ok=True)
        app.logger.info(f"Feedback directory: {feedback_dir}")
        
        # Database path
        db_path = os.path.join(feedback_dir, 'feedback.db')
        app.logger.info(f"Database path: {db_path}")
        
        # Save to database
        conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
        c = conn.cursor()
        
        try:
            # Check if feedback_text column exists
            c.execute("PRAGMA table_info(feedback)")
            columns = [column[1] for column in c.fetchall()]
            app.logger.info(f"Existing columns: {columns}")
            
            # If column doesn't exist, add it
            if 'feedback_text' not in columns:
                app.logger.info("Adding feedback_text column")
                c.execute('ALTER TABLE feedback ADD COLUMN feedback_text TEXT')
                conn.commit()
                app.logger.info("Added feedback_text column to feedback table")
        except sqlite3.OperationalError as e:
            # If table doesn't exist, create it with all columns
            app.logger.info("Creating feedback table")
            c.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    clasa TEXT,
                    user_input TEXT,
                    ai_response TEXT,
                    feedback TEXT,
                    feedback_text TEXT
                )
            ''')
            conn.commit()
            app.logger.info("Created feedback table with all columns")
        
        # Insert feedback
        app.logger.info("Inserting feedback")
        c.execute('''
            INSERT INTO feedback (timestamp, clasa, user_input, ai_response, feedback, feedback_text)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), clasa, user_input, ai_response, fb, feedback_text))
        
        conn.commit()
        conn.close()
        
        app.logger.info("Feedback saved successfully")
        return jsonify({'message': 'Feedback salvat cu succes!'})
        
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': f'Eroare la salvarea în baza de date: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'A apărut o eroare neașteptată: {str(e)}'}), 500

# === Route for viewing feedback ===
@app.route('/view-feedback')
@login_required
def view_feedback():
    # Get filtering parameters from query string
    clasa_filter = request.args.get('clasa', '')
    feedback_filter = request.args.get('feedback', '')
    
    # Connect to database
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    
    # Build SQL query with filters
    query = 'SELECT * FROM feedback WHERE 1=1'
    params = []
    
    if clasa_filter:
        query += ' AND clasa = ?'
        params.append(clasa_filter)
    
    if feedback_filter:
        query += ' AND feedback = ?'
        params.append(feedback_filter)
    
    query += ' ORDER BY timestamp DESC'
    
    # Execute query with parameters
    c.execute(query, params)
    feedback_entries = c.fetchall()
    
    # Close connection
    conn.close()
    
    # Convert results to format easily used in template
    entries = []
    for entry in feedback_entries:
        # Check if response already contains HTML
        if '<pre><code class="cpp">' in entry[4]:
            # If it already contains HTML, use it directly
            formatted_response = entry[4]
        else:
            # If it doesn't contain HTML, apply formatting
            formatted_response = format_code_blocks(entry[4])
            formatted_response = format_steps_and_paragraphs(formatted_response)
            # Apply formatting for words between backticks
            formatted_response = format_inline_code(formatted_response)
        
        entries.append({
            'timestamp': entry[1],
            'clasa': entry[2],
            'user_input': entry[3],
            'ai_response': formatted_response,
            'feedback': entry[5],
            'feedback_text': entry[6] if len(entry) > 6 else ''
        })
    
    return render_template('view_feedback.html', 
                         feedback_entries=entries,
                         current_clasa=clasa_filter,
                         current_feedback=feedback_filter)

# === Route for profile ===
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_clasa = request.form.get('clasa')
        if new_clasa in ['9', '10', '11-12']:
            current_user.clasa = new_clasa
            db.session.commit()
            flash('Clasa a fost actualizată cu succes!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')

# === Route for changing password ===
@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Parola actuală este incorectă.', 'danger')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('Parolele noi nu coincid.', 'danger')
        return redirect(url_for('profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    flash('Parola a fost schimbată cu succes!', 'success')
    return redirect(url_for('profile'))

# === Route for deleting a conversation ===
@app.route('/delete_conversation/<int:conversation_id>', methods=['POST'])
@login_required
def delete_conversation(conversation_id):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    # Ensure the conversation belongs to the current user
    c.execute('SELECT user_id FROM conversations WHERE id = ?', (conversation_id,))
    row = c.fetchone()
    if not row or row[0] != current_user.id:
        conn.close()
        return 'Forbidden', 403
    # Delete messages
    c.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
    # Delete conversation
    c.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# === Start application ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)