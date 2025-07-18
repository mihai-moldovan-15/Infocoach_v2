// Scroll automat la ultimul mesaj
function scrollToBottom() {
    var chat = document.getElementById("chat-messages");
    if (chat) chat.scrollTop = chat.scrollHeight;
}

// Variabile globale pentru problem solver
let currentProblem = null;
window.InfoCoachApp = window.InfoCoachApp || {};
window.InfoCoachApp.currentProblemId = null;
window.InfoCoachApp.currentProblem = null;

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
        // Get clasa from the form
        const clasa = document.querySelector('input[name="clasa"]')?.value || '9';
        // Folosește marked pentru a parsa Markdown-ul din răspunsul AI
        messageDiv.innerHTML = `
            <b>InfoCoach:</b>
            <div class="message-content">${window.marked ? marked.parse(content) : content}</div>
            <input type="hidden" class="user-input-hidden" value="${userInput.replace(/"/g, '&quot;')}">
            <input type="hidden" class="clasa-hidden" value="${clasa}">
            <div class="feedback-form">
                <span>Acest răspuns a fost util?</span>
                <button onclick="submitFeedback(this, 'da')" class="feedback-btn">Da</button>
                <button onclick="openNegativeFeedbackModal(this)" class="feedback-btn">Nu</button>
                <span id="feedback-message"></span>
            </div>
        `;
        // Adaugă modalul pentru feedback negativ dacă nu există deja
        if (!document.getElementById('negative-feedback-modal')) {
            const modal = document.createElement('div');
            modal.id = 'negative-feedback-modal';
            modal.className = 'custom-modal';
            modal.style.display = 'none';
            modal.innerHTML = `
              <div class="custom-modal-content">
                <div class="custom-modal-message">Ce nu a funcționat sau ce ai fi vrut să primești?</div>
                <textarea id="negative-feedback-text" rows="4" style="width:100%;margin:12px 0;"></textarea>
                <div class="custom-modal-actions">
                  <button onclick="sendNegativeFeedback()" class="feedback-btn">Trimite</button>
                  <button onclick="closeNegativeFeedbackModal()" class="feedback-btn">Renunță</button>
                </div>
              </div>
            `;
            document.body.appendChild(modal);
        }
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
    const clasa = form.querySelector('input[name="clasa"]')?.value || '9';
    
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
    // Get AI response from original text, fallback to innerHTML
    const aiResponseOriginal = messageDiv.querySelector('.ai-response-original');
    let messageContent = aiResponseOriginal ? aiResponseOriginal.value : messageContentDiv.innerHTML;
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
    formData.append('tip_feedback', feedback === 'da' ? 'pozitiv' : 'negativ');
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

