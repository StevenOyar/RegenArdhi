// ========================================
// WHATSAPP-STYLE CHAT IMPLEMENTATION
// Complete chat functionality with Backend API Integration
// ========================================

// ========================
// GLOBAL STATE
// ========================
const chatState = {
    currentProjectId: null,
    messages: [],
    isTyping: false,
    isRecording: false,
    recordingStartTime: null,
    recordingInterval: null,
    mediaRecorder: null,
    audioChunks: [],
    selectedFiles: [],
    lastMessageTime: null
};

// ========================
// INITIALIZATION
// ========================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 WhatsApp-style chat initialized');
    
    initializeChatUI();
    updateWelcomeTime();
    
    // Listen for project selection changes
    const projectSelector = document.getElementById('projectSelector');
    if (projectSelector) {
        projectSelector.addEventListener('change', function() {
            const projectId = this.value;
            if (projectId) {
                chatState.currentProjectId = parseInt(projectId);
                loadChatHistory();
            }
        });
    }
});

function initializeChatUI() {
    // Auto-resize textarea
    const input = document.getElementById('messageInput');
    if (input) {
        input.addEventListener('input', handleInputChange);
    }
    
    // Setup auto-scroll
    setupAutoScroll();
}

function updateWelcomeTime() {
    const welcomeTime = document.getElementById('welcomeTime');
    if (welcomeTime) {
        welcomeTime.textContent = formatTime(new Date());
    }
}

// ========================
// MESSAGE SENDING
// ========================
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input?.value.trim();
    
    if (!message) return;
    
    if (!chatState.currentProjectId) {
        showNotification('Please select a project first', 'warning');
        return;
    }
    
    // Clear input and reset UI
    input.value = '';
    handleInputChange();
    
    // Hide quick replies after first message
    const quickReplies = document.getElementById('quickRepliesContainer');
    if (quickReplies) {
        quickReplies.classList.add('hidden');
    }
    
    // Add user message to UI immediately
    addMessageToChat('sent', message);
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch('/chat/api/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                project_id: chatState.currentProjectId
            })
        });
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        
        if (data.success && data.response) {
            // Add AI response
            addMessageToChat('received', data.response);
            
            // Store in state
            chatState.messages.push({
                type: 'user',
                content: message,
                timestamp: new Date()
            });
            chatState.messages.push({
                type: 'ai',
                content: data.response,
                timestamp: new Date()
            });
        } else {
            addMessageToChat('received', '❌ Sorry, I encountered an error. Please try again.');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        addMessageToChat('received', '❌ Connection error. Please check your internet connection and try again.');
    }
    
    // Scroll to bottom
    setTimeout(scrollToBottom, 100);
}

function sendQuickMessage(text) {
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = text;
        sendMessage();
    }
}

// ========================
// MESSAGE DISPLAY
// ========================
function addMessageToChat(type, text) {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;
    
    // Check if we need a new date divider
    const now = new Date();
    if (shouldAddDateDivider(now)) {
        addDateDivider(now);
        chatState.lastMessageTime = now;
    }
    
    // Create message wrapper
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${type}-wrapper`;
    
    // Create message
    const message = document.createElement('div');
    message.className = `message ${type}`;
    
    // Format message content
    const formattedText = formatMessageText(text);
    
    // Build message HTML
    message.innerHTML = `
        <div class="message-content">
            <p class="message-text">${formattedText}</p>
            <div class="message-meta">
                <span class="message-time">${formatTime(now)}</span>
                ${type === 'sent' ? '<i class="fas fa-check-double message-status read"></i>' : ''}
            </div>
        </div>
    `;
    
    wrapper.appendChild(message);
    container.appendChild(wrapper);
    
    // Scroll to bottom with animation
    setTimeout(scrollToBottom, 100);
}

function formatMessageText(text) {
    // Convert markdown-style formatting
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/\n/g, '<br>');
    
    // Convert URLs to links
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    text = text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    return text;
}

function shouldAddDateDivider(now) {
    if (!chatState.lastMessageTime) {
        chatState.lastMessageTime = now;
        return false;
    }
    
    const lastDate = new Date(chatState.lastMessageTime);
    return now.toDateString() !== lastDate.toDateString();
}

function addDateDivider(date) {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;
    
    const divider = document.createElement('div');
    divider.className = 'date-divider';
    divider.innerHTML = `<span>${formatDate(date)}</span>`;
    
    container.appendChild(divider);
}

// ========================
// TYPING INDICATOR
// ========================
function showTypingIndicator() {
    chatState.isTyping = true;
    
    // Update header status
    const typingIndicator = document.getElementById('typingIndicator');
    const onlineStatus = document.getElementById('onlineStatus');
    
    if (typingIndicator && onlineStatus) {
        typingIndicator.style.display = 'inline';
        onlineStatus.style.display = 'none';
    }
    
    // Add typing message bubble
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper received-wrapper';
    wrapper.id = 'typingBubble';
    
    wrapper.innerHTML = `
        <div class="message received">
            <div class="message-content">
                <div class="typing-animation">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(wrapper);
    scrollToBottom();
}

