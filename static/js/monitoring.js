// ========================================
// REGENARDHI - MONITORING DASHBOARD JS
// Real-time monitoring with AI insights
// ========================================

// Global State
const state = {
    projects: [],
    selectedProject: null,
    alerts: [],
    map: null,
    layers: {
        satellite: null,
        ndvi: null,
        soil: null,
        landcover: null,
        current: 'satellite'
    },
    charts: {
        ndvi: null,
        climate: null
    },
    monitoringData: null
};

// ========================
// INITIALIZATION
// ========================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 RegenArdhi Monitoring - Initializing...');
    
    initializeNavigation();
    initializeEventListeners();
    initializeMap();
    loadProjects();
    startRealtimeUpdates();
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
    // Project selector
    document.getElementById('projectSelector')?.addEventListener('change', handleProjectChange);
    
    // Refresh button
    document.getElementById('refreshDataBtn')?.addEventListener('click', refreshAllData);
    
    // Layer controls
    document.querySelectorAll('.layer-btn').forEach(btn => {
        btn.addEventListener('click', () => switchLayer(btn.dataset.layer));
    });
    
    // Close modal on backdrop click
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
            renderProjectSelector();
            
            // Auto-select first project
            if (state.projects.length > 0) {
                state.selectedProject = state.projects[0];
                document.getElementById('projectSelector').value = state.projects[0].id;
                await loadMonitoringData(state.projects[0].id);
            }
            
            console.log(`✓ Loaded ${state.projects.length} projects`);
        } else {
            showNotification(data.error || 'Failed to load projects', 'error');
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        showNotification('Error connecting to server', 'error');
    }
}

function renderProjectSelector() {
    const selector = document.getElementById('projectSelector');
    if (!selector) return;
    
    if (state.projects.length === 0) {
        selector.innerHTML = '<option value="">No projects available</option>';
        return;
    }
    
    selector.innerHTML = state.projects.map(project => 
        `<option value="${project.id}">${escapeHtml(project.name)} - ${project.location || 'Unknown'}</option>`
    ).join('');
}

async function handleProjectChange(e) {
    const projectId = parseInt(e.target.value);
    const project = state.projects.find(p => p.id === projectId);
    
    if (project) {
        state.selectedProject = project;
        await loadMonitoringData(projectId);
    }
}

async function loadMonitoringData(projectId) {
    showNotification('📡 Loading monitoring data...', 'info');
    
    try {
        const response = await fetch(`/monitoring/api/project/${projectId}/data`);
        const data = await response.json();
        
        if (data.success) {
            // Use latest data from backend
            state.monitoringData = data.latest || {};
            state.monitoringHistory = data.history || [];
            
            // If no data exists, trigger update
            if (!data.latest) {
                await updateMonitoringData(projectId);
            } else {
                updateDashboard();
                showNotification('✓ Data loaded successfully', 'success');
            }
        } else {
            showNotification(data.error || 'Failed to load monitoring data', 'error');
            showEmptyDashboard();
        }
    } catch (error) {
        console.error('Error loading monitoring data:', error);
        showNotification('Error loading data', 'error');
        showEmptyDashboard();
    }
}

async function updateMonitoringData(projectId) {
    showNotification('🔄 Updating monitoring data...', 'info');
    
    try {
        const response = await fetch(`/monitoring/api/project/${projectId}/update`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            state.monitoringData = data.data;
            updateDashboard();
            showNotification('✓ Monitoring data updated!', 'success');
        } else {
            showNotification(data.error || 'Failed to update', 'error');
        }
    } catch (error) {
        console.error('Error updating monitoring data:', error);
        showNotification('Error updating data', 'error');
    }
}

// ========================
// DASHBOARD UPDATE
// ========================

function updateDashboard() {
    if (!state.monitoringData) return;
    
    updateQuickStats();
    updateAlerts();
    updateMap();
    updateAIInsights();
    updateCharts();
    updateHealthScore();
}

function updateQuickStats() {
    const data = state.monitoringData;
    
    document.getElementById('currentNDVI').textContent = 
        data.vegetation_index ? parseFloat(data.vegetation_index).toFixed(2) : '--';
    
    document.getElementById('currentTemp').textContent = 
        data.temperature ? `${data.temperature}°C` : '--';
    
    document.getElementById('soilMoisture').textContent = 
        data.soil_moisture ? `${data.soil_moisture}%` : '--';
}

