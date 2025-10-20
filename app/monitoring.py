import os
import requests
import json
from flask import Blueprint, render_template, request, jsonify, session
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import logging
from typing import Dict, List, Optional, Tuple
import random

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/monitoring')

# MySQL connection
mysql = None

# ========================
# API CONFIGURATIONS
# ========================

# Hugging Face API
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY') or os.getenv('HF_TOKEN')
HUGGINGFACE_BASE_URL = "https://api-inference.huggingface.co/models"
HUGGINGFACE_ROUTER_URL = os.getenv('HUGGINGFACE_BASE_URL', 'https://router.huggingface.co/v1')

# OpenWeather API
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# NASA POWER API
NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# ========================
# STATIC FALLBACK DATA
# ========================

FALLBACK_CROP_DATABASE = {
    'tropical': {
        'high_rainfall': {
            'crops': ['Rice', 'Bananas', 'Cassava', 'Yams', 'Taro', 'Cocoa', 'Coffee'],
            'trees': ['Mahogany', 'Teak', 'Rubber Tree', 'Oil Palm', 'Bamboo', 'Mango'],
            'description': 'High rainfall tropical zone - suitable for moisture-loving crops'
        },
        'moderate_rainfall': {
            'crops': ['Maize', 'Beans', 'Sweet Potato', 'Pineapple', 'Papaya', 'Passion Fruit'],
            'trees': ['Acacia', 'Neem', 'Moringa', 'Grevillea', 'Eucalyptus', 'Avocado'],
            'description': 'Moderate rainfall tropical zone - versatile growing conditions'
        },
        'low_rainfall': {
            'crops': ['Millet', 'Sorghum', 'Groundnuts', 'Cowpeas', 'Pigeon Peas', 'Sunflower'],
            'trees': ['Acacia', 'Baobab', 'Neem', 'Moringa', 'Desert Date'],
            'description': 'Dry tropical zone - drought-resistant varieties recommended'
        }
    },
    'subtropical': {
        'high_rainfall': {
            'crops': ['Rice', 'Citrus', 'Grapes', 'Tomatoes', 'Cotton', 'Sugarcane'],
            'trees': ['Oak', 'Citrus', 'Olive', 'Pine', 'Cypress', 'Pecan'],
            'description': 'Humid subtropical - excellent for diverse crops'
        },
        'moderate_rainfall': {
            'crops': ['Wheat', 'Maize', 'Cotton', 'Vegetables', 'Melons', 'Peppers'],
            'trees': ['Oak', 'Maple', 'Pecan', 'Pine', 'Cedar'],
            'description': 'Moderate subtropical - balanced growing conditions'
        },
        'low_rainfall': {
            'crops': ['Wheat', 'Barley', 'Chickpeas', 'Lentils', 'Olives'],
            'trees': ['Olive', 'Almond', 'Carob', 'Pine', 'Cedar'],
            'description': 'Dry subtropical - Mediterranean-style crops'
        }
    },
    'temperate': {
        'high_rainfall': {
            'crops': ['Wheat', 'Barley', 'Oats', 'Potatoes', 'Vegetables', 'Berries'],
            'trees': ['Oak', 'Maple', 'Ash', 'Apple', 'Cherry', 'Walnut'],
            'description': 'Temperate with high rainfall - cool-season crops'
        },
        'moderate_rainfall': {
            'crops': ['Wheat', 'Corn', 'Soybeans', 'Potatoes', 'Vegetables'],
            'trees': ['Oak', 'Maple', 'Birch', 'Pine', 'Spruce'],
            'description': 'Moderate temperate - standard grain crops'
        },
        'low_rainfall': {
            'crops': ['Wheat', 'Barley', 'Canola', 'Sunflower', 'Rye'],
            'trees': ['Pine', 'Juniper', 'Russian Olive', 'Poplar'],
            'description': 'Dry temperate - drought-tolerant varieties'
        }
    }
}

FALLBACK_WEATHER_PATTERNS = {
    'tropical': {'temp': 28, 'humidity': 80, 'rainfall': 2000},
    'subtropical': {'temp': 22, 'humidity': 65, 'rainfall': 1000},
    'temperate': {'temp': 15, 'humidity': 60, 'rainfall': 800},
    'arid': {'temp': 30, 'humidity': 30, 'rainfall': 250},
    'polar': {'temp': 0, 'humidity': 70, 'rainfall': 400}
}

# ========================
# DATABASE INITIALIZATION
# ========================

