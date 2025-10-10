/* ===============================
   RegenArdhi - Dashboard JavaScript
   Modern, Data-Driven Dashboard
   =============================== */

// ========== CONFIGURATION ==========
const CONFIG = {
    API_ENDPOINTS: {
        STATS: '/projects/api/stats',
        PROJECTS: '/projects/api/list',
        MAP_DATA: '/projects/api/map-data'
    },
    REFRESH_INTERVAL: 300000, // 5 minutes
    ANIMATION_DURATION: 1000
};

// ========== STATE ==========
let dashboardState = {
    stats: null,
    projects: [],
    isLoading: true,
    lastUpdate: null,
    userData: null
};

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 RegenArdhi Dashboard Initializing...');
    
    // Load user data from JSON script tag
    loadUserData();
    
    // Initialize all event listeners
    initializeEventListeners();
    
    // Load dashboard data
    loadDashboardData();
    
    // Start auto-refresh
    startAutoRefresh();
    
    console.log('✅ Dashboard Initialized');
});

// ========== USER DATA ==========
function loadUserData() {
    try {
        const userDataScript = document.getElementById('userData');
        if (userDataScript) {
            dashboardState.userData = JSON.parse(userDataScript.textContent);
            console.log('✅ User data loaded:', dashboardState.userData);
        }
    } catch (error) {
        console.error('❌ Error loading user data:', error);
        dashboardState.userData = {};
    }
}

// ========== EVENT LISTENERS ==========
function initializeEventListeners() {
    // User Menu Toggle
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('active');
            closeNotifications();
        });
    }

    // Notification Menu Toggle
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationDropdown = document.getElementById('notificationDropdown');
    
    if (notificationBtn && notificationDropdown) {
        notificationBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationDropdown.classList.toggle('active');
            closeUserMenu();
        });
    }

    // Mark All Read
    const markAllRead = document.getElementById('markAllRead');
    if (markAllRead) {
        markAllRead.addEventListener('click', markAllNotificationsRead);
    }

    // Individual Notifications
    document.querySelectorAll('.notification-item').forEach(item => {
        item.addEventListener('click', () => markNotificationRead(item));
    });

    // Mobile Menu Toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.getElementById('navLinks');
    
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            navLinks.classList.toggle('mobile-open');
            
            const icon = mobileMenuBtn.querySelector('i');
            if (navLinks.classList.contains('mobile-open')) {
                icon.classList.replace('fa-bars', 'fa-times');
            } else {
                icon.classList.replace('fa-times', 'fa-bars');
            }
        });
    }

    // Share Insights Button
    const shareInsightsBtn = document.getElementById('shareInsightsBtn');
    if (shareInsightsBtn) {
        shareInsightsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showSuccess('Share feature coming soon! 🚀');
        });
    }

    // Explore Community Button
    const exploreCommunityBtn = document.getElementById('exploreCommunityBtn');
    if (exploreCommunityBtn) {
        exploreCommunityBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showSuccess('Community features coming soon! 🤝');
        });
    }

    // Close Dropdowns on Outside Click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.user-menu')) {
            closeUserMenu();
        }
        if (!e.target.closest('.notification-menu')) {
            closeNotifications();
        }
        if (!e.target.closest('.nav-links') && !e.target.closest('.mobile-menu-btn')) {
            closeMobileMenu();
        }
    });

    // Flash Messages
    document.querySelectorAll('.close-alert').forEach(btn => {
        btn.addEventListener('click', () => {
            dismissAlert(btn.closest('.alert'));
        });
    });

    // Auto-dismiss flash messages
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => dismissAlert(alert), 5000);
    });

    // Quick Action Buttons (convert any remaining inline handlers)
    document.querySelectorAll('.action-btn').forEach(btn => {
        if (!btn.id && btn.tagName !== 'A') {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const text = btn.querySelector('span')?.textContent || 'Action';
                console.log(`Quick action clicked: ${text}`);
            });
        }
    });
}

// ========== MENU FUNCTIONS ==========
function closeUserMenu() {
    const userDropdown = document.getElementById('userDropdown');
    if (userDropdown) {
        userDropdown.classList.remove('active');
    }
}

function closeNotifications() {
    const notificationDropdown = document.getElementById('notificationDropdown');
    if (notificationDropdown) {
        notificationDropdown.classList.remove('active');
    }
}

