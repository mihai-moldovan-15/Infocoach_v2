from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
import time
import re
import html
from models import db, User
from forms import LoginForm, RegistrationForm, ProfileForm
import tempfile
import shutil
import subprocess
import json
import glob
import openai
import hashlib
from datetime import timedelta
import logging
from functools import wraps

# Încarcă variabilele de mediu din .env
load_dotenv()

# Load API key
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
    "10": client.vector_stores.retrieve("vs_6851c43ad020819182dce3fa43d42afe"),
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
            feedback_text TEXT,
            tip_feedback TEXT
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
            message_count INTEGER DEFAULT 0,
            context_window_size INTEGER DEFAULT 10,
            total_tokens INTEGER DEFAULT 0,
            last_context_update TEXT,
            title TEXT
        )
    ''')

    # Messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            token_count INTEGER DEFAULT 0,
            in_context INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize feedback database
init_db()

# === Update: Add new fields to tables if not present ===
def ensure_schema_updates():
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    
    # Check and add new columns to conversations table
    c.execute("PRAGMA table_info(conversations)")
    conv_columns = [col[1] for col in c.fetchall()]
    
    new_conv_columns = {
        'context_window_size': 'INTEGER DEFAULT 10',
        'total_tokens': 'INTEGER DEFAULT 0',
        'last_context_update': 'TEXT'
    }
    
    for col_name, col_type in new_conv_columns.items():
        if col_name not in conv_columns:
            try:
                c.execute(f'ALTER TABLE conversations ADD COLUMN {col_name} {col_type}')
            except Exception as e:
                print(f"Error adding {col_name} to conversations: {e}")
    
    # Check and add new columns to messages table
    c.execute("PRAGMA table_info(messages)")
    msg_columns = [col[1] for col in c.fetchall()]
    
    new_msg_columns = {
        'token_count': 'INTEGER DEFAULT 0',
        'in_context': 'INTEGER DEFAULT 1'
    }
    
    for col_name, col_type in new_msg_columns.items():
        if col_name not in msg_columns:
            try:
                c.execute(f'ALTER TABLE messages ADD COLUMN {col_name} {col_type}')
            except Exception as e:
                print(f"Error adding {col_name} to messages: {e}")
    
    conn.commit()
    conn.close()

# Run schema updates
ensure_schema_updates()

# === Premium system schema updates ===
def ensure_premium_schema():
    """Ensure premium fields exist in User table"""
    with app.app_context():
        # Check if premium columns exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        # Add premium columns if they don't exist
        with db.engine.connect() as conn:
            if 'is_premium' not in columns:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN is_premium BOOLEAN DEFAULT FALSE'))
            if 'premium_until' not in columns:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN premium_until DATETIME'))
            if 'premium_granted_by' not in columns:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN premium_granted_by INTEGER'))
            if 'premium_granted_at' not in columns:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN premium_granted_at DATETIME'))
            if 'premium_reason' not in columns:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN premium_reason VARCHAR(200)'))
            if 'has_used_trial' not in columns:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN has_used_trial BOOLEAN DEFAULT FALSE'))
            conn.commit()

# Run premium schema updates
ensure_premium_schema()

# === Premium helper functions ===
def is_user_premium(user_id):
    """Check if user has active premium subscription"""
    user = User.query.get(user_id)
    if not user:
        return False
    return user.is_premium_active()

def require_premium(f):
    """Decorator to require premium subscription"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        if not current_user.is_premium_active():
            return jsonify({'error': 'Premium subscription required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# === Helper functions for context management ===
def estimate_tokens(text):
    """Estimate the number of tokens in a text string."""
    # Rough estimation: 1 token ≈ 4 characters for English/Romanian text
    return len(text) // 4

def update_context_window(conversation_id):
    """Update the context window for a conversation."""
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    
    # Get conversation's context window size
    c.execute('SELECT context_window_size FROM conversations WHERE id = ?', (conversation_id,))
    window_size = c.fetchone()[0]
    
    # Get all messages for this conversation
    c.execute('''
        SELECT id, role, content, token_count
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp DESC, id DESC
    ''', (conversation_id,))
    messages = c.fetchall()
    
    # Calculate total tokens and update context
    total_tokens = 0
    messages_in_context = []
    
    for msg_id, role, content, token_count in messages:
        if not token_count:
            token_count = estimate_tokens(content)
            c.execute('UPDATE messages SET token_count = ? WHERE id = ?', (token_count, msg_id))
        
        if len(messages_in_context) < window_size:
            messages_in_context.append(msg_id)
            total_tokens += token_count
            c.execute('UPDATE messages SET in_context = 1 WHERE id = ?', (msg_id,))
        else:
            c.execute('UPDATE messages SET in_context = 0 WHERE id = ?', (msg_id,))
    
    # Update conversation's total tokens and last context update
    c.execute('''
        UPDATE conversations 
        SET total_tokens = ?, last_context_update = ?
        WHERE id = ?
    ''', (total_tokens, datetime.now().isoformat(), conversation_id))
    
    conn.commit()
    conn.close()
    return total_tokens

def get_context_messages(conversation_id):
    """Get messages that are currently in the context window."""
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''
        SELECT role, content, timestamp
        FROM messages
        WHERE conversation_id = ? AND in_context = 1
        ORDER BY timestamp ASC, id ASC
    ''', (conversation_id,))
    
    messages = [
        {'role': row[0], 'content': row[1], 'timestamp': row[2]}
        for row in c.fetchall()
    ]
    
    conn.close()
    return messages

# === Update save_message function to handle context ===
def save_message(conversation_id, user_input, ai_response):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # If conversation_id is None, create a new conversation
    if conversation_id is None:
        c.execute('''
            INSERT INTO conversations (user_id, clasa, start_time, is_active, message_count, context_window_size)
            VALUES (?, ?, ?, 1, 0, 10)
        ''', (current_user.id, request.form.get('clasa', '9'), timestamp))
        conversation_id = c.lastrowid
    
    # Calculate token counts
    user_tokens = estimate_tokens(user_input)
    ai_tokens = estimate_tokens(ai_response)
    
    # Save user message
    c.execute('''
        INSERT INTO messages (conversation_id, role, content, timestamp, token_count, in_context)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (conversation_id, 'user', user_input, timestamp, user_tokens))
    
    # Save assistant message
    c.execute('''
        INSERT INTO messages (conversation_id, role, content, timestamp, token_count, in_context)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (conversation_id, 'assistant', ai_response, timestamp, ai_tokens))
    
    # Increment message count
    c.execute('''
        UPDATE conversations 
        SET message_count = message_count + 1 
        WHERE id = ?
    ''', (conversation_id,))
    
    conn.commit()
    conn.close()
    
    # Update context window
    update_context_window(conversation_id)
    
    return conversation_id

# === Update get_conversation_history to use context window ===
def get_conversation_history(conversation_id):
    """Get conversation history, respecting the context window."""
    return get_context_messages(conversation_id)

# === Function for formatting C++ code blocks ===
def format_code_blocks(text):
    def replacer(match):
        code = match.group(1)  # Don't escape HTML, preserve formatting
        return f'<pre><code class="cpp">{code}</code></pre>'
    return re.sub(r'```cpp\s*([\s\S]*?)```', replacer, text)

# === Function for formatting steps, paragraphs, variables and bold ===
def format_steps_and_paragraphs(text):
    parts = re.split(r'(<pre><code class="cpp">[\s\S]*?<\/code><\/pre>)', text)
    formatted = []
    for part in parts:
        if part.startswith('<pre><code class="cpp">'):
            formatted.append(part)
        else:
            lines = part.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                # Bullet point indicator
                if re.match(r'^\s*-+\s*$', line):
                    # Check for bold title and explanation
                    if i + 2 < len(lines):
                        title_line = lines[i+1].strip()
                        explanation_line = lines[i+2].strip()
                        bold_match = re.match(r'^\*\*([^\*]+)\*\*$', title_line)
                        if bold_match and explanation_line.startswith(':'):
                            title_html = f"<strong>{bold_match.group(1)}</strong>"
                            explanation_html = explanation_line[1:].strip()
                            new_lines.append(f'<ul><li>{title_html}: {explanation_html}</li></ul>')
                            i += 3
                            continue
                    # Fallback: collect all lines until next dash/empty
                    bullet_content = []
                    i += 1
                    while i < len(lines):
                        next_line = lines[i]
                        if not next_line.strip() or re.match(r'^\s*-+\s*$', next_line):
                            break
                        bullet_content.append(next_line.strip())
                        i += 1
                    if bullet_content:
                        new_lines.append('<ul><li>' + ' '.join(bullet_content) + '</li></ul>')
                    else:
                        pass
                    i += 1
                    continue
                if not line.strip():
                    i += 1
                    continue
                
                # Handle ### headers - make text bold until newline
                if line.strip().startswith('###'):
                    # Extract text after ### and make it bold
                    header_text = line.strip()[3:].strip()  # Remove ### and whitespace
                    if header_text:
                        new_lines.append(f"<p><strong>{header_text}</strong></p>")
                    else:
                        new_lines.append(f"<p>{line.strip()}</p>")
                else:
                    line = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", line)
                    m = re.match(r'^\s*(\d+)\.\s+(.*)', line)
                    if m:
                        item_text = m.group(2).strip()
                        new_lines.append(f"<ul><li>{item_text}</li></ul>")
                    else:
                        new_lines.append(f"<p>{line.strip()}</p>")
                i += 1
            formatted.append('\n'.join(new_lines))
    result = ''.join(formatted)
    return result