def init_monitoring(app, mysql_instance):
    """Initialize monitoring module"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            
            # Create monitoring_data table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Vegetation Metrics
                    ndvi DECIMAL(4, 2),
                    vegetation_health VARCHAR(50),
                    canopy_cover DECIMAL(5, 2),
                    
                    -- Climate Data
                    temperature DECIMAL(5, 2),
                    humidity INT,
                    rainfall DECIMAL(7, 2),
                    wind_speed DECIMAL(5, 2),
                    
                    -- Soil Metrics
                    soil_moisture DECIMAL(5, 2),
                    soil_temperature DECIMAL(5, 2),
                    
                    -- Data Source
                    data_source VARCHAR(50) DEFAULT 'api',
                    
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_project_date (project_id, recorded_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Create ai_recommendations table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS ai_recommendations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    recommendation_type VARCHAR(50),
                    title VARCHAR(255),
                    description TEXT,
                    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
                    actions JSON,
                    
                    ai_model VARCHAR(100),
                    confidence DECIMAL(5, 2),
                    
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_project_type (project_id, recommendation_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Check if ai_model column exists and add if missing
            try:
                cur.execute('''
                    SELECT COLUMN_NAME 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'ai_recommendations' 
                    AND COLUMN_NAME = 'ai_model'
                ''')
                
                result = cur.fetchone()
                
                if not result:
                    logger.info("⚙️ Adding missing 'ai_model' column...")
                    cur.execute('''
                        ALTER TABLE ai_recommendations 
                        ADD COLUMN ai_model VARCHAR(100) DEFAULT 'rule_based' AFTER actions
                    ''')
                    logger.info("✅ 'ai_model' column added!")
                    
            except Exception as col_error:
                logger.warning(f"Column check error (non-critical): {col_error}")
            
            # Check if confidence column exists and add if missing
            try:
                cur.execute('''
                    SELECT COLUMN_NAME 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'ai_recommendations' 
                    AND COLUMN_NAME = 'confidence'
                ''')
                
                result = cur.fetchone()
                
                if not result:
                    logger.info("⚙️ Adding missing 'confidence' column...")
                    cur.execute('''
                        ALTER TABLE ai_recommendations 
                        ADD COLUMN confidence DECIMAL(5, 2) DEFAULT 80.00 AFTER ai_model
                    ''')
                    logger.info("✅ 'confidence' column added!")
                    
            except Exception as col_error:
                logger.warning(f"Column check error (non-critical): {col_error}")
            
            mysql.connection.commit()
            cur.close()
            logger.info("✅ Monitoring tables initialized!")
            
        except Exception as e:
            logger.error(f"❌ Error initializing monitoring tables: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("✅ Monitoring module initialized!")

# ========================
# WEATHER API WITH SECURE BACKEND PROXY
# ========================

@monitoring_bp.route('/api/weather')
def get_weather():
    """Secure backend proxy for weather data - API key never exposed to frontend"""
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        
        if not lat or not lon:
            return jsonify({'success': False, 'error': 'Latitude and longitude required'}), 400
        
        lat = float(lat)
        lon = float(lon)
        
        # Determine climate zone for fallback
        climate_zone = determine_climate_zone(lat)
        
        # Try to get real weather data
        weather_data = fetch_openweather_data(lat, lon)
        
        if weather_data:
            # Get forecast
            forecast_data = fetch_weather_forecast(lat, lon)
            
            return jsonify({
                'success': True,
                'current': weather_data,
                'forecast': forecast_data,
                'source': 'openweather_api',
                'climate_zone': climate_zone
            })
        else:
            # Use fallback data
            logger.warning(f"Using fallback weather for {lat}, {lon}")
            fallback = generate_fallback_weather(lat, lon, climate_zone)
            
            return jsonify({
                'success': True,
                'current': fallback['current'],
                'forecast': fallback['forecast'],
                'source': 'estimated',
                'climate_zone': climate_zone
            })
            
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def fetch_openweather_data(lat: float, lon: float) -> Optional[Dict]:
    """Fetch current weather from OpenWeather API"""
    try:
        if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == 'your_key_here':
            return None
        
        url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'temp': round(data['main']['temp'], 1),
                'feels_like': round(data['main'].get('feels_like', data['main']['temp']), 1),
                'humidity': data['main'].get('humidity', 0),
                'pressure': data['main'].get('pressure', 0),
                'description': data['weather'][0]['description'],
                'wind_speed': data.get('wind', {}).get('speed', 0),
                'clouds': data.get('clouds', {}).get('all', 0),
                'visibility': data.get('visibility', 10000) / 1000,
                'rain': data.get('rain', {}).get('1h', 0)
            }
        
        return None
        
    except Exception as e:
        logger.error(f"OpenWeather fetch error: {e}")
        return None

def fetch_weather_forecast(lat: float, lon: float) -> List[Dict]:
    """Fetch 5-day weather forecast"""
    try:
        if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == 'your_key_here':
            return generate_fallback_forecast(lat, lon)
        
        url = f"{OPENWEATHER_BASE_URL}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'cnt': 40  # 5 days * 8 (3-hour intervals)
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Process daily averages
            daily_data = {}
            for item in data['list']:
                date = datetime.fromtimestamp(item['dt']).date()
                if date not in daily_data:
                    daily_data[date] = {
                        'temps': [],
                        'humidity': [],
                        'rain': 0,
                        'dt': item['dt']
                    }
                
                daily_data[date]['temps'].append(item['main']['temp'])
                daily_data[date]['humidity'].append(item['main']['humidity'])
                daily_data[date]['rain'] += item.get('rain', {}).get('3h', 0)
            
            # Create daily forecast
            forecast = []
            for date, values in sorted(daily_data.items())[:5]:
                forecast.append({
                    'dt': values['dt'],
                    'temp': round(sum(values['temps']) / len(values['temps']), 1),
                    'humidity': round(sum(values['humidity']) / len(values['humidity'])),
                    'rain': round(values['rain'], 1)
                })
            
            return forecast
        
        return generate_fallback_forecast(lat, lon)
        
    except Exception as e:
        logger.error(f"Forecast fetch error: {e}")
        return generate_fallback_forecast(lat, lon)

def generate_fallback_weather(lat: float, lon: float, climate_zone: str) -> Dict:
    """Generate realistic fallback weather data"""
    pattern = FALLBACK_WEATHER_PATTERNS.get(climate_zone, FALLBACK_WEATHER_PATTERNS['temperate'])
    
    # Add some randomness
    temp_variation = random.uniform(-3, 3)
    humidity_variation = random.randint(-10, 10)
    
    current = {
        'temp': round(pattern['temp'] + temp_variation, 1),
        'feels_like': round(pattern['temp'] + temp_variation + random.uniform(-2, 2), 1),
        'humidity': max(20, min(100, pattern['humidity'] + humidity_variation)),
        'pressure': 1013,
        'description': 'estimated conditions',
        'wind_speed': round(random.uniform(0, 5), 1),
        'clouds': random.randint(20, 80),
        'visibility': 10,
        'rain': 0
    }
    
    forecast = generate_fallback_forecast(lat, lon, pattern)
    
    return {'current': current, 'forecast': forecast}

def generate_fallback_forecast(lat: float, lon: float, pattern: Dict = None) -> List[Dict]:
    """Generate fallback forecast data"""
    if not pattern:
        climate_zone = determine_climate_zone(lat)
        pattern = FALLBACK_WEATHER_PATTERNS.get(climate_zone, FALLBACK_WEATHER_PATTERNS['temperate'])
    
    forecast = []
    base_time = int(time.time())
    
    for i in range(5):
        day_variation = random.uniform(-4, 4)
        forecast.append({
            'dt': base_time + (i * 86400),
            'temp': round(pattern['temp'] + day_variation, 1),
            'humidity': max(20, min(100, pattern['humidity'] + random.randint(-10, 10))),
            'rain': round(random.uniform(0, 5), 1) if random.random() > 0.6 else 0
        })
    
    return forecast

def determine_climate_zone(lat: float) -> str:
    """Determine climate zone from latitude"""
    abs_lat = abs(lat)
    
    if abs_lat > 66.5:
        return 'polar'
    elif abs_lat > 45:
        return 'temperate'
    elif abs_lat > 23.5:
        return 'subtropical'
    elif abs_lat > 10:
        return 'tropical'
    else:
        return 'tropical'

# ========================
# AI-POWERED CROP RECOMMENDATIONS
# ========================

@monitoring_bp.route('/api/recommended-plants/<int:project_id>')
def get_recommended_plants(project_id):
    """Get AI-powered crop recommendations for a project"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Get project data
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, session['user_id']))
        
        project = cur.fetchone()
        cur.close()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Generate recommendations using AI
        recommendations = generate_ai_crop_recommendations(project)
        
        return jsonify({
            'success': True,
            'plants': recommendations,
            'ai_model': 'huggingface' if HUGGINGFACE_API_KEY else 'fallback',
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting plant recommendations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_ai_crop_recommendations(project: Dict) -> List[Dict]:
    """Generate AI-powered crop recommendations"""
    
    # Extract project data
    climate_zone = project.get('climate_zone', 'tropical')
    soil_type = project.get('soil_type', 'Loamy')
    soil_ph = float(project.get('soil_ph', 6.5))
    annual_rainfall = int(project.get('annual_rainfall', 1000))
    temperature = float(project.get('temperature', 25))
    ndvi = float(project.get('vegetation_index', 0.4))
    degradation = project.get('land_degradation_level', 'moderate')
    
    # Try AI-powered recommendations first
    if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != 'your_key_here':
        ai_recommendations = query_ai_for_crops(
            climate_zone, soil_type, soil_ph, annual_rainfall, 
            temperature, ndvi, degradation
        )
        
        if ai_recommendations:
            return ai_recommendations
    
    # Fallback to rule-based system
    logger.info("Using fallback crop recommendation system")
    return generate_fallback_crop_recommendations(
        climate_zone, soil_type, soil_ph, annual_rainfall, 
        temperature, ndvi, degradation
    )

def query_ai_for_crops(climate_zone: str, soil_type: str, soil_ph: float, 
                       rainfall: int, temp: float, ndvi: float, 
                       degradation: str) -> Optional[List[Dict]]:
    """Query Hugging Face AI for crop recommendations"""
    try:
        # Improved prompt for better AI responses
        prompt = f"""As an agricultural expert, recommend the 5 best crops for these conditions:

LOCATION DATA:
- Climate: {climate_zone}
- Soil: {soil_type}, pH {soil_ph}
- Rainfall: {rainfall}mm/year
- Temperature: {temp}°C average
- Current vegetation health (NDVI): {ndvi}
- Land condition: {degradation}

TASK: List 5 crops with suitability scores (0-100%).

EXAMPLE FORMAT:
Rice - 85% (thrives in high rainfall, tolerates pH 5.5-7.0)
Maize - 75% (moderate water needs, good for this climate)

YOUR RECOMMENDATIONS:"""

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Try multiple models with different strengths
        models = [
            ("facebook/bart-large-cnn", {"max_length": 200, "min_length": 50, "do_sample": False}),
            ("google/flan-t5-large", {"max_new_tokens": 250, "temperature": 0.7, "do_sample": True}),
            ("distilgpt2", {"max_new_tokens": 200, "temperature": 0.8, "do_sample": True})
        ]
        
        for model_name, params in models:
            try:
                url = f"{HUGGINGFACE_BASE_URL}/{model_name}"
                
                payload = {
                    "inputs": prompt,
                    "parameters": params,
                    "options": {"wait_for_model": True, "use_cache": False}
                }
                
                logger.info(f"🤖 Querying {model_name}...")
                response = requests.post(url, headers=headers, json=payload, timeout=25)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract text from different response formats
                    generated_text = None
                    if isinstance(result, list) and result:
                        item = result[0]
                        generated_text = item.get('generated_text') or item.get('summary_text') or item.get('text')
                    elif isinstance(result, dict):
                        generated_text = result.get('generated_text') or result.get('summary_text') or result.get('text')
                    
                    if generated_text:
                        # Remove the original prompt from the response
                        if prompt in generated_text:
                            generated_text = generated_text.replace(prompt, '').strip()
                        
                        # Parse recommendations
                        recommendations = parse_ai_crop_response(generated_text, climate_zone, rainfall)
                        
                        if recommendations and len(recommendations) > 0:
                            logger.info(f"✅ Got {len(recommendations)} AI crop recommendations from {model_name}")
                            return recommendations
                        else:
                            logger.warning(f"⚠️ {model_name} returned unparseable text")
                
                elif response.status_code == 503:
                    logger.info(f"⏳ {model_name} is loading, waiting...")
                    time.sleep(10)  # Wait for model to load
                    continue
                else:
                    logger.warning(f"⚠️ {model_name} returned status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ {model_name} timed out")
                continue
            except Exception as model_error:
                logger.warning(f"❌ {model_name} error: {str(model_error)[:100]}")
                continue
        
        logger.info("ℹ️ All AI models exhausted, using fallback")
        return None
        
    except Exception as e:
        logger.error(f"AI query error: {e}")
        return None

def parse_ai_crop_response(text: str, climate_zone: str, rainfall: int) -> List[Dict]:
    """Enhanced parser for AI-generated crop recommendations"""
    recommendations = []
    
    try:
        # Clean up the text
        text = text.strip()
        lines = text.split('\n')
        
        import re
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Try multiple patterns
            patterns = [
                r'([A-Za-z\s]+)\s*-\s*(\d+)%',  # "Crop - 85%"
                r'(\d+)%\s*-?\s*([A-Za-z\s]+)',  # "85% - Crop"
                r'([A-Za-z\s]+):\s*(\d+)%',     # "Crop: 85%"
                r'([A-Za-z\s]+)\s+\((\d+)%\)',  # "Crop (85%)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                
                if match:
                    # Extract crop name and suitability
                    groups = match.groups()
                    
                    # Determine which group is the name and which is the percentage
                    if groups[0].isdigit():
                        suitability = int(groups[0])
                        crop_name = groups[1].strip()
                    else:
                        crop_name = groups[0].strip()
                        suitability = int(groups[1]) if len(groups) > 1 else 70
                    
                    # Clean crop name
                    crop_name = crop_name.title()
                    crop_name = re.sub(r'^\d+\.?\s*', '', crop_name)  # Remove leading numbers
                    crop_name = crop_name.split('(')[0].strip()  # Remove parenthetical notes
                    
                    # Validate
                    if len(crop_name) > 2 and len(crop_name) < 30 and suitability > 0 and suitability <= 100:
                        # Check for duplicates
                        if not any(r['name'].lower() == crop_name.lower() for r in recommendations):
                            recommendations.append({
                                'name': crop_name,
                                'suitability': suitability,
                                'source': 'ai'
                            })
                            break  # Found a match, move to next line
        
        # If we got fewer than 3 recommendations, supplement with fallback
        if len(recommendations) < 3:
            logger.info(f"⚠️ Only got {len(recommendations)} from AI, supplementing with fallback")
            
            # Get fallback recommendations
            fallback = generate_fallback_crop_recommendations(
                climate_zone, 'Loamy', 6.5, rainfall, 25, 0.4, 'moderate'
            )
            
            # Add fallback crops that aren't already in the list
            for fb_crop in fallback:
                if len(recommendations) >= 5:
                    break
                if not any(r['name'].lower() == fb_crop['name'].lower() for r in recommendations):
                    recommendations.append(fb_crop)
        
        # Sort by suitability
        recommendations = sorted(recommendations, key=lambda x: x['suitability'], reverse=True)[:5]
        
        return recommendations if len(recommendations) > 0 else None
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None

def generate_fallback_crop_recommendations(climate_zone: str, soil_type: str, 
                                          soil_ph: float, rainfall: int, 
                                          temp: float, ndvi: float, 
                                          degradation: str) -> List[Dict]:
    """Generate rule-based crop recommendations"""
    
    # Normalize climate zone
    climate_key = 'tropical' if 'tropical' in climate_zone.lower() else \
                  'subtropical' if 'subtropical' in climate_zone.lower() else \
                  'temperate'
    
    # Determine rainfall category
    if rainfall > 1500:
        rainfall_key = 'high_rainfall'
    elif rainfall > 800:
        rainfall_key = 'moderate_rainfall'
    else:
        rainfall_key = 'low_rainfall'
    
    # Get base recommendations
    crop_data = FALLBACK_CROP_DATABASE.get(climate_key, {}).get(rainfall_key, {})
    crops = crop_data.get('crops', [])[:5]
    
    # Calculate suitability based on conditions
    recommendations = []
    
    for crop in crops:
        # Base suitability
        suitability = 70
        
        # Adjust for soil pH
        if 6.0 <= soil_ph <= 7.5:
            suitability += 10
        elif 5.5 <= soil_ph < 6.0 or 7.5 < soil_ph <= 8.0:
            suitability += 5
        else:
            suitability -= 10
        
        # Adjust for NDVI (vegetation health)
        if ndvi > 0.6:
            suitability += 10
        elif ndvi > 0.4:
            suitability += 5
        elif ndvi < 0.2:
            suitability -= 15
        
        # Adjust for degradation
        if degradation == 'minimal':
            suitability += 10
        elif degradation == 'severe':
            suitability -= 10
        elif degradation == 'critical':
            suitability -= 20
        
        # Add random variation
        suitability += random.randint(-5, 5)
        
        # Clamp to 0-100
        suitability = max(30, min(100, suitability))
        
        recommendations.append({
            'name': crop,
            'suitability': suitability,
            'source': 'rule_based'
        })
    
    # Sort by suitability
    recommendations.sort(key=lambda x: x['suitability'], reverse=True)
    
    return recommendations

# ========================
# PROJECT METRICS
# ========================

@monitoring_bp.route('/api/metrics/<int:project_id>')
def get_project_metrics(project_id):
    """Get current metrics for a project"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get project
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, session['user_id']))
        
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Get latest monitoring data
        cur.execute('''
            SELECT * FROM monitoring_data
            WHERE project_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
        ''', (project_id,))
        
        latest_data = cur.fetchone()
        
        # Calculate metrics
        ndvi = float(project.get('vegetation_index', 0.4))
        temp = float(project.get('temperature', 25))
        humidity = int(project.get('humidity', 60))
        
        # Get soil moisture from monitoring data or estimate
        soil_moisture = float(latest_data.get('soil_moisture', humidity * 0.8)) if latest_data else humidity * 0.8
        
        # Calculate health score
        health_score = calculate_health_score(project)
        
        # Calculate trends (mock for now)
        ndvi_trend = random.uniform(-2, 5)
        
        cur.close()
        
        return jsonify({
            'success': True,
            'metrics': {
                'ndvi': ndvi,
                'ndvi_trend': ndvi_trend,
                'temperature': temp,
                'humidity': humidity,
                'soil_moisture': round(soil_moisture, 1),
                'health_score': health_score['overall']
            },
            'health_score': health_score
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_health_score(project: Dict) -> Dict:
    """Calculate comprehensive health score"""
    
    ndvi = float(project.get('vegetation_index', 0.4))
    soil_ph = float(project.get('soil_ph', 6.5))
    degradation = project.get('land_degradation_level', 'moderate')
    
    # Vegetation score (0-100)
    veg_score = min(100, ndvi * 150)  # NDVI of 0.6-0.7 = 90-100
    
    # Soil score (0-100)
    if 6.0 <= soil_ph <= 7.5:
        soil_score = 90
    elif 5.5 <= soil_ph < 6.0 or 7.5 < soil_ph <= 8.0:
        soil_score = 70
    elif 5.0 <= soil_ph < 5.5 or 8.0 < soil_ph <= 8.5:
        soil_score = 50
    else:
        soil_score = 30
    
    # Water score (estimated from humidity)
    water_score = min(100, int(project.get('humidity', 60)) * 1.2)
    
    # Biodiversity score (based on NDVI and degradation)
    bio_score = veg_score * 0.8
    if degradation == 'minimal':
        bio_score += 20
    elif degradation == 'moderate':
        bio_score += 10
    
    # Overall score
    overall = (veg_score + soil_score + water_score + bio_score) / 4
    
    return {
        'overall': round(overall),
        'components': {
            'vegetation': round(veg_score),
            'soil': round(soil_score),
            'water': round(water_score),
            'biodiversity': round(bio_score)
        }
    }

# ========================
# ALERTS
# ========================

@monitoring_bp.route('/api/alerts/<int:project_id>')
def get_alerts(project_id):
    """Get alerts for a project"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, session['user_id']))
        
        project = cur.fetchone()
        cur.close()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Generate alerts based on project conditions
        alerts = generate_alerts(project)
        
        return jsonify({
            'success': True,
            'alerts': alerts
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_alerts(project: Dict) -> List[Dict]:
    """Generate condition-based alerts"""
    alerts = []
    
    ndvi = float(project.get('vegetation_index', 0.4))
    soil_ph = float(project.get('soil_ph', 6.5))
    degradation = project.get('land_degradation_level', 'moderate')
    temp = float(project.get('temperature', 25))
    humidity = int(project.get('humidity', 60))
    
    # Low NDVI Alert
    if ndvi < 0.3:
        alerts.append({
            'type': 'error',
            'title': 'Critical Vegetation Health',
            'message': f'NDVI is critically low at {ndvi:.2f}. Immediate intervention needed: increase irrigation, apply organic matter, and plant cover crops.',
            'icon': 'exclamation-triangle',
            'timestamp': datetime.now().isoformat()
        })
    elif ndvi < 0.4:
        alerts.append({
            'type': 'warning',
            'title': 'Low Vegetation Health',
            'message': f'NDVI is {ndvi:.2f}. Consider: adding compost, improving water management, and testing for nutrient deficiencies.',
            'icon': 'leaf',
            'timestamp': datetime.now().isoformat()
        })
    
    # Soil pH Alert
    if soil_ph < 5.5 or soil_ph > 8.0:
        alerts.append({
            'type': 'warning',
            'title': 'Soil pH Out of Range',
            'message': f'Soil pH is {soil_ph}. {"Add lime to raise pH" if soil_ph < 5.5 else "Add sulfur or organic matter to lower pH"}.',
            'icon': 'vial',
            'timestamp': datetime.now().isoformat()
        })
    
    # Degradation Alert
    if degradation in ['severe', 'critical']:
        alerts.append({
            'type': 'error',
            'title': f'{degradation.title()} Land Degradation',
            'message': 'Urgent restoration needed. Implement: erosion control, terracing, agroforestry, and professional consultation.',
            'icon': 'mountain',
            'timestamp': datetime.now().isoformat()
        })
    
    # Temperature Alert
    if temp > 35:
        alerts.append({
            'type': 'warning',
            'title': 'High Temperature Alert',
            'message': f'Temperature is {temp}°C. Protect plants with shade, increase watering frequency, and mulch heavily.',
            'icon': 'temperature-high',
            'timestamp': datetime.now().isoformat()
        })
    elif temp < 10:
        alerts.append({
            'type': 'warning',
            'title': 'Low Temperature Alert',
            'message': f'Temperature is {temp}°C. Frost risk - cover sensitive plants and delay planting.',
            'icon': 'snowflake',
            'timestamp': datetime.now().isoformat()
        })
    
    # Humidity Alert
    if humidity < 30:
        alerts.append({
            'type': 'warning',
            'title': 'Low Humidity - Drought Risk',
            'message': f'Humidity is {humidity}%. Increase irrigation, apply mulch, and monitor soil moisture closely.',
            'icon': 'droplet-slash',
            'timestamp': datetime.now().isoformat()
        })
    
    # Positive alerts
    if ndvi > 0.6:
        alerts.append({
            'type': 'info',
            'title': 'Excellent Vegetation Health',
            'message': f'NDVI is {ndvi:.2f} - excellent! Continue current management practices.',
            'icon': 'check-circle',
            'timestamp': datetime.now().isoformat()
        })
    
    return alerts

# ========================
# AI RECOMMENDATIONS
# ========================

@monitoring_bp.route('/api/ai-recommendations/<int:project_id>')
def get_ai_recommendations(project_id):
    """Get AI-generated recommendations"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, session['user_id']))
        
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Check for existing recent recommendations
        cur.execute('''
            SELECT * FROM ai_recommendations
            WHERE project_id = %s
            AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY priority DESC, created_at DESC
            LIMIT 5
        ''', (project_id,))
        
        existing = cur.fetchall()
        
        if existing:
            # Parse JSON actions
            for rec in existing:
                if rec.get('actions') and isinstance(rec['actions'], str):
                    rec['actions'] = json.loads(rec['actions'])
            
            cur.close()
            return jsonify({
                'success': True,
                'recommendations': existing,
                'source': 'database'
            })
        
        # Generate new recommendations
        recommendations = generate_ai_recommendations(project)
        
        # Save to database with better error handling
        saved_count = 0
        for rec in recommendations:
            try:
                # Ensure all required fields have values
                actions_json = json.dumps(rec.get('actions', []))
                
                cur.execute('''
                    INSERT INTO ai_recommendations
                    (project_id, recommendation_type, title, description, priority, actions, ai_model, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    project_id,
                    rec.get('type', 'general'),
                    rec.get('title', 'Recommendation')[:255],  # Truncate if needed
                    rec.get('description', '')[:1000],  # Truncate if needed
                    rec.get('priority', 'medium'),
                    actions_json,
                    rec.get('ai_model', 'rule_based'),
                    float(rec.get('confidence', 80))
                ))
                saved_count += 1
            except Exception as save_error:
                logger.warning(f"Could not save recommendation '{rec.get('title', 'Unknown')}': {save_error}")
                continue
        
        mysql.connection.commit()
        logger.info(f"✅ Saved {saved_count}/{len(recommendations)} recommendations")
        cur.close()
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'source': 'generated',
            'saved': saved_count
        })
        
    except Exception as e:
        logger.error(f"Error getting AI recommendations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_ai_recommendations(project: Dict) -> List[Dict]:
    """Generate AI-powered recommendations"""
    
    recommendations = []
    
    ndvi = float(project.get('vegetation_index', 0.4))
    degradation = project.get('land_degradation_level', 'moderate')
    soil_ph = float(project.get('soil_ph', 6.5))
    climate_zone = project.get('climate_zone', 'Tropical')
    
    # Try AI-powered recommendations
    if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != 'your_key_here':
        ai_recs = query_ai_for_recommendations(project)
        if ai_recs:
            return ai_recs
    
    # Fallback rule-based recommendations
    
    # Vegetation improvement
    if ndvi < 0.5:
        recommendations.append({
            'type': 'vegetation',
            'title': 'Improve Vegetation Cover',
            'description': 'Your vegetation health needs attention. Focus on establishing dense plant cover to improve soil protection and ecosystem health.',
            'priority': 'high' if ndvi < 0.3 else 'medium',
            'actions': [
                'Plant nitrogen-fixing cover crops immediately',
                'Apply 5-10cm organic mulch around existing plants',
                'Install drip irrigation if not present',
                'Test soil for nutrient deficiencies',
                'Consider agroforestry with fast-growing pioneer species'
            ],
            'ai_model': 'rule_based',
            'confidence': 85
        })
    
    # Soil management
    if soil_ph < 6.0 or soil_ph > 7.5:
        recommendations.append({
            'type': 'soil',
            'title': 'Soil pH Correction Required',
            'description': f'Soil pH of {soil_ph} is outside optimal range (6.0-7.5). Correcting pH will significantly improve nutrient availability and crop performance.',
            'priority': 'high',
            'actions': [
                'Apply agricultural lime at 2-4 tons/ha' if soil_ph < 6.0 else 'Apply elemental sulfur at 100-200 kg/ha',
                'Incorporate organic matter (compost) at 5 tons/ha',
                'Retest pH after 3 months',
                'Split applications to avoid shocking plants',
                'Maintain mulch layer to stabilize pH long-term'
            ],
            'ai_model': 'rule_based',
            'confidence': 90
        })
    
    # Degradation restoration
    if degradation in ['severe', 'critical']:
        recommendations.append({
            'type': 'restoration',
            'title': 'Urgent Land Restoration Protocol',
            'description': 'Land shows significant degradation. Comprehensive restoration strategy needed for recovery.',
            'priority': 'urgent',
            'actions': [
                'Construct contour bunds and terraces to prevent erosion',
                'Establish gabion structures in gullies',
                'Plant fast-growing pioneer trees (Acacia, Grevillea)',
                'Apply biochar at 5-10 tons/ha for soil rehabilitation',
                'Install rainwater harvesting systems',
                'Engage professional land restoration consultant'
            ],
            'ai_model': 'rule_based',
            'confidence': 88
        })
    
    # Seasonal planting advice
    current_month = datetime.now().month
    
    if current_month in [3, 4, 5]:  # Long rains season
        recommendations.append({
            'type': 'seasonal',
            'title': 'Optimal Planting Season - Act Now!',
            'description': 'Long rains season is ideal for planting. Maximize this window for best establishment.',
            'priority': 'high',
            'actions': [
                f'Plant recommended crops for {climate_zone} climate now',
                'Prioritize tree seedlings - they need full season to establish',
                'Prepare 60x60x60cm planting holes with compost',
                'Mulch immediately after planting',
                'Monitor moisture weekly - supplement if rains delayed'
            ],
            'ai_model': 'rule_based',
            'confidence': 95
        })
    elif current_month in [10, 11, 12]:  # Short rains
        recommendations.append({
            'type': 'seasonal',
            'title': 'Secondary Planting Window',
            'description': 'Short rains season - suitable for hardy, drought-resistant species.',
            'priority': 'medium',
            'actions': [
                'Focus on drought-resistant varieties',
                'Prepare irrigation backup system',
                'Apply thick mulch layer (10cm minimum)',
                'Plant in evening to reduce transplant shock',
                'Monitor daily for first 2 weeks'
            ],
            'ai_model': 'rule_based',
            'confidence': 80
        })
    else:  # Dry season
        recommendations.append({
            'type': 'seasonal',
            'title': 'Dry Season Maintenance',
            'description': 'Not recommended for new planting. Focus on maintenance and preparation.',
            'priority': 'low',
            'actions': [
                'Maintain existing plants with supplemental irrigation',
                'Prepare planting sites for next season',
                'Apply compost and organic amendments',
                'Clear invasive species',
                'Plan next season planting strategy'
            ],
            'ai_model': 'rule_based',
            'confidence': 85
        })
    
    # Water management
    if int(project.get('humidity', 60)) < 40:
        recommendations.append({
            'type': 'water',
            'title': 'Water Conservation Critical',
            'description': 'Low humidity indicates water stress risk. Implement water conservation measures immediately.',
            'priority': 'high',
            'actions': [
                'Install drip irrigation system for efficiency',
                'Mulch all bare soil with 10cm organic material',
                'Create water harvesting swales on contours',
                'Reduce tillage to preserve soil moisture',
                'Plant deep-rooted cover crops'
            ],
            'ai_model': 'rule_based',
            'confidence': 87
        })
    
    return recommendations

def query_ai_for_recommendations(project: Dict) -> Optional[List[Dict]]:
    """Query AI for personalized recommendations"""
    try:
        prompt = f"""Provide 3 actionable land restoration recommendations for:

Project Type: {project.get('project_type', 'restoration')}
Climate: {project.get('climate_zone', 'tropical')}
NDVI: {project.get('vegetation_index', 0.4)}
Degradation: {project.get('land_degradation_level', 'moderate')}
Soil pH: {project.get('soil_ph', 6.5)}
Area: {project.get('area_hectares', 10)} hectares

Format each as:
Title: [Brief title]
Priority: [high/medium/low]
Actions: [3-5 specific actions]"""

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        models = ["facebook/bart-large-cnn", "google/flan-t5-base"]
        
        for model in models:
            try:
                url = f"{HUGGINGFACE_BASE_URL}/{model}"
                response = requests.post(
                    url, 
                    headers=headers, 
                    json={
                        "inputs": prompt,
                        "parameters": {"max_new_tokens": 300, "temperature": 0.7},
                        "options": {"wait_for_model": True}
                    }, 
                    timeout=20
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result[0].get('generated_text') or result[0].get('summary_text') if isinstance(result, list) else None
                    
                    if text:
                        parsed = parse_ai_recommendations(text)
                        if parsed:
                            logger.info(f"✅ AI recommendations from {model}")
                            return parsed
                        
            except Exception as e:
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"AI recommendations error: {e}")
        return None

def parse_ai_recommendations(text: str) -> Optional[List[Dict]]:
    """Parse AI-generated recommendations"""
    # This is a simplified parser - in production, use more robust NLP
    recommendations = []
    
    try:
        sections = text.split('\n\n')
        
        for section in sections[:3]:  # Limit to 3 recommendations
            if 'Title:' in section or 'Priority:' in section:
                rec = {
                    'type': 'general',
                    'title': 'AI Recommendation',
                    'description': section[:200],
                    'priority': 'medium',
                    'actions': ['Review AI suggestion', 'Consult with agronomist'],
                    'ai_model': 'huggingface',
                    'confidence': 75
                }
                recommendations.append(rec)
        
        return recommendations if recommendations else None
        
    except:
        return None

# ========================
# SUITABLE PRODUCTS
# ========================

@monitoring_bp.route('/api/suitable-products/<int:project_id>')
def get_suitable_products(project_id):
    """Get suitable agricultural products"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, session['user_id']))
        
        project = cur.fetchone()
        cur.close()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Generate product recommendations
        products = generate_product_recommendations(project)
        
        return jsonify({
            'success': True,
            'products': products
        })
        
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_product_recommendations(project: Dict) -> List[Dict]:
    """Generate product recommendations based on project needs"""
    
    products = []
    
    soil_ph = float(project.get('soil_ph', 6.5))
    degradation = project.get('land_degradation_level', 'moderate')
    ndvi = float(project.get('vegetation_index', 0.4))
    
    # Soil amendments
    if soil_ph < 6.0:
        products.append({
            'name': 'Agricultural Lime (Calcium Carbonate)',
            'category': 'Soil Amendment',
            'description': 'Raises soil pH. Apply 2-4 tons/ha depending on current pH and soil type.',
            'priority': 'high'
        })
    
    if soil_ph > 7.5:
        products.append({
            'name': 'Elemental Sulfur',
            'category': 'Soil Amendment',
            'description': 'Lowers soil pH. Apply 100-200 kg/ha. Effects take 3-6 months.',
            'priority': 'high'
        })
    
    # Organic matter
    products.append({
        'name': 'Composted Manure',
        'category': 'Organic Matter',
        'description': 'Improves soil structure, water retention, and fertility. Apply 5-10 tons/ha annually.',
        'priority': 'high' if ndvi < 0.4 else 'medium'
    })
    
    # Fertilizers
    if ndvi < 0.5:
        products.append({
            'name': 'NPK Fertilizer (17-17-17)',
            'category': 'Fertilizer',
            'description': 'Balanced fertilizer for general crop nutrition. Apply 200-400 kg/ha based on soil test.',
            'priority': 'medium'
        })
    
    # Mulch
    products.append({
        'name': 'Organic Mulch Material',
        'category': 'Mulch',
        'description': 'Grass clippings, straw, or wood chips. Apply 5-10cm layer to conserve moisture and suppress weeds.',
        'priority': 'high'
    })
    
    # Irrigation
    if int(project.get('humidity', 60)) < 50:
        products.append({
            'name': 'Drip Irrigation Kit',
            'category': 'Irrigation',
            'description': 'Water-efficient irrigation system. Reduces water use by 50% compared to flood irrigation.',
            'priority': 'high'
        })
    
    # Seeds
    products.append({
        'name': 'Cover Crop Seeds Mix',
        'category': 'Seeds',
        'description': 'Legume and grass mix for nitrogen fixation and soil improvement. Sow at 20-30 kg/ha.',
        'priority': 'medium'
    })
    
    # Biochar (for severe degradation)
    if degradation in ['severe', 'critical']:
        products.append({
            'name': 'Biochar (Agricultural Grade)',
            'category': 'Soil Conditioner',
            'description': 'Improves soil structure and water retention. Apply 5-10 tons/ha for degraded soils.',
            'priority': 'high'
        })
    
    return products[:6]  # Limit to top 6

# ========================
# CHART DATA
# ========================

@monitoring_bp.route('/api/chart-data/<int:project_id>')
def get_chart_data(project_id):
    """Get data for charts"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        period = int(request.args.get('period', 30))
        
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Verify project ownership
        cur.execute('''
            SELECT * FROM projects 
            WHERE id = %s AND user_id = %s
        ''', (project_id, session['user_id']))
        
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Get monitoring data
        cur.execute('''
            SELECT * FROM monitoring_data
            WHERE project_id = %s
            AND recorded_at > DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY recorded_at ASC
        ''', (project_id, period))
        
        monitoring_data = cur.fetchall()
        cur.close()
        
        # Generate chart data
        if monitoring_data:
            ndvi_data = {
                'labels': [d['recorded_at'].strftime('%b %d') for d in monitoring_data],
                'values': [float(d['ndvi']) for d in monitoring_data]
            }
        else:
            # Generate synthetic data for demonstration
            ndvi_data = generate_synthetic_ndvi_data(period, project)
        
        # Land cover data
        land_cover = generate_land_cover_data(project)
        
        return jsonify({
            'success': True,
            'ndvi_data': ndvi_data,
            'land_cover': land_cover
        })
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_synthetic_ndvi_data(days: int, project: Dict) -> Dict:
    """Generate synthetic NDVI trend data"""
    
    base_ndvi = float(project.get('vegetation_index', 0.4))
    degradation = project.get('land_degradation_level', 'moderate')
    
    # Determine trend based on degradation
    if degradation == 'minimal':
        trend = 0.002  # Improving
    elif degradation == 'moderate':
        trend = 0.001  # Slight improvement
    elif degradation == 'severe':
        trend = -0.001  # Declining
    else:
        trend = -0.002  # Critical decline
    
    labels = []
    values = []
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        labels.append(date.strftime('%b %d'))
        
        # Calculate NDVI with trend and random variation
        ndvi = base_ndvi + (trend * i) + random.uniform(-0.05, 0.05)
        ndvi = max(0.1, min(0.9, ndvi))  # Clamp
        values.append(round(ndvi, 2))
    
    return {'labels': labels, 'values': values}

def generate_land_cover_data(project: Dict) -> Dict:
    """Generate land cover distribution data"""
    
    ndvi = float(project.get('vegetation_index', 0.4))
    degradation = project.get('land_degradation_level', 'moderate')
    
    # Estimate land cover based on NDVI and degradation
    if ndvi > 0.6:
        forest = 40
        grassland = 30
        bare_soil = 10
    elif ndvi > 0.4:
        forest = 25
        grassland = 35
        bare_soil = 20
    else:
        forest = 10
        grassland = 25
        bare_soil = 40
    
    water = 5
    agriculture = 100 - forest - grassland - bare_soil - water
    
    return {
        'labels': ['Forest', 'Grassland', 'Bare Soil', 'Water', 'Agriculture'],
        'values': [forest, grassland, bare_soil, water, agriculture]
    }

# ========================
# MAIN ROUTE
# ========================

@monitoring_bp.route('/')
def monitoring():
    """Render monitoring page"""
    if 'user_id' not in session:
        from flask import redirect, url_for
        return redirect(url_for('main.login'))
    
    return render_template('monitoring.html', user=session)

# ========================
# EXPORT
# ========================

__all__ = [
    'monitoring_bp',
    'init_monitoring'
]

logger.info("✅ Monitoring module loaded with AI capabilities!")