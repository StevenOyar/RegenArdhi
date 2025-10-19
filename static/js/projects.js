// ========================================
// REGENARDHI - REDESIGNED PROJECTS JS
// Modern, Clean, Animated
// ========================================

// Global State
const state = {
    projects: [],
    filteredProjects: [],
    selectedStatus: 'all',
    searchTerm: '',
    sortBy: 'recent',
    selectedProject: null,
    maps: {
        main: null,
        modal: null
    },
    markers: {
        main: [],
        modal: null
    },
    editMode: false,
    notifications: [],
    unreadCount: 0,
    statusChangeProject: null,
    newStatus: null
};

// ========================
// INITIALIZATION
// ========================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 RegenArdhi Projects - Initializing...');
    
    initializeNavigation();
    initializeEventListeners();
    loadProjects();
    loadNotifications();
    checkGPSAvailability();
    
    // Refresh notifications every 30 seconds
    setInterval(loadNotifications, 30000);
});

// ========================
// NAVIGATION
// ========================

function initializeNavigation() {
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationPanel = document.getElementById('notificationPanel');
    
    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('show');
        });
        
        document.addEventListener('click', () => {
            userDropdown.classList.remove('show');
        });
    }
    
    if (mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
    
    if (notificationBtn && notificationPanel) {
        notificationBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationPanel.classList.toggle('show');
        });
        
        document.addEventListener('click', (e) => {
            if (!notificationPanel.contains(e.target) && e.target !== notificationBtn) {
                notificationPanel.classList.remove('show');
            }
        });
    }
}

// ========================
// EVENT LISTENERS
// ========================

function initializeEventListeners() {
    // New project button
    document.getElementById('quickCreateBtn')?.addEventListener('click', openProjectModal);
    
    // Form submission
    document.getElementById('projectForm')?.addEventListener('submit', handleProjectSubmit);
    document.getElementById('latitude')?.addEventListener('change', updateModalMarker);
    document.getElementById('longitude')?.addEventListener('change', updateModalMarker);
    
    // Search and filters
    document.getElementById('searchProjects')?.addEventListener('input', (e) => {
        state.searchTerm = e.target.value;
        filterAndRenderProjects();
    });
    
    document.getElementById('sortProjects')?.addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        filterAndRenderProjects();
    });
    
    // Status filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            state.selectedStatus = btn.dataset.status;
            updateStatusFilters();
            filterAndRenderProjects();
        });
    });
    
    // Close modals on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        });
    });
}

// ========================
// DATA LOADING
// ========================

