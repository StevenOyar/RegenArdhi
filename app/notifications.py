import os
from flask import Blueprint, request, jsonify, session, render_template
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
import json

# Create Blueprint
notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

# MySQL connection (passed from main app)
mysql = None

# Notification types and their configurations
NOTIFICATION_TYPES = {
    'project_created': {
        'icon': 'check-circle',
        'color': '#10b981',
        'title': '🌿 Project Created',
        'priority': 'high'
    },
    'project_updated': {
        'icon': 'edit',
        'color': '#3b82f6',
        'title': 'Project Updated',
        'priority': 'low'
    },
    'status_changed': {
        'icon': 'exchange-alt',
        'color': '#f59e0b',
        'title': 'Status Changed',
        'priority': 'medium'
    },
    'project_completed': {
        'icon': 'trophy',
        'color': '#8b5cf6',
        'title': '🎉 Project Completed',
        'priority': 'high'
    },
    'project_deleted': {
        'icon': 'trash',
        'color': '#ef4444',
        'title': 'Project Deleted',
        'priority': 'medium'
    },
    'progress_updated': {
        'icon': 'chart-line',
        'color': '#06b6d4',
        'title': 'Progress Updated',
        'priority': 'low'
    },
    'analysis_complete': {
        'icon': 'brain',
        'color': '#8b5cf6',
        'title': '🧠 AI Analysis Complete',
        'priority': 'high'
    },
    'milestone_reached': {
        'icon': 'flag-checkered',
        'color': '#ec4899',
        'title': '🎯 Milestone Reached',
        'priority': 'high'
    },
    'system': {
        'icon': 'info-circle',
        'color': '#6b7280',
        'title': 'System Notification',
        'priority': 'low'
    }
}

# ========================
# DATABASE INITIALIZATION
# ========================

def init_notifications(app, mysql_instance):
    """Initialize notifications module with Flask app and MySQL instance"""
    global mysql
    mysql = mysql_instance
    
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            
            # Create notifications table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    icon VARCHAR(50),
                    color VARCHAR(20),
                    priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
                    link VARCHAR(500),
                    project_id INT,
                    is_read BOOLEAN DEFAULT FALSE,
                    is_archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP NULL,
                    
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_is_read (is_read),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Create notification preferences table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    email_notifications BOOLEAN DEFAULT TRUE,
                    push_notifications BOOLEAN DEFAULT TRUE,
                    project_created BOOLEAN DEFAULT TRUE,
                    project_updated BOOLEAN DEFAULT TRUE,
                    status_changed BOOLEAN DEFAULT TRUE,
                    project_completed BOOLEAN DEFAULT TRUE,
                    progress_updated BOOLEAN DEFAULT FALSE,
                    analysis_complete BOOLEAN DEFAULT TRUE,
                    milestone_reached BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            mysql.connection.commit()
            cur.close()
            print("✅ Notifications tables initialized successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing notifications tables: {e}")
            import traceback
            traceback.print_exc()

# ========================
# HELPER FUNCTIONS
# ========================