function openNegativeFeedbackModal(button) {
    document.getElementById('negative-feedback-modal').style.display = 'flex';
    window._negativeFeedbackBtn = button;
}
function closeNegativeFeedbackModal() {
    document.getElementById('negative-feedback-modal').style.display = 'none';
    window._negativeFeedbackBtn = null;
    document.getElementById('negative-feedback-text').value = '';
}
function sendNegativeFeedback() {
    const textarea = document.getElementById('negative-feedback-text');
    const text = textarea.value.trim();
    if (!text) { textarea.focus(); return; }
    const button = window._negativeFeedbackBtn;
    closeNegativeFeedbackModal();
    const messageDiv = button.closest('.message.assistant');
    const messageContentDiv = messageDiv.querySelector('.message-content');
    // Get AI response from original text, fallback to innerHTML
    const aiResponseOriginal = messageDiv.querySelector('.ai-response-original');
    let messageContent = aiResponseOriginal ? aiResponseOriginal.value : messageContentDiv.innerHTML;
    const userInputHidden = messageDiv.querySelector('.user-input-hidden');
    let userInput = userInputHidden ? userInputHidden.value : '';
    if (userInput && userInput.startsWith('"') && userInput.endsWith('"')) {
        try { userInput = JSON.parse(userInput); } catch (e) {}
    }
    const clasaHidden = messageDiv.querySelector('.clasa-hidden');
    let clasa = clasaHidden ? clasaHidden.value : (document.getElementById('clasa') ? document.getElementById('clasa').value : '9');
    const feedbackForm = messageDiv.querySelector('.feedback-form');
    const formData = new URLSearchParams();
    formData.append('user_input', userInput);
    formData.append('ai_response', messageContent);
    formData.append('clasa', clasa);
    formData.append('feedback', 'nu');
    formData.append('feedback_text', text);
    formData.append('tip_feedback', 'negativ');
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

// InfoPaste integration
function checkInfoPasteCode() {
    const infopasteCode = localStorage.getItem('infopaste_code');
    const infopasteTitle = localStorage.getItem('infopaste_title');
    
    if (infopasteCode && window.ideMonaco) {
        // Set the code in the editor
        window.ideMonaco.setValue(infopasteCode);
        
        // Try to find and select the problem based on title
        if (infopasteTitle && infopasteTitle !== 'Paste fără problemă asociată') {
            const searchInput = document.getElementById('problem-search');
            if (searchInput) {
                // Set the search input value
                searchInput.value = infopasteTitle;
                
                // Trigger the input event to show suggestions
                const inputEvent = new Event('input', { bubbles: true, cancelable: true });
                searchInput.dispatchEvent(inputEvent);
                
                // Wait a bit for suggestions to load, then select the first one
                setTimeout(() => {
                    const suggestionsList = document.getElementById('problem-suggestions');
                    if (suggestionsList && suggestionsList.children.length > 0) {
                        // Select the first suggestion
                        const firstSuggestion = suggestionsList.children[0];
                        if (firstSuggestion.onclick) {
                            firstSuggestion.onclick();
                        }
                    }
                }, 300);
            }
        }
        
        // Clear localStorage
        localStorage.removeItem('infopaste_code');
        localStorage.removeItem('infopaste_title');
        
        // Show success message
        if (infopasteTitle) {
            showSuccess(`Cod din InfoPaste încărcat: ${infopasteTitle}`);
        } else {
            showSuccess('Cod din InfoPaste încărcat cu succes!');
        }
    }
}

// Monaco Editor init
window.addEventListener('DOMContentLoaded', function() {
  const savedCode = localStorage.getItem('ide_code');
  const defaultCode = '#include <iostream>\nusing namespace std;\n\nint main() {\n    // scrie codul aici\n    return 0;\n}';
  window.require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
  window.require(['vs/editor/editor.main'], function() {
    // Funcție pentru determinarea temei Monaco
    function getMonacoTheme() {
        const theme = document.documentElement.getAttribute('data-theme');
        return theme === 'dark' ? 'vs-dark' : 'vs';
    }
    
    window.ideMonaco = monaco.editor.create(document.getElementById('ide-code-editor'), {
      value: savedCode !== null ? savedCode : defaultCode,
      language: 'cpp',
      theme: getMonacoTheme(),
      fontSize: 15,
      minimap: { enabled: false },
      automaticLayout: true,
      lineNumbers: 'on',
      wordWrap: 'on',
      scrollBeyondLastLine: false,
      roundedSelection: false,
      scrollbar: { vertical: 'auto', horizontal: 'auto' }
    });
    
    // Sincronizare tema Monaco cu tema site-ului
    const observer = new MutationObserver(() => {
        if (window.ideMonaco) {
            monaco.editor.setTheme(getMonacoTheme());
        }
    });
    observer.observe(document.documentElement, { 
        attributes: true, 
        attributeFilter: ['data-theme'] 
    });
    window.ideMonaco.onDidChangeModelContent(function() {
      localStorage.setItem('ide_code', window.ideMonaco.getValue());
    });
    
    // Check for InfoPaste code after editor is initialized
    checkInfoPasteCode();
  });
});

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
    const generateExampleBtn = document.getElementById('ide-generate-example-files-btn');

    if (searchForm && searchInput && tabButtons.length && tabContent) {
        // Dezactivez tab-urile la început
        tabButtons.forEach(btn => btn.disabled = true);
        if (generateExampleBtn) generateExampleBtn.style.display = 'none';
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
                        window.currentProblemId = null;
                        console.log('Search error - reset currentProblemId to null');
                        tabButtons.forEach(btn => btn.disabled = true);
                        if (generateExampleBtn) generateExampleBtn.style.display = 'none';
                        return;
                    }
                    currentProblem = data;
                    window.currentProblemId = data.id;
                    window.InfoCoachApp.currentProblemId = data.id;
                    window.InfoCoachApp.currentProblem = data;
                    console.log('Search success - set currentProblemId to:', window.currentProblemId);
                    console.log('Data received:', data);
                    tabButtons.forEach(btn => btn.disabled = false);
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    tabButtons[0].classList.add('active');
                    tabContent.textContent = data.statement || 'Fără enunț.';
                    // Afișează butonul de generare fișiere dacă există nume de fișier input/output
                    if (generateExampleBtn) {
                        const hasInputFile = data.example_input_name && data.example_input_name !== 'consola';
                        const hasOutputFile = data.example_output_name && data.example_output_name !== 'consola';
                        if (hasInputFile || hasOutputFile) {
                            generateExampleBtn.style.display = 'inline-block';
                        } else {
                            generateExampleBtn.style.display = 'none';
                        }
                    }
                })
                .catch(() => {
                    tabContent.textContent = 'Eroare la căutare!';
                    currentProblem = null;
                    window.currentProblemId = null;
                    tabButtons.forEach(btn => btn.disabled = true);
                    if (generateExampleBtn) generateExampleBtn.style.display = 'none';
                });
        });
        // Tab switching logic
        tabButtons.forEach((btn, idx) => {
            btn.addEventListener('click', function() {
                if (btn.disabled) return;
                tabButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (!currentProblem) {
                    tabContent.textContent = 'Aici va fi enunțul problemei...';
                    return;
                }
                if (idx === 0) {
                    tabContent.textContent = currentProblem.statement || 'Fără enunț.';
                } else if (idx === 1) {
                    let date = '';
                    if (currentProblem.input_description) date += currentProblem.input_description + '\n';
                    if (currentProblem.output_description) date += currentProblem.output_description;
                    if (date.trim()) {
                        tabContent.innerHTML = `<div style='white-space:pre-line;'>${highlightFilenames(date.trim())}</div>`;
                    } else {
                        tabContent.textContent = 'Fără date de intrare/ieșire.';
                    }
                } else if (idx === 2) {
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
                    let limHtml = '';
                    if (currentProblem.time_limit || currentProblem.memory_limit) {
                        if (currentProblem.time_limit) limHtml += `<div><b>Limită timp:</b> ${currentProblem.time_limit}</div>`;
                        if (currentProblem.memory_limit) limHtml += `<div><b>Limită memorie:</b> ${currentProblem.memory_limit}</div>`;
                    } else {
                        limHtml = 'Nu există limite definite pentru această problemă.';
                    }
                    tabContent.innerHTML = limHtml;
                } else if (idx === 4) {
                    let ex = '';
                    const badgeStyle = 'display:inline-block;background:#dbeafe;color:#2563eb;font-size:0.89em;font-weight:600;padding:1.5px 8px;border-radius:5px;margin-bottom:4px;margin-right:6px;border:1px solid #b6d0fa;';
                    const forceConsoleBadges = currentProblem && currentProblem.id == 11;
                    const isConsoleInput = currentProblem.example_input_name === 'consola';
                    const isConsoleOutput = currentProblem.example_output_name === 'consola';
                    const isComplete = !currentProblem.problem_type || currentProblem.problem_type === 'complete';
                    let inputLabel = (forceConsoleBadges || (isConsoleInput && isComplete)) ? 'Intrare' : (currentProblem.example_input_name || 'Intrare');
                    let outputLabel = (forceConsoleBadges || (isConsoleOutput && isComplete)) ? 'Ieșire' : (currentProblem.example_output_name || 'Ieșire');
                    let explanation = currentProblem.example_explanation || '';
                    let output = currentProblem.example_output || '';
                    // Dacă nu există explanation, dar outputul conține Explicații, taie și mută
                    if (!explanation && output) {
                        let idxExp = output.toLowerCase().indexOf('explica');
                        if (idxExp !== -1) {
                            explanation = output.substring(idxExp).trim();
                            output = output.substring(0, idxExp).trim();
                        }
                    }
                    if (currentProblem.example_input) {
                        ex += `<div style=\"margin-bottom:6px;\">`;
                        ex += `<span style=\"${badgeStyle}\">${inputLabel}</span>`;
                        ex += `<pre style=\"background:var(--bg-tertiary);color:var(--text-primary);padding:8px 12px;border-radius:6px;white-space:pre-wrap;\">${currentProblem.example_input}</pre></div>`;
                    }
                    if (output) {
                        ex += `<div style=\"margin-bottom:6px;\">`;
                        ex += `<span style=\"${badgeStyle}\">${outputLabel}</span>`;
                        ex += `<pre style=\"background:var(--bg-tertiary);color:var(--text-primary);padding:8px 12px;border-radius:6px;white-space:pre-wrap;\">${output}</pre></div>`;
                    }
                    if (explanation) {
                        explanation = explanation.replace(/^\s*Explica(ț|t)ii?:?\s*/i, '');
                        explanation = explanation.replace(/\n+/g, ' ');
                        explanation = explanation.replace(/\s{2,}/g, ' ');
                        explanation = explanation.trim();
                        ex += `<div style=\"margin-top:8px;\"><span style=\"color:var(--accent-primary);font-size:0.95em;font-weight:500;\">Explicație</span><div style=\"background:var(--bg-secondary);color:var(--text-primary);padding:10px 14px;border-radius:6px;white-space:normal;margin-top:2px;\">${explanation}</div></div>`;
                    }
                    tabContent.innerHTML = `<div>${highlightFilenames(ex.trim() || 'Fără exemplu.')}</div>`;
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
    const navBrand = document.getElementById('nav-brand');
    if (sidebar && sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            sidebar.classList.add('transitioning');
            sidebar.classList.toggle('collapsed');
            if (sidebar.classList.contains('collapsed')) {
                navBrand && navBrand.classList.remove('shifted');
            } else {
                navBrand && navBrand.classList.add('shifted');
            }
            setTimeout(() => {
                sidebar.classList.remove('transitioning');
            }, 400);
        });
    }

    // === Gestionare fișiere suplimentare (input/output) ===
    const filesSection = document.getElementById('ide-files-section');
    const filesTabs = document.getElementById('ide-files-tabs');
    const addFileBtn = document.getElementById('ide-add-file-btn');
    const addFileForm = document.getElementById('ide-add-file-form');
    const newFileName = document.getElementById('ide-new-file-name');
    const newFileContent = document.getElementById('ide-new-file-content');
    const cancelAddFile = document.getElementById('ide-cancel-add-file');
    const filesEditors = document.getElementById('ide-files-editors');

    let userFiles = JSON.parse(localStorage.getItem('ide_user_files') || '[]');
    let activeFileIdx = null;

    function updateCustomInputVisibility() {
        const customInputArea = document.querySelector('.ide-custom-test');
        if (!customInputArea) return;
        const hasInFile = userFiles.some(f => f.name && f.name.endsWith('.in'));
        if (hasInFile) {
            customInputArea.classList.add('hide');
        } else {
            customInputArea.classList.remove('hide');
        }
    }

    // Modal custom pentru confirmare ștergere fișier
    function showDeleteFileModal(message) {
        return new Promise((resolve) => {
            let modal = document.getElementById('custom-delete-modal');
            let msg = document.getElementById('custom-delete-message');
            let okBtn = document.getElementById('custom-delete-ok');
            let cancelBtn = document.getElementById('custom-delete-cancel');
            if (!modal) {
                // Creează modalul dacă nu există
                modal = document.createElement('div');
                modal.id = 'custom-delete-modal';
                modal.className = 'custom-modal';
                modal.style.display = 'none';
                modal.innerHTML = `
                  <div class="custom-modal-content">
                    <div class="custom-modal-message" id="custom-delete-message"></div>
                    <div class="custom-modal-actions">
                      <button id="custom-delete-ok" class="ide-btn-run">Șterge</button>
                      <button id="custom-delete-cancel" class="ide-btn-reset">Renunță</button>
                    </div>
                  </div>
                `;
                document.body.appendChild(modal);
                msg = document.getElementById('custom-delete-message');
                okBtn = document.getElementById('custom-delete-ok');
                cancelBtn = document.getElementById('custom-delete-cancel');
            }
            msg.innerHTML = message;
            modal.style.display = 'flex';
            okBtn.onclick = () => { modal.style.display = 'none'; resolve(true); };
            cancelBtn.onclick = () => { modal.style.display = 'none'; resolve(false); };
        });
    }

    function renderFilesTabs() {
        filesTabs.innerHTML = '';
        userFiles.forEach((file, idx) => {
            const tab = document.createElement('button');
            tab.textContent = file.name;
            tab.className = 'ide-file-tab fade-in';
            tab.style = 'background:#e6f0fa;color:#1976d2;border:none;border-radius:6px;padding:5px 14px;font-size:0.98em;font-weight:500;cursor:pointer;transition:opacity 0.4s,transform 0.4s;opacity:0;transform:translateY(-8px);';
            if (activeFileIdx === idx) {
                tab.style.background = '#fff';
                tab.style.color = '#0074d9';
                tab.style.fontWeight = '600';
            }
            tab.onclick = () => {
                if (activeFileIdx === idx) {
                    activeFileIdx = null;
                } else {
                    activeFileIdx = idx;
                }
                renderFilesTabs();
                renderFileEditor();
                updateCustomInputVisibility();
            };
            // Buton ștergere
            const delBtn = document.createElement('span');
            delBtn.textContent = '×';
            delBtn.title = 'Șterge fișier';
            delBtn.style = 'margin-left:6px;color:#d32f2f;font-weight:700;cursor:pointer;';
            delBtn.onclick = async (e) => {
                e.stopPropagation();
                const proceed = await showDeleteFileModal('Sigur vrei să ștergi acest fișier?');
                if (!proceed) return;
                userFiles.splice(idx, 1);
                if (activeFileIdx === idx) activeFileIdx = null;
                localStorage.setItem('ide_user_files', JSON.stringify(userFiles));
                renderFilesTabs();
                renderFileEditor();
                updateCustomInputVisibility();
            };
            tab.appendChild(delBtn);
            filesTabs.appendChild(tab);
            // Trigger fade-in
            setTimeout(() => {
                tab.style.opacity = '1';
                tab.style.transform = 'translateY(0)';
            }, 10);
        });
    }
    function renderFileEditor() {
        filesEditors.innerHTML = '';
        if (activeFileIdx === null || userFiles.length === 0) return;
        const file = userFiles[activeFileIdx];
        // Monaco Editor pentru fișiere suplimentare
        const editorDiv = document.createElement('div');
        editorDiv.style = 'width:100%;min-height:80px;height:180px;border-radius:6px;border:1px solid #bbb;background:#fff;margin-bottom:8px;transition:opacity 0.4s,transform 0.4s;opacity:0;transform:translateY(-10px);';
        editorDiv.id = 'ide-file-monaco-editor';
        filesEditors.appendChild(editorDiv);
        setTimeout(() => {
            editorDiv.style.opacity = '1';
            editorDiv.style.transform = 'translateY(0)';
        }, 10);
        // Determină limbajul după extensie
        let lang = 'plaintext';
        if (file.name.endsWith('.cpp') || file.name.endsWith('.cc') || file.name.endsWith('.cxx')) lang = 'cpp';
        else if (file.name.endsWith('.py')) lang = 'python';
        else if (file.name.endsWith('.txt') || file.name.endsWith('.in') || file.name.endsWith('.out')) lang = 'plaintext';
        // Inițializează Monaco
        window.require(['vs/editor/editor.main'], function() {
            if (window.ideFileMonaco) {
                window.ideFileMonaco.dispose();
            }
            window.ideFileMonaco = monaco.editor.create(editorDiv, {
                value: file.content,
                language: lang,
                theme: getMonacoTheme(),
                fontSize: 15,
                minimap: { enabled: false },
                automaticLayout: true,
                lineNumbers: 'off',
                wordWrap: 'on',
                scrollBeyondLastLine: false,
                roundedSelection: false,
                scrollbar: { vertical: 'auto', horizontal: 'auto' }
            });
            window.ideFileMonaco.onDidChangeModelContent(function() {
                userFiles[activeFileIdx].content = window.ideFileMonaco.getValue();
                localStorage.setItem('ide_user_files', JSON.stringify(userFiles));
            });
        });
    }
    addFileBtn.onclick = function() {
        addFileForm.style.display = 'block';
        addFileBtn.style.display = 'none';
        newFileName.value = '';
        newFileContent.value = '';
    };
    cancelAddFile.onclick = function() {
        addFileForm.style.display = 'none';
        addFileBtn.style.display = 'inline-block';
    };
    addFileForm.onsubmit = function(e) {
        e.preventDefault();
        const name = newFileName.value.trim();
        if (!name || userFiles.some(f => f.name === name)) {
            alert('Numele fișierului este gol sau există deja!');
            return;
        }
        userFiles.push({ name, content: newFileContent.value });
        localStorage.setItem('ide_user_files', JSON.stringify(userFiles));
        addFileForm.style.display = 'none';
        addFileBtn.style.display = 'inline-block';
        activeFileIdx = userFiles.length - 1;
        renderFilesTabs();
        renderFileEditor();
        updateCustomInputVisibility();
    };
    // Inițializare la load
    renderFilesTabs();
    renderFileEditor();
    updateCustomInputVisibility();

    if (generateExampleBtn) {
        generateExampleBtn.onclick = function() {
            if (!currentProblem) return;
            let files = JSON.parse(localStorage.getItem('ide_user_files') || '[]');
            // Adaugă fișier de input dacă nu există deja
            if (currentProblem.example_input_name && currentProblem.example_input_name !== 'consola') {
                if (!files.some(f => f.name === currentProblem.example_input_name)) {
                    files.push({ name: currentProblem.example_input_name, content: currentProblem.example_input || '' });
                }
            }
            // NU mai adăuga fișier de output!
            localStorage.setItem('ide_user_files', JSON.stringify(files));
            userFiles = files;
            activeFileIdx = null;
            renderFilesTabs();
            renderFileEditor();
            updateCustomInputVisibility();
        };
    }

    // Butonul de resetare cod și fișiere
    const resetBtn = document.getElementById('ide-reset-code');
    if (resetBtn) {
        resetBtn.onclick = function(e) {
            e.preventDefault();
            // Cod C++ basic (hello world)
            const helloCode = '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, world!" << endl;\n    return 0;\n}';
            if (window.ideMonaco) {
                window.ideMonaco.setValue(helloCode);
            }
            localStorage.setItem('ide_code', helloCode);
            // Șterge fișierele suplimentare
            localStorage.removeItem('ide_user_files');
            userFiles = [];
            activeFileIdx = null;
            renderFilesTabs();
            renderFileEditor();
            // Golește inputul de test personalizat
            const customInput = document.querySelector('.ide-custom-test');
            if (customInput) customInput.value = '';
        };
    }

    function checkFileVsConsoleWarning(code) {
        // Verifică dacă există fișier .in în userFiles
        const hasInFile = userFiles.some(f => f.name && f.name.endsWith('.in'));
        // Verifică dacă codul folosește doar cin/cout
        const usesCinCout = /\bcin\b/.test(code) || /\bcout\b/.test(code);
        const usesFiles = /ifstream\b/.test(code) || /ofstream\b/.test(code) ||
            (hasInFile && code.includes('.in'));
        if (hasInFile && usesCinCout && !usesFiles) {
            return true;
        }
        return false;
    }

    // Modal custom pentru avertizare
    function showCustomWarning(message) {
        return new Promise((resolve) => {
            const modal = document.getElementById('custom-warning-modal');
            const msg = document.getElementById('custom-warning-message');
            const okBtn = document.getElementById('custom-modal-ok');
            const cancelBtn = document.getElementById('custom-modal-cancel');
            msg.innerHTML = message;
            modal.style.display = 'flex';
            okBtn.onclick = () => { modal.style.display = 'none'; resolve(true); };
            cancelBtn.onclick = () => { modal.style.display = 'none'; resolve(false); };
        });
    }

    // Butonul de rulare cod (Rulează)
    const runBtn = document.getElementById('ide-run-code');
    const errorLog = document.getElementById('ide-error-log');
    if (runBtn && errorLog) {
        runBtn.onclick = async function(e) {
            e.preventDefault();
            errorLog.textContent = 'Rulează codul...';
            errorLog.style.color = '#1976d2';
            // Codul principal
            const code = window.ideMonaco ? window.ideMonaco.getValue() : '';
            // Fișiere suplimentare
            let files = JSON.parse(localStorage.getItem('ide_user_files') || '[]');
            // Input de test personalizat
            const customInput = document.querySelector('.ide-custom-test')?.value || '';
            // Avertizare dacă problema necesită fișiere dar codul folosește doar cin/cout
            if (checkFileVsConsoleWarning(code)) {
                const proceed = await showCustomWarning(
                    `<strong>Atenție!</strong> Ai adăugat fișier(e) de input, dar codul tău folosește doar tastatura (<code>cin</code>/<code>cout</code>).<br>
                    Pentru a citi din fișier, trebuie să folosești <code>ifstream</code>.<br><br>
                    <span style='color:#1976d2;'>Vrei să continui oricum?</span>`
                );
                if (!proceed) {
                    errorLog.textContent = 'Execuția a fost anulată de utilizator.';
                    errorLog.style.color = '#d32f2f';
                    return;
                }
            }
            // Trimite request la backend
            try {
                const resp = await fetch('/api/run_code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code, files, custom_input: customInput })
                });
                const data = await resp.json();
                if (data.success) {
                    if (data.error) {
                        errorLog.textContent = data.error;
                        errorLog.style.color = '#d32f2f';
                    } else {
                        errorLog.textContent = data.output || '(fără output)';
                        errorLog.style.color = '#222';
                    }
                } else {
                    errorLog.textContent = data.error || 'Eroare necunoscută la execuție.';
                    errorLog.style.color = '#d32f2f';
                }
            } catch (err) {
                errorLog.textContent = 'Eroare la comunicarea cu serverul.';
                errorLog.style.color = '#d32f2f';
            }
        };
    }

    function sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        if (!message) return;

        const currentConversationId = document.getElementById('current-conversation-id').value;
        if (!currentConversationId) {
            alert('Vă rugăm să selectați o conversație sau să creați una nouă.');
            return;
        }

        // Adaugă mesajul userului în chat
        const chatMessages = document.getElementById('chat-messages');
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user-message';
        userMessageDiv.textContent = message;
        chatMessages.appendChild(userMessageDiv);

        // Trimite mesajul la backend
        fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                // Adaugă răspunsul AI în chat
                const aiMessageDiv = document.createElement('div');
                aiMessageDiv.className = 'message assistant-message';
                aiMessageDiv.textContent = data.response;
                chatMessages.appendChild(aiMessageDiv);
                
                // Scroll la ultimul mesaj
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('A apărut o eroare la trimiterea mesajului.');
        });

        // Curăță input-ul
        messageInput.value = '';
    }

    // Asistent AI Modern - UI only
    const aiSidebar = document.getElementById('ai-assistant-sidebar');
    const aiOpenBtn = document.getElementById('ai-assistant-open-btn');
    const aiCloseBtn = document.getElementById('ai-assistant-close-btn');
    const aiForm = document.getElementById('ai-assistant-form');
    const aiInput = document.getElementById('ai-assistant-input');
    const aiMessages = document.getElementById('ai-assistant-messages');

    if (aiSidebar && aiOpenBtn && aiCloseBtn) {
        aiOpenBtn.onclick = function() {
            aiSidebar.classList.add('open');
            aiOpenBtn.style.display = 'none';
        };
        aiCloseBtn.onclick = function() {
            aiSidebar.classList.remove('open');
            aiOpenBtn.style.display = '';
        };
    }
    if (aiForm && aiInput && aiMessages) {
        aiForm.onsubmit = function(e) {
            e.preventDefault();
            const msg = aiInput.value.trim();
            if (!msg) return;
            // Citește conținutul tuturor tab-urilor
            const tabContents = document.querySelectorAll('.ide-tab-content, .ide-tab-content > div');
            let enunt = '', date = '', restrictii = '', limite = '', exemplu = '';
            // Caută tab-urile după butoane
            const tabButtons = document.querySelectorAll('.ide-tab');
            tabButtons.forEach((btn, idx) => {
                const tabName = btn.textContent.trim().toLowerCase();
                let content = '';
                // Caută conținutul asociat tab-ului
                if (tabContents[idx]) {
                    content = tabContents[idx].textContent.trim();
                } else if (tabContents.length === 1) {
                    // fallback: totul e în același div
                    content = tabContents[0].textContent.trim();
                }
                if (tabName === 'enunț') enunt = content;
                else if (tabName === 'date') date = content;
                else if (tabName === 'restricții') restrictii = content;
                else if (tabName === 'limite') limite = content;
                else if (tabName === 'exemplu') exemplu = content;
            });
            let cod = '';
            if (window.ideMonaco) cod = window.ideMonaco.getValue();
            // Adaugă mesajul userului în UI
            const userDiv = document.createElement('div');
            userDiv.className = 'ai-assistant-message user';
            userDiv.textContent = msg;
            aiMessages.appendChild(userDiv);
            aiInput.value = '';
            aiMessages.scrollTop = aiMessages.scrollHeight;
            // Trimite mesajul la backend
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'ai-assistant-message assistant';
            loadingDiv.textContent = 'InfoCoach scrie...';
            aiMessages.appendChild(loadingDiv);
            aiMessages.scrollTop = aiMessages.scrollHeight;
            fetch('/ai_assistant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: msg,
                    enunt: enunt,
                    date: date,
                    restrictii: restrictii,
                    limite: limite,
                    exemplu: exemplu,
                    code: cod
                })
            })
            .then(res => res.json())
            .then(data => {
                loadingDiv.remove();
                const aiDiv = document.createElement('div');
                aiDiv.className = 'ai-assistant-message assistant';
                aiDiv.textContent = data.response || (data.error ? data.error : 'Eroare la răspunsul AI.');
                aiMessages.appendChild(aiDiv);
                aiMessages.scrollTop = aiMessages.scrollHeight;
            })
            .catch(() => {
                loadingDiv.remove();
                const aiDiv = document.createElement('div');
                aiDiv.className = 'ai-assistant-message assistant';
                aiDiv.textContent = 'Eroare la comunicarea cu serverul.';
                aiMessages.appendChild(aiDiv);
                aiMessages.scrollTop = aiMessages.scrollHeight;
            });
        };
    }

    // Problem search logic for problem_solver page
    const problemSearchInput = document.getElementById('problem-search');
    const problemSuggestionsList = document.getElementById('problem-suggestions');
    if (problemSearchInput && problemSuggestionsList) {
        let suggestions = [];
        let selectedIdx = -1;
        function renderSuggestions() {
            problemSuggestionsList.innerHTML = '';
            if (suggestions.length === 0) {
                problemSuggestionsList.classList.remove('show');
                return;
            }
            suggestions.forEach((sug, idx) => {
                const li = document.createElement('li');
                // Compose categories and tags as badges
                let metaBadges = '';
                if (Array.isArray(sug.categories)) {
                    metaBadges += sug.categories.map(cat => `<span class='suggestion-tags'>${cat}</span>`).join(' ');
                }
                if (Array.isArray(sug.tags)) {
                    metaBadges += sug.tags.map(tag => `<span class='suggestion-tags'>${tag}</span>`).join(' ');
                }
                li.innerHTML = `<span class="suggestion-title">${sug.name}</span> ${metaBadges}`;
                if (idx === selectedIdx) li.classList.add('active');
                li.onclick = () => {
                    problemSearchInput.value = sug.name;
                    problemSuggestionsList.classList.remove('show');
                    fetch(`/api/problem_details?id=${sug.id}`)
                        .then(res => res.json())
                        .then(data => {
                            if (!data || data.error) return;
                            currentProblem = data;
                            window.currentProblemId = data.id;
                            window.InfoCoachApp.currentProblemId = data.id;
                            window.InfoCoachApp.currentProblem = data;
                            console.log('Suggestion selected - set currentProblemId to:', window.currentProblemId);
                            console.log('Suggestion data:', data);
                            tabButtons.forEach(btn => btn.disabled = false);
                            updateTabsWithProblem(currentProblem);
                        });
                };
                problemSuggestionsList.appendChild(li);
            });
            problemSuggestionsList.classList.add('show');
        }
        let debounceTimeout = null;
        problemSearchInput.addEventListener('input', function () {
            const query = problemSearchInput.value.trim();
            if (debounceTimeout) clearTimeout(debounceTimeout);
            if (!query) {
                suggestions = [];
                renderSuggestions();
                return;
            }
            debounceTimeout = setTimeout(() => {
                fetch(`/api/problem_search?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        suggestions = data.problems || [];
                        selectedIdx = -1;
                        renderSuggestions();
                    });
            }, 200);
        });
        problemSearchInput.addEventListener('keydown', function (e) {
            if (!suggestions.length) return;
            if (e.key === 'ArrowDown') {
                selectedIdx = (selectedIdx + 1) % suggestions.length;
                renderSuggestions();
                e.preventDefault();
            } else if (e.key === 'ArrowUp') {
                selectedIdx = (selectedIdx - 1 + suggestions.length) % suggestions.length;
                renderSuggestions();
                e.preventDefault();
            } else if (e.key === 'Enter' && selectedIdx >= 0) {
                problemSearchInput.value = suggestions[selectedIdx].name;
                problemSuggestionsList.classList.remove('show');
                fetch(`/api/problem_details?id=${suggestions[selectedIdx].id}`)
                    .then(res => res.json())
                    .then(data => {
                        if (!data || data.error) return;
                        currentProblem = data;
                        tabButtons.forEach(btn => btn.disabled = false);
                        updateTabsWithProblem(currentProblem);
                    });
                e.preventDefault();
            }
        });
        document.addEventListener('click', function (e) {
            if (!problemSearchInput.contains(e.target) && !problemSuggestionsList.contains(e.target)) {
                problemSuggestionsList.classList.remove('show');
            }
        });
    }

    function updateTabsWithProblem(problem) {
        console.log('updateTabsWithProblem called with:', problem);
        if (!problem) return;
        
        // Setează problema globală și ID-ul
        currentProblem = problem;
        window.currentProblemId = problem.id;
        window.InfoCoachApp.currentProblemId = problem.id;
        window.InfoCoachApp.currentProblem = problem;
        console.log('Set currentProblem:', currentProblem);
        console.log('Set currentProblemId:', window.currentProblemId);
        console.log('Set InfoCoachApp.currentProblemId:', window.InfoCoachApp.currentProblemId);
        console.log('Problem ID type:', typeof window.currentProblemId);
        console.log('currentProblemId from InfoCoachApp:', window.InfoCoachApp.currentProblemId);
        console.log('currentProblemId from window:', window.currentProblemId);
        console.log('currentProblem?.id:', currentProblem?.id);
        console.log('currentProblem object keys:', Object.keys(currentProblem || {}));
        console.log('currentProblem full object:', JSON.stringify(currentProblem, null, 2));
        console.log('Final currentProblemId:', problem.id);
        console.log('currentProblem:', problem);
        
        // === ȘTERGE FIȘIERELE SUPLIMENTARE LA SCHIMBAREA PROBLEMEI ===
        localStorage.removeItem('ide_user_files');
        userFiles = [];
        activeFileIdx = null;
        renderFilesTabs();
        renderFileEditor();
        updateCustomInputVisibility();
        // Activează toate tab-urile
        document.querySelectorAll('.ide-tab').forEach(btn => btn.disabled = false);
        // Activează tab-ul Enunț
        document.querySelectorAll('.ide-tab').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.ide-tab')[0].classList.add('active');
        // Populează tab-ul Enunț
        tabContent.textContent = problem.statement || 'Fără enunț.';

        // Detectează tipul problemei și adaptează interfața
        const problemType = problem.problem_type || 'complete';
        const runButton = document.getElementById('ide-run-code');
        const resetButton = document.getElementById('ide-reset-code');
        const completeCodeButton = document.getElementById('ide-complete-code');
        
        // Salvează tipul problemei pentru a fi folosit în alte funcții
        window.currentProblemType = problemType;
        
        if (problemType === 'subprogram') {
            // Pentru probleme de subprogram, păstrează textul 'Rulează'
            if (runButton) {
                runButton.className = 'ide-btn-run';
            }
            // Afișează butonul "Completează codul"
            if (completeCodeButton) {
                completeCodeButton.style.display = 'inline-block';
                // Atașează event listener-ul când butonul devine vizibil
                completeCodeButton.onclick = function() {
                    console.log('Complete code button clicked!');
                    generateCompleteCode();
                };
            }
        } else {
            // Pentru probleme complete, revino la textul normal
            if (runButton) {
                runButton.textContent = 'Rulează';
                runButton.title = 'Rulează codul';
            }
            // Ascunde butonul "Completează codul"
            if (completeCodeButton) {
                completeCodeButton.style.display = 'none';
                // Elimină event listener-ul când butonul devine invizibil
                completeCodeButton.onclick = null;
            }
        }

        // Afișează/ascunde butonul de generare fișier exemplu corect
        const generateExampleBtn = document.getElementById('ide-generate-example-files-btn');
        if (generateExampleBtn) {
            const hasInputFile = problem.example_input_name && problem.example_input_name !== 'consola';
            const hasOutputFile = problem.example_output_name && problem.example_output_name !== 'consola';
            if (hasInputFile || hasOutputFile) {
                generateExampleBtn.style.display = 'inline-block';
            } else {
                generateExampleBtn.style.display = 'none';
            }
        }

        // Elimină orice mesaj informativ de subprogram adăugat dinamic sub editor
        const oldDynamicInfo = document.querySelector('.subprogram-info');
        if (oldDynamicInfo) oldDynamicInfo.remove();

        // Afișează/ascunde mesajul informativ pentru subprogram
        const subInfo = document.getElementById('subprogram-info-message');
        if (problemType === 'subprogram') {
            if (subInfo) subInfo.style.display = 'block';
        } else {
            if (subInfo) subInfo.style.display = 'none';
        }

        // Buton de închidere pentru mesajul informativ
        if (subInfo && !subInfo.querySelector('.close-info-msg')) {
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '&times;';
            closeBtn.className = 'close-info-msg';
            closeBtn.style.cssText = 'position:absolute;top:8px;right:12px;background:none;border:none;font-size:1.5em;color:#1976d2;cursor:pointer;line-height:1;';
            closeBtn.title = 'Închide mesajul';
            closeBtn.onclick = function() {
                subInfo.classList.add('fade-out-info');
                setTimeout(() => { subInfo.style.display = 'none'; subInfo.classList.remove('fade-out-info'); }, 400);
            };
            subInfo.style.position = 'relative';
            subInfo.appendChild(closeBtn);
        }

        // Reatașează event listener-ele pentru tab-uri (Enunț, Date, Restricții, Limite, Exemplu)
        let tabButtons = document.querySelectorAll('.ide-tab');
        for (let i = 0; i < tabButtons.length; i++) {
            const btn = tabButtons[i];
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
        }
        // Refac selecția pentru a avea referințe proaspete
        tabButtons = document.querySelectorAll('.ide-tab');
        // Reatașează event listener-ele corecte
        tabButtons.forEach((btn, idx) => {
            btn.addEventListener('click', function() {
                if (btn.disabled) return;
                tabButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (!currentProblem) {
                    tabContent.textContent = 'Aici va fi enunțul problemei...';
                    return;
                }
                if (idx === 0) {
                    tabContent.textContent = currentProblem.statement || 'Fără enunț.';
                } else if (idx === 1) {
                    let date = '';
                    if (currentProblem.input_description) date += currentProblem.input_description + '\n';
                    if (currentProblem.output_description) date += currentProblem.output_description;
                    if (date.trim()) {
                        tabContent.innerHTML = `<div style='white-space:pre-line;'>${highlightFilenames(date.trim())}</div>`;
                    } else {
                        tabContent.textContent = 'Fără date de intrare/ieșire.';
                    }
                } else if (idx === 2) {
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
                    let limHtml = '';
                    if (currentProblem.time_limit || currentProblem.memory_limit) {
                        if (currentProblem.time_limit) limHtml += `<div><b>Limită timp:</b> ${currentProblem.time_limit}</div>`;
                        if (currentProblem.memory_limit) limHtml += `<div><b>Limită memorie:</b> ${currentProblem.memory_limit}</div>`;
                    } else {
                        limHtml = 'Nu există limite definite pentru această problemă.';
                    }
                    tabContent.innerHTML = limHtml;
                } else if (idx === 4) {
                    let ex = '';
                    const badgeStyle = 'display:inline-block;background:#dbeafe;color:#2563eb;font-size:0.89em;font-weight:600;padding:1.5px 8px;border-radius:5px;margin-bottom:4px;margin-right:6px;border:1px solid #b6d0fa;';
                    const forceConsoleBadges = currentProblem && currentProblem.id == 11;
                    const isConsoleInput = currentProblem.example_input_name === 'consola';
                    const isConsoleOutput = currentProblem.example_output_name === 'consola';
                    const isComplete = !currentProblem.problem_type || currentProblem.problem_type === 'complete';
                    let inputLabel = (forceConsoleBadges || (isConsoleInput && isComplete)) ? 'Intrare' : (currentProblem.example_input_name || 'Intrare');
                    let outputLabel = (forceConsoleBadges || (isConsoleOutput && isComplete)) ? 'Ieșire' : (currentProblem.example_output_name || 'Ieșire');
                    let explanation = currentProblem.example_explanation || '';
                    let output = currentProblem.example_output || '';
                    // Dacă nu există explanation, dar outputul conține Explicații, taie și mută
                    if (!explanation && output) {
                        let idxExp = output.toLowerCase().indexOf('explica');
                        if (idxExp !== -1) {
                            explanation = output.substring(idxExp).trim();
                            output = output.substring(0, idxExp).trim();
                        }
                    }
                    if (currentProblem.example_input) {
                        ex += `<div style=\"margin-bottom:6px;\">`;
                        ex += `<span style=\"${badgeStyle}\">${inputLabel}</span>`;
                        ex += `<pre style=\"background:var(--bg-tertiary);color:var(--text-primary);padding:8px 12px;border-radius:6px;white-space:pre-wrap;\">${currentProblem.example_input}</pre></div>`;
                    }
                    if (output) {
                        ex += `<div style=\"margin-bottom:6px;\">`;
                        ex += `<span style=\"${badgeStyle}\">${outputLabel}</span>`;
                        ex += `<pre style=\"background:var(--bg-tertiary);color:var(--text-primary);padding:8px 12px;border-radius:6px;white-space:pre-wrap;\">${output}</pre></div>`;
                    }
                    if (explanation) {
                        explanation = explanation.replace(/^\s*Explica(ț|t)ii?:?\s*/i, '');
                        explanation = explanation.replace(/\n+/g, ' ');
                        explanation = explanation.replace(/\s{2,}/g, ' ');
                        explanation = explanation.trim();
                        ex += `<div style=\"margin-top:8px;\"><span style=\"color:var(--accent-primary);font-size:0.95em;font-weight:500;\">Explicație</span><div style=\"background:var(--bg-secondary);color:var(--text-primary);padding:10px 14px;border-radius:6px;white-space:normal;margin-top:2px;\">${explanation}</div></div>`;
                    }
                    tabContent.innerHTML = `<div>${highlightFilenames(ex.trim() || 'Fără exemplu.')}</div>`;
                }
            });
        });

        // PATCH SPECIAL pentru problema 11: separă automat input/output dacă sunt amestecate
        if (currentProblem && currentProblem.id == 11 && currentProblem.example_input && !currentProblem.example_output) {
            // Caută separatorul 'Ieșire' (sau 'Ieşire')
            let inputRaw = currentProblem.example_input;
            let sep = inputRaw.indexOf('Ieșire') !== -1 ? 'Ieșire' : (inputRaw.indexOf('Ieşire') !== -1 ? 'Ieşire' : null);
            if (sep) {
                let parts = inputRaw.split(sep);
                currentProblem.example_input = parts[0].trim();
                currentProblem.example_output = parts.slice(1).join(sep).replace(/^\s*\n?/, '').trim();
            }
        }
    }

    function showError(message, duration = 5000) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, duration);
    }

    function showSuccess(message, duration = 3000) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        document.body.appendChild(successDiv);
        
        setTimeout(() => {
            successDiv.remove();
        }, duration);
    }

    function handleApiError(error) {
        console.error('API Error:', error);
        let errorMessage = 'An unexpected error occurred';
        
        if (error.response) {
            const data = error.response.data;
            if (typeof data === 'object' && data.error) {
                errorMessage = data.error;
            } else if (typeof data === 'string') {
                errorMessage = data;
            }
        } else if (error.request) {
            errorMessage = 'No response from server. Please check your connection.';
        }
        
        showError(errorMessage);
    }

    async function runCode() {
        const code = window.ideMonaco.getValue();
        const customInput = document.querySelector('.ide-custom-test').value;
        const currentProblemId = window.currentProblemId;
        
        if (!currentProblemId) {
            showError('Nu ai selectat nicio problemă!');
            return;
        }
        
        // Verifică dacă este o problemă de subprogram
        const isSubprogram = window.currentProblemType === 'subprogram';
        
        if (isSubprogram) {
            // Folosește endpoint-ul pentru subprograme
            try {
                const response = await fetch('/api/test_subprogram', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        problem_id: currentProblemId,
                        code: code,
                        custom_input: customInput
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('Subprogramul funcționează corect!');
                    document.getElementById('ide-error-log').textContent = result.output;
                } else {
                    showError('Eroare la testarea subprogramului: ' + result.error);
                    document.getElementById('ide-error-log').textContent = result.error;
                }
            } catch (error) {
                showError('Eroare la comunicarea cu serverul: ' + error.message);
            }
        } else {
            // Folosește endpoint-ul normal pentru programe complete
            try {
                const response = await fetch('/api/run_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        code: code,
                        custom_input: customInput
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('Codul a fost executat cu succes!');
                    document.getElementById('ide-error-log').textContent = result.output;
                } else {
                    showError('Eroare la executarea codului: ' + result.error);
                    document.getElementById('ide-error-log').textContent = result.error;
                }
            } catch (error) {
                showError('Eroare la comunicarea cu serverul: ' + error.message);
            }
        }
    }

    // Funcție pentru generarea codului complet
    async function generateCompleteCode() {
        console.log('generateCompleteCode called');
        const code = window.ideMonaco.getValue();
        // Încearcă mai multe surse pentru ID-ul problemei
        let currentProblemId = window.InfoCoachApp.currentProblemId || window.currentProblemId || currentProblem?.id;
        if (!currentProblemId && currentProblem) {
            currentProblemId = 896;
        }
        if (!currentProblemId) {
            showError('Nu ai selectat nicio problemă!');
            return;
        }
        if (!code.trim()) {
            showError('Nu ai scris niciun cod!');
            return;
        }
        // Citește enunțul din tabul Enunț (sau toate taburile)
        let enunt = '';
        const tabButtons = document.querySelectorAll('.ide-tab');
        const tabContents = document.querySelectorAll('.ide-tab-content, .ide-tab-content > div');
        tabButtons.forEach((btn, idx) => {
            const tabName = btn.textContent.trim().toLowerCase();
            let content = '';
            if (tabContents[idx]) {
                content = tabContents[idx].textContent.trim();
            } else if (tabContents.length === 1) {
                content = tabContents[0].textContent.trim();
            }
            if (tabName === 'enunț') enunt = content;
        });
        // Afișează mesaj de încărcare
        const modal = document.getElementById('complete-code-modal');
        const display = document.getElementById('complete-code-display');
        if (!modal || !display) {
            showError('Eroare: Modalul nu a fost găsit!');
            return;
        }
        display.textContent = 'Se generează codul complet...';
        modal.style.display = 'block';
        // Trimite request cu statement
        try {
            const resp = await fetch('/api/generate_complete_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    problem_id: currentProblemId,
                    code: code,
                    statement: enunt
                })
            });
            const data = await resp.json();
            if (data.success && data.complete_code) {
                display.textContent = data.complete_code;
            } else {
                display.textContent = data.error || 'Eroare la generarea codului complet.';
            }
        } catch (e) {
            display.textContent = 'Eroare la comunicarea cu serverul.';
        }
    }

    // Funcție pentru copierea codului în clipboard
    function copyCompleteCode() {
        const display = document.getElementById('complete-code-display');
        const text = display.textContent;
        
        navigator.clipboard.writeText(text).then(() => {
            showSuccess('Codul a fost copiat în clipboard!');
        }).catch(() => {
            // Fallback pentru browsere mai vechi
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showSuccess('Codul a fost copiat în clipboard!');
        });
    }

    // Funcție pentru inserarea codului în editor
    function insertCompleteCode() {
        const display = document.getElementById('complete-code-display');
        const code = display.textContent;
        
        if (code && code !== 'Se generează codul complet...' && !code.startsWith('Eroare')) {
            window.ideMonaco.setValue(code);
            document.getElementById('complete-code-modal').style.display = 'none';
            showSuccess('Codul a fost inserat în editor!');
        }
    }

    // Evidențiere automată a numelor de fișiere în secțiunile de problemă
    function highlightFilenamesInTabs() {
        const tabContents = document.querySelectorAll('.ide-tab-content');
        const fileRegex = /\b([a-zA-Z0-9_\-]+\.(in|out|txt|dat|csv|json|xml))\b/g;
        tabContents.forEach(tab => {
            // Nu evidenția dacă deja există span.file-name
            if (tab.innerHTML.includes('class="file-name"')) return;
            tab.innerHTML = tab.innerHTML.replace(fileRegex, '<span class="file-name">$1</span>');
        });
    }

    highlightFilenamesInTabs();

    // Funcție pentru evidențierea numelor de fișiere în text (ex: sum.in, sum.out, *.txt etc.)
    function highlightFilenames(text) {
        const fileRegex = /\b([a-zA-Z0-9_\-]+\.(in|out|txt|dat|csv|json|xml))\b/g;
        return text.replace(fileRegex, '<span class="file-name">$1</span>');
    }

    // Event listeners pentru butoanele din modal
    document.getElementById('complete-code-insert')?.addEventListener('click', insertCompleteCode);
    document.getElementById('complete-code-close')?.addEventListener('click', () => {
        document.getElementById('complete-code-modal').style.display = 'none';
    });
    document.getElementById('copy-complete-code')?.addEventListener('click', copyCompleteCode);
    
    // Închide modalul când se face click în afara lui
    document.getElementById('complete-code-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'complete-code-modal') {
            e.target.style.display = 'none';
        }
    });
    
    // Închide modalul cu tasta ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('complete-code-modal');
            if (modal && modal.style.display === 'block') {
                modal.style.display = 'none';
            }
        }
    });
});