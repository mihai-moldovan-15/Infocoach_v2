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
function addMessage(content, isUser = false) {
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
    
    const form = document.getElementById('chat-form');
    const formData = new FormData(form);
    
    // Add user message to chat immediately
    const userInput = document.getElementById('user-input').value;
    addMessage(userInput, true);
    
    // Clear input field
    document.getElementById('user-input').value = '';
    
    // Show waiting message
    startWaitMessages();
    
    // Send request
    fetch('/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        // Hide waiting message regardless of success/failure
        document.getElementById('wait-message').style.display = 'none';
        if (window.intervalId) {
            clearInterval(window.intervalId);
            window.intervalId = null;
        }

        // Create a temporary div to parse the HTML response
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Find the assistant's message content div in the parsed HTML response
        // This should contain the formatted response including code blocks
        const assistantMessageContentDiv = doc.querySelector('.message.assistant .message-content');
        
        if (assistantMessageContentDiv) {
            // Get ONLY the innerHTML of the message content div from the response
            const assistantMessageContentHTML = assistantMessageContentDiv.innerHTML;
            
            // Add the assistant message to the chat using the extracted content
            addMessage(assistantMessageContentHTML, false);
        } else {
             console.error("Could not find assistant message content in response.");
             // Optionally add a generic error message to the chat
             addMessage("A apărut o problemă la preluarea răspunsului.", false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('A apărut o eroare la trimiterea mesajului. Te rugăm să încerci din nou.');
        document.getElementById('wait-message').style.display = 'none';
        if (window.intervalId) {
            clearInterval(window.intervalId);
            window.intervalId = null;
        }
    });
    
    return false;
}

// Feedback handling
function submitFeedback(button, feedback) {
    const messageDiv = button.closest('.message.assistant');
    const messageContent = messageDiv.querySelector('.message-content').innerHTML;
    const feedbackMessage = messageDiv.querySelector('#feedback-message');
    
    // Get the user input from the previous message
    const userMessage = messageDiv.previousElementSibling;
    let userInput = '';
    if (userMessage && userMessage.classList.contains('user')) {
        // Extract text after "Tu:" and any <br> tags
        const content = userMessage.innerHTML;
        const match = content.match(/<b>Tu:<\/b><br>(.*)/);
        if (match) {
            userInput = match[1].trim();
        }
    }
    
    // Get the class from the select element
    const clasa = document.getElementById('clasa').value;
    
    // Disable feedback buttons
    const buttons = messageDiv.querySelectorAll('.feedback-btn');
    buttons.forEach(btn => btn.disabled = true);
    
    // Prepare the data
    const formData = new URLSearchParams();
    formData.append('user_input', userInput);
    formData.append('ai_response', messageContent);
    formData.append('clasa', clasa);
    formData.append('feedback', feedback);
    
    // Log the data being sent
    console.log('Sending feedback data:', {
        userInput,
        clasa,
        feedback,
        messageContentLength: messageContent.length
    });
    
    // Send feedback to server
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
        if (data.error) {
            console.error('Server error:', data.error);
            feedbackMessage.textContent = 'Eroare la salvarea feedback-ului: ' + data.error;
            feedbackMessage.style.color = '#dc3545';
            // Re-enable buttons on error
            buttons.forEach(btn => btn.disabled = false);
        } else {
            feedbackMessage.textContent = 'Mulțumim pentru feedback!';
            feedbackMessage.style.color = '#28a745';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        feedbackMessage.textContent = 'Eroare la salvarea feedback-ului. Te rugăm să încerci din nou.';
        feedbackMessage.style.color = '#dc3545';
        // Re-enable buttons on error
        buttons.forEach(btn => btn.disabled = false);
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