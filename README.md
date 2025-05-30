# InfoCoach - AI Assistant for Computer Science

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-web--framework-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

A Flask-based web application that provides an AI assistant specialized in computer science learning, adapted for grades 9-12. The application uses OpenAI GPT-4 to provide personalized and interactive responses, with support for C++ and conversation saving.

---

## ⚙️ Main Features

- 🤖 AI assistant specialized in computer science
- 📚 Content adapted for grades 9-12
- 💬 Interactive chat interface, ChatGPT style
- 🧠 Conversation history for each user
- ✍️ Automatic conversation summarization
- 📝 Feedback system for improving responses
- 🔒 Authentication and registration system
- 📊 Feedback viewing and filtering
- 💻 C++ code support with formatting and syntax highlighting

---

## 🖥️ System Requirements

- Python 3.8 or newer
- pip (Python package installer)
- SQLite3
- OpenAI account with GPT-4 API access

---

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/<user>/InfoCoach.git
cd InfoCoach
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix/MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with configuration variables:
```
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key
```

---

## 🗂️ Project Structure

```
.
├── app.py              # Main Flask application
├── models.py           # Database models (users, feedback, conversations)
├── forms.py            # Web forms (login, register, feedback)
├── chat/               # Conversation management logic
├── feedback/           # Feedback management
├── static/             # CSS and JavaScript files
├── templates/          # HTML pages (chat, login, dashboard etc.)
├── requirements.txt    # Python dependencies list
└── resources/          # Additional educational resources
```

---

## ▶️ Local Run

1. Make sure the virtual environment is activated
2. Run the Flask application:
```bash
python app.py
```
3. Open your browser and access `http://localhost:5000`

---

## 🧑‍🏫 Usage

1. Create a new account or log in
2. Select your grade (9-12)
3. Write your computer science questions (theory or code)
4. Receive personalized responses with detailed explanations
5. Provide feedback to improve response quality
6. Access conversation history and view quick summaries

---

## 🔐 Technical Features

- **Secure authentication** (password hashing, CSRF protection)
- **Relational database** with SQLite + SQLAlchemy
- **Modern and responsive interface**
- **Conversation persistence** and AI-generated summaries
- **C++ code highlighting** for technical responses

---

## 🤝 Contribution

1. Fork this repository
2. Create a new branch (`git checkout -b new-feature`)
3. Commit your changes (`git commit -am 'Add feature X'`)
4. Push to branch (`git push origin new-feature`)
5. Create a Pull Request 🙌

---

## 📄 License

This project is licensed under [MIT License](LICENSE).

---

## 📬 Support

For support or questions:

- Open an [issue on GitHub](https://github.com/<user>/InfoCoach/issues)
- Send an email to: `mihai.moldovan152007@gmail.com`