async function loadProjects() {
    console.log('📊 Loading projects...');
    
    try {
        const response = await fetch('/projects/api/list');
        const data = await response.json();
        
        if (data.success) {
            state.projects = data.projects || [];
            
            updateStatistics();
            updateStatusCounts();
            renderRecentProjects();
            filterAndRenderProjects();
            
            // IMPORTANT: Set initial progress bar widths after rendering
            setTimeout(() => {
                initializeProgressBars();
            }, 100);
            
            // Initialize map if it's expanded
            if (!document.getElementById('mapSection').classList.contains('collapsed')) {
                initializeMainMap();
                updateMainMap();
            }
            
            console.log(`✅ Loaded ${state.projects.length} projects`);
        } else {
            showToast(data.error || 'Failed to load projects', 'error');
            showEmptyState();
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        showToast('Error connecting to server', 'error');
        showEmptyState();
    }
}

// Add this NEW function to initialize progress bars with correct widths
function initializeProgressBars() {
    state.projects.forEach(project => {
        const cards = document.querySelectorAll(`[data-project-id="${project.id}"]`);
        cards.forEach(card => {
            const progressFill = card.querySelector('.progress-fill');
            const progressValue = card.querySelector('.progress-value');
            
            if (progressFill && progressValue) {
                const progress = parseInt(project.progress_percentage || 0);
                progressFill.style.width = progress + '%';
                progressValue.textContent = progress + '%';
            }
        });
    });
}

// ========================
// NOTIFICATIONS
// ========================

async function loadNotifications() {
    try {
        const response = await fetch('/notifications/api/list');
        const data = await response.json();
        
        if (data.success) {
            state.notifications = data.notifications || [];
            state.unreadCount = data.unread_count || 0;
            
            updateNotificationBadge();
            renderNotifications();
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}


// ========================================
// KEY CHANGES TO projects.js FOR NOTIFICATIONS
// Add these updates to your existing projects.js
// ========================================

// UPDATE: handleProjectSubmit function
async function handleProjectSubmit(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('projectId')?.value;
    const formData = {
        name: document.getElementById('projectName')?.value,
        description: document.getElementById('projectDescription')?.value || '',
        project_type: document.getElementById('projectType')?.value,
        area_hectares: parseFloat(document.getElementById('projectArea')?.value),
        latitude: parseFloat(document.getElementById('latitude')?.value),
        longitude: parseFloat(document.getElementById('longitude')?.value)
    };
    
    if (!formData.name || !formData.project_type || !formData.area_hectares || 
        !formData.latitude || !formData.longitude) {
        NotificationSystem.showToast('Please fill all required fields', 'warning');
        return;
    }
    
    // 🆕 Show creating animation
    NotificationSystem.showCreatingAnimation(
        projectId ? 'Updating project...' : 'Creating project with AI analysis...'
    );
    
    try {
        const url = projectId ? `/projects/${projectId}/update` : '/projects/create';
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        // 🆕 Hide creating animation
        NotificationSystem.hideCreatingAnimation();
        
        if (data.success) {
            // 🆕 Show appropriate live notification
            if (projectId) {
                NotificationSystem.notifyProjectUpdated(formData.name);
            } else {
                NotificationSystem.notifyProjectCreated(formData.name);
            }
            
            closeProjectModal();
            await loadProjects();
        } else {
            NotificationSystem.showToast(data.error || 'Failed to save project', 'error');
        }
    } catch (error) {
        console.error('Form submit error:', error);
        NotificationSystem.hideCreatingAnimation();
        NotificationSystem.showToast('Error saving project', 'error');
    }
}

// UPDATE: confirmStatusChange function
window.confirmStatusChange = async function() {
    if (!state.statusChangeProject || !state.newStatus) {
        NotificationSystem.showToast('Please select a status', 'warning');
        return;
    }
    
    const project = state.projects.find(p => p.id === state.statusChangeProject);
    const projectName = project ? project.name : 'Project';
    
    const requestData = { status: state.newStatus };
    
    // Include progress if status is 'active'
    if (state.newStatus === 'active') {
        const progressSlider = document.getElementById('progressSlider');
        if (progressSlider) {
            requestData.progress_percentage = parseInt(progressSlider.value);
        }
    } else if (state.newStatus === 'planning') {
        requestData.progress_percentage = 0;
    } else if (state.newStatus === 'completed') {
        requestData.progress_percentage = 100;
    }
    
    console.log('📤 Sending status update:', requestData);
    
    const confirmBtn = event.target;
    const originalHTML = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    
    try {
        const response = await fetch(`/projects/${state.statusChangeProject}/update-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ Status update successful:', data);
            
            // Update the project in state with actual saved data
            const projectIndex = state.projects.findIndex(p => p.id === state.statusChangeProject);
            if (projectIndex !== -1 && data.project) {
                state.projects[projectIndex].status = data.project.status;
                state.projects[projectIndex].progress_percentage = data.project.progress_percentage;
                console.log(`✅ Updated local state - Progress: ${data.project.progress_percentage}%`);
            }
            
            // 🆕 Show status change notification
            NotificationSystem.notifyStatusChanged(projectName, state.newStatus);
            
            // 🆕 Show progress notification if applicable
            if (requestData.progress_percentage !== undefined) {
                NotificationSystem.notifyProgressUpdated(projectName, requestData.progress_percentage);
            }
            
            // Animate the progress bar update using actual saved value
            if (data.project && data.project.progress_percentage !== undefined) {
                await animateProgressUpdate(state.statusChangeProject, data.project.progress_percentage);
            }
            
            // Close modal
            closeStatusModal();
            
            // Reload projects to ensure everything is in sync
            await loadProjects();
            
        } else {
            console.error('❌ Update failed:', data.error);
            NotificationSystem.showToast(data.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('❌ Status update error:', error);
        NotificationSystem.showToast('Error updating status', 'error');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalHTML;
    }
};

// UPDATE: deleteProject function
window.deleteProject = async function(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    const projectName = project ? project.name : 'this project';
    
    if (!confirm(`Are you sure you want to delete "${projectName}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/projects/${projectId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 🆕 Show deletion notification
            NotificationSystem.notifyProjectDeleted(projectName);
            
            await loadProjects();
        } else {
            NotificationSystem.showToast(data.error || 'Failed to delete project', 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        NotificationSystem.showToast('Error deleting project', 'error');
    }
};

// UPDATE: handleQuickCreate function
async function handleQuickCreate() {
    const btn = event.target.closest('button');
    if (!btn) return;
    
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    
    // 🆕 Show live notification
    NotificationSystem.showLiveNotification(
        '📍 Getting Location',
        'Detecting your GPS coordinates...',
        'info',
        3000
    );
    
    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            });
        });
        
        const projectData = {
            name: `Quick Project - ${new Date().toLocaleString()}`,
            description: 'Quick-created project using GPS location',
            project_type: 'reforestation',
            area_hectares: 10,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
        };
        
        // 🆕 Show creating animation
        NotificationSystem.showCreatingAnimation('Creating project with AI analysis...');
        
        const response = await fetch('/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData)
        });
        
        const data = await response.json();
        
        // 🆕 Hide creating animation
        NotificationSystem.hideCreatingAnimation();
        
        if (data.success) {
            // 🆕 Show success notification
            NotificationSystem.notifyProjectCreated(projectData.name);
            
            await loadProjects();
        } else {
            NotificationSystem.showToast(data.error || 'Failed to create project', 'error');
        }
    } catch (error) {
        console.error('Quick create error:', error);
        
        // 🆕 Hide creating animation if shown
        NotificationSystem.hideCreatingAnimation();
        
        if (error.code === 1) {
            NotificationSystem.showToast('Please enable location access to use Quick Create', 'warning');
        } else {
            NotificationSystem.showToast('Failed to create project. Please try manual creation.', 'error');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

// 🆕 NEW: Function to show analysis complete notification
async function reanalyzeProject(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) return;
    
    // Show creating animation
    NotificationSystem.showCreatingAnimation('Re-analyzing with AI...');
    
    try {
        const response = await fetch(`/projects/${projectId}/reanalyze`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        NotificationSystem.hideCreatingAnimation();
        
        if (data.success) {
            // 🆕 Show analysis complete notification
            NotificationSystem.notifyAnalysisComplete(project.name);
            
            await loadProjects();
        } else {
            NotificationSystem.showToast('Analysis failed', 'error');
        }
    } catch (error) {
        NotificationSystem.hideCreatingAnimation();
        NotificationSystem.showToast('Error during analysis', 'error');
    }
}

// 🆕 NEW: Replace all showToast calls with NotificationSystem.showToast
// Example - Update loadProjects error handling:
async function loadProjects() {
    console.log('📊 Loading projects...');
    
    try {
        const response = await fetch('/projects/api/list');
        const data = await response.json();
        
        if (data.success) {
            state.projects = data.projects || [];
            
            updateStatistics();
            updateStatusCounts();
            renderRecentProjects();
            filterAndRenderProjects();
            
            setTimeout(() => {
                initializeProgressBars();
            }, 100);
            
            if (!document.getElementById('mapSection').classList.contains('collapsed')) {
                initializeMainMap();
                updateMainMap();
            }
            
            console.log(`✅ Loaded ${state.projects.length} projects`);
        } else {
            // 🆕 Use NotificationSystem
            NotificationSystem.showToast(data.error || 'Failed to load projects', 'error');
            showEmptyState();
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        // 🆕 Use NotificationSystem
        NotificationSystem.showToast('Error connecting to server', 'error');
        showEmptyState();
    }
}

// 🆕 NEW: Update error handlers in other functions
window.useCurrentLocation = function() {
    NotificationSystem.showLiveNotification(
        '📍 Getting Location',
        'Accessing your GPS...',
        'info',
        3000
    );
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude.toFixed(6);
            const lng = position.coords.longitude.toFixed(6);
            
            document.getElementById('latitude').value = lat;
            document.getElementById('longitude').value = lng;
            
            updateModalMarker();
            
            // 🆕 Use NotificationSystem
            NotificationSystem.showToast('✅ Location detected successfully!', 'success');
        },
        (error) => {
            let message = 'Could not get your location';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = 'Location permission denied. Please enable GPS.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = 'Location information unavailable';
                    break;
                case error.TIMEOUT:
                    message = 'Location request timed out';
                    break;
            }
            // 🆕 Use NotificationSystem
            NotificationSystem.showToast(message, 'error');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
};


console.log('✅ Projects.js with Notification Integration Ready!');
function updateNotificationBadge() {
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        badge.textContent = state.unreadCount;
        if (state.unreadCount > 0) {
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

function renderNotifications() {
    const container = document.getElementById('notificationList');
    if (!container) return;
    
    if (state.notifications.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 2rem;">
                <i class="fas fa-bell-slash"></i>
                <p>No notifications yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.notifications.map(notif => `
        <div class="notification-item ${!notif.is_read ? 'unread' : ''}" 
             onclick="handleNotificationClick(${notif.id}, '${notif.link || ''}')">
            <div class="notification-item-header">
                <span class="notification-item-title">
                    <i class="fas fa-${notif.icon || 'info-circle'}"></i>
                    ${escapeHtml(notif.title)}
                </span>
                <span class="notification-item-time">${formatTimeAgo(notif.created_at)}</span>
            </div>
            <div class="notification-item-message">${escapeHtml(notif.message)}</div>
        </div>
    `).join('');
}

async function handleNotificationClick(notificationId, link) {
    try {
        await fetch('/notifications/api/mark-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notification_id: notificationId })
        });
        
        await loadNotifications();
        
        if (link) {
            window.location.href = link;
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

window.markAllRead = async function() {
    try {
        await fetch('/notifications/api/mark-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        await loadNotifications();
        showToast('All notifications marked as read', 'success');
    } catch (error) {
        console.error('Error marking all as read:', error);
        showToast('Failed to mark notifications as read', 'error');
    }
};

window.closeNotificationPanel = function() {
    document.getElementById('notificationPanel')?.classList.remove('show');
};

// ========================
// GPS FUNCTIONALITY
// ========================

function checkGPSAvailability() {
    if ("geolocation" in navigator) {
        console.log('✓ GPS available');
    } else {
        console.log('✗ GPS not available');
    }
}

window.useCurrentLocation = function() {
    showToast('📍 Getting your location...', 'info');
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude.toFixed(6);
            const lng = position.coords.longitude.toFixed(6);
            
            document.getElementById('latitude').value = lat;
            document.getElementById('longitude').value = lng;
            
            updateModalMarker();
            showToast('✅ Location detected successfully!', 'success');
        },
        (error) => {
            let message = 'Could not get your location';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = 'Location permission denied. Please enable GPS.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = 'Location information unavailable';
                    break;
                case error.TIMEOUT:
                    message = 'Location request timed out';
                    break;
            }
            showToast(message, 'error');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
};

// ========================
// FILTERING & SORTING
// ========================

function filterAndRenderProjects() {
    let filtered = state.projects;
    
    // Apply status filter
    if (state.selectedStatus !== 'all') {
        filtered = filtered.filter(p => p.status === state.selectedStatus);
    }
    
    // Apply search
    if (state.searchTerm) {
        const term = state.searchTerm.toLowerCase();
        filtered = filtered.filter(p => 
            p.name.toLowerCase().includes(term) ||
            (p.location && p.location.toLowerCase().includes(term)) ||
            (p.description && p.description.toLowerCase().includes(term))
        );
    }
    
    // Apply sorting
    filtered = sortProjects(filtered, state.sortBy);
    
    state.filteredProjects = filtered;
    
    // Only render in the all projects panel (if it's open)
    if (document.getElementById('allProjectsPanel')?.classList.contains('show')) {
        renderAllProjects();
    }
}

function sortProjects(projects, sortBy) {
    const sorted = [...projects];
    
    switch(sortBy) {
        case 'recent':
            sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            break;
        case 'name':
            sorted.sort((a, b) => a.name.localeCompare(b.name));
            break;
        case 'area':
            sorted.sort((a, b) => parseFloat(b.area_hectares || 0) - parseFloat(a.area_hectares || 0));
            break;
        case 'progress':
            sorted.sort((a, b) => parseInt(b.progress_percentage || 0) - parseInt(a.progress_percentage || 0));
            break;
    }
    
    return sorted;
}

function updateStatusFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.status === state.selectedStatus) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function updateStatusCounts() {
    const counts = {
        all: state.projects.length,
        active: state.projects.filter(p => p.status === 'active').length,
        planning: state.projects.filter(p => p.status === 'planning').length,
        completed: state.projects.filter(p => p.status === 'completed').length,
        paused: state.projects.filter(p => p.status === 'paused').length
    };
    
    Object.keys(counts).forEach(status => {
        const elem = document.getElementById(`count${status.charAt(0).toUpperCase() + status.slice(1)}`);
        if (elem) elem.textContent = counts[status];
    });
}

// ========================
// RENDER FUNCTIONS
// ========================

function renderProjects() {
    // This function now only renders recent projects
    // All projects are rendered in the floating panel
    renderRecentProjects();
}

function renderRecentProjects() {
    const section = document.getElementById('recentProjectsSection');
    const container = document.getElementById('recentProjectsGrid');
    
    if (!section || !container) return;
    
    // Get 2-3 most recent projects
    const recentProjects = [...state.projects]
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 3);
    
    if (recentProjects.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    container.innerHTML = recentProjects.map(project => createProjectCard(project)).join('');
}
function createProjectCard(project) {
    const statusColors = {
        'planning': '#3b82f6',
        'active': '#10b981',
        'completed': '#8b5cf6',
        'paused': '#f59e0b'
    };
    
    const typeIcons = {
        'reforestation': '🌲',
        'soil-conservation': '🏔️',
        'watershed': '💧',
        'agroforestry': '🌾'
    };
    
    return `
    <div class="project-card" data-project-id="${project.id}" data-status="${project.status}" onclick="viewProjectDetails(${project.id})">
            <!-- Rest of the card content remains the same -->
            <div class="project-card-header">
                <div class="project-card-title">
                    <h4>
                        <span class="project-type-icon">${typeIcons[project.project_type] || '🌿'}</span>
                        ${escapeHtml(project.name)}
                    </h4>
                    <span class="project-status-badge" 
                          style="background: ${statusColors[project.status]}"
                          onclick="openStatusModal(${project.id}, '${project.name}', '${project.status}'); event.stopPropagation();">
                        ${project.status}
                    </span>
                </div>
                <div class="project-card-meta">
                    <span><i class="fas fa-map-marker-alt"></i> ${escapeHtml(project.location || 'Unknown')}</span>
                    <span><i class="fas fa-calendar"></i> ${formatDate(project.created_at)}</span>
                </div>
            </div>
            
            <div class="project-card-body">
                <div class="project-progress">
                    <div class="progress-header">
                        <span class="progress-label">Progress</span>
                        <span class="progress-value">${parseInt(project.progress_percentage || 0)}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${project.progress_percentage || 0}%"></div>
                    </div>
                </div>
                
                <div class="project-info-grid">
                    <div class="info-item">
                        <span class="info-label">Area</span>
                        <span class="info-value">${parseFloat(project.area_hectares || 0).toFixed(1)} ha</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">NDVI</span>
                        <span class="info-value">${project.vegetation_index ? parseFloat(project.vegetation_index).toFixed(2) : 'N/A'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Climate</span>
                        <span class="info-value">${project.climate_zone || 'N/A'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Soil pH</span>
                        <span class="info-value">${project.soil_ph ? parseFloat(project.soil_ph).toFixed(1) : 'N/A'}</span>
                    </div>
                </div>
            </div>
            
            <div class="project-card-footer">
                <button class="btn-card" onclick="viewProjectDetails(${project.id}); event.stopPropagation();">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn-card" onclick="editProject(${project.id}); event.stopPropagation();">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn-card" onclick="deleteProject(${project.id}); event.stopPropagation();">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
}

// ========================
// MAP FUNCTIONS
// ========================

window.toggleMap = function() {
    const mapSection = document.getElementById('mapSection');
    const toggleText = document.getElementById('mapToggleText');
    
    mapSection.classList.toggle('collapsed');
    
    if (mapSection.classList.contains('collapsed')) {
        toggleText.textContent = 'Show Project Map';
    } else {
        toggleText.textContent = 'Hide Project Map';
        
        // Initialize map if not already done
        if (!state.maps.main) {
            setTimeout(() => {
                initializeMainMap();
                updateMainMap();
            }, 300);
        }
    }
};

function initializeMainMap() {
    const container = document.getElementById('projectsMap');
    if (!container || typeof L === 'undefined') {
        console.error('Leaflet not loaded or container not found');
        return;
    }
    
    try {
        if (state.maps.main) {
            state.maps.main.remove();
        }
        
        state.maps.main = L.map(container).setView([-1.2921, 36.8219], 7);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(state.maps.main);
        
        console.log('✅ Main map initialized');
    } catch (error) {
        console.error('Map initialization error:', error);
    }
}

function updateMainMap() {
    if (!state.maps.main || !state.projects.length) return;
    
    // Clear existing markers
    state.markers.main.forEach(marker => state.maps.main.removeLayer(marker));
    state.markers.main = [];
    
    const bounds = [];
    
    // Add markers for each project
    state.projects.forEach(project => {
        if (project.latitude && project.longitude) {
            const statusColors = {
                'planning': '#3b82f6',
                'active': '#10b981',
                'completed': '#8b5cf6',
                'paused': '#f59e0b'
            };
            
            const icon = L.divIcon({
                className: 'custom-marker',
                html: `<div style="background: ${statusColors[project.status]}; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"></div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            const marker = L.marker([project.latitude, project.longitude], { icon })
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <strong style="font-size: 1.1em; color: #10b981;">${escapeHtml(project.name)}</strong><br>
                        <span style="color: #6b7280;">📍 ${escapeHtml(project.location || 'Unknown')}</span><br>
                        <span style="color: #6b7280;">📏 ${parseFloat(project.area_hectares || 0).toFixed(1)} hectares</span><br>
                        <span style="color: #6b7280;">📊 ${project.status}</span><br>
                        <button onclick="viewProjectDetails(${project.id})" 
                                style="margin-top: 10px; padding: 6px 12px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer;">
                            View Details
                        </button>
                    </div>
                `)
                .addTo(state.maps.main);
            
            state.markers.main.push(marker);
            bounds.push([project.latitude, project.longitude]);
        }
    });
    
    // Fit map to show all markers
    if (bounds.length > 0) {
        state.maps.main.fitBounds(bounds, { padding: [50, 50] });
    }
}

function initializeModalMap() {
    const container = document.getElementById('modalMap');
    if (!container || typeof L === 'undefined') return;
    
    try {
        if (state.maps.modal) {
            state.maps.modal.remove();
        }
        
        state.maps.modal = L.map(container).setView([-1.2921, 36.8219], 7);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(state.maps.modal);
        
        // Click to set location
        state.maps.modal.on('click', (e) => {
            document.getElementById('latitude').value = e.latlng.lat.toFixed(6);
            document.getElementById('longitude').value = e.latlng.lng.toFixed(6);
            updateModalMarker();
        });
        
        console.log('✅ Modal map initialized');
    } catch (error) {
        console.error('Modal map error:', error);
    }
}

function updateModalMarker() {
    const lat = parseFloat(document.getElementById('latitude')?.value);
    const lng = parseFloat(document.getElementById('longitude')?.value);
    
    if (!isNaN(lat) && !isNaN(lng) && state.maps.modal) {
        if (state.markers.modal) {
            state.maps.modal.removeLayer(state.markers.modal);
        }
        
        state.markers.modal = L.marker([lat, lng]).addTo(state.maps.modal);
        state.maps.modal.setView([lat, lng], 12);
    }
}

// ========================
// PROJECT ACTIONS
// ========================

window.viewProjectDetails = async function(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) {
        showToast('Project not found', 'error');
        return;
    }
    
    const modal = document.getElementById('projectDetailsModal');
    const content = document.getElementById('projectDetailsContent');
    const title = document.getElementById('detailsProjectName');
    
    if (!modal || !content) return;
    
    title.innerHTML = `<i class="fas fa-info-circle"></i> ${escapeHtml(project.name)}`;
    
    content.innerHTML = createProjectDetailsContent(project);
    
    modal.classList.add('show');
};

function createProjectDetailsContent(project) {
    return `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
            <div style="background: var(--gray-50); padding: 1.5rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200);">
                <h4 style="margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-info-circle" style="color: var(--primary);"></i>
                    Basic Information
                </h4>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Type</span>
                        <strong>${project.project_type || 'N/A'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Status</span>
                        <strong>${project.status || 'N/A'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Area</span>
                        <strong>${parseFloat(project.area_hectares || 0).toFixed(1)} ha</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Location</span>
                        <strong>${escapeHtml(project.location || 'Unknown')}</strong>
                    </div>
                </div>
            </div>
            
            <div style="background: var(--gray-50); padding: 1.5rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200);">
                <h4 style="margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-leaf" style="color: var(--primary);"></i>
                    Environmental Data
                </h4>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Climate</span>
                        <strong>${project.climate_zone || 'N/A'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Soil Type</span>
                        <strong>${project.soil_type || 'N/A'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">NDVI</span>
                        <strong>${project.vegetation_index ? parseFloat(project.vegetation_index).toFixed(2) : 'N/A'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: var(--gray-600);">Degradation</span>
                        <strong>${project.land_degradation_level || 'N/A'}</strong>
                    </div>
                </div>
            </div>
        </div>
        
        ${project.description ? `
            <div style="margin-top: 1.5rem; padding: 1.5rem; background: var(--gray-50); border-radius: var(--radius-lg); border: 1px solid var(--gray-200);">
                <h4 style="margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-align-left" style="color: var(--primary);"></i>
                    Description
                </h4>
                <p style="color: var(--gray-700); line-height: 1.6;">${escapeHtml(project.description)}</p>
            </div>
        ` : ''}
        
        <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: flex-end;">
            <button class="btn btn-outline" onclick="closeDetailsModal()">Close</button>
            <button class="btn btn-primary" onclick="editProject(${project.id}); closeDetailsModal();">
                <i class="fas fa-edit"></i> Edit Project
            </button>
        </div>
    `;
}

window.editProject = function(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) {
        showToast('Project not found', 'error');
        return;
    }
    
    state.editMode = true;
    
    document.getElementById('modalTitle').innerHTML = '<i class="fas fa-edit"></i> Edit Project';
    document.getElementById('submitBtnText').textContent = 'Update Project';
    document.getElementById('projectId').value = project.id;
    document.getElementById('projectName').value = project.name || '';
    document.getElementById('projectType').value = project.project_type || '';
    document.getElementById('projectArea').value = project.area_hectares || '';
    document.getElementById('projectDescription').value = project.description || '';
    document.getElementById('latitude').value = project.latitude || '';
    document.getElementById('longitude').value = project.longitude || '';
    
    openProjectModal();
    
    setTimeout(() => {
        initializeModalMap();
        updateModalMarker();
    }, 100);
};

window.deleteProject = async function(projectId) {
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/projects/${projectId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ Project deleted successfully', 'success');
            await loadProjects();
        } else {
            showToast(data.error || 'Failed to delete project', 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showToast('Error deleting project', 'error');
    }
};

// ========================
// STATUS CHANGE
// ========================

window.openStatusModal = function(projectId, projectName, currentStatus) {
    state.statusChangeProject = projectId;
    state.newStatus = null;
    
    document.getElementById('statusProjectName').textContent = projectName;
    
    // Setup status options
    const statusOptions = document.querySelectorAll('.status-option');
    statusOptions.forEach(option => {
        option.classList.remove('selected');
        
        if (option.dataset.status === currentStatus) {
            option.classList.add('selected');
            state.newStatus = currentStatus;
        }
        
        option.onclick = function() {
            statusOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            state.newStatus = this.dataset.status;
        };
    });
    
    document.getElementById('statusChangeModal').classList.add('show');
};

// Enhanced status change with progress slider
window.openStatusModal = function(projectId, projectName, currentStatus) {
    state.statusChangeProject = projectId;
    state.newStatus = currentStatus;
    
    const project = state.projects.find(p => p.id === projectId);
    const currentProgress = project ? parseInt(project.progress_percentage || 0) : 0;
    
    document.getElementById('statusProjectName').textContent = projectName;
    
    // Setup status options
    const statusOptions = document.querySelectorAll('.status-option');
    const flowLine = document.querySelector('.status-flow-line');
    const progressAdjustment = document.getElementById('progressAdjustment');
    const progressSlider = document.getElementById('progressSlider');
    const progressValue = document.getElementById('progressValue');
    const progressPreviewFill = document.getElementById('progressPreviewFill');
    
    statusOptions.forEach(option => {
        option.classList.remove('selected');
        
        if (option.dataset.status === currentStatus) {
            option.classList.add('selected');
            updateFlowLine(currentStatus, flowLine);
        }
        
        option.onclick = function() {
            statusOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            state.newStatus = this.dataset.status;
            
            // Update flow line animation
            updateFlowLine(state.newStatus, flowLine);
            
            // Show/hide progress slider for 'active' status
            if (state.newStatus === 'active') {
                progressAdjustment.style.display = 'block';
                progressSlider.value = currentProgress > 0 && currentProgress < 100 ? currentProgress : 50;
                updateProgressDisplay(progressSlider.value);
            } else {
                progressAdjustment.style.display = 'none';
            }
        };
    });
    
    // Progress slider events
    if (progressSlider) {
        progressSlider.value = currentProgress > 0 && currentProgress < 100 ? currentProgress : 50;
        updateProgressDisplay(progressSlider.value);
        
        progressSlider.oninput = function() {
            updateProgressDisplay(this.value);
        };
    }
    
    function updateProgressDisplay(value) {
        if (progressValue) progressValue.textContent = value;
        if (progressPreviewFill) progressPreviewFill.style.width = value + '%';
    }
    
    function updateFlowLine(status, line) {
        if (!line) return;
        line.className = 'status-flow-line active-' + status;
    }
    
    // Show progress adjustment if current status is active
    if (currentStatus === 'active') {
        progressAdjustment.style.display = 'block';
    } else {
        progressAdjustment.style.display = 'none';
    }
    
    document.getElementById('statusChangeModal').classList.add('show');
};

// Update confirmStatusChange to include progress
window.confirmStatusChange = async function() {
    if (!state.statusChangeProject || !state.newStatus) {
        showToast('Please select a status', 'warning');
        return;
    }
    
    const requestData = { status: state.newStatus };
    
    // Include progress if status is 'active'
    if (state.newStatus === 'active') {
        const progressSlider = document.getElementById('progressSlider');
        if (progressSlider) {
            requestData.progress_percentage = parseInt(progressSlider.value);
        }
    } else if (state.newStatus === 'planning') {
        requestData.progress_percentage = 0;
    } else if (state.newStatus === 'completed') {
        requestData.progress_percentage = 100;
    }
    // For 'paused', don't change progress - backend will keep existing value
    
    console.log('📤 Sending status update:', requestData);
    
    // Add visual feedback
    const confirmBtn = event.target;
    const originalHTML = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    
    try {
        const response = await fetch(`/projects/${state.statusChangeProject}/update-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ Status update successful:', data);
            
            // IMPORTANT: Update the project in state with actual saved data
            const projectIndex = state.projects.findIndex(p => p.id === state.statusChangeProject);
            if (projectIndex !== -1 && data.project) {
                state.projects[projectIndex].status = data.project.status;
                state.projects[projectIndex].progress_percentage = data.project.progress_percentage;
                console.log(`✅ Updated local state - Progress: ${data.project.progress_percentage}%`);
            }
            
            // Show success toast
            showToast('✅ Status and progress updated!', 'success');
            
            // Animate the progress bar update using actual saved value
            if (data.project && data.project.progress_percentage !== undefined) {
                await animateProgressUpdate(state.statusChangeProject, data.project.progress_percentage);
            }
            
            // Close modal
            closeStatusModal();
            
            // Reload projects to ensure everything is in sync
            await loadProjects();
            
        } else {
            console.error('❌ Update failed:', data.error);
            showToast(data.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('❌ Status update error:', error);
        showToast('Error updating status', 'error');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalHTML;
    }
};


async function animateProgressUpdate(projectId, newProgress) {
    return new Promise((resolve) => {
        const projectCards = document.querySelectorAll(`[data-project-id="${projectId}"]`);
        
        if (projectCards.length === 0) {
            console.log('⚠️ No cards found for project:', projectId);
            resolve();
            return;
        }
        
        console.log(`🎬 Animating ${projectCards.length} card(s) to ${newProgress}%`);
        
        projectCards.forEach(card => {
            const progressFill = card.querySelector('.progress-fill');
            const progressValue = card.querySelector('.progress-value');
            
            if (progressFill && progressValue) {
                const currentWidth = progressFill.style.width || '0%';
                const currentProgress = parseInt(currentWidth) || 0;
                const targetProgress = parseInt(newProgress) || 0;
                
                console.log(`📊 Animating from ${currentProgress}% to ${targetProgress}%`);
                
                // Add updating class for pulse animation
                progressValue.classList.add('updating');
                
                // Animate the progress change
                animateValue(currentProgress, targetProgress, 1000, (value) => {
                    progressFill.style.width = value + '%';
                    progressValue.textContent = Math.round(value) + '%';
                });
                
                // IMPORTANT: Set final value explicitly after animation
                setTimeout(() => {
                    progressFill.style.width = targetProgress + '%';
                    progressValue.textContent = targetProgress + '%';
                    progressValue.classList.remove('updating');
                    console.log(`✅ Animation complete - Final: ${targetProgress}%`);
                    
                    // Celebrate if reaching 100%
                    if (targetProgress === 100 && currentProgress < 100) {
                        celebrateCompletion(projectId);
                    }
                }, 1050);
            }
        });
        
        // Resolve after animation completes
        setTimeout(resolve, 1200);
    });
}

window.closeStatusModal = function() {
    document.getElementById('statusChangeModal').classList.remove('show');
    state.statusChangeProject = null;
    state.newStatus = null;
};

window.confirmStatusChange = async function() {
    if (!state.statusChangeProject || !state.newStatus) {
        showToast('Please select a status', 'warning');
        return;
    }
    
    const requestData = { status: state.newStatus };
    
    // Include progress if status is 'active'
    if (state.newStatus === 'active') {
        const progressSlider = document.getElementById('progressSlider');
        if (progressSlider) {
            requestData.progress_percentage = parseInt(progressSlider.value);
        }
    } else if (state.newStatus === 'planning') {
        requestData.progress_percentage = 0;
    } else if (state.newStatus === 'completed') {
        requestData.progress_percentage = 100;
    }
    
    // Add visual feedback
    const confirmBtn = event.target;
    const originalHTML = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    
    try {
        const response = await fetch(`/projects/${state.statusChangeProject}/update-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success toast
            showToast('✅ Status updated successfully!', 'success');
            
            // Animate the progress bar update before closing modal
            await animateProgressUpdate(state.statusChangeProject, requestData.progress_percentage);
            
            // Close modal and reload
            closeStatusModal();
            await loadProjects();
        } else {
            showToast(data.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('Status update error:', error);
        showToast('Error updating status', 'error');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalHTML;
    }
};

// Add this new function to animate progress updates
// Enhanced function to animate progress updates everywhere
async function animateProgressUpdate(projectId, newProgress) {
    return new Promise((resolve) => {
        // Find all project cards with this ID (both in recent and all projects panel)
        const projectCards = document.querySelectorAll(`[data-project-id="${projectId}"]`);
        
        if (projectCards.length === 0) {
            console.log('No cards found for project:', projectId);
            resolve();
            return;
        }
        
        projectCards.forEach(card => {
            const progressFill = card.querySelector('.progress-fill');
            const progressValue = card.querySelector('.progress-value');
            
            if (progressFill && progressValue) {
                // Get current progress from the element
                const currentWidth = progressFill.style.width || '0%';
                const currentProgress = parseInt(currentWidth) || 0;
                const targetProgress = newProgress || 0;
                
                console.log(`Animating progress from ${currentProgress}% to ${targetProgress}%`);
                
                // Add updating class for pulse animation
                progressValue.classList.add('updating');
                
                // Animate the progress change
                animateValue(currentProgress, targetProgress, 1000, (value) => {
                    progressFill.style.width = value + '%';
                    progressValue.textContent = Math.round(value) + '%';
                });
                
                // Remove updating class after animation
                setTimeout(() => {
                    progressValue.classList.remove('updating');
                }, 1000);
                
                // Celebrate if reaching 100%
                if (targetProgress === 100 && currentProgress < 100) {
                    setTimeout(() => {
                        celebrateCompletion(projectId);
                    }, 1000);
                }
            } else {
                console.warn('Progress elements not found in card:', card);
            }
        });
        
        // Resolve after animation completes
        setTimeout(resolve, 1200);
    });
}

// Add this helper function for smooth number animation
function animateValue(start, end, duration, callback) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function for smooth animation
        const easeOutCubic = 1 - Math.pow(1 - progress, 3);
        const currentValue = start + (end - start) * easeOutCubic;
        
        callback(currentValue);
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ========================
// MODAL FUNCTIONS
// ========================

function openProjectModal() {
    if (!state.editMode) {
        document.getElementById('projectForm')?.reset();
        document.getElementById('modalTitle').innerHTML = '<i class="fas fa-plus"></i> Create New Project';
        document.getElementById('submitBtnText').textContent = 'Create Project';
        document.getElementById('projectId').value = '';
    }
    
    document.getElementById('projectModal')?.classList.add('show');
    
    setTimeout(() => {
        initializeModalMap();
    }, 100);
}

window.closeProjectModal = function() {
    document.getElementById('projectModal')?.classList.remove('show');
    state.editMode = false;
};

window.closeDetailsModal = function() {
    document.getElementById('projectDetailsModal')?.classList.remove('show');
};

// ========================
// FORM HANDLING
// ========================

async function handleQuickCreate() {
    const btn = event.target.closest('button');
    if (!btn) return;
    
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    
    showToast('🎯 Getting your location...', 'info');
    
    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            });
        });
        
        const projectData = {
            name: `Quick Project - ${new Date().toLocaleString()}`,
            description: 'Quick-created project using GPS location',
            project_type: 'reforestation',
            area_hectares: 10,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
        };
        
        const response = await fetch('/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('🎉 Project created successfully!', 'success');
            await loadProjects();
        } else {
            showToast(data.error || 'Failed to create project', 'error');
        }
    } catch (error) {
        console.error('Quick create error:', error);
        if (error.code === 1) {
            showToast('Please enable location access to use Quick Create', 'warning');
        } else {
            showToast('Failed to create project. Please try manual creation.', 'error');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

window.handleQuickCreate = handleQuickCreate;

async function handleProjectSubmit(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('projectId')?.value;
    const formData = {
        name: document.getElementById('projectName')?.value,
        description: document.getElementById('projectDescription')?.value || '',
        project_type: document.getElementById('projectType')?.value,
        area_hectares: parseFloat(document.getElementById('projectArea')?.value),
        latitude: parseFloat(document.getElementById('latitude')?.value),
        longitude: parseFloat(document.getElementById('longitude')?.value)
    };
    
    if (!formData.name || !formData.project_type || !formData.area_hectares || 
        !formData.latitude || !formData.longitude) {
        showToast('Please fill all required fields', 'warning');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }
    
    try {
        const url = projectId ? `/projects/${projectId}/update` : '/projects/create';
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(projectId ? '✅ Project updated!' : '🎉 Project created!', 'success');
            closeProjectModal();
            await loadProjects();
        } else {
            showToast(data.error || 'Failed to save project', 'error');
        }
    } catch (error) {
        console.error('Form submit error:', error);
        showToast('Error saving project', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fas fa-check"></i> <span id="submitBtnText">${projectId ? 'Update' : 'Create'} Project</span>`;
        }
    }
}

// ========================
// STATISTICS
// ========================

function updateStatistics() {
    const total = state.projects.length;
    const active = state.projects.filter(p => p.status === 'active').length;
    const totalArea = state.projects.reduce((sum, p) => sum + parseFloat(p.area_hectares || 0), 0);
    
    // Animate numbers
    animateNumber('totalProjects', total);
    animateNumber('totalArea', totalArea.toFixed(1));
    animateNumber('activeProjects', active);
}

function animateNumber(elementId, targetValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = parseFloat(element.textContent) || 0;
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function
        const easeOutQuad = 1 - Math.pow(1 - progress, 3);
        const currentValue = startValue + (targetValue - startValue) * easeOutQuad;
        
        element.textContent = typeof targetValue === 'string' && targetValue.includes('.') 
            ? currentValue.toFixed(1)
            : Math.round(currentValue);
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ========================
// UTILITY FUNCTIONS
// ========================

window.scrollToAllProjects = function() {
    // This function is no longer needed - replaced with floating panel
    openAllProjectsPanel();
};

window.openAllProjectsPanel = function() {
    const panel = document.getElementById('allProjectsPanel');
    if (!panel) return;
    
    panel.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    // Render all projects in the panel
    renderAllProjects();
};

window.closeAllProjectsPanel = function() {
    const panel = document.getElementById('allProjectsPanel');
    if (!panel) return;
    
    // Add closing animation
    panel.classList.add('closing');
    
    setTimeout(() => {
        panel.classList.remove('show', 'closing');
        document.body.style.overflow = '';
    }, 300);
};

function renderAllProjects() {
    const container = document.querySelector('#allProjectsPanel .projects-grid');
    if (!container) return;
    
    if (state.filteredProjects.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <h3>No Projects Found</h3>
                <p>${state.searchTerm ? 'Try adjusting your search' : 'Create your first project to get started'}</p>
                ${!state.searchTerm ? '<button class="btn btn-primary" onclick="closeAllProjectsPanel(); openProjectModal()"><i class="fas fa-plus"></i> Create Project</button>' : ''}
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.filteredProjects.map(project => createProjectCard(project)).join('');
}

function showEmptyState() {
    const container = document.getElementById('projectsGrid');
    if (!container) return;
    
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-seedling"></i>
            <h3>No Projects Yet</h3>
            <p>Start your first land restoration project</p>
            <button class="btn btn-primary" onclick="openProjectModal()">
                <i class="fas fa-plus"></i> Create Project
            </button>
        </div>
    `;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function formatTimeAgo(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    
    return formatDate(dateString);
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function showToast(message, type = 'info') {
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
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


// Add this function after the createProjectCard function
function updateProjectProgress(projectId, newProgress, animated = true) {
    const projectCards = document.querySelectorAll(`[data-project-id="${projectId}"]`);
    
    projectCards.forEach(card => {
        const progressFill = card.querySelector('.progress-fill');
        const progressValue = card.querySelector('.progress-value');
        
        if (!progressFill || !progressValue) return;
        
        if (animated) {
            // Add updating class for animation
            progressValue.classList.add('updating');
            
            // Get current progress
            const currentWidth = progressFill.style.width || '0%';
            const currentProgress = parseInt(currentWidth);
            
            // Animate to new progress
            animateValue(currentProgress, newProgress, 800, (value) => {
                progressFill.style.width = value + '%';
                progressValue.textContent = Math.round(value) + '%';
            });
            
            // Remove updating class after animation
            setTimeout(() => {
                progressValue.classList.remove('updating');
            }, 800);
        } else {
            // Instant update
            progressFill.style.width = newProgress + '%';
            progressValue.textContent = newProgress + '%';
        }
    });
}

// Export for use in other functions
window.updateProjectProgress = updateProjectProgress;

function celebrateCompletion(projectId) {
    const projectCards = document.querySelectorAll(`[data-project-id="${projectId}"]`);
    
    projectCards.forEach(card => {
        // Add completion effect
        card.style.animation = 'none';
        setTimeout(() => {
            card.style.animation = 'completionPulse 0.6s ease';
        }, 10);
        
        // Create confetti effect (optional)
        createConfetti(card);
    });
}

// Add this CSS for the completion animation
const completionStyles = document.createElement('style');
completionStyles.textContent = `
    @keyframes completionPulse {
        0%, 100% {
            transform: scale(1);
        }
        25% {
            transform: scale(1.02);
        }
        75% {
            transform: scale(0.98);
        }
    }
`;
document.head.appendChild(completionStyles);

// Optional: Simple confetti effect
function createConfetti(element) {
    const colors = ['#10b981', '#8b5cf6', '#f59e0b', '#3b82f6'];
    const rect = element.getBoundingClientRect();
    
    for (let i = 0; i < 20; i++) {
        const confetti = document.createElement('div');
        confetti.style.cssText = `
            position: fixed;
            width: 8px;
            height: 8px;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            left: ${rect.left + rect.width / 2}px;
            top: ${rect.top + rect.height / 2}px;
            border-radius: 50%;
            pointer-events: none;
            z-index: 10000;
        `;
        document.body.appendChild(confetti);
        
        // Animate confetti
        const angle = (Math.random() * 360) * (Math.PI / 180);
        const velocity = 100 + Math.random() * 100;
        const tx = Math.cos(angle) * velocity;
        const ty = Math.sin(angle) * velocity;
        
        confetti.animate([
            { transform: 'translate(0, 0) scale(1)', opacity: 1 },
            { transform: `translate(${tx}px, ${ty}px) scale(0)`, opacity: 0 }
        ], {
            duration: 1000,
            easing: 'cubic-bezier(0, 0.5, 0.5, 1)'
        }).onfinish = () => confetti.remove();
    }
}


// ========================
// ADDITIONAL CSS STYLES
// ========================

// Add notification item styles
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification-item {
        padding: 1rem;
        border-bottom: 1px solid var(--gray-200);
        cursor: pointer;
        transition: var(--transition);
        background: var(--white);
    }
    
    .notification-item:hover {
        background: var(--gray-50);
    }
    
    .notification-item.unread {
        background: linear-gradient(90deg, #eff6ff, var(--white));
        border-left: 3px solid var(--primary);
    }
    
    .notification-item-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.5rem;
    }
    
    .notification-item-title {
        font-weight: 600;
        color: var(--gray-900);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1;
    }
    
    .notification-item-title i {
        color: var(--primary);
    }
    
    .notification-item-time {
        font-size: 0.75rem;
        color: var(--gray-500);
        white-space: nowrap;
    }
    
    .notification-item-message {
        font-size: 0.875rem;
        color: var(--gray-600);
        line-height: 1.5;
    }
    
    .project-details-tabs {
        display: flex;
        gap: 0.5rem;
        border-bottom: 2px solid var(--gray-200);
        margin-bottom: 2rem;
    }
    
    .tab-btn {
        padding: 1rem 1.5rem;
        background: transparent;
        border: none;
        border-bottom: 3px solid transparent;
        cursor: pointer;
        font-weight: 600;
        color: var(--gray-600);
        transition: var(--transition);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .tab-btn:hover {
        color: var(--primary);
    }
    
    .tab-btn.active {
        color: var(--primary);
        border-bottom-color: var(--primary);
    }
    
    .tab-content {
        display: none;
    }
    
    .tab-content.active {
        display: block;
        animation: fadeInUp 0.3s ease;
    }
    
    /* Custom Leaflet marker styles */
    .custom-marker {
        background: transparent;
        border: none;
    }
    
    /* Smooth scroll */
    html {
        scroll-behavior: smooth;
    }
    
    /* Progress bar animation */
    .progress-fill {
        animation: progressGrow 1.5s ease-in-out;
    }
    
    @keyframes progressGrow {
        from {
            width: 0 !important;
        }
    }
    
    /* Card hover effects */
    .project-card {
        position: relative;
        overflow: hidden;
    }
    
    .project-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary), var(--primary-light));
        transform: translateX(-100%);
        transition: transform 0.3s ease;
    }
    
    .project-card:hover::before {
        transform: translateX(0);
    }
    
    /* Status badge pulse animation for active projects */
    .project-status-badge[style*="background: #10b981"] {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        50% {
            box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
        }
    }
    
    /* Enhanced card animations */
    .project-card:nth-child(1) { animation-delay: 0.05s; }
    .project-card:nth-child(2) { animation-delay: 0.1s; }
    .project-card:nth-child(3) { animation-delay: 0.15s; }
    .project-card:nth-child(4) { animation-delay: 0.2s; }
    .project-card:nth-child(5) { animation-delay: 0.25s; }
    .project-card:nth-child(6) { animation-delay: 0.3s; }
    
    /* Button ripple effect */
    .btn, .btn-card, .filter-btn {
        position: relative;
        overflow: hidden;
    }
    
    .btn::after, .btn-card::after, .filter-btn::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.5);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .btn:active::after, .btn-card:active::after, .filter-btn:active::after {
        width: 300px;
        height: 300px;
    }
    
    /* Skeleton loading for cards */
    @keyframes shimmer {
        0% {
            background-position: -1000px 0;
        }
        100% {
            background-position: 1000px 0;
        }
    }
    
    .skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 1000px 100%;
        animation: shimmer 2s infinite;
    }
    
    /* Focus visible for accessibility */
    *:focus-visible {
        outline: 2px solid var(--primary);
        outline-offset: 2px;
    }
    
    /* Smooth transitions for all interactive elements */
    button, a, input, select, textarea {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
`;
document.head.appendChild(notificationStyles);

console.log('✅ RegenArdhi Projects loaded!');

// ========================
// EXPORT FOR TESTING
// ========================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        state,
        loadProjects,
        filterAndRenderProjects,
        updateStatistics,
        showToast
    };
}