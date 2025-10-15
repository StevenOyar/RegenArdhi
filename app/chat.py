import os
import requests
import json
from flask import Blueprint, request, jsonify, session
from flask_mysqldb import MySQL
from datetime import datetime
from dotenv import load_dotenv
import time
import logging

# Try to import OpenAI, but don't fail if not installed
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI package not installed. Install with: pip install openai")

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# MySQL connection
mysql = None

# API Configuration - PRIMARY: Hugging Face Router (OpenAI-compatible)
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY') or os.getenv('HF_TOKEN')
HUGGINGFACE_BASE_URL = os.getenv('HUGGINGFACE_BASE_URL', 'https://router.huggingface.co/v1')
HUGGINGFACE_MODEL = os.getenv('HUGGINGFACE_MODEL', 'google/gemma-2-2b-it')

# FALLBACK: Direct Hugging Face Inference API
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models"
WORKING_MODELS = [
    "facebook/bart-large-cnn",
    "distilbert-base-uncased-finetuned-sst-2-english",
    "gpt2",
    "distilgpt2",
]

# Initialize OpenAI-compatible client for Hugging Face
hf_client = None
if OPENAI_AVAILABLE and HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != ' HUGGINGFACE_API_KEY':
    try:
        # FIX: Remove proxies argument - not supported in newer versions
        hf_client = OpenAI(
            base_url=HUGGINGFACE_BASE_URL,
            api_key=HUGGINGFACE_API_KEY
        )
        logger.info(f"✅ Hugging Face Router initialized with model: {HUGGINGFACE_MODEL}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Hugging Face client: {e}")
        hf_client = None
else:
    if not OPENAI_AVAILABLE:
        logger.warning("⚠️ OpenAI package not available")
    logger.warning("⚠️ No Hugging Face API key found, will use fallback responses")


def init_chat(app, mysql_instance):
    """Initialize chat module"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            # FIX: Use regular cursor, not DictCursor for DESCRIBE
            cur = mysql.connection.cursor()
            
            # First, check if table exists
            cur.execute("SHOW TABLES LIKE 'chat_history'")
            table_exists = cur.fetchone()
            
            if not table_exists:
                # Create new table with all columns
                cur.execute('''
                    CREATE TABLE chat_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        project_id INT,
                        message TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                        response TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                        context JSON,
                        ai_method VARCHAR(50) DEFAULT 'huggingface_router',
                        response_time_ms INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
                        INDEX idx_user_project (user_id, project_id),
                        INDEX idx_ai_method (ai_method)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                logger.info("✅ Chat history table created!")
            else:
                # Table exists, check for missing columns
                cur.execute("DESCRIBE chat_history")
                # FIX: Access tuple by index, not key
                columns = [row[0] for row in cur.fetchall()]
                
                # Add ai_method if missing
                if 'ai_method' not in columns:
                    try:
                        cur.execute('''
                            ALTER TABLE chat_history 
                            ADD COLUMN ai_method VARCHAR(50) DEFAULT 'huggingface_router' AFTER context
                        ''')
                        logger.info("✅ Added ai_method column")
                    except Exception as e:
                        logger.debug(f"Could not add ai_method: {e}")
                
                # Add response_time_ms if missing
                if 'response_time_ms' not in columns:
                    try:
                        cur.execute('''
                            ALTER TABLE chat_history 
                            ADD COLUMN response_time_ms INT AFTER ai_method
                        ''')
                        logger.info("✅ Added response_time_ms column")
                    except Exception as e:
                        logger.debug(f"Could not add response_time_ms: {e}")
            
            mysql.connection.commit()
            cur.close()
            logger.info("✅ Chat history table initialized!")
        except Exception as e:
            logger.error(f"⚠️ Chat table error: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("✅ Chat module initialized!")


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
                   COALESCE(SUM(area_hectares), 0) as total_area,
                   COUNT(CASE WHEN status = 'active' THEN 1 END) as active_projects
            FROM projects
            WHERE user_id = %s
        ''', (user_id,))
        
        stats = cur.fetchone()
        
        if not stats:
            cur.close()
            return {}
        
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
            'total_area': float(stats['total_area']),
            'active_projects': stats['active_projects'] or 0,
            'recent_projects': [
                f"{p['name']} ({p['project_type']}, {p['status']})"
                for p in recent_projects
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting user context: {e}")
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
        logger.error(f"Error getting project context: {e}")
        return None


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


# ========================
# PRIMARY: HUGGING FACE ROUTER (OpenAI-Compatible)
# ========================

def query_huggingface_router(user_message, context_info=""):
    """
    PRIMARY METHOD: Query Hugging Face using OpenAI-compatible router
    """
    if not hf_client:
        logger.warning("⚠️ Hugging Face client not initialized")
        return None
    
    try:
        logger.info(f"🤖 Querying Hugging Face Router with model: {HUGGINGFACE_MODEL}")
        
        start_time = time.time()
        
        # Build system prompt for land restoration context
        system_prompt = """You are RegenAI, a knowledgeable and supportive land restoration assistant specializing in:
