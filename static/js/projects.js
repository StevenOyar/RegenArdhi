// ========================================
// REGENARDHI - MAP-CENTRIC REDESIGN JS
// Clean, organized, and efficient
// ========================================

// Global State
const state = {
    projects: [],
    filteredProjects: [],
    selectedProject: null,
    maps: {
        main: null,
        modal: null
    },
    markers: {
        main: [],
        modal: null
    },
    editMode: false
};

// ========================
// INITIALIZATION
// ========================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 RegenArdhi Projects - Initializing...');
    
    initializeNavigation();
    initializeEventListeners();
    initializeMainMap();
    loadProjects();
    checkGPSAvailability();
});

// ========================
// NAVIGATION
// ========================

function initializeNavigation() {
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');
    
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
}

// ========================
// EVENT LISTENERS
// ========================

function initializeEventListeners() {
    // Modal controls
    document.getElementById('viewAllBtn')?.addEventListener('click', openAllProjectsModal);
    document.getElementById('closeAllProjectsBtn')?.addEventListener('click', closeAllProjectsModal);
    document.getElementById('newProjectBtn')?.addEventListener('click', openProjectModal);
    document.getElementById('closeProjectModalBtn')?.addEventListener('click', closeProjectModal);
    document.getElementById('closeDetailsModalBtn')?.addEventListener('click', closeDetailsModal);
    document.getElementById('quickCreateBtn')?.addEventListener('click', handleQuickCreate);
    
    // Form
    document.getElementById('projectForm')?.addEventListener('submit', handleProjectSubmit);
    document.getElementById('latitude')?.addEventListener('change', updateModalMarker);
    document.getElementById('longitude')?.addEventListener('change', updateModalMarker);
    
    // Filters
    document.getElementById('searchProjects')?.addEventListener('input', filterProjects);
    document.getElementById('filterStatus')?.addEventListener('change', filterProjects);
    document.getElementById('filterType')?.addEventListener('change', filterProjects);
    
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
    showNotification('📍 Getting your location...', 'info');
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude.toFixed(6);
            const lng = position.coords.longitude.toFixed(6);
            
            document.getElementById('latitude').value = lat;
            document.getElementById('longitude').value = lng;
            
            updateModalMarker();
            showNotification('✓ Location detected successfully!', 'success');
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
            showNotification(message, 'error');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
};

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
            state.filteredProjects = [...state.projects];
            
            renderLatestProjects();
            updateStatistics();
            updateMainMap();
            
            console.log(`✓ Loaded ${state.projects.length} projects`);
        } else {
            showNotification(data.error || 'Failed to load projects', 'error');
            showEmptyState('latestProjects');
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        showNotification('Error connecting to server', 'error');
        showEmptyState('latestProjects');
    }
}

// ========================
// RENDER FUNCTIONS
// ========================

function renderLatestProjects() {
    const container = document.getElementById('latestProjects');
    if (!container) return;
    
    const latestProjects = state.projects.slice(0, 4);
    
    if (latestProjects.length === 0) {
        showEmptyState('latestProjects');
        return;
    }
    
    container.innerHTML = latestProjects.map(project => createMiniCard(project)).join('');
    
    // Attach click listeners
    container.querySelectorAll('.project-card-mini').forEach(card => {
        const projectId = parseInt(card.dataset.projectId);
        card.addEventListener('click', () => selectProject(projectId));
    });
}

function createMiniCard(project) {
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
        <div class="project-card-mini ${state.selectedProject?.id === project.id ? 'selected' : ''}" 
             data-project-id="${project.id}">
            <div class="project-card-header-mini">
                <div>
                    <h4>${escapeHtml(project.name)}</h4>
                    <span class="project-status-mini" style="background: ${statusColors[project.status]}">
                        ${project.status}
                    </span>
                </div>
                <div class="project-type-badge">
                    ${typeIcons[project.project_type] || '🌿'}
                </div>
            </div>
            <div class="project-meta-mini">
                <span><i class="fas fa-map-marker-alt"></i> ${escapeHtml(project.location || 'Unknown')}</span>
                <span><i class="fas fa-ruler-combined"></i> ${parseFloat(project.area_hectares || 0).toFixed(1)} ha</span>
                <span><i class="fas fa-calendar"></i> ${formatDate(project.created_at)}</span>
            </div>
            <div class="project-actions-mini">
                <button class="btn-mini" onclick="viewProjectDetails(${project.id}); event.stopPropagation();">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn-mini" onclick="editProject(${project.id}); event.stopPropagation();">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn-mini" onclick="deleteProject(${project.id}); event.stopPropagation();">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
}

