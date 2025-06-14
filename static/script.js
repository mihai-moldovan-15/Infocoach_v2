// Scroll automat la ultimul mesaj
function scrollToBottom() {
    var chat = document.getElementById("chat-messages");
    if (chat) chat.scrollTop = chat.scrollHeight;
}

// Mesaje de așteptare
const messages = [
    "Se procesează întrebarea ta...",
    "Încă lucrez la răspuns...",
    "Verific resursele pentru cel mai bun răspuns...",
    "Aproape am terminat, mai ai puțină răbdare!"
];
let msgIndex = 0;
let intervalId = null;

function startWaitMessages() {
    const waitDiv = document.getElementById("wait-message");
    waitDiv.style.display = "block";
    waitDiv.textContent = messages[msgIndex];
    intervalId = setInterval(() => {
        msgIndex = (msgIndex + 1) % messages.length;
        waitDiv.textContent = messages[msgIndex];
    }, 2000);
    window.intervalId = intervalId;
    window.msgIndex = msgIndex;
}

// Function to add a message to the chat interface
function addMessage(content, isUser = false, userInput = '') {
    const chatMessages = document.getElementById("chat-messages");
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    if (isUser) {
        messageDiv.innerHTML = `<b>Tu:</b><br>${content}`;
    } else {
        // Create the full assistant message structure with feedback form
        messageDiv.innerHTML = `
            <b>InfoCoach:</b>
            <div class="message-content">${content}</div>
            <input type="hidden" class="user-input-hidden" value="${userInput.replace(/"/g, '&quot;')}">
            <div class="feedback-form">
                <span>Acest răspuns a fost util?</span>
                <button onclick="submitFeedback(this, 'da')" class="feedback-btn">Da</button>
                <button onclick="submitFeedback(this, 'nu')" class="feedback-btn">Nu</button>
                <span id="feedback-message"></span>
            </div>
        `;
    }

    chatMessages.appendChild(messageDiv);
    // Highlight code blocks within the newly added message
    messageDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
    });
    scrollToBottom();
}

function submitForm(event) {
    event.preventDefault();
    const form = event.target;
    const userInput = form.querySelector('textarea[name="user_input"]').value;
    const conversationId = form.querySelector('input[name="conversation_id"]').value;
    const clasa = form.querySelector('select[name="clasa"]')?.value || '9';
    
    if (!userInput.trim()) return false;
    
    // Add user message to chat
    addMessage(userInput, true);
    
    // Show waiting message
    const waitMessage = document.getElementById('wait-message');
    waitMessage.textContent = 'InfoCoach scrie...';
    waitMessage.style.display = 'block';
    
    // Disable form while waiting
    form.querySelector('textarea').disabled = true;
    form.querySelector('input[type="submit"]').disabled = true;
    
    // Prepare form data
    const formData = new FormData();
    formData.append('user_input', userInput);
    formData.append('clasa', clasa);
    if (conversationId) {
        formData.append('conversation_id', conversationId);
    }
    
    // Send request
    fetch('/api/chat', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Add assistant message to chat
            addMessage(data.response, false, userInput);
            
            // Update conversation ID in form if it's a new conversation
            if (data.conversation_id) {
                form.querySelector('input[name="conversation_id"]').value = data.conversation_id;
            }
        } else {
            addMessage('A apărut o problemă la generarea răspunsului asistentului.', false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addMessage('A apărut o problemă la comunicarea cu serverul.', false);
    })
    .finally(() => {
        // Clear and enable form
        form.querySelector('textarea').value = '';
        form.querySelector('textarea').disabled = false;
        form.querySelector('input[type="submit"]').disabled = false;
        waitMessage.style.display = 'none';
        scrollToBottom();
    });
    
    return false;
}