function updateAlerts() {
    const alertsList = document.getElementById('alertsList');
    const alertCount = document.getElementById('alertCount');
    
    if (!alertsList) return;
    
    // Generate smart alerts based on data
    const alerts = generateSmartAlerts();
    state.alerts = alerts;
    
    alertCount.textContent = alerts.length;
    
    if (alerts.length === 0) {
        alertsList.innerHTML = `
            <div class="empty-state" style="padding: 2rem 1rem;">
                <i class="fas fa-check-circle" style="color: #10b981;"></i>
                <p style="font-size: 0.9rem; color: #6b7280;">No alerts - All good!</p>
            </div>
        `;
        return;
    }
    
    alertsList.innerHTML = alerts.map(alert => createAlertCard(alert)).join('');
}

function generateSmartAlerts() {
    const alerts = [];
    const data = state.monitoringData;
    
    if (!data) return alerts;
    
    // NDVI degradation alert
    if (data.vegetation_index && data.vegetation_index < 0.3) {
        alerts.push({
            type: 'critical',
            title: 'Vegetation Degradation Detected',
            description: `NDVI index at ${parseFloat(data.vegetation_index).toFixed(2)} - Below healthy threshold`,
            zone: 'Zone 3',
            time: 'Just now'
        });
    }
    
    // Soil moisture alert
    if (data.soil_moisture && data.soil_moisture < 20) {
        alerts.push({
            type: 'warning',
            title: 'Low Soil Moisture',
            description: `Soil moisture at ${data.soil_moisture}% - Consider irrigation`,
            zone: 'Multiple zones',
            time: '15 minutes ago'
        });
    }
    
    // Temperature stress alert
    if (data.temperature && data.temperature > 35) {
        alerts.push({
            type: 'warning',
            title: 'High Temperature Stress',
            description: `Temperature at ${data.temperature}°C - Plants may need protection`,
            zone: 'All zones',
            time: '1 hour ago'
        });
    }
    
    // Land degradation alert
    if (data.land_degradation_level && data.land_degradation_level !== 'low') {
        alerts.push({
            type: 'critical',
            title: 'Land Degradation Detected',
            description: `${data.land_degradation_level} level degradation - Immediate action needed`,
            zone: 'Central area',
            time: '2 hours ago'
        });
    }
    
    // Positive alert for good progress
    if (data.vegetation_index && data.vegetation_index > 0.6) {
        alerts.push({
            type: 'info',
            title: 'Excellent Vegetation Health',
            description: `NDVI at ${parseFloat(data.vegetation_index).toFixed(2)} - Keep up the good work!`,
            zone: 'All zones',
            time: '30 minutes ago'
        });
    }
    
    return alerts;
}

