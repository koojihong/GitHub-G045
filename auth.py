from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_bcrypt import Bcrypt
from database import db, User

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# ── Register ──────────────────────────────────────────
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # Hash password & save user
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user  = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('auth.login'))

    return render_template('register.html')

# ── Login ─────────────────────────────────────────────
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # Verify user and password
        if not user or not bcrypt.check_password_hash(user.password, password):
            return jsonify({'error': 'Invalid email or password'}), 401

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