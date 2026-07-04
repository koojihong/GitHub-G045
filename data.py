from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_mail import Mail, Message
from datetime import timedelta
import sqlite3, hashlib, secrets, datetime, random
from functools import wraps

app = Flask(__name__)
app.secret_key = "budgetbee-secret-key-2025"
app.permanent_session_lifetime = timedelta(minutes=30)

# ── Flask-Mail config (update these with your Gmail) ──
app.config['MAIL_SERVER']         = 'smtp.gmail.com'
app.config['MAIL_PORT']           = 587
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = 'gamertonydoesgaming@gmail.com'   # ← change this
app.config['MAIL_PASSWORD']       = 'bdjzrwwokybisish'      # ← change this (Gmail App Password)
app.config['MAIL_DEFAULT_SENDER'] = ('Budget Bee', 'gamertonydoesgaming@gmail.com')  # ← change this

mail = Mail(app)

DB = "users.db"

# ── DATABASE ──────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL UNIQUE,
            email      TEXT    NOT NULL UNIQUE,
            password   TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now'))
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            token      TEXT    NOT NULL UNIQUE,
            expires_at TEXT    NOT NULL,
            used       INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            description TEXT    NOT NULL,
            category    TEXT    DEFAULT 'others',
            amount      REAL    NOT NULL,
            date        TEXT    DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            month       TEXT    NOT NULL,
            budget      REAL    NOT NULL,
            alert_pct   INTEGER DEFAULT 70,
            UNIQUE(user_id, month),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS savings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            goal_name   TEXT    NOT NULL,
            target      REAL    NOT NULL,
            saved       REAL    DEFAULT 0,
            target_date TEXT,
            created_at  TEXT    DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            description TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            type        TEXT    DEFAULT 'salary',
            date        TEXT    DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    NOT NULL,
            code       TEXT    NOT NULL,
            purpose    TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now')),
            used       INTEGER DEFAULT 0
        )
    """)
    db.commit()
    db.close()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ── OTP HELPERS ───────────────────────────────────────────────────────────

def create_otp(email, purpose):
    """Delete any existing unused OTPs for this email+purpose, then create a new one."""
    db = get_db()
    db.execute("DELETE FROM otp_codes WHERE email=? AND purpose=? AND used=0", (email, purpose))
    code = str(random.randint(100000, 999999))
    db.execute("INSERT INTO otp_codes (email, code, purpose) VALUES (?,?,?)", (email, code, purpose))
    db.commit()
    db.close()
    return code

def verify_otp(email, purpose, entered_code):
    """Returns 'ok', 'expired', 'wrong', or 'notfound'."""
    db  = get_db()
    row = db.execute(
        "SELECT * FROM otp_codes WHERE email=? AND purpose=? AND used=0 ORDER BY id DESC LIMIT 1",
        (email, purpose)
    ).fetchone()
    if not row:
        db.close()
        return 'notfound'
    created = datetime.datetime.fromisoformat(row["created_at"])
    if (datetime.datetime.utcnow() - created).total_seconds() > 600:
        db.close()
        return 'expired'
    if row["code"] != entered_code:
        db.close()
        return 'wrong'
    db.execute("UPDATE otp_codes SET used=1 WHERE id=?", (row["id"],))
    db.commit()
    db.close()
    return 'ok'

def send_otp_email(to_email, code, purpose):
    if purpose == 'register':
        subject = '🐝 Budget Bee — Verify your email'
        body = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#FEFAF2;border-radius:12px">
          <h2 style="color:#C47B0E">🐝 Welcome to Budget Bee!</h2>
          <p style="color:#5a4a3a;font-size:14px;margin-bottom:24px">Use this code to verify your email. Expires in <strong>10 minutes</strong>.</p>
          <div style="background:#FDF3DC;border:1px solid rgba(196,123,14,0.3);border-radius:10px;padding:24px;text-align:center">
            <div style="font-size:36px;font-weight:700;letter-spacing:10px;color:#C47B0E">{code}</div>
          </div>
          <p style="color:#9A8878;font-size:12px;margin-top:20px">If you didn't create a Budget Bee account, ignore this email.</p>
        </div>"""
    else:
        subject = '🔐 Budget Bee — Password change verification'
        body = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#FEFAF2;border-radius:12px">
          <h2 style="color:#C47B0E">🔐 Password Change Request</h2>
          <p style="color:#5a4a3a;font-size:14px;margin-bottom:24px">Enter this code to confirm your password change. Expires in <strong>10 minutes</strong>.</p>
          <div style="background:#FDF3DC;border:1px solid rgba(196,123,14,0.3);border-radius:10px;padding:24px;text-align:center">
            <div style="font-size:36px;font-weight:700;letter-spacing:10px;color:#C47B0E">{code}</div>
          </div>
          <p style="color:#9A8878;font-size:12px;margin-top:20px">If you didn't request this, your password was not changed.</p>
        </div>"""
    msg = Message(subject=subject, recipients=[to_email], html=body)
    mail.send(msg)

def send_reset_email(to_email, reset_url):
    subject = '🔑 Budget Bee — Reset your password'
    body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#FEFAF2;border-radius:12px">
      <h2 style="color:#C47B0E">🔑 Reset your password</h2>
      <p style="color:#5a4a3a;font-size:14px;margin-bottom:24px">
        We received a request to reset your Budget Bee password. Click the button below to choose a new one.
        This link expires in <strong>1 hour</strong>.
      </p>
      <div style="text-align:center;margin-bottom:24px">
        <a href="{reset_url}" style="display:inline-block;background:#D4870A;color:#fff;text-decoration:none;
           padding:14px 28px;border-radius:10px;font-weight:600;font-size:15px">Reset Password →</a>
      </div>
      <p style="color:#9A8878;font-size:12px">If the button doesn't work, copy and paste this link into your browser:<br>
        <a href="{reset_url}" style="color:#D4870A;word-break:break-all">{reset_url}</a></p>
      <p style="color:#9A8878;font-size:12px;margin-top:16px">If you didn't request this, you can safely ignore this email — your password will not be changed.</p>
    </div>"""
    msg = Message(subject=subject, recipients=[to_email], html=body)
    mail.send(msg)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def sv():
    return {"username": session.get("username",""), "email": session.get("email","")}

