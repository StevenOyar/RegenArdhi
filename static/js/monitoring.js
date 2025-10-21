// ========================================
// REGENARDHI - ADVANCED MONITORING SYSTEM
// Production-Ready with NASA GIBS, OpenWeather & Notifications
// Version 3.0 - Fully Integrated
// ========================================

const MonitoringSystem = {
    state: {
        map: null,
        currentLayer: 'satellite',
        selectedProject: null,
        projects: [],
        weatherData: null,
        forecastData: [],
        alerts: [],
        aiRecommendations: [],
        markers: [],
        currentOverlay: null,
        charts: {},
        refreshInterval: null,
        weatherInterval: null,
        lastWeatherUpdate: null,
        isInitialized: false
    },

    // NASA GIBS Layer Configurations - Fixed for proper tile loading
    layers: {
        satellite: {
            name: 'NASA VIIRS True Color',
            type: 'nasa',
            getUrl: function() {
                // Use yesterday's date for most reliable imagery
                const date = new Date();
                date.setDate(date.getDate() - 1);
                const dateStr = date.toISOString().split('T')[0];
                return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/${dateStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;
            },
            attribution: '© NASA EOSDIS GIBS',
            maxZoom: 9,
            minZoom: 1,
            tileSize: 256,
            opacity: 1.0,
            tms: false
        },
        ndvi: {
            name: 'MODIS NDVI (Vegetation Index)',
            type: 'nasa',
            getUrl: function() {
                // MODIS NDVI is 8-day composite, use date from 8 days ago
                const date = new Date();
                date.setDate(date.getDate() - 8);
                const dateStr = date.toISOString().split('T')[0];
                return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/${dateStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`;
            },
            attribution: '© NASA MODIS Terra',
            maxZoom: 9,
            minZoom: 1,
            tileSize: 256,
            opacity: 0.8,
            tms: false
        },
       soil: {
            name: 'SMAP Soil Moisture',
            type: 'nasa',
            getUrl: function() {
                // SMAP L4 updates every 3 days, use recent date that has data
                const date = new Date();
                date.setDate(date.getDate() - 7); // Use 7 days ago for more reliable data
                const dateStr = date.toISOString().split('T')[0];
                // Use corrected SMAP layer name - Surface Soil Moisture is more reliable
                return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/SMAP_L4_Analyzed_Surface_Soil_Moisture/default/${dateStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`;
            },
            attribution: '© NASA SMAP',
            maxZoom: 9,
            minZoom: 1,
            tileSize: 256,
            opacity: 0.75,
            tms: false
        },
        terrain: {
            name: 'OpenTopoMap Terrain',
            type: 'osm',
            getUrl: function() {
                return 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png';
            },
            attribution: '© OpenTopoMap contributors',
            maxZoom: 17,
            minZoom: 1,
            tileSize: 256,
            opacity: 1.0,
            subdomains: ['a', 'b', 'c'],
            tms: false
        }
    },

    // ========================
    // INITIALIZATION
    // ========================

    init() {
        console.log('🛰️ Initializing Advanced Monitoring System...');

        // Check dependencies
        if (!this.checkDependencies()) {
            console.error('❌ Missing required dependencies');
            return;
        }

        this.setupEventListeners();
        this.loadProjects();
        this.initializeCharts();

        // Auto-refresh every 5 minutes
        this.state.refreshInterval = setInterval(() => {
            this.refreshData();
        }, 300000);

        this.state.isInitialized = true;
        console.log('✅ Monitoring System Ready!');

        // Show welcome notification
        if (window.NotificationSystem) {
            NotificationSystem.showLiveNotification(
                'Monitoring Active',
                'Real-time satellite and weather monitoring enabled',
                'success',
                4000
            );
        }
    },

    checkDependencies() {
        const required = ['L', 'Chart', 'NotificationSystem'];
        const missing = required.filter(dep => typeof window[dep] === 'undefined');
        
        if (missing.length > 0) {
            console.error('Missing dependencies:', missing);
            return false;
        }
        
        return true;
    },

    setupEventListeners() {
        // Project selector
        const selector = document.getElementById('projectSelector');
        if (selector) {
            selector.addEventListener('change', (e) => {
                this.selectProject(e.target.value);
            });
        }

        // Layer controls
        document.querySelectorAll('.layer-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchLayer(btn.dataset.layer);
            });
        });

        // Refresh button
        const refreshBtn = document.getElementById('refreshDataBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshData();
            });
        }

        // Period buttons for charts
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.updateChartPeriod(parseInt(btn.dataset.period));
            });
        });
    },

    // ========================
    // PROJECT LOADING
    // ========================

    async loadProjects() {
        try {
            const response = await fetch('/projects/api/list');
            const data = await response.json();

            if (data.success) {
                this.state.projects = data.projects || [];
                this.populateProjectSelector();

                if (this.state.projects.length > 0) {
                    this.selectProject(this.state.projects[0].id);
                }
            }
        } catch (error) {
            console.error('Error loading projects:', error);
            this.showNotification('Failed to load projects', 'error');
        }
    },

    populateProjectSelector() {
        const selector = document.getElementById('projectSelector');
        if (!selector) return;

        if (this.state.projects.length === 0) {
            selector.innerHTML = '<option value="">No projects available</option>';
            return;
        }

        selector.innerHTML = `
            <option value="">Select a project...</option>
            ${this.state.projects.map(p => `
                <option value="${p.id}">
                    ${this.escapeHtml(p.name)} (${parseFloat(p.area_hectares || 0).toFixed(1)} ha)
                </option>
            `).join('')}
        `;
    },

    // ========================
    // PROJECT SELECTION
    // ========================

    async selectProject(projectId) {
        if (!projectId) return;

        const project = this.state.projects.find(p => p.id == projectId);
        if (!project) return;

        this.state.selectedProject = project;

        // Show loading states
        this.showLoadingStates();

        try {
            // Load all data in parallel
            await Promise.all([
                this.loadProjectMetrics(projectId),
                this.loadWeatherData(project.latitude, project.longitude),
                this.loadAlerts(projectId),
                this.loadAIRecommendations(projectId),
                this.loadRecommendedPlants(projectId),
                this.loadSuitableProducts(projectId)
            ]);

            // Initialize/update map
            this.initializeMap(project);

            // Update charts
            this.updateCharts(projectId);

            this.showNotification(`Monitoring ${project.name}`, 'success');
        } catch (error) {
            console.error('Error loading project data:', error);
            this.showNotification('Failed to load complete project data', 'error');
        }
    },

    showLoadingStates() {
        const loadingHTML = `
            <div class="loading-state">
                <div class="loader-ring"></div>
                <p>Loading data...</p>
            </div>
        `;

        const containers = [
            'alertsList',
            'aiRecommendations',
            'recommendedPlants',
            'suitableProducts'
        ];

        containers.forEach(id => {
            const elem = document.getElementById(id);
            if (elem) elem.innerHTML = loadingHTML;
        });
    },

    // ========================
    // PROJECT METRICS
    // ========================

    async loadProjectMetrics(projectId) {
        try {
            const response = await fetch(`/monitoring/api/metrics/${projectId}`);
            const data = await response.json();

            if (data.success) {
                this.updateQuickStats(data.metrics);
                this.updateHealthScore(data.health_score);
            }
        } catch (error) {
            console.error('Error loading metrics:', error);
        }
    },

    updateQuickStats(metrics) {
        // NDVI
        const ndvi = parseFloat(metrics.ndvi || 0).toFixed(2);
        const ndviElem = document.getElementById('currentNDVI');
        const ndviTrend = document.getElementById('ndviTrend');
        
        if (ndviElem) {
            ndviElem.textContent = ndvi;
            ndviElem.style.color = this.getNDVIColor(ndvi);
        }
        
        if (ndviTrend && metrics.ndvi_trend) {
            const trend = parseFloat(metrics.ndvi_trend);
            const trendClass = trend > 0 ? 'up' : 'down';
            ndviTrend.className = `stat-trend ${trendClass}`;
            ndviTrend.innerHTML = trend > 0 
                ? `<i class="fas fa-arrow-up"></i> ${trend.toFixed(1)}%`
                : `<i class="fas fa-arrow-down"></i> ${Math.abs(trend).toFixed(1)}%`;
        }

        // Temperature
        const temp = document.getElementById('currentTemp');
        if (temp && metrics.temperature) {
            temp.textContent = `${Math.round(metrics.temperature)}°C`;
        }

        // Soil Moisture
        const moisture = document.getElementById('soilMoisture');
        if (moisture && metrics.soil_moisture) {
            moisture.textContent = `${Math.round(metrics.soil_moisture)}%`;
        }

        // Health Score
        const healthScore = document.getElementById('healthScore');
        if (healthScore && metrics.health_score) {
            healthScore.textContent = Math.round(metrics.health_score);
        }
    },

    updateHealthScore(scoreData) {
        const scoreValue = document.getElementById('healthScoreValue');
        const scoreCircle = document.getElementById('scoreCircle');

        if (scoreValue && scoreData) {
            const score = parseInt(scoreData.overall || 0);
            scoreValue.textContent = score;

            // Animate circle
            if (scoreCircle) {
                const circumference = 2 * Math.PI * 70;
                const offset = circumference - (score / 100) * circumference;
                scoreCircle.style.strokeDashoffset = offset;
                scoreCircle.style.stroke = this.getHealthColor(score);
            }

            // Update component scores
            if (scoreData.components) {
                const vegScore = document.getElementById('vegScore');
                const soilScore = document.getElementById('soilScore');
                const waterScore = document.getElementById('waterScore');
                const bioScore = document.getElementById('bioScore');

                if (vegScore) vegScore.textContent = scoreData.components.vegetation || '--';
                if (soilScore) soilScore.textContent = scoreData.components.soil || '--';
                if (waterScore) waterScore.textContent = scoreData.components.water || '--';
                if (bioScore) bioScore.textContent = scoreData.components.biodiversity || '--';
            }
        }
    },

    // ========================
    // SECURE WEATHER API (BACKEND PROXY)
    // ========================

    async loadWeatherData(lat, lon) {
        try {
            // Call secure backend endpoint - API key never exposed
            const response = await fetch(`/monitoring/api/weather?lat=${lat}&lon=${lon}`);
            const data = await response.json();

            if (data.success) {
                this.state.weatherData = data.current;
                this.state.forecastData = data.forecast || [];
                this.state.lastWeatherUpdate = new Date();

                this.updateWeatherDisplay();
                this.updateWeatherChart();
                this.checkWeatherAlerts();

                console.log('✅ Weather data loaded:', {
                    source: data.source,
                    temp: data.current.temp,
                    forecast_days: data.forecast.length
                });
            }
        } catch (error) {
            console.error('Error loading weather:', error);
            this.showNotification('Weather data unavailable', 'warning');
        }
    },

    updateWeatherDisplay() {
        const weather = this.state.weatherData;
        if (!weather) return;

        // Update temperature
        const tempElem = document.getElementById('currentTemp');
        const tempTrend = document.getElementById('tempTrend');
        
        if (tempElem) {
            tempElem.textContent = `${Math.round(weather.temp)}°C`;
        }

        if (tempTrend) {
            const feels = Math.round(weather.feels_like);
            tempTrend.innerHTML = `<i class="fas fa-thermometer-half"></i> Feels ${feels}°C`;
            tempTrend.className = 'stat-trend';
        }

        // Update humidity in soil moisture stat temporarily
        const moistureElem = document.getElementById('soilMoisture');
        if (moistureElem && !this.state.selectedProject?.soil_moisture) {
            moistureElem.textContent = `${weather.humidity}%`;
            const moistureTrend = document.getElementById('moistureTrend');
            if (moistureTrend) {
                moistureTrend.textContent = 'Air Humidity';
            }
        }
    },

    updateWeatherChart() {
        if (!this.state.forecastData || this.state.forecastData.length === 0) {
            console.log('No forecast data available');
            return;
        }

        const ctx = document.getElementById('climateChart');
        if (!ctx) return;

        // Prepare data
        const labels = this.state.forecastData.map(f => {
            const date = new Date(f.dt * 1000);
            return date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric' 
            });
        });

        const temps = this.state.forecastData.map(f => f.temp);
        const rainfall = this.state.forecastData.map(f => f.rain || 0);
        const humidity = this.state.forecastData.map(f => f.humidity);

        // Destroy existing chart
        if (this.state.charts.climate) {
            this.state.charts.climate.destroy();
        }

        // Create new chart
        this.state.charts.climate = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Temperature (°C)',
                        data: temps,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Rainfall (mm)',
                        data: rainfall,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        tension: 0.4,
                        yAxisID: 'y1',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        fill: true
                    },
                    {
                        label: 'Humidity (%)',
                        data: humidity,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y2',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
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
                        position: 'top',
                        labels: { 
                            usePointStyle: true, 
                            padding: 15,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#10b981',
                        borderWidth: 1,
                        displayColors: true
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: { 
                            display: true, 
                            text: 'Temperature (°C)',
                            font: { size: 11 }
                        },
                        ticks: { font: { size: 10 } }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: { 
                            display: true, 
                            text: 'Rainfall (mm)',
                            font: { size: 11 }
                        },
                        grid: { drawOnChartArea: false },
                        ticks: { font: { size: 10 } }
                    },
                    y2: {
                        type: 'linear',
                        position: 'right',
                        title: { 
                            display: true, 
                            text: 'Humidity (%)',
                            font: { size: 11 }
                        },
                        grid: { drawOnChartArea: false },
                        ticks: { font: { size: 10 } }
                    },
                    x: {
                        ticks: { font: { size: 10 } }
                    }
                }
            }
        });

        console.log('✅ Weather forecast chart updated');
    },

    checkWeatherAlerts() {
        const weather = this.state.weatherData;
        if (!weather) return;

        const alerts = [];

        // High temperature alert
        if (weather.temp > 35) {
            alerts.push({
                type: 'warning',
                title: 'High Temperature Alert',
                message: `Temperature is ${Math.round(weather.temp)}°C. Increase irrigation frequency and protect sensitive plants.`,
                icon: 'temperature-high',
                timestamp: new Date().toISOString()
            });
        }

        // Low temperature alert
        if (weather.temp < 5) {
            alerts.push({
                type: 'warning',
                title: 'Low Temperature Alert',
                message: `Temperature is ${Math.round(weather.temp)}°C. Frost risk - protect vegetation.`,
                icon: 'snowflake',
                timestamp: new Date().toISOString()
            });
        }

        // Rain forecast
        const upcomingRain = this.state.forecastData.slice(0, 3).reduce((sum, f) => sum + (f.rain || 0), 0);
        if (upcomingRain > 10) {
            alerts.push({
                type: 'info',
                title: 'Heavy Rain Forecast',
                message: `${upcomingRain.toFixed(1)}mm of rain expected in next 24-72 hours. Adjust irrigation plans.`,
                icon: 'cloud-rain',
                timestamp: new Date().toISOString()
            });
        }

        // Drought warning
        if (weather.humidity < 30 && weather.temp > 30) {
            alerts.push({
                type: 'error',
                title: 'Drought Conditions',
                message: `Low humidity (${weather.humidity}%) and high temperature. Implement water conservation measures.`,
                icon: 'droplet-slash',
                timestamp: new Date().toISOString()
            });
        }

        // Add alerts to the system
        alerts.forEach(alert => this.addAlert(alert));
    },

    // ========================
    // MAP SYSTEM WITH NASA GIBS
    // ========================

    initializeMap(project) {
        const container = document.getElementById('monitoringMap');
        if (!container || typeof L === 'undefined') {
            console.error('Map container or Leaflet not found');
            return;
        }

        // Remove existing map
        if (this.state.map) {
            this.state.map.remove();
            this.state.map = null;
            this.state.currentOverlay = null;
        }

        // Create map centered on project with better default view
        this.state.map = L.map(container, {
            center: [project.latitude, project.longitude],
            zoom: 8, // Changed from 13 to 8 for better NASA GIBS tile visibility
            zoomControl: true,
            attributionControl: true,
            maxBounds: [[-90, -180], [90, 180]], // Prevent panning outside world
            worldCopyJump: true // Handle date line crossing
        });

        // Add zoom control with better positioning
        this.state.map.zoomControl.setPosition('topleft');

        // Add initial layer (satellite by default)
        this.addMapLayer('satellite');

        // Add project marker
        this.addProjectMarker(project);

        // Add scale control
        L.control.scale({ position: 'bottomleft', imperial: false }).addTo(this.state.map);

        // Add debug info in console
        console.log('🗺️ Map initialized:', {
            center: [project.latitude, project.longitude],
            zoom: this.state.map.getZoom(),
            bounds: this.state.map.getBounds()
        });

        // Update layer buttons
        this.updateLayerButtons('satellite');

        // Log NASA GIBS tile URLs for debugging
        const testUrl = this.layers.satellite.getUrl()
            .replace('{z}', '5')
            .replace('{y}', '10')
            .replace('{x}', '15');
        console.log('🛰️ Example NASA tile URL:', testUrl);

        console.log('✅ Map initialized with NASA GIBS layers');
    },

    addMapLayer(layerType) {
        if (!this.state.map) {
            console.warn('Map not initialized');
            return;
        }

        // Remove existing overlay
        if (this.state.currentOverlay) {
            this.state.map.removeLayer(this.state.currentOverlay);
            this.state.currentOverlay = null;
        }

        const layerConfig = this.layers[layerType];
        if (!layerConfig) {
            console.error('Unknown layer type:', layerType);
            return;
        }

        try {
            const tileUrl = layerConfig.getUrl();
            
            console.log(`🗺️ Loading ${layerType} layer from:`, tileUrl);
            
            const layerOptions = {
                attribution: layerConfig.attribution,
                maxZoom: layerConfig.maxZoom || 18,
                minZoom: layerConfig.minZoom || 1,
                opacity: layerConfig.opacity || 1,
                tileSize: layerConfig.tileSize || 256,
                crossOrigin: true,
                tms: layerConfig.tms || false,
                // NASA GIBS specific options
                bounds: [[-90, -180], [90, 180]]
            };

            // Add subdomains for OSM layers
            if (layerConfig.subdomains) {
                layerOptions.subdomains = layerConfig.subdomains;
            }

            const layer = L.tileLayer(tileUrl, layerOptions);

            // Enhanced error handling
            let tileLoadCount = 0;
            let tileErrorCount = 0;

            layer.on('tileerror', (error) => {
                tileErrorCount++;
                console.warn(`❌ Tile error for ${layerType} (${tileErrorCount} errors):`, error.coords);
                
                // If too many errors, show notification
                if (tileErrorCount === 5) {
                    this.showNotification(
                        `Some ${layerType} tiles failed to load. Imagery may be incomplete.`,
                        'warning'
                    );
                }
            });

            layer.on('tileload', () => {
                tileLoadCount++;
                if (tileLoadCount === 1) {
                    console.log(`✅ ${layerType} tiles loading successfully`);
                }
            });

            layer.on('load', () => {
                console.log(`✅ ${layerConfig.name} layer loaded successfully!`);
                this.showNotification(`${layerConfig.name} layer active`, 'success');
            });

            layer.addTo(this.state.map);
            this.state.currentOverlay = layer;
            this.state.currentLayer = layerType;

            // Update legend
            this.updateMapLegend(layerType);

            console.log(`✅ Added ${layerConfig.name} layer to map`);
        } catch (error) {
            console.error('Error adding map layer:', error);
            this.showNotification(`Failed to load ${layerType} layer`, 'error');
            
            // Fallback to OpenStreetMap
            if (layerType !== 'terrain') {
                console.log('Falling back to terrain layer...');
                this.addMapLayer('terrain');
            }
        }
    },

    switchLayer(layerType) {
        if (!this.state.map) {
            this.showNotification('Please select a project first', 'warning');
            return;
        }

        this.state.currentLayer = layerType;
        this.updateLayerButtons(layerType);
        this.addMapLayer(layerType);
        
        const layerName = this.layers[layerType]?.name || layerType;
        this.showNotification(`Switched to ${layerName}`, 'info');
    },

    updateLayerButtons(activeLayer) {
        document.querySelectorAll('.layer-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.layer === activeLayer);
        });
    },

