from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
import secrets
from datetime import datetime, timedelta

# Create blueprint
main = Blueprint('main', __name__)

# We'll get mysql from current_app
def get_mysql():
    from run import mysql
    return mysql

def get_mail():
    from run import mail
    return mail

@main.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page route"""
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip().lower()
        age = request.form.get('age', '').strip()
        location = request.form.get('location', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        
        # Validation
        if not all([first_name, last_name, email, age, location, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        # Validate age
        try:
            age_int = int(age)
            if age_int < 13 or age_int > 120:
                flash('Age must be between 13 and 120', 'error')
                return render_template('register.html')
        except ValueError:
            flash('Invalid age format', 'error')
            return render_template('register.html')
        
        # Validate password match
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Validate password length
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('register.html')
        
        try:
            mysql = get_mysql()
            cur = mysql.connection.cursor()
            
            # Check if email already exists
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            existing_user = cur.fetchone()
            
            if existing_user:
                flash('Email already registered. Please login or use a different email.', 'error')
                cur.close()
                return render_template('register.html')
            
            # Hash password
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            
            # Insert new user
            cur.execute('''
                INSERT INTO users (first_name, last_name, email, age, location, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (first_name, last_name, email, age_int, location, hashed_password))
            
            mysql.connection.commit()
            cur.close()
            
            flash('Registration successful! Please login to continue.', 'success')
            return redirect(url_for('main.login'))
            
        except Exception as e:
            flash('An error occurred during registration. Please try again.', 'error')
            print(f"Registration error: {e}")
            return render_template('register.html')
    
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember')
        
        # Validation
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        try:
            mysql = get_mysql()
            cur = mysql.connection.cursor()
            
            # Get user by email
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            cur.close()
            
            if user and check_password_hash(user['password_hash'], password):
                # Set session with all user data
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['first_name'] = user['first_name']
                session['last_name'] = user['last_name']
                session['user_name'] = f"{user['first_name']} {user['last_name']}"
                
                # Set session to permanent if remember me is checked
                if remember:
                    session.permanent = True
                
                flash(f'Welcome back, {user["first_name"]}!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid email or password', 'error')
                return render_template('login.html')
                
        except Exception as e:
            flash('An error occurred during login. Please try again.', 'error')
            print(f"Login error: {e}")
            return render_template('login.html')
    
    return render_template('login.html')

@main.route('/dashboard')
def dashboard():
    """Dashboard page - requires login"""
    if 'user_id' not in session:
        flash('Please login to access the dashboard', 'warning')
        return redirect(url_for('main.login'))
    
    try:
        mysql = get_mysql()
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        cur.close()
        
        if user:
            return render_template('dashboard.html', user=user)
        else:
            session.clear()
            flash('User not found. Please login again.', 'error')
            return redirect(url_for('main.login'))
            
    except Exception as e:
        flash('An error occurred. Please try again.', 'error')
        print(f"Dashboard error: {e}")
        return redirect(url_for('main.login'))

@main.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('main.home'))

@main.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Password reset request page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Email is required', 'error')
            return render_template('reset_password.html')
        
        try:
            mysql = get_mysql()
            mail = get_mail()
            cur = mysql.connection.cursor()
            
            # Check if user exists
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            
            if user:
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                reset_expiry = datetime.now() + timedelta(hours=1)
                
                # Store token in database
                cur.execute('''
                    UPDATE users 
                    SET reset_token = %s, reset_token_expiry = %s 
                    WHERE email = %s
                ''', (reset_token, reset_expiry, email))
                mysql.connection.commit()
                
                # Send reset email
                reset_url = url_for('main.reset_password_confirm', token=reset_token, _external=True)
                
                msg = Message(
                    'Password Reset Request - RegenArdhi',
                    sender=('RegenArdhi', 'noreply@regenardhi.org'),
                    recipients=[email]
                )
                msg.body = f'''Hello {user["first_name"]},

You requested to reset your password for your RegenArdhi account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The RegenArdhi Team
'''
                
                mail.send(msg)
                flash('Password reset instructions have been sent to your email', 'success')
            else:
                # Don't reveal if email exists or not for security
                flash('If an account exists with this email, you will receive password reset instructions', 'info')
            
            cur.close()
            return redirect(url_for('main.login'))
            
        except Exception as e:
            flash('An error occurred. Please try again.', 'error')
            print(f"Password reset error: {e}")
            return render_template('reset_password.html')
    
    return render_template('reset_password.html')

@main.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_confirm(token):
    """Password reset confirmation page"""
    try:
        mysql = get_mysql()
        cur = mysql.connection.cursor()
        
        # Find user with valid token
        cur.execute('''
            SELECT * FROM users 
            WHERE reset_token = %s AND reset_token_expiry > %s
        ''', (token, datetime.now()))
        user = cur.fetchone()
        
        if not user:
            flash('Invalid or expired reset link', 'error')
            cur.close()
            return redirect(url_for('main.reset_password'))
        
        if request.method == 'POST':
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirmPassword', '')
            
            # Validation
            if not password or not confirm_password:
                flash('All fields are required', 'error')
                return render_template('reset_password_confirm.html', token=token)
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('reset_password_confirm.html', token=token)
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'error')
                return render_template('reset_password_confirm.html', token=token)
            
            # Hash new password
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            
            # Update password and clear reset token
            cur.execute('''
                UPDATE users 
                SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL 
                WHERE id = %s
            ''', (hashed_password, user['id']))
            mysql.connection.commit()
            cur.close()
            
            flash('Your password has been reset successfully! Please login with your new password.', 'success')
            return redirect(url_for('main.login'))
        
        cur.close()
        return render_template('reset_password_confirm.html', token=token)
        
    except Exception as e:
        flash('An error occurred. Please try again.', 'error')
        print(f"Password reset confirm error: {e}")
        return redirect(url_for('main.reset_password'))

# FIXED: Redirect to the projects blueprint instead of creating a loop
@main.route('/projects')
def projects():
    """Redirect to projects blueprint"""
    if 'user_id' not in session:
        flash('Please login to access projects', 'warning')
        return redirect(url_for('main.login'))
    # Redirect to the projects blueprint (projects.projects), NOT main.projects
    return redirect(url_for('projects.projects'))