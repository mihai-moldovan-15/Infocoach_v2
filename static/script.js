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
        // Get clasa from the form
        const clasa = document.querySelector('input[name="clasa"]')?.value || '9';
        
        // Create the full assistant message structure with feedback form
        messageDiv.innerHTML = `
            <b>InfoCoach:</b>
            <div class="message-content">${content}</div>
            <input type="hidden" class="user-input-hidden" value="${userInput.replace(/"/g, '&quot;')}">
            <input type="hidden" class="clasa-hidden" value="${clasa}">
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
                        tabButtons.forEach(btn => btn.disabled = true);
                        if (generateExampleBtn) generateExampleBtn.style.display = 'none';
                        return;
                    }
                    currentProblem = data;
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
                    // Date de intrare și ieșire
                    let date = '';
                    if (currentProblem.input_description) date += currentProblem.input_description + '\n';
                    if (currentProblem.output_description) date += currentProblem.output_description;
                    if (date.trim()) {
                        tabContent.innerHTML = `<div style='white-space:pre-line;'>${highlightFilenames(date.trim())}</div>`;
                    } else {
                        tabContent.textContent = 'Fără date de intrare/ieșire.';
                    }
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
                    // Limite de timp și memorie
                    let limHtml = '';
                    if (currentProblem.time_limit || currentProblem.memory_limit) {
                        if (currentProblem.time_limit) limHtml += `<div><b>Limită timp:</b> ${currentProblem.time_limit}</div>`;
                        if (currentProblem.memory_limit) limHtml += `<div><b>Limită memorie:</b> ${currentProblem.memory_limit}</div>`;
                    } else {
                        limHtml = 'Nu există limite definite pentru această problemă.';
                    }
                    tabContent.innerHTML = limHtml;
                } else if (idx === 4) {
                    // Exemplu cu etichete colorate și font mai mic pentru fișiere/intrare/ieșire
                    let ex = '';
                    let inputLabel = currentProblem.example_input_name && currentProblem.example_input_name !== 'consola'
                        ? currentProblem.example_input_name : 'Intrare';
                    let outputLabel = currentProblem.example_output_name && currentProblem.example_output_name !== 'consola'
                        ? currentProblem.example_output_name : 'Ieșire';
                    const labelStyle = 'color:#1976d2;font-size:0.95em;font-weight:500;';
                    if (currentProblem.example_input) {
                        ex += `<span style=\"${labelStyle}\">${inputLabel}</span><br>` + currentProblem.example_input + '<br>';
                    }
                    if (currentProblem.example_output) {
                        ex += `<span style=\"${labelStyle}\">${outputLabel}</span><br>` + currentProblem.example_output + '<br>';
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
                theme: 'vs',
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
                li.innerHTML = `<span class="suggestion-title">${sug.name}</span>${sug.category ? `<span class="suggestion-tags">${sug.category}</span>` : ''}`;
                if (idx === selectedIdx) li.classList.add('active');
                li.onclick = () => {
                    problemSearchInput.value = sug.name;
                    problemSuggestionsList.classList.remove('show');
                    fetch(`/api/problem_details?id=${sug.id}`)
                        .then(res => res.json())
                        .then(data => {
                            if (!data || data.error) return;
                            currentProblem = data;
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
        if (!problem) return;
        // Activează toate tab-urile
        document.querySelectorAll('.ide-tab').forEach(btn => btn.disabled = false);
        // Activează tab-ul Enunț
        document.querySelectorAll('.ide-tab').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.ide-tab')[0].classList.add('active');
        // Populează tab-ul Enunț
        tabContent.textContent = problem.statement || 'Fără enunț.';

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

        // Elimină event listener-ele vechi (prin clonare)
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
                    let inputLabel = currentProblem.example_input_name && currentProblem.example_input_name !== 'consola'
                        ? currentProblem.example_input_name : 'Intrare';
                    let outputLabel = currentProblem.example_output_name && currentProblem.example_output_name !== 'consola'
                        ? currentProblem.example_output_name : 'Ieșire';
                    const labelStyle = 'color:#1976d2;font-size:0.95em;font-weight:500;';
                    if (currentProblem.example_input) {
                        ex += `<span style=\"${labelStyle}\">${inputLabel}</span><br>` + currentProblem.example_input + '<br>';
                    }
                    if (currentProblem.example_output) {
                        ex += `<span style=\"${labelStyle}\">${outputLabel}</span><br>` + currentProblem.example_output + '<br>';
                    }
                    tabContent.innerHTML = `<div>${highlightFilenames(ex.trim() || 'Fără exemplu.')}</div>`;
                }
            });
        });
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
        const code = editor.getValue();
        const customInput = document.getElementById('custom-input').value;
        const files = getFiles();
        
        try {
            const response = await axios.post('/api/run_code', {
                code,
                files,
                custom_input: customInput
            });
            
            const result = response.data;
            if (result.success) {
                document.getElementById('output').textContent = result.output;
                document.getElementById('error').textContent = '';
                showSuccess('Code executed successfully');
            } else {
                document.getElementById('output').textContent = '';
                document.getElementById('error').textContent = result.error;
                showError('Execution failed');
            }
        } catch (error) {
            handleApiError(error);
            document.getElementById('output').textContent = '';
            document.getElementById('error').textContent = 'Failed to execute code';
        }
    }

    async function submitSolution() {
        const code = editor.getValue();
        const files = getFiles();
        
        try {
            const response = await axios.post('/api/submit', {
                code,
                files
            });
            
            const result = response.data;
            if (result.success) {
                showSuccess('Solution submitted successfully');
                updateTestResults(result.results);
            } else {
                showError(result.error || 'Failed to submit solution');
            }
        } catch (error) {
            handleApiError(error);
        }
    }

    function updateTestResults(results) {
        const resultsContainer = document.getElementById('test-results');
        resultsContainer.innerHTML = '';
        
        results.forEach((result, index) => {
            const resultDiv = document.createElement('div');
            resultDiv.className = `test-result ${result.passed ? 'passed' : 'failed'}`;
            
            const status = document.createElement('div');
            status.className = 'test-status';
            status.textContent = result.passed ? '✓' : '✗';
            
            const details = document.createElement('div');
            details.className = 'test-details';
            details.innerHTML = `
                <div>Test ${index + 1}</div>
                <div>${result.passed ? 'Passed' : 'Failed'}</div>
                ${result.message ? `<div class="test-message">${result.message}</div>` : ''}
            `;
            
            resultDiv.appendChild(status);
            resultDiv.appendChild(details);
            resultsContainer.appendChild(resultDiv);
        });
    }

    // Add CSS for notifications
    const style = document.createElement('style');
    style.textContent = `
        .error-message, .success-message {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        }
        
        .error-message {
            background-color: #dc3545;
        }
        
        .success-message {
            background-color: #28a745;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .test-result {
            display: flex;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            background-color: #f8f9fa;
        }
        
        .test-result.passed {
            border-left: 4px solid #28a745;
        }
        
        .test-result.failed {
            border-left: 4px solid #dc3545;
        }
        
        .test-status {
            font-size: 1.2em;
            margin-right: 10px;
        }
        
        .test-details {
            flex: 1;
        }
        
        .test-message {
            margin-top: 5px;
            font-size: 0.9em;
            color: #666;
        }
    `;

    document.head.appendChild(style);

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
});