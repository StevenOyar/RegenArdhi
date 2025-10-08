import os
import requests
import json
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

load_dotenv()

# Create Blueprint
projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

# MySQL connection (passed from main app)
mysql = None

# API Keys
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', 'your_key_here')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', 'your_key_here')
NASA_EARTH_API_KEY = os.getenv('NASA_EARTH_API_KEY', 'DEMO_KEY')

# ========================
# REAL API INTEGRATION
# ========================

def get_location_name(latitude, longitude):
    """Get location name using reverse geocoding with OpenStreetMap Nominatim"""
    try:
        # Using free Nominatim service (respecting usage policy)
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': 10
        }
        headers = {
            'User-Agent': 'RegenArdhi/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            # Build location string
            parts = []
            if address.get('town') or address.get('city'):
                parts.append(address.get('town') or address.get('city'))
            if address.get('county'):
                parts.append(address.get('county'))
            if address.get('state'):
                parts.append(address.get('state'))
            if address.get('country'):
                parts.append(address.get('country'))
            
            if parts:
                return ', '.join(parts)
        
        # Fallback to coordinates
        return f"{latitude:.4f}, {longitude:.4f}"
        
    except Exception as e:
        print(f"Error getting location name: {e}")
        return f"{latitude:.4f}, {longitude:.4f}"

def get_real_climate_data(latitude, longitude):
    """Fetch REAL climate data from OpenWeather API"""
    try:
        if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == 'your_key_here':
            print("⚠️ OpenWeather API key not configured, using fallback")
            return get_fallback_climate_data(latitude, longitude)
        
        # Current weather API
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            return {
                'temperature': round(data['main']['temp'], 1),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'wind_speed': data.get('wind', {}).get('speed', 0)
            }
        else:
            print(f"OpenWeather API error: {response.status_code}")
            return get_fallback_climate_data(latitude, longitude)
            
    except Exception as e:
        print(f"Error fetching climate data: {e}")
        return get_fallback_climate_data(latitude, longitude)

def get_fallback_climate_data(latitude, longitude):
    """Fallback climate estimation based on coordinates"""
    # Basic climate estimation
    abs_lat = abs(latitude)
    
    # Temperature estimation (decreases with latitude)
    base_temp = 30 - (abs_lat * 0.6)
    
    # Humidity estimation
    if abs_lat < 23.5:  # Tropics
        humidity = 70 + (abs(longitude) % 20)
    else:
        humidity = 50 + (abs(longitude) % 30)
    
    return {
        'temperature': round(base_temp, 1),
        'humidity': int(humidity),
        'pressure': 1013,
        'description': 'estimated',
        'wind_speed': 0
    }

def get_elevation_data(latitude, longitude):
    """Get elevation data from Open-Elevation API (free)"""
    try:
        url = "https://api.open-elevation.com/api/v1/lookup"
        params = {
            'locations': f"{latitude},{longitude}"
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                elevation = data['results'][0].get('elevation', 0)
                return elevation
        
        return 0
        
    except Exception as e:
        print(f"Error getting elevation: {e}")
        return 0

def calculate_ndvi_estimate(latitude, longitude, climate_data):
    """
    Estimate NDVI based on location and climate
    In production, this would use Sentinel Hub or similar satellite API
    """
    try:
        abs_lat = abs(latitude)
        temp = climate_data.get('temperature', 20)
        humidity = climate_data.get('humidity', 50)
        
        # Base NDVI calculation
        # Higher in tropics, lower in arid/polar regions
        if abs_lat < 10:  # Equatorial
            base_ndvi = 0.6
        elif abs_lat < 23.5:  # Tropics
            base_ndvi = 0.5
        elif abs_lat < 35:  # Subtropics
            base_ndvi = 0.4
        elif abs_lat < 50:  # Temperate
            base_ndvi = 0.35
        else:  # Polar
            base_ndvi = 0.2
        
        # Adjust for temperature and humidity
        if temp > 25 and humidity > 60:
            base_ndvi += 0.1
        elif temp < 10 or humidity < 30:
            base_ndvi -= 0.15
        
        # Add some variation
        variation = (abs(longitude) % 10) * 0.02
        ndvi = max(0.0, min(1.0, base_ndvi + variation - 0.1))
        
        return round(ndvi, 2)
        
    except Exception as e:
        print(f"Error calculating NDVI: {e}")
        return 0.4

def analyze_soil_type(latitude, longitude, elevation):
    """
    Estimate soil type based on geography
    In production, use FAO soil database or similar
    """
    abs_lat = abs(latitude)
    
    # Elevation-based classification
    if elevation > 2000:
        soil_types = ["Rocky", "Mountain Soil", "Thin Soil"]
    elif elevation > 1000:
        soil_types = ["Loamy", "Clay-Loam", "Sandy-Loam"]
    else:
        # Latitude-based
        if abs_lat < 10:
            soil_types = ["Laterite", "Tropical Red", "Alluvial"]
        elif abs_lat < 30:
            soil_types = ["Alluvial", "Loamy", "Red Soil"]
        elif abs_lat < 50:
            soil_types = ["Loamy", "Clay", "Podzol"]
        else:
            soil_types = ["Tundra", "Permafrost", "Gleysol"]
    
    # Select based on longitude for variation
    index = int(abs(longitude)) % len(soil_types)
    return soil_types[index]

def calculate_soil_ph(soil_type, climate_data):
    """Estimate soil pH based on soil type and climate"""
    base_ph = {
        "Laterite": 5.5,
        "Tropical Red": 6.0,
        "Alluvial": 7.0,
        "Loamy": 6.5,
        "Clay": 7.2,
        "Sandy": 6.8,
        "Rocky": 7.5,
        "Mountain Soil": 6.3,
        "Podzol": 5.0,
        "Tundra": 5.5,
    }
    
    # Get base pH
    ph = base_ph.get(soil_type, 6.5)
    
    # Adjust for rainfall (estimated from humidity)
    humidity = climate_data.get('humidity', 50)
    if humidity > 70:  # High rainfall areas
        ph -= 0.3  # More acidic
    elif humidity < 40:  # Arid areas
        ph += 0.3  # More alkaline
    
    return round(ph, 1)

def determine_climate_zone(latitude, temperature):
    """Determine climate zone classification"""
    abs_lat = abs(latitude)
    
    if abs_lat > 66.5:
        return "Polar"
    elif abs_lat > 60:
        return "Subpolar"
    elif abs_lat > 45:
        if temperature > 20:
            return "Warm Temperate"
        else:
            return "Cool Temperate"
    elif abs_lat > 30:
        if temperature > 25:
            return "Subtropical"
        else:
            return "Warm Temperate"
    elif abs_lat > 23.5:
        return "Tropical"
    else:
        return "Equatorial"

def estimate_annual_rainfall(climate_zone, humidity, longitude):
    """Estimate annual rainfall in mm"""
    base_rainfall = {
        "Equatorial": 2500,
        "Tropical": 1800,
        "Subtropical": 1000,
        "Warm Temperate": 800,
        "Cool Temperate": 700,
        "Subpolar": 500,
        "Polar": 250
    }
    
    rainfall = base_rainfall.get(climate_zone, 800)
    
    # Adjust for humidity
    if humidity > 70:
        rainfall *= 1.3
    elif humidity < 40:
        rainfall *= 0.6
    
    # Add coastal/continental variation based on longitude
    variation = (abs(longitude) % 15) * 20
    rainfall += variation
    
    return int(rainfall)

def assess_land_degradation(ndvi, soil_ph, area_hectares):
    """Assess land degradation level"""
    # NDVI thresholds
    if ndvi < 0.2:
        score = 4  # Critical
    elif ndvi < 0.35:
        score = 3  # Severe
    elif ndvi < 0.5:
        score = 2  # Moderate
    else:
        score = 1  # Minimal
    
    # pH problems
    if soil_ph < 5.0 or soil_ph > 8.5:
        score += 1
    
    # Large areas often have more degradation
    if area_hectares > 100:
        score += 1
    
    # Final classification
    if score >= 5:
        return "critical"
    elif score >= 4:
        return "severe"
    elif score >= 2:
        return "moderate"
    else:
        return "minimal"

def generate_recommendations(climate_zone, soil_type, soil_ph, degradation_level, annual_rainfall):
    """Generate crop, tree, and technique recommendations"""
    
    # Crop recommendations by climate zone
    crops_db = {
        "Equatorial": ["Rice", "Bananas", "Cassava", "Yams", "Cocoa", "Coffee"],
        "Tropical": ["Maize", "Beans", "Cassava", "Sweet Potato", "Millet", "Sorghum"],
        "Subtropical": ["Wheat", "Maize", "Citrus", "Grapes", "Cotton", "Rice"],
        "Warm Temperate": ["Wheat", "Barley", "Potato", "Apple", "Cherry", "Corn"],
        "Cool Temperate": ["Oats", "Barley", "Potato", "Cabbage", "Berries", "Rye"],
        "Subpolar": ["Barley", "Potato", "Root Vegetables", "Hardy Grasses"],
        "Polar": ["Hardy Grasses", "Moss"]
    }
    
    # Tree recommendations
    trees_db = {
        "Equatorial": ["Mahogany", "Teak", "Rubber", "Oil Palm", "Bamboo"],
        "Tropical": ["Acacia", "Neem", "Mango", "Moringa", "Grevillea", "Eucalyptus"],
        "Subtropical": ["Oak", "Citrus", "Olive", "Pine", "Cypress"],
        "Warm Temperate": ["Oak", "Maple", "Ash", "Pine", "Walnut"],
        "Cool Temperate": ["Spruce", "Fir", "Birch", "Alder", "Larch"],
        "Subpolar": ["Birch", "Willow", "Alder", "Hardy Conifers"],
        "Polar": ["Dwarf Willow", "Arctic Birch"]
    }
    
    # Adjust for pH
    if soil_ph < 5.5:
        # Add acid-tolerant species
        crops_db[climate_zone] = [c for c in crops_db[climate_zone] if c not in ["Wheat", "Barley"]]
        crops_db[climate_zone].extend(["Blueberries", "Cranberries"])
    elif soil_ph > 7.5:
        # Add alkaline-tolerant species
        if "Olive" not in trees_db[climate_zone]:
            trees_db[climate_zone].append("Date Palm")
    
    # Restoration techniques by degradation level
    techniques_db = {
        "minimal": [
            "Regular mulching and organic matter addition",
            "Crop rotation practices",
            "Water conservation techniques",
            "Integrated pest management"
        ],
        "moderate": [
            "Contour farming and terracing",
            "Agroforestry integration",
            "Soil amendment with compost",
            "Cover cropping",
            "Erosion control structures"
        ],
        "severe": [
            "Intensive afforestation program",
            "Deep tillage and soil loosening",
            "Gabion and stone wall construction",
            "Watershed management systems",
            "Biochar application",
            "Pioneer species planting"
        ],
        "critical": [
            "Emergency restoration protocols",
            "Comprehensive soil remediation",
            "Mechanical intervention (ripping, subsoiling)",
            "Intensive irrigation system installation",
            "Rock dam and check dam construction",
            "Fast-growing pioneer species",
            "Professional consultation required"
        ]
    }
    
    # Timeline estimation (months)
    timeline_map = {
        "minimal": 12,
        "moderate": 24,
        "severe": 36,
        "critical": 48
    }
    
    # Budget estimation (KES per hectare)
    base_budget_per_ha = {
        "minimal": 50000,
        "moderate": 150000,
        "severe": 350000,
        "critical": 700000
    }
    
    budget = base_budget_per_ha.get(degradation_level, 100000)
    
    # Adjust for rainfall (irrigation needs)
    if annual_rainfall < 600:
        budget *= 1.5
    
    return {
        'crops': crops_db.get(climate_zone, ["Consult local agronomist"]),
        'trees': trees_db.get(climate_zone, ["Consult local forester"]),
        'techniques': techniques_db.get(degradation_level, []),
        'timeline_months': timeline_map.get(degradation_level, 24),
        'budget_per_hectare': round(budget, 2)
    }

def comprehensive_land_analysis(latitude, longitude, area_hectares):
    """
    Perform comprehensive land analysis using real and estimated data
    """
    try:
        print(f"🔍 Analyzing location: {latitude}, {longitude}")
        
        # Step 1: Get real climate data
        climate_data = get_real_climate_data(latitude, longitude)
        print(f"✓ Climate data: {climate_data['temperature']}°C, {climate_data['humidity']}% humidity")
        
        # Step 2: Get elevation
        elevation = get_elevation_data(latitude, longitude)
        print(f"✓ Elevation: {elevation}m")
        
        # Step 3: Determine climate zone
        climate_zone = determine_climate_zone(latitude, climate_data['temperature'])
        print(f"✓ Climate zone: {climate_zone}")
        
        # Step 4: Estimate annual rainfall
        annual_rainfall = estimate_annual_rainfall(
            climate_zone, 
            climate_data['humidity'],
            longitude
        )
        print(f"✓ Annual rainfall estimate: {annual_rainfall}mm")
        
        # Step 5: Analyze soil
        soil_type = analyze_soil_type(latitude, longitude, elevation)
        soil_ph = calculate_soil_ph(soil_type, climate_data)
        print(f"✓ Soil: {soil_type}, pH {soil_ph}")
        
        # Step 6: Calculate NDVI
        ndvi = calculate_ndvi_estimate(latitude, longitude, climate_data)
        print(f"✓ NDVI estimate: {ndvi}")
        
        # Step 7: Assess degradation
        degradation_level = assess_land_degradation(ndvi, soil_ph, area_hectares)
        print(f"✓ Degradation level: {degradation_level}")
        
        # Step 8: Determine soil fertility
        if 6.0 <= soil_ph <= 7.5 and ndvi > 0.5:
            soil_fertility = "high"
        elif (5.5 <= soil_ph < 6.0 or 7.5 < soil_ph <= 8.0) and ndvi > 0.35:
            soil_fertility = "medium"
        else:
            soil_fertility = "low"
        
        # Step 9: Generate recommendations
        recommendations = generate_recommendations(
            climate_zone,
            soil_type,
            soil_ph,
            degradation_level,
            annual_rainfall
        )
        
        # Step 10: Calculate total budget
        total_budget = recommendations['budget_per_hectare'] * area_hectares
        
        # Compile final analysis
        analysis = {
            'soil_type': soil_type,
            'soil_ph': soil_ph,
            'soil_fertility': soil_fertility,
            'climate_zone': climate_zone,
            'annual_rainfall': annual_rainfall,
            'temperature': climate_data['temperature'],
            'humidity': climate_data['humidity'],
            'elevation': elevation,
            'vegetation_index': ndvi,
            'land_degradation_level': degradation_level,
            'recommended_crops': recommendations['crops'][:5],  # Top 5
            'recommended_trees': recommendations['trees'][:5],  # Top 5
            'restoration_techniques': recommendations['techniques'],
            'estimated_timeline_months': recommendations['timeline_months'],
            'estimated_budget': total_budget,
            'satellite_image_url': None  # Would use Sentinel Hub in production
        }
        
        print(f"✅ Analysis complete!")
        return analysis
        
    except Exception as e:
        print(f"❌ Error in comprehensive analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========================
# DATABASE INITIALIZATION
# ========================

def init_projects(app, mysql_instance):
    """Initialize projects module with Flask app and MySQL instance"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            
            # Create projects table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    project_type ENUM('reforestation', 'soil-conservation', 'watershed', 'agroforestry') NOT NULL,
                    area_hectares DECIMAL(10, 2) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    latitude DECIMAL(10, 8) NOT NULL,
                    longitude DECIMAL(11, 8) NOT NULL,
                    
                    -- AI Analysis Data
                    soil_type VARCHAR(100),
                    soil_ph DECIMAL(3, 1),
                    soil_fertility VARCHAR(100),
                    climate_zone VARCHAR(100),
                    annual_rainfall INT,
                    temperature DECIMAL(5, 2),
                    humidity INT,
                    elevation INT,
                    vegetation_index DECIMAL(4, 2),
                    land_degradation_level ENUM('minimal', 'moderate', 'severe', 'critical'),
                    
                    -- AI Recommendations
                    recommended_crops JSON,
                    recommended_trees JSON,
                    restoration_techniques JSON,
                    estimated_timeline_months INT,
                    estimated_budget DECIMAL(12, 2),
                    
                    -- Project Progress
                    status ENUM('planning', 'active', 'completed', 'paused') DEFAULT 'planning',
                    progress_percentage INT DEFAULT 0,
                    start_date DATE,
                    end_date DATE,
                    
                    -- Tracking
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_ai_analysis TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_status (status),
                    INDEX idx_coordinates (latitude, longitude)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Check if elevation column exists, if not add it
            cur.execute('''
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'projects' 
                AND COLUMN_NAME = 'elevation'
            ''')
            
            if cur.fetchone()[0] == 0:
                print("⚠️ Adding 'elevation' column to projects table...")
                cur.execute('''
                    ALTER TABLE projects 
                    ADD COLUMN elevation INT DEFAULT 0 AFTER humidity
                ''')
                print("✅ 'elevation' column added successfully!")
            
            mysql.connection.commit()
            cur.close()
            print("✅ Projects tables initialized successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing projects tables: {e}")
            import traceback
            traceback.print_exc()

# ========================
# API ROUTES
# ========================

@projects_bp.route('/api/list')
def api_list_projects():
    """API endpoint to list all user projects"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        # Use DictCursor to get results as dictionaries
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        user_id = session.get('user_id')
        
        print(f"📊 Fetching projects for user_id: {user_id}")
        
        cur.execute('''
            SELECT * FROM projects
            WHERE user_id = %s
            ORDER BY created_at DESC
        ''', (user_id,))
        
        projects = cur.fetchall()  # Already returns list of dicts with DictCursor
        
        print(f"🔍 Raw projects from DB: {len(projects)} found")
        
        # Process each project
        processed_projects = []
        for project in projects:
            print(f"🔍 Processing project: {project.get('name', 'Unknown')}")
            print(f"   - ID: {project.get('id')}")
            print(f"   - Type: {project.get('project_type')}")
            print(f"   - Status: {project.get('status')}")
            print(f"   - Climate: {project.get('climate_zone')}")
            print(f"   - Soil: {project.get('soil_type')}")
            print(f"   - Degradation: {project.get('land_degradation_level')}")
            print(f"   - NDVI: {project.get('vegetation_index')}")
            
            # Parse JSON fields safely
            json_fields = ['recommended_crops', 'recommended_trees', 'restoration_techniques']
            for field in json_fields:
                if project.get(field):
                    try:
                        if isinstance(project[field], str):
                            project[field] = json.loads(project[field])
                        # If already a list/dict, keep as is
                    except Exception as e:
                        print(f"   ⚠️ Error parsing {field}: {e}")
                        project[field] = []
                else:
                    project[field] = []
            
            # Convert dates to strings
            date_fields = ['start_date', 'end_date', 'created_at', 'updated_at', 'last_ai_analysis']
            for date_field in date_fields:
                if project.get(date_field):
                    try:
                        project[date_field] = str(project[date_field])
                    except:
                        project[date_field] = None
            
            # Ensure numeric fields have defaults
            if project.get('progress_percentage') is None:
                project['progress_percentage'] = 0
            if project.get('area_hectares') is None:
                project['area_hectares'] = 0
            if project.get('vegetation_index') is None:
                project['vegetation_index'] = 0
            
            # Convert Decimal types to float for JSON serialization
            if project.get('area_hectares'):
                project['area_hectares'] = float(project['area_hectares'])
            if project.get('soil_ph'):
                project['soil_ph'] = float(project['soil_ph'])
            if project.get('temperature'):
                project['temperature'] = float(project['temperature'])
            if project.get('vegetation_index'):
                project['vegetation_index'] = float(project['vegetation_index'])
            if project.get('estimated_budget'):
                project['estimated_budget'] = float(project['estimated_budget'])
            if project.get('latitude'):
                project['latitude'] = float(project['latitude'])
            if project.get('longitude'):
                project['longitude'] = float(project['longitude'])
            
            processed_projects.append(project)
        
        cur.close()
        
        print(f"✅ Successfully processed {len(processed_projects)} projects")
        if processed_projects:
            print(f"📤 Sample project data: {processed_projects[0].get('name')} - Type: {processed_projects[0].get('project_type')}")
        
        return jsonify({'success': True, 'projects': processed_projects})
        
    except Exception as e:
        print(f"❌ Error in api_list_projects: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@projects_bp.route('/api/analyze', methods=['POST'])
def api_analyze_location():
    """API endpoint for location analysis"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        required = ['latitude', 'longitude', 'area_hectares']
        if not all(field in data for field in required):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Perform analysis
        analysis = comprehensive_land_analysis(
            float(data['latitude']),
            float(data['longitude']),
            float(data['area_hectares'])
        )
        
        if not analysis:
            return jsonify({'success': False, 'error': 'Analysis failed'}), 500
        
        return jsonify({'success': True, 'analysis': analysis})
        
    except Exception as e:
        print(f"Error in api_analyze_location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================
# MAIN ROUTES
# ========================

@projects_bp.route('/')
def projects():
    """Display all projects for the logged-in user"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    return render_template('projects.html', user=session)

@projects_bp.route('/create', methods=['POST'])
def create_project():
    """Create a new project with AI analysis"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        required_fields = ['name', 'project_type', 'area_hectares', 'latitude', 'longitude']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        print(f"Creating project: {data['name']}")
        
        # Perform AI analysis
        ai_analysis = comprehensive_land_analysis(
            float(data['latitude']),
            float(data['longitude']),
            float(data['area_hectares'])
        )
        
        if not ai_analysis:
            return jsonify({'error': 'Failed to analyze location'}), 500
        
        # Get readable location name
        location_name = get_location_name(float(data['latitude']), float(data['longitude']))
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            INSERT INTO projects 
            (user_id, name, description, project_type, area_hectares, location,
             latitude, longitude, soil_type, soil_ph, soil_fertility, climate_zone,
             annual_rainfall, temperature, humidity, elevation, vegetation_index, 
             land_degradation_level, recommended_crops, recommended_trees, 
             restoration_techniques, estimated_timeline_months, estimated_budget, 
             status, start_date, last_ai_analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            user_id,
            data.get('name'),
            data.get('description', ''),
            data.get('project_type'),
            data.get('area_hectares'),
            location_name,
            data.get('latitude'),
            data.get('longitude'),
            ai_analysis['soil_type'],
            ai_analysis['soil_ph'],
            ai_analysis['soil_fertility'],
            ai_analysis['climate_zone'],
            ai_analysis['annual_rainfall'],
            ai_analysis.get('temperature'),
            ai_analysis.get('humidity'),
            ai_analysis.get('elevation', 0),
            ai_analysis['vegetation_index'],
            ai_analysis['land_degradation_level'],
            json.dumps(ai_analysis['recommended_crops']),
            json.dumps(ai_analysis['recommended_trees']),
            json.dumps(ai_analysis['restoration_techniques']),
            ai_analysis['estimated_timeline_months'],
            ai_analysis['estimated_budget'],
            'planning',
            datetime.now().date(),
            datetime.now()
        ))
        
        mysql.connection.commit()
        project_id = cur.lastrowid
        cur.close()
        
        print(f"✅ Project created successfully! ID: {project_id}")
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'ai_analysis': ai_analysis
        }), 201
        
    except Exception as e:
        print(f"Error creating project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>')
def project_detail(project_id):
    """View project details"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return render_template('404.html'), 404
        
        # Parse JSON fields
        for field in ['recommended_crops', 'recommended_trees', 'restoration_techniques']:
            if project.get(field):
                try:
                    if isinstance(project[field], str):
                        project[field] = json.loads(project[field])
                except:
                    project[field] = []
        
        cur.close()
        
        return render_template('project_detail.html', project=project, user=session)
        
    except Exception as e:
        print(f"Error fetching project detail: {e}")
        return render_template('404.html'), 404

@projects_bp.route('/<int:project_id>/reanalyze', methods=['POST'])
def reanalyze_project(project_id):
    """Re-run AI analysis on a project"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT * FROM projects WHERE id = %s AND user_id = %s', 
                   (project_id, session.get('user_id')))
        
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'error': 'Project not found'}), 404
        
        # Re-analyze
        ai_analysis = comprehensive_land_analysis(
            float(project['latitude']),
            float(project['longitude']),
            float(project['area_hectares'])
        )
        
        if not ai_analysis:
            cur.close()
            return jsonify({'error': 'Analysis failed'}), 500
        
        # Update project
        cur.execute('''
            UPDATE projects
            SET vegetation_index = %s,
                land_degradation_level = %s,
                soil_ph = %s,
                temperature = %s,
                humidity = %s,
                last_ai_analysis = %s
            WHERE id = %s
        ''', (
            ai_analysis['vegetation_index'],
            ai_analysis['land_degradation_level'],
            ai_analysis['soil_ph'],
            ai_analysis['temperature'],
            ai_analysis['humidity'],
            datetime.now(),
            project_id
        ))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True, 'analysis': ai_analysis}), 200
        
    except Exception as e:
        print(f"Error re-analyzing: {e}")
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>/update-progress', methods=['POST'])
def update_progress(project_id):
    """Update project progress percentage"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        progress = data.get('progress_percentage', 0)
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            UPDATE projects
            SET progress_percentage = %s,
                status = CASE
                    WHEN %s >= 100 THEN 'completed'
                    WHEN %s > 0 THEN 'active'
                    ELSE status
                END
            WHERE id = %s AND user_id = %s
        ''', (progress, progress, progress, project_id, session.get('user_id')))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating progress: {e}")
        return jsonify({'error': str(e)}), 500
    
    