- Vegetation health analysis (NDVI interpretation)
- Soil health and remediation
- Sustainable agriculture practices
- Climate-appropriate planting strategies
- Land degradation restoration techniques

Key guidelines:
- Provide practical, actionable advice
- Base recommendations on scientific best practices
- Consider local climate and soil conditions
- Be encouraging and supportive
- Keep responses clear and concise (2-3 paragraphs max)
- Focus on sustainable, long-term solutions
"""
        
        # Add user context if available
        if context_info:
            system_prompt += f"\nUser Context: {context_info}\n"
        
        # Get AI configuration from environment
        max_tokens = int(os.getenv('AI_MAX_TOKENS', 300))
        temperature = float(os.getenv('AI_TEMPERATURE', 0.7))
        
        # Call Hugging Face API using OpenAI-compatible interface
        completion = hf_client.chat.completions.create(
            model=HUGGINGFACE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        bot_reply = completion.choices[0].message.content
        
        if bot_reply and len(bot_reply.strip()) > 20:
            logger.info(f"✅ HF Router response received in {response_time}ms")
            return {
                'response': bot_reply.strip(),
                'method': 'huggingface_router',
                'model': HUGGINGFACE_MODEL,
                'response_time_ms': response_time
            }
        else:
            logger.warning(f"⚠️ HF Router returned empty/short response")
            return None
            
    except Exception as e:
        logger.error(f"❌ Hugging Face Router error: {str(e)}")
        return None


# ========================
# FALLBACK: DIRECT INFERENCE API
# ========================

def query_huggingface_inference(user_message, context_info=""):
    """
    FALLBACK METHOD: Query Hugging Face Inference API directly
    """
    if not HUGGINGFACE_API_KEY or HUGGINGFACE_API_KEY == 'your_key_here':
        return None
    
    logger.info("🔄 Trying fallback: Hugging Face Inference API")
    
    # Build prompt
    if context_info:
        prompt = f"""Land Restoration Context: {context_info}

User Question: {user_message}

Provide a helpful, detailed answer about land restoration, agriculture, or environmental management."""
    else:
        prompt = f"""Agricultural and Land Restoration Assistant

User Question: {user_message}

