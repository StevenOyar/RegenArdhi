"""
RegenArdhi - Dashboard Module
Handles dashboard routes and data aggregation
"""

import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# MySQL connection (passed from main app)
mysql = None

# ========================
# INITIALIZATION
# ========================

def init_dashboard(app, mysql_instance):
    """Initialize dashboard module with Flask app and MySQL instance"""
    global mysql
    mysql = mysql_instance
    
    print("✅ Dashboard module initialized!")

# ========================
# HELPER FUNCTIONS
# ========================

def get_dashboard_stats(user_id):
    """Get comprehensive dashboard statistics for a user"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get project statistics
        cur.execute('''
            SELECT 
                COUNT(*) as total_projects,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_projects,
                SUM(CASE WHEN status = 'planning' THEN 1 ELSE 0 END) as planning_projects,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_projects,
                SUM(CASE WHEN status = 'paused' THEN 1 ELSE 0 END) as paused_projects,
                SUM(area_hectares) as total_area,
                COUNT(DISTINCT location) as total_locations,
                AVG(vegetation_index) as avg_ndvi,
                AVG(progress_percentage) as avg_progress
            FROM projects
            WHERE user_id = %s
        ''', (user_id,))
        
        stats = cur.fetchone()
        
        # Get month-over-month growth
        cur.execute('''
            SELECT COUNT(*) as new_projects_this_month
            FROM projects
            WHERE user_id = %s
            AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ''', (user_id,))
        
        growth = cur.fetchone()
        
        # Get health score (calculated from monitoring data)
        cur.execute('''
            SELECT 
                AVG(md.ndvi) as avg_ndvi,
                AVG(md.soil_moisture) as avg_soil_moisture,
                AVG(md.canopy_cover) as avg_canopy
            FROM monitoring_data md
            JOIN projects p ON md.project_id = p.id
            WHERE p.user_id = %s
            AND md.recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ''', (user_id,))
        
        health_data = cur.fetchone()
        
        # Calculate overall health score (0-100)
        health_score = calculate_health_score(health_data)
        
        # Get community stats
        cur.execute('''
            SELECT 
                COUNT(DISTINCT cr.id) as total_reports,
                COUNT(DISTINCT CASE WHEN cr.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN cr.id END) as recent_reports
            FROM community_reports cr
            JOIN projects p ON cr.project_id = p.id
            WHERE p.user_id = %s
        ''', (user_id,))
        
        community_stats = cur.fetchone()
        
        cur.close()
        
        # Convert Decimal to float for JSON serialization
        result = {
            'total_projects': stats['total_projects'] or 0,
            'active_projects': stats['active_projects'] or 0,
            'planning_projects': stats['planning_projects'] or 0,
            'completed_projects': stats['completed_projects'] or 0,
            'paused_projects': stats['paused_projects'] or 0,
            'total_area': float(stats['total_area'] or 0),
            'total_locations': stats['total_locations'] or 0,
            'avg_ndvi': float(stats['avg_ndvi'] or 0),
            'avg_progress': float(stats['avg_progress'] or 0),
            'new_projects_this_month': growth['new_projects_this_month'] or 0,
            'health_score': health_score,
            'vegetation_cover': calculate_metric_percentage(health_data, 'avg_ndvi'),
            'soil_quality': calculate_metric_percentage(health_data, 'avg_soil_moisture'),
            'water_retention': calculate_metric_percentage(health_data, 'avg_canopy'),
            'biodiversity': 71,  # Placeholder - calculate from actual data
            'total_reports': community_stats['total_reports'] or 0,
            'recent_reports': community_stats['recent_reports'] or 0,
            'photos_shared': 158,  # Placeholder - implement photo tracking
            'collaborations': 12  # Placeholder - implement collaboration tracking
        }
        
        return result
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        import traceback
        traceback.print_exc()
        return get_default_stats()

def calculate_health_score(health_data):
    """Calculate overall land health score (0-100)"""
    try:
        if not health_data:
            return 78  # Default score
        
        ndvi = float(health_data.get('avg_ndvi') or 0)
        soil_moisture = float(health_data.get('avg_soil_moisture') or 0)
        canopy = float(health_data.get('avg_canopy') or 0)
        
        # Weighted average
        # NDVI: 40%, Soil Moisture: 30%, Canopy Cover: 30%
        if ndvi > 0 or soil_moisture > 0 or canopy > 0:
            score = (ndvi * 100 * 0.4) + (soil_moisture * 0.3) + (canopy * 0.3)
            return min(100, max(0, int(score)))
        
        return 78  # Default score
        
    except Exception as e:
        print(f"Error calculating health score: {e}")
        return 78

def calculate_metric_percentage(health_data, metric):
    """Calculate percentage for a specific metric"""
    try:
        if not health_data:
            return 0
        
        value = float(health_data.get(metric) or 0)
        
        if metric == 'avg_ndvi':
            # NDVI is 0-1, convert to percentage
            return min(100, int(value * 100))
        elif metric == 'avg_soil_moisture':
            # Soil moisture is already percentage
            return min(100, int(value))
        elif metric == 'avg_canopy':
            # Canopy cover is already percentage
            return min(100, int(value))
        
        return 0
        
    except Exception as e:
        print(f"Error calculating metric: {e}")
        return 0

def get_default_stats():
    """Return default stats when no data is available"""
    return {
        'total_projects': 0,
        'active_projects': 0,
        'planning_projects': 0,
        'completed_projects': 0,
        'paused_projects': 0,
        'total_area': 0,
        'total_locations': 0,
        'avg_ndvi': 0,
        'avg_progress': 0,
        'new_projects_this_month': 0,
        'health_score': 0,
        'vegetation_cover': 0,
        'soil_quality': 0,
        'water_retention': 0,
        'biodiversity': 0,
        'total_reports': 0,
        'recent_reports': 0,
        'photos_shared': 0,
        'collaborations': 0
    }

def get_recent_projects(user_id, limit=3):
    """Get recent projects for dashboard display"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT 
                id, name, project_type, area_hectares, status,
                progress_percentage, vegetation_index, land_degradation_level,
                climate_zone, latitude, longitude, created_at
            FROM projects
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        ''', (user_id, limit))
        
        projects = cur.fetchall()
        cur.close()
        
        # Convert data types for JSON serialization
        for project in projects:
            for key, value in project.items():
                if isinstance(value, Decimal):
                    project[key] = float(value)
                elif isinstance(value, datetime):
                    project[key] = value.isoformat()
        
        return projects
        
    except Exception as e:
        print(f"Error getting recent projects: {e}")
        return []

def get_recent_activities(user_id, limit=10):
    """Get recent activities for dashboard feed"""
    try:
        activities = []
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        # Get recent monitoring data updates
        cur.execute('''
            SELECT 
                md.created_at as timestamp,
                'monitoring_update' as type,
                p.name as project_name,
                md.ndvi as value
            FROM monitoring_data md
            JOIN projects p ON md.project_id = p.id
            WHERE p.user_id = %s
            ORDER BY md.created_at DESC
            LIMIT 3
        ''', (user_id,))
        
        monitoring_updates = cur.fetchall()
        for update in monitoring_updates:
            activities.append({
                'type': 'monitoring_update',
                'icon': 'plus',
                'color': 'green',
                'message': f'New monitoring data added to {update["project_name"]}',
                'time': format_relative_time(update['timestamp'])
            })
        
        # Get recent project creations
        cur.execute('''
            SELECT 
                created_at as timestamp,
                name as project_name
            FROM projects
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 2
        ''', (user_id,))
        
        new_projects = cur.fetchall()
        for project in new_projects:
            activities.append({
                'type': 'project_created',
                'icon': 'seedling',
                'color': 'blue',
                'message': f'New project created: {project["project_name"]}',
                'time': format_relative_time(project['timestamp'])
            })
        
        # Get recent community reports
        cur.execute('''
            SELECT 
                cr.created_at as timestamp,
                p.name as project_name,
                COUNT(*) as report_count
            FROM community_reports cr
            JOIN projects p ON cr.project_id = p.id
            WHERE p.user_id = %s
            AND cr.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY p.id, p.name
            ORDER BY cr.created_at DESC
            LIMIT 2
        ''', (user_id,))
        
        reports = cur.fetchall()
        for report in reports:
            activities.append({
                'type': 'community_report',
                'icon': 'users',
                'color': 'orange',
                'message': f'{report["report_count"]} community reports for {report["project_name"]}',
                'time': format_relative_time(report['timestamp'])
            })
        
        cur.close()
        
        # Sort by time and limit
        activities.sort(key=lambda x: x.get('time', ''), reverse=True)
        return activities[:limit]
        
    except Exception as e:
        print(f"Error getting recent activities: {e}")
        return get_default_activities()

def get_default_activities():
    """Return default activities when no data is available"""
    return [
        {
            'type': 'info',
            'icon': 'info-circle',
            'color': 'blue',
            'message': 'Welcome to RegenArdhi! Start by creating your first project.',
            'time': 'just now'
        }
    ]

def format_relative_time(timestamp):
    """Format timestamp to relative time string"""
    try:
        if not timestamp:
            return 'recently'
        
        now = datetime.now()
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        diff = now - timestamp
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} hour{"s" if hours > 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} day{"s" if days > 1 else ""} ago'
        else:
            return timestamp.strftime('%b %d, %Y')
            
    except Exception as e:
        print(f"Error formatting time: {e}")
        return 'recently'

# ========================
# ROUTES
# ========================

@dashboard_bp.route('/')
def dashboard():
    """Main dashboard page"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    try:
        # Get user data from session
        user_data = {
            'id': session.get('user_id'),
            'first_name': session.get('first_name', 'User'),
            'last_name': session.get('last_name', ''),
            'email': session.get('user_email', '')
        }
        
        return render_template('dashboard.html', user=user_data)
        
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', user={'first_name': 'User'})

@dashboard_bp.route('/api/stats')
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        stats = get_dashboard_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch statistics'
        }), 500

@dashboard_bp.route('/api/recent-projects')
def api_recent_projects():
    """API endpoint for recent projects"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        limit = int(request.args.get('limit', 3))
        
        projects = get_recent_projects(user_id, limit)
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        print(f"Error fetching recent projects: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch projects'
        }), 500

@dashboard_bp.route('/api/activities')
def api_recent_activities():
    """API endpoint for recent activities"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        limit = int(request.args.get('limit', 10))
        
        activities = get_recent_activities(user_id, limit)
        
        return jsonify({
            'success': True,
            'activities': activities
        })
        
    except Exception as e:
        print(f"Error fetching activities: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch activities'
        }), 500

@dashboard_bp.route('/api/health-metrics')
def api_health_metrics():
    """API endpoint for land health metrics"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        stats = get_dashboard_stats(user_id)
        
        metrics = {
            'overall_score': stats['health_score'],
            'vegetation_cover': stats['vegetation_cover'],
            'soil_quality': stats['soil_quality'],
            'water_retention': stats['water_retention'],
            'biodiversity': stats['biodiversity']
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        print(f"Error fetching health metrics: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch health metrics'
        }), 500

@dashboard_bp.route('/api/community-stats')
def api_community_stats():
    """API endpoint for community statistics"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        stats = get_dashboard_stats(user_id)
        
        community = {
            'field_reports': stats['total_reports'],
            'photos_shared': stats['photos_shared'],
            'collaborations': stats['collaborations'],
            'recent_reports': stats['recent_reports']
        }
        
        return jsonify({
            'success': True,
            'community': community
        })
        
    except Exception as e:
        print(f"Error fetching community stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch community stats'
        }), 500

@dashboard_bp.route('/api/summary')
def api_dashboard_summary():
    """Complete dashboard summary (all data in one call)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        
        # Get all dashboard data
        stats = get_dashboard_stats(user_id)
        projects = get_recent_projects(user_id, 3)
        activities = get_recent_activities(user_id, 10)
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'recent_projects': projects,
                'activities': activities,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Error fetching dashboard summary: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch dashboard summary'
        }), 500

# ========================
# ERROR HANDLERS
# ========================

@dashboard_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@dashboard_bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('500.html'), 500