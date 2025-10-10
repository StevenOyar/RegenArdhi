import os
import requests
import json
from flask import Blueprint, request, jsonify, session
from flask_mysqldb import MySQL
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()

# Create Blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# MySQL connection
mysql = None

# API Configuration
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/"

# Working models (tested and verified)
# ✅ Publicly available and stable text-generation models
WORKING_MODELS = [
    "mistralai/mistral-7b-instruct",
    "google/gemma-2-2b-it",           # Conversational & open-access
    "tiiuae/falcon-7b-instruct",    # Strong instruction-following model
    "mistralai/Mistral-7B-Instruct-v0.2"  # Reliable fallback
]
DEFAULT_MODEL = WORKING_MODELS[0]

DEFAULT_MODEL = WORKING_MODELS[0]

def init_chat(app, mysql_instance):
    """Initialize chat module"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    project_id INT,
                    message TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    response TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    context JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
                    INDEX idx_user_project (user_id, project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            mysql.connection.commit()
            cur.close()
            print("✅ Chat history table initialized!")
        except Exception as e:
            print(f"⚠️ Chat table error (may already exist): {e}")
    
    print("✅ Chat module initialized!")

# ========================
# CONTEXT BUILDING
# ========================

def get_user_context(user_id):
    """Get user's project context for better responses"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('''
            SELECT COUNT(*) as total_projects,
                   SUM(area_hectares) as total_area,
                   COUNT(CASE WHEN status = 'active' THEN 1 END) as active_projects
            FROM projects
            WHERE user_id = %s
        ''', (user_id,))
        
        stats = cur.fetchone()
        
        cur.execute('''
            SELECT name, project_type, status, land_degradation_level
            FROM projects
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 3
        ''', (user_id,))
        
        recent_projects = cur.fetchall()
        cur.close()
        
        return {
            'total_projects': stats['total_projects'] or 0,
            'total_area': float(stats['total_area'] or 0),
            'active_projects': stats['active_projects'] or 0,
            'recent_projects': [
                f"{p['name']} ({p['project_type']}, {p['status']})"
                for p in recent_projects
            ]
        }
        
    except Exception as e:
        print(f"Error getting user context: {e}")
        return {}

def get_project_context(project_id):
    """Get specific project context"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            return None
        
        cur.execute('''
            SELECT * FROM monitoring_data
            WHERE project_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
        ''', (project_id,))
        
        monitoring = cur.fetchone()
        cur.close()
        
        context = {
            'name': project['name'],
            'type': project['project_type'],
            'area': float(project['area_hectares']),
            'location': project['location'],
            'status': project['status'],
            'degradation': project.get('land_degradation_level'),
            'soil_type': project.get('soil_type'),
            'climate_zone': project.get('climate_zone')
        }
        
        if monitoring:
            context['current_ndvi'] = float(monitoring.get('ndvi', 0)) if monitoring.get('ndvi') else None
            context['vegetation_health'] = monitoring.get('vegetation_health')
            context['soil_moisture'] = float(monitoring.get('soil_moisture', 0)) if monitoring.get('soil_moisture') else None
        
        return context
        
    except Exception as e:
        print(f"Error getting project context: {e}")
        return None

# ========================
# AI RESPONSE GENERATION
# ========================

def build_context_prompt(user_context, project_context=None):
    """Build context information for the AI"""
    context_parts = []
    
    if user_context and user_context.get('total_projects', 0) > 0:
        context_parts.append(f"User manages {user_context['total_projects']} projects covering {user_context['total_area']:.1f} hectares")
    
    if project_context:
        context_parts.append(f"Current project: {project_context['name']} ({project_context['type']})")
        
        if project_context.get('current_ndvi'):
            ndvi = project_context['current_ndvi']
            health = "excellent" if ndvi > 0.6 else "good" if ndvi > 0.4 else "fair" if ndvi > 0.2 else "poor"
            context_parts.append(f"NDVI: {ndvi:.2f} ({health})")
        
        if project_context.get('vegetation_health'):
            context_parts.append(f"Vegetation health: {project_context['vegetation_health']}")
        
        if project_context.get('soil_moisture'):
            context_parts.append(f"Soil moisture: {project_context['soil_moisture']:.1f}%")
    
    return " | ".join(context_parts) if context_parts else ""

def query_huggingface(user_message, context_info="", max_retries=1):
    """Query Hugging Face API with enhanced error handling and logging"""
    
    # If no API key, go straight to fallback
    if not HUGGINGFACE_API_KEY or HUGGINGFACE_API_KEY == 'your_key_here':
        print("⚠️ No Hugging Face API key, using intelligent fallback")
        return generate_intelligent_fallback(user_message, context_info)
    
    # Build prompt
    prompt = f"{user_message}"
    if context_info:
        prompt = f"Context: {context_info}\nQuestion: {user_message}\nAnswer:"
    
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    api_errors = []  # Track all errors for debugging
    
    # Try each working model
    for model in WORKING_MODELS:
        try:
            model_url = f"{HUGGINGFACE_API_URL}{model}"
            print(f"🤖 Trying model: {model}")
            print(f"🔗 Full URL: {model_url}")
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "return_full_text": False
                },
                "options": {
                    "wait_for_model": True
                }
            }
            
            response = requests.post(
                model_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            print(f"📡 Status Code: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Raw Response Type: {type(result)}")
                print(f"✅ Raw Response: {str(result)[:200]}")
                
                # Extract text from response
                text = None
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict):
                        text = result[0].get('generated_text', '')
                    elif isinstance(result[0], str):
                        text = result[0]
                elif isinstance(result, dict):
                    text = result.get('generated_text', '')
                
                if text:
                    # Clean up response
                    text = text.replace(prompt, '').strip()
                    if len(text) > 20:
                        print(f"✅ Got valid response from {model}")
                        return text
                    else:
                        error_msg = f"Response too short: '{text}'"
                        print(f"⚠️ {error_msg}")
                        api_errors.append({
                            'model': model,
                            'status': 200,
                            'error': error_msg
                        })
                else:
                    error_msg = "No text in response"
                    print(f"⚠️ {error_msg}")
                    api_errors.append({
                        'model': model,
                        'status': 200,
                        'error': error_msg,
                        'response': result
                    })
            
            elif response.status_code == 404:
                error_msg = f"Model not found (404)"
                print(f"❌ 404 Error: Model '{model}' not found at {model_url}")
                try:
                    error_detail = response.json()
                    print(f"📄 Error Details: {error_detail}")
                    api_errors.append({
                        'model': model,
                        'status': 404,
                        'url': model_url,
                        'error': error_msg,
                        'details': error_detail
                    })
                except:
                    print(f"📄 Raw Response Text: {response.text[:500]}")
                    api_errors.append({
                        'model': model,
                        'status': 404,
                        'url': model_url,
                        'error': error_msg,
                        'raw_response': response.text[:500]
                    })
                continue
            
            elif response.status_code == 401:
                error_msg = "Unauthorized - Invalid API key"
                print(f"❌ 401 Error: {error_msg}")
                print(f"🔑 API Key (first 15 chars): {HUGGINGFACE_API_KEY[:15]}...")
                api_errors.append({
                    'model': model,
                    'status': 401,
                    'error': error_msg
                })
                # Don't try other models if API key is invalid
                break
            
            elif response.status_code == 403:
                error_msg = "Forbidden - No access to this model"
                print(f"❌ 403 Error: {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"📄 Error Details: {error_detail}")
                    api_errors.append({
                        'model': model,
                        'status': 403,
                        'error': error_msg,
                        'details': error_detail
                    })
                except:
                    api_errors.append({
                        'model': model,
                        'status': 403,
                        'error': error_msg
                    })
                continue
                
            elif response.status_code == 503:
                error_msg = "Service unavailable - Model loading"
                print(f"⏳ 503 Error: {error_msg}")
                try:
                    error_detail = response.json()
                    estimated_time = error_detail.get('estimated_time', 'unknown')
                    print(f"⏱️ Estimated wait time: {estimated_time}s")
                    api_errors.append({
                        'model': model,
                        'status': 503,
                        'error': error_msg,
                        'estimated_time': estimated_time
                    })
                except:
                    api_errors.append({
                        'model': model,
                        'status': 503,
                        'error': error_msg
                    })
                continue
            
            elif response.status_code == 429:
                error_msg = "Rate limit exceeded"
                print(f"⏸️ 429 Error: {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"📄 Error Details: {error_detail}")
                    api_errors.append({
                        'model': model,
                        'status': 429,
                        'error': error_msg,
                        'details': error_detail
                    })
                except:
                    api_errors.append({
                        'model': model,
                        'status': 429,
                        'error': error_msg
                    })
                continue
            
            else:
                error_msg = f"Unexpected status: {response.status_code}"
                print(f"❌ {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"📄 Error Details: {error_detail}")
                    api_errors.append({
                        'model': model,
                        'status': response.status_code,
                        'error': error_msg,
                        'details': error_detail
                    })
                except:
                    print(f"📄 Raw Response: {response.text[:500]}")
                    api_errors.append({
                        'model': model,
                        'status': response.status_code,
                        'error': error_msg,
                        'raw_response': response.text[:500]
                    })
                continue
                
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout after 15s"
            print(f"⏱️ Timeout Error: {error_msg}")
            api_errors.append({
                'model': model,
                'error_type': 'Timeout',
                'error': error_msg
            })
            continue
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed: {str(e)[:100]}"
            print(f"🔌 Connection Error: {error_msg}")
            api_errors.append({
                'model': model,
                'error_type': 'ConnectionError',
                'error': error_msg
            })
            continue
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)[:100]}"
            print(f"❌ Request Error: {error_msg}")
            api_errors.append({
                'model': model,
                'error_type': 'RequestException',
                'error': error_msg
            })
            continue
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {str(e)}"
            print(f"📄 JSON Error: {error_msg}")
            api_errors.append({
                'model': model,
                'error_type': 'JSONDecodeError',
                'error': error_msg
            })
            continue
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)[:100]}"
            print(f"❌ Unexpected Error: {error_msg}")
            import traceback
            traceback.print_exc()
            api_errors.append({
                'model': model,
                'error_type': type(e).__name__,
                'error': error_msg
            })
            continue
    
    # All models failed - log summary
    print("\n" + "="*70)
    print("❌ ALL HUGGINGFACE MODELS FAILED - ERROR SUMMARY:")
    print("="*70)
    for i, err in enumerate(api_errors, 1):
        print(f"\n{i}. Model: {err.get('model', 'Unknown')}")
        print(f"   Status: {err.get('status', err.get('error_type', 'Unknown'))}")
        print(f"   Error: {err.get('error', 'No error message')}")
        if 'url' in err:
            print(f"   URL: {err['url']}")
        if 'details' in err:
            print(f"   Details: {err['details']}")
        if 'raw_response' in err:
            print(f"   Raw Response: {err['raw_response'][:150]}...")
    print("="*70 + "\n")
    
    # Save errors to log file
    try:
        with open('huggingface_errors.log', 'a') as f:
            f.write(f"\n\n{'='*70}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Message: {user_message}\n")
            f.write(f"Context: {context_info}\n")
            f.write(f"API Key Present: {'Yes' if HUGGINGFACE_API_KEY else 'No'}\n")
            if HUGGINGFACE_API_KEY:
                f.write(f"API Key Preview: {HUGGINGFACE_API_KEY[:15]}...\n")
            f.write(f"Base URL: {HUGGINGFACE_API_URL}\n")
            f.write(f"\nErrors:\n{json.dumps(api_errors, indent=2)}\n")
    except Exception as e:
        print(f"⚠️ Could not write to error log: {e}")
    
    # Use intelligent fallback
    print("⚠️ Falling back to intelligent responses")
    return generate_intelligent_fallback(user_message, context_info)

def generate_intelligent_fallback(user_message, context_info=""):
    """Enhanced fallback responses - NO emojis for database compatibility"""
    message_lower = user_message.lower()
    
    # Extract NDVI from context
    has_ndvi = 'ndvi' in context_info.lower()
    
    # NDVI queries
    if 'ndvi' in message_lower or 'vegetation' in message_lower:
        if has_ndvi:
            import re
            ndvi_match = re.search(r'ndvi:\s*([\d.]+)', context_info.lower())
            if ndvi_match:
                ndvi = float(ndvi_match.group(1))
                if ndvi > 0.6:
                    return f"Great news! Your NDVI is {ndvi:.2f}, indicating excellent vegetation health. Your restoration efforts are showing strong results. Continue with current management practices and monitor for any pest or disease issues."
                elif ndvi > 0.4:
                    return f"Your NDVI is {ndvi:.2f}, showing good vegetation cover. To improve further, consider: 1) Increasing organic matter through composting, 2) Implementing better water management, 3) Adding nitrogen-fixing cover crops."
                elif ndvi > 0.2:
                    return f"Your NDVI is {ndvi:.2f}, indicating fair vegetation health. Action needed: 1) Implement cover cropping, 2) Apply organic mulch 5-10cm thick, 3) Test and amend soil pH, 4) Ensure adequate irrigation."
                else:
                    return f"ALERT: Your NDVI is {ndvi:.2f}, showing critical vegetation stress. Immediate actions: 1) Increase irrigation frequency, 2) Add organic matter and compost, 3) Consider replanting with drought-resistant species, 4) Consult with an agronomist."
        
        return """NDVI (Normalized Difference Vegetation Index) is a key indicator of vegetation health.

Scale interpretation:
* 0.6 to 1.0 = Excellent (dense, healthy vegetation)
* 0.4 to 0.6 = Good (moderate, healthy cover)
* 0.2 to 0.4 = Fair (sparse or stressed vegetation)
* Below 0.2 = Poor/Critical (severe stress or bare soil)

Higher values indicate healthier, denser vegetation. Select a project to see your specific NDVI analysis and recommendations."""
    
    # Soil health
    elif 'soil' in message_lower:
        if 'moisture' in message_lower:
            return """Soil moisture is critical for plant growth and restoration success.

Optimal ranges:
* 40-60% = Ideal for most crops and restoration species
* 30-40% = Acceptable but may need supplemental irrigation
* Below 30% = Plants experiencing water stress
* Above 70% = Risk of waterlogging and root diseases

Improvement strategies:
1. Apply 5-10cm organic mulch to retain moisture
2. Install drip irrigation systems for efficiency
3. Add compost to improve water-holding capacity
4. Plant deep-rooted cover crops
5. Create swales and berms to capture runoff"""
        
        return """Soil health is the foundation of successful land restoration.

Key indicators:
* pH level: 6.0-7.5 optimal for most species
* Organic matter: Target 3-5% or higher
* Moisture: 40-60% for active growth
* Structure: Good aggregation, drainage, and aeration
* Nutrients: Adequate N, P, K levels

Improvement plan:
1. Test soil (pH, nutrients, organic matter)
2. Add compost or well-rotted manure (2-4 tons/hectare)
3. Use cover crops (legumes fix nitrogen)
4. Minimize soil disturbance and tillage
5. Apply organic mulch (conserves moisture, adds nutrients)
6. Monitor progress with annual testing"""
    
    # Planting timing
    elif any(word in message_lower for word in ['plant', 'season', 'when', 'timing']):
        current_month = datetime.now().month
        
        if current_month in [3, 4, 5]:
            return """OPTIMAL PLANTING SEASON: Long Rains (March-May)

This is THE BEST time for planting in Kenya!

Recommended actions:
* Plant indigenous tree species NOW
* Establish soil conservation structures (terraces, bunds)
* Maximize seedling establishment
* Prepare for 6-8 weeks of optimal growing conditions
* Priority species: Acacia, Grevillea, Neem, indigenous fruits

Success tips:
1. Plant at start of rains (not during heavy downpours)
2. Dig holes 60x60x60cm, fill with topsoil + compost
3. Space trees 3-4 meters apart
4. Stake tall seedlings
5. Apply mulch around base (keep clear of stem)"""
        
        elif current_month in [10, 11, 12]:
            return """SECONDARY PLANTING WINDOW: Short Rains (October-December)

Good for hardy, drought-resistant species.

Recommended species:
* Acacia varieties
* Grevillea robusta
* Moringa oleifera
* Drought-adapted indigenous species

Best practices:
1. Focus on drought-resistant varieties
2. Prepare irrigation backup
3. Apply thick mulch (10cm) for moisture retention
4. Monitor seedlings closely (short rains less reliable)
5. Water daily for first 2 weeks if rains insufficient

This window is shorter and less predictable than long rains."""
        
        else:
            return """CURRENT STATUS: Dry Season

NOT recommended for planting new seedlings.

Focus activities:
* Maintain and water established plants
* Prepare planting sites for next season
* Build soil conservation structures
* Source quality seedlings
* Test and amend soil
* Clear invasive species
* Plan restoration strategy

Next planting windows:
* Primary: March-May (Long Rains) - BEST
* Secondary: October-December (Short Rains) - Good

Use this time to prepare thoroughly for successful planting when rains arrive."""
    
    # Restoration techniques
    elif any(word in message_lower for word in ['restore', 'technique', 'how', 'improve', 'help']):
        return """COMPREHENSIVE RESTORATION STRATEGIES

1. SOIL CONSERVATION
   * Build contour terraces on slopes over 15%
   * Establish grass strips along contours
   * Plant cover crops (legumes, grasses)
   * Apply mulch (5-10cm) to prevent erosion
   * Create stone bunds or gabions

2. WATER MANAGEMENT
   * Install rainwater harvesting (tanks, ponds)
   * Dig infiltration ditches along contours
   * Create swales to slow runoff
   * Use drip irrigation for efficiency
   * Implement zai pits in degraded areas

3. VEGETATION ESTABLISHMENT
   * Use indigenous species (adapted to local conditions)
   * Mix trees, shrubs, and grasses
   * Plant in suitable seasons (March-May best)
   * Space appropriately (3-4m for trees)
   * Succession planting (pioneer species first)

4. MONITORING & ADAPTATION
   * Track NDVI monthly
   * Monitor soil health quarterly
   * Measure tree growth and survival
   * Record rainfall and weather
   * Adjust strategies based on data

What specific aspect would you like to explore in detail?"""
    
    # Data interpretation
    elif any(word in message_lower for word in ['data', 'interpret', 'understand', 'mean', 'explain']):
        return """DATA INTERPRETATION GUIDE

Key metrics I monitor:

VEGETATION HEALTH (NDVI)
* Measures photosynthetic activity
* 0.6+ = Excellent restoration progress
* 0.4-0.6 = Good, on track
* 0.2-0.4 = Fair, needs intervention
* Below 0.2 = Critical, immediate action

SOIL METRICS
* Moisture: 40-60% optimal
* pH: 6.0-7.5 for most species
* Organic matter: Target 3-5%
* Erosion risk: Monitor after heavy rains

CLIMATE DATA
* Temperature: Affects growth rates
* Rainfall: Critical for establishment
* Humidity: Influences disease risk
* Solar radiation: Drives photosynthesis

TRENDS TO WATCH
* Improving NDVI = Restoration working
* Declining NDVI = Investigate causes
* Seasonal patterns = Normal variation
* Extreme events = May require intervention

Share your specific data for detailed analysis and recommendations!"""
    
    # Greetings
    elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greet']):
        project_note = ""
        if context_info:
            project_note = "\n\nI can see you're working on a project. I can help analyze its data and provide specific recommendations!"
        
        return f"""Hello! I'm RegenAI, your intelligent land restoration assistant.

I can help you with:
* Vegetation health analysis (NDVI interpretation)
* Soil health assessment and management
* Climate pattern analysis and seasonal planning
* Data interpretation and trend analysis
* Restoration technique recommendations
* Species selection guidance{project_note}

What would you like to know about your restoration project?"""
    
    # Thank you
    elif 'thank' in message_lower:
        return "You're welcome! I'm here to support your restoration efforts. Feel free to ask anything about your projects, data, or best practices. Together we can restore degraded lands!"
    
    # Default comprehensive
    else:
        return """I'm your land restoration AI assistant!

I can help with:
* VEGETATION: Analyze NDVI data, interpret trends, diagnose issues
* SOIL: Assess health, recommend amendments, improve fertility
* CLIMATE: Understand patterns, plan seasonal activities
* DATA: Interpret metrics, identify trends, track progress
* TECHNIQUES: Suggest strategies, select species, optimize methods

Popular questions:
* "What is my current NDVI?"
* "When should I plant?"
* "How can I improve soil health?"
* "What do my monitoring metrics mean?"
* "What restoration techniques work best?"

Please select a project from the dropdown, then ask me anything specific about your data or restoration needs!"""

# ========================
# CHAT ROUTES
# ========================

@chat_bp.route('/api/message', methods=['POST'])
def chat_message():
    """Handle chat message"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        project_id = data.get('project_id')
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        print(f"💬 Message: '{user_message}' | Project: {project_id}")
        
        # Get context
        user_context = get_user_context(session['user_id'])
        project_context = None
        
        if project_id:
            project_context = get_project_context(project_id)
        
        context_info = build_context_prompt(user_context, project_context)
        print(f"📋 Context: {context_info}")
        
        # Generate response
        ai_response = query_huggingface(user_message, context_info)
        
        if not ai_response:
            ai_response = generate_intelligent_fallback(user_message, context_info)
        
        print(f"🤖 Response: {ai_response[:100]}...")
        
        # Save to history (with error handling)
        try:
            cur = mysql.connection.cursor()
            cur.execute('''
                INSERT INTO chat_history (user_id, project_id, message, response, context)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                session['user_id'],
                project_id,
                user_message,
                ai_response,
                json.dumps({'user': user_context, 'project': project_context})
            ))
            mysql.connection.commit()
            cur.close()
            print("✅ Chat saved")
        except Exception as e:
            print(f"⚠️ Save error: {e}")
            # Continue anyway
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to generate response'
        }), 500