// Feedback handling
function submitFeedback(button, feedback) {
    const messageDiv = button.closest('.message.assistant');
    const messageContentDiv = messageDiv.querySelector('.message-content');
    // Get AI response from innerHTML
    let messageContent = messageContentDiv.innerHTML;
    // Get user input from hidden input
    const userInputHidden = messageDiv.querySelector('.user-input-hidden');
    let userInput = userInputHidden ? userInputHidden.value : '';
    if (userInput && userInput.startsWith('"') && userInput.endsWith('"')) {
        try { userInput = JSON.parse(userInput); } catch (e) {}
    }
    // Get clasa from hidden input
    const clasaHidden = messageDiv.querySelector('.clasa-hidden');
    let clasa = clasaHidden ? clasaHidden.value : (document.getElementById('clasa') ? document.getElementById('clasa').value : '9');
    const feedbackForm = messageDiv.querySelector('.feedback-form');
    // Pregătește datele
    const formData = new URLSearchParams();
    formData.append('user_input', userInput);
    formData.append('ai_response', messageContent);
    formData.append('clasa', clasa);
    formData.append('feedback', feedback);
    // Trimite feedback la server
    fetch('/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (feedbackForm) {
            if (data.error) {
                feedbackForm.innerHTML = '<span class="feedback-thankyou" style="color:#dc3545;">Eroare la salvarea feedback-ului: ' + data.error + '</span>';
            } else {
                feedbackForm.innerHTML = '<span class="feedback-thankyou" style="color:#28a745;">Mulțumim pentru feedback!</span>';
            }
        }
    })
    .catch(error => {
        if (feedbackForm) {
            feedbackForm.innerHTML = '<span class="feedback-thankyou" style="color:#dc3545;">Eroare la trimiterea feedback-ului: ' + error.message + '</span>';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Initial scroll to bottom
    scrollToBottom();
    // Initial highlight in case there's content on page load (e.g., previous messages)
    // This is less crucial now as highlighting is done per message addition
    // hljs.highlightAll();

    // Removed feedback form submission logic

    // Problem search logic for problem_solver page
    const searchForm = document.querySelector('.ide-search-bar');
    const searchInput = document.querySelector('.ide-search-input');
    const tabButtons = document.querySelectorAll('.ide-tab');
    const tabContent = document.querySelector('.ide-tab-content');
    let currentProblem = null;

    if (searchForm && searchInput && tabButtons.length && tabContent) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (!query) return;
            fetch(`/api/problem_search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        tabContent.textContent = 'Problema nu a fost găsită!';
                        currentProblem = null;
                        return;
                    }
                    currentProblem = data;
                    // Show statement by default
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    tabButtons[0].classList.add('active');
                    tabContent.textContent = data.statement || 'Fără enunț.';
                })
                .catch(() => {
                    tabContent.textContent = 'Eroare la căutare!';
                    currentProblem = null;
                });
        });
        // Tab switching logic
        tabButtons.forEach((btn, idx) => {
            btn.addEventListener('click', function() {
                tabButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (!currentProblem) {
                    tabContent.textContent = 'Aici va fi enunțul problemei...';
                    return;
                }
                if (idx === 0) {
                    tabContent.textContent = currentProblem.statement || 'Fără enunț.';
                } else if (idx === 1) {
                    // Date de intrare și ieșire
                    let date = '';
                    if (currentProblem.input_description) date += currentProblem.input_description + '\n';
                    if (currentProblem.output_description) date += currentProblem.output_description;
                    tabContent.textContent = date.trim() || 'Fără date de intrare/ieșire.';
                } else if (idx === 2) {
                    // Restricții ca listă neordonată (bullets), chiar și pentru una singură
                    if (currentProblem.constraints) {
                        const lines = currentProblem.constraints.split('\n').filter(l => l.trim());
                        let ul = document.createElement('ul');
                        lines.forEach(line => {
                            let li = document.createElement('li');
                            li.textContent = line;
                            ul.appendChild(li);
                        });
                        tabContent.innerHTML = '';
                        tabContent.appendChild(ul);
                    } else {
                        tabContent.textContent = 'Fără restricții.';
                    }
                } else if (idx === 3) {
                    // Exemplu cu etichete colorate și font mai mic pentru fișiere/intrare/ieșire
                    let ex = '';
                    let inputLabel = currentProblem.example_input_name && currentProblem.example_input_name !== 'consola'
                        ? currentProblem.example_input_name : 'Intrare';
                    let outputLabel = currentProblem.example_output_name && currentProblem.example_output_name !== 'consola'
                        ? currentProblem.example_output_name : 'Ieșire';
                    const labelStyle = 'color:#1976d2;font-size:0.95em;font-weight:500;';
                    if (currentProblem.example_input) {
                        ex += `<span style="${labelStyle}">${inputLabel}</span><br>` + currentProblem.example_input + '<br>';
                    }
                    if (currentProblem.example_output) {
                        ex += `<span style="${labelStyle}">${outputLabel}</span><br>` + currentProblem.example_output + '<br>';
                    }
                    tabContent.innerHTML = `<div>${ex.trim() || 'Fără exemplu.'}</div>`;
                }
            });
        });
    }

    // Chat sidebar toggle logic (Asistent AI)
    const chatSidebar = document.getElementById('ide-chat-sidebar');
    const closeChatBtn = document.getElementById('ide-close-chat-btn');
    const chatToggleBtn = document.getElementById('ide-chat-toggle-btn');
    if (closeChatBtn && chatSidebar && chatToggleBtn) {
        closeChatBtn.onclick = function() {
            chatSidebar.classList.add('closed');
            setTimeout(() => { chatToggleBtn.style.display = 'block'; }, 350);
        };
        chatToggleBtn.onclick = function() {
            chatSidebar.classList.remove('closed');
            chatToggleBtn.style.display = 'none';
        };
    }

    // Sidebar toggle logic ca pe index
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    if (sidebar && sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
});