function closeMobileMenu() {
    const navLinks = document.getElementById('navLinks');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    
    if (navLinks) {
        navLinks.classList.remove('mobile-open');
    }
    
    if (mobileMenuBtn) {
        const icon = mobileMenuBtn.querySelector('i');
        if (icon) {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    }
}

function dismissAlert(alert) {
    if (!alert) return;
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(100%)';
    setTimeout(() => alert.remove(), 300);
}

// ========== NOTIFICATION FUNCTIONS ==========
function markAllNotificationsRead() {
    const unreadItems = document.querySelectorAll('.notification-item.unread');
    unreadItems.forEach(item => item.classList.remove('unread'));
    updateNotificationBadge();
}

function markNotificationRead(item) {
    if (!item) return;
    item.classList.remove('unread');
    updateNotificationBadge();
}

function updateNotificationBadge() {
    const badge = document.getElementById('notificationBadge');
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;
    
    if (badge) {
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'block' : 'none';
    }
}

// ========== DATA FETCHING ==========
async function loadDashboardData() {
    try {
        dashboardState.isLoading = true;
        
        // Fetch stats and projects in parallel
        const [statsData, projectsData] = await Promise.all([
            fetchStats(),
            fetchProjects()
        ]);
        
        dashboardState.stats = statsData;
        dashboardState.projects = projectsData;
        dashboardState.lastUpdate = new Date();
        dashboardState.isLoading = false;
        
        // Render everything
        renderStats(statsData);
        renderProjects(projectsData);
        animateHealthMetrics();
        
        console.log('✅ Dashboard data loaded successfully');
    } catch (error) {
        console.error('❌ Error loading dashboard:', error);
        showError('Failed to load dashboard data. Please refresh the page.');
        dashboardState.isLoading = false;
    }
}

async function fetchStats() {
    try {
        const response = await fetch(CONFIG.API_ENDPOINTS.STATS);
        const data = await response.json();
        
        if (data.success) {
            return data.stats;
        } else {
            throw new Error('Failed to fetch stats');
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
        return {
            total_projects: 0,
            active_projects: 0,
            total_area: 0,
            total_locations: 0
        };
    }
}

async function fetchProjects() {
    try {
        const response = await fetch(CONFIG.API_ENDPOINTS.PROJECTS);
        const data = await response.json();
        
        if (data.success) {
            return data.projects.slice(0, 3); // Get top 3 recent projects
        } else {
            throw new Error('Failed to fetch projects');
        }
    } catch (error) {
        console.error('Error fetching projects:', error);
        return [];
    }
}

// ========== RENDERING FUNCTIONS ==========
function renderStats(stats) {
    const statsGrid = document.getElementById('statsGrid');
    if (!statsGrid) return;
    
    const statsHTML = `
        <div class="stat-card">
            <div class="stat-icon green">
                <i class="fas fa-seedling"></i>
            </div>
            <div class="stat-content">
                <span class="stat-label">Active Projects</span>
                <p class="stat-number" data-value="${stats.active_projects || 0}">0</p>
                <span class="stat-change positive">+2 this month</span>
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-icon blue">
                <i class="fas fa-map-marked-alt"></i>
            </div>
            <div class="stat-content">
                <span class="stat-label">Land Monitored</span>
                <p class="stat-number" data-value="${Math.round(stats.total_area || 0)}">0<span class="unit">ha</span></p>
                <span class="stat-change positive">+15% coverage</span>
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-icon orange">
                <i class="fas fa-chart-line"></i>
            </div>
            <div class="stat-content">
                <span class="stat-label">Health Score</span>
                <p class="stat-number" data-value="78">0<span class="unit">%</span></p>
                <span class="stat-change positive">+12% improvement</span>
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-icon purple">
                <i class="fas fa-users"></i>
            </div>
            <div class="stat-content">
                <span class="stat-label">Contributors</span>
                <p class="stat-number" data-value="156">0</p>
                <span class="stat-change positive">+23 joined</span>
            </div>
        </div>
    `;
    
    statsGrid.innerHTML = statsHTML;
    
    // Animate numbers
    setTimeout(() => animateStatNumbers(), 100);
}

function renderProjects(projects) {
    const projectsList = document.getElementById('projectsList');
    if (!projectsList) return;
    
    if (projects.length === 0) {
        projectsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <h3>No Projects Yet</h3>
                <p>Create your first land restoration project to get started</p>
                <a href="/projects" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Create Project
                </a>
            </div>
        `;
        return;
    }
    
    const projectsHTML = projects.map(project => {
        const ndviValue = project.vegetation_index || 0;
        const ndviPercent = (ndviValue * 100).toFixed(0);
        const degradationColor = getDegradationColor(project.land_degradation_level);
        
        return `
            <div class="project-item" data-project-id="${project.id}">
                <div class="project-icon">
                    ${getProjectIcon(project.project_type)}
                </div>
                <div class="project-info">
                    <h3>${escapeHtml(project.name)}</h3>
                    <p>${project.area_hectares} ha • ${project.climate_zone || 'Climate data loading...'}</p>
                    ${project.vegetation_index ? `
                        <div class="ndvi-bar">
                            <div class="ndvi-progress">
                                <div class="ndvi-fill" 
                                     style="width: ${ndviPercent}%; background: ${degradationColor}">
                                </div>
                            </div>
                            <span class="ndvi-label">NDVI: ${ndviValue.toFixed(2)}</span>
                        </div>
                    ` : ''}
                </div>
                <div class="project-status">
                    <span class="status-badge ${project.status}">${capitalizeFirst(project.status)}</span>
                    <div class="progress-ring">
                        <span>${project.progress_percentage || 0}%</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    projectsList.innerHTML = projectsHTML;
    
    // Add click handlers to project items
    document.querySelectorAll('.project-item').forEach(item => {
        item.addEventListener('click', () => {
            const projectId = item.dataset.projectId;
            if (projectId) {
                window.location.href = `/projects/${projectId}`;
            }
        });
        
        // Add hover effect
        item.style.cursor = 'pointer';
    });
}

// ========== ANIMATION FUNCTIONS ==========
function animateStatNumbers() {
    const statNumbers = document.querySelectorAll('.stat-number[data-value]');
    
    statNumbers.forEach(element => {
        const targetValue = parseInt(element.dataset.value);
        if (isNaN(targetValue)) return;
        
        const hasUnit = element.querySelector('.unit');
        const duration = CONFIG.ANIMATION_DURATION;
        const increment = targetValue / (duration / 16);
        let currentValue = 0;
        
        const counter = setInterval(() => {
            currentValue += increment;
            
            if (currentValue >= targetValue) {
                currentValue = targetValue;
                clearInterval(counter);
            }
            
            const displayValue = Math.floor(currentValue);
            
            if (hasUnit) {
                const unitHTML = element.querySelector('.unit').outerHTML;
                element.innerHTML = displayValue + unitHTML;
            } else {
                element.textContent = displayValue;
            }
        }, 16);
    });
}

function animateHealthMetrics() {
    const metricFills = document.querySelectorAll('.metric-fill[data-value]');
    
    setTimeout(() => {
        metricFills.forEach(fill => {
            const targetWidth = fill.dataset.value + '%';
            fill.style.width = targetWidth;
        });
    }, 200);
}

// ========== UTILITY FUNCTIONS ==========
function getProjectIcon(type) {
    const icons = {
        'reforestation': '🌲',
        'soil-conservation': '🏔️',
        'watershed': '💧',
        'agroforestry': '🌾'
    };
    return icons[type] || '🌿';
}

function getDegradationColor(level) {
    const colors = {
        'minimal': '#10b981',
        'moderate': '#f59e0b',
        'severe': '#ef4444',
        'critical': '#dc2626'
    };
    return colors[level] || '#6b7280';
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    const alertHTML = `
        <div class="alert alert-error">
            <i class="fas fa-exclamation-circle"></i>
            ${escapeHtml(message)}
            <button class="close-alert"><i class="fas fa-times"></i></button>
        </div>
    `;
    
    let container = document.querySelector('.flash-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-container';
        document.body.appendChild(container);
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHTML;
    const alert = alertDiv.firstElementChild;
    container.appendChild(alert);
    
    const closeBtn = alert.querySelector('.close-alert');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => dismissAlert(alert));
    }
    
    setTimeout(() => dismissAlert(alert), 5000);
}

function showSuccess(message) {
    const alertHTML = `
        <div class="alert alert-success">
            <i class="fas fa-check-circle"></i>
            ${escapeHtml(message)}
            <button class="close-alert"><i class="fas fa-times"></i></button>
        </div>
    `;
    
    let container = document.querySelector('.flash-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-container';
        document.body.appendChild(container);
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHTML;
    const alert = alertDiv.firstElementChild;
    container.appendChild(alert);
    
    const closeBtn = alert.querySelector('.close-alert');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => dismissAlert(alert));
    }
    
    setTimeout(() => dismissAlert(alert), 3000);
}

// ========== AUTO REFRESH ==========
function startAutoRefresh() {
    setInterval(() => {
        console.log('🔄 Auto-refreshing dashboard data...');
        loadDashboardData();
    }, CONFIG.REFRESH_INTERVAL);
}

// ========== FORMAT UTILITIES ==========
function formatNumber(num) {
    if (!num) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatRelativeTime(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (seconds < 60) return 'just now';
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (days < 30) return `${days} day${days > 1 ? 's' : ''} ago`;
    return new Date(date).toLocaleDateString();
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatCurrency(amount, currency = 'KES') {
    if (!amount) return `${currency} 0`;
    return `${currency} ${formatNumber(amount)}`;
}

function formatPercentage(value, decimals = 0) {
    if (!value) return '0%';
    return `${value.toFixed(decimals)}%`;
}

// ========== PROJECT UTILITIES ==========
function getStatusBadgeClass(status) {
    const classes = {
        'active': 'status-badge active',
        'planning': 'status-badge planning',
        'completed': 'status-badge completed',
        'paused': 'status-badge paused'
    };
    return classes[status] || 'status-badge';
}

function getDegradationLabel(level) {
    const labels = {
        'minimal': 'Minimal Degradation',
        'moderate': 'Moderate Degradation',
        'severe': 'Severe Degradation',
        'critical': 'Critical Degradation'
    };
    return labels[level] || 'Unknown';
}

// ========== EXPORT FUNCTIONS ==========
window.dashboardUtils = {
    // Data functions
    refreshData: loadDashboardData,
    fetchStats,
    fetchProjects,
    getUserData: () => dashboardState.userData,
    
    // Format functions
    formatNumber,
    formatRelativeTime,
    formatDate,
    formatCurrency,
    formatPercentage,
    
    // UI functions
    showError,
    showSuccess,
    dismissAlert,
    
    // Project functions
    getProjectIcon,
    getDegradationColor,
    getDegradationLabel,
    getStatusBadgeClass,
    capitalizeFirst,
    escapeHtml
};

// ========== DEBUG MODE ==========
if (window.location.search.includes('debug=true')) {
    console.log('🐛 Debug mode enabled');
    console.log('Dashboard State:', dashboardState);
    console.log('Configuration:', CONFIG);
    
    window.dashboard = {
        state: dashboardState,
        config: CONFIG,
        reload: loadDashboardData,
        stats: fetchStats,
        projects: fetchProjects,
        utils: window.dashboardUtils
    };
    
    console.log('💡 Access dashboard object via window.dashboard');
    console.log('💡 Example: window.dashboard.reload()');
}

// ========== ERROR HANDLING ==========
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});

// ========== VISIBILITY CHANGE HANDLER ==========
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        console.log('👀 Tab visible again, refreshing data...');
        loadDashboardData();
    }
});

// ========== ONLINE/OFFLINE DETECTION ==========
window.addEventListener('online', () => {
    showSuccess('Connection restored. Refreshing data...');
    loadDashboardData();
});

window.addEventListener('offline', () => {
    showError('No internet connection. Some features may not work.');
});

// ========== SMOOTH SCROLL FOR ANCHOR LINKS ==========
document.addEventListener('click', (e) => {
    const target = e.target.closest('a');
    if (target && target.getAttribute('href')?.startsWith('#')) {
        const href = target.getAttribute('href');
        const element = document.querySelector(href);
        if (href !== '#' && element) {
            e.preventDefault();
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
});

// ========== CONSOLE WELCOME MESSAGE ==========
console.log('%c🌿 RegenArdhi Dashboard', 'color: #10b981; font-size: 24px; font-weight: bold;');
console.log('%cAI-Powered Land Restoration Platform', 'color: #6b7280; font-size: 14px;');
console.log('%cVersion 2.0 - Built with ❤️ for a Greener Future', 'color: #6b7280; font-size: 12px;');
console.log('%c---', 'color: #e5e7eb;');
console.log('%cAdd ?debug=true to URL for debug mode', 'color: #3b82f6; font-size: 11px;');

// ========== END ==========