function createAlertCard(alert) {
    return `
        <div class="alert-item" onclick="showZoneDetails('${alert.zone}')">
            <div class="alert-header">
                <div class="alert-icon ${alert.type}">
                    <i class="fas fa-${alert.type === 'critical' ? 'exclamation-triangle' : 
                                       alert.type === 'warning' ? 'exclamation-circle' : 'info-circle'}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-description">${alert.description}</div>
                    <div class="alert-meta">
                        <span><i class="fas fa-map-marker-alt"></i> ${alert.zone}</span>
                        <span><i class="fas fa-clock"></i> ${alert.time}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ========================
// MAP FUNCTIONS
// ========================

function initializeMap() {
    const container = document.getElementById('monitoringMap');
    if (!container || typeof L === 'undefined') {
        console.error('Leaflet not loaded or container not found');
        return;
    }
    
    try {
        state.map = L.map(container).setView([-1.2921, 36.8219], 7);
        
        // Default satellite layer
        state.layers.satellite = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(state.map);
        
        updateLegend('satellite');
        console.log('✓ Map initialized');
    } catch (error) {
        console.error('Map initialization error:', error);
    }
}

function updateMap() {
    if (!state.map || !state.selectedProject) return;
    
    const project = state.selectedProject;
    
    if (project.latitude && project.longitude) {
        // Center on project
        state.map.setView([project.latitude, project.longitude], 13);
        
        // Add project marker
        const marker = L.marker([project.latitude, project.longitude])
            .bindPopup(`
                <div style="min-width: 200px;">
                    <strong style="font-size: 1.1em; color: #10b981;">${project.name}</strong><br>
                    <span style="color: #6b7280;">📍 ${project.location || 'Unknown'}</span><br>
                    <span style="color: #6b7280;">📏 ${parseFloat(project.area_hectares || 0).toFixed(1)} hectares</span>
                </div>
            `)
            .addTo(state.map);
        
        // Add degraded zone markers (simulated)
        addDegradedZoneMarkers();
    }
}

function addDegradedZoneMarkers() {
    if (!state.monitoringData || !state.selectedProject) return;
    
    const project = state.selectedProject;
    const data = state.monitoringData;
    
    // Simulate degraded zones around the project
    if (data.vegetation_index && data.vegetation_index < 0.4) {
        const zones = [
            { lat: project.latitude + 0.01, lng: project.longitude + 0.01, severity: 'high' },
            { lat: project.latitude - 0.01, lng: project.longitude + 0.01, severity: 'medium' },
            { lat: project.latitude + 0.01, lng: project.longitude - 0.01, severity: 'low' }
        ];
        
        zones.forEach((zone, index) => {
            const color = zone.severity === 'high' ? '#ef4444' : 
                         zone.severity === 'medium' ? '#f59e0b' : '#10b981';
            
            const icon = L.divIcon({
                className: 'zone-marker',
                html: `<div class="zone-marker ${zone.severity === 'high' ? 'degraded' : 
                                                 zone.severity === 'medium' ? 'warning' : ''}" 
                            style="width: 24px; height: 24px; background: ${color}; 
                                   border: 3px solid white; border-radius: 50%; 
                                   box-shadow: 0 2px 8px rgba(0,0,0,0.3);"></div>`,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            
            L.marker([zone.lat, zone.lng], { icon })
                .bindPopup(`
                    <div style="min-width: 150px;">
                        <strong>Zone ${index + 1}</strong><br>
                        <span style="color: ${color};">⚠️ ${zone.severity.toUpperCase()} degradation</span><br>
                        <button onclick="showZoneDetails('Zone ${index + 1}')" 
                                style="margin-top: 8px; padding: 4px 12px; background: #10b981; 
                                       color: white; border: none; border-radius: 6px; cursor: pointer;">
                            View Details
                        </button>
                    </div>
                `)
                .addTo(state.map);
        });
    }
}

function switchLayer(layerName) {
    if (!state.map) return;
    
    // Update button states
    document.querySelectorAll('.layer-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.layer === layerName);
    });
    
    // Switch layer (for demo, just update legend)
    state.layers.current = layerName;
    updateLegend(layerName);
    
    showNotification(`📡 Switched to ${layerName.toUpperCase()} layer`, 'info');
}

function updateLegend(layerName) {
    const legend = document.getElementById('mapLegend');
    if (!legend) return;
    
    const legends = {
        satellite: `
            <div class="legend-item">
                <span style="color: #6b7280;">Standard satellite view</span>
            </div>
        `,
        ndvi: `
            <div class="legend-item">
                <div class="legend-gradient ndvi"></div>
                <div class="legend-labels" style="width: 100px;">
                    <span>Low</span>
                    <span>High</span>
                </div>
            </div>
            <div class="legend-item">
                <span style="color: #6b7280;">Vegetation Health (NDVI)</span>
            </div>
        `,
        soil: `
            <div class="legend-item">
                <div class="legend-gradient soil"></div>
                <div class="legend-labels" style="width: 100px;">
                    <span>Poor</span>
                    <span>Good</span>
                </div>
            </div>
            <div class="legend-item">
                <span style="color: #6b7280;">Soil Health Index</span>
            </div>
        `,
        landcover: `
            <div class="legend-item">
                <span class="score-dot" style="background: #10b981;"></span>
                <span>Forest</span>
            </div>
            <div class="legend-item">
                <span class="score-dot" style="background: #fbbf24;"></span>
                <span>Grassland</span>
            </div>
            <div class="legend-item">
                <span class="score-dot" style="background: #78350f;"></span>
                <span>Bare Soil</span>
            </div>
        `
    };
    
    legend.innerHTML = legends[layerName] || '';
}

window.toggleFullscreenMap = function() {
    const container = document.querySelector('.map-section');
    if (!document.fullscreenElement) {
        container.requestFullscreen?.();
    } else {
        document.exitFullscreen?.();
    }
};

// ========================
// AI INSIGHTS
// ========================

