// projects.js - Enhanced with GPS and Real API Integration

// Global variables
let map = null;
let marker = null;
let projectsData = [];
let currentAnalysis = null;
let gpsWatchId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 RegenArdhi Projects - Initializing...');
    initializeNavigation();
    loadProjects();
    setupEventListeners();
    checkGPSAvailability();
});

// ========================
// GPS FUNCTIONALITY
// ========================

function checkGPSAvailability() {
    if ("geolocation" in navigator) {
        console.log('✓ GPS available');
        const gpsBtn = document.getElementById('useGPSBtn');
        if (gpsBtn) {
            gpsBtn.style.display = 'inline-flex';
        }
    } else {
        console.log('✗ GPS not available');
    }
}

function useCurrentLocation() {
    const btn = document.getElementById('useGPSBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting Location...';
    }
    
    showNotification('📍 Getting your location...', 'info');
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude.toFixed(6);
            const lng = position.coords.longitude.toFixed(6);
            
            console.log('GPS Location:', lat, lng);
            
            document.getElementById('latitude').value = lat;
            document.getElementById('longitude').value = lng;
            
            updateMapMarker();
            showNotification('✓ Location detected successfully!', 'success');
            
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-crosshairs"></i> Use My Location';
            }
        },
        (error) => {
            console.error('GPS Error:', error);
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
            
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-crosshairs"></i> Use My Location';
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

// Make function globally accessible
window.useCurrentLocation = useCurrentLocation;

// ========================
// LOCATION CONVERSION
// ========================

async function getLocationName(latitude, longitude) {
    // """Convert coordinates to place name using reverse geocoding"""
    try {
        // Use OpenStreetMap Nominatim (free, no API key needed)
        const url = `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&zoom=10`;
        
        const response = await fetch(url, {
            headers: {
                'User-Agent': 'RegenArdhi/1.0'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            const address = data.address || {};
            
            // Build location string from address components
            const parts = [];
            
            if (address.town || address.city || address.village) {
                parts.push(address.town || address.city || address.village);
            }
            if (address.county || address.state_district) {
                parts.push(address.county || address.state_district);
            }
            if (address.state) {
                parts.push(address.state);
            }
            if (address.country) {
                parts.push(address.country);
            }
            
            if (parts.length > 0) {
                return parts.join(', ');
            }
        }
        
        // Fallback to coordinates
        return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
        
    } catch (error) {
        console.error('Error getting location name:', error);
        return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
    }
}

// Cache for location names to avoid repeated API calls
const locationCache = {};

async function getLocationNameCached(latitude, longitude) {
    // """Get location name with caching"""
    const key = `${latitude.toFixed(4)},${longitude.toFixed(4)}`;
    
    if (locationCache[key]) {
        return locationCache[key];
    }
    
    const locationName = await getLocationName(latitude, longitude);
    locationCache[key] = locationName;
    return locationName;
}

// ========================
// NAVIGATION & UI
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

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Modal controls
    const newProjectBtn = document.getElementById('newProjectBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const projectModal = document.getElementById('projectModal');
    
    if (newProjectBtn) {
        newProjectBtn.addEventListener('click', openProjectModal);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeProjectModal);
    }
    
    if (projectModal) {
        projectModal.addEventListener('click', (e) => {
            if (e.target === projectModal) closeProjectModal();
        });
    }
    
    // Form submission
    const projectForm = document.getElementById('projectForm');
    if (projectForm) {
        projectForm.addEventListener('submit', handleProjectSubmit);
    }
    
    // Quick create button
    const quickCreateBtn = document.getElementById('quickCreateBtn');
    if (quickCreateBtn) {
        quickCreateBtn.addEventListener('click', handleQuickCreate);
    }
    
    // Coordinate inputs
    const latInput = document.getElementById('latitude');
    const lonInput = document.getElementById('longitude');
    
    if (latInput) latInput.addEventListener('change', updateMapMarker);
    if (lonInput) lonInput.addEventListener('change', updateMapMarker);
    
    // Search and filters
    const searchInput = document.getElementById('searchProjects');
    const statusFilter = document.getElementById('filterStatus');
    const typeFilter = document.getElementById('filterType');
    
    if (searchInput) searchInput.addEventListener('input', filterProjects);
    if (statusFilter) statusFilter.addEventListener('change', filterProjects);
    if (typeFilter) typeFilter.addEventListener('change', filterProjects);
}

// ========================
// PROJECT LOADING
// ========================

async function loadProjects() {
    console.log('📊 Loading projects from database...');
    const grid = document.getElementById('projectsGrid');
    
    grid.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Loading projects...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/projects/api/list');
        const data = await response.json();
        
        console.log('📦 Full API Response:', data); // Debug
        
        if (data.success) {
            projectsData = data.projects || [];
            console.log(`✓ Loaded ${projectsData.length} projects`);
            
            // Debug: Log first project structure if available
            if (projectsData.length > 0) {
                console.log('📋 First project structure:', projectsData[0]);
                console.log('📋 First project keys:', Object.keys(projectsData[0]));
            }
            
            renderProjects();
            updateStatistics();
        } else {
            console.error('❌ API returned error:', data.error);
            showNotification(data.error || 'Failed to load projects', 'error');
            showEmptyState();
        }
    } catch (error) {
        console.error('❌ Error loading projects:', error);
        showNotification('Error connecting to server', 'error');
        showEmptyState();
    }
}

function renderProjects(filteredProjects = null) {
    const grid = document.getElementById('projectsGrid');
    const projects = filteredProjects || projectsData;
    
    if (!projects || projects.length === 0) {
        showEmptyState();
        return;
    }
    
    grid.innerHTML = projects.map(project => createProjectCard(project)).join('');
    
    // Add click handlers
    document.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.project-actions')) {
                const projectId = card.dataset.projectId;
                viewProjectDetail(projectId);
            }
        });
    });
}