# ── ROUTES ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


# ── AUTH ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Please fill in all fields.", "error")
        else:
            db   = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE email=? AND password=?",
                (email, hash_pw(password))
            ).fetchone()
            db.close()
            if user:
                session.permanent   = True
                session["user_id"]  = user["id"]
                session["username"] = user["username"]
                session["email"]    = user["email"]
                flash(f"Welcome back, {user['username']}! 👋", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        if not all([username, email, password, confirm]):
            flash("Please fill in all fields.", "error")
        elif len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
        elif "@" not in email:
            flash("Please enter a valid email.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            db = get_db()
            exists = db.execute("SELECT id FROM users WHERE email=? OR username=?", (email, username)).fetchone()
            db.close()
            if exists:
                flash("Username or email already registered.", "error")
            else:
                # Stash form data in session, send OTP
                session["pending_register"] = {
                    "username": username,
                    "email":    email,
                    "password": hash_pw(password)
                }
                try:
                    code = create_otp(email, "register")
                    send_otp_email(email, code, "register")
                    return redirect(url_for("verify_register"))
                except Exception as e:
                    app.logger.error(f"Mail error: {e}")
                    flash("Could not send verification email. Check MAIL config in data.py.", "error")
    return render_template("register.html")


@app.route("/verify-register", methods=["GET", "POST"])
def verify_register():
    pending = session.get("pending_register")
    if not pending:
        return redirect(url_for("register"))

    error = None
    if request.method == "POST":
        entered = request.form.get("otp", "").strip()
        result  = verify_otp(pending["email"], "register", entered)

        if result == "ok":
            db = get_db()
            try:
                cur = db.execute(
                    "INSERT INTO users (username, email, password) VALUES (?,?,?)",
                    (pending["username"], pending["email"], pending["password"])
                )
                db.commit()
                new_id = cur.lastrowid
                db.close()
                session.pop("pending_register", None)
                session.permanent   = True
                session["user_id"]  = new_id
                session["username"] = pending["username"]
                session["email"]    = pending["email"]
                flash(f"Account verified! Welcome, {pending['username']}! 🎉", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                db.close()
                error = "Username or email already taken. Please register again."
        elif result == "expired":
            error = "Code has expired. Please register again."
        elif result == "wrong":
            error = "Incorrect code. Please try again."
        else:
            error = "No code found. Please register again."

    return render_template("verify_otp.html", purpose="register",
                           email=pending["email"], error=error)


@app.route("/resend-otp/<purpose>")
def resend_otp(purpose):
    if purpose == "register":
        pending = session.get("pending_register")
        if not pending:
            return redirect(url_for("register"))
        email = pending["email"]
        redirect_to = url_for("verify_register")
    elif purpose == "password":
        if "user_id" not in session:
            return redirect(url_for("login"))
        db    = get_db()
        user  = db.execute("SELECT email FROM users WHERE id=?", (session["user_id"],)).fetchone()
        db.close()
        email = user["email"]
        redirect_to = url_for("verify_password_otp")
    else:
        return redirect("/")

    try:
        code = create_otp(email, purpose)
        send_otp_email(email, code, purpose)
        flash("A new code has been sent to your email.", "success")
    except Exception as e:
        app.logger.error(f"Mail error: {e}")
        flash("Could not resend. Please try again.", "error")

    return redirect(redirect_to)


@app.route("/logout")
def logout():
    name = session.get("username", "")
    session.clear()
    flash(f"You've been signed out. See you soon, {name}!", "success")
    return redirect(url_for("login"))


# ── MAIN PAGES ────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    uid   = session["user_id"]
    db    = get_db()
    month = datetime.date.today().strftime("%Y-%m")

    total = db.execute(
        "SELECT COALESCE(SUM(amount),0) AS t FROM expenses WHERE user_id=? AND date LIKE ?",
        (uid, f"{month}%")
    ).fetchone()["t"]

    income_total = db.execute(
        "SELECT COALESCE(SUM(amount),0) AS t FROM income WHERE user_id=? AND date LIKE ?",
        (uid, f"{month}%")
    ).fetchone()["t"]

    bud = db.execute(
        "SELECT budget FROM budget WHERE user_id=? AND month=?", (uid, month)
    ).fetchone()

    recent  = db.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC LIMIT 5", (uid,)
    ).fetchall()

    savings = db.execute(
        "SELECT * FROM savings WHERE user_id=?", (uid,)
    ).fetchall()

    db.close()
    return render_template("dashboard.html", **sv(),
                           total_spent=total,
                           income_total=income_total,
                           budget=bud["budget"] if bud else None,
                           recent=recent,
                           savings=savings)


@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    uid = session["user_id"]
    db  = get_db()

    if request.method == "POST":
        desc     = request.form.get("description", "").strip()
        category = request.form.get("category", "others")
        amount   = request.form.get("amount", "")
        date     = request.form.get("date", datetime.date.today().isoformat())
        if not desc or not amount:
            flash("Description and amount are required.", "error")
        else:
            db.execute(
                "INSERT INTO expenses (user_id,description,category,amount,date) VALUES (?,?,?,?,?)",
                (uid, desc, category, float(amount), date)
            )
            db.commit()
            flash(f"Expense '{desc}' added successfully! 💸", "success")

    month = request.args.get("month", datetime.date.today().strftime("%Y-%m"))
    rows  = db.execute(
        "SELECT * FROM expenses WHERE user_id=? AND date LIKE ? ORDER BY date DESC",
        (uid, f"{month}%")
    ).fetchall()
    total = sum(r["amount"] for r in rows)
    db.close()

    return render_template("expenses.html", **sv(),
                           expenses=rows, total=total, month=month)


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    uid = session["user_id"]
    db  = get_db()

    if request.method == "POST":
        amount    = request.form.get("budget", "")
        month     = request.form.get("month", "")
        alert_pct = request.form.get("alert_pct", 70)
        if not amount or not month:
            flash("Budget amount and month are required.", "error")
        else:
            db.execute(
                """INSERT INTO budget (user_id,month,budget,alert_pct) VALUES (?,?,?,?)
                   ON CONFLICT(user_id,month) DO UPDATE SET
                   budget=excluded.budget, alert_pct=excluded.alert_pct""",
                (uid, month, float(amount), int(alert_pct))
            )
            db.commit()
            flash(f"Budget of RM {float(amount):.2f} set for {month}! 🎯", "success")

    budgets  = db.execute(
        "SELECT * FROM budget WHERE user_id=? ORDER BY month DESC", (uid,)
    ).fetchall()
    spending = db.execute(
        "SELECT strftime('%Y-%m',date) AS month, SUM(amount) AS total FROM expenses WHERE user_id=? GROUP BY month",
        (uid,)
    ).fetchall()
    spending_map = {r["month"]: r["total"] for r in spending}
    db.close()

    return render_template("budget.html", **sv(),
                           budgets=budgets, spending=spending_map,
                           current_month=datetime.date.today().strftime("%Y-%m"))


@app.route("/savings", methods=["GET", "POST"])
@login_required
def savings():
    uid = session["user_id"]
    db  = get_db()

    if request.method == "POST":
        goal_name   = request.form.get("goal_name", "").strip()
        target      = request.form.get("target", "")
        target_date = request.form.get("target_date") or None
        if not goal_name or not target:
            flash("Goal name and target amount are required.", "error")
        else:
            db.execute(
                "INSERT INTO savings (user_id,goal_name,target,target_date) VALUES (?,?,?,?)",
                (uid, goal_name, float(target), target_date)
            )
            db.commit()
            flash(f"Savings goal '{goal_name}' created! 🐷", "success")

    goals = db.execute(
        "SELECT * FROM savings WHERE user_id=? ORDER BY created_at DESC", (uid,)
    ).fetchall()
    db.close()

    return render_template("savings.html", **sv(), goals=goals)


# ── PROFILE ───────────────────────────────────────────────────────────────

@app.route("/profile")
@login_required
def profile():
    uid = session["user_id"]
    db  = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    db.close()
    return render_template("profile.html", **sv(), user=user)


@app.route("/profile/update", methods=["POST"])
@login_required
def profile_update():
    uid      = session["user_id"]
    username = request.form.get("username", "").strip()
    email    = request.form.get("email", "").strip()

    if not username or not email:
        flash("Username and email cannot be empty.", "error")
        return redirect(url_for("profile"))
    if len(username) < 3:
        flash("Username must be at least 3 characters.", "error")
        return redirect(url_for("profile"))
    if "@" not in email:
        flash("Please enter a valid email.", "error")
        return redirect(url_for("profile"))

    db = get_db()
    try:
        db.execute(
            "UPDATE users SET username=?, email=? WHERE id=?",
            (username, email, uid)
        )
        db.commit()
        # Update session so nav shows the new name immediately
        session["username"] = username
        session["email"]    = email
        flash("Profile updated successfully! ✅", "success")
    except sqlite3.IntegrityError:
        flash("That username or email is already taken.", "error")
    finally:
        db.close()

    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["POST"])
@login_required
def profile_password():
    uid              = session["user_id"]
    current_password = request.form.get("current_password", "")
    new_password     = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    db   = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    db.close()

    if user["password"] != hash_pw(current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile"))
    if len(new_password) < 6:
        flash("New password must be at least 6 characters.", "error")
        return redirect(url_for("profile"))
    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    # All checks passed — stash hashed new password and send OTP
    session["pending_pw"] = hash_pw(new_password)
    try:
        code = create_otp(user["email"], "password")
        send_otp_email(user["email"], code, "password")
        return redirect(url_for("verify_password_otp"))
    except Exception as e:
        app.logger.error(f"Mail error: {e}")
        flash("Could not send verification email. Check MAIL config in data.py.", "error")
        return redirect(url_for("profile"))


@app.route("/profile/verify-password", methods=["GET", "POST"])
@login_required
def verify_password_otp():
    pending_pw = session.get("pending_pw")
    if not pending_pw:
        return redirect(url_for("profile"))

    db    = get_db()
    user  = db.execute("SELECT email FROM users WHERE id=?", (session["user_id"],)).fetchone()
    db.close()
    email = user["email"]

    error = None
    if request.method == "POST":
        entered = request.form.get("otp", "").strip()
        result  = verify_otp(email, "password", entered)

        if result == "ok":
            db = get_db()
            db.execute("UPDATE users SET password=? WHERE id=?", (pending_pw, session["user_id"]))
            db.commit()
            db.close()
            session.pop("pending_pw", None)
            flash("Password changed successfully! 🔒", "success")
            return redirect(url_for("profile"))
        elif result == "expired":
            error = "Code has expired. Request a new one."
        elif result == "wrong":
            error = "Incorrect code. Please try again."
        else:
            error = "No code found. Please try again."

    return render_template("verify_otp.html", purpose="password", email=email, error=error)


@app.route("/profile/delete", methods=["POST"])
@login_required
def profile_delete():
    uid = session["user_id"]
    db  = get_db()
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    db.close()
    session.clear()
    flash("Your account has been permanently deleted.", "success")
    return redirect(url_for("login"))


# ── PASSWORD RESET ────────────────────────────────────────────────────────

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email or "@" not in email:
            error = "Please enter a valid email address."
        else:
            db   = get_db()
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user:
                token   = secrets.token_urlsafe(32)
                expires = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
                db.execute(
                    "INSERT INTO password_resets (user_id,token,expires_at) VALUES (?,?,?)",
                    (user["id"], token, expires)
                )
                db.commit()
                reset_url = url_for("reset_password", token=token, _external=True)
                db.close()
                try:
                    send_reset_email(email, reset_url)
                except Exception as e:
                    # Email failed to send (e.g. bad SMTP credentials) — log it and
                    # still fall back to showing the link so nobody gets locked out
                    # while you're debugging your Gmail App Password setup.
                    print(f"[WARN] Failed to send password reset email to {email}: {e}")
                    return render_template("forgot_password.html", sent=reset_url)
                return render_template("forgot_password.html", sent=True)
            db.close()
            # Don't reveal if email exists — always show success
            return render_template("forgot_password.html", sent=True)
    return render_template("forgot_password.html", sent=None, error=error)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    db    = get_db()
    reset = db.execute(
        "SELECT * FROM password_resets WHERE token=? AND used=0", (token,)
    ).fetchone()
    invalid = not reset or datetime.datetime.fromisoformat(reset["expires_at"]) < datetime.datetime.now()

    error = None
    if not invalid and request.method == "POST":
        pw = request.form.get("password", "")
        cf = request.form.get("confirm", "")
        if len(pw) < 6:
            error = "Password must be at least 6 characters."
        elif pw != cf:
            error = "Passwords do not match."
        else:
            db.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(pw), reset["user_id"]))
            db.execute("UPDATE password_resets SET used=1 WHERE token=?", (token,))
            db.commit()
            db.close()
            flash("Password reset successful! You can now sign in. ✅", "success")
            return redirect(url_for("login"))

    db.close()
    return render_template("reset_password.html", invalid=invalid, token=token, error=error)


