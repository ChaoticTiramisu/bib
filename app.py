from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
import os
from database import Bibliothecaris, Ontlener, Boeken, Login

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
        user = db.session.query(Login).filter_by(user_email=email).first()
        if user is not None and user.user_paswoord == password:
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
        name = request.form["name"]
        email = request.form["register_email"]
        password = request.form["register_paswoord"]

       
        new_ontlener = Ontlener(lln_naam=name)
        db.session.add(new_ontlener)
        db.session.commit()

        
        new_login = Login(lln_id=new_ontlener.lln_id, user_email=email, user_paswoord=password)
        db.session.add(new_login)
        db.session.commit()

        session["email"] = email
        flash("Registratie succesvol")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session["email"] = None
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
