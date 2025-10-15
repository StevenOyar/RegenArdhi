import os
from flask import Flask
from flask_mail import Mail
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables FIRST
load_dotenv()

# Create Flask app
app = Flask(__name__)

# -------------------------
# 🔧 Configurations
# -------------------------
app.secret_key = os.getenv("SECRET_KEY", "dev-key-please-change-this-in-production")

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Email (Flask-Mail)
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_SENDER_EMAIL")

# MySQL Configuration
# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'regenardhi_db')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))  # ADD THIS LINE
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize extensions
mail = Mail(app)
mysql = MySQL(app)

# Initialize database tables
with app.app_context():
    try:
        cur = mysql.connection.cursor()
        
        # Create users table with password reset fields
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
        print("✅ Users table initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing users table: {e}")

# -------------------------
# 📦 Register Blueprints
# -------------------------
print("\n" + "="*80)
print("🔧 LOADING MODULES")
print("="*80)

# Initialize Projects module
try:
    from app.projects import projects_bp, init_projects
    init_projects(app, mysql)
    app.register_blueprint(projects_bp)
    print(f"✅ Projects module loaded at: {projects_bp.url_prefix}")
except Exception as e:
    print(f"❌ Failed to load Projects module: {e}")
    import traceback
    traceback.print_exc()

# Initialize Monitoring module
try:
    from app.monitoring import monitoring_bp, init_monitoring
    init_monitoring(app, mysql)
    app.register_blueprint(monitoring_bp)
    print(f"✅ Monitoring module loaded at: {monitoring_bp.url_prefix}")
except Exception as e:
    print(f"❌ Failed to load Monitoring module: {e}")
    import traceback
    traceback.print_exc()

# Initialize Insights module - WITH EXPLICIT ERROR HANDLING
try:
    print("\n🔍 Loading Insights module...")
    from app.insights import insights_bp, init_insights
    print(f"  → Blueprint imported: {insights_bp}")
    print(f"  → URL prefix: {insights_bp.url_prefix}")
    
    # Initialize first
    init_insights(app, mysql)
    print("  → Database initialized")
    
    # Then register
    app.register_blueprint(insights_bp)
    print(f"✅ Insights module loaded successfully at: {insights_bp.url_prefix}")
    
    # Verify routes were registered
    insights_routes = [str(rule) for rule in app.url_map.iter_rules() if 'insights' in str(rule)]
    print(f"  → Registered routes: {insights_routes}")
    
except ImportError as e:
    print(f"❌ Failed to import Insights module: {e}")
    print("   → Check if app/insights.py exists")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Failed to load Insights module: {e}")
    import traceback
    traceback.print_exc()

# Initialize Chat module
try:
    from app.chat import chat_bp, init_chat
    init_chat(app, mysql)
    app.register_blueprint(chat_bp)
    print(f"✅ Chat module loaded at: {chat_bp.url_prefix}")
except Exception as e:
    print(f"❌ Failed to load Chat module: {e}")
    import traceback
    traceback.print_exc()

# Import and register main routes (LAST - to avoid conflicts)
try:
    from app.routes import main
    app.register_blueprint(main)
    print(f"✅ Main routes loaded")
except Exception as e:
    print(f"❌ Error loading routes: {e}")
    import traceback
    traceback.print_exc()

print("="*80 + "\n")

# -------------------------
# 🔍 DEBUG: Print all routes
# -------------------------
def print_all_routes():
    print("\n" + "="*80)
    print("🗺️  ALL REGISTERED ROUTES")
    print("="*80)
    
    insights_found = False
    
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        route_str = f"{str(rule):50s} [{methods:15s}] -> {rule.endpoint}"
        
        if 'insights' in str(rule).lower():
            print(f"✅ {route_str}")
            insights_found = True
        else:
            print(f"   {route_str}")
    
    print("="*80)
    
    if not insights_found:
        print("\n⚠️  WARNING: No insights routes found!")
        print("   This means insights_bp was NOT registered correctly.")
        print("\n   Troubleshooting steps:")
        print("   1. Check if app/insights.py exists")
        print("   2. Check if insights_bp = Blueprint('insights', __name__, url_prefix='/insights')")
        print("   3. Check if app.register_blueprint(insights_bp) was called")
        print("   4. Check for any import errors in insights.py")
    else:
        print("\n✅ Insights routes are registered correctly!")
    
    print("="*80 + "\n")

print_all_routes()

# -------------------------
# 🧪 Test API Keys (Optional)
# -------------------------
print("🧪 Testing API Integrations...")
try:
    from app.api_integrations import OpenWeatherAPI, NASAPowerAPI
    from datetime import datetime, timedelta
    
    # Test OpenWeather
    print("  → Testing OpenWeather API...")
    weather = OpenWeatherAPI.get_current_weather(-1.2921, 36.8219)
    if weather:
        print("  ✅ OpenWeather API working")
    else:
        print("  ⚠️  OpenWeather API failed")
    
    # Test NASA POWER
    print("  → Testing NASA POWER API...")
    climate = NASAPowerAPI.get_climate_data(
        -1.2921, 36.8219,
        datetime.now() - timedelta(days=7),
        datetime.now()
    )
    if climate:
        print("  ✅ NASA POWER API working")
    else:
        print("  ⚠️  NASA POWER API failed")
        
except Exception as e:
    print(f"  ⚠️  API test failed: {e}")

print("\n" + "="*80)

# -------------------------
# 🚀 Run Server
# -------------------------
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🌿 REGENARDHI SERVER")
    print("="*80)
    print(f"Environment: {'Development' if app.debug else 'Production'}")
    print(f"Secret Key: {'✅ Set' if app.secret_key else '❌ NOT SET'}")
    print(f"MySQL Host: {app.config.get('MYSQL_HOST')}")
    print(f"MySQL User: {app.config.get('MYSQL_USER')}")
    print(f"MySQL DB: {app.config.get('MYSQL_DB')}")
    print(f"Mail Server: {app.config.get('MAIL_SERVER')}")
    print("="*80)
    print("\n🔗 Server URLs:")
    print(f"  → Main: http://127.0.0.1:5000")
    print(f"  → Insights: http://127.0.0.1:5000/insights/")
    print(f"  → Insights Test: http://127.0.0.1:5000/insights/test")
    print("\n" + "="*80 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