function showEmptyState() {
    const grid = document.getElementById('projectsGrid');
    grid.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-seedling"></i>
            <h3>No Projects Yet</h3>
            <p>Start your first land restoration project with just one click</p>
            <button class="btn btn-primary" onclick="openProjectModal()">
                <i class="fas fa-plus"></i> Create Project
            </button>
        </div>
    `;
}

function createProjectCard(project) {
    console.log('Creating card for project:', project); // Debug log
    
    const statusColors = {
        'planning': '#3498db',
        'active': '#2ecc71',
        'completed': '#9b59b6',
        'paused': '#e67e22'
    };
    
    const degradationIcons = {
        'minimal': '✅',
        'moderate': '⚠️',
        'severe': '🔴',
        'critical': '🚨'
    };
    
    // Safely get values with fallbacks
    const projectName = project.name || 'Unnamed Project';
    const projectType = project.project_type || 'unknown';
    const projectStatus = project.status || 'planning';
    const location = project.location || 'Unknown Location';
    const areaHectares = project.area_hectares || 0;
    const climateZone = project.climate_zone || 'N/A';
    const soilType = project.soil_type || 'N/A';
    const degradationLevel = project.land_degradation_level || 'unknown';
    const vegetationIndex = project.vegetation_index !== null && project.vegetation_index !== undefined 
        ? project.vegetation_index 
        : 'N/A';
    const progressPercentage = project.progress_percentage || 0;
    
    const degradationIcon = degradationIcons[degradationLevel] || '❓';
    const statusColor = statusColors[projectStatus] || '#95a5a6';
    
    return `
        <div class="project-card" data-project-id="${project.id}">
            <div class="project-header">
                <div class="project-title">
                    <h3>${escapeHtml(projectName)}</h3>
                    <span class="project-type">${formatProjectType(projectType)}</span>
                </div>
                <span class="project-status" style="background: ${statusColor}">
                    ${projectStatus.charAt(0).toUpperCase() + projectStatus.slice(1)}
                </span>
            </div>
            
            <div class="project-meta">
                <span><i class="fas fa-map-marker-alt"></i> ${escapeHtml(location)}</span>
                <span><i class="fas fa-ruler-combined"></i> ${parseFloat(areaHectares).toFixed(1)} ha</span>
            </div>
            
            <div class="project-analysis">
                <div class="analysis-item">
                    <span class="label">Climate Zone</span>
                    <span class="value">${climateZone}</span>
                </div>
                <div class="analysis-item">
                    <span class="label">Soil Type</span>
                    <span class="value">${soilType}</span>
                </div>
                <div class="analysis-item">
                    <span class="label">Degradation</span>
                    <span class="value">
                        ${degradationIcon}
                        ${degradationLevel.charAt(0).toUpperCase() + degradationLevel.slice(1)}
                    </span>
                </div>
                <div class="analysis-item">
                    <span class="label">NDVI</span>
                    <span class="value">${vegetationIndex !== 'N/A' ? parseFloat(vegetationIndex).toFixed(2) : 'N/A'}</span>
                </div>
            </div>
            
            <div class="progress-section">
                <div class="progress-header">
                    <span>Progress</span>
                    <span>${parseInt(progressPercentage)}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${parseInt(progressPercentage)}%"></div>
                </div>
            </div>
            
            <div class="project-actions">
                <button class="btn-icon" onclick="event.stopPropagation(); viewProjectDetail(${project.id})" title="View Details">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn-icon" onclick="event.stopPropagation(); reanalyzeProject(${project.id})" title="Re-analyze">
                    <i class="fas fa-sync"></i>
                </button>
                <button class="btn-icon" onclick="event.stopPropagation(); editProject(${project.id})" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        </div>
    `;
}

function updateStatistics() {
    const activeProjects = projectsData.filter(p => p.status === 'active').length;
    const totalArea = projectsData.reduce((sum, p) => sum + parseFloat(p.area_hectares || 0), 0);
    const avgProgress = projectsData.length > 0 
        ? projectsData.reduce((sum, p) => sum + (parseInt(p.progress_percentage) || 0), 0) / projectsData.length 
        : 0;
    const alerts = projectsData.filter(p => 
        p.land_degradation_level === 'severe' || p.land_degradation_level === 'critical'
    ).length;
    
    const activeCountEl = document.getElementById('activeCount');
    const totalAreaEl = document.getElementById('totalArea');
    const avgProgressEl = document.getElementById('avgProgress');
    const alertCountEl = document.getElementById('alertCount');
    
    if (activeCountEl) activeCountEl.textContent = activeProjects;
    if (totalAreaEl) totalAreaEl.textContent = totalArea.toFixed(1);
    if (avgProgressEl) avgProgressEl.textContent = Math.round(avgProgress);
    if (alertCountEl) alertCountEl.textContent = alerts;
}

// ========================
// FILTER FUNCTIONALITY
// ========================

function filterProjects() {
    const searchTerm = document.getElementById('searchProjects')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('filterStatus')?.value || '';
    const typeFilter = document.getElementById('filterType')?.value || '';
    
    const filtered = projectsData.filter(project => {
        const matchesSearch = project.name.toLowerCase().includes(searchTerm) ||
                            (project.location && project.location.toLowerCase().includes(searchTerm));
        const matchesStatus = !statusFilter || project.status === statusFilter;
        const matchesType = !typeFilter || project.project_type === typeFilter;
        
        return matchesSearch && matchesStatus && matchesType;
    });
    
    renderProjects(filtered);
}

// ========================
// MODAL MANAGEMENT
// ========================

function openProjectModal() {
    console.log('Opening project modal...');
    const modal = document.getElementById('projectModal');
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        setTimeout(() => {
            if (!map) {
                initializeMap();
            }
        }, 100);
    }
}

function closeProjectModal() {
    const modal = document.getElementById('projectModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
        
        const form = document.getElementById('projectForm');
        if (form) form.reset();
        
        currentAnalysis = null;
    }
}

// ========================
// MAP FUNCTIONALITY
// ========================

function initializeMap() {
    const container = document.getElementById('mapContainer');
    if (!container) return;
    
    console.log('Initializing map...');
    
    const defaultLat = -1.2921;
    const defaultLng = 36.8219;
    
    try {
        map = L.map(container).setView([defaultLat, defaultLng], 7);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
        map.on('click', (e) => {
            const lat = e.latlng.lat.toFixed(6);
            const lng = e.latlng.lng.toFixed(6);
            
            document.getElementById('latitude').value = lat;
            document.getElementById('longitude').value = lng;
            
            updateMapMarker();
        });
        
        console.log('✓ Map initialized');
    } catch (error) {
        console.error('Map error:', error);
    }
}

function updateMapMarker() {
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    
    if (!latInput || !lngInput) return;
    
    const lat = parseFloat(latInput.value);
    const lng = parseFloat(lngInput.value);
    
    if (!isNaN(lat) && !isNaN(lng) && map) {
        if (marker) {
            map.removeLayer(marker);
        }
        
        marker = L.marker([lat, lng]).addTo(map);
        map.setView([lat, lng], 12);
    }
}

// ========================
// QUICK CREATE FUNCTIONALITY
// ========================

async function handleQuickCreate() {
    console.log('🚀 Quick Create initiated');
    
    const btn = document.getElementById('quickCreateBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    }
    
    showNotification('🎯 Getting your location and analyzing...', 'info');
    
    try {
        // Get GPS location
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            });
        });
        
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        
        console.log('GPS Location:', lat, lng);
        
        // Create project with minimal info
        const projectData = {
            name: `Project at ${new Date().toLocaleString()}`,
            description: 'Quick-created project',
            project_type: 'reforestation',
            area_hectares: 10, // Default 10 hectares
            latitude: lat,
            longitude: lng
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
        showNotification('Failed to create project. Please try manual creation.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-bolt"></i> Quick Create';
        }
    }
}

// ========================
// FORM SUBMISSION
// ========================

async function handleProjectSubmit(e) {
    e.preventDefault();
    console.log('📝 Submitting project form...');
    
    const formData = {
        name: document.getElementById('projectName')?.value,
        description: document.getElementById('projectDescription')?.value || '',
        project_type: document.getElementById('projectType')?.value,
        area_hectares: parseFloat(document.getElementById('projectArea')?.value),
        latitude: parseFloat(document.getElementById('latitude')?.value),
        longitude: parseFloat(document.getElementById('longitude')?.value)
    };
    
    // Validate
    if (!formData.name || !formData.project_type || !formData.area_hectares || !formData.latitude || !formData.longitude) {
        showNotification('Please fill all required fields', 'warning');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    }
    
    try {
        const response = await fetch('/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('🎉 Project created successfully!', 'success');
            closeProjectModal();
            await loadProjects();
        } else {
            showNotification(data.error || 'Failed to create project', 'error');
        }
    } catch (error) {
        console.error('Submission error:', error);
        showNotification('Failed to create project', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Create Project';
        }
    }
}

// ========================
// PROJECT ACTIONS
// ========================

function viewProjectDetail(projectId) {
    window.location.href = `/projects/${projectId}`;
}

async function reanalyzeProject(projectId) {
    if (!confirm('Re-analyze this project?')) return;
    
    try {
        const response = await fetch(`/projects/${projectId}/reanalyze`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('✓ Project re-analyzed', 'success');
            await loadProjects();
        } else {
            showNotification(data.error || 'Re-analysis failed', 'error');
        }
    } catch (error) {
        showNotification('Failed to re-analyze', 'error');
    }
}

function editProject(projectId) {
    window.location.href = `/projects/${projectId}/edit`;
}

// Make functions globally accessible
window.viewProjectDetail = viewProjectDetail;
window.reanalyzeProject = reanalyzeProject;
window.editProject = editProject;
window.openProjectModal = openProjectModal;
window.closeProjectModal = closeProjectModal;

// ========================
// UTILITY FUNCTIONS
// ========================

function formatProjectType(type) {
    if (!type) return 'Unknown';
    return type.split('-').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
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
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10000;';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    setTimeout(() => notification.classList.add('show'), 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

console.log('✓ RegenArdhi Projects JavaScript loaded!');