from flask import Flask, redirect, url_for, render_template, request, session, jsonify, flash
from database import db, User, Expense, Income, SavingsGoal
from auth import auth, bcrypt
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# ── Config ────────────────────────────────────────────
app.config['SECRET_KEY']                     = 'budgetbee-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///budgetbee.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── Init ──────────────────────────────────────────────
db.init_app(app)
bcrypt.init_app(app)
app.register_blueprint(auth)

# ── Auth guard ────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access that page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

# Helper: common session vars for templates
def sv():
    return {'username': session.get('username', ''), 'email': session.get('email', '')}

# ── Page Routes ───────────────────────────────────────
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# ── Setup Page ────────────────────────────────────────
@app.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    user = User.query.get(session['user_id'])

    if user.income is not None:
        return redirect('/dashboard')

    if request.method == 'POST':
        user.income       = float(request.form.get('income'))
        user.budget_limit = float(request.form.get('budget_limit'))
        db.session.commit()
        return redirect('/dashboard')

    return render_template('setup.html', username=session['username'])

# ── Dashboard ─────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    uid   = session['user_id']
    month = datetime.today().strftime('%Y-%m')

    expenses     = Expense.query.filter_by(user_id=uid).all()
    incomes      = Income.query.filter_by(user_id=uid).all()
    savings      = SavingsGoal.query.filter_by(user_id=uid).all()

    # Monthly totals
    total_spent  = sum(
        e.amount for e in expenses
        if e.date.strftime('%Y-%m') == month
    )
    income_total = sum(
        i.amount for i in incomes
        if i.date.strftime('%Y-%m') == month
    )

    recent = sorted(expenses, key=lambda e: e.date, reverse=True)[:5]

    user = User.query.get(uid)
    budget = user.budget_limit

    return render_template('dashboard.html', **sv(),
                           total_spent=total_spent,
                           income_total=income_total,
                           budget=budget,
                           recent=recent,
                           savings=savings)

# ── Expenses Page ─────────────────────────────────────
@app.route('/expenses')
@login_required
def expenses_page():
    return render_template('expenses.html', username=session['username'])

# ── Get Expenses (filter by month) ────────────────────
@app.route('/api/expenses')
@login_required
def get_expenses():
    month = request.args.get('month')
    year  = request.args.get('year')

    query = Expense.query.filter_by(user_id=session['user_id'])

    if month and year:
        query = query.filter(
            db.extract('month', Expense.date) == int(month),
            db.extract('year',  Expense.date) == int(year)
        )

    expenses = query.order_by(Expense.date.desc()).all()

    exp_list = [{
        'id':          e.id,
        'description': e.description,
        'amount':      e.amount,
        'category':    e.category,
        'date':        e.date.strftime('%Y-%m-%d')
    } for e in expenses]

    return jsonify({
        'expenses': exp_list,
        'total':    round(sum(e.amount for e in expenses), 2)
    })

# ── Add New Expense ────────────────────────────────────
@app.route('/api/expenses/add', methods=['POST'])
@login_required
def add_expense():
    data = request.get_json()

    desc     = (data.get('description') or '').strip()
    amount   = data.get('amount', 0)
    category = data.get('category', 'others')
    date_str = data.get('date', datetime.today().isoformat()[:10])

    if not desc or not amount:
        return jsonify({'error': 'Description and amount are required'}), 400

    new_expense = Expense(
        user_id     = session['user_id'],
        description = desc,
        amount      = float(amount),
        category    = category,
        date        = datetime.strptime(date_str, '%Y-%m-%d')
    )
    db.session.add(new_expense)
    db.session.commit()
    return jsonify({
        'id': new_expense.id, 'description': desc,
        'category': category, 'amount': float(amount), 'date': date_str
    }), 201