# === Function for formatting words between backticks ===
def format_inline_code(text):
    def replacer(match):
        code = html.escape(match.group(1))
        return f'<span style="background-color: var(--bg-tertiary); padding: 2px 4px; border-radius: 3px; font-family: monospace; color: var(--accent-primary);">{code}</span>'
    pattern = r'`([^`]+?)`'
    parts = re.split(r'(<pre><code class="cpp">[\s\S]*?<\/code><\/pre>)', text)
    formatted = []
    for part in parts:
        if part.startswith('<pre><code class="cpp">'):
            formatted.append(part)
        else:
            temp_part = part.replace('#', '___HASH___')
            temp_part = re.sub(pattern, replacer, temp_part)
            temp_part = temp_part.replace('___HASH___', '#')
            formatted.append(temp_part)
    return ''.join(formatted)

# === Route for login ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('problem_solver'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            user.last_login = datetime.now()
            db.session.commit()
            flash('Autentificare reușită!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('problem_solver'))
        flash('Nume de utilizator sau parolă incorectă', 'danger')
    return render_template('login.html', form=form)

# === Route for register ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Get selected plan
        selected_plan = request.form.get('plan', 'free')
        
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        # Set premium if selected
        if selected_plan == 'premium':
            user.is_premium = True
            user.premium_until = datetime.now() + timedelta(days=30)  # 30 days trial
            user.premium_granted_at = datetime.now()
            user.premium_reason = "registration_premium"
            user.has_used_trial = True  # Mark trial as used
        
        db.session.add(user)
        db.session.commit()
        
        if selected_plan == 'premium':
            # Redirect to payment page for premium users
            return redirect(url_for('payment'))
        else:
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
    clasa = current_user.clasa or '9'
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
                formatted = format_inline_code(formatted)
                msg['content'] = formatted

    if request.method == 'POST':
        user_input = request.form.get('user_input', '')
        clasa = request.form.get('clasa', current_user.clasa or '9')
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
                    formatted_output = format_inline_code(formatted_output)

                    # Save message to database and get the conversation_id
                    conversation_id = save_message(conversation_id, user_input, output)

                    # Get updated chat history
                    chat_history = get_conversation_history(conversation_id)

                    # Render the assistant message fragment and return it
                    return render_template('assistant_message.html', 
                                        output=formatted_output,
                                        ai_response_original=output,
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
    clasa = request.form.get('clasa', current_user.clasa or '9')
    conversation_id = request.form.get('conversation_id')
    if conversation_id:
        conversation_id = int(conversation_id)

    if not user_input:
        return jsonify({'error': 'Lipsește input-ul utilizatorului'}), 400

    # Get context messages if in a conversation
    context_messages = []
    if conversation_id:
        context_messages = get_context_messages(conversation_id)
    
    # Prepare the prompt with context
    prompt_content = user_input
    if context_messages:
        # Add context from previous messages
        context_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in context_messages[-5:]
        ])
        prompt_content = f"Previous conversation:\n{context_text}\n\nCurrent question: {user_input}"

    # Explicit instruction to use file_search
    prompt_content += "\n\nDacă găsești informații relevante în sursele din vector store, folosește-le. Dacă nu, poți răspunde și din cunoștințele tale generale, dar niciodata nu inventa informatii"

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
                formatted_output = format_inline_code(formatted_output)

                # Save message to database and get the conversation_id
                conversation_id = save_message(conversation_id, user_input, output)

                return jsonify({
                    'success': True,
                    'response': formatted_output,
                    'response_original': output,
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
        tip_feedback = data.get('tip_feedback', '').strip()
        app.logger.info(f"Received feedback request - Clasa: {clasa}, Feedback: {fb}, Text: {feedback_text}, Tip: {tip_feedback}")
        
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
        if not tip_feedback:
            app.logger.warning("Missing tip_feedback")
            return jsonify({'error': 'Lipsește tip_feedback-ul'}), 400
            
        # Sanitize inputs
        user_input = html.escape(user_input)
        # Nu mai escapăm HTML pentru răspunsul AI, îl salvăm așa cum este
        clasa = html.escape(clasa)
        fb = html.escape(fb)
        feedback_text = html.escape(feedback_text)
        tip_feedback = html.escape(tip_feedback)
        
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
                    feedback_text TEXT,
                    tip_feedback TEXT
                )
            ''')
            conn.commit()
            app.logger.info("Created feedback table with all columns")
        
        # Insert feedback
        app.logger.info("Inserting feedback")
        c.execute('''
            INSERT INTO feedback (timestamp, clasa, user_input, ai_response, feedback, feedback_text, tip_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), clasa, user_input, ai_response, fb, feedback_text, tip_feedback))
        
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
    tip_filter = request.args.get('tip_feedback', '')
    
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
    
    if tip_filter:
        query += ' AND tip_feedback = ?'
        params.append(tip_filter)
    
    query += ' ORDER BY timestamp DESC'
    
    # Execute query with parameters
    c.execute(query, params)
    feedback_entries = c.fetchall()
    
    # Close connection
    conn.close()
    
    # Convert results to format easily used in template
    entries = []
    for entry in feedback_entries:
        # Check if response already contains HTML formatting
        if '<pre><code class="cpp">' in entry[4] or '<ul>' in entry[4] or '<p>' in entry[4] or '<strong>' in entry[4]:
            # If it already contains HTML, use it directly
            formatted_response = entry[4]
        else:
            # If it doesn't contain HTML, apply formatting
            formatted_response = format_code_blocks(entry[4])
            formatted_response = format_steps_and_paragraphs(formatted_response)
            formatted_response = format_inline_code(formatted_response)
        
        entries.append({
            'id': entry[0],
            'timestamp': entry[1],
            'clasa': entry[2],
            'user_input': entry[3],
            'ai_response': formatted_response,
            'feedback': entry[5],
            'feedback_text': entry[6] if len(entry) > 6 else '',
            'tip_feedback': entry[7] if len(entry) > 7 else ''
        })
    
    return render_template('view_feedback.html', 
                         feedback_entries=entries,
                         current_clasa=clasa_filter,
                         current_feedback=feedback_filter,
                         current_tip=tip_filter)

# === Route for profile ===
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            current_user.clasa = form.clasa.data
            db.session.commit()
            flash('Clasa a fost actualizată cu succes!', 'success')
        return redirect(url_for('profile'))
    # Pre-populate the form with current user's class
    form.clasa.data = current_user.clasa
    return render_template('profile.html', form=form)

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

def migrate_set_titles_for_old_conversations():
    """Setează titlul pentru toate conversațiile care nu au titlu, folosind primul mesaj al utilizatorului."""
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    # Selectează conversațiile fără titlu sau cu titlu NULL/vid
    c.execute('''
        SELECT id FROM conversations WHERE title IS NULL OR title = ''
    ''')
    convs = c.fetchall()
    for (conv_id,) in convs:
        # Ia primul mesaj al utilizatorului
        c.execute('''
            SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY timestamp ASC, id ASC LIMIT 1
        ''', (conv_id,))
        row = c.fetchone()
        if row and row[0]:
            title = row[0][:50] + "..." if len(row[0]) > 50 else row[0]
            c.execute('''
                UPDATE conversations SET title = ? WHERE id = ?
            ''', (title, conv_id))
    conn.commit()
    conn.close()

# === Route for debugging conversations ===
@app.route('/api/debug_conversations')
def debug_conversations():
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT id, title FROM conversations ORDER BY start_time DESC')
    data = c.fetchall()
    conn.close()
    return jsonify([{'id': row[0], 'title': row[1]} for row in data])

# === Route for getting conversation stats ===
@app.route('/api/conversation_stats/<int:conversation_id>')
@login_required
def get_conversation_stats(conversation_id):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    # Get conversation stats
    c.execute('''
        SELECT context_window_size, total_tokens, message_count, last_context_update, title
        FROM conversations
        WHERE id = ? AND user_id = ?
    ''', (conversation_id, current_user.id))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Conversation not found'}), 404
    context_window_size, total_tokens, message_count, last_update, title = row
    # Get messages in context
    c.execute('''
        SELECT COUNT(*) FROM messages 
        WHERE conversation_id = ? AND in_context = 1
    ''', (conversation_id,))
    messages_in_context = c.fetchone()[0]
    conn.close()
    return jsonify({
        'context_window_size': context_window_size,
        'total_tokens': total_tokens,
        'message_count': message_count,
        'messages_in_context': messages_in_context,
        'last_update': last_update,
        'title': title
    })

# === Route for updating context window size ===
@app.route('/api/update_context_window/<int:conversation_id>', methods=['POST'])
@login_required
def update_context_window_size(conversation_id):
    new_size = request.json.get('size')
    if not new_size or not isinstance(new_size, int) or new_size < 1:
        return jsonify({'error': 'Invalid window size'}), 400
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    # Verify conversation belongs to user
    c.execute('SELECT user_id FROM conversations WHERE id = ?', (conversation_id,))
    row = c.fetchone()
    if not row or row[0] != current_user.id:
        conn.close()
        return jsonify({'error': 'Conversation not found'}), 404
    # Update window size
    c.execute('''
        UPDATE conversations 
        SET context_window_size = ?
        WHERE id = ?
    ''', (new_size, conversation_id))
    conn.commit()
    conn.close()
    # Update context window with new size
    update_context_window(conversation_id)
    return jsonify({'success': True, 'new_size': new_size})

