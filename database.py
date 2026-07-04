from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    income       = db.Column(db.Float, nullable=True)
    budget_limit = db.Column(db.Float, nullable=True)
    is_verified  = db.Column(db.Boolean, default=False)   # True after email OTP confirmed

    def __repr__(self):
        return f'<User {self.username}>'

class OTPCode(db.Model):
    """Stores a short-lived 6-digit OTP for email verification."""
    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(120), nullable=False)
    code       = db.Column(db.String(6), nullable=False)
    purpose    = db.Column(db.String(20), nullable=False)  # 'register' or 'password'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used       = db.Column(db.Boolean, default=False)

    def is_expired(self):
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds() > 600  # 10 minutes
    
class Expense(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float, nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    date        = db.Column(db.DateTime, default=datetime.utcnow)
 
    def __repr__(self):
        return f'<Expense {self.description}>'

class Income(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float, nullable=False)
    income_type = db.Column(db.String(50), nullable=False)  # Salary/Part-time/Allowance/etc
    date        = db.Column(db.DateTime, default=datetime.utcnow)
 
    def __repr__(self):
        return f'<Income {self.description}>'
    
class SavingsGoal(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name         = db.Column(db.String(100), nullable=False)
    target_amount= db.Column(db.Float, nullable=False)
    saved_amount = db.Column(db.Float, default=0.0)
    deadline     = db.Column(db.String(20), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SavingsGoal {self.name}>'