function updateAIInsights() {
    const container = document.getElementById('aiInsightsContent');
    if (!container || !state.monitoringData) return;
    
    const insights = generateAIInsights();
    
    container.innerHTML = insights.map(insight => createInsightCard(insight)).join('');
}

function generateAIInsights() {
    const data = state.monitoringData;
    const insights = [];
    
    if (!data) return insights;
    
    // NDVI Analysis
    if (data.vegetation_index) {
        const ndvi = parseFloat(data.vegetation_index);
        if (ndvi > 0.6) {
            insights.push({
                type: 'positive',
                title: 'Excellent Vegetation Health',
                description: `Current NDVI of ${ndvi.toFixed(2)} indicates healthy, dense vegetation. Continue current management practices.`,
                confidence: 92
            });
        } else if (ndvi < 0.3) {
            insights.push({
                type: 'critical',
                title: 'Vegetation Stress Detected',
                description: `NDVI of ${ndvi.toFixed(2)} suggests significant vegetation loss. Recommend immediate reforestation efforts and soil conservation measures.`,
                confidence: 88
            });
        }
    }
    
    // Climate Analysis
    if (data.temperature && data.rainfall) {
        if (data.temperature > 30 && data.rainfall < 500) {
            insights.push({
                type: 'warning',
                title: 'Drought Risk',
                description: 'High temperatures combined with low rainfall increase drought risk. Consider drought-resistant species and water conservation techniques.',
                confidence: 85
            });
        }
    }
    
    // Soil Health
    if (data.soil_type) {
        insights.push({
            type: 'positive',
            title: 'Soil Suitability Analysis',
            description: `${data.soil_type} soil detected. Optimal for agroforestry and indigenous tree species. Recommended crops: ${(data.recommended_crops || []).slice(0, 3).join(', ')}.`,
            confidence: 90
        });
    }
    
    // Restoration Progress
    if (data.progress_percentage) {
        const progress = parseInt(data.progress_percentage);
        if (progress > 50) {
            insights.push({
                type: 'positive',
                title: 'Strong Restoration Progress',
                description: `Project is ${progress}% complete. Vegetation recovery is on track. Maintain current interventions for continued success.`,
                confidence: 87
            });
        }
    }
    
    // Seasonal Recommendations
    const month = new Date().getMonth();
    if (month >= 2 && month <= 4) { // March-May (long rains)
        insights.push({
            type: 'positive',
            title: 'Optimal Planting Season',
            description: 'Current season is ideal for tree planting. High rainfall expected. Maximize planting efforts in the next 4-6 weeks.',
            confidence: 95
        });
    }
    
    return insights;
}

function createInsightCard(insight) {
    const iconMap = {
        positive: 'check-circle',
        warning: 'exclamation-triangle',
        critical: 'exclamation-circle'
    };
    
    return `
        <div class="insight-card ${insight.type}">
            <div class="insight-header">
                <div class="insight-icon">
                    <i class="fas fa-${iconMap[insight.type] || 'brain'}"></i>
                </div>
                <div class="insight-title">${insight.title}</div>
            </div>
            <div class="insight-description">${insight.description}</div>
            <div class="insight-confidence">
                AI Confidence: ${insight.confidence}%
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${insight.confidence}%;"></div>
                </div>
            </div>
        </div>
    `;
}

window.refreshInsights = function() {
    showNotification('🔄 Refreshing AI insights...', 'info');
    setTimeout(() => {
        updateAIInsights();
        showNotification('✓ Insights updated', 'success');
    }, 1000);
};

// ========================
// CHARTS
// ========================

function updateCharts() {
    updateNDVIChart();
    updateClimateChart();
}

function updateNDVIChart() {
    const canvas = document.getElementById('ndviChart');
    if (!canvas || typeof Chart === 'undefined') return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart
    if (state.charts.ndvi) {
        state.charts.ndvi.destroy();
    }
    
    // Generate sample NDVI trend data
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const currentNDVI = state.monitoringData?.vegetation_index || 0.5;
    const ndviData = generateTrendData(currentNDVI, 6);
    
    state.charts.ndvi = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: 'NDVI Index',
                data: ndviData,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#10b981',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: { size: 12, weight: '600' },
                        color: '#374151'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    padding: 12,
                    titleFont: { size: 13, weight: '600' },
                    bodyFont: { size: 12 },
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    grid: {
                        color: '#e5e7eb',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 }
                    }
                }
            }
        }
    });
}

