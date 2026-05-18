from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_bcrypt import Bcrypt
from database import db, User

auth = Blueprint('auth', __name__, url_prefix='')
bcrypt = Bcrypt()

# ── Register ──────────────────────────────────────────
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')
        confirm  = request.form.get('confirm')        

        # FIX 3: Check passwords match
        if password != confirm:
            return render_template('register.html', error='Passwords do not match')

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')

        # Hash password & save user
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user  = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        session['user_id']  = new_user.id
        session['username'] = new_user.username

        return redirect('/setup')                     

    return render_template('register.html')

# ── Login ─────────────────────────────────────────────
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # FIX 2: correct indentation
        if not user or not bcrypt.check_password_hash(user.password, password):
            return render_template('login.html', error='Invalid email or password')

        # Save user session
        session['user_id']  = user.id
        session['username'] = user.username
        return redirect(url_for('auth.dashboard'))

    return render_template('login.html')

# ── Dashboard (protected) ─────────────────────────────
@auth.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', username=session['username'])

# ── Logout ────────────────────────────────────────────
@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))