addProjectMarker(project) {
    if (!this.state.map) return;

    // Clear existing markers
    this.state.markers.forEach(marker => this.state.map.removeLayer(marker));
    this.state.markers = [];

    const icon = L.divIcon({
        className: 'project-marker-custom',
        html: `
            <div style="
                background: linear-gradient(135deg, #10b981, #059669);
                width: 48px;
                height: 48px;
                border-radius: 50%;
                border: 4px solid white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 24px;
                animation: markerPulse 2s infinite;
            ">
                <i class="fas fa-seedling"></i>
            </div>
        `,
        iconSize: [48, 48],
        iconAnchor: [24, 24],
        popupAnchor: [0, -24]
    });

    // Get NDVI value and class
    const ndviValue = project.vegetation_index || project.ndvi || 0;
    const ndvi = parseFloat(ndviValue);
    let ndviClass = 'ndvi-critical';
    if (ndvi >= 0.6) ndviClass = 'ndvi-healthy';
    else if (ndvi >= 0.4) ndviClass = 'ndvi-moderate';
    else if (ndvi >= 0.2) ndviClass = 'ndvi-low';

    // Get status
    const status = project.status || 'planning';
    const statusClass = `status-${status}`;
    
    // Format project type
    const projectType = project.project_type || project.type || 'N/A';
    const areaHectares = parseFloat(project.area_hectares || project.area || 0).toFixed(1);

    const popupContent = `
        <div class="popup-card">
            <div class="popup-header">
                <h3 class="popup-project-name">
                    <i class="fas fa-map-marker-alt"></i>
                    ${this.escapeHtml(project.name)}
                </h3>
            </div>
            <div class="popup-body">
                <div class="popup-info-grid">
                    <div class="popup-info-item">
                        <span class="popup-info-label">
                            <i class="fas fa-ruler-combined"></i>
                            Area:
                        </span>
                        <strong class="popup-info-value">${areaHectares} ha</strong>
                    </div>
                    <div class="popup-info-item">
                        <span class="popup-info-label">
                            <i class="fas fa-tag"></i>
                            Type:
                        </span>
                        <strong class="popup-info-value">${this.escapeHtml(projectType)}</strong>
                    </div>
                    <div class="popup-info-item">
                        <span class="popup-info-label">
                            <i class="fas fa-info-circle"></i>
                            Status:
                        </span>
                        <span class="popup-status-badge ${statusClass}">
                            <i class="fas fa-circle"></i>
                            ${this.escapeHtml(status)}
                        </span>
                    </div>
                    <div class="popup-info-item">
                        <span class="popup-info-label">
                            <i class="fas fa-leaf"></i>
                            NDVI:
                        </span>
                        <strong class="popup-info-value ndvi-value ${ndviClass}">
                            ${ndvi.toFixed(2)}
                        </strong>
                    </div>
                </div>
            </div>
        </div>
    `;

    const marker = L.marker([project.latitude, project.longitude], { icon })
        .bindPopup(popupContent, {
            maxWidth: 320,
            minWidth: 280,
            className: 'custom-popup',
            closeButton: true,
            autoClose: false,
            closeOnClick: false
        })
        .addTo(this.state.map);

    this.state.markers.push(marker);
    
    // Open popup after a small delay to ensure proper rendering
    setTimeout(() => {
        marker.openPopup();
    }, 100);
    
    console.log('✅ Marker added with popup:', project.name);
},
    updateMapLegend(layerType) {
        const legend = document.getElementById('mapLegend');
        if (!legend) return;

        const legends = {
            satellite: `
                <div class="legend-content">
                    <div class="legend-title">🛰️ True Color Satellite</div>
                    <p style="font-size: 0.85em; color: #6b7280; margin: 0;">
                        NASA VIIRS daily imagery showing actual vegetation colors
                    </p>
                </div>
            `,
            ndvi: `
                <div class="legend-content">
                    <div class="legend-title">🌿 NDVI - Vegetation Index</div>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background: #d73027;"></span>
                            <span>&lt; 0.2 - Bare soil / No vegetation</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: #fee08b;"></span>
                            <span>0.2 - 0.4 - Sparse vegetation</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: #d9ef8b;"></span>
                            <span>0.4 - 0.6 - Moderate vegetation</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: #1a9850;"></span>
                            <span>&gt; 0.6 - Dense healthy vegetation</span>
                        </div>
                    </div>
                </div>
            `,
            soil: `
                <div class="legend-content">
                    <div class="legend-title">💧 Soil Moisture</div>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background: #8b4513;"></span>
                            <span>Very Dry (&lt; 10%)</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: #d2691e;"></span>
                            <span>Dry (10-30%)</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: #90ee90;"></span>
                            <span>Optimal (30-60%)</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: #4169e1;"></span>
                            <span>Wet (&gt; 60%)</span>
                        </div>
                    </div>
                    <p style="font-size: 0.8em; color: #6b7280; margin-top: 8px;">
                        NASA SMAP root zone moisture data
                    </p>
                </div>
            `,
            terrain: `
                <div class="legend-content">
                    <div class="legend-title">🏔️ Terrain</div>
                    <p style="font-size: 0.85em; color: #6b7280; margin: 0;">
                        Topographic map showing elevation and land features
                    </p>
                </div>
            `
        };

        legend.innerHTML = legends[layerType] || '';
        legend.style.display = legends[layerType] ? 'block' : 'none';
    },

    // ========================
    // ALERTS SYSTEM WITH NOTIFICATIONS
    // ========================

    async loadAlerts(projectId) {
        try {
            const response = await fetch(`/monitoring/api/alerts/${projectId}`);
            const data = await response.json();

            if (data.success) {
                this.state.alerts = data.alerts || [];
                this.renderAlerts();
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.renderEmptyAlerts();
        }
    },

    addAlert(alert) {
        // Add to state
        this.state.alerts.unshift(alert);
        
        // Render alerts
        this.renderAlerts();
        
        // Send notification
        if (window.NotificationSystem) {
            const typeMap = {
                'warning': 'warning',
                'error': 'error',
                'info': 'info',
                'critical': 'error'
            };
            
            NotificationSystem.showLiveNotification(
                alert.title,
                alert.message,
                typeMap[alert.type] || 'info',
                6000
            );
        }
    },

    renderAlerts() {
        const container = document.getElementById('alertsList');
        const badge = document.getElementById('alertCount');

        if (!container) return;

        if (badge) {
            badge.textContent = this.state.alerts.length;
        }

        if (this.state.alerts.length === 0) {
            this.renderEmptyAlerts();
            return;
        }

        container.innerHTML = this.state.alerts.map(alert => `
            <div class="alert-item alert-${alert.type || 'info'}">
                <div class="alert-icon">
                    <i class="fas fa-${alert.icon || 'info-circle'}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-title">${this.escapeHtml(alert.title)}</div>
                    <div class="alert-message">${this.escapeHtml(alert.message)}</div>
                    ${alert.timestamp ? `<div class="alert-time">${this.formatTimeAgo(alert.timestamp)}</div>` : ''}
                </div>
            </div>
        `).join('');
    },

    renderEmptyAlerts() {
        const container = document.getElementById('alertsList');
        if (!container) return;

        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-check-circle" style="color: #10b981;"></i>
                <h3>All Clear!</h3>
                <p>No active alerts - all systems normal</p>
            </div>
        `;
    },

    // ========================
    // AI RECOMMENDATIONS
    // ========================

    async loadAIRecommendations(projectId) {
        try {
            const response = await fetch(`/monitoring/api/ai-recommendations/${projectId}`);
            const data = await response.json();

            if (data.success) {
                this.state.aiRecommendations = data.recommendations || [];
                this.renderAIRecommendations();
            }
        } catch (error) {
            console.error('Error loading AI recommendations:', error);
            this.renderEmptyAI();
        }
    },

    renderAIRecommendations() {
        const container = document.getElementById('aiRecommendations');
        if (!container) return;

        if (this.state.aiRecommendations.length === 0) {
            this.renderEmptyAI();
            return;
        }

        container.innerHTML = this.state.aiRecommendations.map(rec => `
            <div class="ai-recommendation">
                <div class="ai-recommendation-header">
                    <div class="ai-icon">
                        <i class="fas fa-brain"></i>
                    </div>
                    <div class="ai-title">${this.escapeHtml(rec.title)}</div>
                </div>
                <div class="ai-text">${this.escapeHtml(rec.description)}</div>
                ${rec.actions && rec.actions.length > 0 ? `
                    <div class="ai-actions">
                        ${rec.actions.map(action => `
                            <div class="action-item">
                                <i class="fas fa-check-circle"></i>
                                <span>${this.escapeHtml(action)}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                <div class="ai-confidence">
                    <span>Priority: <strong>${rec.priority || 'medium'}</strong></span>
                </div>
            </div>
        `).join('');
    },

    renderEmptyAI() {
        const container = document.getElementById('aiRecommendations');
        if (!container) return;

        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-brain"></i>
                <h3>AI Analysis</h3>
                <p>No recommendations at this time</p>
            </div>
        `;
    },

    // ========================
    // RECOMMENDED PLANTS
    // ========================

    async loadRecommendedPlants(projectId) {
        try {
            const response = await fetch(`/monitoring/api/recommended-plants/${projectId}`);
            const data = await response.json();

            if (data.success) {
                this.renderRecommendedPlants(data.plants || []);
            }
        } catch (error) {
            console.error('Error loading plants:', error);
        }
    },

    renderRecommendedPlants(plants) {
        const container = document.getElementById('recommendedPlants');
        if (!container) return;

        if (plants.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-seedling"></i>
                    <p>No plant recommendations</p>
                </div>
            `;
            return;
        }

        container.innerHTML = plants.map(plant => `
            <div class="plant-item">
                <div class="plant-item-header">
                    <div class="plant-icon">🌱</div>
                    <div class="plant-name">${this.escapeHtml(plant.name)}</div>
                </div>
                <div class="plant-details">
                    <div class="plant-suitability">
                        <div class="suitability-bar">
                            <div class="suitability-fill" style="width: ${plant.suitability || 0}%"></div>
                        </div>
                        <span class="suitability-text">${plant.suitability || 0}% match</span>
                    </div>
                </div>
            </div>
        `).join('');
    },

    // ========================
    // SUITABLE PRODUCTS
    // ========================

    async loadSuitableProducts(projectId) {
        try {
            const response = await fetch(`/monitoring/api/suitable-products/${projectId}`);
            const data = await response.json();

            if (data.success) {
                this.renderSuitableProducts(data.products || []);
            }
        } catch (error) {
            console.error('Error loading products:', error);
        }
    },

    renderSuitableProducts(products) {
        const container = document.getElementById('suitableProducts');
        if (!container) return;

        if (products.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box"></i>
                    <p>No product recommendations</p>
                </div>
            `;
            return;
        }

        container.innerHTML = products.map(product => `
            <div class="product-item">
                <div class="product-item-header">
                    <div class="product-icon">📦</div>
                    <div class="product-name">${this.escapeHtml(product.name)}</div>
                </div>
                <div class="product-details">
                    <span class="product-category">${this.escapeHtml(product.category || 'General')}</span>
                    ${product.description ? `<p>${this.escapeHtml(product.description)}</p>` : ''}
                </div>
            </div>
        `).join('');
    },

    // ========================
    // CHARTS
    // ========================

    initializeCharts() {
        this.initNDVIChart();
        this.initLandCoverChart();
    },

    initNDVIChart() {
        const ctx = document.getElementById('ndviChart');
        if (!ctx) return;

        this.state.charts.ndvi = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'NDVI Trend',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        callbacks: {
                            label: function(context) {
                                return `NDVI: ${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(1);
                            }
                        }
                    }
                }
            }
        });
    },

    initLandCoverChart() {
        const ctx = document.getElementById('landCoverChart');
        if (!ctx) return;

        this.state.charts.landCover = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Forest', 'Grassland', 'Bare Soil', 'Water', 'Agriculture'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        '#10b981',
                        '#84cc16',
                        '#f59e0b',
                        '#3b82f6',
                        '#8b5cf6'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    },

    async updateCharts(projectId) {
        try {
            const response = await fetch(`/monitoring/api/chart-data/${projectId}?period=30`);
            const data = await response.json();

            if (data.success) {
                // Update NDVI chart
                if (this.state.charts.ndvi && data.ndvi_data) {
                    this.state.charts.ndvi.data.labels = data.ndvi_data.labels;
                    this.state.charts.ndvi.data.datasets[0].data = data.ndvi_data.values;
                    this.state.charts.ndvi.update('active');
                }

                // Update land cover chart
                if (this.state.charts.landCover && data.land_cover) {
                    this.state.charts.landCover.data.datasets[0].data = data.land_cover.values;
                    this.state.charts.landCover.update('active');
                }
            }
        } catch (error) {
            console.error('Error updating charts:', error);
        }
    },

    async updateChartPeriod(days) {
        if (!this.state.selectedProject) return;

        try {
            const response = await fetch(
                `/monitoring/api/chart-data/${this.state.selectedProject.id}?period=${days}`
            );
            const data = await response.json();

            if (data.success && this.state.charts.ndvi) {
                this.state.charts.ndvi.data.labels = data.ndvi_data.labels;
                this.state.charts.ndvi.data.datasets[0].data = data.ndvi_data.values;
                this.state.charts.ndvi.update('active');
            }
        } catch (error) {
            console.error('Error updating chart period:', error);
        }
    },

    // ========================
    // DATA REFRESH
    // ========================

    async refreshData() {
        if (!this.state.selectedProject) {
            this.showNotification('Please select a project first', 'warning');
            return;
        }

        this.showNotification('Refreshing data...', 'info');

        try {
            await Promise.all([
                this.loadProjectMetrics(this.state.selectedProject.id),
                this.loadWeatherData(
                    this.state.selectedProject.latitude,
                    this.state.selectedProject.longitude
                ),
                this.loadAlerts(this.state.selectedProject.id),
                this.updateCharts(this.state.selectedProject.id)
            ]);

            this.showNotification('Data refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Failed to refresh data', 'error');
        }
    },

    // ========================
    // NOTIFICATION HELPER
    // ========================

    showNotification(message, type = 'info') {
        if (window.NotificationSystem) {
            NotificationSystem.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    },

    // ========================
    // UTILITY FUNCTIONS
    // ========================

    getNDVIColor(ndvi) {
        const value = parseFloat(ndvi);
        if (value < 0.2) return '#d73027';
        if (value < 0.4) return '#fee08b';
        if (value < 0.6) return '#d9ef8b';
        return '#1a9850';
    },

    getHealthColor(score) {
        if (score >= 80) return '#10b981';
        if (score >= 60) return '#84cc16';
        if (score >= 40) return '#f59e0b';
        return '#ef4444';
    },

    formatTimeAgo(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric'
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

    // ========================
    // CLEANUP
    // ========================

    destroy() {
        if (this.state.refreshInterval) {
            clearInterval(this.state.refreshInterval);
        }
        if (this.state.weatherInterval) {
            clearInterval(this.state.weatherInterval);
        }
        if (this.state.map) {
            this.state.map.remove();
        }
        Object.values(this.state.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        
        console.log('🗑️ Monitoring System destroyed');
    }
};

// ========================
// GLOBAL FUNCTIONS
// ========================

window.toggleMapView = function() {
    const mapSection = document.getElementById('mapSection');
    const btn = event.target.closest('button');
    
    if (!mapSection) return;
    
    mapSection.classList.toggle('collapsed');
    
    if (mapSection.classList.contains('collapsed')) {
        if (btn) btn.innerHTML = '<i class="fas fa-map"></i> Show Map';
    } else {
        if (btn) btn.innerHTML = '<i class="fas fa-map"></i> Hide Map';
        
        if (!MonitoringSystem.state.map && MonitoringSystem.state.selectedProject) {
            setTimeout(() => {
                MonitoringSystem.initializeMap(MonitoringSystem.state.selectedProject);
            }, 300);
        } else if (MonitoringSystem.state.map) {
            MonitoringSystem.state.map.invalidateSize();
        }
    }
};

window.downloadMapData = function() {
    if (!MonitoringSystem.state.selectedProject) {
        MonitoringSystem.showNotification('Please select a project first', 'warning');
        return;
    }

    MonitoringSystem.showNotification('Preparing download...', 'info');

    const exportData = {
        project: {
            id: MonitoringSystem.state.selectedProject.id,
            name: MonitoringSystem.state.selectedProject.name,
            location: MonitoringSystem.state.selectedProject.location
        },
        weather: MonitoringSystem.state.weatherData,
        forecast: MonitoringSystem.state.forecastData,
        alerts: MonitoringSystem.state.alerts,
        recommendations: MonitoringSystem.state.aiRecommendations,
        exported_at: new Date().toISOString()
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `monitoring-${MonitoringSystem.state.selectedProject.name}-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    MonitoringSystem.showNotification('Data downloaded successfully', 'success');
};

window.toggleFullscreenMap = function() {
    const mapSection = document.getElementById('mapSection');
    if (!mapSection) return;

    if (!document.fullscreenElement) {
        mapSection.requestFullscreen().catch(err => {
            console.error('Error enabling fullscreen:', err);
        });
    } else {
        document.exitFullscreen();
    }

    setTimeout(() => {
        if (MonitoringSystem.state.map) {
            MonitoringSystem.state.map.invalidateSize();
        }
    }, 100);
};

window.refreshAI = async function() {
    if (!MonitoringSystem.state.selectedProject) {
        MonitoringSystem.showNotification('Please select a project first', 'warning');
        return;
    }

    const btn = event.target.closest('button');
    const originalHTML = btn ? btn.innerHTML : '';
    
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    try {
        await MonitoringSystem.loadAIRecommendations(MonitoringSystem.state.selectedProject.id);
        MonitoringSystem.showNotification('AI recommendations refreshed', 'success');
    } catch (error) {
        MonitoringSystem.showNotification('Failed to refresh recommendations', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    }
};

window.closeZoneModal = function() {
    const modal = document.getElementById('zoneModal');
    if (modal) {
        modal.classList.remove('show');
    }
};

// ========================
// AUTO-INITIALIZE
// ========================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 RegenArdhi Monitoring - Initializing...');
    
    const initMonitoring = () => {
        if (window.NotificationSystem && window.L && window.Chart) {
            MonitoringSystem.init();
        } else {
            console.log('Waiting for dependencies...');
            setTimeout(initMonitoring, 100);
        }
    };
    
    initMonitoring();
});

// Handle visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && MonitoringSystem.state.selectedProject) {
        MonitoringSystem.refreshData();
    }
});