# ── Delete Expense ─────────────────────────────────────
@app.route('/api/expenses/delete/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
    if not expense:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(expense)
    db.session.commit()
    return jsonify({'deleted': expense_id})

# ── Update Income & Budget ─────────────────────────────
@app.route('/api/update-settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    user = User.query.get(session['user_id'])
    user.income       = float(data['income'])
    user.budget_limit = float(data['budget_limit'])
    db.session.commit()
    return jsonify({'status': 'ok'})

# ── Get Budget Data ────────────────────────────────────
@app.route('/api/data')
@login_required
def get_data():
    user        = User.query.get(session['user_id'])
    expenses    = Expense.query.filter_by(user_id=session['user_id']).all()
    incomes     = Income.query.filter_by(user_id=session['user_id']).all()

    total_spent  = sum(e.amount for e in expenses)
    total_income = sum(i.amount for i in incomes)

    if total_income == 0:
        total_income = user.income or 0

    return jsonify({
        'income':  total_income,
        'spent':   total_spent,
        'balance': total_income - total_spent,
        'limit':   user.budget_limit,
    })

# ── Income Page ───────────────────────────────────────
@app.route('/income')
@login_required
def income_page():
    return render_template('income.html', **sv())

# ── Get Income (filter by month) ──────────────────────
@app.route('/api/income')
@login_required
def get_income():
    month = request.args.get('month')
    year  = request.args.get('year')

    query = Income.query.filter_by(user_id=session['user_id'])

    if month and year:
        query = query.filter(
            db.extract('month', Income.date) == int(month),
            db.extract('year',  Income.date) == int(year)
        )

    incomes = query.order_by(Income.date.desc()).all()

    return jsonify({
        'income': [{
            'id':          i.id,
            'description': i.description,
            'amount':      i.amount,
            'income_type': i.income_type,
            'date':        i.date.strftime('%Y-%m-%d')
        } for i in incomes],
        'total': round(sum(i.amount for i in incomes), 2)
    })

# ── Add Income ────────────────────────────────────────
@app.route('/api/income/add', methods=['POST'])
@login_required
def add_income():
    data = request.get_json()

    desc        = (data.get('description') or '').strip()
    amount      = data.get('amount', 0)
    income_type = data.get('income_type', 'salary')
    date_str    = data.get('date', datetime.today().isoformat()[:10])

    if not desc or not amount:
        return jsonify({'error': 'Description and amount are required'}), 400

    new_income = Income(
        user_id     = session['user_id'],
        description = desc,
        amount      = float(amount),
        income_type = income_type,
        date        = datetime.strptime(date_str, '%Y-%m-%d')
    )
    db.session.add(new_income)
    db.session.commit()
    return jsonify({
        'id': new_income.id, 'description': desc,
        'amount': float(amount), 'income_type': income_type, 'date': date_str
    }), 201

# ── Delete Income ─────────────────────────────────────
@app.route('/api/income/delete/<int:income_id>', methods=['DELETE'])
@login_required
def delete_income(income_id):
    income = Income.query.filter_by(id=income_id, user_id=session['user_id']).first()
    if not income:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(income)
    db.session.commit()
    return jsonify({'deleted': income_id})

# ── Profile Page ──────────────────────────────────────
@app.route('/profile')
@login_required
def profile_page():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', **sv(), user=user)

# ── Update Profile ────────────────────────────────────
@app.route('/profile/update', methods=['POST'])
@login_required
def profile_update():
    username = request.form.get('username', '').strip()
    email    = request.form.get('email', '').strip()

    if not username or not email:
        flash('Username and email cannot be empty.', 'error')
        return redirect(url_for('profile_page'))
    if len(username) < 3:
        flash('Username must be at least 3 characters.', 'error')
        return redirect(url_for('profile_page'))
    if '@' not in email:
        flash('Please enter a valid email.', 'error')
        return redirect(url_for('profile_page'))

    user = User.query.get(session['user_id'])
    try:
        user.username = username
        user.email    = email
        db.session.commit()
        session['username'] = username
        session['email']    = email
        flash('Profile updated successfully! ✅', 'success')
    except Exception:
        db.session.rollback()
        flash('That username or email is already taken.', 'error')

    return redirect(url_for('profile_page'))

# ── Change Password ───────────────────────────────────
@app.route('/profile/password', methods=['POST'])
@login_required
def profile_password():
    current_password = request.form.get('current_password', '')
    new_password     = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    user = User.query.get(session['user_id'])

    if not bcrypt.check_password_hash(user.password, current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('profile_page'))
    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('profile_page'))
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('profile_page'))

    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    flash('Password changed successfully! 🔒', 'success')
    return redirect(url_for('profile_page'))