# ── STATIC PAGES ──────────────────────────────────────────────────────────

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/income", methods=["GET", "POST"])
@login_required
def income():
    uid = session["user_id"]
    db  = get_db()

    if request.method == "POST":
        desc        = request.form.get("description", "").strip()
        amount      = request.form.get("amount", "")
        income_type = request.form.get("type", "salary")
        date        = request.form.get("date", datetime.date.today().isoformat())
        if not desc or not amount:
            flash("Description and amount are required.", "error")
        else:
            db.execute(
                "INSERT INTO income (user_id,description,amount,type,date) VALUES (?,?,?,?,?)",
                (uid, desc, float(amount), income_type, date)
            )
            db.commit()
            flash(f"Income '{desc}' added successfully! 💰", "success")

    month = request.args.get("month", datetime.date.today().strftime("%Y-%m"))
    rows  = db.execute(
        "SELECT * FROM income WHERE user_id=? AND date LIKE ? ORDER BY date DESC",
        (uid, f"{month}%")
    ).fetchall()
    total = sum(r["amount"] for r in rows)
    db.close()

    return render_template("income.html", **sv(),
                           income_list=rows, total=total, month=month)



# ══════════════════════════════════════════════════════════════════════════
# API ROUTES — called by fetch() in templates
# ══════════════════════════════════════════════════════════════════════════