def create_notification(user_id, notification_type, message, project_id=None, project_name=None):
    """
    Create a new notification - FIXED FOR EMOJI SUPPORT
    
    Args:
        user_id: User ID to send notification to
        notification_type: Type of notification (from NOTIFICATION_TYPES)
        message: Notification message
        project_id: Optional project ID
        project_name: Optional project name for link text
    """
    try:
        config = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES['system'])
        
        # Build link if project_id provided
        link = None
        if project_id:
            link = f"/projects/{project_id}"
        
        # EMOJI FIX: Remove emojis from title and message if database doesn't support utf8mb4
        # Option 1: Remove emojis completely
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        
        clean_title = emoji_pattern.sub('', config['title'])
        clean_message = emoji_pattern.sub('', message)
        
        # If title is now empty, use a default
        if not clean_title.strip():
            clean_title = notification_type.replace('_', ' ').title()
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            INSERT INTO notifications 
            (user_id, type, title, message, icon, color, priority, link, project_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            user_id,
            notification_type,
            clean_title.strip(),
            clean_message.strip(),
            config['icon'],
            config['color'],
            config['priority'],
            link,
            project_id
        ))
        
        mysql.connection.commit()
        notification_id = cur.lastrowid
        cur.close()
        
        print(f"✅ Notification created: {notification_type} for user {user_id}")
        return notification_id
        
    except Exception as e:
        print(f"❌ Error creating notification: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    
def get_user_preferences(user_id):
    """Get user notification preferences"""
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        
        cur.execute('SELECT * FROM notification_preferences WHERE user_id = %s', (user_id,))
        prefs = cur.fetchone()
        
        if not prefs:
            # Create default preferences
            cur.execute('''
                INSERT INTO notification_preferences (user_id)
                VALUES (%s)
            ''', (user_id,))
            mysql.connection.commit()
            
            cur.execute('SELECT * FROM notification_preferences WHERE user_id = %s', (user_id,))
            prefs = cur.fetchone()
        
        cur.close()
        return prefs
        
    except Exception as e:
        print(f"Error getting preferences: {e}")
        return None

# ========================
# API ROUTES
# ========================

@notifications_bp.route('/api/list')
def api_list_notifications():
    """Get all notifications for the logged-in user"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        from MySQLdb.cursors import DictCursor
        cur = mysql.connection.cursor(DictCursor)
        user_id = session.get('user_id')
        
        # Get notifications
        cur.execute('''
            SELECT * FROM notifications
            WHERE user_id = %s AND is_archived = FALSE
            ORDER BY created_at DESC
            LIMIT 50
        ''', (user_id,))
        
        notifications = cur.fetchall()
        
        # Get unread count
        cur.execute('''
            SELECT COUNT(*) as count
            FROM notifications
            WHERE user_id = %s AND is_read = FALSE AND is_archived = FALSE
        ''', (user_id,))
        
        unread_count = cur.fetchone()['count']
        
        cur.close()
        
        # Convert dates to strings
        for notif in notifications:
            if notif.get('created_at'):
                notif['created_at'] = str(notif['created_at'])
            if notif.get('read_at'):
                notif['read_at'] = str(notif['read_at'])
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count
        })
        
    except Exception as e:
        print(f"Error listing notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/api/mark-read', methods=['POST'])
def api_mark_read():
    """Mark notification(s) as read"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        notification_id = data.get('notification_id')
        
        cur = mysql.connection.cursor()
        
        if notification_id:
            # Mark specific notification as read
            cur.execute('''
                UPDATE notifications
                SET is_read = TRUE, read_at = %s
                WHERE id = %s AND user_id = %s
            ''', (datetime.now(), notification_id, user_id))
        else:
            # Mark all as read
            cur.execute('''
                UPDATE notifications
                SET is_read = TRUE, read_at = %s
                WHERE user_id = %s AND is_read = FALSE
            ''', (datetime.now(), user_id))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error marking as read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/api/archive', methods=['POST'])
def api_archive():
    """Archive notification(s)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        notification_id = data.get('notification_id')
        
        cur = mysql.connection.cursor()
        
        if notification_id:
            # Archive specific notification
            cur.execute('''
                UPDATE notifications
                SET is_archived = TRUE
                WHERE id = %s AND user_id = %s
            ''', (notification_id, user_id))
        else:
            # Archive all read notifications
            cur.execute('''
                UPDATE notifications
                SET is_archived = TRUE
                WHERE user_id = %s AND is_read = TRUE
            ''', (user_id,))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error archiving: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/api/preferences')
def api_get_preferences():
    """Get user notification preferences"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        prefs = get_user_preferences(user_id)
        
        if prefs:
            # Convert to dict if needed
            if hasattr(prefs, 'keys'):
                prefs = dict(prefs)
            
            # Convert dates to strings
            if prefs.get('created_at'):
                prefs['created_at'] = str(prefs['created_at'])
            if prefs.get('updated_at'):
                prefs['updated_at'] = str(prefs['updated_at'])
            
            return jsonify({'success': True, 'preferences': prefs})
        else:
            return jsonify({'success': False, 'error': 'Preferences not found'}), 404
            
    except Exception as e:
        print(f"Error getting preferences: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/api/preferences/update', methods=['POST'])
def api_update_preferences():
    """Update user notification preferences"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # Build update query dynamically
        allowed_fields = [
            'email_notifications', 'push_notifications',
            'project_created', 'project_updated', 'status_changed',
            'project_completed', 'progress_updated', 'analysis_complete',
            'milestone_reached'
        ]
        
        update_fields = []
        update_values = []
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_values.append(bool(data[field]))
        
        if not update_fields:
            return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
        cur = mysql.connection.cursor()
        
        query = f'''
            UPDATE notification_preferences
            SET {', '.join(update_fields)}
            WHERE user_id = %s
        '''
        update_values.append(user_id)
        
        cur.execute(query, tuple(update_values))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating preferences: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/api/unread-count')
def api_unread_count():
    """Get count of unread notifications"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_id = session.get('user_id')
        
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT COUNT(*) as count
            FROM notifications
            WHERE user_id = %s AND is_read = FALSE AND is_archived = FALSE
        ''', (user_id,))
        
        result = cur.fetchone()
        count = result[0] if result else 0
        
        cur.close()
        
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        print(f"Error getting unread count: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/api/delete', methods=['DELETE'])
def api_delete():
    """Delete a notification"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        notification_id = data.get('notification_id')
        
        if not notification_id:
            return jsonify({'success': False, 'error': 'notification_id required'}), 400
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            DELETE FROM notifications
            WHERE id = %s AND user_id = %s
        ''', (notification_id, user_id))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error deleting notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================
# MAIN ROUTES
# ========================

@notifications_bp.route('/')
def notifications_page():
    """Render notifications page"""
    if 'user_id' not in session:
        from flask import redirect, url_for
        return redirect(url_for('main.login'))
    
    return render_template('notifications.html', user=session)

# ========================
# NOTIFICATION TRIGGERS
# ========================

def notify_project_created(user_id, project_id, project_name):
    """Notify when project is created"""
    message = f"🌿 '{project_name}' has been successfully created with AI analysis!"
    create_notification(user_id, 'project_created', message, project_id, project_name)

def notify_project_updated(user_id, project_id, project_name):
    """Notify when project is updated"""
    message = f"'{project_name}' has been updated"
    create_notification(user_id, 'project_updated', message, project_id, project_name)

def notify_status_changed(user_id, project_id, project_name, old_status, new_status):
    """Notify when project status changes"""
    status_messages = {
        'planning': '📋 is now in planning phase',
        'active': '▶️ is now active',
        'completed': '🎉 has been completed!',
        'paused': '⏸️ has been paused'
    }
    
    message = f"'{project_name}' {status_messages.get(new_status, f'status changed to {new_status}')}"
    
    # Use completed notification type if status is completed
    notif_type = 'project_completed' if new_status == 'completed' else 'status_changed'
    create_notification(user_id, notif_type, message, project_id, project_name)

def notify_progress_updated(user_id, project_id, project_name, progress):
    """Notify when project progress is updated"""
    message = f"'{project_name}' progress updated to {progress}%"
    create_notification(user_id, 'progress_updated', message, project_id, project_name)
    
    # Check for milestone achievements
    milestones = [25, 50, 75]
    if progress in milestones:
        milestone_message = f"🎯 '{project_name}' reached {progress}% completion milestone!"
        create_notification(user_id, 'milestone_reached', milestone_message, project_id, project_name)

def notify_project_deleted(user_id, project_name):
    """Notify when project is deleted"""
    message = f"'{project_name}' has been deleted"
    create_notification(user_id, 'project_deleted', message)

def notify_analysis_complete(user_id, project_id, project_name):
    """Notify when AI analysis is complete"""
    message = f"🧠 AI analysis completed for '{project_name}'"
    create_notification(user_id, 'analysis_complete', message, project_id, project_name)

# ========================
# EXPORT HELPER FUNCTION
# ========================

# Make create_notification available to other modules
__all__ = [
    'notifications_bp', 
    'init_notifications', 
    'create_notification',
    'notify_project_created',
    'notify_project_updated',
    'notify_status_changed',
    'notify_progress_updated',
    'notify_project_deleted',
    'notify_analysis_complete'
]