function updateClimateChart() {
    const canvas = document.getElementById('climateChart');
    if (!canvas || typeof Chart === 'undefined') return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart
    if (state.charts.climate) {
        state.charts.climate.destroy();
    }
    
    // Generate sample climate data
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const rainfallData = [45, 60, 120, 180, 150, 80];
    const currentNDVI = state.monitoringData?.vegetation_index || 0.5;
    const ndviData = generateTrendData(currentNDVI, 6).map(v => v * 100); // Scale for visibility
    
    state.charts.climate = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Rainfall (mm)',
                    data: rainfallData,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: '#3b82f6',
                    borderWidth: 2,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Vegetation Index (scaled)',
                    data: ndviData,
                    type: 'line',
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: { size: 12, weight: '600' },
                        color: '#374151',
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    padding: 12,
                    titleFont: { size: 13, weight: '600' },
                    bodyFont: { size: 12 },
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    grid: {
                        color: '#e5e7eb',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 },
                        callback: value => value + 'mm'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 }
                    }
                }
            }
        }
    });
}

function generateTrendData(current, count) {
    const data = [];
    let value = current * 0.6; // Start lower
    
    for (let i = 0; i < count; i++) {
        value += (Math.random() * 0.1 - 0.02); // Gradual increase with some variance
        value = Math.max(0.1, Math.min(1, value)); // Clamp between 0.1 and 1
        data.push(parseFloat(value.toFixed(2)));
    }
    
    return data;
}

// ========================
// HEALTH SCORE
// ========================

function updateHealthScore() {
    const data = state.monitoringData;
    if (!data) return;
    
    // Calculate component scores
    const vegScore = calculateVegetationScore(data.vegetation_index);
    const soilScore = calculateSoilScore(data.soil_moisture, data.soil_type);
    const waterScore = calculateWaterScore(data.rainfall);
    
    // Overall health score (weighted average)
    const healthScore = Math.round((vegScore * 0.4) + (soilScore * 0.3) + (waterScore * 0.3));
    
    // Update display
    document.getElementById('healthScore').textContent = healthScore;
    document.getElementById('vegScore').textContent = vegScore + '%';
    document.getElementById('soilScore').textContent = soilScore + '%';
    document.getElementById('waterScore').textContent = waterScore + '%';
    
    // Animate circle
    animateHealthCircle(healthScore);
}

function calculateVegetationScore(ndvi) {
    if (!ndvi) return 50;
    const score = Math.round(parseFloat(ndvi) * 100);
    return Math.max(0, Math.min(100, score));
}

function calculateSoilScore(moisture, type) {
    let score = 50;
    
    if (moisture) {
        score = Math.round((moisture / 100) * 100);
    }
    
    // Bonus for good soil type
    if (type && (type.toLowerCase().includes('loam') || type.toLowerCase().includes('clay'))) {
        score = Math.min(100, score + 10);
    }
    
    return Math.max(0, Math.min(100, score));
}

function calculateWaterScore(rainfall) {
    if (!rainfall) return 60;
    
    // Optimal rainfall range: 800-1500mm/year
    let score;
    if (rainfall >= 800 && rainfall <= 1500) {
        score = 100;
    } else if (rainfall < 800) {
        score = Math.round((rainfall / 800) * 100);
    } else {
        score = Math.round(100 - ((rainfall - 1500) / 1000) * 20);
    }
    
    return Math.max(0, Math.min(100, score));
}

function animateHealthCircle(score) {
    const circle = document.getElementById('scoreCircle');
    if (!circle) return;
    
    const circumference = 2 * Math.PI * 54; // radius = 54
    const offset = circumference - (score / 100) * circumference;
    
    // Set color based on score
    let color = '#10b981'; // Green
    if (score < 40) color = '#ef4444'; // Red
    else if (score < 70) color = '#f59e0b'; // Orange
    
    circle.style.stroke = color;
    circle.style.strokeDashoffset = offset;
}

// ========================
// ZONE DETAILS
// ========================