// Cleanup on unload
window.addEventListener('beforeunload', () => {
    MonitoringSystem.destroy();
});

// ========================
// EXPORT
// ========================

window.MonitoringSystem = MonitoringSystem;

// ========================
// CUSTOM STYLES
// ========================

const customStyles = document.createElement('style');
customStyles.textContent = `
    @keyframes markerPulse {
        0%, 100% {
            transform: scale(1);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        50% {
            transform: scale(1.05);
            box-shadow: 0 8px 20px rgba(16,185,129,0.5);
        }
    }

    .custom-popup .leaflet-popup-content-wrapper {
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }

    .legend-content {
        padding: 0;
    }

    .legend-title {
        font-weight: 700;
        font-size: 0.95em;
        margin-bottom: 12px;
        color: #111827;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .legend-items {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85em;
        color: #374151;
    }

    .legend-color {
        width: 24px;
        height: 14px;
        border-radius: 3px;
        display: block;
        border: 1px solid rgba(0,0,0,0.1);
    }

    .action-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 8px 0;
        font-size: 0.9em;
        line-height: 1.5;
    }

    .action-item i {
        color: #10b981;
        margin-top: 2px;
        flex-shrink: 0;
    }

    .suitability-bar {
        flex: 1;
        height: 8px;
        background: #e5e7eb;
        border-radius: 4px;
        overflow: hidden;
    }

    .suitability-fill {
        height: 100%;
        background: linear-gradient(90deg, #10b981, #059669);
        transition: width 0.6s ease;
    }

    .suitability-text {
        font-size: 0.85em;
        color: #6b7280;
        white-space: nowrap;
    }
`;
document.head.appendChild(customStyles);

console.log('✅ Enhanced Monitoring System v3.0 Loaded!');
console.log('🛰️ NASA GIBS integration active');
console.log('🌦️ OpenWeather forecasting enabled');
console.log('🔔 Notification system integrated');
console.log('🔒 All API keys secured via backend proxy')