@chat_bp.route('/api/history')
def get_chat_history():
    """Get chat history for user"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        project_id = request.args.get('project_id')
        limit = int(request.args.get('limit', 20))
        
        if project_id:
            cur.execute('''
                SELECT * FROM chat_history
                WHERE user_id = %s AND project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ''', (session['user_id'], project_id, limit))
        else:
            cur.execute('''
                SELECT * FROM chat_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ''', (session['user_id'], limit))
        
        history = cur.fetchall()
        cur.close()
        
        for item in history:
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'history': list(reversed(history))
        })
        
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/clear', methods=['POST'])
def clear_chat_history():
    """Clear chat history"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        cur = mysql.connection.cursor()
        
        if project_id:
            cur.execute('''
                DELETE FROM chat_history
                WHERE user_id = %s AND project_id = %s
            ''', (session['user_id'], project_id))
        else:
            cur.execute('''
                DELETE FROM chat_history
                WHERE user_id = %s
            ''', (session['user_id'],))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error clearing history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/suggestions')
def get_suggestions():
    """Get suggested questions"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        project_id = request.args.get('project_id')
        
        suggestions = [
            "What does my current NDVI tell me?",
            "When is the best time to plant?",
            "How can I improve soil health?",
            "What restoration techniques should I use?"
        ]
        
        if project_id:
            project_context = get_project_context(int(project_id))
            
            if project_context:
                if project_context.get('current_ndvi', 0) < 0.4:
                    suggestions.insert(0, "Why is my vegetation health low?")
                
                if project_context.get('degradation') in ['severe', 'critical']:
                    suggestions.insert(0, "What emergency actions should I take?")
        
        return jsonify({
            'success': True,
            'suggestions': suggestions[:5]
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': True,
            'suggestions': [
                "Tell me about NDVI",
                "How do I start restoration?",
                "What are the best native species?"
            ]
        })


# ========================
# DATABASE FIX UTILITY
# ========================

def fix_database_charset():
    """
    Run this ONCE to fix emoji/UTF-8 issues.
    Call from app.py after initializing chat:
    
    from app.chat import fix_database_charset
    fix_database_charset()
    """
    try:
        cur = mysql.connection.cursor()
        
        cur.execute('''
            ALTER TABLE chat_history 
            CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        
        cur.execute('''
            ALTER TABLE chat_history 
            MODIFY message TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            MODIFY response TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        
        mysql.connection.commit()
        cur.close()
        print("✅ Database charset fixed!")
        return True
        
    except Exception as e:
        print(f"⚠️ Charset fix error: {e}")
        return False