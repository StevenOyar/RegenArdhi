import os
import requests
import json
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time


from app.notifications import create_notification


load_dotenv()

# Create Blueprint
projects_bp = Blueprint('projects', __name__, url_prefix='/projects')
# Create Blueprint

# MySQL connection (passed from main app)
mysql = None

# API Keys
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
NASA_EARTH_API_KEY = os.getenv('NASA_EARTH_API_KEY')

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
            
            # FIX: Check if elevation column exists using proper cursor access
            try:
                cur.execute('''
                    SELECT COLUMN_NAME 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'projects' 
                    AND COLUMN_NAME = 'elevation'
                ''')
                
                result = cur.fetchone()
                
                # If result is None or empty, column doesn't exist
                if not result:
                    print("⚠️ Adding 'elevation' column to projects table...")
                    cur.execute('''
                        ALTER TABLE projects 
                        ADD COLUMN elevation INT DEFAULT 0 AFTER humidity
                    ''')
                    print("✅ 'elevation' column added successfully!")
                else:
                    print("✅ 'elevation' column already exists")
                    
            except Exception as col_check_error:
                print(f"⚠️ Column check error (non-critical): {col_check_error}")
                # Continue anyway - the column might already exist
            
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
    """Create a new project with AI analysis - ENHANCED"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        required_fields = ['name', 'project_type', 'area_hectares', 'latitude', 'longitude']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        print(f"Creating project: {data['name']}")
        
        # Perform AI analysis
        ai_analysis = comprehensive_land_analysis(
            float(data['latitude']),
            float(data['longitude']),
            float(data['area_hectares'])
        )
        
        if not ai_analysis:
            return jsonify({'success': False, 'error': 'Failed to analyze location'}), 500
        
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
        
        # CREATE NOTIFICATION with proper link
        create_notification(
            user_id=user_id,
            notification_type='project_created',
            message=f'🌿 "{data.get("name")}" has been successfully created with AI analysis!',
            project_id=project_id,
            project_name=data.get('name')
        )
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'ai_analysis': ai_analysis
        }), 201
        
    except Exception as e:
        print(f"Error creating project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



@projects_bp.route('/<int:project_id>')
def project_detail(project_id):
    """View project details - FIXED VERSION"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        user_id = session.get('user_id')
        
        # Verify project belongs to user
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, user_id))
        
        project = cur.fetchone()
        
        if not project:
            cur.close()
            flash('Project not found or access denied', 'error')
            return redirect(url_for('projects.projects'))
        
        # Parse JSON fields
        for field in ['recommended_crops', 'recommended_trees', 'restoration_techniques']:
            if project.get(field):
                try:
                    if isinstance(project[field], str):
                        project[field] = json.loads(project[field])
                except:
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
        
        # Convert Decimal types to float
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
        
        cur.close()
        
        # Create inline template since project_detail.html doesn't exist
        # This renders the project detail in a modal-like view
        return render_template('projects.html', project=project, user=session)
        
    except Exception as e:
        print(f"Error fetching project detail: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading project details', 'error')
        return redirect(url_for('projects.projects'))
# ========================
# NEW ROUTES FOR REDESIGNED FRONTEND
# ========================
@projects_bp.route('/<int:project_id>/update', methods=['POST'])
def update_project(project_id):
    """Update an existing project - ENHANCED"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # First check if project exists and belongs to user
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT * FROM projects WHERE id = %s AND user_id = %s', 
                   (project_id, user_id))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Update basic fields
        name = data.get('name', project['name'])
        description = data.get('description', project['description'])
        project_type = data.get('project_type', project['project_type'])
        area_hectares = data.get('area_hectares', project['area_hectares'])
        latitude = data.get('latitude', project['latitude'])
        longitude = data.get('longitude', project['longitude'])
        
        # Check if location changed - if so, re-analyze
        location_changed = (
            float(latitude) != float(project['latitude']) or 
            float(longitude) != float(project['longitude']) or
            float(area_hectares) != float(project['area_hectares'])
        )
        
        if location_changed:
            print(f"🔄 Location changed, running new AI analysis...")
            
            # Run new AI analysis
            ai_analysis = comprehensive_land_analysis(
                float(latitude),
                float(longitude),
                float(area_hectares)
            )
            
            if not ai_analysis:
                cur.close()
                return jsonify({'success': False, 'error': 'Failed to analyze new location'}), 500
            
            # Get new location name
            location_name = get_location_name(float(latitude), float(longitude))
            
            # Update with new analysis
            cur.execute('''
                UPDATE projects 
                SET name = %s,
                    description = %s,
                    project_type = %s,
                    area_hectares = %s,
                    location = %s,
                    latitude = %s,
                    longitude = %s,
                    soil_type = %s,
                    soil_ph = %s,
                    soil_fertility = %s,
                    climate_zone = %s,
                    annual_rainfall = %s,
                    temperature = %s,
                    humidity = %s,
                    elevation = %s,
                    vegetation_index = %s,
                    land_degradation_level = %s,
                    recommended_crops = %s,
                    recommended_trees = %s,
                    restoration_techniques = %s,
                    estimated_timeline_months = %s,
                    estimated_budget = %s,
                    last_ai_analysis = %s,
                    updated_at = %s
                WHERE id = %s AND user_id = %s
            ''', (
                name, description, project_type, area_hectares, location_name,
                latitude, longitude,
                ai_analysis['soil_type'],
                ai_analysis['soil_ph'],
                ai_analysis['soil_fertility'],
                ai_analysis['climate_zone'],
                ai_analysis['annual_rainfall'],
                ai_analysis['temperature'],
                ai_analysis['humidity'],
                ai_analysis.get('elevation', 0),
                ai_analysis['vegetation_index'],
                ai_analysis['land_degradation_level'],
                json.dumps(ai_analysis['recommended_crops']),
                json.dumps(ai_analysis['recommended_trees']),
                json.dumps(ai_analysis['restoration_techniques']),
                ai_analysis['estimated_timeline_months'],
                ai_analysis['estimated_budget'],
                datetime.now(),
                datetime.now(),
                project_id,
                user_id
            ))
            
            # CREATE NOTIFICATION for re-analysis
            create_notification(
                user_id=user_id,
                notification_type='analysis_complete',
                message=f'🧠 AI analysis completed for "{name}"',
                project_id=project_id,
                project_name=name
            )
        else:
            # Just update basic info
            cur.execute('''
                UPDATE projects 
                SET name = %s,
                    description = %s,
                    project_type = %s,
                    updated_at = %s
                WHERE id = %s AND user_id = %s
            ''', (name, description, project_type, datetime.now(), project_id, user_id))
        
        mysql.connection.commit()
        cur.close()
        
        print(f"✅ Project {project_id} updated successfully!")
        
        # CREATE NOTIFICATION for update
        create_notification(
            user_id=user_id,
            notification_type='project_updated',
            message=f'"{name}" has been updated',
            project_id=project_id,
            project_name=name
        )
        
        return jsonify({
            'success': True,
            'message': 'Project updated successfully',
            'location_changed': location_changed,
            'project_id': project_id  # Return ID for frontend animation
        }), 200
        
    except Exception as e:
        print(f"❌ Error updating project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# delete 
@projects_bp.route('/<int:project_id>/delete', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project - ENHANCED WITH ANIMATION"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        
        # Get project name before deleting (for notification)
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT name FROM projects WHERE id = %s AND user_id = %s', 
                   (project_id, user_id))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        project_name = project['name']
        
        # Delete the project (CASCADE will handle related records)
        cur.execute('DELETE FROM projects WHERE id = %s AND user_id = %s', 
                   (project_id, user_id))
        
        mysql.connection.commit()
        cur.close()
        
        print(f"✅ Project {project_id} deleted successfully!")
        
        # CREATE NOTIFICATION for deletion (no link since project is deleted)
        create_notification(
            user_id=user_id,
            notification_type='project_deleted',
            message=f'"{project_name}" has been deleted',
            project_id=None,
            project_name=project_name
        )
        
        return jsonify({
            'success': True,
            'message': 'Project deleted successfully',
            'project_id': project_id  # Return ID for frontend animation
        }), 200
        
    except Exception as e:
        print(f"❌ Error deleting project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ========================================
# UPDATE: update_project_status() function
# ========================================

@projects_bp.route('/<int:project_id>/update-status', methods=['POST'])
def update_project_status(project_id):
    """Update project status and progress"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        status = data.get('status')
        progress_percentage = data.get('progress_percentage')
        user_id = session.get('user_id')
        
        print(f"📥 Update request - Project: {project_id}, Status: {status}, Progress: {progress_percentage}")
        
        valid_statuses = ['planning', 'active', 'completed', 'paused']
        if status not in valid_statuses:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        # Prepare update query
        update_fields = ['status = %s', 'updated_at = %s']
        update_values = [status, datetime.now()]
        
        # Handle progress_percentage if provided
        if progress_percentage is not None:
            progress_percentage = int(progress_percentage)
            
            if progress_percentage < 0 or progress_percentage > 100:
                return jsonify({'success': False, 'error': 'Progress must be between 0 and 100'}), 400
            
            update_fields.append('progress_percentage = %s')
            update_values.append(progress_percentage)
            
            print(f"✅ Setting progress to {progress_percentage}%")
        else:
            # Auto-set progress based on status if not provided
            if status == 'planning':
                update_fields.append('progress_percentage = %s')
                update_values.append(0)
                progress_percentage = 0
            elif status == 'completed':
                update_fields.append('progress_percentage = %s')
                update_values.append(100)
                progress_percentage = 100
        
        # Get current project info
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT name, status, start_date, progress_percentage FROM projects WHERE id = %s AND user_id = %s', 
                   (project_id, user_id))
        current_project = cur.fetchone()
        
        if not current_project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        project_name = current_project['name']
        old_status = current_project['status']
        old_progress = current_project['progress_percentage'] or 0
        
        # Set start_date if moving from planning to active
        if current_project['status'] == 'planning' and status == 'active':
            if not current_project['start_date']:
                update_fields.append('start_date = %s')
                update_values.append(datetime.now().date())
                print(f"📅 Setting start_date to today")
        
        # Set end_date if moving to completed
        if status == 'completed':
            update_fields.append('end_date = %s')
            update_values.append(datetime.now().date())
            print(f"🏁 Setting end_date to today")
        
        # Build and execute update query
        update_query = f'''
            UPDATE projects 
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s
        '''
        update_values.extend([project_id, user_id])
        
        print(f"🔄 Executing query with values: {update_values}")
        
        cur.execute(update_query, tuple(update_values))
        
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found or no changes made'}), 404
        
        mysql.connection.commit()
        
        # Fetch updated project data to return
        cur.execute('''
            SELECT status, progress_percentage, start_date, end_date, updated_at
            FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, user_id))
        
        updated_project = cur.fetchone()
        cur.close()
        
        print(f"✅ Status updated successfully! New progress: {updated_project['progress_percentage']}%")
        
        # 🆕 CREATE NOTIFICATION for status change
        if status != old_status:
            notification_type = 'project_completed' if status == 'completed' else 'status_changed'
            
            status_messages = {
                'planning': 'is now in planning phase',
                'active': 'is now active',
                'completed': 'has been completed! 🎉',
                'paused': 'has been paused'
            }
            
            create_notification(
                user_id=user_id,
                notification_type=notification_type,
                message=f'"{project_name}" {status_messages.get(status, f"status changed to {status}")}',
                project_id=project_id,
                project_name=project_name
            )
        
        # 🆕 CREATE NOTIFICATION for progress update (if changed significantly)
        if progress_percentage is not None and abs(progress_percentage - old_progress) >= 5:
            create_notification(
                user_id=user_id,
                notification_type='progress_updated',
                message=f'"{project_name}" progress updated to {progress_percentage}%',
                project_id=project_id,
                project_name=project_name
            )
            
            # 🆕 CHECK FOR MILESTONES
            milestones = [25, 50, 75]
            for milestone in milestones:
                if old_progress < milestone <= progress_percentage:
                    create_notification(
                        user_id=user_id,
                        notification_type='milestone_reached',
                        message=f'🎯 "{project_name}" reached {milestone}% completion milestone!',
                        project_id=project_id,
                        project_name=project_name
                    )
        
        # Return updated data
        return jsonify({
            'success': True,
            'message': 'Status updated successfully',
            'project': {
                'id': project_id,
                'status': updated_project['status'],
                'progress_percentage': int(updated_project['progress_percentage'] or 0),
                'start_date': str(updated_project['start_date']) if updated_project['start_date'] else None,
                'end_date': str(updated_project['end_date']) if updated_project['end_date'] else None,
                'updated_at': str(updated_project['updated_at'])
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error updating status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@projects_bp.route('/<int:project_id>/report')
def download_report(project_id):
    """Generate and download project report"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        user_id = session.get('user_id')
        
        cur.execute('SELECT * FROM projects WHERE id = %s AND user_id = %s', 
                   (project_id, user_id))
        project = cur.fetchone()
        cur.close()
        
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('projects.projects'))
        
        # Parse JSON fields
        for field in ['recommended_crops', 'recommended_trees', 'restoration_techniques']:
            if project.get(field):
                try:
                    if isinstance(project[field], str):
                        project[field] = json.loads(project[field])
                except:
                    project[field] = []
        
        # For now, render an HTML report
        # In production, you could generate a PDF using libraries like ReportLab or WeasyPrint
        return render_template('project_report.html', project=project, user=session)
        
    except Exception as e:
        print(f"Error generating report: {e}")
        flash('Error generating report', 'error')
        return redirect(url_for('projects.projects'))


@projects_bp.route('/api/stats')
def api_project_stats():
    """Get project statistics for dashboard"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        user_id = session.get('user_id')
        
        # Get count by status
        cur.execute('''
            SELECT 
                COUNT(*) as total_projects,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_projects,
                SUM(CASE WHEN status = 'planning' THEN 1 ELSE 0 END) as planning_projects,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_projects,
                SUM(area_hectares) as total_area,
                COUNT(DISTINCT location) as total_locations
            FROM projects
            WHERE user_id = %s
        ''', (user_id,))
        
        stats = cur.fetchone()
        
        # Get recent projects
        cur.execute('''
            SELECT id, name, status, created_at
            FROM projects
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        ''', (user_id,))
        
        recent_projects = cur.fetchall()
        
        cur.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_projects': stats['total_projects'] or 0,
                'active_projects': stats['active_projects'] or 0,
                'planning_projects': stats['planning_projects'] or 0,
                'completed_projects': stats['completed_projects'] or 0,
                'total_area': float(stats['total_area'] or 0),
                'total_locations': stats['total_locations'] or 0
            },
            'recent_projects': [dict(p) for p in recent_projects]
        })
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@projects_bp.route('/api/map-data')
def api_map_data():
    """Get simplified project data for map markers"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        user_id = session.get('user_id')
        
        cur.execute('''
            SELECT 
                id, name, location, latitude, longitude, 
                status, area_hectares, project_type,
                vegetation_index, land_degradation_level
            FROM projects
            WHERE user_id = %s
        ''', (user_id,))
        
        projects = cur.fetchall()
        cur.close()
        
        # Convert Decimal types
        for project in projects:
            if project.get('latitude'):
                project['latitude'] = float(project['latitude'])
            if project.get('longitude'):
                project['longitude'] = float(project['longitude'])
            if project.get('area_hectares'):
                project['area_hectares'] = float(project['area_hectares'])
            if project.get('vegetation_index'):
                project['vegetation_index'] = float(project['vegetation_index'])
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        print(f"Error getting map data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # Update project with new analysis
        cur.execute('''
            UPDATE projects
            SET vegetation_index = %s,
                land_degradation_level = %s,
                soil_ph = %s,
                temperature = %s,
                humidity = %s,
                elevation = %s,
                last_ai_analysis = %s
            WHERE id = %s
        ''', (
            ai_analysis['vegetation_index'],
            ai_analysis['land_degradation_level'],
            ai_analysis['soil_ph'],
            ai_analysis['temperature'],
            ai_analysis['humidity'],
            ai_analysis.get('elevation', 0),
            datetime.now(),
            project_id
        ))
        
        mysql.connection.commit()
        cur.close()
        
        # 🆕 CREATE NOTIFICATION for analysis complete
        create_notification(
            user_id=session.get('user_id'),
            notification_type='analysis_complete',
            message=f'🧠 AI analysis completed for "{project["name"]}"',
            project_id=project_id,
            project_name=project['name']
        )
        
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
    
    
