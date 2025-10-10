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
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'regenardhi_db')
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
print("\n=== Loading Modules ===")

# Initialize Projects module
try:
    from app.projects import projects_bp, init_projects
    init_projects(app, mysql)
    app.register_blueprint(projects_bp)
    print("✅ Projects module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Projects module: {e}")
    import traceback
    traceback.print_exc()

# Initialize Monitoring module
try:
    from app.monitoring import monitoring_bp, init_monitoring
    init_monitoring(app, mysql)
    app.register_blueprint(monitoring_bp)
    print("✅ Monitoring module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Monitoring module: {e}")
    import traceback
    traceback.print_exc()

# Initialize Insights module
try:
    from app.insights import insights_bp, init_insights
    init_insights(app, mysql)
    app.register_blueprint(insights_bp)
    print("✅ Insights module loaded successfully!")
    print(f"  → Insights blueprint registered at: {insights_bp.url_prefix}")
except Exception as e:
    print(f"❌ Failed to load Insights module: {e}")
    import traceback
    traceback.print_exc()

# Initialize Chat module
try:
    from app.chat import chat_bp, init_chat
    init_chat(app, mysql)
    app.register_blueprint(chat_bp)
    print("✅ Chat module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Chat module: {e}")
    import traceback
    traceback.print_exc()

# Import and register main routes (LAST)
try:
    from app.routes import main
    app.register_blueprint(main)
    print("✅ Main routes loaded successfully!")
except Exception as e:
    print(f"❌ Error loading routes: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All Modules Loaded ===")

# Print all registered routes for debugging
print("\n=== Registered Routes ===")
for rule in app.url_map.iter_rules():
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"  {rule.endpoint:40s} {methods:15s} {rule.rule}")
print("========================\n")



# Test API keys
from app.api_integrations import OpenWeatherAPI, NASAPowerAPI

# Test OpenWeather
weather = OpenWeatherAPI.get_current_weather(-1.2921, 36.8219)
print(weather)

# Test NASA POWER
from datetime import datetime, timedelta
climate = NASAPowerAPI.get_climate_data(
    -1.2921, 36.8219,
    datetime.now() - timedelta(days=7),
    datetime.now()
)
print(climate)

if __name__ == "__main__":
    print("=" * 60)
    print("🌿 RegenArdhi Server Starting...")
    print("=" * 60)
    print(f"SECRET_KEY: {'✅ Set' if app.secret_key else '❌ NOT SET'}")
    print(f"MYSQL_HOST: {app.config.get('MYSQL_HOST')}")
    print(f"MYSQL_USER: {app.config.get('MYSQL_USER')}")
    print(f"MYSQL_DB: {app.config.get('MYSQL_DB')}")
    print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print("=" * 60)
    print("📡 Server running at http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)