Provide a helpful, practical answer about land restoration, agriculture, NDVI, soil health, or planting."""
    
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try each working model
    for model_name in WORKING_MODELS:
        try:
            model_url = f"{HUGGINGFACE_API_URL}/{model_name}"
            logger.info(f"🔗 Trying: {model_name}")
            
            start_time = time.time()
            
            # Payload based on model type
            if "bart" in model_name.lower():
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_length": 250,
                        "min_length": 50,
                        "do_sample": False,
                        "early_stopping": True
                    },
                    "options": {"wait_for_model": True, "use_cache": True}
                }
            else:
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "do_sample": True,
                        "return_full_text": False
                    },
                    "options": {"wait_for_model": True, "use_cache": True}
                }
            
            response = requests.post(model_url, headers=headers, json=payload, timeout=30)
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text
                text = None
                if isinstance(result, list) and len(result) > 0:
                    first_item = result[0]
                    if isinstance(first_item, dict):
                        text = (first_item.get('summary_text') or 
                               first_item.get('generated_text') or 
                               first_item.get('text'))
                    elif isinstance(first_item, str):
                        text = first_item
                elif isinstance(result, dict):
                    text = (result.get('summary_text') or 
                           result.get('generated_text') or 
                           result.get('text'))
                
                if text and len(text.strip()) > 20:
                    text = text.strip()
                    if prompt in text:
                        text = text.replace(prompt, '').strip()
                    
                    # Remove artifacts
                    for artifact in ['Answer:', 'Response:', 'Summary:', 'CNN.com']:
                        text = text.replace(artifact, '').strip()
                    
                    if len(text) > 20:
                        logger.info(f"✅ Inference success: {model_name}")
                        return {
                            'response': text,
                            'method': 'huggingface_inference',
                            'model': model_name,
                            'response_time_ms': response_time
                        }
            
            elif response.status_code == 503:
                logger.info(f"⏳ Model loading...")
                time.sleep(10)
                continue
            
        except Exception as e:
            logger.error(f"❌ Error on {model_name}: {str(e)[:100]}")
            continue
    
    return None


# ========================
# INTELLIGENT FALLBACK
# ========================

def generate_intelligent_fallback(user_message, context_info=""):
    """Keyword-based fallback responses"""
    message_lower = user_message.lower()
    
    # NDVI queries
    if 'ndvi' in message_lower or 'vegetation index' in message_lower:
        if context_info and 'ndvi' in context_info.lower():
            import re
            ndvi_match = re.search(r'ndvi:\s*([\d.]+)', context_info.lower())
            if ndvi_match:
                ndvi = float(ndvi_match.group(1))
                if ndvi > 0.6:
                    return f"Your NDVI is {ndvi:.2f}, indicating excellent vegetation health! Your land shows dense, healthy vegetation cover. Continue your current management practices and monitor for any changes."
                elif ndvi > 0.4:
                    return f"Your NDVI is {ndvi:.2f}, showing good vegetation health. To improve further: 1) Add organic matter through composting, 2) Implement better water management, 3) Consider nitrogen-fixing cover crops."
                elif ndvi > 0.2:
                    return f"Your NDVI is {ndvi:.2f}, indicating fair vegetation health. Actions needed: 1) Implement cover cropping immediately, 2) Apply organic mulch 5-10cm thick, 3) Test and amend soil pH, 4) Ensure adequate irrigation."
                else:
                    return f"CRITICAL: Your NDVI is {ndvi:.2f}, showing severe vegetation stress. Immediate actions: 1) Increase irrigation, 2) Apply compost, 3) Plant drought-resistant species, 4) Consult an agronomist."
        
        return """NDVI (Normalized Difference Vegetation Index) measures vegetation health using satellite data.

Scale:
• 0.6-1.0 = Excellent (dense, healthy vegetation)
• 0.4-0.6 = Good (moderate healthy cover)
• 0.2-0.4 = Fair (sparse or stressed vegetation)
• Below 0.2 = Poor/Critical (severe stress)

Higher values = healthier vegetation. Select a project to see your specific NDVI analysis."""
    
    # Soil queries
    elif 'soil' in message_lower:
        if 'moisture' in message_lower:
            return """Soil moisture is crucial for plant growth and restoration success.

Optimal ranges:
• 40-60% = Ideal for most crops
• 30-40% = Acceptable, may need irrigation
• Below 30% = Water stress
• Above 70% = Risk of waterlogging

Improvement strategies:
1. Apply 5-10cm organic mulch
2. Install drip irrigation
3. Add compost for water retention
4. Plant deep-rooted cover crops
5. Create swales to capture runoff"""
        
        return """Soil health foundations for successful restoration:

Key indicators:
• pH: 6.0-7.5 optimal
• Organic matter: 3-5% minimum
• Moisture: 40-60% for growth
• Good structure and drainage

