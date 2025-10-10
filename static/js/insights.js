// ========================================
// REGENARDHI - AI INSIGHTS SYSTEM
// Complete JavaScript with API Integration
// ========================================

// ========================
// GLOBAL STATE
// ========================
let currentProject = null;
let currentPeriod = '30d';
let charts = {
    ndvi: null,
    climate: null,
    soil: null
};
let chatHistory = [];
let isAIOnline = false;

// ========================
// INITIALIZATION
// ========================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Insights page initialized');
    
    initializeUI();
    loadProjects();
    checkAIStatus();
    setupEventListeners();
    
    // Check AI status every 30 seconds
    setInterval(checkAIStatus, 30000);
});

// ========================
// UI INITIALIZATION
// ========================
function initializeUI() {
    // Mobile menu toggle
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');
    
    if (mobileToggle) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
    
    // User dropdown
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('show');
        });
        
        document.addEventListener('click', () => {
            userDropdown.classList.remove('show');
        });
    }
}

// ========================
// PROJECT MANAGEMENT
// ========================
async function loadProjects() {
    try {
        const response = await fetch('/projects/api/list');
        const data = await response.json();
        
        if (data.success && data.projects) {
            populateProjectSelector(data.projects);
            
            // Auto-select first project if available
            if (data.projects.length > 0) {
                currentProject = data.projects[0].id;
                document.getElementById('projectSelector').value = currentProject;
                await loadProjectData(currentProject);
            }
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        showNotification('Failed to load projects', 'error');
    }
}

function populateProjectSelector(projects) {
    const selector = document.getElementById('projectSelector');
    
    // Clear existing options except first
    selector.innerHTML = '<option value="">Select a project...</option>';
    
    projects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.id;
        option.textContent = `${project.name} (${project.project_type})`;
        selector.appendChild(option);
    });
}

// ========================
// DATA LOADING
// ========================
async function loadProjectData(projectId) {
    currentProject = projectId;
    
    // Set project for chat
    if (typeof setCurrentProject === 'function') {
        setCurrentProject(projectId);
    }
    if (!projectId) return;
    
    showLoading();
    
    try {
        // Load analytics data
        await loadAnalyticsData(projectId);
        
        // Load AI insights
        await loadAIInsights(projectId);
        
        // Load chat history
        await loadChatHistory(projectId);
        
    } catch (error) {
        console.error('Error loading project data:', error);
        showNotification('Failed to load project data', 'error');
    } finally {
        hideLoading();
    }
}

