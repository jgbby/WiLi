#! /venv/bin/python3

import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required

# pi imports
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo, AngularServo


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///wili.db")

# Instantiate servo
pigpio_factory = PiGPIOFactory()
servo = AngularServo(14, pin_factory=pigpio_factory)

# DISPLAY HOME PAGE
@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    # Init vars
    uid = session["user_id"]

    # Get db parties
    parties = db.execute("SELECT * FROM parties WHERE hostid = :uid", uid=uid)

    # Return template and variables
    return render_template("index.html")


@app.route("/unlock", methods=["GET"])
@login_required
def unlock():
    if request.method == "GET":
        uid = session["user_id"]
        # servo unlock
        print("Unlocking!")
        servo.angle = 90
        return redirect("/")

@app.route("/lock", methods=["GET"])
@login_required
def lock():
    if request.method == "GET":
        uid = session["user_id"]
        # servo unlock
        print("Locking!")
        servo.angle = -90
        return redirect("/")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 400)

        # Ensure passwords were submitted
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Must provide passwords", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) == 1:
            return apology("Sorry username is already in use", 400)

        # Ensure passwords are the same
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords entered are not the same!")

        # Insert registree into users table
        phash = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :phash)", username=request.form.get("username"), phash=phash)

        # Redirect user to login
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


# CHECK IF USER IS AVAILABLE
@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    # Error check username
    username = request.args.get("username")
    checkuser = db.execute("SELECT * FROM users WHERE username = :username", username=username)
    if len(username) < 1 or checkuser:
        return jsonify(False)
    # Valid
    return jsonify(True)


# RESET PASSWORD
@app.route("/reset", methods=["GET", "POST"])
@login_required
def reset():
    if request.method == "POST":

        # Ensure passwords were submitted
        if not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Must provide passwords", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE id = :uid", uid=session["user_id"])

        # Ensure passwords are the same
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords entered are not the same!")

        # Insert registree into users table
        phash = generate_password_hash(request.form.get("password"))
        db.execute("UPDATE users SET hash=:phash WHERE id=:uid", uid=session["user_id"], phash=phash)
        return redirect("/")
    else:
        return render_template("reset.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)





if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0")

    # Listen for errors
    for code in default_exceptions:
        app.errorhandler(code)(errorhandler)