window.showZoneDetails = function(zoneName) {
    const modal = document.getElementById('zoneModal');
    const title = document.getElementById('zoneModalTitle');
    const content = document.getElementById('zoneModalContent');
    
    if (!modal) return;
    
    title.innerHTML = `<i class="fas fa-map-pin"></i> ${zoneName}`;
    
    content.innerHTML = `
        <div style="padding: 1rem;">
            <div class="details-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                <div class="details-card" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1.5rem;">
                    <h4 style="margin-bottom: 1rem; color: #111827;">📊 Zone Statistics</h4>
                    <div class="project-info-row" style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #e5e7eb;">
                        <span style="color: #6b7280;">Area</span>
                        <strong style="color: #111827;">2.5 hectares</strong>
                    </div>
                    <div class="project-info-row" style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #e5e7eb;">
                        <span style="color: #6b7280;">NDVI</span>
                        <strong style="color: #111827;">0.42</strong>
                    </div>
                    <div class="project-info-row" style="display: flex; justify-content: space-between; padding: 0.5rem 0;">
                        <span style="color: #6b7280;">Status</span>
                        <strong style="color: #f59e0b;">⚠️ Degraded</strong>
                    </div>
                </div>
                
                <div class="details-card" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1.5rem;">
                    <h4 style="margin-bottom: 1rem; color: #111827;">🎯 Recommendations</h4>
                    <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.5rem;">
                        <li style="padding: 0.5rem; background: white; border-left: 3px solid #10b981; border-radius: 6px; font-size: 0.9rem;">
                            <i class="fas fa-check-circle" style="color: #10b981; margin-right: 0.5rem;"></i>
                            Plant drought-resistant species
                        </li>
                        <li style="padding: 0.5rem; background: white; border-left: 3px solid #10b981; border-radius: 6px; font-size: 0.9rem;">
                            <i class="fas fa-check-circle" style="color: #10b981; margin-right: 0.5rem;"></i>
                            Implement soil conservation
                        </li>
                        <li style="padding: 0.5rem; background: white; border-left: 3px solid #10b981; border-radius: 6px; font-size: 0.9rem;">
                            <i class="fas fa-check-circle" style="color: #10b981; margin-right: 0.5rem;"></i>
                            Install water harvesting
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    `;
    
    modal.classList.add('show');
};

window.closeZoneModal = function() {
    document.getElementById('zoneModal')?.classList.remove('show');
};

// ========================
// REALTIME UPDATES
// ========================

function startRealtimeUpdates() {
    // Refresh data every 5 minutes
    setInterval(() => {
        if (state.selectedProject) {
            console.log('🔄 Auto-refreshing monitoring data...');
            loadMonitoringData(state.selectedProject.id);
        }
    }, 300000); // 5 minutes
}

async function refreshAllData() {
    const btn = document.getElementById('refreshDataBtn');
    if (!btn) return;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    showNotification('🔄 Refreshing all data...', 'info');
    
    try {
        await loadProjects();
        if (state.selectedProject) {
            await loadMonitoringData(state.selectedProject.id);
        }
        showNotification('✓ All data refreshed!', 'success');
    } catch (error) {
        showNotification('Error refreshing data', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sync"></i>';
    }
}

// ========================
// HELPER FUNCTIONS
// ========================

function showEmptyDashboard() {
    document.getElementById('currentNDVI').textContent = '--';
    document.getElementById('currentTemp').textContent = '--';
    document.getElementById('soilMoisture').textContent = '--';
    document.getElementById('healthScore').textContent = '--';
    document.getElementById('vegScore').textContent = '--';
    document.getElementById('soilScore').textContent = '--';
    document.getElementById('waterScore').textContent = '--';
    
    const alertsList = document.getElementById('alertsList');
    if (alertsList) {
        alertsList.innerHTML = `
            <div class="empty-state" style="padding: 2rem 1rem;">
                <i class="fas fa-satellite-dish" style="font-size: 3rem; color: #d1d5db;"></i>
                <p style="font-size: 0.9rem; color: #6b7280; margin-top: 1rem;">No monitoring data available</p>
            </div>
        `;
    }
    
    const insights = document.getElementById('aiInsightsContent');
    if (insights) {
        insights.innerHTML = `
            <div class="empty-state" style="padding: 2rem 1rem;">
                <i class="fas fa-brain" style="font-size: 3rem; color: #d1d5db;"></i>
                <p style="font-size: 0.9rem; color: #6b7280; margin-top: 1rem;">No AI insights available</p>
            </div>
        `;
    }
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

console.log('✓ RegenArdhi Monitoring loaded!');