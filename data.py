from flask import Flask, render_template, request, redirect, url_for, session
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

@app.route("/login.html")
def login():
    return render_template("login.html")

<<<<<<< HEAD
=======
@app.route("/terms.html")
def terms():
    return render_template("terms.html")

@app.route("/privacy.html")
def privacy():
    return render_template("privacy.html")

@app.route("/admin")
def admin():
    return redirect(url_for("login.html"))



>>>>>>> e9ef47eb166c13a53f2c7feec12df5e9325069fd
if __name__ == "__main__":
    app.run(debug=True)