# ── EXPENSES API ─────────────────────────────────────────────────────────

@app.route("/api/expenses")
@login_required
def api_expenses_get():
    uid      = session["user_id"]
    all_time = request.args.get("all", "false").lower() == "true"
    db       = get_db()
    if all_time:
        rows = db.execute(
            "SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC",
            (uid,)
        ).fetchall()
    else:
        month = request.args.get("month", datetime.date.today().strftime("%m")).zfill(2)
        year  = request.args.get("year",  datetime.date.today().strftime("%Y"))
        rows  = db.execute(
            """SELECT * FROM expenses
               WHERE user_id=?
                 AND strftime('%m',date)=?
                 AND strftime('%Y',date)=?
               ORDER BY date DESC""",
            (uid, month, year)
        ).fetchall()
    total = sum(r["amount"] for r in rows)
    db.close()
    return {"expenses": [dict(r) for r in rows], "total": round(total, 2)}


@app.route("/api/expenses/add", methods=["POST"])
@login_required
def api_expenses_add():
    uid  = session["user_id"]
    data = request.get_json()
    desc     = data.get("description", "").strip()
    amount   = data.get("amount", 0)
    category = data.get("category", "Other")
    date     = data.get("date", datetime.date.today().isoformat())
    if not desc or not amount:
        return {"error": "Description and amount are required"}, 400
    db  = get_db()
    cur = db.execute(
        "INSERT INTO expenses (user_id,description,category,amount,date) VALUES (?,?,?,?,?)",
        (uid, desc, category, float(amount), date)
    )
    db.commit()
    new_id = cur.lastrowid
    db.close()
    return {"id": new_id, "description": desc, "category": category,
            "amount": float(amount), "date": date}, 201


