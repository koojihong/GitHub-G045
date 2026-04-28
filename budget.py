# Budget Tracker
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# This is "database"
transactions = []
budget_limit = 2000
income = 3000

# Serve the dashboard page
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# GET all budget data
@app.route("/api/data")
def get_data():
    total_spent = sum(t["amount"] for t in transactions)
    balance = income - total_spent

    return jsonify({
        "income": income,
        "spent": total_spent,
        "balance": balance,
        "limit": budget_limit,
        "transactions": transactions
    })

# POST a new transaction
@app.route("/api/add", methods=["POST"])
def add_transaction():
    data = request.get_json()
    transactions.append({
        "desc": data["desc"],
        "amount": float(data["amount"]),
        "category": data["category"]
    })
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)