# RegenArdhi
PLP hackathon 



# RegenArdhi - AI-Powered Land Restoration Platform

## Overview
RegenArdhi is a comprehensive web application that leverages AI and satellite data to help users assess, monitor, and restore degraded land. The platform provides real-time environmental analysis, project management, and community-driven monitoring for sustainable land restoration initiatives.

## Features

### 🌱 Core Functionality
- **AI-Powered Land Analysis**: Automated assessment of soil quality, vegetation health, and degradation levels
- **Project Management**: Create, track, and manage land restoration projects
- **Real-Time Monitoring**: Track vegetation indices (NDVI), climate data, and soil conditions
- **Community Reports**: Collaborative monitoring through user-submitted observations
- **Restoration Planning**: AI-generated recommendations for crops, trees, and restoration techniques
- **Interactive Maps**: Visualize project locations and environmental data
- **Progress Tracking**: Monitor restoration outcomes over time

### 📊 Technical Capabilities
- Real-time weather data integration (OpenWeather API)
- Elevation data retrieval (Open-Elevation API)
- Geolocation services (OpenStreetMap Nominatim)
- NDVI estimation and vegetation health assessment
- Soil type and pH analysis
- Climate zone classification
- Erosion risk assessment
- Budget and timeline estimation

## Technology Stack

### Backend
- **Framework**: Flask (Python web framework)
- **Database**: MySQL with Flask-MySQLdb
- **Authentication**: Session-based with werkzeug security
- **Email**: Flask-Mail for notifications

### APIs & External Services
- OpenWeather API (climate data)
- OpenStreetMap Nominatim (geocoding)
- Open-Elevation API (terrain data)
- Google Maps API (optional, for enhanced mapping)
- NASA Earth API (configurable for satellite imagery)

### Frontend Dependencies
- HTML5, CSS3, JavaScript
- Responsive design for mobile and desktop

## Requirements

### System Requirements
```
Python 3.8+
MySQL 5.7+ or MariaDB 10.3+
```

### Python Dependencies
```
Flask>=2.3.0
Flask-MySQLdb>=1.0.1
Flask-Mail>=0.9.1
python-dotenv>=1.0.0
werkzeug>=2.3.0
requests>=2.31.0
mysqlclient>=2.2.0
```

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/regenardhi.git
cd regenardhi
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE regenardhi_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;
```

### 5. Environment Configuration
Create a `.env` file in the project root:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_ENV=development

# Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DB=regenardhi_db

# Email Configuration (Gmail example)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
MAIL_SENDER_EMAIL=your-email@gmail.com

# API Keys
OPENWEATHER_API_KEY=your-openweather-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key (optional)
NASA_EARTH_API_KEY=DEMO_KEY
```

### 6. Initialize Database Tables
Tables are automatically created on first run. Start the application:

```bash
python run.py
```

The application will create the following tables:
- `users` - User accounts and authentication
- `projects` - Land restoration projects
- `monitoring_data` - Environmental monitoring records
- `community_reports` - User-submitted observations
- `restoration_actions` - Planned and completed restoration activities

## Configuration

### Required API Keys

1. **OpenWeather API** (Recommended)
   - Sign up at: https://openweathermap.org/api
   - Free tier: 1,000 calls/day
   - Used for: Real-time weather and climate data

2. **Google Maps API** (Optional)
   - Get key at: https://console.cloud.google.com/
   - Enable: Maps JavaScript API, Geocoding API
   - Used for: Enhanced mapping features

3. **NASA Earth API** (Optional)
   - Register at: https://api.nasa.gov/
   - Used for: Satellite imagery (future enhancement)

### Email Configuration

For Gmail:
1. Enable 2-Factor Authentication
2. Generate an App-Specific Password
3. Use the app password in your `.env` file

For other providers, adjust `MAIL_SERVER` and `MAIL_PORT` accordingly.

## Running the Application

### Development Mode
```bash
python run.py
```
Access at: `http://localhost:5000`

### Production Deployment

#### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

#### Using Apache/Nginx
Configure WSGI with your preferred web server.

## Project Structure

```
regenardhi/
│
├── app/
│   ├── __init__.py          # Flask app initialization
│   ├── routes.py            # Core routes (auth, dashboard)
│   ├── projects.py          # Project management module
│   ├── monitoring.py        # Environmental monitoring module
│   ├── models.py            # Database models (placeholder)
│   └── utils.py             # Utility functions (placeholder)
│
├── templates/               # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── projects.html
│   ├── project_detail.html
│   ├── monitoring.html
│   └── ...
│
├── static/                  # Static assets (CSS, JS, images)
│
├── .env                     # Environment variables (not in repo)
├── .env.example             # Example environment file
├── requirements.txt         # Python dependencies
├── run.py                   # Application entry point
└── README.md               # This file
```

## Database Schema

### Users Table
Stores user account information and authentication data.

### Projects Table
Contains land restoration project details including:
- Location data (coordinates, area)
- AI analysis results (soil, climate, vegetation)
- Recommendations (crops, trees, techniques)
- Progress tracking

### Monitoring Data Table
Tracks environmental metrics over time:
- Vegetation indices (NDVI)
- Soil conditions (moisture, temperature, pH)
- Climate data (temperature, rainfall, humidity)
- Alert levels and messages

### Community Reports Table
User-submitted field observations and reports.

### Restoration Actions Table
Planned and completed restoration activities.

## API Endpoints

### Authentication
- `GET/POST /register` - User registration
- `GET/POST /login` - User login
- `GET /logout` - User logout
- `GET/POST /reset-password` - Password reset

### Projects
- `GET /projects` - List all projects
- `POST /projects/create` - Create new project
- `GET /projects/<id>` - View project details
- `POST /projects/<id>/update` - Update project
- `DELETE /projects/<id>/delete` - Delete project
- `POST /projects/<id>/reanalyze` - Re-run AI analysis

### Monitoring
- `GET /monitoring/api/project/<id>/data` - Get monitoring data
- `POST /monitoring/api/project/<id>/update` - Update monitoring data
- `GET /monitoring/api/project/<id>/reports` - Get community reports
- `POST /monitoring/api/project/<id>/report` - Submit community report

## Usage Guide

### 1. Register an Account
Create a new account with your email and basic information.

### 2. Create a Project
- Enter project name and description
- Select project type (reforestation, soil conservation, etc.)
- Specify location (coordinates or map selection)
- Define project area in hectares

### 3. Review AI Analysis
The system automatically analyzes:
- Soil type and fertility
- Climate conditions
- Vegetation health
- Degradation level
- Recommended interventions

### 4. Monitor Progress
- View real-time environmental data
- Track vegetation changes
- Submit field observations
- Update project status

### 5. Manage Actions
- Plan restoration activities
- Track implementation
- Monitor costs and timelines

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Email: support@regenardhi.org
- Documentation: https://docs.regenardhi.org

## Acknowledgments

- OpenWeather API for climate data
- OpenStreetMap for geocoding services
- Open-Elevation for terrain data
- NASA Earth for satellite imagery capabilities

## Roadmap

- [ ] Integration with Sentinel Hub for real satellite imagery
- [ ] Mobile application (iOS/Android)
- [ ] Advanced analytics and reporting
- [ ] Multi-language support
- [ ] Offline mode for field use
- [ ] Integration with agricultural extension services
- [ ] Carbon credit calculation
- [ ] Community marketplace for restoration services

---

**Built with ❤️ for sustainable land restoration**