function renderAllProjects() {
    const container = document.getElementById('allProjectsGrid');
    if (!container) return;
    
    if (state.filteredProjects.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <i class="fas fa-search"></i>
                <h3>No Projects Found</h3>
                <p>Try adjusting your filters</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.filteredProjects.map(project => createFullCard(project)).join('');
}

function createFullCard(project) {
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
        <div class="project-card-full">
            <div class="project-card-full-header">
                <h3>
                    <span class="project-type-icon">${typeIcons[project.project_type] || '🌿'}</span>
                    ${escapeHtml(project.name)}
                </h3>
                <span class="project-status-badge" style="background: ${statusColors[project.status]}">
                    ${project.status}
                </span>
            </div>
            <div class="project-card-full-body">
                <div class="project-info-row">
                    <span><i class="fas fa-map-marker-alt"></i> Location</span>
                    <strong>${escapeHtml(project.location || 'Unknown')}</strong>
                </div>
                <div class="project-info-row">
                    <span><i class="fas fa-ruler-combined"></i> Area</span>
                    <strong>${parseFloat(project.area_hectares || 0).toFixed(1)} hectares</strong>
                </div>
                <div class="project-info-row">
                    <span><i class="fas fa-chart-line"></i> Progress</span>
                    <strong>${parseInt(project.progress_percentage || 0)}%</strong>
                </div>
                <div class="project-info-row">
                    <span><i class="fas fa-leaf"></i> NDVI</span>
                    <strong>${project.vegetation_index ? parseFloat(project.vegetation_index).toFixed(2) : 'N/A'}</strong>
                </div>
                <div class="project-info-row">
                    <span><i class="fas fa-calendar"></i> Created</span>
                    <strong>${formatDate(project.created_at)}</strong>
                </div>
            </div>
            <div class="project-card-full-footer">
                <button class="btn-mini" onclick="viewProjectDetails(${project.id})">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn-mini" onclick="editProject(${project.id})">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn-mini" onclick="deleteProject(${project.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
}

// ========================
// MAP FUNCTIONS
// ========================

function initializeMainMap() {
    const container = document.getElementById('projectsMap');
    if (!container || typeof L === 'undefined') {
        console.error('Leaflet not loaded or container not found');
        return;
    }
    
    try {
        state.maps.main = L.map(container).setView([-1.2921, 36.8219], 7);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(state.maps.main);
        
        console.log('✓ Main map initialized');
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
                        <strong style="font-size: 1.1em; color: #10b981;">${project.name}</strong><br>
                        <span style="color: #6b7280;">📍 ${project.location || 'Unknown'}</span><br>
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
        
        console.log('✓ Modal map initialized');
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

window.centerMap = function() {
    if (state.maps.main && state.projects.length > 0) {
        const bounds = state.projects
            .filter(p => p.latitude && p.longitude)
            .map(p => [p.latitude, p.longitude]);
        
        if (bounds.length > 0) {
            state.maps.main.fitBounds(bounds, { padding: [50, 50] });
        }
    }
};

window.toggleFullscreen = function() {
    const container = document.querySelector('.map-container');
    if (!document.fullscreenElement) {
        container.requestFullscreen?.();
    } else {
        document.exitFullscreen?.();
    }
};

// ========================
// PROJECT ACTIONS
// ========================

function selectProject(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (project) {
        state.selectedProject = project;
        renderLatestProjects();
        
        // Center map on selected project
        if (state.maps.main && project.latitude && project.longitude) {
            state.maps.main.setView([project.latitude, project.longitude], 12);
            
            // Open popup for this project
            state.markers.main.forEach(marker => {
                const latlng = marker.getLatLng();
                if (latlng.lat === project.latitude && latlng.lng === project.longitude) {
                    marker.openPopup();
                }
            });
        }
    }
}

window.viewProjectDetails = async function(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) {
        showNotification('Project not found', 'error');
        return;
    }
    
    const modal = document.getElementById('projectDetailsModal');
    const content = document.getElementById('projectDetailsContent');
    const title = document.getElementById('detailsProjectName');
    
    if (!modal || !content) return;
    
    title.innerHTML = `<i class="fas fa-info-circle"></i> ${escapeHtml(project.name)}`;
    
    content.innerHTML = `
        <div class="project-details-tabs">
            <button class="tab-btn active" data-tab="overview">
                <i class="fas fa-info-circle"></i> Overview
            </button>
            <button class="tab-btn" data-tab="monitoring">
                <i class="fas fa-satellite-dish"></i> Monitoring
            </button>
            <button class="tab-btn" data-tab="insights">
                <i class="fas fa-brain"></i> AI Insights
            </button>
        </div>
        
        <div class="tab-content active" data-tab="overview">
            ${createOverviewTab(project)}
        </div>
        <div class="tab-content" data-tab="monitoring">
            ${createMonitoringTab(project)}
        </div>
        <div class="tab-content" data-tab="insights">
            ${createInsightsTab(project)}
        </div>
    `;
    
    // Setup tab switching
    content.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            content.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            content.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            content.querySelector(`.tab-content[data-tab="${tab}"]`)?.classList.add('active');
        });
    });
    
    modal.classList.add('show');
};