# === Route for rezumat conversatie ===
@app.route('/api/rezumat_conversatie/<int:conversation_id>')
@login_required
def rezumat_conversatie(conversation_id):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    # Verifică dacă conversația aparține userului
    c.execute('SELECT user_id FROM conversations WHERE id = ?', (conversation_id,))
    row = c.fetchone()
    if not row or row[0] != current_user.id:
        conn.close()
        return jsonify({'error': 'Conversație inexistentă sau acces interzis'}), 404
    # Ia mesajele din conversație (max 20 pentru context)
    c.execute('''
        SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC, id ASC LIMIT 20
    ''', (conversation_id,))
    messages = c.fetchall()
    conn.close()
    if not messages:
        return jsonify({'error': 'Conversația nu are mesaje'}), 400
    # Construiește contextul pentru OpenAI
    conv_text = "\n".join([
        ("Utilizator: " if m[0]=='user' else "InfoCoach: ") + m[1] for m in messages
    ])
    prompt = f"""Rezumă conversația de mai jos într-un mod clar, structurat și pe scurt (maxim 5-7 propoziții). Folosește titluri de secțiuni dacă e relevant.\n\n{conv_text}\n\nRezumat structurat:"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ești un asistent care face rezumate clare, structurate și concise pentru conversații educaționale."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.4
        )
        rezumat = response.choices[0].message.content.strip()
        return jsonify({'success': True, 'rezumat': rezumat})
    except Exception as e:
        return jsonify({'error': f'Eroare la generarea rezumatului: {e}'})

# === Route for quiz conversatie ===
@app.route('/api/quiz_conversatie/<int:conversation_id>')
@login_required
def quiz_conversatie(conversation_id):
    conn = sqlite3.connect('feedback/feedback.db', check_same_thread=False)
    c = conn.cursor()
    # Verifică dacă conversația aparține userului
    c.execute('SELECT user_id FROM conversations WHERE id = ?', (conversation_id,))
    row = c.fetchone()
    if not row or row[0] != current_user.id:
        conn.close()
        return jsonify({'error': 'Conversație inexistentă sau acces interzis'}), 404
    # Ia mesajele din conversație (max 20 pentru context)
    c.execute('''
        SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC, id ASC LIMIT 20
    ''', (conversation_id,))
    messages = c.fetchall()
    conn.close()
    if not messages:
        return jsonify({'error': 'Conversația nu are mesaje'}), 400
    # Determină volumul conversației și crește numărul de întrebări
    total_chars = sum(len(m[1]) for m in messages)
    if total_chars < 600:
        n_questions = 4
    elif total_chars < 1200:
        n_questions = 6
    elif total_chars < 2000:
        n_questions = 8
    else:
        n_questions = 10
    # Construiește contextul pentru OpenAI
    conv_text = "\n".join([
        ("Utilizator: " if m[0]=='user' else "InfoCoach: ") + m[1] for m in messages
    ])
    prompt = f"""Generează un quiz cu {n_questions} întrebări pe baza conversației de mai jos.
Fiecare întrebare trebuie să fie clară, fără ambiguități, provocatoare (nu doar de memorare, ci să implice raționament sau aplicare), și să poată fi răspunsă folosind conceptele și explicațiile din conversație (NU din cunoștințe generale).
Concentrează-te pe conceptele de bază, principiile și raționamentele explicate în conversație, nu pe detalii superficiale sau specifice (de exemplu, nu întreba despre nume de variabile, valori exacte sau alte detalii triviale).
Nu folosi întrebări cu răspunsuri ambigue sau interpretabile. Nu genera întrebări la care răspunsul nu se găsește explicit sau implicit în explicațiile din conversație.
Pentru fiecare întrebare, folosește exact formatul:
### Întrebarea aici
- variantă 1
- variantă 2
- variantă 3
IMPORTANT: Marchează cu (corect) doar o singură variantă la fiecare întrebare, și doar dacă ești 100% sigur că este corectă conform explicațiilor din conversație. Poziția răspunsului corect trebuie să fie complet aleatorie și să varieze de la o întrebare la alta (nu urma niciun tipar, nu pune mereu pe a doua poziție). Nu marca nicio variantă ca fiind corectă dacă nu ești sigur. Nu folosi bold sau alte marcaje, doar (corect) la varianta corectă. Folosește Markdown pentru structură, ca la exemplu.

{conv_text}

Quiz structurat în Markdown:"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": (
                    "Ești un asistent care generează quiz-uri clare, structurate și concise pentru conversații educaționale. "
                    "Fiecare întrebare trebuie să aibă EXACT 3 variante de răspuns, doar una marcată cu (corect), fără bold sau alte marcaje. "
                    "Nu genera întrebări ambigue, interpretabile sau la care răspunsul nu se găsește explicit sau implicit în conversație. "
                    "Nu folosi cunoștințe generale, doar informații din conversație."
                )},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.4
        )
        quiz = response.choices[0].message.content.strip()
        return jsonify({'success': True, 'quiz': quiz})
    except Exception as e:
        return jsonify({'error': f'Eroare la generarea quiz-ului: {e}'})

# === Route for quiz report ===
@app.route('/api/quiz_report/<int:conversation_id>', methods=['POST'])
def quiz_report(conversation_id):
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Textul raportului este gol.'}), 400
    try:
        with open('quiz_reports.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} | conv_id={conversation_id} | {text}\n")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === Route for problem solver page ===
@app.route('/problem_solver')
@login_required
def problem_solver():
    return render_template('problem_solver.html')

# === Route for viewing problems ===
@app.route('/problems')
@login_required
def view_problems():
    page = request.args.get('page', 1, type=int)
    grade = request.args.get('grade', type=int)
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    search = request.args.get('search', '')
    
    # Construim query-ul de bază
    query = "SELECT id, name, statement, input_description, output_description, constraints, example_input, example_output, example_input_name, example_output_name, grade, category, difficulty FROM problems WHERE 1=1"
    params = []
    
    if grade:
        query += " AND grade = ?"
        params.append(grade)
    if category:
        query += " AND category = ?"
        params.append(category)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)
    if search:
        query += " AND (name LIKE ? OR id LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    # Adăugăm paginarea
    per_page = 10
    offset = (page - 1) * per_page
    
    # Obținem totalul de probleme pentru paginare
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total = get_db().execute(count_query, params).fetchone()[0]
    
    # Adăugăm LIMIT și OFFSET la query-ul principal
    query += " ORDER BY id LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    # Obținem problemele pentru pagina curentă
    problems = get_db().execute(query, params).fetchall()
    
    # Obținem toate categoriile, dificultățile și clasele pentru filtre
    categories = [row[0] for row in get_db().execute("SELECT DISTINCT category FROM problems WHERE category != '' ORDER BY category").fetchall()]
    difficulties = [row[0] for row in get_db().execute("SELECT DISTINCT difficulty FROM problems WHERE difficulty != '' ORDER BY difficulty").fetchall()]
    grades = [row[0] for row in get_db().execute("SELECT DISTINCT grade FROM problems WHERE grade IS NOT NULL AND grade != '' ORDER BY grade").fetchall()]
    
    has_next = (page * per_page) < total
    
    return render_template('view_problems.html',
                         problems=problems,
                         page=page,
                         grade=grade,
                         category=category,
                         difficulty=difficulty,
                         search=search,
                         categories=categories,
                         difficulties=difficulties,
                         grades=grades,
                         has_next=has_next,
                         total=total
    )

