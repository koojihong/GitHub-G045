from flask import Flask, redirect, url_for, render_template, request, session, jsonify
from database import db, User, Expense, Income
from auth import auth, bcrypt
from datetime import datetime
 
app = Flask(__name__)
 
# ── Config ────────────────────────────────────────────
app.config['SECRET_KEY']                     = 'budgetbee-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///budgetbee.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
 
# ── Init ──────────────────────────────────────────────
db.init_app(app)
bcrypt.init_app(app)
app.register_blueprint(auth)
 
# ── Page Routes ───────────────────────────────────────
@app.route('/')
def home():
    return redirect(url_for('auth.login'))
 
@app.route('/terms.html')
def terms():
    return render_template('terms.html')
 
@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

# ── Setup Page ───────────────────────────────────────
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])

    # If already set up, skip to dashboard
    if user.income is not None:
        return redirect('/dashboard')

    if request.method == 'POST':
        user.income       = float(request.form.get('income'))
        user.budget_limit = float(request.form.get('budget_limit'))
        db.session.commit()
        return redirect('/dashboard')

    return render_template('setup.html', username=session['username'])
 
# ── Expenses Page ─────────────────────────────────────
@app.route('/expenses')
def expenses_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('expenses.html', username=session['username'])
 
# ── Get Expenses (filter by month) ────────────────────
@app.route('/api/expenses')
def get_expenses():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    month = request.args.get('month')
    year  = request.args.get('year')
 
    query = Expense.query.filter_by(user_id=session['user_id'])
 
    if month and year:
        query = query.filter(
            db.extract('month', Expense.date) == int(month),
            db.extract('year',  Expense.date) == int(year)
        )
 
    expenses = query.order_by(Expense.date.desc()).all()
 
    return jsonify([{
        'id':          e.id,
        'description': e.description,
        'amount':      e.amount,
        'category':    e.category,
        'date':        e.date.strftime('%Y-%m-%d')
    } for e in expenses])
 
# ── Add New Expense ────────────────────────────────────
@app.route('/api/expenses/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    data = request.get_json()
    new_expense = Expense(
        user_id     = session['user_id'],
        description = data['description'],
        amount      = float(data['amount']),
        category    = data['category'],
        date        = datetime.strptime(data['date'], '%Y-%m-%d')
    )
    db.session.add(new_expense)
    db.session.commit()
    return jsonify({'status': 'ok'})
 
# ── Delete Expense ─────────────────────────────────────
@app.route('/api/expenses/delete/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
    if not expense:
        return jsonify({'error': 'Not found'}), 404
 
    db.session.delete(expense)
    db.session.commit()
    return jsonify({'status': 'ok'})
 
# ── Update Income & Budget ─────────────────────────────
@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    data = request.get_json()
    user = User.query.get(session['user_id'])
    user.income       = float(data['income'])
    user.budget_limit = float(data['budget_limit'])
    db.session.commit()
    return jsonify({'status': 'ok'})
 
# ── Get Budget Data ────────────────────────────────────
@app.route('/api/data')
def get_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    user = User.query.get(session['user_id'])
 
    expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    total_spent = sum(e.amount for e in expenses)
 
    return jsonify({
        'income':       user.income,
        'spent':        total_spent,
        'balance':      user.income - total_spent,
        'limit':        user.budget_limit,
    })
 
# ── Income Page ───────────────────────────────────────
@app.route('/income')
def income_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('income.html', username=session['username'])
 
# ── Get Income (filter by month) ──────────────────────
@app.route('/api/income')
def get_income():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    month = request.args.get('month')
    year  = request.args.get('year')
 
    query = Income.query.filter_by(user_id=session['user_id'])
 
    if month and year:
        query = query.filter(
            db.extract('month', Income.date) == int(month),
            db.extract('year',  Income.date) == int(year)
        )
 
    incomes = query.order_by(Income.date.desc()).all()
 
    return jsonify([{
        'id':          i.id,
        'description': i.description,
        'amount':      i.amount,
        'income_type': i.income_type,
        'date':        i.date.strftime('%Y-%m-%d')
    } for i in incomes])
 
# ── Add Income ────────────────────────────────────────
@app.route('/api/income/add', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    data = request.get_json()
 
    if not data or not data.get('description') or not data.get('amount') or not data.get('date'):
        return jsonify({'error': 'Missing fields'}), 400
 
    new_income = Income(
        user_id     = session['user_id'],
        description = data['description'],
        amount      = float(data['amount']),
        income_type = data['income_type'],
        date        = datetime.strptime(data['date'], '%Y-%m-%d')
    )
    db.session.add(new_income)
    db.session.commit()
    return jsonify({'status': 'ok'})
 
# ── Delete Income ─────────────────────────────────────
@app.route('/api/income/delete/<int:income_id>', methods=['DELETE'])
def delete_income(income_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
 
    income = Income.query.filter_by(id=income_id, user_id=session['user_id']).first()
    if not income:
        return jsonify({'error': 'Not found'}), 404
 
    db.session.delete(income)
    db.session.commit()
    return jsonify({'status': 'ok'})

# ── Create DB & Run ────────────────────────────────────
with app.app_context():
    db.create_all()
 
if __name__ == '__main__':
    app.run(debug=True)
 