# ── Delete Account ────────────────────────────────────
@app.route('/profile/delete', methods=['POST'])
@login_required
def profile_delete():
    user = User.query.get(session['user_id'])
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash('Your account has been permanently deleted.', 'success')
    return redirect(url_for('auth.login'))

# ── Forgot Password Page ──────────────────────────────
@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

# ── Reset Password Page ───────────────────────────────
@app.route('/reset-password/<token>')
def reset_password(token):
    return render_template('reset_password.html', token=token)

# ── Savings Page ──────────────────────────────────────
@app.route('/savings')
@login_required
def savings_page():
    return render_template('savings.html', **sv())

# ── Get All Savings Goals ─────────────────────────────
@app.route('/api/savings')
@login_required
def get_savings():
    goals = SavingsGoal.query.filter_by(user_id=session['user_id']).order_by(SavingsGoal.created_at.desc()).all()

    result = []
    for g in goals:
        goal_dict = {
            'id':            g.id,
            'name':          g.name,
            'target_amount': g.target_amount,
            'saved_amount':  g.saved_amount,
            'deadline':      g.deadline,
            'created_at':    g.created_at.strftime('%Y-%m-%d'),
            'progress_pct':  round((g.saved_amount / g.target_amount) * 100, 1) if g.target_amount > 0 else 0,
            'remaining':     round(g.target_amount - g.saved_amount, 2)
        }
        result.append(goal_dict)

    return jsonify({'goals': result})

# ── Add New Savings Goal ──────────────────────────────
@app.route('/api/savings/add', methods=['POST'])
@login_required
def add_savings():
    data = request.get_json()

    name          = (data.get('name') or '').strip()
    target_amount = data.get('target_amount', 0)
    deadline      = data.get('deadline') or None

    if not name or not target_amount:
        return jsonify({'error': 'Goal name and target amount are required'}), 400

    new_goal = SavingsGoal(
        user_id       = session['user_id'],
        name          = name,
        target_amount = float(target_amount),
        saved_amount  = float(data.get('saved_amount', 0)),
        deadline      = deadline
    )
    db.session.add(new_goal)
    db.session.commit()
    return jsonify({
        'id': new_goal.id, 'name': name,
        'target_amount': float(target_amount),
        'saved_amount': 0, 'progress_pct': 0, 'deadline': deadline
    }), 201

# ── Add Money to a Goal ────────────────────────────────
@app.route('/api/savings/topup/<int:goal_id>', methods=['POST'])
@login_required
def topup_savings(goal_id):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=session['user_id']).first()
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404

    data   = request.get_json()
    amount = float(data.get('amount', 0))

    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than 0'}), 400

    goal.saved_amount = min(goal.saved_amount + amount, goal.target_amount)
    db.session.commit()

    return jsonify({
        'id':           goal_id,
        'saved_amount': goal.saved_amount,
        'completed':    goal.saved_amount >= goal.target_amount
    })

# ── Delete Savings Goal ────────────────────────────────
@app.route('/api/savings/delete/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_savings(goal_id):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=session['user_id']).first()
    if not goal:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(goal)
    db.session.commit()
    return jsonify({'deleted': goal_id})

# ── Create DB & Run ────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)