function hideTypingIndicator() {
    chatState.isTyping = false;
    
    // Update header status
    const typingIndicator = document.getElementById('typingIndicator');
    const onlineStatus = document.getElementById('onlineStatus');
    
    if (typingIndicator && onlineStatus) {
        typingIndicator.style.display = 'none';
        onlineStatus.style.display = 'inline';
    }
    
    // Remove typing bubble
    const typingBubble = document.getElementById('typingBubble');
    if (typingBubble) {
        typingBubble.remove();
    }
}

// ========================
// INPUT HANDLING
// ========================
function handleInputKeydown(event) {
    // Send on Enter (without Shift)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function handleInputChange() {
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendButton');
    const voiceBtn = document.getElementById('voiceButton');
    
    if (!input || !sendBtn || !voiceBtn) return;
    
    const hasText = input.value.trim().length > 0;
    
    // Toggle send/voice button
    if (hasText) {
        sendBtn.style.display = 'flex';
        voiceBtn.style.display = 'none';
    } else {
        sendBtn.style.display = 'none';
        voiceBtn.style.display = 'flex';
    }
    
    // Auto-resize textarea
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 100) + 'px';
}

// ========================
// EMOJI PICKER
// ========================
function toggleEmojiPicker() {
    const picker = document.getElementById('emojiPicker');
    if (!picker) return;
    
    if (picker.style.display === 'none' || !picker.style.display) {
        picker.style.display = 'block';
    } else {
        picker.style.display = 'none';
    }
}

function insertEmoji(emoji) {
    const input = document.getElementById('messageInput');
    if (!input) return;
    
    const cursorPos = input.selectionStart || 0;
    const textBefore = input.value.substring(0, cursorPos);
    const textAfter = input.value.substring(cursorPos);
    
    input.value = textBefore + emoji + textAfter;
    input.focus();
    
    // Move cursor after emoji
    const newCursorPos = cursorPos + emoji.length;
    input.setSelectionRange(newCursorPos, newCursorPos);
    
    handleInputChange();
    
    // Close emoji picker
    toggleEmojiPicker();
}

// ========================
// FILE HANDLING
// ========================
function attachFile() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.click();
    }
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    
    chatState.selectedFiles = files;
    showFilePreview(files);
}