def get_db():
    import sqlite3
    conn = sqlite3.connect('problems.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Asigură rezultate ca dict
    return conn

# === Route for problem search ===
@app.route('/api/problem_search')
def api_problem_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'problems': []})
    # Exemplu: caută în nume și categorie, ordonează după potrivire simplă
    conn = sqlite3.connect('problems.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Caută problemele care conțin toți termenii din query în nume sau categorie
    terms = q.split()
    sql = "SELECT id, name, category, tags, categories FROM problems"
    cur.execute(sql)
    all_problems = cur.fetchall()
    def score(problem):
        name = problem['name'].lower()
        category = problem['category'].lower() if problem['category'] else ''
        tags = problem['tags'].lower() if 'tags' in problem.keys() and problem['tags'] else ''
        categories = problem['categories'].lower() if 'categories' in problem.keys() and problem['categories'] else ''
        return sum(1 for term in terms if term in name or term in category or term in tags or term in categories)
    filtered_problems = [p for p in all_problems if score(p) > 0]
    filtered_problems.sort(key=score, reverse=True)
    def parse_json_field(field):
        import json
        if not field:
            return []
        try:
            return json.loads(field)
        except Exception:
            return [field] if isinstance(field, str) else []
    return jsonify({'problems': [
        {
            'id': p['id'],
            'name': p['name'],
            'category': p['category'],
            'tags': parse_json_field(p['tags']) if 'tags' in p.keys() else [],
            'categories': parse_json_field(p['categories']) if 'categories' in p.keys() else []
        }
        for p in filtered_problems[:10]
    ]})

# === Route for running code ===
@app.route('/api/run_code', methods=['POST'])
def api_run_code():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
        
    code = data.get('code', '').strip()
    files = data.get('files', [])  # list of {name, content}
    custom_input = data.get('custom_input') or data.get('input') or ''
    
    # Validate input
    if not code:
        return jsonify({'error': 'No code provided'}), 400
        
    # Validate file names and content
    for file in files:
        if not isinstance(file, dict) or 'name' not in file or 'content' not in file:
            return jsonify({'error': 'Invalid file format'}), 400
        if not file['name'] or not isinstance(file['name'], str):
            return jsonify({'error': 'Invalid file name'}), 400
        if not isinstance(file['content'], str):
            return jsonify({'error': 'Invalid file content'}), 400
            
    main_filename = 'main.cpp'
    result = {'success': False, 'output': '', 'error': ''}
    tempdir = tempfile.mkdtemp(prefix='cpp_run_')
    
    try:
        # Write main.cpp with proper encoding
        with open(f'{tempdir}/{main_filename}', 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Write additional files with proper validation
        for fobj in files:
            fname = fobj.get('name')
            fcontent = fobj.get('content', '')
            if fname and fname != main_filename and not fname.endswith('.out'):
                # Validate file path to prevent directory traversal
                if '..' in fname or '/' in fname or '\\' in fname:
                    raise ValueError('Invalid file path')
                with open(f'{tempdir}/{fname}', 'w', encoding='utf-8') as ff:
                    ff.write(fcontent)
                    
        # Check for input file
        input_file = None
        for fobj in files:
            if fobj['name'].endswith('.in'):
                input_file = fobj['name']
                break
                
        # Detect if code uses cin/cout and nu ifstream
        uses_cin = 'cin' in code
        uses_ifstream = 'ifstream' in code
        # If input_file exists, code uses cin, and nu ifstream, inject file as stdin
        inject_input_as_stdin = False
        if input_file and uses_cin and not uses_ifstream:
            try:
                with open(f'{tempdir}/{input_file}', 'r', encoding='utf-8') as f:
                    custom_input = f.read()
            except Exception:
                custom_input = ''
            inject_input_as_stdin = True
        
        # Compile command with additional security flags
        compile_cmd = f"g++ -O2 -std=c++17 -Wall -Wextra main.cpp -o main 2> compile_err.txt"
        
        # Run command with timeout and resource limits
        run_cmd = f"timeout 2s ./main"
        if input_file and not inject_input_as_stdin:
            run_cmd += f" < {input_file}"
            run_cmd += " > program_out.txt 2> runtime_err.txt"
            
            # Run in Docker with enhanced security
            docker_cmd = [
                'docker', 'run', '--rm',
                '--network', 'none',
                '--memory', '256m', '--cpus', '0.5',
                '--security-opt', 'no-new-privileges',
                '--cap-drop', 'ALL',
                '-v', f'{tempdir}:/workspace:rw',
                '-w', '/workspace',
                'cpp-runner',
                '/bin/bash', '-c', f"{compile_cmd} && {run_cmd}"
            ]
            
            try:
                proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=10)
            except subprocess.TimeoutExpired:
                result['error'] = 'Execution timed out'
                return jsonify(result)
                
            # Read compilation errors
            compile_err = ''
            try:
                with open(f'{tempdir}/compile_err.txt', 'r', encoding='utf-8') as f:
                    compile_err = f.read().strip()
            except Exception:
                pass
                
            if compile_err:
                result['output'] = ''
                result['error'] = compile_err
                result['success'] = False
                return jsonify(result)
                
            # Read program output and errors
            prog_out = ''
            runtime_err = ''
            try:
                with open(f'{tempdir}/program_out.txt', 'r', encoding='utf-8') as f:
                    prog_out = f.read().strip()
                with open(f'{tempdir}/runtime_err.txt', 'r', encoding='utf-8') as f:
                    runtime_err = f.read().strip()
            except Exception:
                pass
                
            # Read any generated .out files
            out_files = glob.glob(f'{tempdir}/*.out')
            file_outputs = []
            for out_file in out_files:
                try:
                    with open(out_file, 'r', encoding='utf-8') as f:
                        file_outputs.append(f.read().strip())
                except Exception:
                    pass
                    
            # Combine outputs
            combined_output = ''
            if file_outputs:
                combined_output += '\n'.join(file_outputs)
            if prog_out:
                if combined_output:
                    combined_output += '\n' + prog_out
                else:
                    combined_output = prog_out
                    
            if runtime_err:
                result['output'] = ''
                result['error'] = runtime_err
                result['success'] = False
            else:
                result['output'] = combined_output if combined_output else '(no output)'
                result['error'] = ''
                result['success'] = True
                
            return jsonify(result)
            
        else:
            # Compile separately with enhanced security
            compile_docker_cmd = [
                'docker', 'run', '--rm',
                '--network', 'none',
                '--memory', '256m', '--cpus', '0.5',
                '--security-opt', 'no-new-privileges',
                '--cap-drop', 'ALL',
                '-v', f'{tempdir}:/workspace:rw',
                '-w', '/workspace',
                'cpp-runner',
                'g++', '-O2', '-std=c++17', '-Wall', '-Wextra', 'main.cpp', '-o', 'main'
            ]
            
            try:
                compile_proc = subprocess.run(compile_docker_cmd, capture_output=True, text=True, timeout=10)
            except subprocess.TimeoutExpired:
                result['error'] = 'Compilation timed out'
                return jsonify(result)
                
            if compile_proc.returncode != 0:
                result['output'] = ''
                result['error'] = compile_proc.stderr + '\n' + compile_proc.stdout
                result['success'] = False
                return jsonify(result)
                
            # Run with custom input (either from user or injected from .in file)
            run_docker_cmd = [
                'docker', 'run', '--rm',
                '-i',
                '--network', 'none',
                '--memory', '256m', '--cpus', '0.5',
                '--security-opt', 'no-new-privileges',
                '--cap-drop', 'ALL',
                '-v', f'{tempdir}:/workspace:rw',
                '-w', '/workspace',
                'cpp-runner',
                './main'
            ]
            try:
                proc = subprocess.run(run_docker_cmd, input=custom_input, capture_output=True, text=True, timeout=10)
            except subprocess.TimeoutExpired:
                result['error'] = 'Execution timed out'
                return jsonify(result)
            prog_out = proc.stdout.strip()
            runtime_err = proc.stderr.strip()
            if runtime_err:
                result['output'] = ''
                result['error'] = runtime_err
                result['success'] = False
            else:
                result['output'] = prog_out
                result['error'] = ''
                result['success'] = True
            return jsonify(result)
            
    except Exception as e:
        result['error'] = f'Execution error: {str(e)}'
        return jsonify(result)
        
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(tempdir, ignore_errors=True)
        except Exception:
            pass

# === Route for sending message ===
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    
    # Extrage enunțul problemei și codul curent al userului din baza de date
    problem = db.execute("SELECT problem_statement FROM problems WHERE id = (SELECT problem_id FROM conversations WHERE id = ?)", (conversation_id,)).fetchone()
    user_code = db.execute("SELECT code FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    
    if not problem or not user_code:
        return jsonify({"error": "Problemă sau cod negăsit"}), 404
    
    problem_statement = problem['problem_statement']
    user_code = user_code['code']
    
    # Construiește promptul specific pentru asistentul de programare
    system_prompt = """Ești un asistent specializat în programare, cu focus pe C++. 
    Rolul tău este să ajuti studenții să înțeleagă și să rezolve probleme de programare.
    Răspunsurile tale trebuie să fie clare, concise și să includă explicații pas cu pas.
    Dacă observi erori în cod, explică-le și sugerează corecții.
    Nu rescrie niciodată codul corectat
    Dacă codul este corect, oferă sugestii de optimizare sau îmbunătățire."""
    
    user_prompt = f"""
    Problemă: {problem_statement}
    
    Codul curent al studentului:
    {user_code}
    
    Întrebarea studentului: {message}
    """
    
    try:
        # Configurare OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY1')  # Folosește OPENAI_API_KEY1 din .env
        
        # Trimite promptul la API-ul OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Controllează creativitatea răspunsurilor
            max_tokens=1000   # Limitează lungimea răspunsului
        )
        
        ai_response = response.choices[0].message['content']
        
        # Salvează mesajul și răspunsul în baza de date
        db.execute("INSERT INTO messages (conversation_id, content, is_user) VALUES (?, ?, ?)", 
                  (conversation_id, message, True))
        db.execute("INSERT INTO messages (conversation_id, content, is_user) VALUES (?, ?, ?)", 
                  (conversation_id, ai_response, False))
        db.commit()
        
        return jsonify({"response": ai_response})
        
    except Exception as e:
        print(f"Eroare la comunicarea cu OpenAI: {str(e)}")
        return jsonify({"error": "A apărut o eroare la procesarea cererii. Vă rugăm să încercați din nou."}), 500

# === Route for AI assistant ===
@app.route('/ai_assistant', methods=['POST'])
def ai_assistant():
    data = request.get_json()
    user_message = data.get('message', '')
    enunt = data.get('enunt', '')
    date = data.get('date', '')
    restrictii = data.get('restrictii', '')
    limite = data.get('limite', '')
    exemplu = data.get('exemplu', '')
    code = data.get('code', '')
    if not user_message:
        return jsonify({'error': 'Mesajul este gol.'}), 400
    import openai
    import os
    api_key = os.getenv('OPENAI_API_KEY1')
    client = openai.OpenAI(api_key=api_key)
    # Încarcă system promptul din fișier
    try:
        with open(os.path.join(os.path.dirname(__file__), 'instructions_code.txt'), encoding='utf-8') as f:
            system_prompt = f.read().strip()
    except Exception as e:
        return jsonify({'error': f'Nu pot citi instructions_code.txt: {str(e)}'}), 500
    # Construiește promptul contextual cu toate secțiunile
    user_prompt = f"""Problemă:
Enunț: {enunt}
Date: {date}
Restricții: {restrictii}
Limite: {limite}
Exemplu: {exemplu}

Codul curent al utilizatorului:
{code}

Întrebare:
{user_message}"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        ai_reply = response.choices[0].message.content
        return jsonify({'response': ai_reply})
    except Exception as e:
        return jsonify({'error': f'Eroare la OpenAI: {str(e)}'}), 500

# === Route for problem details ===
@app.route('/api/problem_details')
def api_problem_details():
    problem_id = request.args.get('id', type=int)
    if not problem_id:
        return jsonify({'error': 'ID lipsă'}), 400
    conn = sqlite3.connect('problems.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name, statement, input_description, output_description, constraints, example_input, example_output, example_input_name, example_output_name, time_limit, memory_limit FROM problems WHERE id = ?", (problem_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'Problemă inexistentă'}), 404
    
    # Obține exemplele multiple
    cur.execute("SELECT example_number, input_data, output_data, input_file_name, output_file_name FROM examples WHERE problem_id = ? ORDER BY example_number", (problem_id,))
    examples = cur.fetchall()
    
    # Detectează tipul problemei
    problem_type = detect_problem_type(row['statement'])
    
    response = jsonify({
        'id': problem_id,
        'name': row['name'],
        'statement': row['statement'],
        'input_description': row['input_description'],
        'output_description': row['output_description'],
        'constraints': row['constraints'],
        'example_input': row['example_input'],  # Păstrează pentru compatibilitate
        'example_output': row['example_output'],  # Păstrează pentru compatibilitate
        'example_input_name': row['example_input_name'],
        'example_output_name': row['example_output_name'],
        'time_limit': row['time_limit'],
        'memory_limit': row['memory_limit'],
        'problem_type': problem_type,
        'examples': [{
            'number': ex['example_number'],
            'input': ex['input_data'],
            'output': ex['output_data'],
            'input_file_name': ex['input_file_name'],
            'output_file_name': ex['output_file_name']
        } for ex in examples]
    })
    
    # Adaugă headers pentru a preveni cache-ul
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# === Function to detect problem type ===
def detect_problem_type(statement):
    """
    Detectează dacă problema cere doar un subprogram (funcție/clasă) 
    sau un program complet cu main().
    
    Returns:
        'subprogram' - dacă problema cere doar o funcție/clasă
        'complete' - dacă problema cere un program complet
    """
    if not statement:
        return 'complete'
    
    statement_lower = statement.lower()
    
    # Cuvinte cheie care indică că se cere doar un subprogram
    subprogram_keywords = [
        'scrie o funcție',
        'scrie funcția',
        'implementează o funcție',
        'implementează funcția',
        'defineste o funcție',
        'defineste funcția',
        'scrie o clasă',
        'scrie clasa',
        'implementează o clasă',
        'implementează clasa',
        'defineste o clasă',
        'defineste clasa',
        'să se scrie o funcție',
        'să se scrie funcția',
        'să se implementeze o funcție',
        'să se implementeze funcția',
        'să se definească o funcție',
        'să se definească funcția',
        'să se scrie o clasă',
        'să se scrie clasa',
        'să se implementeze o clasă',
        'să se implementeze clasa',
        'să se definească o clasă',
        'să se definească clasa'
    ]
    
    # Verifică dacă cerința conține cuvinte cheie pentru subprograme
    for keyword in subprogram_keywords:
        if keyword in statement_lower:
            return 'subprogram'
    
    # Cuvinte cheie care indică că se cere un program complet
    complete_program_keywords = [
        'scrie un program',
        'scrie programul',
        'implementează un program',
        'implementează programul',
        'să se scrie un program',
        'să se scrie programul',
        'să se implementeze un program',
        'să se implementeze programul',
        'programul va citi',
        'programul va afișa',
        'programul va scrie'
    ]
    
    # Verifică dacă cerința conține cuvinte cheie pentru programe complete
    for keyword in complete_program_keywords:
        if keyword in statement_lower:
            return 'complete'
    
    # Dacă nu găsește cuvinte cheie clare, presupune că este un program complet
    return 'complete'

# === Function to generate test code for subprograms ===
def generate_test_code_for_subprogram(problem_statement, user_code, problem_id):
    """
    Generează cod de test pentru un subprogram folosind AI.
    Include sistem de cache pentru a evita regenerarea aceluiași cod.
    """
    import hashlib
    import json
    from datetime import datetime, timedelta
    
    # Generează un hash pentru codul utilizatorului și problema
    code_hash = hashlib.md5(f"{user_code}_{problem_id}".encode()).hexdigest()
    
    # Verifică cache-ul
    cache_key = f"test_code_{problem_id}_{code_hash}"
    cache_file = f"cache/{cache_key}.json"
    
    # Creează directorul cache dacă nu există
    os.makedirs("cache", exist_ok=True)
    
    # Verifică dacă există în cache și nu a expirat (24 ore)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Verifică dacă cache-ul nu a expirat
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=24):
                logging.info(f"Using cached test code for problem {problem_id}")
                return cache_data['test_code']
        except Exception as e:
            logging.warning(f"Error reading cache: {e}")
    
    # Generează codul de test cu AI
    try:
        system_prompt = """Ești un expert în C++ care generează cod de test pentru subprograme.\n\nSarcina ta este să generezi un program C++ complet care:\n1. Include EXACT subprogramul scris de utilizator (cu toți parametrii, inclusiv cei cu valori implicite)\n2. Adaugă un main() care citește datele de intrare (fără niciun mesaj pentru utilizator) și apelează subprogramul\n3. Afișează rezultatul (fără niciun mesaj explicativ, doar rezultatul brut)\n\nREGULI IMPORTANTE:\n- NU adăuga niciun mesaj pentru utilizator (NU folosi cout << cu text explicativ sau validare)\n- NU adăuga validări suplimentare\n- Include funcția utilizatorului EXACT așa cum a fost scrisă, inclusiv parametrii cu valori implicite\n- Nu modifica semnătura funcției utilizatorului\n- Nu adăuga implementări alternative\n- Generează doar codul C++ complet, fără explicații\n\nRăspunsul tău trebuie să fie DOAR codul C++ complet, fără explicații suplimentare."""
        
        user_prompt = f"""
        Problemă: {problem_statement}
        
        Subprogramul utilizatorului:
        {user_code}
        
        Generează un program C++ complet care să testeze acest subprogram.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        test_code = response.choices[0].message.content.strip()
        
        # Curăță codul de markdown dacă există
        if test_code.startswith('```'):
            # Elimină prima linie (```cpp sau ```)
            lines = test_code.split('\n')
            if len(lines) > 1:
                lines = lines[1:]
                # Elimină ultima linie dacă este ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                test_code = '\n'.join(lines)
        
        # Asigură-te că codul conține main()
        if 'main()' not in test_code:
            logging.warning(f"Generated code doesn't contain main() for problem {problem_id}")
            return None
        
        # Salvează în cache
        cache_data = {
            'test_code': test_code,
            'timestamp': datetime.now().isoformat(),
            'problem_id': problem_id,
            'code_hash': code_hash
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Generated and cached test code for problem {problem_id}")
        return test_code
        
    except Exception as e:
        logging.error(f"Error generating test code: {e}")
        return None

# === Route for testing subprograms ===
@app.route('/api/test_subprogram', methods=['POST'])
def api_test_subprogram():
    """Endpoint pentru testarea subprogramelor cu generare automată de cod de test"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
        
    problem_id = data.get('problem_id')
    user_code = data.get('code', '').strip()
    custom_input = data.get('custom_input', '')
    
    if not problem_id or not user_code:
        return jsonify({'error': 'Problem ID and code are required'}), 400
    
    try:
        # Obține detaliile problemei
        conn = sqlite3.connect('problems.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT statement, example_input FROM problems WHERE id = ?", (problem_id,))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Problem not found'}), 404
        
        problem_statement = row['statement']
        example_input = row['example_input'] or custom_input
        
        # Generează codul de test
        test_code = generate_test_code_for_subprogram(problem_statement, user_code, problem_id)
        
        if not test_code:
            return jsonify({'error': 'Failed to generate test code'}), 500
        
        # Rulează codul de test
        result = {'success': False, 'output': '', 'error': ''}
        tempdir = tempfile.mkdtemp(prefix='cpp_test_')
        
        try:
            # Scrie codul de test
            with open(f'{tempdir}/main.cpp', 'w', encoding='utf-8') as f:
                f.write(test_code)
            
            # Compilează și rulează
            compile_cmd = f"g++ -O2 -std=c++17 -Wall -Wextra main.cpp -o main 2> compile_err.txt"
            
            compile_docker_cmd = [
                'docker', 'run', '--rm',
                '--network', 'none',
                '--memory', '256m', '--cpus', '0.5',
                '--security-opt', 'no-new-privileges',
                '--cap-drop', 'ALL',
                '-v', f'{tempdir}:/workspace:rw',
                '-w', '/workspace',
                'cpp-runner',
                'g++', '-O2', '-std=c++17', '-Wall', '-Wextra', 'main.cpp', '-o', 'main'
            ]
            
            compile_proc = subprocess.run(compile_docker_cmd, capture_output=True, text=True, timeout=10)
            
            if compile_proc.returncode != 0:
                result['error'] = compile_proc.stderr + '\n' + compile_proc.stdout
                return jsonify(result)
            
            # Rulează cu input-ul de test
            run_docker_cmd = [
                'docker', 'run', '--rm',
                '-i',
                '--network', 'none',
                '--memory', '256m', '--cpus', '0.5',
                '--security-opt', 'no-new-privileges',
                '--cap-drop', 'ALL',
                '-v', f'{tempdir}:/workspace:rw',
                '-w', '/workspace',
                'cpp-runner',
                './main'
            ]
            
            proc = subprocess.run(run_docker_cmd, input=example_input, capture_output=True, text=True, timeout=10)
            
            if proc.stderr:
                result['error'] = proc.stderr
            else:
                result['output'] = proc.stdout.strip()
                result['success'] = True
                
        finally:
            # Curăță directorul temporar
            try:
                shutil.rmtree(tempdir, ignore_errors=True)
            except Exception:
                pass
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error testing subprogram: {e}")
        return jsonify({'error': f'Execution error: {str(e)}'}), 500

# === Route for generating complete code ===
@app.route('/api/generate_complete_code', methods=['POST'])
def api_generate_complete_code():
    """Endpoint pentru generarea codului complet cu AI"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    problem_id = data.get('problem_id')
    user_code = data.get('code', '').strip()
    statement = data.get('statement', '').strip()
    
    if not problem_id or not user_code:
        return jsonify({'error': 'Problem ID and code are required'}), 400
    
    try:
        # Folosește statementul din request dacă există, altfel din baza de date
        if statement:
            problem_statement = statement
        else:
            conn = sqlite3.connect('problems.db')
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT statement FROM problems WHERE id = ?", (problem_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return jsonify({'error': 'Problem not found'}), 404
            problem_statement = row['statement']
        
        # Generează codul complet cu AI
        system_prompt = """Ești un expert în C++ care generează cod complet pentru probleme de programare.

Sarcina ta este să generezi un program C++ complet care:
1. Include EXACT subprogramul scris de utilizator (cu toate greșelile, fără modificări)
2. Adaugă doar include-urile necesare și using namespace std
3. Adaugă un main() complet care citește datele de intrare și apelează subprogramul
4. Afișează rezultatul în formatul așteptat

REGULI IMPORTANTE:
- Include funcția utilizatorului EXACT așa cum a fost scrisă, inclusiv greșelile de sintaxă
- NU modifica deloc subprogramul utilizatorului
- NU corecta greșelile din subprogramul utilizatorului
- Generează doar include-urile, using namespace std, și funcția main()
- Generează doar codul C++ complet, fără explicații

EXEMPLU:
Input utilizator:
int fact(int n, int p=1)
{
    for(int i=1;i<=n;i++)
        p*=i
        retun p;
}

Output așteptat:
#include <iostream>
using namespace std;

int fact(int n, int p=1)
{
    for(int i=1;i<=n;i++)
        p*=i
        retun p;
}

int main()
{
    int n;
    cin >> n;
    if (n < 0)
        cout << "Factorialul nu este definit pentru numere negative.\\n";
    else
        cout << "Factorialul lui " << n << " este " << fact(n) << ".\\n";
    return 0;
}

Răspunsul tău trebuie să fie DOAR codul C++ complet, fără explicații suplimentare."""
        
        user_prompt = f"""
        Problemă: {problem_statement}
        
        Subprogramul utilizatorului:
        {user_code}
        
        Generează un program C++ complet care să rezolve această problemă.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        complete_code = response.choices[0].message.content.strip()
        
        # Curăță codul de markdown dacă există
        if complete_code.startswith('```'):
            lines = complete_code.split('\n')
            if len(lines) > 1:
                lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                complete_code = '\n'.join(lines)
        
        return jsonify({
            'success': True,
            'complete_code': complete_code
        })
        
    except Exception as e:
        logging.error(f"Error generating complete code: {e}")
        return jsonify({'error': f'Failed to generate complete code: {str(e)}'}), 500

# === Initialize InfoPaste database ===
def cleanup_expired_pastes():
    """Șterge paste-urile expirate din baza de date"""
    try:
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        c = conn.cursor()
        
        # Șterge paste-urile expirate
        c.execute('''
            DELETE FROM code_pastes 
            WHERE expires_at IS NOT NULL 
            AND expires_at < ?
        ''', (datetime.now().isoformat(),))
        
        deleted_count = c.rowcount
        
        # Șterge și înregistrările de vizualizări pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_views 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        # Șterge comentariile pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_comments 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        # Șterge explicațiile pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_explanations 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        # Șterge aprecierile pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_likes 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"Cleanup completed: {deleted_count} expired pastes removed")
        return deleted_count
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return 0

def init_infopaste_db():
    """Initialize InfoPaste database tables"""
    conn = sqlite3.connect('infopaste.db', check_same_thread=False)
    c = conn.cursor()
    
    # Code pastes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS code_pastes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            code TEXT NOT NULL,
            language TEXT DEFAULT 'cpp',
            description TEXT,
            is_public BOOLEAN DEFAULT 1,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            expiration_type TEXT DEFAULT '1_week',
            expires_at TEXT,
            one_view_only BOOLEAN DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Add new columns to existing table if they don't exist
    c.execute("PRAGMA table_info(code_pastes)")
    paste_columns = [col[1] for col in c.fetchall()]
    
    new_paste_columns = {
        'expiration_type': 'TEXT DEFAULT "1_week"',
        'expires_at': 'TEXT',
        'one_view_only': 'BOOLEAN DEFAULT 0'
    }
    
    for col_name, col_type in new_paste_columns.items():
        if col_name not in paste_columns:
            try:
                c.execute(f'ALTER TABLE code_pastes ADD COLUMN {col_name} {col_type}')
            except Exception as e:
                print(f"Error adding {col_name} to code_pastes: {e}")
    
    # Paste explanations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS paste_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paste_id INTEGER,
            explanation_type TEXT, -- 'comments', 'suggestions', 'complexity'
            content TEXT,
            is_premium BOOLEAN DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY (paste_id) REFERENCES code_pastes(id)
        )
    ''')
    
    # Paste comments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS paste_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paste_id INTEGER,
            user_id INTEGER,
            comment TEXT,
            created_at TEXT,
            FOREIGN KEY (paste_id) REFERENCES code_pastes(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Paste views tracking table
    c.execute('''
        CREATE TABLE IF NOT EXISTS paste_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paste_id INTEGER,
            user_id INTEGER, -- NULL for anonymous users
            session_id TEXT, -- For anonymous users
            ip_address TEXT,
            viewed_at TEXT,
            FOREIGN KEY (paste_id) REFERENCES code_pastes(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Paste likes tracking table
    c.execute('''
        CREATE TABLE IF NOT EXISTS paste_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paste_id INTEGER,
            user_id INTEGER,
            liked_at TEXT,
            FOREIGN KEY (paste_id) REFERENCES code_pastes(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(paste_id, user_id)
        )
    ''')
    
    # Add subscription fields to users if not exist
    c.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in c.fetchall()]
    
    new_user_columns = {
        'subscription_type': 'TEXT DEFAULT "free"',
        'subscription_expires': 'TEXT',
        'premium_features_enabled': 'BOOLEAN DEFAULT 0'
    }
    
    for col_name, col_type in new_user_columns.items():
        if col_name not in user_columns:
            try:
                c.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
            except Exception as e:
                print(f"Error adding {col_name} to users: {e}")
    
    conn.commit()
    conn.close()

# Initialize InfoPaste database
init_infopaste_db()

# Run initial cleanup
cleanup_expired_pastes()

# === InfoPaste Routes ===

@app.route('/infopaste')
def infopaste_editor():
    """Editor principal pentru InfoPaste"""
    return render_template('infopaste_editor.html')

@app.route('/infopaste/create', methods=['POST'])
@login_required
def create_paste():
    """Creează un nou paste"""
    try:
        title = request.form.get('title', '').strip()
        code = request.form.get('code', '').strip()
        language = request.form.get('language', 'cpp')
        description = request.form.get('description', '').strip()
        is_public = request.form.get('is_public', '1') == '1'
        expiration_type = request.form.get('expiration', '1_week')
        one_view_only = request.form.get('one_view_only', '0') == '1'
        
        if not code:
            return jsonify({'error': 'Codul este obligatoriu'}), 400
        
        # Calculate expiration date
        expires_at = None
        if expiration_type != 'never':
            from datetime import timedelta
            now = datetime.now()
            
            if expiration_type == '1_hour':
                expires_at = (now + timedelta(hours=1)).isoformat()
            elif expiration_type == '6_hours':
                expires_at = (now + timedelta(hours=6)).isoformat()
            elif expiration_type == '1_day':
                expires_at = (now + timedelta(days=1)).isoformat()
            elif expiration_type == '3_days':
                expires_at = (now + timedelta(days=3)).isoformat()
            elif expiration_type == '1_week':
                expires_at = (now + timedelta(weeks=1)).isoformat()
            elif expiration_type == '1_month':
                expires_at = (now + timedelta(days=30)).isoformat()
        
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        c.execute('''
            INSERT INTO code_pastes (user_id, title, code, language, description, is_public, 
                                   expiration_type, expires_at, one_view_only, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (current_user.id, title, code, language, description, is_public, 
              expiration_type, expires_at, one_view_only, timestamp, timestamp))
        
        paste_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Run cleanup periodically (every 10th paste creation)
        # This is a simple way to run cleanup without external schedulers
        try:
            c.execute('SELECT COUNT(*) FROM code_pastes')
            total_pastes = c.fetchone()[0]
            if total_pastes % 10 == 0:  # Run cleanup every 10 paste creations
                cleanup_expired_pastes()
        except:
            pass  # Don't fail if cleanup fails
        
        return jsonify({
            'success': True,
            'paste_id': paste_id,
            'share_url': url_for('view_paste', paste_id=paste_id, _external=True)
        })
        
    except Exception as e:
        return jsonify({'error': f'Eroare la salvarea paste-ului: {str(e)}'}), 500

@app.route('/paste/<string:paste_id>')
def view_paste(paste_id):
    """Vizualizare paste public"""
    try:
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get paste details
        c.execute('''
            SELECT cp.* 
            FROM code_pastes cp 
            WHERE cp.id = ? AND cp.is_public = 1
        ''', (paste_id,))
        paste = c.fetchone()
        
        if not paste:
            return "Paste-ul nu a fost găsit sau nu este public", 404
        
        # Check if paste has expired
        if paste['expires_at']:
            try:
                expires_at = datetime.fromisoformat(paste['expires_at'])
                if datetime.now() > expires_at:
                    return render_template('paste_expired.html', 
                                        title="Paste-ul a expirat",
                                        message="Acest paste a expirat și nu mai este disponibil.",
                                        icon="⏰"), 410
            except:
                pass  # If date parsing fails, continue anyway
        
        # Check one view only
        if paste['one_view_only']:
            session_id = request.cookies.get('session_id')
            if not session_id:
                session_id = hashlib.md5(f"{request.remote_addr}_{datetime.now().isoformat()}".encode()).hexdigest()
            
            # Check if this paste has been viewed before
            c.execute('''
                SELECT id FROM paste_views 
                WHERE paste_id = ?
            ''', (paste_id,))
            
            if c.fetchone():
                return render_template('paste_expired.html', 
                                    title="Paste-ul a fost deja vizualizat",
                                    message="Acest paste poate fi accesat o singură dată și a fost deja vizualizat.",
                                    icon="🔒"), 410
        
        # Get username from main users database
        username = "Anonim"
        if paste['user_id']:
            try:
                user = User.query.get(paste['user_id'])
                if user:
                    username = user.username
            except:
                pass
        
        # Create a new dict with username
        paste_dict = dict(paste)
        paste_dict['username'] = username
        
        # Track view with session/IP tracking
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = hashlib.md5(f"{request.remote_addr}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Check if this view should be counted
        should_count_view = True
        
        if current_user.is_authenticated:
            # For logged in users, check if they've viewed this paste before
            c.execute('''
                SELECT id FROM paste_views 
                WHERE paste_id = ? AND user_id = ?
            ''', (paste_id, current_user.id))
            if c.fetchone():
                should_count_view = False
        else:
            # For anonymous users, check if they've viewed this paste in the last 24 hours
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            c.execute('''
                SELECT id FROM paste_views 
                WHERE paste_id = ? AND session_id = ? AND viewed_at > ?
            ''', (paste_id, session_id, yesterday))
            if c.fetchone():
                should_count_view = False
        
        # Only increment views if this is a new view
        if should_count_view:
            c.execute('UPDATE code_pastes SET views = views + 1 WHERE id = ?', (paste_id,))
            
            # Record the view
            c.execute('''
                INSERT INTO paste_views (paste_id, user_id, session_id, ip_address, viewed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (paste_id, current_user.id if current_user.is_authenticated else None, 
                  session_id, request.remote_addr, datetime.now().isoformat()))
        
        # Get comments
        c.execute('''
            SELECT pc.* 
            FROM paste_comments pc 
            WHERE pc.paste_id = ? 
            ORDER BY pc.created_at ASC
        ''', (paste_id,))
        comments_raw = c.fetchall()
        
        # Get usernames for comments
        comments = []
        for comment in comments_raw:
            comment_dict = dict(comment)
            comment_username = "Anonim"
            if comment['user_id']:
                try:
                    user = User.query.get(comment['user_id'])
                    if user:
                        comment_username = user.username
                except:
                    pass
            comment_dict['username'] = comment_username
            comments.append(comment_dict)
        
        # Get explanations (premium feature)
        c.execute('SELECT * FROM paste_explanations WHERE paste_id = ?', (paste_id,))
        explanations = c.fetchall()
        
        conn.commit()
        conn.close()
        
        return render_template('view_paste.html', 
                             paste=paste_dict, 
                             comments=comments, 
                             explanations=explanations)
        
    except Exception as e:
        return f"Eroare la încărcarea paste-ului: {str(e)}", 500

@app.route('/api/explain_paste', methods=['POST'])
@login_required
@require_premium
def explain_paste():
    """Generează explicații AI pentru paste"""
    try:
        data = request.get_json()
        paste_id = data.get('paste_id')
        code = data.get('code', '').strip()
        analysis_type = data.get('analysis_type', 'explanation')
        
        if not code:
            return jsonify({'error': 'Codul este obligatoriu'}), 400
        
        # Generează explicații AI în funcție de tipul de analiză
        if analysis_type == 'explanation':
            prompt = f"""
            Explică acest cod C++ pe scurt și structurat:
            
            {code}
            
            Răspunsul să conțină:
            • Ce face codul (1-2 propoziții)
            • Concepte C++ importante folosite
            • Cum funcționează algoritmul (pe scurt)
            
            Fii concis și direct.
            """
            system_prompt = "Ești un expert C++ care explică codul pe scurt și clar pentru elevi de liceu. Fii concis și direct."
        elif analysis_type == 'complexity':
            prompt = f"""
            Analizează complexitatea acestui cod C++:
            
            {code}
            
            Răspunsul să conțină:
            • Complexitatea temporală (Big O)
            • Complexitatea spațială
            • Cazul cel mai rău
            
            Fii concis și tehnic.
            """
            system_prompt = "Ești expert în analiza algoritmilor. Oferă analize concise și precise pentru elevi de liceu."
        else:
            return jsonify({'error': 'Tip de analiză necunoscut'}), 400
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        explanation = response.choices[0].message.content.strip()
        
        # Salvează explicația în baza de date
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        c.execute('''
            INSERT INTO paste_explanations (paste_id, explanation_type, content, created_at)
            VALUES (?, ?, ?, ?)
        ''', (paste_id, analysis_type, explanation, timestamp))
        
        conn.commit()
        conn.close()
        
        # Format the explanation for HTML display
        formatted_explanation = format_code_blocks(explanation)
        formatted_explanation = format_steps_and_paragraphs(formatted_explanation)
        formatted_explanation = format_inline_code(formatted_explanation)
        
        return jsonify({
            'success': True,
            'explanation': formatted_explanation
        })
        
    except Exception as e:
        return jsonify({'error': f'Eroare la generarea explicației: {str(e)}'}), 500

@app.route('/api/optimize_paste', methods=['POST'])
@login_required
@require_premium
def optimize_paste():
    """Sugerează optimizări pentru paste"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        analysis_type = data.get('analysis_type', 'optimization')
        
        if not code:
            return jsonify({'error': 'Codul este obligatoriu'}), 400
        
        # Generează sugestii de optimizare în funcție de tipul de analiză
        if analysis_type == 'optimization':
            prompt = f"""
            Sugerează optimizări pentru acest cod C++:
            
            {code}
            
            Răspunsul să conțină:
            • Principalele optimizări de performanță
            • Best practices C++ importante
            • Explicații concise despre ce să schimbi și de ce
            
            Fii practic și concis. Nu genera cod complet, doar explicații și sugestii.
            """
            system_prompt = "Ești expert în optimizarea C++. Sugerează îmbunătățiri practice și concise pentru elevi de liceu."
        elif analysis_type == 'complexity':
            prompt = f"""
            Analizează complexitatea acestui cod C++:
            
            {code}
            
            Răspunsul să conțină:
            • Complexitatea temporală (Big O)
            • Complexitatea spațială
            • Cazul cel mai rău
            
            Fii concis și tehnic.
            """
            system_prompt = "Ești expert în analiza algoritmilor. Oferă analize concise și precise pentru elevi de liceu."
        else:
            return jsonify({'error': 'Tip de analiză necunoscut'}), 400
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        optimization = response.choices[0].message.content.strip()
        
        # Format the optimization for HTML display
        formatted_optimization = format_code_blocks(optimization)
        formatted_optimization = format_steps_and_paragraphs(formatted_optimization)
        formatted_optimization = format_inline_code(formatted_optimization)
        
        return jsonify({
            'success': True,
            'optimization': formatted_optimization
        })
        
    except Exception as e:
        return jsonify({'error': f'Eroare la generarea optimizărilor: {str(e)}'}), 500

@app.route('/api/generate_description', methods=['POST'])
@login_required
@require_premium
def generate_description():
    """Generează o descriere scurtă automată pentru cod"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        language = data.get('language', 'cpp')
        
        if not code:
            return jsonify({'error': 'Codul este obligatoriu'}), 400
        
        # Generează o descriere scurtă automată
        prompt = f"""
        Generează o descriere FOARTE SCURTĂ (maxim 50 de caractere) pentru acest cod {language.upper()}:
        
        {code}
        
        Descrierea să fie:
        • Foarte scurtă (maxim 50 de caractere)
        • Să explice pe scurt ce face programul
        • Să nu fie prea detaliată pentru a nu avantaja prea mult utilizatorii non-premium
        • Să fie în română
        
        Exemple de descrieri scurte:
        - "Calculează suma numerelor pare"
        - "Găsește elementul maxim"
        - "Sortează vectorul"
        - "Verifică dacă numărul este prim"
        
        Răspunde doar cu descrierea, fără explicații suplimentare.
        """
        
        system_prompt = "Ești expert în programare. Generează descrieri scurte și concise pentru cod."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        description = response.choices[0].message.content.strip()
        
        # Elimină ghilimelele dacă există
        if description.startswith('"') and description.endswith('"'):
            description = description[1:-1]
        elif description.startswith('"'):
            description = description[1:]
        elif description.endswith('"'):
            description = description[:-1]
        
        # Asigură-te că descrierea nu depășește 50 de caractere
        if len(description) > 50:
            description = description[:47] + "..."
        
        return jsonify({
            'success': True,
            'description': description
        })
        
    except Exception as e:
        return jsonify({'error': f'Eroare la generarea descrierii: {str(e)}'}), 500

@app.route('/api/open_in_editor/<string:paste_id>')
def open_in_editor(paste_id):
    """Deschide paste-ul în problem_solver"""
    try:
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM code_pastes WHERE id = ?', (paste_id,))
        paste = c.fetchone()
        conn.close()
        
        if not paste:
            return jsonify({'error': 'Paste-ul nu a fost găsit'}), 404
        
        # Redirect către problem_solver cu codul pre-completat
        return jsonify({
            'success': True,
            'redirect_url': url_for('problem_solver'),
            'code': paste['code'],
            'title': paste['title']
        })
        
    except Exception as e:
        return jsonify({'error': f'Eroare la deschiderea în editor: {str(e)}'}), 500

@app.route('/api/like_paste/<string:paste_id>', methods=['POST'])
def like_paste(paste_id):
    """Like/unlike un paste"""
    try:
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        c = conn.cursor()
        
        # Check if user already liked this paste
        c.execute('''
            SELECT id FROM paste_likes 
            WHERE paste_id = ? AND user_id = ?
        ''', (paste_id, current_user.id))
        
        if c.fetchone():
            # User already liked this paste, unlike it
            c.execute('DELETE FROM paste_likes WHERE paste_id = ? AND user_id = ?', (paste_id, current_user.id))
            c.execute('UPDATE code_pastes SET likes = likes - 1 WHERE id = ?', (paste_id,))
            action = 'unliked'
        else:
            # User hasn't liked this paste, like it
            c.execute('''
                INSERT INTO paste_likes (paste_id, user_id, liked_at)
                VALUES (?, ?, ?)
            ''', (paste_id, current_user.id, datetime.now().isoformat()))
            c.execute('UPDATE code_pastes SET likes = likes + 1 WHERE id = ?', (paste_id,))
            action = 'liked'
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'action': action})
        
    except Exception as e:
        return jsonify({'error': f'Eroare la like: {str(e)}'}), 500

@app.route('/premium')
def premium():
    """Premium upgrade page"""
    if current_user.is_authenticated:
        can_use_trial = current_user.can_use_trial()
        has_used_trial = current_user.has_used_trial
        is_premium_active = current_user.is_premium_active()
    else:
        can_use_trial = True  # Allow trial for non-authenticated users
        has_used_trial = False
        is_premium_active = False
    
    return render_template('premium.html', 
                         can_use_trial=can_use_trial,
                         has_used_trial=has_used_trial,
                         is_premium_active=is_premium_active)

@app.route('/payment')
def payment():
    """Payment simulation page"""
    if current_user.is_authenticated:
        can_use_trial = current_user.can_use_trial()
        is_premium_active = current_user.is_premium_active()
    else:
        can_use_trial = True  # Allow trial for non-authenticated users
        is_premium_active = False
    
    return render_template('payment.html', 
                         can_use_trial=can_use_trial,
                         is_premium_active=is_premium_active)

# === Admin routes for premium management ===
@app.route('/admin/grant_premium/<int:user_id>')
@login_required
def admin_grant_premium(user_id):
    """Grant premium to a user (admin only)"""
    # For now, allow any authenticated user to grant premium
    # In production, you'd want proper admin checks
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.grant_premium(
        granted_by_id=current_user.id,
        duration_days=365,
        reason="admin_grant"
    )
    
    return jsonify({
        'success': True,
        'message': f'Premium granted to {user.username}'
    })

@app.route('/admin/revoke_premium/<int:user_id>')
@login_required
def admin_revoke_premium(user_id):
    """Revoke premium from a user (admin only)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.revoke_premium()
    
    return jsonify({
        'success': True,
        'message': f'Premium revoked from {user.username}'
    })

@app.route('/admin/premium_users')
@login_required
def admin_premium_users():
    """List all premium users (admin only)"""
    premium_users = User.query.filter_by(is_premium=True).all()
    users_data = []
    
    for user in premium_users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_premium': user.is_premium,
            'premium_until': user.premium_until.isoformat() if user.premium_until else None,
            'premium_reason': user.premium_reason
        })
    
    return jsonify({
        'success': True,
        'users': users_data
    })

