from flask import Flask
from database import init_db
from routes.users     import users_bp
from routes.expenses  import expenses_bp
from routes.budgets   import budgets_bp
from routes.savings   import savings_bp
from routes.dashboard import dashboard_bp

app = Flask(__name__)

# Register all blueprints
app.register_blueprint(users_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(budgets_bp)
app.register_blueprint(savings_bp)
app.register_blueprint(dashboard_bp)

# Initialize DB on startup
init_db()


@app.route("/")
def index():
    return {
        "app": "Budget Bee API",
        "version": "1.0",
        "endpoints": {
            "auth":     ["POST /register", "POST /login"],
            "users":    ["GET/PUT/DELETE /users/<id>"],
            "expenses": ["POST/GET /users/<id>/expenses", "GET/PUT/DELETE /users/<id>/expenses/<id>"],
            "budget":   ["POST /users/<id>/budget", "GET/PUT /users/<id>/budget/<month>"],
            "savings":  ["POST/GET /users/<id>/savings", "PUT/DELETE /users/<id>/savings/<id>"],
            "dashboard":["GET /users/<id>/dashboard?month=YYYY-MM"],
        }
    }


if __name__ == "__main__":
    app.run(debug=True)