from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
import os
from database import Gebruiker, Rol, Boek, Genre, Auteur, Thema

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
        rol = request.form["recht"]

        new_gebruiker = Gebruiker(naam=register_name, email = register_email, paswoord = register_password, rol = rol)
        db.session.add(new_gebruiker)
        db.session.commit()

        flash("Registratie succesvol")
        return redirect(url_for("login"))
    else:
        rol_choices = [(value, label) for value, label in Gebruiker.rol_list]
        return render_template("register.html",rol_choices=rol_choices)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/boeken")
def boeken():
    return render_template("boeken.html")

@app.route("/add",methods = ["POST","GET"])
def add():
    if request.method == "POST":
        test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
        print("loop")
        if test.rol == "Bibliothecaris":

            if "genre" and not "ISBN" in request.form:
                genre = Genre(genre = request.form["genre"])
                db.session.add(genre)
                db.session.commit()
                flash("genre succesvol toegevoegd")

            elif "thema" and not "ISBN" in request.form:
                thema = Thema(thema = request.form["thema"])
                db.session.add(thema)
                db.session.commit()
                flash("thema succesvol toegevoegd")

            elif "auteur" and not "ISBN" in request.form:
                auteur = Auteur(auteur = request.form["auteur"])
                db.session.add(auteur)
                db.session.commit()
                flash("auteur succesvol toegevoegd")

            elif "ISBN" in request.form:
                ISBN = request.form["ISBN"]
                titel = request.form["titel"]
                form_genre = request.form["genre"]
                form_auteur = request.form["auteur"]
                form_thema = request.form["thema"]

                genre = db.session.query(Genre).filter_by(genre=form_genre).first()
                auteur = db.session.query(Auteur).filter_by(auteur=form_auteur).first()
                thema = db.session.query(Thema).filter_by(thema=form_thema).first()

                boek = Boek(genre_id = genre.id, titel = titel, auteur_id = auteur.id, ISBN = ISBN, thema_id = thema.id)

                db.session.add(boek)
                db.session.commit()

                flash("Boek succesvol toegevoegd.")
            else:
                abort(404)
    else:
        genres = db.session.query(Genre.genre)
        return render_template("boeken_control.html", genres = genres)
            
    






if __name__ == "__main__":
    app.run(debug=True)
