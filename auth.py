import random
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from database import db, User, OTPCode

auth   = Blueprint('auth', __name__, url_prefix='')
bcrypt = Bcrypt()
mail   = Mail()


# ── Helpers ───────────────────────────────────────────
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(to_email, otp_code, purpose):
    subject = '🐝 Budget Bee — Your Verification Code'
    if purpose == 'register':
        body_html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#FEFAF2;border-radius:12px">
          <h2 style="color:#C47B0E;font-size:22px;margin-bottom:8px">🐝 Welcome to Budget Bee!</h2>
          <p style="color:#5a4a3a;font-size:14px;margin-bottom:24px">
            Use the code below to verify your email and activate your account.
            It expires in <strong>10 minutes</strong>.
          </p>
          <div style="background:#FDF3DC;border:1px solid rgba(196,123,14,0.3);border-radius:10px;padding:24px;text-align:center;margin-bottom:24px">
            <div style="font-size:36px;font-weight:700;letter-spacing:10px;color:#C47B0E">{otp_code}</div>
          </div>
          <p style="color:#9A8878;font-size:12px">If you didn't create a Budget Bee account, ignore this email.</p>
        </div>"""
    else:
        body_html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#FEFAF2;border-radius:12px">
          <h2 style="color:#C47B0E;font-size:22px;margin-bottom:8px">🔐 Password Change Request</h2>
          <p style="color:#5a4a3a;font-size:14px;margin-bottom:24px">
            Someone requested a password change on your Budget Bee account.
            Enter this code to confirm. It expires in <strong>10 minutes</strong>.
          </p>
          <div style="background:#FDF3DC;border:1px solid rgba(196,123,14,0.3);border-radius:10px;padding:24px;text-align:center;margin-bottom:24px">
            <div style="font-size:36px;font-weight:700;letter-spacing:10px;color:#C47B0E">{otp_code}</div>
          </div>
          <p style="color:#9A8878;font-size:12px">If you did not request this, your password was not changed.</p>
        </div>"""

    msg = Message(subject=subject, recipients=[to_email], html=body_html)
    mail.send(msg)

def create_otp(email, purpose):
    # Invalidate any existing unused OTPs for this email + purpose
    OTPCode.query.filter_by(email=email, purpose=purpose, used=False).delete()
    db.session.commit()
    code = generate_otp()
    otp  = OTPCode(email=email, code=code, purpose=purpose)
    db.session.add(otp)
    db.session.commit()
    return code


# ── Register ──────────────────────────────────────────
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')

        if password != confirm:
            return render_template('register.html', error='Passwords do not match')
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')

        # Stash form data in session so we can create the account after OTP
        session['pending_register'] = {
            'username': username,
            'email':    email,
            'password': bcrypt.generate_password_hash(password).decode('utf-8')
        }

        # Send OTP
        try:
            code = create_otp(email, 'register')
            send_otp_email(email, code, 'register')
        except Exception as e:
            current_app.logger.error(f'Mail error: {e}')
            return render_template('register.html', error='Could not send verification email. Check mail config.')

        return redirect(url_for('auth.verify_register'))

    return render_template('register.html')


@auth.route('/verify-register', methods=['GET', 'POST'])
def verify_register():
    pending = session.get('pending_register')
    if not pending:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        email   = pending['email']

        otp = OTPCode.query.filter_by(email=email, purpose='register', used=False)\
                           .order_by(OTPCode.created_at.desc()).first()

        if not otp:
            return render_template('verify_otp.html', purpose='register',
                                   email=email, error='No verification code found. Please register again.')
        if otp.is_expired():
            return render_template('verify_otp.html', purpose='register',
                                   email=email, error='Code has expired. Please register again.')
        if otp.code != entered:
            return render_template('verify_otp.html', purpose='register',
                                   email=email, error='Incorrect code. Please try again.')

        # OTP valid — create the user
        otp.used = True
        new_user = User(
            username    = pending['username'],
            email       = pending['email'],
            password    = pending['password'],
            is_verified = True
        )
        db.session.add(new_user)
        db.session.commit()

        session.pop('pending_register', None)
        session['user_id']  = new_user.id
        session['username'] = new_user.username
        return redirect('/setup')

    return render_template('verify_otp.html', purpose='register', email=pending['email'])


@auth.route('/resend-otp/<purpose>')
def resend_otp(purpose):
    if purpose == 'register':
        pending = session.get('pending_register')
        if not pending:
            return redirect(url_for('auth.register'))
        email = pending['email']
    elif purpose == 'password':
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user  = User.query.get(session['user_id'])
        email = user.email
    else:
        return redirect('/')

    try:
        code = create_otp(email, purpose)
        send_otp_email(email, code, purpose)
        flash('A new code has been sent to your email.', 'success')
    except Exception as e:
        current_app.logger.error(f'Mail error: {e}')
        flash('Could not resend. Please try again.', 'error')

    return redirect(url_for('auth.verify_register') if purpose == 'register' else url_for('verify_password_otp'))


# ── Login ─────────────────────────────────────────────
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.check_password_hash(user.password, password):
            return render_template('login.html', error='Invalid email or password')

        session['user_id']  = user.id
        session['username'] = user.username
        return redirect('/dashboard')

    return render_template('login.html')


# ── Dashboard (fallback — main app overrides this) ────
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