function createOverviewTab(project) {
    return `
        <div class="details-grid">
            <div class="details-card">
                <h4><i class="fas fa-info-circle"></i> Basic Information</h4>
                <div class="project-info-row">
                    <span>Type</span>
                    <strong>${project.project_type || 'N/A'}</strong>
                </div>
                <div class="project-info-row">
                    <span>Status</span>
                    <strong>${project.status || 'N/A'}</strong>
                </div>
                <div class="project-info-row">
                    <span>Area</span>
                    <strong>${parseFloat(project.area_hectares || 0).toFixed(1)} hectares</strong>
                </div>
                <div class="project-info-row">
                    <span>Location</span>
                    <strong>${escapeHtml(project.location || 'Unknown')}</strong>
                </div>
                <div class="project-info-row">
                    <span>Created</span>
                    <strong>${formatDate(project.created_at)}</strong>
                </div>
            </div>
            
            <div class="details-card">
                <h4><i class="fas fa-globe-africa"></i> Environmental Data</h4>
                <div class="project-info-row">
                    <span>Climate Zone</span>
                    <strong>${project.climate_zone || 'N/A'}</strong>
                </div>
                <div class="project-info-row">
                    <span>Soil Type</span>
                    <strong>${project.soil_type || 'N/A'}</strong>
                </div>
                <div class="project-info-row">
                    <span>Temperature</span>
                    <strong>${project.temperature || 'N/A'}°C</strong>
                </div>
                <div class="project-info-row">
                    <span>Degradation Level</span>
                    <strong>${project.land_degradation_level || 'N/A'}</strong>
                </div>
            </div>
            
            <div class="details-card" style="grid-column: 1 / -1;">
                <h4><i class="fas fa-align-left"></i> Description</h4>
                <p>${escapeHtml(project.description || 'No description provided')}</p>
            </div>
            
            ${project.recommended_crops && project.recommended_crops.length > 0 ? `
                <div class="details-card">
                    <h4><i class="fas fa-seedling"></i> Recommended Crops</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                        ${project.recommended_crops.slice(0, 6).map(crop => 
                            `<span style="padding: 0.5rem 1rem; background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white; border-radius: 20px; font-size: 0.875rem;">${crop}</span>`
                        ).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${project.recommended_trees && project.recommended_trees.length > 0 ? `
                <div class="details-card">
                    <h4><i class="fas fa-tree"></i> Recommended Trees</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                        ${project.recommended_trees.slice(0, 6).map(tree => 
                            `<span style="padding: 0.5rem 1rem; background: linear-gradient(135deg, #10b981, #059669); color: white; border-radius: 20px; font-size: 0.875rem;">${tree}</span>`
                        ).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function createMonitoringTab(project) {
    return `
        <div class="details-grid">
            <div class="details-card">
                <h4><i class="fas fa-leaf"></i> Vegetation Health</h4>
                <div class="project-info-row">
                    <span>NDVI Index</span>
                    <strong>${project.vegetation_index ? parseFloat(project.vegetation_index).toFixed(2) : 'N/A'}</strong>
                </div>
                <div class="project-info-row">
                    <span>Health Status</span>
                    <strong>${getHealthStatus(project.vegetation_index)}</strong>
                </div>
            </div>
            
            <div class="details-card">
                <h4><i class="fas fa-chart-line"></i> Progress</h4>
                <div class="project-info-row">
                    <span>Completion</span>
                    <strong>${parseInt(project.progress_percentage || 0)}%</strong>
                </div>
                <div style="width: 100%; height: 8px; background: #e5e7eb; border-radius: 999px; overflow: hidden; margin-top: 1rem;">
                    <div style="height: 100%; background: linear-gradient(90deg, #10b981, #059669); width: ${project.progress_percentage || 0}%; transition: width 0.5s;"></div>
                </div>
            </div>
            
            <div class="details-card" style="grid-column: 1 / -1;">
                <h4><i class="fas fa-satellite"></i> Monitoring Data</h4>
                <p style="color: #6b7280; margin-bottom: 1rem;">Real-time satellite monitoring and AI analysis</p>
                <button class="btn btn-primary" onclick="updateMonitoring(${project.id})">
                    <i class="fas fa-sync"></i> Update Monitoring Data
                </button>
            </div>
        </div>
    `;
}

function createInsightsTab(project) {
    const techniques = Array.isArray(project.restoration_techniques) ? project.restoration_techniques : [];
    
    return `
        <div class="details-grid">
            <div class="details-card" style="grid-column: 1 / -1;">
                <h4><i class="fas fa-brain"></i> AI Recommendations</h4>
                <p style="color: #6b7280; margin-bottom: 1rem;">Personalized restoration strategies based on AI analysis</p>
                ${techniques.length > 0 ? `
                    <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.75rem;">
                        ${techniques.slice(0, 5).map(tech => `
                            <li style="padding: 0.75rem 1rem; background: #f9fafb; border-left: 3px solid #10b981; border-radius: 8px;">
                                <i class="fas fa-check-circle" style="color: #10b981; margin-right: 0.5rem;"></i>
                                ${tech}
                            </li>
                        `).join('')}
                    </ul>
                ` : '<p style="color: #9ca3af;">No AI recommendations available yet</p>'}
            </div>
            
            <div class="details-card" style="grid-column: 1 / -1;">
                <button class="btn btn-success btn-block" onclick="downloadReport(${project.id})">
                    <i class="fas fa-download"></i> Download Full AI Analysis Report
                </button>
            </div>
        </div>
    `;
}

window.editProject = function(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) {
        showNotification('Project not found', 'error');
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
            showNotification('✓ Project deleted successfully', 'success');
            await loadProjects();
        } else {
            showNotification(data.error || 'Failed to delete project', 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showNotification('Error deleting project', 'error');
    }
};

window.updateMonitoring = async function(projectId) {
    showNotification('🔄 Updating monitoring data...', 'info');
    
    try {
        const response = await fetch(`/monitoring/api/project/${projectId}/update`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('✓ Monitoring data updated!', 'success');
            await loadProjects();
            closeDetailsModal();
        } else {
            showNotification(data.error || 'Failed to update', 'error');
        }
    } catch (error) {
        showNotification('Error updating monitoring data', 'error');
    }
};

window.downloadReport = function(projectId) {
    showNotification('Downloading AI analysis report...', 'info');
    window.location.href = `/projects/${projectId}/report`;
};

// ========================
// MODAL FUNCTIONS
// ========================

function openAllProjectsModal() {
    state.filteredProjects = [...state.projects];
    renderAllProjects();
    document.getElementById('allProjectsModal')?.classList.add('show');
}

function closeAllProjectsModal() {
    document.getElementById('allProjectsModal')?.classList.remove('show');
}

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

function closeProjectModal() {
    document.getElementById('projectModal')?.classList.remove('show');
    state.editMode = false;
}

function closeDetailsModal() {
    document.getElementById('projectDetailsModal')?.classList.remove('show');
}

// ========================
// FORM HANDLING
// ========================

async function handleQuickCreate() {
    const btn = document.getElementById('quickCreateBtn');
    if (!btn) return;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    
    showNotification('🎯 Getting your location...', 'info');
    
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
            description: 'Quick-created project using GPS',
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
            showNotification('🎉 Project created successfully!', 'success');
            await loadProjects();
        } else {
            showNotification(data.error || 'Failed to create project', 'error');
        }
    } catch (error) {
        console.error('Quick create error:', error);
        showNotification('Failed to create project. Please enable GPS.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-bolt"></i> Quick Create';
    }
}

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
        showNotification('Please fill all required fields', 'warning');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }
    
    try {
        const url = projectId ? `/projects/${projectId}/update` : '/projects/create';
        const method = 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(projectId ? '✓ Project updated!' : '🎉 Project created!', 'success');
            closeProjectModal();
            await loadProjects();
        } else {
            showNotification(data.error || 'Failed to save project', 'error');
        }
    } catch (error) {
        console.error('Form submit error:', error);
        showNotification('Error saving project', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fas fa-check"></i> <span id="submitBtnText">${projectId ? 'Update' : 'Create'} Project</span>`;
        }
    }
}