function showFilePreview(files) {
    const container = document.getElementById('filePreviewContainer');
    const list = document.getElementById('filePreviewList');
    
    if (!container || !list) return;
    
    list.innerHTML = '';
    
    files.forEach((file, index) => {
        const preview = document.createElement('div');
        preview.className = 'file-preview-item';
        
        const icon = getFileIcon(file.type);
        const size = formatFileSize(file.size);
        
        preview.innerHTML = `
            <div class="file-icon">
                <i class="fas ${icon}"></i>
            </div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-size">${size}</div>
            </div>
            <button class="remove-file-btn" onclick="removeFile(${index})">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        list.appendChild(preview);
    });
    
    container.style.display = 'block';
}

function removeFile(index) {
    chatState.selectedFiles.splice(index, 1);
    
    if (chatState.selectedFiles.length === 0) {
        clearFilePreview();
    } else {
        showFilePreview(chatState.selectedFiles);
    }
}

function clearFilePreview() {
    const container = document.getElementById('filePreviewContainer');
    const input = document.getElementById('fileInput');
    
    if (container) {
        container.style.display = 'none';
    }
    
    if (input) {
        input.value = '';
    }
    
    chatState.selectedFiles = [];
}

function getFileIcon(mimeType) {
    if (mimeType.startsWith('image/')) return 'fa-image';
    if (mimeType.startsWith('video/')) return 'fa-video';
    if (mimeType.startsWith('audio/')) return 'fa-music';
    if (mimeType.includes('pdf')) return 'fa-file-pdf';
    if (mimeType.includes('word')) return 'fa-file-word';
    if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'fa-file-excel';
    return 'fa-file';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ========================
// VOICE RECORDING
// ========================
async function startVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        chatState.mediaRecorder = new MediaRecorder(stream);
        chatState.audioChunks = [];
        chatState.isRecording = true;
        chatState.recordingStartTime = Date.now();
        
        chatState.mediaRecorder.ondataavailable = (event) => {
            chatState.audioChunks.push(event.data);
        };
        
        chatState.mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(chatState.audioChunks, { type: 'audio/webm' });
            console.log('Audio recorded:', audioBlob);
            // In production, upload this to your server
        };
        
        chatState.mediaRecorder.start();
        
        // Show recording UI
        showVoiceRecordingUI();
        
        // Start timer
        updateRecordingTime();
        chatState.recordingInterval = setInterval(updateRecordingTime, 1000);
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        showNotification('Could not access microphone. Please check permissions.', 'error');
    }
}

function showVoiceRecordingUI() {
    const inputWrapper = document.querySelector('.input-wrapper');
    const recordingUI = document.getElementById('voiceRecordingUI');
    
    if (inputWrapper && recordingUI) {
        inputWrapper.style.display = 'none';
        recordingUI.style.display = 'block';
    }
}

function hideVoiceRecordingUI() {
    const inputWrapper = document.querySelector('.input-wrapper');
    const recordingUI = document.getElementById('voiceRecordingUI');
    
    if (inputWrapper && recordingUI) {
        inputWrapper.style.display = 'flex';
        recordingUI.style.display = 'none';
    }
}

function updateRecordingTime() {
    if (!chatState.isRecording || !chatState.recordingStartTime) return;
    
    const elapsed = Date.now() - chatState.recordingStartTime;
    const seconds = Math.floor(elapsed / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    const timeDisplay = document.getElementById('recordingTime');
    if (timeDisplay) {
        timeDisplay.textContent = `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
}

function cancelVoiceRecording() {
    if (chatState.mediaRecorder && chatState.isRecording) {
        chatState.mediaRecorder.stop();
        chatState.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    clearInterval(chatState.recordingInterval);
    chatState.isRecording = false;
    chatState.audioChunks = [];
    
    hideVoiceRecordingUI();
}

async function sendVoiceMessage() {
    if (!chatState.mediaRecorder || !chatState.isRecording) return;
    
    chatState.mediaRecorder.stop();
    chatState.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    
    clearInterval(chatState.recordingInterval);
    chatState.isRecording = false;
    
    hideVoiceRecordingUI();
    
    // Add voice message to chat
    const duration = Math.floor((Date.now() - chatState.recordingStartTime) / 1000);
    addVoiceMessageToChat(duration);
    
    showNotification('🎤 Voice message sent!', 'success');
}

function addVoiceMessageToChat(duration) {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper sent-wrapper';
    
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    const durationText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    wrapper.innerHTML = `
        <div class="message sent">
            <div class="message-content">
                <div class="voice-message">
                    <button class="play-voice-btn" onclick="playVoiceMessage(this)">
                        <i class="fas fa-play"></i>
                    </button>
                    <div class="voice-waveform">
                        <div class="waveform-bars">
                            ${Array(20).fill('<div class="waveform-bar"></div>').join('')}
                        </div>
                        <span class="voice-duration">${durationText}</span>
                    </div>
                </div>
                <div class="message-meta">
                    <span class="message-time">${formatTime(new Date())}</span>
                    <i class="fas fa-check-double message-status read"></i>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(wrapper);
    scrollToBottom();
}

function playVoiceMessage(button) {
    const icon = button.querySelector('i');
    
    if (icon.classList.contains('fa-play')) {
        icon.classList.remove('fa-play');
        icon.classList.add('fa-pause');
        console.log('Playing voice message');
    } else {
        icon.classList.remove('fa-pause');
        icon.classList.add('fa-play');
        console.log('Pausing voice message');
    }
}

// ========================
// CHAT HISTORY
// ========================
async function loadChatHistory() {
    if (!chatState.currentProjectId) return;
    
    try {
        const response = await fetch(`/chat/api/history?project_id=${chatState.currentProjectId}&limit=50`);
        const data = await response.json();
        
        if (data.success && data.history && data.history.length > 0) {
            // Clear existing messages (except welcome and date divider)
            const container = document.getElementById('chatMessagesContainer');
            if (!container) return;
            
            // Keep welcome message and first date divider
            const welcomeMsg = document.getElementById('welcomeMessage');
            const dateDivider = container.querySelector('.date-divider');
            
            container.innerHTML = '';
            
            if (dateDivider) container.appendChild(dateDivider);
            if (welcomeMsg) container.appendChild(welcomeMsg);
            
            // Add historical messages
            data.history.forEach(chat => {
                if (chat.message) addMessageToChat('sent', chat.message);
                if (chat.response) addMessageToChat('received', chat.response);
            });
            
            chatState.messages = data.history;
            scrollToBottom();
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

async function clearChat() {
    if (!confirm('Are you sure you want to clear all messages? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/chat/api/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_id: chatState.currentProjectId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Clear UI
            const container = document.getElementById('chatMessagesContainer');
            if (container) {
                container.innerHTML = `
                    <div class="date-divider">
                        <span>TODAY</span>
                    </div>
                    <div class="message-wrapper received-wrapper" id="welcomeMessage">
                        <div class="message received">
                            <div class="message-content">
                                <p class="message-text">
                                    👋 Hi! I'm <strong>RegenAI</strong>, your intelligent assistant for land restoration.
                                    <br><br>
                                    I can help you with:
                                    <br>🌿 Vegetation health analysis
                                    <br>📊 Data interpretation
                                    <br>🌱 Restoration recommendations
                                    <br>📅 Seasonal planning
                                    <br><br>
                                    <em>What would you like to know?</em>
                                </p>
                                <div class="message-meta">
                                    <span class="message-time">${formatTime(new Date())}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Show quick replies again
            const quickReplies = document.getElementById('quickRepliesContainer');
            if (quickReplies) {
                quickReplies.classList.remove('hidden');
            }
            
            chatState.messages = [];
            showNotification('✓ Chat cleared', 'success');
        }
    } catch (error) {
        console.error('Error clearing chat:', error);
        showNotification('Failed to clear chat', 'error');
    }
    
    // Close menu
    toggleChatMenu();
}

async function exportChat() {
    try {
        if (chatState.messages.length === 0) {
            showNotification('No messages to export', 'warning');
            return;
        }
        
        const messages = chatState.messages.map(msg => {
            const type = msg.type === 'user' ? 'You' : 'RegenAI';
            const time = new Date(msg.timestamp).toLocaleString();
            return `[${time}] ${type}: ${msg.content}`;
        }).join('\n\n');
        
        const blob = new Blob([messages], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `regenai-chat-${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        
        showNotification('✓ Chat exported', 'success');
    } catch (error) {
        console.error('Error exporting chat:', error);
        showNotification('Failed to export chat', 'error');
    }
    
    toggleChatMenu();
}

// ========================
// MENU ACTIONS
// ========================
function toggleChatMenu() {
    const menu = document.getElementById('chatMenuDropdown');
    if (!menu) return;
    
    menu.classList.toggle('show');
}

function closeChatPanel() {
    console.log('Close chat panel');
}

function viewChatInfo() {
    showNotification('Chat info feature coming soon', 'info');
    toggleChatMenu();
}

function selectMessages() {
    showNotification('Select messages feature coming soon', 'info');
    toggleChatMenu();
}

function muteNotifications() {
    showNotification('Notifications muted for this chat', 'success');
    toggleChatMenu();
}

function startVoiceCall() {
    showNotification('Voice call feature coming soon', 'info');
}

function startVideoCall() {
    showNotification('Video call feature coming soon', 'info');
}

// ========================
// UTILITY FUNCTIONS
// ========================
function scrollToBottom() {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;
    
    container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
    });
}

function setupAutoScroll() {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;
    
    const observer = new MutationObserver(() => {
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        if (isNearBottom) {
            scrollToBottom();
        }
    });
    
    observer.observe(container, { childList: true, subtree: true });
}

function formatTime(date) {
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    const displayMinutes = minutes.toString().padStart(2, '0');
    return `${displayHours}:${displayMinutes} ${ampm}`;
}

function formatDate(date) {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
        return 'TODAY';
    } else if (date.toDateString() === yesterday.toDateString()) {
        return 'YESTERDAY';
    } else {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        }).toUpperCase();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Use window.showNotification if available from insights.js
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// ========================
// PROJECT SELECTION
// ========================
function setCurrentProject(projectId) {
    chatState.currentProjectId = projectId;
    loadChatHistory();
}

// ========================
// CLOSE MENUS ON OUTSIDE CLICK
// ========================
document.addEventListener('click', function(event) {
    const emojiPicker = document.getElementById('emojiPicker');
    const emojiButton = event.target.closest('[onclick*="toggleEmojiPicker"]');
    
    if (emojiPicker && !emojiPicker.contains(event.target) && !emojiButton) {
        emojiPicker.style.display = 'none';
    }
    
    const chatMenu = document.getElementById('chatMenuDropdown');
    const menuButton = event.target.closest('[onclick*="toggleChatMenu"]');
    
    if (chatMenu && !chatMenu.contains(event.target) && !menuButton) {
        chatMenu.classList.remove('show');
    }
});

// ========================
// EXPORT FUNCTIONS TO WINDOW
// ========================
window.sendMessage = sendMessage;
window.sendQuickMessage = sendQuickMessage;
window.handleInputKeydown = handleInputKeydown;
window.handleInputChange = handleInputChange;
window.toggleEmojiPicker = toggleEmojiPicker;
window.insertEmoji = insertEmoji;
window.attachFile = attachFile;
window.handleFileSelect = handleFileSelect;
window.removeFile = removeFile;
window.clearFilePreview = clearFilePreview;
window.startVoiceRecording = startVoiceRecording;
window.cancelVoiceRecording = cancelVoiceRecording;
window.sendVoiceMessage = sendVoiceMessage;
window.playVoiceMessage = playVoiceMessage;
window.clearChat = clearChat;
window.exportChat = exportChat;
window.toggleChatMenu = toggleChatMenu;
window.closeChatPanel = closeChatPanel;
window.viewChatInfo = viewChatInfo;
window.selectMessages = selectMessages;
window.muteNotifications = muteNotifications;
window.startVoiceCall = startVoiceCall;
window.startVideoCall = startVideoCall;
window.setCurrentProject = setCurrentProject;

console.log('✅ WhatsApp-style chat loaded successfully!');