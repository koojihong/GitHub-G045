from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/register.html")
def register():
    return render_template("register.html")

@app.route("/home")
def home_page():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)