@app.route("/api/expenses/delete/<int:eid>", methods=["DELETE"])
@login_required
def api_expenses_delete(eid):
    uid = session["user_id"]
    db  = get_db()
    db.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (eid, uid))
    db.commit()
    db.close()
    return {"deleted": eid}


@app.route("/api/expenses/edit/<int:eid>", methods=["PUT"])
@login_required
def api_expenses_edit(eid):
    uid  = session["user_id"]
    data = request.get_json()
    desc     = data.get("description", "").strip()
    amount   = data.get("amount", 0)
    category = data.get("category", "Other")
    date     = data.get("date", datetime.date.today().isoformat())
    if not desc or not amount:
        return {"error": "Description and amount are required"}, 400
    db = get_db()
    db.execute(
        "UPDATE expenses SET description=?, amount=?, category=?, date=? WHERE id=? AND user_id=?",
        (desc, float(amount), category, date, eid, uid)
    )
    db.commit()
    db.close()
    return {"id": eid, "description": desc, "amount": float(amount),
            "category": category, "date": date}


# ── INCOME API ────────────────────────────────────────────────────────────

@app.route("/api/income")
@login_required
def api_income_get():
    uid      = session["user_id"]
    all_time = request.args.get("all", "false").lower() == "true"
    db       = get_db()
    if all_time:
        rows = db.execute(
            "SELECT * FROM income WHERE user_id=? ORDER BY date DESC",
            (uid,)
        ).fetchall()
    else:
        month = request.args.get("month", datetime.date.today().strftime("%m")).zfill(2)
        year  = request.args.get("year",  datetime.date.today().strftime("%Y"))
        rows  = db.execute(
            """SELECT * FROM income
               WHERE user_id=?
                 AND strftime('%m',date)=?
                 AND strftime('%Y',date)=?
               ORDER BY date DESC""",
            (uid, month, year)
        ).fetchall()
    total = sum(r["amount"] for r in rows)
    db.close()
    return {"income": [dict(r) for r in rows], "total": round(total, 2)}


