from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
import os
from database import Gebruiker, Rol, Boeken

dirname = os.path.dirname(__file__)
app = Flask(__name__, instance_path=dirname)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/bib.db"
app.secret_key = "Arno_augu_Cairo"
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()


@app.route("/")
def index():
    name = session.get('email')
    if name is not None:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["login_email"]
        password = request.form["login_paswoord"]
        user = db.session.query(Gebruiker).filter_by(email=email).first()
        if user is not None and user.paswoord == password:
            session["email"] = email
            flash("Login succesvol")
            return redirect("/")
        else:
            flash("Paswoord incorrect of de gebruiker bestaat nog niet.")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":

        register_name = request.form["name"]
        register_achternaam = request.form["achternaam"]
        register_email = request.form["register_email"]
        register_password = request.form["register_paswoord"]

        new_gebruiker = Gebruiker(naam=register_name, email = register_email, paswoord = register_password)
        db.session.add(new_gebruiker)
        db.session.commit()

        flash("Registratie succesvol")
        return redirect(url_for("login"))
    else:
        return render_template("register.html")


@app.route("/logout")
def logout():
    session["email"] = None
    return redirect("/")

@app.route("/boeken")
def boeken():
    return render_template("boeken.html")

@app.route("/boeken/add",methods = ["POST,GET"])
def boeken_add():

    if request.method == "POST":
        test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()

        if test.rol == "Bibliothecaris":
            admin = True
            return render_template("boeken_toev.html")
    else:
        abort(404)


if __name__ == "__main__":
    app.run(debug=True)
