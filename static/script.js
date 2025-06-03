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
});