@app.route("/api/income/add", methods=["POST"])
@login_required
def api_income_add():
    uid  = session["user_id"]
    data = request.get_json()
    desc        = data.get("description", "").strip()
    amount      = data.get("amount", 0)
    income_type = data.get("income_type", "Salary")
    date        = data.get("date", datetime.date.today().isoformat())
    if not desc or not amount:
        return {"error": "Description and amount are required"}, 400
    db  = get_db()
    cur = db.execute(
        "INSERT INTO income (user_id,description,amount,type,date) VALUES (?,?,?,?,?)",
        (uid, desc, float(amount), income_type, date)
    )
    db.commit()
    new_id = cur.lastrowid
    db.close()
    return {"id": new_id, "description": desc, "amount": float(amount),
            "type": income_type, "date": date}, 201


@app.route("/api/income/delete/<int:iid>", methods=["DELETE"])
@login_required
def api_income_delete(iid):
    uid = session["user_id"]
    db  = get_db()
    db.execute("DELETE FROM income WHERE id=? AND user_id=?", (iid, uid))
    db.commit()
    db.close()
    return {"deleted": iid}


@app.route("/api/income/edit/<int:iid>", methods=["PUT"])
@login_required
def api_income_edit(iid):
    uid  = session["user_id"]
    data = request.get_json()
    desc        = data.get("description", "").strip()
    amount      = data.get("amount", 0)
    income_type = data.get("income_type", "Other")
    date        = data.get("date", datetime.date.today().isoformat())
    if not desc or not amount:
        return {"error": "Description and amount are required"}, 400
    db = get_db()
    db.execute(
        "UPDATE income SET description=?, amount=?, type=?, date=? WHERE id=? AND user_id=?",
        (desc, float(amount), income_type, date, iid, uid)
    )
    db.commit()
    db.close()
    return {"id": iid, "description": desc, "amount": float(amount),
            "type": income_type, "date": date}