Improvement plan:
1. Test soil (pH, nutrients, organic matter)
2. Add compost (2-4 tons/hectare)
3. Use cover crops (legumes fix nitrogen)
4. Minimize tillage
5. Apply organic mulch
6. Monitor with annual testing"""
    
    # Planting timing
    elif any(word in message_lower for word in ['plant', 'season', 'when', 'timing']):
        current_month = datetime.now().month
        
        if current_month in [3, 4, 5]:
            return """OPTIMAL PLANTING SEASON: Long Rains (March-May)

This is the BEST time for planting in Kenya!

Actions:
• Plant indigenous trees NOW
• Establish conservation structures
• Maximize seedling establishment
• Priority: Acacia, Grevillea, Neem

Success tips:
1. Plant at rain start
2. Dig 60x60x60cm holes with compost
3. Space trees 3-4 meters apart
4. Stake tall seedlings
5. Mulch around base"""
        
        elif current_month in [10, 11, 12]:
            return """SECONDARY PLANTING: Short Rains (October-December)

Good for hardy, drought-resistant species.

Best species:
• Acacia varieties
• Grevillea robusta
• Moringa oleifera
• Drought-adapted indigenous species

Best practices:
1. Focus on drought-resistant varieties
2. Prepare irrigation backup
3. Apply thick mulch (10cm)
4. Water daily for first 2 weeks
5. Monitor closely"""
        
        else:
            return """CURRENT STATUS: Dry Season

NOT recommended for new planting.

Focus activities now:
• Maintain established plants
• Prepare planting sites
• Build conservation structures
• Source quality seedlings
• Test and amend soil
• Clear invasive species

Next planting windows:
• Primary: March-May (Long Rains) - BEST
• Secondary: Oct-Dec (Short Rains) - Good"""
    
    # Greetings
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return """Hello! I'm RegenAI, your land restoration assistant.

I can help with:
• Vegetation health analysis (NDVI)
• Soil health assessment
• Planting season guidance
• Restoration techniques
• Species selection
• Data interpretation

What would you like to know about your restoration project?"""
    
    # Default
    else:
        return """I'm your land restoration AI assistant!

I can help with:
• VEGETATION: NDVI analysis, trends, health assessment
• SOIL: Health evaluation, pH, moisture, amendments
• PLANTING: Seasonal timing, species selection
• TECHNIQUES: Restoration strategies, best practices
• DATA: Metric interpretation, progress tracking

Popular questions:
• "What is my current NDVI?"
• "When should I plant trees?"
• "How can I improve soil health?"
• "What restoration techniques should I use?"

