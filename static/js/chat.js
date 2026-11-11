/**
 * Django Assistant - Vanilla JavaScript Frontend Controller
 * Strictly adheres to specifications:
 * - Uses Fetch API with CSRF token
 * - Displays user message immediately
 * - Displays bot response with typing indicator
 * - Safe rendering with textContent (prevents XSS/HTML injection)
 * - Auto-scroll, sidebar navigation, conversation switching & new chat
 */

document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // DOM Element References
    // =========================================================================
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const charCount = document.getElementById('char-count');
    const typingIndicator = document.getElementById('typing-indicator');
    const conversationList = document.getElementById('conversation-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const activeChatTitle = document.getElementById('active-chat-title');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    const chatSidebar = document.getElementById('chat-sidebar');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');
    const welcomeBox = document.getElementById('welcome-box');

    // =========================================================================
    // Application State
    // =========================================================================
    let currentConversationId = null;
    let isRequestPending = false;

    // =========================================================================
    // CSRF Token Retrieval Helper
    // =========================================================================
    function getCsrfToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag && metaTag.content) {
            return metaTag.content;
        }
        const inputTag = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (inputTag && inputTag.value) {
            return inputTag.value;
        }
        // Fallback to cookie
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return decodeURIComponent(cookie.substring('csrftoken='.length));
            }
        }
        return '';
    }

    // =========================================================================
    // Formatting Helpers
    // =========================================================================
    function formatTime(dateString) {
        const date = dateString ? new Date(dateString) : new Date();
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // =========================================================================
    // Message Rendering (Uses textContent to prevent HTML injection)
    // =========================================================================
    function appendMessage(senderType, contentText, timestamp = null) {
        // Hide initial welcome box once a message is appended
        if (welcomeBox && welcomeBox.parentNode) {
            welcomeBox.style.display = 'none';
        }

        const isUser = senderType === 'user';
        const row = document.createElement('div');
        row.className = `message-row ${isUser ? 'user-row' : 'bot-row'}`;

        // Avatar icon
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        if (isUser) {
            avatar.textContent = 'U';
        } else {
            avatar.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg>`;
        }

        // Message content wrapper
        const contentWrap = document.createElement('div');
        contentWrap.className = 'message-content';

        // Message bubble (STRICT: using textContent for security)
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = contentText;

        // Timestamp
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = formatTime(timestamp);

        contentWrap.appendChild(bubble);
        contentWrap.appendChild(timeSpan);

        row.appendChild(avatar);
        row.appendChild(contentWrap);

        chatMessages.appendChild(row);
        scrollToBottom();
    }

    // =========================================================================
    // Typing Indicator Control
    // =========================================================================
    function showTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.classList.remove('hidden');
            scrollToBottom();
        }
    }

    function hideTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.classList.add('hidden');
        }
    }

    // =========================================================================
    // Sidebar Mobile Drawer Controls
    // =========================================================================
    function openSidebar() {
        if (chatSidebar) chatSidebar.classList.add('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
    }

    function closeSidebar() {
        if (chatSidebar) chatSidebar.classList.remove('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
    }

    if (sidebarToggle) sidebarToggle.addEventListener('click', openSidebar);
    if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
    if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

    // =========================================================================
    // Textarea Auto-expand & Character Counter
    // =========================================================================
    if (chatInput) {
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = `${Math.min(chatInput.scrollHeight, 150)}px`;

            const currentLength = chatInput.value.length;
            if (charCount) {
                charCount.textContent = `${currentLength} / 2000`;
                if (currentLength >= 1900) {
                    charCount.style.color = '#ef4444';
                } else {
                    charCount.style.color = '';
                }
            }
        });

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });
    }

    // =========================================================================
    // Suggestion Chips Quick Send
    // =========================================================================
    document.querySelectorAll('.chip').forEach((chip) => {
        chip.addEventListener('click', () => {
            const promptText = chip.getAttribute('data-prompt');
            if (promptText && chatInput) {
                chatInput.value = promptText;
                chatInput.dispatchEvent(new Event('input'));
                chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });
    });

    // =========================================================================
    // Sidebar Conversation List Update
    // =========================================================================
    function updateSidebarItem(convoId, convoTitle) {
        if (!conversationList) return;

        // Remove "no conversations" placeholder if present
        const noConvMsg = document.getElementById('no-conversations-msg');
        if (noConvMsg) noConvMsg.remove();

        let existingItem = conversationList.querySelector(`.conversation-item[data-id="${convoId}"]`);
        if (!existingItem) {
            existingItem = document.createElement('div');
            existingItem.className = 'conversation-item active';
            existingItem.setAttribute('data-id', convoId);
            existingItem.setAttribute('tabindex', '0');

            const icon = document.createElement('span');
            icon.innerHTML = `<svg class="convo-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`;

            const titleSpan = document.createElement('span');
            titleSpan.className = 'convo-title';
            titleSpan.textContent = convoTitle;

            existingItem.appendChild(icon);
            existingItem.appendChild(titleSpan);

            // Bind click event
            existingItem.addEventListener('click', () => selectConversation(convoId, convoTitle));

            // Prepend as latest active
            conversationList.insertBefore(existingItem, conversationList.firstChild);
        } else {
            const titleSpan = existingItem.querySelector('.convo-title');
            if (titleSpan) titleSpan.textContent = convoTitle;
            conversationList.insertBefore(existingItem, conversationList.firstChild);
        }

        // Highlight this conversation
        document.querySelectorAll('.conversation-item').forEach((item) => {
            item.classList.toggle('active', item.getAttribute('data-id') == convoId);
        });
    }

    // =========================================================================
    // Selecting and Loading an Existing Conversation
    // =========================================================================
    async function selectConversation(convoId, convoTitle) {
        if (isRequestPending) return;

        currentConversationId = convoId;
        closeSidebar();

        // Update active UI highlights
        document.querySelectorAll('.conversation-item').forEach((item) => {
            item.classList.toggle('active', item.getAttribute('data-id') == convoId);
        });

        if (activeChatTitle) {
            activeChatTitle.textContent = convoTitle || `Conversation #${convoId}`;
        }

        // Clear chat area & display loading
        chatMessages.innerHTML = '';
        showTypingIndicator();

        try {
            const response = await fetch(`/api/conversations/${convoId}/`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });

            hideTypingIndicator();

            if (!response.ok) {
                throw new Error('Failed to load conversation history.');
            }

            const data = await response.json();
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach((msg) => {
                    appendMessage(msg.sender_type, msg.content, msg.created_at);
                });
            } else {
                appendMessage('bot', 'This conversation has no recorded messages.');
            }
        } catch (err) {
            hideTypingIndicator();
            appendMessage('bot', `⚠️ Error: ${err.message || 'Unable to retrieve messages.'}`);
        }
    }

    // Bind click events on server-rendered conversation items
    document.querySelectorAll('.conversation-item').forEach((item) => {
        const id = item.getAttribute('data-id');
        const title = item.querySelector('.convo-title')?.textContent || `Chat #${id}`;
        item.addEventListener('click', () => selectConversation(id, title));
    });

    // =========================================================================
    // New Chat Action
    // =========================================================================
    function startNewChat() {
        if (isRequestPending) return;

        currentConversationId = null;
        closeSidebar();

        // Remove active selection from sidebar
        document.querySelectorAll('.conversation-item').forEach((item) => {
            item.classList.remove('active');
        });

        if (activeChatTitle) {
            activeChatTitle.textContent = 'New Conversation • Rule-based local assistant';
        }

        // Reset message container to welcome screen
        chatMessages.innerHTML = '';
        if (welcomeBox) {
            welcomeBox.style.display = 'block';
            chatMessages.appendChild(welcomeBox);
        }

        if (chatInput) {
            chatInput.value = '';
            chatInput.style.height = 'auto';
            if (charCount) charCount.textContent = '0 / 2000';
            chatInput.focus();
        }
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', startNewChat);
    }

    // =========================================================================
    // Sending Message via Fetch API (/api/chat/)
    // =========================================================================
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (isRequestPending) return;

            const messageText = chatInput ? chatInput.value.trim() : '';
            if (!messageText) return;

            if (messageText.length > 2000) {
                alert('Message is too long. Maximum allowed length is 2000 characters.');
                return;
            }

            // Immediately display user message in the chat feed
            appendMessage('user', messageText);

            // Clear input & reset sizing
            chatInput.value = '';
            chatInput.style.height = 'auto';
            if (charCount) charCount.textContent = '0 / 2000';

            // Disable controls during request
            isRequestPending = true;
            if (sendBtn) sendBtn.disabled = true;
            if (chatInput) chatInput.disabled = true;

            // Show bot typing indicator
            showTypingIndicator();

            try {
                const payload = {
                    message: messageText,
                    conversation_id: currentConversationId
                };

                const response = await fetch('/api/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                hideTypingIndicator();

                const data = await response.json();

                if (!response.ok) {
                    const errorDetail = data.error || (data.details && JSON.stringify(data.details)) || 'Server error';
                    throw new Error(errorDetail);
                }

                // Update current conversation id if new
                currentConversationId = data.conversation_id;

                // Update active chat header title & sidebar item
                if (data.conversation_title && activeChatTitle) {
                    activeChatTitle.textContent = data.conversation_title;
                }
                updateSidebarItem(data.conversation_id, data.conversation_title);

                // Display bot response safely
                const botReply = data.response || data.bot_response || 'No response generated.';
                appendMessage('bot', botReply);

            } catch (error) {
                hideTypingIndicator();
                appendMessage('bot', `⚠️ Could not send message: ${error.message || 'Network error'}`);
            } finally {
                // Re-enable controls
                isRequestPending = false;
                if (sendBtn) sendBtn.disabled = false;
                if (chatInput) {
                    chatInput.disabled = false;
                    chatInput.focus();
                }
            }
        });
    }

    // Auto-focus input on initial page load
    if (chatInput) {
        chatInput.focus();
    }
});
