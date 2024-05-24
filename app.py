from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
import os
from database import Gebruiker, Boek, Genre, Auteur, Thema

dirname = os.path.dirname(__file__)
app = Flask(__name__, instance_path=dirname)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/bib.db"
app.secret_key = "Arno_augu_Cairo"
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

def checkContains(table, column, item):
    
    result = db.session.query(table).filter(column == item).first()
    
    if result == None:
        return False
    else:

        return True

def getValue(table, column, item):
    result = db.session.query(table).filter(column == item).first()

    return result


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



#boeken toevoegen
@app.route("/add",methods = ["POST","GET"])
def add():
    if request.method == "POST":
        test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()

        if str(test.rol) == "Bibliothecaris":

            if "genre" in request.form and "ISBN" not in request.form:
                genre_naam = Genre(naam = request.form["genre"].lower())
                if not checkContains(Genre,"naam",genre_naam):
                    db.session.add(genre_naam)
                    db.session.commit()
                    flash("genre succesvol toegevoegd")
                else:
                    flash("Genre zit al in database.")
                

            elif "thema" in request.form and "ISBN" not in request.form:
                thema_naam = Thema(naam = request.form["genre"].lower())
                if not checkContains(Thema,"naam",thema_naam):
                    db.session.add(thema_naam)
                    db.session.commit()
                    flash("Thema succesvol toegevoegd")
                else:
                    flash("Thema zit al in database.")

            elif "auteur" in request.form and "ISBN" not in request.form:
                auteur_naam = Thema(naam = request.form["auteur"].lower())
                if not checkContains(Thema,"naam",thema_naam):
                    db.session.add(thema_naam)
                    db.session.commit()
                    flash("Auteur succesvol toegevoegd")
                else:
                    flash("De auteur zit al in database.")

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
      
    genres = db.session.query(Genre.naam).all()
    thema = db.session.query(Thema.naam).all()
    auteur = db.session.query(Auteur.naam).all()
    return render_template("boeken_control.html", genres = genres, thema = thema , auteur = auteur)

#boeken verwijderen
@app.route("/delete",methods = ["POST","GET"])
def delete():
    if request.method == "POST":
        test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
        print(test.rol)

        if str(test.rol) == "Bibliothecaris":
            if "boek" in request.form:
                boek_naam = Boek(naam = request.form["boek"].lower())
                if checkContains(Boek,"Titel",boek_naam):
                    ISBN = request.form["ISBN"].lower()
                    boek = db.session.query(Boek).filter_by(ISBN = ISBN)
                    db.session.delete(boek)
                    db.session.commit()
                    flash("Boek succesvol verwijderd")
                else:
                    flash("Boek zit niet in de database.")
            elif "Auteur" in request.form:
                auteur_naam = Auteur( naam = request.form["auteur"].lower())
                if checkContains(Boek,"naam",auteur_naam):
                    naam = request.form["auteur"].lower()
                    auteur = db.session.query(Auteur).filter_by(naam = naam)
                    db.session.delete(auteur)
                    db.session.commit()
                    flash("Auteur succesvol verwijderd")
                else:
                    flash("Auteur zit niet in de database.")
            elif "Genre" in request.form:
                genre_naam = Genre(naam = request.form["genre"].lower())
                if checkContains(Genre,"naam",genre_naam):
                    naam = request.form["genre"].lower()
                    genre = db.session.query(Genre).filter_by(naam = naam)
                    db.session.delete(genre)
                    db.session.commit()
                    flash("Genre succesvol verwijderd")
                else:
                    flash("Genre zit niet in de database.")
            elif "Thema" in request.form:
                thema_naam = Thema(naam = request.form["thema"].lower())
                if checkContains(Thema,"naam",thema_naam):
                    naam = request.form["thema"].lower()
                    thema = db.session.query(Thema).filter_by(naam = naam)
                    db.session.delete(thema)
                    db.session.commit()
                    flash("Thema succesvol verwijderd")
                else:
                    flash("Thema zit niet in de database.")

    genres = db.session.query(Genre.naam).all()
    thema = db.session.query(Thema.naam).all()
    auteur = db.session.query(Auteur.naam).all()
    return render_template("boeken_control.html", genres = genres, thema = thema , auteur = auteur)

#data aanpassen 
@app.route("/change",methods = ["POST","GET"])
def change():
    if request.method == "POST":
        test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()

        if str(test.rol) == "Bibliothecaris":
            if "ISBN" in request.form:
                boek = Boek(Titel = request.form["boek"].lower())
                if checkContains(Boek,"naam",boek):
                    
                    
                    boek = db.session.query(Boek).filter_by(ISBN = request.form["ISBN"]).first()
                    genre = db.session.query(Genre).filter_by(naam = request.form["Genre"]).first()
                    auteur = db.session.query(Auteur).filter_by(naam = request.form["auteur"]).first()
                    thema = db.session.query(Thema).filter_by(naam = request.form["thema"]).first()
                    boek.ISBN = request.form["ISBN"].lower()
                    boek.titel = request.form["Titel"].lower()
                    boek.genre_id = genre.id
                    boek.auteur_id = auteur.id
                    boek.thema_id = auteur.id

                    db.session.commit()
                   
                    flash("Boek succesvol veranderd")
                else:
                    flash("Boek zit niet in de database.")
            else:
                flash("Er is een fout opgetreden.")
            

    genres = db.session.query(Genre.naam).all()
    thema = db.session.query(Thema.naam).all()
    auteur = db.session.query(Auteur.naam).all()
    return render_template("boeken_control.html", genres = genres, thema = thema , auteur = auteur)








if __name__ == "__main__":
    app.run(debug=True)