Select a project and ask me anything!"""


# ========================
# MAIN AI QUERY
# ========================

def query_ai(user_message, context_info=""):
    """
    Cascading fallback strategy:
    1. Hugging Face Router (OpenAI-compatible) - PRIMARY
    2. Hugging Face Inference API - FALLBACK
    3. Intelligent keyword responses - LAST RESORT
    """
    logger.info(f"🚀 Query: {user_message[:50]}...")
    
    # Try primary
    result = query_huggingface_router(user_message, context_info)
    if result:
        return result
    
    # Try fallback
    result = query_huggingface_inference(user_message, context_info)
    if result:
        return result
    
    # Last resort
    logger.warning("⚠️ Using intelligent fallback")
    return {
        'response': generate_intelligent_fallback(user_message, context_info),
        'method': 'intelligent_fallback',
        'model': 'keyword_matching',
        'response_time_ms': 0
    }


# ========================
# ROUTES
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
        
        # Validate
        if not user_message:
            return jsonify({'success': False, 'error': 'Message required'}), 400
        
        if len(user_message) > 1000:
            return jsonify({'success': False, 'error': 'Message too long'}), 400
        
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid project_id'}), 400
        
        logger.info(f"💬 Message: '{user_message[:50]}...' | Project: {project_id}")
        
        # Get context
        user_context = get_user_context(session['user_id'])
        project_context = None
        
        if project_id:
            project_context = get_project_context(project_id)
        
        context_info = build_context_prompt(user_context, project_context)
        
        # Generate response
        result = query_ai(user_message, context_info)
        ai_response = result['response']
        ai_method = result['method']
        response_time = result.get('response_time_ms', 0)
        
        logger.info(f"🤖 Response ({ai_method}): {ai_response[:100]}...")
        
        # Save to database with comprehensive error handling
        try:
            # FIX: Use regular cursor for DESCRIBE
            cur = mysql.connection.cursor()
            
            # Check if new columns exist
            try:
                cur.execute("DESCRIBE chat_history")
                # FIX: Access tuple by index
                columns = [row[0] for row in cur.fetchall()]
                has_new_columns = 'ai_method' in columns and 'response_time_ms' in columns
            except Exception as desc_error:
                logger.error(f"Error checking columns: {desc_error}")
                has_new_columns = False
            
            # Prepare context data
            try:
                context_data = json.dumps({
                    'user': user_context, 
                    'project': project_context
                })
            except Exception as json_error:
                logger.error(f"Error encoding context to JSON: {json_error}")
                context_data = json.dumps({'error': 'Could not encode context'})
            
            # Try to insert
            try:
                if has_new_columns:
                    cur.execute('''
                        INSERT INTO chat_history 
                        (user_id, project_id, message, response, context, ai_method, response_time_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        session['user_id'],
                        project_id,
                        user_message,
                        ai_response,
                        context_data,
                        ai_method,
                        response_time
                    ))
                else:
                    # Store ai_method and response_time in context JSON for old schema
                    context_with_meta = json.dumps({
                        'user': user_context, 
                        'project': project_context,
                        'ai_method': ai_method,
                        'response_time_ms': response_time
                    })
                    cur.execute('''
                        INSERT INTO chat_history 
                        (user_id, project_id, message, response, context)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (
                        session['user_id'],
                        project_id,
                        user_message,
                        ai_response,
                        context_with_meta
                    ))
                
                mysql.connection.commit()
                logger.info("✅ Saved to database successfully")
                
            except Exception as insert_error:
                logger.error(f"⚠️ Insert error: {type(insert_error).__name__}: {insert_error}")
                mysql.connection.rollback()
                
                # Try basic insert without context as last resort
                try:
                    logger.warning("Attempting basic insert without context...")
                    if has_new_columns:
                        cur.execute('''
                            INSERT INTO chat_history 
                            (user_id, project_id, message, response, ai_method, response_time_ms)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            session['user_id'],
                            project_id,
                            user_message,
                            ai_response,
                            ai_method,
                            response_time
                        ))
                    else:
                        cur.execute('''
                            INSERT INTO chat_history 
                            (user_id, project_id, message, response)
                            VALUES (%s, %s, %s, %s)
                        ''', (
                            session['user_id'],
                            project_id,
                            user_message,
                            ai_response
                        ))
                    mysql.connection.commit()
                    logger.info("✅ Saved with basic insert")
                except Exception as basic_error:
                    logger.error(f"⚠️ Even basic insert failed: {type(basic_error).__name__}: {basic_error}")
                    mysql.connection.rollback()
            
            cur.close()
            
        except Exception as e:
            logger.error(f"⚠️ Database save error: {type(e).__name__}: {str(e)}")
            try:
                mysql.connection.rollback()
            except:
                pass
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'method': ai_method,
            'response_time_ms': response_time,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500


@chat_bp.route('/api/history')
def get_chat_history():
    """Get chat history"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        project_id = request.args.get('project_id')
        try:
            limit = min(int(request.args.get('limit', 20)), 100)
        except:
            limit = 20
        
        if project_id:
            try:
                project_id = int(project_id)
                cur.execute('''
                    SELECT * FROM chat_history
                    WHERE user_id = %s AND project_id = %s
                    ORDER BY created_at DESC LIMIT %s
                ''', (session['user_id'], project_id, limit))
            except:
                return jsonify({'success': False, 'error': 'Invalid project_id'}), 400
        else:
            cur.execute('''
                SELECT * FROM chat_history
                WHERE user_id = %s
                ORDER BY created_at DESC LIMIT %s
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
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/api/clear', methods=['POST'])
def clear_chat_history():
    """Clear chat history"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        
        cur = mysql.connection.cursor()
        
        if project_id:
            try:
                project_id = int(project_id)
                cur.execute('''
                    DELETE FROM chat_history
                    WHERE user_id = %s AND project_id = %s
                ''', (session['user_id'], project_id))
            except:
                return jsonify({'success': False, 'error': 'Invalid project_id'}), 400
        else:
            cur.execute('''
                DELETE FROM chat_history
                WHERE user_id = %s
            ''', (session['user_id'],))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error: {e}")
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
            try:
                project_context = get_project_context(int(project_id))
                
                if project_context:
                    if project_context.get('current_ndvi', 0) < 0.4:
                        suggestions.insert(0, "Why is my vegetation health low?")
                    
                    if project_context.get('degradation') in ['severe', 'critical']:
                        suggestions.insert(0, "What emergency actions should I take?")
            except:
                pass
        
        return jsonify({
            'success': True,
            'suggestions': suggestions[:5]
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({
            'success': True,
            'suggestions': [
                "Tell me about NDVI",
                "How do I start restoration?",
                "What are the best native species?"
            ]
        })


@chat_bp.route('/api/test', methods=['GET'])
def test_chat():
    """Test endpoint to verify chat is working"""
    
    # Check HF Router client
    hf_router_status = "✅ Configured" if hf_client else "❌ Not configured"
    hf_api_status = "✅ Configured" if (HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != 'your_key_here') else "❌ Not configured"
    
    # Check OpenAI package
    openai_status = "✅ Installed" if OPENAI_AVAILABLE else "❌ Not installed"
    
    # Check database columns
    db_status = "Unknown"
    db_columns = []
    db_details = {}
    try:
        cur = mysql.connection.cursor()
        cur.execute("DESCRIBE chat_history")
        columns_data = cur.fetchall()
        # FIX: Access tuple by index
        db_columns = [row[0] for row in columns_data]
        
        # Get detailed column info
        for row in columns_data:
            db_details[row[0]] = {
                'type': row[1],
                'null': row[2],
                'key': row[3],
                'default': row[4]
            }
        
        cur.close()
        
        has_ai_method = 'ai_method' in db_columns
        has_response_time = 'response_time_ms' in db_columns
        
        if has_ai_method and has_response_time:
            db_status = "✅ All columns present"
        elif has_ai_method or has_response_time:
            db_status = "⚠️ Some columns missing"
        else:
            db_status = "⚠️ New columns not added yet (run migration)"
    except Exception as e:
        db_status = f"❌ Error: {str(e)}"
    
    # Determine which methods are available
    available_methods = []
    if hf_client:
        available_methods.append("Hugging Face Router (PRIMARY)")
    if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != 'your_key_here':
        available_methods.append("Hugging Face Inference API (FALLBACK)")
    available_methods.append("Intelligent Fallback (ALWAYS)")
    
    return jsonify({
        'success': True,
        'message': 'Chat API is operational!',
        'status': {
            'openai_package': openai_status,
            'huggingface_router': hf_router_status,
            'huggingface_inference': hf_api_status,
            'database': db_status,
            'database_columns': db_columns,
            'database_details': db_details
        },
        'configuration': {
            'model': HUGGINGFACE_MODEL,
            'base_url': HUGGINGFACE_BASE_URL,
            'fallback_models': WORKING_MODELS,
            'max_tokens': int(os.getenv('AI_MAX_TOKENS', 300)),
            'temperature': float(os.getenv('AI_TEMPERATURE', 0.7))
        },
        'available_methods': available_methods,
        'cascade_order': [
            '1. Hugging Face Router (OpenAI-compatible) - Best quality',
            '2. Hugging Face Inference API (Direct) - Good fallback',
            '3. Intelligent Fallback (Keyword-based) - Always works'
        ]
    })