"""
RegenArdhi - AI-Powered Land Restoration Platform
Main Application Entry Point
"""

import os
from flask import Flask, jsonify
from flask_mail import Mail
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# ===============================
#  CREATE FLASK APP
# ===============================
app = Flask(__name__)

# ===============================
#  BASIC CONFIGURATION
# ===============================
app.secret_key = os.getenv("SECRET_KEY", "dev-key-please-change-this-in-production")

app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# ===============================
#  DATABASE CONFIGURATION
# ===============================
app.config.update(
    MYSQL_HOST=os.getenv("MYSQL_HOST", "localhost"),
    MYSQL_USER=os.getenv("MYSQL_USER", "root"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", ""),
    MYSQL_DB=os.getenv("MYSQL_DB", "regenardhi_db"),
    MYSQL_PORT=int(os.getenv("MYSQL_PORT", 3306)),
    MYSQL_CURSORCLASS='DictCursor'
)

# ===============================
#  EMAIL CONFIGURATION
# ===============================
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_SENDER_EMAIL"),
)

# ===============================
#  INITIALIZE EXTENSIONS
# ===============================
mail = Mail(app)
mysql = MySQL(app)

print("\n" + "="*80)
print("🌿 REGENARDHI - INITIALIZING")
print("="*80)

# ===============================
#  INITIALIZE DATABASE TABLES
# ===============================
with app.app_context():
    try:
        cur = mysql.connection.cursor()

        # Users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                age INT NOT NULL,
                location VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                reset_token VARCHAR(255) DEFAULT NULL,
                reset_token_expiry DATETIME DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_reset_token (reset_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        mysql.connection.commit()
        cur.close()
        print("✅ Users table initialized")

    except Exception as e:
        print(f"❌ Error initializing users table: {e}")

# ===============================
#  REGISTER BLUEPRINTS
# ===============================

# 1. NOTIFICATIONS MODULE (First - others depend on it)
try:
    from app.notifications import notifications_bp, init_notifications
    init_notifications(app, mysql)
    app.register_blueprint(notifications_bp)
    print("✅ Notifications module loaded")
except Exception as e:
    print(f"❌ Failed to load Notifications: {e}")
    import traceback
    traceback.print_exc()

# 2. PROJECTS MODULE
try:
    from app.projects import projects_bp, init_projects
    init_projects(app, mysql)
    app.register_blueprint(projects_bp)
    print("✅ Projects module loaded")
except Exception as e:
    print(f"❌ Failed to load Projects: {e}")
    import traceback
    traceback.print_exc()

# 3. MONITORING MODULE
try:
    from app.monitoring import monitoring_bp, init_monitoring
    init_monitoring(app, mysql)
    app.register_blueprint(monitoring_bp)
    print("✅ Monitoring module loaded")
except Exception as e:
    print(f"❌ Failed to load Monitoring: {e}")
    import traceback
    traceback.print_exc()

# 4. INSIGHTS MODULE
try:
    from app.insights import insights_bp, init_insights
    init_insights(app, mysql)
    app.register_blueprint(insights_bp)
    print("✅ Insights module loaded")
except Exception as e:
    print(f"❌ Failed to load Insights: {e}")
    import traceback
    traceback.print_exc()

# 5. CHAT MODULE
try:
    from app.chat import chat_bp, init_chat
    init_chat(app, mysql)
    app.register_blueprint(chat_bp)
    print("✅ Chat module loaded")
except Exception as e:
    print(f"❌ Failed to load Chat: {e}")
    import traceback
    traceback.print_exc()

# 6. DASHBOARD MODULE
try:
    from app.dashboard import dashboard_bp, init_dashboard
    init_dashboard(app, mysql)
    app.register_blueprint(dashboard_bp)
    print("✅ Dashboard module loaded")
except Exception as e:
    print(f"❌ Failed to load Dashboard: {e}")
    import traceback
    traceback.print_exc()

# 7. MAIN ROUTES (Authentication, etc.)
try:
    from app.routes import main
    app.register_blueprint(main)
    print("✅ Main routes loaded")
except Exception as e:
    print(f"❌ Failed to load Main routes: {e}")
    import traceback
    traceback.print_exc()

print("="*80)
print("✅ REGENARDHI INITIALIZED SUCCESSFULLY")
print("="*80 + "\n")

# ===============================
#  DEBUG ROUTES
# ===============================

@app.route('/debug/routes')
def debug_routes():
    """Show all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    
    # Filter notification routes
    notification_routes = [r for r in routes if 'notification' in r['path'].lower()]
    
    return jsonify({
        'success': True,
        'total_routes': len(routes),
        'notification_routes': notification_routes,
        'all_routes': sorted(routes, key=lambda x: x['path'])
    })

@app.route('/debug/blueprints')
def debug_blueprints():
    """Show all registered blueprints"""
    blueprints = {}
    for name, blueprint in app.blueprints.items():
        blueprints[name] = {
            'name': blueprint.name,
            'url_prefix': blueprint.url_prefix,
            'static_folder': blueprint.static_folder,
            'template_folder': blueprint.template_folder
        }
    
    return jsonify({
        'success': True,
        'blueprints': blueprints,
        'count': len(blueprints)
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'RegenArdhi',
        'version': '1.0.0',
        'modules': {
            'notifications': 'notifications' in app.blueprints,
            'projects': 'projects' in app.blueprints,
            'monitoring': 'monitoring' in app.blueprints,
            'insights': 'insights' in app.blueprints,
            'chat': 'chat' in app.blueprints,
            'dashboard': 'dashboard' in app.blueprints,
            'main': 'main' in app.blueprints
        }
    })

# ===============================
#  ERROR HANDLERS
# ===============================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'status': 500
    }), 500

# ===============================
#  RUN APPLICATION
# ===============================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 STARTING REGENARDHI SERVER")
    print("="*80)
    print("📍 Local:   http://127.0.0.1:5000")
    print("📍 Network: http://localhost:5000")
    print("\n💡 Debug Routes:")
    print("   - http://localhost:5000/health")
    print("   - http://localhost:5000/debug/routes")
    print("   - http://localhost:5000/debug/blueprints")
    print("="*80 + "\n")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=True
    )