async function loadAnalyticsData(projectId) {
    try {
        const response = await fetch(`/insights/api/project/${projectId}/analytics?period=${currentPeriod}`);
        const data = await response.json();
        
        if (data.success) {
            updateCharts(data.analytics);
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

async function loadAIInsights(projectId) {
    try {
        const insightsList = document.getElementById('insightsList');
        insightsList.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i><p>Analyzing your data...</p></div>';
        
        const response = await fetch(`/insights/api/project/${projectId}/insights`);
        const data = await response.json();
        
        if (data.success && data.insights) {
            displayInsights(data.insights);
        } else {
            insightsList.innerHTML = '<div class="empty-state"><i class="fas fa-lightbulb"></i><p>No insights available yet</p></div>';
        }
    } catch (error) {
        console.error('Error loading insights:', error);
        document.getElementById('insightsList').innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Failed to load insights</p></div>';
    }
}

async function loadChatHistory(projectId) {
    try {
        const response = await fetch(`/chat/api/history?project_id=${projectId}&limit=20`);
        const data = await response.json();
        
        if (data.success && data.history) {
            chatHistory = data.history;
            displayChatHistory();
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

// ========================
// CHARTS
// ========================
function updateCharts(analytics) {
    updateNDVIChart(analytics.ndvi);
    updateClimateChart(analytics.climate);
    updateSoilChart(analytics.soil);
}

function updateNDVIChart(data) {
    const ctx = document.getElementById('ndviChart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (charts.ndvi) {
        charts.ndvi.destroy();
    }
    
    const labels = data.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    
    charts.ndvi = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'NDVI Index',
                    data: data.map(d => d.ndvi),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Canopy Cover %',
                    data: data.map(d => d.canopy),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 14 },
                    bodyFont: { size: 13 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateClimateChart(data) {
    const ctx = document.getElementById('climateChart');
    if (!ctx) return;
    
    if (charts.climate) {
        charts.climate.destroy();
    }
    
    const labels = data.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    
    charts.climate = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: data.map(d => d.temperature),
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y',
                    tension: 0.4
                },
                {
                    label: 'Rainfall (mm)',
                    data: data.map(d => d.rainfall),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    type: 'bar'
                },
                {
                    label: 'Humidity (%)',
                    data: data.map(d => d.humidity),
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temperature / Humidity'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Rainfall (mm)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateSoilChart(data) {
    const ctx = document.getElementById('soilChart');
    if (!ctx) return;
    
    if (charts.soil) {
        charts.soil.destroy();
    }
    
    const labels = data.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    
    charts.soil = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Soil Moisture (%)',
                    data: data.map(d => d.moisture),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Soil pH',
                    data: data.map(d => d.ph),
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Moisture (%)'
                    },
                    max: 100
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'pH Level'
                    },
                    min: 0,
                    max: 14,
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// ========================
// INSIGHTS DISPLAY
// ========================
function displayInsights(insights) {
    const insightsList = document.getElementById('insightsList');
    const insightCount = document.getElementById('insightCount');
    
    if (!insights || insights.length === 0) {
        insightsList.innerHTML = '<div class="empty-state"><i class="fas fa-lightbulb"></i><p>No insights available yet</p></div>';
        insightCount.textContent = '0';
        return;
    }
    
    insightCount.textContent = insights.length;
    
    insightsList.innerHTML = insights.map(insight => `
        <div class="insight-item insight-${insight.type}">
            <div class="insight-header">
                <div class="insight-icon">
                    <i class="fas ${getInsightIcon(insight.type)}"></i>
                </div>
                <div class="insight-title-group">
                    <h4>${insight.title}</h4>
                    <span class="insight-category">${insight.category}</span>
                </div>
                <div class="insight-confidence">
                    <span class="confidence-badge">${insight.confidence}%</span>
                </div>
            </div>
            <div class="insight-body">
                <p>${insight.description}</p>
                ${insight.recommendations && insight.recommendations.length > 0 ? `
                    <div class="insight-recommendations">
                        <strong>Recommendations:</strong>
                        <ul>
                            ${insight.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function getInsightIcon(type) {
    const icons = {
        'positive': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'critical': 'fa-times-circle',
        'info': 'fa-info-circle'
    };
    return icons[type] || 'fa-lightbulb';
}

// ========================
// CHAT FUNCTIONALITY
// ========================
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    if (!currentProject) {
        showNotification('Please select a project first', 'warning');
        return;
    }
    
    // Add user message to chat
    addMessageToChat('user', message);
    input.value = '';
    
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
                project_id: currentProject
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator();
        
        if (data.success) {
            addMessageToChat('ai', data.response);
            chatHistory.push({
                message: message,
                response: data.response,
                created_at: data.timestamp
            });
        } else {
            addMessageToChat('ai', 'Sorry, I encountered an error. Please try again.');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        addMessageToChat('ai', 'Sorry, I\'m having trouble connecting. Please check your internet connection.');
    }
}

function addMessageToChat(sender, text) {
    const chatMessages = document.getElementById('chatMessages');
    const welcome = chatMessages.querySelector('.chat-welcome');
    
    // Remove welcome message if exists
    if (welcome) {
        welcome.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    if (sender === 'ai') {
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">${formatMessage(text)}</div>
                <span class="message-time">${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-bubble">${text}</div>
                <span class="message-time">${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessage(text) {
    // Convert markdown-style formatting
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/\n/g, '<br>');
    return text;
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const indicator = document.createElement('div');
    indicator.className = 'chat-message ai-message typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function displayChatHistory() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';
    
    if (chatHistory.length === 0) {
        chatMessages.innerHTML = `
            <div class="chat-welcome">
                <div class="ai-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <h4>👋 Hello! I'm RegenAI</h4>
                <p>Your intelligent assistant for land restoration. Ask me anything about:</p>
                <ul class="welcome-topics">
                    <li><i class="fas fa-leaf"></i> Vegetation health</li>
                    <li><i class="fas fa-chart-line"></i> Data interpretation</li>
                    <li><i class="fas fa-seedling"></i> Restoration strategies</li>
                    <li><i class="fas fa-calendar"></i> Seasonal planning</li>
                </ul>
            </div>
        `;
        return;
    }
    
    chatHistory.forEach(chat => {
        addMessageToChat('user', chat.message);
        addMessageToChat('ai', chat.response);
    });
}

function sendSuggestion(button) {
    const message = button.textContent.trim();
    document.getElementById('chatInput').value = message;
    sendMessage();
}

async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) return;
    
    try {
        const response = await fetch('/chat/api/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_id: currentProject
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            chatHistory = [];
            displayChatHistory();
            showNotification('Chat history cleared', 'success');
        }
    } catch (error) {
        console.error('Error clearing chat:', error);
        showNotification('Failed to clear chat history', 'error');
    }
}

// ========================
// AI STATUS CHECK
// ========================
async function checkAIStatus() {
    try {
        const response = await fetch('/chat/api/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: 'ping',
                project_id: currentProject || 0
            })
        });
        
        isAIOnline = response.ok;
        updateAIStatus();
    } catch (error) {
        isAIOnline = false;
        updateAIStatus();
    }
}

function updateAIStatus() {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    
    if (statusIndicator && statusText) {
        if (isAIOnline) {
            statusIndicator.className = 'status-indicator online';
            statusText.textContent = 'AI Online';
        } else {
            statusIndicator.className = 'status-indicator offline';
            statusText.textContent = 'AI Offline';
        }
    }
}

// ========================
// EVENT LISTENERS
// ========================
function setupEventListeners() {
    // Project selector
    const projectSelector = document.getElementById('projectSelector');
    projectSelector.addEventListener('change', (e) => {
        currentProject = e.target.value ? parseInt(e.target.value) : null;
        if (currentProject) {
            loadProjectData(currentProject);
        }
    });
    
    // Period selector
    const periodSelector = document.getElementById('periodSelector');
    periodSelector.addEventListener('change', (e) => {
        currentPeriod = e.target.value;
        if (currentProject) {
            loadProjectData(currentProject);
        }
    });
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    refreshBtn.addEventListener('click', () => {
        if (currentProject) {
            loadProjectData(currentProject);
            showNotification('Data refreshed', 'success');
        }
    });
    
    // Chat input - Enter key
    const chatInput = document.getElementById('chatInput');
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// ========================
// UTILITY FUNCTIONS
// ========================
function downloadChart(chartId) {
    const chart = charts[chartId.replace('Chart', '')];
    if (!chart) return;
    
    const url = chart.toBase64Image();
    const link = document.createElement('a');
    link.download = `${chartId}-${new Date().toISOString().split('T')[0]}.png`;
    link.href = url;
    link.click();
    
    showNotification('Chart downloaded', 'success');
}

function showLoading() {
    const insightsList = document.getElementById('insightsList');
    insightsList.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i><p>Loading insights...</p></div>';
}

function hideLoading() {
    // Loading is hidden when content is displayed
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    notification.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Remove after 4 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}