// ========================
// FILTER FUNCTIONS
// ========================

function filterProjects() {
    const searchTerm = document.getElementById('searchProjects')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('filterStatus')?.value || '';
    const typeFilter = document.getElementById('filterType')?.value || '';
    
    state.filteredProjects = state.projects.filter(project => {
        const matchesSearch = project.name.toLowerCase().includes(searchTerm) ||
                            (project.location && project.location.toLowerCase().includes(searchTerm));
        const matchesStatus = !statusFilter || project.status === statusFilter;
        const matchesType = !typeFilter || project.project_type === typeFilter;
        
        return matchesSearch && matchesStatus && matchesType;
    });
    
    renderAllProjects();
}

// ========================
// STATISTICS
// ========================

function updateStatistics() {
    const total = state.projects.length;
    const active = state.projects.filter(p => p.status === 'active').length;
    const totalArea = state.projects.reduce((sum, p) => sum + parseFloat(p.area_hectares || 0), 0);
    
    // Count unique locations
    const locations = new Set(state.projects.map(p => p.location).filter(Boolean));
    const totalLocations = locations.size;
    
    document.getElementById('totalProjects').textContent = total;
    document.getElementById('activeProjects').textContent = active;
    document.getElementById('totalArea').textContent = totalArea.toFixed(1);
    document.getElementById('totalLocations').textContent = totalLocations;
}

// ========================
// HELPER FUNCTIONS
// ========================

function showEmptyState(containerId) {
    const container = document.getElementById(containerId);
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

function getHealthStatus(ndvi) {
    if (!ndvi) return 'Unknown';
    if (ndvi >= 0.6) return 'Excellent';
    if (ndvi >= 0.4) return 'Good';
    if (ndvi >= 0.2) return 'Fair';
    return 'Poor';
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

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    notification.innerHTML = `
        <i class="fas fa-${icons[type] || 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    setTimeout(() => notification.classList.add('show'), 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

console.log('✓ RegenArdhi Projects loaded!');