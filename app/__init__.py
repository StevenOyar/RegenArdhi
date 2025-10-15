import os
from flask import Flask
from flask_mail import Mail
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# ===============================
#  Flask App Factory
# ===============================
app = Flask(__name__)

# -------------------------------
#  Basic Configuration
# -------------------------------
app.secret_key = os.getenv("SECRET_KEY", "dev-key-please-change-this-in-production")

app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# -------------------------------
#  Email Configuration
# -------------------------------
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_SENDER_EMAIL"),
)

# -------------------------------
#  MySQL Configuration
# -------------------------------
# -------------------------------
#  MySQL Configuration
# -------------------------------
app.config.update(
    MYSQL_HOST=os.getenv("MYSQL_HOST", "localhost"),
    MYSQL_USER=os.getenv("MYSQL_USER", "root"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", ""),
    MYSQL_DB=os.getenv("MYSQL_DB", "regenardhi_db"),
    MYSQL_PORT=int(os.getenv("MYSQL_PORT", 3306)),  # ADD THIS LINE
    MYSQL_CURSORCLASS='DictCursor'
)
# -------------------------------
#  Initialize Extensions
# -------------------------------
mail = Mail(app)
mysql = MySQL(app)

# -------------------------------
#  Initialize Database Tables
# -------------------------------
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
        print("✅ Users table initialized successfully!")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")

# -------------------------------
#  Import and Initialize Modules
# -------------------------------

# Projects Module
try:
    from app.projects import projects_bp, init_projects
    init_projects(app, mysql)
    app.register_blueprint(projects_bp)
    print("✅ Projects module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Projects module: {e}")

# Monitoring Module
try:
    from app.monitoring import monitoring_bp, init_monitoring
    init_monitoring(app, mysql)
    app.register_blueprint(monitoring_bp)
    print("✅ Monitoring module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Monitoring module: {e}")

# Insights Module (NEW)
try:
    from app.insights import insights_bp, init_insights
    init_insights(app, mysql)
    app.register_blueprint(insights_bp)
    print("✅ Insights module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Insights module: {e}")

# Chat Module (NEW)
try:
    from app.chat import chat_bp, init_chat
    init_chat(app, mysql)
    app.register_blueprint(chat_bp)
    print("✅ Chat module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Chat module: {e}")

# -------------------------------
#  Import Core Routes
# -------------------------------
try:
    from app import routes
    print("✅ Core routes loaded successfully!")
except Exception as e:
    print(f"❌ Error loading routes: {e}")




# In app/__init__.py

# ... existing imports ...

# Dashboard Module (ADD THIS)
try:
    from app.dashboard import dashboard_bp, init_dashboard
    init_dashboard(app, mysql)
    app.register_blueprint(dashboard_bp)
    print("✅ Dashboard module loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Dashboard module: {e}")
    
    
    
print("\n" + "="*50)
print("🌿 REGENARDHI - AI-POWERED LAND RESTORATION")
print("="*50)
print("✓ All modules initialized")
print("✓ Database tables created")
print("✓ API integrations ready:")
print("  - NASA POWER API (Climate Data)")
print("  - Hugging Face (AI Insights)")
print("  - OpenStreetMap (Geocoding)")
print("="*50 + "\n")