@app.route('/admin/cleanup_expired_pastes')
@login_required
def admin_cleanup_pastes():
    """Endpoint pentru curățenia manuală a paste-urilor expirate"""
    try:
        deleted_count = cleanup_expired_pastes()
        return jsonify({
            'success': True,
            'message': f'Curățenie completă: {deleted_count} paste-uri expirate au fost șterse',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Eroare la curățenie: {str(e)}'
        }), 500

@app.route('/api/comment_paste/<string:paste_id>', methods=['POST'])
def comment_paste(paste_id):
    """Adaugă comentariu la un paste"""
    try:
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        comment = data.get('comment', '').strip()
        
        if not comment:
            return jsonify({'error': 'Comentariul este obligatoriu'}), 400
        
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        c.execute('''
            INSERT INTO paste_comments (paste_id, user_id, comment, created_at)
            VALUES (?, ?, ?, ?)
        ''', (paste_id, current_user.id, comment, timestamp))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': f'Eroare la adăugarea comentariului: {str(e)}'}), 500

@app.context_processor
def inject_theme():
    theme = request.cookies.get('theme', 'light')
    return dict(theme=theme)

@app.route('/test_theme')
def test_theme():
    return render_template('test_theme.html')

# === Admin decorator ===
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.username != 'mihaimoldovan':
            flash('Nu ai permisiuni de admin.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# === Admin routes ===
@app.route('/admin/problems')
@login_required
@require_admin
def admin_problems():
    conn = sqlite3.connect('problems.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name, statement FROM problems ORDER BY id")
    problems = cur.fetchall()
    conn.close()
    return render_template('admin_problems.html', problems=problems)

@app.route('/admin/problem/<int:problem_id>')
@login_required
@require_admin
def admin_edit_problem(problem_id):
    conn = sqlite3.connect('problems.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    problem = cur.fetchone()
    conn.close()
    
    if not problem:
        flash('Problema nu a fost găsită.', 'error')
        return redirect(url_for('admin_problems'))
    
    return render_template('admin_edit_problem.html', problem=problem)

@app.route('/admin/problem/<int:problem_id>', methods=['POST'])
@login_required
@require_admin
def admin_update_problem(problem_id):
    conn = sqlite3.connect('problems.db')
    cur = conn.cursor()
    
    try:
        # Obține datele din formular
        name = request.form.get('name', '').strip()
        statement = request.form.get('statement', '').strip()
        input_description = request.form.get('input_description', '').strip()
        output_description = request.form.get('output_description', '').strip()
        constraints = request.form.get('constraints', '').strip()
        time_limit = request.form.get('time_limit', '').strip()
        memory_limit = request.form.get('memory_limit', '').strip()
        
        # Actualizează problema
        cur.execute("""
            UPDATE problems SET 
                name = ?, statement = ?, input_description = ?, output_description = ?,
                constraints = ?, time_limit = ?, memory_limit = ?
            WHERE id = ?
        """, (name, statement, input_description, output_description, constraints,
              time_limit, memory_limit, problem_id))
        
        # Procesează exemplele multiple
        examples_data = {}
        for key, value in request.form.items():
            if key.startswith('examples['):
                # Parsează examples[1][input] -> (1, 'input', value)
                parts = key.replace('examples[', '').replace(']', '').split('[')
                if len(parts) == 2:
                    example_num = int(parts[0])
                    field_name = parts[1]
                    if example_num not in examples_data:
                        examples_data[example_num] = {}
                    examples_data[example_num][field_name] = value.strip()
        
        # Șterge exemplele existente
        cur.execute("DELETE FROM examples WHERE problem_id = ?", (problem_id,))
        
        # Adaugă exemplele noi
        for example_num, example_data in examples_data.items():
            if example_data.get('input') or example_data.get('output'):
                cur.execute("""
                    INSERT INTO examples (problem_id, example_number, input_data, output_data, input_file_name, output_file_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    problem_id, example_num, 
                    example_data.get('input', ''), 
                    example_data.get('output', ''),
                    example_data.get('input_file_name', ''),
                    example_data.get('output_file_name', '')
                ))
        
        conn.commit()
        flash('Problema a fost actualizată cu succes!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Eroare la actualizarea problemei: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_edit_problem', problem_id=problem_id))

@app.route('/api/problem_examples/<int:problem_id>')
@login_required
@require_admin
def api_problem_examples(problem_id):
    conn = sqlite3.connect('problems.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT example_number, input_data, output_data, input_file_name, output_file_name 
        FROM examples 
        WHERE problem_id = ? 
        ORDER BY example_number
    """, (problem_id,))
    
    examples = cur.fetchall()
    conn.close()
    
    return jsonify({
        'examples': [{
            'number': ex['example_number'],
            'input': ex['input_data'],
            'output': ex['output_data'],
            'input_file_name': ex['input_file_name'],
            'output_file_name': ex['output_file_name']
        } for ex in examples]
    })

@app.route('/api/public/problem_examples/<int:problem_id>')
def api_public_problem_examples(problem_id):
    """API public pentru exemple, fără permisiuni de admin"""
    conn = sqlite3.connect('problems.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT example_number, input_data, output_data, input_file_name, output_file_name 
        FROM examples 
        WHERE problem_id = ? 
        ORDER BY example_number
    """, (problem_id,))
    
    examples = cur.fetchall()
    conn.close()
    
    response = jsonify({
        'examples': [{
            'number': ex['example_number'],
            'input': ex['input_data'],
            'output': ex['output_data'],
            'input_file_name': ex['input_file_name'],
            'output_file_name': ex['output_file_name']
        } for ex in examples]
    })
    
    # Adaugă headers pentru a preveni cache-ul
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/admin/problem/<int:problem_id>/delete', methods=['POST'])
@login_required
@require_admin
def admin_delete_problem(problem_id):
    conn = sqlite3.connect('problems.db')
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
        conn.commit()
        flash('Problema a fost ștearsă cu succes!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Eroare la ștergerea problemei: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_problems'))

# === Function to ensure problems schema updates ===
def ensure_problems_schema_updates():
    conn = sqlite3.connect('problems.db')
    cur = conn.cursor()
    
    # Verifică dacă tabelul examples există
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='examples'
    """)
    
    if not cur.fetchone():
        # Creează tabelul examples pentru exemple multiple
        cur.execute("""
            CREATE TABLE examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER NOT NULL,
                example_number INTEGER NOT NULL,
                input_data TEXT,
                output_data TEXT,
                input_file_name TEXT,
                output_file_name TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems (id) ON DELETE CASCADE,
                UNIQUE(problem_id, example_number)
            )
        """)
        
        # Migrează exemplele existente din tabelul problems
        cur.execute("""
            INSERT INTO examples (problem_id, example_number, input_data, output_data, input_file_name, output_file_name)
            SELECT id, 1, example_input, example_output, example_input_name, example_output_name
            FROM problems 
            WHERE example_input IS NOT NULL AND example_input != ''
        """)
        
        print("Tabelul examples a fost creat și datele au fost migrate.")
    
    conn.commit()
    conn.close()

# Run problems schema updates
ensure_problems_schema_updates()

# === Start application ===
if __name__ == '__main__':
    migrate_set_titles_for_old_conversations()
    app.run(debug=True)
    
##nu pot adauga exemple, nu mi se schimba exemplele atunci cand selectez din dropbar