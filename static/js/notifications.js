// ========================================
// REGENARDHI - REUSABLE NOTIFICATION SYSTEM
// Fixed version with proper error handling
// ========================================

const NotificationSystem = {
    state: {
        notifications: [],
        unreadCount: 0,
        isOpen: false,
        autoRefreshInterval: null
    },

    // ========================
    // INITIALIZATION
    // ========================
    
    init() {
        console.log('🔔 Initializing Notification System...');
        
        // Check if notification panel exists, if not create it
        if (!document.getElementById('notificationPanel')) {
            this.createNotificationPanel();
        }
        
        // Check if live notification container exists
        if (!document.getElementById('liveNotification')) {
            this.createLiveNotificationContainer();
        }
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load notifications
        this.loadNotifications();
        
        // Auto-refresh every 30 seconds
        this.state.autoRefreshInterval = setInterval(() => {
            this.loadNotifications(true); // silent refresh
        }, 30000);
        
        console.log('✅ Notification System Ready!');
    },

    // ========================
    // CREATE UI COMPONENTS
    // ========================
    
    createNotificationPanel() {
        const panel = document.createElement('div');
        panel.id = 'notificationPanel';
        panel.className = 'notification-panel';
        panel.innerHTML = `
            <div class="notification-header">
                <h3><i class="fas fa-bell"></i> Notifications</h3>
                <div class="notification-actions">
                    <button class="btn-text" onclick="NotificationSystem.markAllAsRead()">
                        Mark all read
                    </button>
                    <button class="btn-close-panel" onclick="NotificationSystem.closePanel()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="notification-list" id="notificationList">
                <div class="loading-state">
                    <div class="loader-ring"></div>
                    <p>Loading notifications...</p>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
    },

    createLiveNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'liveNotification';
        container.className = 'live-notification';
        container.innerHTML = `
            <div class="live-notif-icon" id="liveNotifIcon">
                <i class="fas fa-check-circle"></i>
            </div>
            <div class="live-notif-content">
                <div class="live-notif-title" id="liveNotifTitle">Notification</div>
                <div class="live-notif-message" id="liveNotifMessage">Message</div>
            </div>
            <button class="live-notif-close" onclick="NotificationSystem.closeLiveNotification()">
                <i class="fas fa-times"></i>
            </button>
        `;
        document.body.appendChild(container);
    },

    // ========================
    // EVENT LISTENERS
    // ========================
    
    setupEventListeners() {
        // Notification button click
        const notifBtn = document.getElementById('notificationBtn');
        if (notifBtn) {
            notifBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.togglePanel();
            });
        }

        // Close panel when clicking outside
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('notificationPanel');
            const notifBtn = document.getElementById('notificationBtn');
            
            if (panel && this.state.isOpen && 
                !panel.contains(e.target) && 
                e.target !== notifBtn &&
                !notifBtn?.contains(e.target)) {
                this.closePanel();
            }
        });

        // Prevent panel close when clicking inside
        const panel = document.getElementById('notificationPanel');
        if (panel) {
            panel.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    },

    // ========================
    // LOAD NOTIFICATIONS
    // ========================
    
    async loadNotifications(silent = false) {
        try {
            const response = await fetch('/notifications/api/list');
            const data = await response.json();
            
            if (data.success) {
                const oldUnreadCount = this.state.unreadCount;
                
                this.state.notifications = data.notifications || [];
                this.state.unreadCount = data.unread_count || 0;
                
                // Update badge
                this.updateBadge();
                
                // If not silent and unread count increased, show animation
                if (!silent && this.state.unreadCount > oldUnreadCount) {
                    const badge = document.getElementById('notificationBadge');
                    if (badge) {
                        badge.classList.add('new-notification');
                        setTimeout(() => badge.classList.remove('new-notification'), 600);
                    }
                }
                
                // Render if panel is open
                if (this.state.isOpen) {
                    this.renderNotifications();
                }
                
                console.log(`🔔 Loaded ${this.state.notifications.length} notifications (${this.state.unreadCount} unread)`);
            } else {
                console.error('Failed to load notifications:', data.error);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    },

    // ========================
    // RENDER NOTIFICATIONS
    // ========================
    
    renderNotifications() {
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        if (this.state.notifications.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-bell-slash"></i>
                    <h3>All Caught Up!</h3>
                    <p>You don't have any notifications</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.state.notifications.map(notif => this.createNotificationHTML(notif)).join('');
    },

    createNotificationHTML(notif) {
        const iconMap = {
            'project_created': 'fa-check-circle',
            'project_updated': 'fa-edit',
            'status_changed': 'fa-exchange-alt',
            'project_completed': 'fa-trophy',
            'project_deleted': 'fa-trash',
            'progress_updated': 'fa-chart-line',
            'analysis_complete': 'fa-brain',
            'milestone_reached': 'fa-flag-checkered',
            'system': 'fa-info-circle'
        };
        
        const icon = notif.icon || iconMap[notif.type] || 'fa-bell';
        const unreadClass = !notif.is_read ? 'unread' : '';
        
        // FIX: Use proper escaping and safe link handling
        const safeLink = notif.link && notif.link !== 'null' ? this.escapeHtml(notif.link) : '';
        
        return `
            <div class="notification-item ${unreadClass}" 
                 data-type="${this.escapeHtml(notif.type)}"
                 onclick="NotificationSystem.handleNotificationClick(${notif.id}, '${safeLink}')">
                <div class="notification-item-header">
                    <span class="notification-item-title">
                        <i class="fas ${icon}"></i>
                        ${this.escapeHtml(notif.title)}
                    </span>
                    <span class="notification-item-time">${this.formatTimeAgo(notif.created_at)}</span>
                </div>
                <div class="notification-item-message">${this.escapeHtml(notif.message)}</div>
            </div>
        `;
    },

    // ========================
    // ACTIONS
    // ========================
    
    async handleNotificationClick(notificationId, link) {
        try {
            // Mark as read
            await fetch('/notifications/api/mark-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notification_id: notificationId })
            });
            
            // Reload notifications
            await this.loadNotifications();
            
            // Navigate if link provided and valid
            if (link && link !== '' && link !== 'null' && link !== 'None') {
                this.closePanel();
                window.location.href = link;
            }
        } catch (error) {
            console.error('Error handling notification click:', error);
            this.showToast('Error processing notification', 'error');
        }
    },

    async markAllAsRead() {
        try {
            const response = await fetch('/notifications/api/mark-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            const data = await response.json();
            
            if (data.success) {
                await this.loadNotifications();
                this.showToast('All notifications marked as read', 'success');
            } else {
                this.showToast('Failed to mark as read', 'error');
            }
        } catch (error) {
            console.error('Error marking all as read:', error);
            this.showToast('Error marking notifications as read', 'error');
        }
    },

    // ========================
    // PANEL CONTROLS
    // ========================
    
    togglePanel() {
        const panel = document.getElementById('notificationPanel');
        if (!panel) return;
        
        if (this.state.isOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    },

    openPanel() {
        const panel = document.getElementById('notificationPanel');
        if (!panel) return;
        
        panel.classList.add('show');
        this.state.isOpen = true;
        
        // Render notifications
        this.renderNotifications();
    },

    closePanel() {
        const panel = document.getElementById('notificationPanel');
        if (!panel) return;
        
        panel.classList.remove('show');
        this.state.isOpen = false;
    },

    // ========================
    // BADGE UPDATE
    // ========================
    
    updateBadge() {
        const badges = document.querySelectorAll('#notificationBadge, #navBadge');
        
        badges.forEach(badge => {
            if (!badge) return;
            
            badge.textContent = this.state.unreadCount;
            
            if (this.state.unreadCount > 0) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        });
    },

    // ========================
    // LIVE NOTIFICATION (Google Cloud Style)
    // ========================
    
    showLiveNotification(title, message, type = 'success', duration = 5000) {
        const container = document.getElementById('liveNotification');
        if (!container) return;
        
        const iconEl = document.getElementById('liveNotifIcon');
        const titleEl = document.getElementById('liveNotifTitle');
        const messageEl = document.getElementById('liveNotifMessage');
        
        if (!iconEl || !titleEl || !messageEl) return;
        
        // Set icon based on type
        const icons = {
            'success': 'fa-check-circle',
            'info': 'fa-info-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle',
            'completed': 'fa-trophy',
            'milestone': 'fa-flag-checkered'
        };
        
        iconEl.innerHTML = `<i class="fas ${icons[type] || icons.success}"></i>`;
        titleEl.textContent = title;
        messageEl.textContent = message;
        
        // Add type class
        container.className = 'live-notification ' + type;
        
        // Show with animation
        setTimeout(() => container.classList.add('show'), 10);
        
        // Auto-hide after duration
        setTimeout(() => {
            this.closeLiveNotification();
        }, duration);
    },

    closeLiveNotification() {
        const container = document.getElementById('liveNotification');
        if (container) {
            container.classList.remove('show');
        }
    },

    // ========================
    // SHOW CREATING ANIMATION
    // ========================
    
    showCreatingAnimation(message = 'Creating project...') {
        const overlay = document.createElement('div');
        overlay.id = 'creatingOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
            z-index: 10002;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        overlay.innerHTML = `
            <div class="creating-project-animation">
                <div class="creating-loader"></div>
                <div class="creating-text">${message}</div>
                <div class="creating-subtext">Analyzing location with AI...</div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Animate in
        setTimeout(() => {
            overlay.style.opacity = '1';
        }, 10);
    },

    hideCreatingAnimation() {
        const overlay = document.getElementById('creatingOverlay');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => overlay.remove(), 300);
        }
    },

    // ========================
    // NOTIFICATION TRIGGERS (Call from other modules)
    // ========================
    
    async notifyProjectCreated(projectName) {
        this.showLiveNotification(
            'Project Created!',
            `"${projectName}" has been successfully created with AI analysis`,
            'success',
            6000
        );
        
        // Reload to get the new notification from backend
        await this.loadNotifications();
    },

    async notifyProjectUpdated(projectName) {
        this.showLiveNotification(
            'Project Updated',
            `"${projectName}" has been updated`,
            'info',
            4000
        );
        
        await this.loadNotifications();
    },

    async notifyStatusChanged(projectName, newStatus) {
        const statusMessages = {
            'planning': 'is now in planning phase',
            'active': 'is now active',
            'completed': 'has been completed! 🎉',
            'paused': 'has been paused'
        };
        
        const type = newStatus === 'completed' ? 'completed' : 'warning';
        
        this.showLiveNotification(
            'Status Changed',
            `"${projectName}" ${statusMessages[newStatus] || 'status updated'}`,
            type,
            5000
        );
        
        await this.loadNotifications();
    },

    async notifyProgressUpdated(projectName, progress) {
        // Check for milestones
        const milestones = [25, 50, 75];
        if (milestones.includes(progress)) {
            this.showLiveNotification(
                'Milestone Reached! 🎯',
                `"${projectName}" reached ${progress}% completion`,
                'milestone',
                6000
            );
        } else {
            this.showLiveNotification(
                'Progress Updated',
                `"${projectName}" is now ${progress}% complete`,
                'info',
                4000
            );
        }
        
        await this.loadNotifications();
    },

    async notifyProjectDeleted(projectName) {
        this.showLiveNotification(
            'Project Deleted',
            `"${projectName}" has been deleted`,
            'error',
            4000
        );
        
        await this.loadNotifications();
    },

    async notifyAnalysisComplete(projectName) {
        this.showLiveNotification(
            'AI Analysis Complete',
            `Analysis finished for "${projectName}"`,
            'info',
            5000
        );
        
        await this.loadNotifications();
    },

    // ========================
    // GCP-STYLE CARD ANIMATIONS
    // ========================
    
    animateCardAction(projectId, actionType) {
        const cards = document.querySelectorAll(`[data-project-id="${projectId}"]`);
        
        if (cards.length === 0) return;
        
        cards.forEach(card => {
            // Remove any existing animation classes
            card.classList.remove('deleting', 'updating', 'status-changing');
            
            // Add appropriate animation class based on action
            switch(actionType) {
                case 'delete':
                    card.classList.add('deleting');
                    break;
                case 'update':
                    card.classList.add('updating');
                    break;
                case 'status':
                    card.classList.add('status-changing');
                    break;
            }
            
            // Remove animation class after animation completes
            setTimeout(() => {
                card.classList.remove('deleting', 'updating', 'status-changing');
            }, 800);
        });
    },

    // ========================
    // UTILITY FUNCTIONS
    // ========================
    
    formatTimeAgo(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    },

    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    },

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        
        toast.innerHTML = `
            <i class="fas fa-${icons[type] || 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.cssText = `
                position: fixed;
                top: 90px;
                right: 24px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 12px;
            `;
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    // ========================
    // CLEANUP
    // ========================
    
    destroy() {
        if (this.state.autoRefreshInterval) {
            clearInterval(this.state.autoRefreshInterval);
        }
        
        const panel = document.getElementById('notificationPanel');
        const liveNotif = document.getElementById('liveNotification');
        
        if (panel) panel.remove();
        if (liveNotif) liveNotif.remove();
        
        console.log('🔔 Notification System Destroyed');
    }
};

// ========================
// AUTO-INITIALIZE ON DOM READY
// ========================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        NotificationSystem.init();
    });
} else {
    NotificationSystem.init();
}

// ========================
// EXPORT FOR USE IN OTHER MODULES
// ========================

// Make it available globally
window.NotificationSystem = NotificationSystem;

// Also export for ES6 modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationSystem;
}

console.log('✅ Notification System Loaded!');