# ── BUDGET API ────────────────────────────────────────────────────────────

@app.route("/api/budget")
@login_required
def api_budget_get():
    uid   = session["user_id"]
    month = request.args.get("month", datetime.date.today().strftime("%m")).zfill(2)
    year  = request.args.get("year",  datetime.date.today().strftime("%Y"))
    month_str = f"{year}-{month}"
    db  = get_db()
    bud = db.execute(
        "SELECT budget, alert_pct FROM budget WHERE user_id=? AND month=?",
        (uid, month_str)
    ).fetchone()
    db.close()
    if bud:
        return {"budget": bud["budget"], "alert_pct": bud["alert_pct"], "month": month_str}
    return {"budget": 0, "alert_pct": 70, "month": month_str}


@app.route("/api/budget/delete/<int:bid>", methods=["DELETE"])
@login_required
def api_budget_delete(bid):
    uid = session["user_id"]
    db  = get_db()
    db.execute("DELETE FROM budget WHERE id=? AND user_id=?", (bid, uid))
    db.commit()
    db.close()
    return {"deleted": bid}


@app.route("/api/budget/edit/<int:bid>", methods=["PUT"])
@login_required
def api_budget_edit(bid):
    uid  = session["user_id"]
    data = request.get_json()
    month     = data.get("month", "").strip()
    amount    = data.get("budget", 0)
    alert_pct = data.get("alert_pct", 70)
    if not month or not amount:
        return {"error": "Month and budget amount are required"}, 400
    db = get_db()
    try:
        db.execute(
            "UPDATE budget SET month=?, budget=?, alert_pct=? WHERE id=? AND user_id=?",
            (month, float(amount), int(alert_pct), bid, uid)
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        return {"error": f"A budget for {month} already exists"}, 409
    db.close()
    return {"id": bid, "month": month, "budget": float(amount), "alert_pct": int(alert_pct)}


# ── SAVINGS API ───────────────────────────────────────────────────────────

@app.route("/api/savings")
@login_required
def api_savings_get():
    uid  = session["user_id"]
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM savings WHERE user_id=? ORDER BY created_at DESC", (uid,)
    ).fetchall()
    db.close()
    goals = []
    for r in rows:
        g = dict(r)
        g["progress_pct"] = round((g["saved"] / g["target"]) * 100, 1) if g["target"] > 0 else 0
        g["remaining"]    = round(g["target"] - g["saved"], 2)
        goals.append(g)
    return {"goals": goals}


