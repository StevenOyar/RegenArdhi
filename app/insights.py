import os
import requests
import json
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from dotenv import load_dotenv
import numpy as np
from collections import defaultdict

load_dotenv()


from app.api_integrations import NASAPowerAPI, OpenWeatherAPI, LandAnalysisService


# Create Blueprint
insights_bp = Blueprint('insights', __name__, url_prefix='/insights')

# MySQL connection (passed from main app)
mysql = None

# API Keys
NASA_POWER_API_KEY = os.getenv('NASA_POWER_API_KEY', 'DEMO_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

# ========================
# DATABASE INITIALIZATION
# ========================

def init_insights(app, mysql_instance):
    """Initialize insights module with Flask app and MySQL instance"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            
            # AI insights cache table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS ai_insights (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    insight_type VARCHAR(100) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    confidence_score DECIMAL(5, 2),
                    data_sources JSON,
                    recommendations JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_project_type (project_id, insight_type),
                    INDEX idx_expires (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Chat history table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    project_id INT,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    context JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
                    INDEX idx_user_project (user_id, project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            mysql.connection.commit()
            cur.close()
            print("✅ Insights tables initialized successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing insights tables: {e}")
            import traceback
            traceback.print_exc()

# ========================
# NASA POWER API INTEGRATION
# ========================

def get_nasa_power_data(latitude, longitude, start_date, end_date):
    """
    Fetch climate data from NASA POWER API
    Free API providing solar and meteorological data
    """
    try:
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        
        params = {
            'parameters': 'T2M,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN',
            'community': 'AG',
            'longitude': longitude,
            'latitude': latitude,
            'start': start_date.strftime('%Y%m%d'),
            'end': end_date.strftime('%Y%m%d'),
            'format': 'JSON'
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return process_nasa_power_data(data)
        else:
            print(f"NASA POWER API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error fetching NASA POWER data: {e}")
        return None

def process_nasa_power_data(raw_data):
    """Process NASA POWER API response"""
    try:
        parameters = raw_data.get('properties', {}).get('parameter', {})
        
        # Extract data arrays
        temps = list(parameters.get('T2M', {}).values())
        rainfall = list(parameters.get('PRECTOTCORR', {}).values())
        humidity = list(parameters.get('RH2M', {}).values())
        wind_speed = list(parameters.get('WS2M', {}).values())
        solar_rad = list(parameters.get('ALLSKY_SFC_SW_DWN', {}).values())
        
        # Calculate statistics
        return {
            'temperature': {
                'avg': np.mean(temps) if temps else 0,
                'min': np.min(temps) if temps else 0,
                'max': np.max(temps) if temps else 0,
                'trend': calculate_trend(temps)
            },
            'rainfall': {
                'total': np.sum(rainfall) if rainfall else 0,
                'avg_daily': np.mean(rainfall) if rainfall else 0,
                'days_with_rain': sum(1 for r in rainfall if r > 0)
            },
            'humidity': {
                'avg': np.mean(humidity) if humidity else 0
            },
            'wind_speed': {
                'avg': np.mean(wind_speed) if wind_speed else 0
            },
            'solar_radiation': {
                'avg': np.mean(solar_rad) if solar_rad else 0
            },
            'raw_data': {
                'dates': list(parameters.get('T2M', {}).keys()),
                'temperature': temps,
                'rainfall': rainfall,
                'humidity': humidity
            }
        }
        
    except Exception as e:
        print(f"Error processing NASA data: {e}")
        return None

# ========================
# VEGETATION ANALYSIS
# ========================

# FIX for insights.py
# Replace the calculate_ndvi_trend function (around line 241)

def calculate_ndvi_trend(project_id, days=90):
    """Calculate NDVI trend from monitoring data - FIXED VERSION"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # FIX: Use 'ndvi' instead of 'vegetation_index'
        cur.execute('''
            SELECT ndvi, recorded_at
            FROM monitoring_data
            WHERE project_id = %s
            AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            AND ndvi IS NOT NULL
            ORDER BY recorded_at ASC
        ''', (project_id, days))
        
        records = cur.fetchall()
        cur.close()
        
        if not records:
            print(f"⚠️ No NDVI data found for project {project_id}")
            return None
        
        ndvi_values = [float(r['ndvi']) for r in records if r['ndvi']]
        dates = [r['recorded_at'].strftime('%Y-%m-%d') for r in records]
        
        if len(ndvi_values) < 2:
            print(f"⚠️ Insufficient NDVI data points: {len(ndvi_values)}")
            return None
        
        return {
            'current': ndvi_values[-1],
            'previous': ndvi_values[0],
            'change': ndvi_values[-1] - ndvi_values[0],
            'change_percent': ((ndvi_values[-1] - ndvi_values[0]) / ndvi_values[0] * 100) if ndvi_values[0] > 0 else 0,
            'trend': calculate_trend(ndvi_values),
            'values': ndvi_values,
            'dates': dates,
            'avg': np.mean(ndvi_values),
            'volatility': np.std(ndvi_values)
        }
        
    except Exception as e:
        print(f"Error calculating NDVI trend: {e}")
        import traceback
        traceback.print_exc()
        return None
# ========================
# AI INSIGHTS GENERATION
# ========================

def generate_vegetation_insights(project, ndvi_data, climate_data):
    """Generate AI insights for vegetation health"""
    insights = []
    
    if not ndvi_data:
        return insights
    
    current_ndvi = ndvi_data['current']
    trend = ndvi_data['trend']
    change_percent = ndvi_data['change_percent']
    
    # Vegetation Health Analysis
    if current_ndvi > 0.6:
        insights.append({
            'type': 'positive',
            'category': 'vegetation',
            'title': 'Excellent Vegetation Health',
            'description': f'Current NDVI of {current_ndvi:.2f} indicates dense, healthy vegetation cover. Your restoration efforts are showing strong results.',
            'confidence': 92,
            'recommendations': [
                'Continue current management practices',
                'Monitor for pest and disease',
                'Consider expanding restoration to adjacent areas'
            ]
        })
    elif current_ndvi < 0.3:
        insights.append({
            'type': 'critical',
            'category': 'vegetation',
            'title': 'Critical Vegetation Loss',
            'description': f'NDVI of {current_ndvi:.2f} indicates severe vegetation stress or loss. Immediate intervention required.',
            'confidence': 88,
            'recommendations': [
                'Conduct immediate site assessment',
                'Implement emergency reforestation',
                'Apply soil conservation measures',
                'Consider drought-resistant species'
            ]
        })
    
    # Trend Analysis
    if trend == 'improving' and change_percent > 10:
        insights.append({
            'type': 'positive',
            'category': 'trend',
            'title': 'Strong Recovery Trend',
            'description': f'Vegetation index has improved by {change_percent:.1f}% over the monitoring period. Ecosystem is recovering well.',
            'confidence': 85,
            'recommendations': [
                'Maintain current restoration activities',
                'Document successful practices',
                'Share learnings with community'
            ]
        })
    elif trend == 'declining' and change_percent < -10:
        insights.append({
            'type': 'warning',
            'category': 'trend',
            'title': 'Declining Vegetation Trend',
            'description': f'Vegetation health has declined by {abs(change_percent):.1f}%. Investigation needed to identify causes.',
            'confidence': 87,
            'recommendations': [
                'Investigate decline causes',
                'Increase monitoring frequency',
                'Review and adjust management plan',
                'Check for environmental stressors'
            ]
        })
    
    # Climate Impact
    if climate_data:
        rainfall_total = climate_data.get('rainfall', {}).get('total', 0)
        avg_temp = climate_data.get('temperature', {}).get('avg', 0)
        
        if rainfall_total < 200 and avg_temp > 30:
            insights.append({
                'type': 'warning',
                'category': 'climate',
                'title': 'Drought Stress Detected',
                'description': f'Low rainfall ({rainfall_total:.0f}mm) combined with high temperatures ({avg_temp:.1f}°C) increasing drought risk.',
                'confidence': 83,
                'recommendations': [
                    'Implement water conservation techniques',
                    'Install rainwater harvesting systems',
                    'Use mulching to retain soil moisture',
                    'Consider drought-resistant species'
                ]
            })
    
    return insights

def generate_soil_insights(project, monitoring_data):
    """Generate AI insights for soil health"""
    insights = []
    
    if not monitoring_data:
        return insights
    
    soil_moisture = monitoring_data.get('soil_moisture', 0)
    soil_ph = monitoring_data.get('soil_ph', 7.0)
    erosion_risk = monitoring_data.get('erosion_risk', 'medium')
    
    # Soil Moisture Analysis
    if soil_moisture < 20:
        insights.append({
            'type': 'warning',
            'category': 'soil',
            'title': 'Low Soil Moisture',
            'description': f'Soil moisture at {soil_moisture}% is below optimal levels. Plants may experience water stress.',
            'confidence': 85,
            'recommendations': [
                'Increase irrigation frequency',
                'Apply organic mulch',
                'Consider drip irrigation',
                'Monitor daily until moisture improves'
            ]
        })
    elif soil_moisture > 80:
        insights.append({
            'type': 'info',
            'category': 'soil',
            'title': 'High Soil Moisture',
            'description': f'Soil moisture at {soil_moisture}% is very high. Monitor for waterlogging or drainage issues.',
            'confidence': 78,
            'recommendations': [
                'Check drainage systems',
                'Reduce irrigation if applicable',
                'Monitor for root diseases',
                'Consider drainage improvement'
            ]
        })
    
    # pH Analysis
    if soil_ph < 5.5:
        insights.append({
            'type': 'warning',
            'category': 'soil',
            'title': 'Acidic Soil Detected',
            'description': f'Soil pH of {soil_ph} is too acidic. This may limit nutrient availability and plant growth.',
            'confidence': 90,
            'recommendations': [
                'Apply agricultural lime',
                'Use wood ash amendments',
                'Choose acid-tolerant species',
                'Retest pH after amendments'
            ]
        })
    elif soil_ph > 8.5:
        insights.append({
            'type': 'warning',
            'category': 'soil',
            'title': 'Alkaline Soil Detected',
            'description': f'Soil pH of {soil_ph} is too alkaline. Iron and other nutrients may become unavailable.',
            'confidence': 88,
            'recommendations': [
                'Apply sulfur or organic matter',
                'Use acidifying fertilizers',
                'Choose alkaline-tolerant species',
                'Monitor nutrient deficiencies'
            ]
        })
    
    # Erosion Risk
    if erosion_risk in ['high', 'critical']:
        insights.append({
            'type': 'critical',
            'category': 'soil',
            'title': f'{erosion_risk.title()} Erosion Risk',
            'description': 'Soil erosion risk is elevated. Immediate soil conservation measures recommended.',
            'confidence': 86,
            'recommendations': [
                'Implement contour farming',
                'Build terraces or bunds',
                'Plant cover crops',
                'Install erosion control structures',
                'Increase vegetation cover'
            ]
        })
    
    return insights

def generate_seasonal_insights(project, current_month):
    """Generate seasonal recommendations"""
    insights = []
    
    # Kenya's main seasons
    if current_month in [3, 4, 5]:  # Long rains (March-May)
        insights.append({
            'type': 'positive',
            'category': 'seasonal',
            'title': 'Optimal Planting Season',
            'description': 'Long rains season is ideal for tree planting and establishing vegetation. Maximize restoration efforts now.',
            'confidence': 95,
            'recommendations': [
                'Accelerate tree planting activities',
                'Prepare seedlings in advance',
                'Focus on indigenous species',
                'Establish soil conservation structures',
                'Plan for 6-8 weeks of optimal conditions'
            ]
        })
    elif current_month in [10, 11, 12]:  # Short rains (Oct-Dec)
        insights.append({
            'type': 'positive',
            'category': 'seasonal',
            'title': 'Secondary Planting Window',
            'description': 'Short rains provide another opportunity for planting. Focus on hardy species.',
            'confidence': 85,
            'recommendations': [
                'Plant drought-resistant species',
                'Supplement with irrigation if needed',
                'Apply mulch for moisture retention',
                'Monitor seedling establishment closely'
            ]
        })
    elif current_month in [1, 2]:  # Dry season
        insights.append({
            'type': 'info',
            'category': 'seasonal',
            'title': 'Dry Season Management',
            'description': 'Dry season requires careful water management and protection of established vegetation.',
            'confidence': 88,
            'recommendations': [
                'Focus on watering established plants',
                'Apply mulch to conserve moisture',
                'Avoid planting new seedlings',
                'Monitor for drought stress',
                'Prepare for next planting season'
            ]
        })
    
    return insights

# ========================
# COMPREHENSIVE INSIGHTS
# ========================

def generate_comprehensive_insights(project_id):
    """Generate all insights for a project"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get project details
        cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return []
        
        # Get latest monitoring data
        cur.execute('''
            SELECT * FROM monitoring_data
            WHERE project_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
        ''', (project_id,))
        monitoring_data = cur.fetchone()
        
        cur.close()
        
        # Calculate NDVI trend
        ndvi_data = calculate_ndvi_trend(project_id, days=90)
        
        # Fetch NASA climate data (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        climate_data = get_nasa_power_data(
            float(project['latitude']),
            float(project['longitude']),
            start_date,
            end_date
        )
        
        # Generate insights
        all_insights = []
        
        # Vegetation insights
        veg_insights = generate_vegetation_insights(project, ndvi_data, climate_data)
        all_insights.extend(veg_insights)
        
        # Soil insights
        soil_insights = generate_soil_insights(project, monitoring_data)
        all_insights.extend(soil_insights)
        
        # Seasonal insights
        seasonal_insights = generate_seasonal_insights(project, datetime.now().month)
        all_insights.extend(seasonal_insights)
        
        # Sort by confidence and category
        all_insights.sort(key=lambda x: (-x['confidence'], x['type']))
        
        return all_insights
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        return []

# ========================
# ANALYTICS DATA
# ========================

def get_analytics_data(project_id, period='30d'):
    """Get comprehensive analytics data for charts"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Determine date range
        days = int(period.replace('d', ''))
        
        # NDVI trend
        cur.execute('''
            SELECT DATE(recorded_at) as date, 
                   AVG(ndvi) as avg_ndvi,
                   AVG(canopy_cover) as avg_canopy
            FROM monitoring_data
            WHERE project_id = %s
            AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(recorded_at)
            ORDER BY date ASC
        ''', (project_id, days))
        
        ndvi_trend = cur.fetchall()
        
        # Climate data
        cur.execute('''
            SELECT DATE(recorded_at) as date,
                   AVG(temperature) as avg_temp,
                   SUM(rainfall) as total_rainfall,
                   AVG(humidity) as avg_humidity
            FROM monitoring_data
            WHERE project_id = %s
            AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(recorded_at)
            ORDER BY date ASC
        ''', (project_id, days))
        
        climate_trend = cur.fetchall()
        
        # Soil health
        cur.execute('''
            SELECT DATE(recorded_at) as date,
                   AVG(soil_moisture) as avg_moisture,
                   AVG(soil_ph) as avg_ph
            FROM monitoring_data
            WHERE project_id = %s
            AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(recorded_at)
            ORDER BY date ASC
        ''', (project_id, days))
        
        soil_trend = cur.fetchall()
        
        cur.close()
        
        # Convert to JSON-serializable format
        return {
            'ndvi': [
                {
                    'date': str(r['date']),
                    'ndvi': float(r['avg_ndvi']) if r['avg_ndvi'] else 0,
                    'canopy': float(r['avg_canopy']) if r['avg_canopy'] else 0
                }
                for r in ndvi_trend
            ],
            'climate': [
                {
                    'date': str(r['date']),
                    'temperature': float(r['avg_temp']) if r['avg_temp'] else 0,
                    'rainfall': float(r['total_rainfall']) if r['total_rainfall'] else 0,
                    'humidity': float(r['avg_humidity']) if r['avg_humidity'] else 0
                }
                for r in climate_trend
            ],
            'soil': [
                {
                    'date': str(r['date']),
                    'moisture': float(r['avg_moisture']) if r['avg_moisture'] else 0,
                    'ph': float(r['avg_ph']) if r['avg_ph'] else 0
                }
                for r in soil_trend
            ]
        }
        
    except Exception as e:
        print(f"Error getting analytics data: {e}")
        return {'ndvi': [], 'climate': [], 'soil': []}

# ========================
# API ROUTES
# ========================

@insights_bp.route('/')
def insights_dashboard():
    """Main insights dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    return render_template('insights.html', user=session)

@insights_bp.route('/api/project/<int:project_id>/insights')
def get_project_insights(project_id):
    """Get AI insights for a project"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        insights = generate_comprehensive_insights(project_id)
        
        return jsonify({
            'success': True,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error getting insights: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@insights_bp.route('/api/project/<int:project_id>/analytics')
def get_project_analytics(project_id):
    """Get analytics data for charts"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        period = request.args.get('period', '30d')
        analytics = get_analytics_data(project_id, period)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        print(f"Error getting analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================
# HELPER FUNCTIONS
# ========================

def calculate_trend(values):
    """Calculate trend direction from array of values"""
    if not values or len(values) < 2:
        return 'stable'
    
    # Simple linear regression
    n = len(values)
    x = list(range(n))
    y = values
    
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return 'stable'
    
    slope = numerator / denominator
    
    if slope > 0.01:
        return 'improving'
    elif slope < -0.01:
        return 'declining'
    else:
        return 'stable'
    
    


def get_real_time_analytics(project_id, period='30d'):
    """Get real-time analytics with API data"""
    try:
        # ... existing code to get project ...
        
        # Get real-time climate data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(period.replace('d', '')))
        
        climate_data = NASAPowerAPI.get_climate_data(
            project['latitude'],
            project['longitude'],
            start_date,
            end_date
        )
        
        # Merge with database monitoring data
        # ... rest of your code ...
        
    except Exception as e:
        print(f"Error getting real-time analytics: {e}")
        # Fallback to database-only data


# Add this to insights.py temporarily to test if the blueprint is working

@insights_bp.route('/test')
def test_route():
    """Test route to verify blueprint is working"""
    return jsonify({
        'success': True,
        'message': 'Insights blueprint is working!',
        'routes': [str(rule) for rule in insights_bp.url_map.iter_rules()] if hasattr(insights_bp, 'url_map') else []
    })


