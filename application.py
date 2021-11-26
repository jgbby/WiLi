import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required


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
db = SQL("sqlite:///planme.db")

# DISPLAY MYPARTY
@app.route("/", methods=["GET", "POST"])
@login_required
def myparty():
    # Init vars
    uid = session["user_id"]

    # Get db parties
    parties = db.execute("SELECT * FROM parties WHERE hostid = :uid", uid=uid)

    # Return template and variables
    return render_template("index.html", parties=parties)


# DELETE PARTY
@app.route("/delete", methods=["GET"])
@login_required
def delete():
    uid = session["user_id"]
    pid = request.args.get("pid")


    # Ensure user is the host of given party
    hostid = db.execute("SELECT hostid FROM parties WHERE id=:pid", pid=pid)
    if hostid[0]["hostid"] == uid:
        db.execute("DELETE FROM parties WHERE hostid=:uid AND id=:pid", uid=uid, pid=pid)
        db.execute("DELETE FROM invited WHERE partyid=:pid", pid=pid)

    return redirect("/")

# DECLINE METHOD
@app.route("/decline", methods=["GET"])
@login_required
def decline():
    uid = session["user_id"]
    pid = request.args.get("pid")
    db.execute("DELETE FROM invited WHERE partyid=:pid AND userid=:uid", pid=pid, uid=uid)
    return redirect("/invited")

# DISPLAY INVITED
@app.route("/invited", methods=["GET", "POST"])
@login_required
def invited():

    # Init vars
    uid = session["user_id"]

    # Init all invited parties
    parties = db.execute("""SELECT parties.nec, parties.id, parties.name, parties.notes,
    parties.date, parties.place FROM invited, parties WHERE parties.id = invited.partyid
    AND invited.userid = :uid""", uid=uid)

    # Return template and variables
    return render_template("invited.html", parties=parties)


# CREATE FORM
@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":

        # Gather inputs
        uid = session["user_id"]
        name = request.form.get("name")
        date = request.form.get("date")
        place = request.form.get("place")
        notes = request.form.get("notes")
        nec = request.form.get("nec")
        inviteesl = []
        for i in range(0,16):
            if (request.form.get("in"+str(i))):
                inviteesl.append(request.form.get("in"+str(i)))

        # Error checking
        if not name:
            return apology("Must enter a name!")
        elif not date:
            return apology("Must enter a date!")
        elif not place:
            return apology("Must enter a place!")
        elif not inviteesl:
            return apology("Must enter an invite!")
        elif not nec:
            return apology("Must enter a necessity!")
        elif not notes:
            return apology("Must enter a greeting!")

        # Init pinfo1
        pinfo1 = {"name": name, "date": date, "place": place, "notes": notes, "nec": nec}

        # Update db parties
        db.execute('''INSERT INTO parties (name, place, date, notes, hostid, nec)
                      VALUES (:name, :place, :date, :notes, :hostid, :nec)''',
                      name=pinfo1["name"], date=pinfo1["date"], place=pinfo1["place"], notes=pinfo1["notes"], hostid=uid, nec=pinfo1["nec"])

        # Get most recently created party (THIS IS ALSO A RACE CONDITION)
        partyid = db.execute("SELECT id FROM parties WHERE hostid = :uid ORDER BY id DESC LIMIT 1", uid=uid)

        # Update db invited
        for invitee in inviteesl:
            # Get userid
            validuser = db.execute("SELECT id FROM users WHERE username = :username", username=invitee)
            if validuser:
                db.execute('''INSERT INTO invited (userid, partyid)
                              VALUES (:iid, :partyid)''', iid=validuser[0]["id"], partyid=partyid[0]["id"])

        # Return updated page
        message = "Success!"
        return render_template("create.html", pinfo1=pinfo1, inviteesl=inviteesl, message=message)

    else:
        return render_template("create.html")


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


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
