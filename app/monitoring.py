import os
import requests
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

load_dotenv()

# Create Blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/monitoring')

# MySQL connection (passed from main app)
mysql = None

# API Keys
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# ========================
# DATABASE INITIALIZATION
# ========================

def init_monitoring(app, mysql_instance):
    """Initialize monitoring module with Flask app and MySQL instance"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            
            # Monitoring data table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Vegetation Metrics
                    ndvi DECIMAL(4, 2),
                    vegetation_health VARCHAR(50),
                    canopy_cover DECIMAL(5, 2),
                    
                    -- Soil Metrics
                    soil_moisture DECIMAL(5, 2),
                    soil_temperature DECIMAL(5, 2),
                    soil_ph DECIMAL(3, 1),
                    erosion_risk VARCHAR(50),
                    
                    -- Climate Data
                    temperature DECIMAL(5, 2),
                    rainfall DECIMAL(10, 2),
                    humidity INT,
                    wind_speed DECIMAL(5, 2),
                    
                    -- Change Detection
                    vegetation_change DECIMAL(5, 2),
                    land_use_change TEXT,
                    degradation_trend VARCHAR(50),
                    
                    -- Alerts
                    alert_level ENUM('none', 'low', 'medium', 'high', 'critical') DEFAULT 'none',
                    alert_message TEXT,
                    
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_project_date (project_id, recorded_at),
                    INDEX idx_alert_level (alert_level)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Community reports table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS community_reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    user_id INT NOT NULL,
                    report_type ENUM('vegetation_loss', 'soil_erosion', 'water_stress', 'pest_disease', 'positive_change') NOT NULL,
                    description TEXT,
                    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    image_url VARCHAR(500),
                    status ENUM('pending', 'verified', 'resolved', 'invalid') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_project_status (project_id, status),
                    INDEX idx_severity (severity)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Restoration actions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS restoration_actions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    action_type VARCHAR(100) NOT NULL,
                    description TEXT,
                    target_area DECIMAL(10, 2),
                    status ENUM('planned', 'in_progress', 'completed', 'cancelled') DEFAULT 'planned',
                    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
                    start_date DATE,
                    end_date DATE,
                    completion_percentage INT DEFAULT 0,
                    cost_estimate DECIMAL(12, 2),
                    actual_cost DECIMAL(12, 2),
                    assigned_to VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_project_status (project_id, status),
                    INDEX idx_priority (priority)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            mysql.connection.commit()
            cur.close()
            print("✅ Monitoring tables initialized successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing monitoring tables: {e}")
            import traceback
            traceback.print_exc()

# ========================
# MONITORING FUNCTIONS
# ========================

def calculate_vegetation_health(ndvi):
    """Calculate vegetation health category from NDVI"""
    if ndvi >= 0.6:
        return 'excellent'
    elif ndvi >= 0.4:
        return 'good'
    elif ndvi >= 0.2:
        return 'fair'
    elif ndvi >= 0.1:
        return 'poor'
    else:
        return 'critical'

def assess_erosion_risk(slope, vegetation_cover, rainfall):
    """Assess soil erosion risk"""
    risk_score = 0
    
    # Slope factor
    if slope > 30:
        risk_score += 3
    elif slope > 15:
        risk_score += 2
    elif slope > 5:
        risk_score += 1
    
    # Vegetation cover factor
    if vegetation_cover < 20:
        risk_score += 3
    elif vegetation_cover < 40:
        risk_score += 2
    elif vegetation_cover < 60:
        risk_score += 1
    
    # Rainfall factor
    if rainfall > 1500:
        risk_score += 2
    elif rainfall > 1000:
        risk_score += 1
    
    if risk_score >= 6:
        return 'critical'
    elif risk_score >= 4:
        return 'high'
    elif risk_score >= 2:
        return 'medium'
    else:
        return 'low'

def get_real_climate_data(latitude, longitude):
    """Fetch real climate data from OpenWeather API"""
    try:
        if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == 'your_key_here':
            return get_fallback_climate_data(latitude, longitude)
        
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
            return get_fallback_climate_data(latitude, longitude)
            
    except Exception as e:
        print(f"Error fetching climate data: {e}")
        return get_fallback_climate_data(latitude, longitude)

def get_fallback_climate_data(latitude, longitude):
    """Fallback climate estimation"""
    abs_lat = abs(latitude)
    base_temp = 30 - (abs_lat * 0.6)
    
    if abs_lat < 23.5:
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

def calculate_ndvi_estimate(latitude, longitude, climate_data):
    """Estimate NDVI based on location and climate"""
    try:
        abs_lat = abs(latitude)
        temp = climate_data.get('temperature', 20)
        humidity = climate_data.get('humidity', 50)
        
        # Base NDVI calculation
        if abs_lat < 10:
            base_ndvi = 0.6
        elif abs_lat < 23.5:
            base_ndvi = 0.5
        elif abs_lat < 35:
            base_ndvi = 0.4
        elif abs_lat < 50:
            base_ndvi = 0.35
        else:
            base_ndvi = 0.2
        
        # Adjust for temperature and humidity
        if temp > 25 and humidity > 60:
            base_ndvi += 0.1
        elif temp < 10 or humidity < 30:
            base_ndvi -= 0.15
        
        # Add variation
        variation = (abs(longitude) % 10) * 0.02
        ndvi = max(0.0, min(1.0, base_ndvi + variation - 0.1))
        
        return round(ndvi, 2)
        
    except Exception as e:
        print(f"Error calculating NDVI: {e}")
        return 0.4

def generate_monitoring_data(project):
    """Generate comprehensive monitoring data for a project"""
    try:
        # Get current climate
        climate = get_real_climate_data(
            float(project['latitude']),
            float(project['longitude'])
        )
        
        # Calculate NDVI
        ndvi = calculate_ndvi_estimate(
            float(project['latitude']),
            float(project['longitude']),
            climate
        )
        
        # Vegetation health
        veg_health = calculate_vegetation_health(ndvi)
        
        # Estimate canopy cover from NDVI
        canopy_cover = min(100, max(0, (ndvi - 0.1) * 111))
        
        # Soil moisture estimate
        soil_moisture = min(100, climate['humidity'] * 0.7)
        
        # Erosion risk
        erosion_risk = assess_erosion_risk(
            5,  # Moderate slope
            canopy_cover,
            project.get('annual_rainfall', 800)
        )
        
        # Vegetation change
        baseline_ndvi = project.get('vegetation_index', 0.4)
        if baseline_ndvi and baseline_ndvi > 0:
            veg_change = ((ndvi - float(baseline_ndvi)) / float(baseline_ndvi)) * 100
        else:
            veg_change = 0
        
        # Determine alert level
        alert_level = 'none'
        alert_message = None
        
        if ndvi < 0.2:
            alert_level = 'critical'
            alert_message = 'Critical vegetation loss detected'
        elif veg_change < -20:
            alert_level = 'high'
            alert_message = 'Significant vegetation decline detected'
        elif erosion_risk in ['high', 'critical']:
            alert_level = 'high'
            alert_message = f'{erosion_risk.title()} erosion risk detected'
        elif ndvi < 0.35:
            alert_level = 'medium'
            alert_message = 'Vegetation health below optimal'
        
        return {
            'ndvi': ndvi,
            'vegetation_health': veg_health,
            'canopy_cover': round(canopy_cover, 2),
            'soil_moisture': round(soil_moisture, 2),
            'soil_temperature': climate['temperature'],
            'soil_ph': float(project.get('soil_ph', 6.5)),
            'erosion_risk': erosion_risk,
            'temperature': climate['temperature'],
            'rainfall': 0,  # Current rainfall
            'humidity': climate['humidity'],
            'wind_speed': climate.get('wind_speed', 0),
            'vegetation_change': round(veg_change, 2),
            'land_use_change': None,
            'degradation_trend': 'improving' if veg_change > 0 else 'declining',
            'alert_level': alert_level,
            'alert_message': alert_message
        }
        
    except Exception as e:
        print(f"Error generating monitoring data: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========================
# API ROUTES
# ========================

@monitoring_bp.route('/api/project/<int:project_id>/data')
def get_monitoring_data(project_id):
    """Get latest monitoring data for a project"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get latest monitoring data
        cur.execute('''
            SELECT * FROM monitoring_data
            WHERE project_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
        ''', (project_id,))
        
        latest = cur.fetchone()
        
        # Get historical data (last 30 days)
        cur.execute('''
            SELECT * FROM monitoring_data
            WHERE project_id = %s
            AND recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY recorded_at ASC
        ''', (project_id,))
        
        history = cur.fetchall()
        
        cur.close()
        
        # Convert Decimal to float
        if latest:
            for key, value in latest.items():
                if value is not None and hasattr(value, 'real'):
                    latest[key] = float(value)
                elif isinstance(value, datetime):
                    latest[key] = value.isoformat()
        
        for record in history:
            for key, value in record.items():
                if value is not None and hasattr(value, 'real'):
                    record[key] = float(value)
                elif isinstance(value, datetime):
                    record[key] = value.isoformat()
        
        return jsonify({
            'success': True,
            'latest': latest,
            'history': history
        })
        
    except Exception as e:
        print(f"Error fetching monitoring data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/project/<int:project_id>/update', methods=['POST'])
def update_monitoring_data(project_id):
    """Update monitoring data for a project"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get project
        cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Generate monitoring data
        monitoring = generate_monitoring_data(project)
        
        if not monitoring:
            cur.close()
            return jsonify({'success': False, 'error': 'Failed to generate monitoring data'}), 500
        
        # Insert monitoring record
        cur.execute('''
            INSERT INTO monitoring_data
            (project_id, ndvi, vegetation_health, canopy_cover, soil_moisture,
             soil_temperature, soil_ph, erosion_risk, temperature, rainfall,
             humidity, wind_speed, vegetation_change, degradation_trend,
             alert_level, alert_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            project_id,
            monitoring['ndvi'],
            monitoring['vegetation_health'],
            monitoring['canopy_cover'],
            monitoring['soil_moisture'],
            monitoring['soil_temperature'],
            monitoring['soil_ph'],
            monitoring['erosion_risk'],
            monitoring['temperature'],
            monitoring['rainfall'],
            monitoring['humidity'],
            monitoring['wind_speed'],
            monitoring['vegetation_change'],
            monitoring['degradation_trend'],
            monitoring['alert_level'],
            monitoring['alert_message']
        ))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True, 'data': monitoring})
        
    except Exception as e:
        print(f"Error updating monitoring data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/project/<int:project_id>/reports')
def get_community_reports(project_id):
    """Get community reports for a project"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT cr.*, u.first_name, u.last_name
            FROM community_reports cr
            JOIN users u ON cr.user_id = u.id
            WHERE cr.project_id = %s
            ORDER BY cr.created_at DESC
        ''', (project_id,))
        
        reports = cur.fetchall()
        cur.close()
        
        # Convert dates and decimals
        for report in reports:
            if report.get('created_at'):
                report['created_at'] = str(report['created_at'])
            if report.get('updated_at'):
                report['updated_at'] = str(report['updated_at'])
            if report.get('latitude'):
                report['latitude'] = float(report['latitude'])
            if report.get('longitude'):
                report['longitude'] = float(report['longitude'])
        
        return jsonify({'success': True, 'reports': reports})
        
    except Exception as e:
        print(f"Error fetching community reports: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/project/<int:project_id>/report', methods=['POST'])
def submit_community_report(project_id):
    """Submit a community report"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            INSERT INTO community_reports
            (project_id, user_id, report_type, description, severity,
             latitude, longitude, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            project_id,
            user_id,
            data.get('report_type'),
            data.get('description'),
            data.get('severity', 'medium'),
            data.get('latitude'),
            data.get('longitude'),
            data.get('image_url')
        ))
        
        mysql.connection.commit()
        report_id = cur.lastrowid
        cur.close()
        
        return jsonify({'success': True, 'report_id': report_id})
        
    except Exception as e:
        print(f"Error submitting report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/project/<int:project_id>/actions')
def get_restoration_actions(project_id):
    """Get restoration actions for a project"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT * FROM restoration_actions
            WHERE project_id = %s
            ORDER BY priority DESC, created_at DESC
        ''', (project_id,))
        
        actions = cur.fetchall()
        cur.close()
        
        # Convert data types
        for action in actions:
            for key, value in action.items():
                if value is not None and hasattr(value, 'real'):
                    action[key] = float(value)
                elif isinstance(value, datetime):
                    action[key] = str(value)
        
        return jsonify({'success': True, 'actions': actions})
        
    except Exception as e:
        print(f"Error fetching restoration actions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/project/<int:project_id>/action', methods=['POST'])
def add_restoration_action(project_id):
    """Add a restoration action"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            INSERT INTO restoration_actions
            (project_id, action_type, description, target_area, status,
             priority, start_date, end_date, cost_estimate, assigned_to, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            project_id,
            data.get('action_type'),
            data.get('description'),
            data.get('target_area'),
            data.get('status', 'planned'),
            data.get('priority', 'medium'),
            data.get('start_date'),
            data.get('end_date'),
            data.get('cost_estimate'),
            data.get('assigned_to'),
            data.get('notes')
        ))
        
        mysql.connection.commit()
        action_id = cur.lastrowid
        cur.close()
        
        return jsonify({'success': True, 'action_id': action_id})
        
    except Exception as e:
        print(f"Error adding restoration action: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================
# MAIN ROUTES
# ========================

@monitoring_bp.route('/')
def monitoring_dashboard():
    """Main monitoring dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    return render_template('monitoring.html', user=session)

@monitoring_bp.route('/project/<int:project_id>')
def project_monitoring(project_id):
    """Individual project monitoring page"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cur.fetchone()
        cur.close()
        
        if not project:
            return render_template('404.html'), 404
        
        return render_template('project_monitoring.html', project=project, user=session)
        
    except Exception as e:
        print(f"Error loading project monitoring: {e}")
        return render_template('404.html'), 404
    
    
    
def generate_historical_data(project_id, days=30):
    """Generate historical monitoring data for a project"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get project
        cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cur.fetchone()
        
        if not project:
            return False
        
        # Generate data for past X days
        for i in range(days, 0, -1):
            # Calculate date
            date = datetime.now() - timedelta(days=i)
            
            # Generate monitoring data
            monitoring = generate_monitoring_data(project)
            
            # Add some variation over time (simulate improvement)
            progress_factor = (days - i) / days  # 0 to 1
            monitoring['ndvi'] = max(0.1, min(1.0, 
                monitoring['ndvi'] * (0.8 + progress_factor * 0.4)))
            
            # Insert with custom timestamp
            cur.execute('''
                INSERT INTO monitoring_data
                (project_id, ndvi, vegetation_health, canopy_cover, 
                 soil_moisture, temperature, recorded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                project_id,
                monitoring['ndvi'],
                monitoring['vegetation_health'],
                monitoring['canopy_cover'],
                monitoring['soil_moisture'],
                monitoring['temperature'],
                date
            ))
        
        mysql.connection.commit()
        cur.close()
        return True
        
    except Exception as e:
        print(f"Error generating historical data: {e}")
        return False
@monitoring_bp.route('/api/project/<int:project_id>/generate-history', methods=['POST'])
def generate_history(project_id):
    """Generate historical data for a project"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        success = generate_historical_data(project_id, days)
        
        if success:
            return jsonify({'success': True, 'message': f'Generated {days} days of history'})
        else:
            return jsonify({'success': False, 'error': 'Failed to generate history'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500