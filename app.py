from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import or_
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
    email = session.get('email')
    if email == None:
        return redirect(url_for("login"))
    user = db.session.query(Gebruiker).filter_by(email=email).first()
    return render_template("index.html", user = user)
    


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
    boeken = db.session.query(Boek).all()
    user = db.session.query(Gebruiker).filter_by(email = session.get('email')).first()
    return render_template("boeken.html", boeken = boeken, user = user)

@app.route("/search")
def search():
    q = request.args.get("q")
    print(q)
    if q:
        
        q = request.args.get('q')
        results = db.session.query(Boek).join(Boek.auteurs).filter(
        or_(
            Boek.titel.ilike(f"%{q}%"),
            Auteur.naam.ilike(f"%{q}%")
        )
        ).limit(20).all()
    else:
        results = []
    user = db.session.query(Gebruiker).filter_by(email = session.get('email')).first()
    return render_template("search_result.html", results = results , user = user)

@app.route("/adminworkspace",methods = ["GET"])
def adminworkspace():
    if request.method == "GET":
        if session.get('email') == None:
            return redirect(url_for("login"))
        else:
            test = db.session.query(Gebruiker).filter_by(email = session.get('email')).first()
            if test.rol == "bibliothecaris":
                genres = db.session.query(Genre.naam).all()
                themas = db.session.query(Thema.naam).all()
                auteurs = db.session.query(Auteur.naam).all()
                
                return render_template("boeken_control.html", genres = genres, themas = themas , auteurs = auteurs)
            else:
                abort(404)
    else:
        abort(404)



#boeken toevoegen
@app.route("/adminworkspace/tools/add",methods = ["POST"])
def add():
    if request.method == "POST":
        
        if session.get('email') == None:
            return redirect(url_for("login"))
        test = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
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
                thema_naam = Thema(naam = request.form["thema"].lower())
                if not checkContains(Thema,"naam",thema_naam):
                    db.session.add(thema_naam)
                    db.session.commit()
                    flash("Thema succesvol toegevoegd")
                else:
                    flash("Thema zit al in database.")

            elif "auteur" in request.form and "ISBN" not in request.form:
                auteur_naam = Auteur(naam = request.form["auteur"].lower())
                if not checkContains(Auteur,"naam",auteur_naam):
                    db.session.add(auteur_naam)
                    db.session.commit()
                    flash("Auteur succesvol toegevoegd")
                else:
                    flash("De auteur zit al in database.")

            elif "ISBN" in request.form:
                ISBN = request.form["ISBN"]
                titel = request.form["titel"]
                selected_genres = request.form.getlist("genres")
                selected_auteurs = request.form.getlist("auteurs")
                selected_themas = request.form.getlist("themas")


                genres = [db.session.query(Genre).filter_by(naam=genre_name).first() or Genre(naam=genre_name) for genre_name in selected_genres]
                auteurs = [db.session.query(Auteur).filter_by(naam=auteur_name).first() or Auteur(naam=auteur_name) for auteur_name in selected_auteurs]
                themas = [db.session.query(Thema).filter_by(naam=thema_name).first() or Thema(naam=thema_name) for thema_name in selected_themas]

               
                boek = Boek(titel=titel, ISBN=ISBN)

                
                boek.genres.extend(genres)
                boek.auteurs.extend(auteurs)
                boek.themas.extend(themas)

                
                db.session.add(boek)
                db.session.commit()

                flash("Boek succesvol toegevoegd.")
            else:
                abort(404)
      
    return redirect(url_for("adminworkspace"))

#boeken verwijderen
@app.route("/adminworkspace/tools/delete",methods = ["POST"])
def delete():
    if request.method == "POST":
        test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
        print(test.rol)

        if str(test.rol) == "Bibliothecaris":
            if "boek" in request.form:
                ISBN_nummer = Boek(ISBN = request.form["ISBN"].lower())
                if checkContains(Boek,"ISBN",boek):
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

    return redirect("adminworkspace")

#data aanpassen 
@app.route("/adminworkspace/tools/change/<int:ISBN>",methods = ["POST","GET"])
def change(ISBN):
    test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if str(test.rol) == "Bibliothecaris":
        if request.method == "POST":
            if "ISBN" in request.form:
                
                if checkContains(Boek, Boek.ISBN , ISBN):
                    
                    boek = db.session.query(Boek).filter_by(ISBN = ISBN).first()
                    genre = db.session.query(Genre).filter_by(naam = request.form["genre"]).first()
                    auteur = db.session.query(Auteur).filter_by(naam = request.form["auteur"]).first()
                    thema = db.session.query(Thema).filter_by(naam = request.form["thema"]).first()
                    boek.ISBN = request.form["ISBN"].lower()
                    boek.titel = request.form["titel"].lower()
                    boek.genre = genre
                    boek.auteur = auteur
                    boek.thema = thema

                    db.session.commit()
                    flash("Boek succesvol veranderd")
                    return redirect(url_for("index"))
                    
                else:
                    flash("Boek zit niet in de database.")
                    return redirect(url_for("index"))
            else:
                flash("Er is een fout opgetreden.")
                return redirect(url_for("index"))
        else:
            genres = db.session.query(Genre.naam).all()
            themas = db.session.query(Thema.naam).all()
            auteurs = db.session.query(Auteur.naam).all()
            boek = db.session.query(Boek).filter_by(ISBN = ISBN).first()
            return render_template("boek_edit.html"
                                   , def_ISBN = boek.ISBN
                                   , def_titel = boek.titel
                                   , def_genres = [Genre.naam for genre in boek.genres]
                                   , def_themas = [Thema.naam for thema in boek.themas]
                                   , def_auteurs = [Auteur.naam for auteur in boek.auteurs]
                                   ,genres = genres
                                   ,themas = themas
                                   ,auteurs = auteurs
                                     )
    else:
        abort(404)
            

    


@app.route("/PICT")
def PICT():
    return render_template("PICT.html")

@app.route("/taal")
def taal():
    return render_template("taal.html")



if __name__ == "__main__":
    app.run(debug=True)
