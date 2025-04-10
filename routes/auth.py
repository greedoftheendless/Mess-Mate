from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User
from flask_mail import Message
from extensions import mail
import jwt
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
            
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        new_user.email_verified = True  # Set email as verified by default
        new_user.is_active = True  # Set user as active
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. You can now login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'error')
            return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('Your account is not active. Please contact support.', 'error')
            return redirect(url_for('auth.login'))

        if not user.email_verified:
            flash('Please verify your email before logging in.', 'error')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect(url_for('main.dashboard'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = generate_reset_token(user.email)
            send_password_reset_email(user.email, token)
            
        flash('Check your email for the instructions to reset your password', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    try:
        email = verify_reset_token(token)
    except:
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('auth.reset_password_request'))
        
    if request.method == 'POST':
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(request.form.get('password'))
            db.session.commit()
            flash('Your password has been reset.', 'success')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/reset_password.html')

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    try:
        email = verify_verification_token(token)
    except:
        flash('Invalid or expired verification token', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=email).first()
    if user:
        user.email_verified = True
        db.session.commit()
        flash('Email verified successfully. You can now login.', 'success')
    
    return redirect(url_for('auth.login'))

def generate_verification_token(email):
    return jwt.encode(
        {'email': email, 'exp': datetime.utcnow() + timedelta(hours=24)},
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

def verify_verification_token(token):
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return data['email']
    except:
        return None

def generate_reset_token(email):
    return jwt.encode(
        {'reset_password': email, 'exp': datetime.utcnow() + timedelta(hours=1)},
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

def verify_reset_token(token):
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return data['reset_password']
    except:
        return None

def send_verification_email(email, token):
    msg = Message('Verify Your Email',
                  recipients=[email])
    msg.body = f'''
    To verify your email, visit the following link:
    {url_for('auth.verify_email', token=token, _external=True)}
    
    If you did not make this request then simply ignore this email.
    '''
    mail.send(msg)

def send_password_reset_email(email, token):
    msg = Message('Password Reset Request',
                  recipients=[email])
    msg.body = f'''
    To reset your password, visit the following link:
    {url_for('auth.reset_password', token=token, _external=True)}
    
    If you did not make this request then simply ignore this email.
    '''
    mail.send(msg)