@app.route("/api/savings/add", methods=["POST"])
@login_required
def api_savings_add():
    uid  = session["user_id"]
    data = request.get_json()
    name          = data.get("name", "").strip()
    target_amount = data.get("target_amount", 0)
    deadline      = data.get("deadline") or None
    if not name or not target_amount:
        return {"error": "Goal name and target amount are required"}, 400
    db  = get_db()
    cur = db.execute(
        "INSERT INTO savings (user_id,goal_name,target,target_date) VALUES (?,?,?,?)",
        (uid, name, float(target_amount), deadline)
    )
    db.commit()
    new_id = cur.lastrowid
    db.close()
    return {"id": new_id, "name": name, "target_amount": float(target_amount),
            "saved": 0, "progress_pct": 0, "deadline": deadline}, 201


@app.route("/api/savings/topup/<int:gid>", methods=["POST"])
@login_required
def api_savings_topup(gid):
    uid  = session["user_id"]
    data = request.get_json()
    amount = float(data.get("amount", 0))
    if amount <= 0:
        return {"error": "Amount must be greater than 0"}, 400
    db   = get_db()
    goal = db.execute(
        "SELECT * FROM savings WHERE id=? AND user_id=?", (gid, uid)
    ).fetchone()
    if not goal:
        db.close()
        return {"error": "Goal not found"}, 404
    new_saved = min(goal["saved"] + amount, goal["target"])
    db.execute("UPDATE savings SET saved=? WHERE id=?", (new_saved, gid))
    db.commit()
    db.close()
    return {"id": gid, "saved": new_saved, "completed": new_saved >= goal["target"]}


@app.route("/api/savings/delete/<int:gid>", methods=["DELETE"])
@login_required
def api_savings_delete(gid):
    uid = session["user_id"]
    db  = get_db()
    db.execute("DELETE FROM savings WHERE id=? AND user_id=?", (gid, uid))
    db.commit()
    db.close()
    return {"deleted": gid}

# ── INIT ──────────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    app.run(debug=True)