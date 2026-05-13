from flask import Flask, redirect, url_for, render_template, request, session
from datetime import timedelta
import sqlite3, hashlib, secrets, datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "budgetbee-secret-key-2025"
app.permanent_session_lifetime = timedelta(minutes=30)

DB = "users.db"

# ── DATABASE ──────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
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
    db.commit()
    db.close()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ── ROUTES ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))       # FIX 1: was url_for("dashboard.html")

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Please fill in all fields."
        else:
            db   = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE email = ? AND password = ?",
                (email, hash_pw(password))
            ).fetchone()
            db.close()

            if user:
                session.permanent   = True
                session["user_id"]  = user["id"]
                session["username"] = user["username"]
                session["email"]    = user["email"]
                return redirect(url_for("dashboard"))
            else:
                error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])    # FIX 2: was /register.html
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))        # FIX 3: was url_for("dashboard.html")

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not all([username, email, password, confirm]):
            error = "Please fill in all fields."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif "@" not in email:
            error = "Please enter a valid email."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            db = get_db()
            try:
                cur = db.execute(
                    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                    (username, email, hash_pw(password))
                )
                db.commit()
                new_id = cur.lastrowid
                db.close()

                session.permanent   = True
                session["user_id"]  = new_id
                session["username"] = username
                session["email"]    = email

                return redirect(url_for("dashboard"))

            except sqlite3.IntegrityError:
                db.close()
                error = "Username or email already registered."

    return render_template("register.html", error=error)


@app.route("/dashboard")                            # FIX 4: was /dashboard.html
@login_required
def dashboard():
    return render_template("dashboard.html",        # FIX 5: was user.html (doesn't exist)
                           username=session["username"],
                           email=session["email"])

@app.route("/expenses")
@login_required
def expenses():
    return render_template("expenses.html", username=session["username"], email=session["email"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])   # FIX 6: route was missing entirely
def forgot_password():
    sent = error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email or "@" not in email:
            error = "Please enter a valid email address."
        else:
            db   = get_db()
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                token   = secrets.token_urlsafe(32)
                expires = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
                db.execute(
                    "INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)",
                    (user["id"], token, expires)
                )
                db.commit()
                sent = url_for("reset_password", token=token, _external=True)
            else:
                sent = "not_found"
            db.close()
    return render_template("forgot_password.html", sent=sent, error=error)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    db    = get_db()
    reset = db.execute(
        "SELECT * FROM password_resets WHERE token = ? AND used = 0", (token,)
    ).fetchone()
    invalid = not reset or datetime.datetime.fromisoformat(reset["expires_at"]) < datetime.datetime.now()
    error = success = None
    if not invalid and request.method == "POST":
        pw = request.form.get("password", "")
        cf = request.form.get("confirm", "")
        if len(pw) < 6:
            error = "Password must be at least 6 characters."
        elif pw != cf:
            error = "Passwords do not match."
        else:
            db.execute("UPDATE users SET password = ? WHERE id = ?", (hash_pw(pw), reset["user_id"]))
            db.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
            db.commit()
            success = True
    db.close()
    return render_template("reset_password.html", invalid=invalid, error=error, success=success, token=token)


@app.route("/terms")                                # FIX 7: route was missing
def terms():
    return render_template("terms.html")


@app.route("/privacy")                              # FIX 8: route was missing
def privacy():
    return render_template("privacy.html")


# ── INIT ──────────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    app.run(debug=True)
