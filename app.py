# de nodige zaken importeren
from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.sql.expression import or_
import os
from database import Gebruiker, Boek, Genre, Auteur, Thema
from werkzeug.utils import secure_filename
from flask_migrate import Migrate


from sqlalchemy_utils import ChoiceType


# dirname, is de weg naar dit bestand. 
dirname = os.path.abspath('instance')
app = Flask(__name__, instance_path=dirname)

# configugeren van de sessie
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app)

app.config["SESSION_PERMANENT"] = False
# je hebt verschillende soort databases dus vandaar het type nog eens toelichten.
app.config["SESSION_TYPE"] = "sqlalchemy"
# het pad configugeren van de route naar de database
basedir = os.path.abspath(os.path.dirname(__file__)) 
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'instance', 'bib.db')}"
app.config['UPLOAD_FOLDER'] = 'static/upload'

# de beveillingssleutel voor rededenen
app.secret_key = "Arno_augu_Cairo"
# een variabel weer korter maken voor sneller gebruik
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# hier worden alle tabellen aangemaakt

# definitie om te checken als een bepaalde waarde in een tabel zit in een bepaalde kolom
def checkContains(table_naam,column_naam,item):
 # getattr een string waarde omvormen naar een databasesyntax
    column = getattr(table_naam, column_naam)
    # het resultaat, query is dat hij gaat zoeken in de database. scalar = voor output terug naar string terug te brengen anders wordt het niet leesbaar voor de mens
    result = db.session.query(db.session.query(table_naam).filter(column == item).exists()).scalar()

    print(result)
    return result

# haalt een waarde uit een kolom
def getValue(table, column, item):
    result = db.session.query(table).filter(column == item).first()

    return result

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


    
# brengt je naar de hoofdpagina
@app.route("/")
def index():
    # hier word de email uit de sessie gehaald
    email = session.get('email')
    #indien er geen email is, wordt je terug gestuurd naar de inlogpagina
    if email == None:
        return redirect(url_for("login"))
    else:
    # zoeken op basis van email, welke gebruikers naam je hebt om nadien op de hoofdpagina weer te geven.
    user = db.session.query(Gebruiker).filter_by(email=email).first()
    if db.session.query(Boek).filter_by(bvdm=1).first():
        boek = db.session.query(Boek).filter_by(bvdm=1).first()
        bvdm = boek.bvdm
        isbn = boek.ISBN
    else:
        bvdm = None
        isbn = None
    if str(user.rol) == "Bibliothecaris":
        return render_template("index.html", rol=user.rol, bvdm = bvdm, isbn = isbn)
    return render_template("index.html", user = user, bvdm = bvdm, isbn = isbn)

# 2 methodes POST en GET, POST= wanneer een gebruiker data naar jou verstuurd. Get is wanneer een gebruiker data vraagt.
@app.route("/login", methods=["POST", "GET"])
def login():
    # checkt welke methode er wordt uitgevoerd
    if request.method == "POST":
        # haalt de email van form(input) en haalt het password uit de form
        email = request.form["login_email"]
        password = request.form["login_paswoord"]
        # hier zal hij zoeken in de database op basis van email naar een gebruiker.
        user = db.session.query(Gebruiker).filter_by(email=email).first()
        # als er een gebruiker bestaat en het password klopt, zet hij de email in de sessie en is de login succesvol en hij brengt je terug naar de hoofdpagina
        if user is not None and user.paswoord == password:
            session["email"] = email
            flash("Login succesvol")
            return redirect("/")
        # als er een gebruiker nog niet bestaat of het wachtwoord oncorrect. toont(flash), de melding en brengt hij je terug naar de login pagina(loop)
        else:
            flash("Paswoord incorrect of de gebruiker bestaat nog niet.")
            return redirect(url_for("login"))
        # render_template, als de methode niet post is zal hij deze runnen en dat is de html pagina runnen.
    return render_template("login.html")

# methodes post en get
@app.route("/register", methods=["POST", "GET"])
def register():
    rol_choices = [(value, label) for value, label in Gebruiker.rol_list]
    #als de methode post is runt hij onderstaande commando's
    if request.method == "POST":
        register_email = request.form["register_email"]
        if checkContains(Gebruiker,"email",register_email) == False:

    # alle velden die de gebruiker heeft ingevuld eruit halen (post)
            register_name = request.form["name"]
            register_achternaam = request.form["achternaam"]
            register_email = request.form["register_email"]
            register_password = request.form["register_paswoord"]
            rol = request.form["recht"]

            if "@" not in register_email:
                flash("Deze email bestaat niet")
            else:

            
            
            # een nieuwe gebruiker toevoegen aan de database met volgende velden.
                new_gebruiker = Gebruiker(naam=register_name, email = register_email, paswoord = register_password, rol = rol)
            #database voert dit uit
                db.session.add(new_gebruiker)
            # het opslaan van de veranderingen
                db.session.commit()

                flash("Registratie succesvol")
            return redirect(url_for("login"))
    else:
        #als het geen post is maar een get, steekt hij de rollen die hij uit de database haalt in een variabele en dan geeft hij deze weer in de rendertemplate om weer te geven.
        
        return render_template("register.html",rol_choices=rol_choices)









# als je uitlogt stopt de sessie, en zal je nadien opnieuw moeten inloggen
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# boekenpagina
@app.route("/boeken")
def boeken():
    # functie die alle boeken weergeeft
    boeken = db.session.query(Boek).all() # haalt alle boeken uit database en kent hen toe aan variabelle
    # de gebruiker van de persoon zelf opzoeken, die momenteel is ingelod en geeft hem nadien mee in de render template
    user = db.session.query(Gebruiker).filter_by(email = session.get('email')).first()
    return render_template("boeken.html", user = user)


@app.route("/search")
def search():
    # je kan argumenten in de url plaatsen en die q haalt de argumenten uit de url
    # checkt als q wel argumenten heeft
    q = request.args.get("q")
    if q:
        # haalt alle resultaten uit de database, join betekent dat ze er allebei moeten worden uitgehaald. 
        # De filter zorgt ervoor dat alles dat erop lijkt van de input wordt weergegeven
        results = db.session.query(Boek).join(Boek.auteurs).filter(
            or_(
                Boek.titel.ilike(f"%{q}%"),
                Auteur.naam.ilike(f"%{q}%"),
                Boek.ISBN.ilike(f"%{q}%")
                
            )
            # er is een limit van max 2O items uit de database te halen (max 20 prints)
        ).limit(20).all()
    else:
        # als er geen argumenten worden meegegeven, zal hij enkel de eerste 20 items van de database eruit halen
        results = db.session.query(Boek).limit(20).all()
        
    user = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
    # geeft gebruiker en resultaten weer terug
    return render_template("search_result.html", results=results, user=user)

# de werkplaats waar de bibliothecaris kan bewerekn en toevoegen
@app.route("/adminworkspace",methods = ["GET"])
def adminworkspace():
    if request.method == "GET":
        if session.get('email') == None:
            return redirect(url_for("login"))
        # hij test als je wel een bibliothecaris bent, via naam indien het niet zo is errorcode 404
        test = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
        if str(test.rol) == "Bibliothecaris":
            test = db.session.query(Gebruiker).filter_by(email = session.get('email')).first()
            #haalt alle genres, themas en auteurs uit database.
            if test.rol == "bibliothecaris":
                genres = db.session.query(Genre.naam).all()
                themas = db.session.query(Thema.naam).all()
                auteurs = db.session.query(Auteur.naam).all()
                
                return render_template("boeken_control.html", genres = genres, themas = themas , auteurs = auteurs)
            else:
                abort(404)
        else:
            return redirect(url_for("index"))
    else:
        abort(404)



#boeken toevoegen url
@app.route("/adminworkspace/tools/add",methods = ["POST"])
def add():
    if request.method == "POST":
        
        if session.get('email') == None:
            return redirect(url_for("login"))
        test = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
        if str(test.rol) == "Bibliothecaris":
            #hij kijkt als genr in je request form zit en niet een isbn, dus gaat ervan uit dat je enkle genre wilt toevoegen
            if "genre" in request.form and "ISBN" not in request.form:
                genre_naam = request.form["genre"].lower()
                #checkt als genre nog niet in database zit, indien niet voegt hij deze toe
                if checkContains(Genre,"naam",genre_naam) != True:
                    genre_naam = Genre(naam = genre_naam)
                    db.session.add(genre_naam)
                    db.session.commit()
                    flash("genre succesvol toegevoegd")
                else:
                    flash("Genre zit al in database.")
                

            elif "thema" in request.form and "ISBN" not in request.form:
                thema_naam = request.form["thema"].lower()
                if checkContains(Thema,"naam",thema_naam) != True:
                    thema_naam = Thema(naam = thema_naam)
                    db.session.add(thema_naam)
                    db.session.commit()
                    flash("Thema succesvol toegevoegd")
                else:
                    flash("Thema zit al in database.")

            elif "auteur" in request.form and "ISBN" not in request.form:
                auteur_naam = request.form["auteur"].lower()
                if checkContains(Auteur,"naam",auteur_naam) != True:
                    auteur_naam = Auteur(naam = request.form["auteur"].lower())
                    db.session.add(auteur_naam)
                    db.session.commit()
                    flash("Auteur succesvol toegevoegd")
                else:
                    flash("De auteur zit al in database.")
            #indien ISBN wel in je form zit, gaat ervan uit dat je boekt wilt toevoegen
            elif "ISBN" in request.form:
                ISBN_nr = request.form["ISBN"].lower()
                # controleren als hij nog niet in database zit
                if checkContains(Boek,"ISBN",ISBN_nr) != True:
                    ISBN = request.form["ISBN"]
                    titel = request.form["titel"]
                    beschrijving = request.form["beschrijving"]
                    status = request.form.get("status") == "Afwezig"
                    bvdm = request.form.get("bvdm") == "Ja"
                    # meerdere genres voer een boek mogelijk daarom is dit een lijst
                    selected_genres = request.form.getlist("genres")
                    selected_auteurs = request.form.getlist("auteurs")
                    selected_themas = request.form.getlist("themas")

                    #genres zoeken in database en indien er meerdere genres voor een boek zijn zal hij in een for lus elk genre toevoegen voor dit boek.
                    genres = [db.session.query(Genre).filter_by(naam=genre_name).first() or Genre(naam=genre_name) for genre_name in selected_genres]
                    auteurs = [db.session.query(Auteur).filter_by(naam=auteur_name).first() or Auteur(naam=auteur_name) for auteur_name in selected_auteurs]
                    themas = [db.session.query(Thema).filter_by(naam=thema_name).first() or Thema(naam=thema_name) for thema_name in selected_themas]
                    # titel en isbn toevoegen aan variabele boek
                    boek = Boek(titel=titel, ISBN=ISBN, beschrijving = beschrijving, status=status, bvdm=bvdm)
                    # meerdere genres verlengen met nieuwe genres
                    boek.genres.extend(genres)
                    boek.auteurs.extend(auteurs)
                    boek.themas.extend(themas)

                    
                    db.session.add(boek)
                    db.session.commit()

                    flash("Boek succesvol toegevoegd.")
                else:
                    flash("Deze ISBN is al eens gebruikt.")
               
                

                
                
            else:
                abort(404)
      
    return redirect(url_for("adminworkspace"))


# zoek boek, genre of thema om te  verwijderen
@app.route("/adminworkspace/tools/delete/<string:table>/search", methods=["GET"])
# <string:table> => zorgt voor dynamisch url en zorgt dat elk boek eigen aparte pagina heeft en het is ook een variabele
def searchdelete(table):
    #checken als de variabele wel in de tabel zetten, indien dit niet het geval is, error code ==> zorgen dat database niet crasht
    if table not in ["boek", "genre", "auteur", "thema"]:
        abort(404)
    table_temp = globals()[table.capitalize()]
    # weer argument uit url halen
    q = request.args.get("q")
    if q:
        if table == "boek":
            # als je tabel gelijk is aan de boek, zal hij op boek zoeken aan de hand van de titel.
            results = db.session.query(table_temp).filter(table_temp.titel.ilike(f"%{q}%")).all()
        else:
            # zoeken op de andere argumenten
            results = db.session.query(table_temp).filter(table_temp.naam.ilike(f"%{q}%")).all()
    else:
        results = db.session.query(table_temp).all()

    return render_template("search_delete.html", table=table, results=results)

 

@app.route("/adminworkspace/tools/delete/<string:table>", methods=["GET"])
# geeft weer welke je kan verwijderen
def delete(table):
    return render_template("delete.html",table=table)

# het effectief verwijderen van een boek 
@app.route("/adminworkspace/tools/delete/<string:table>/<int:voorwerp_id>", methods=["POST","GET"])
def delete_voorwerp(table, voorwerp_id):
        
        if table not in ["boek", "genre", "auteur", "thema"]:
            abort(404)  
 
        if not voorwerp_id:
            abort(400)  
    
        if table == "boek":
            # als je een boek wilt verwijderen gaat hij zoeken op basis van tabel en ISBN, 
            instance = db.session.query(globals()[table.capitalize()]).filter_by(ISBN = voorwerp_id).first()
            
        else:
            instance = db.session.query(globals()[table.capitalize()]).filter_by(id = voorwerp_id).first()
        print("test1")
        if instance is None:
            abort(404)  
        print("test")
        # het daadwerkelijk verwijderen van voorwerp en het opslaan van de database nadien
        db.session.delete(instance)
        db.session.commit()
# weergeven van boek of auteur of genre of thema, en als de table een boek is dan geeft hij ISBN weer en als het niet zo is enkel het ID
        flash(f"{table.capitalize()} with {'ISBN' if table == 'ISBN' else 'id'}  {voorwerp_id} succesvol verwijderd")
        return redirect(url_for("delete", table = table)) 

# verandernde van boekn
@app.route("/adminworkspace/tools/change/<int:ISBN>", methods=["POST", "GET"])
def change(ISBN):
    test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if str(test.rol) == "Bibliothecaris":
        if request.method == "POST":
            if "ISBN" in request.form:
                # kijken als je boek daadwerkelijk bestaat
                if checkContains(Boek, "ISBN", ISBN):
                    boek = db.session.query(Boek).filter_by(ISBN=ISBN).first()
                    new_ISBN = request.form["ISBN"]
                    titel = request.form["titel"]
                    status = request.form.get("status") == "Aanwezig"
                    bvdm = request.form.get("bvdm") == "Ja"
                    genre_names = request.form.getlist("genres")
                    thema_names = request.form.getlist("themas")
                    auteur_names = request.form.getlist("auteurs")
                    file = request.files['file']
                    if file and allowed_file(file.filename):
                    
                        old_filename = f"{ISBN}{os.path.splitext(file.filename)[1]}"
                        new_filename = f"{new_ISBN}{os.path.splitext(file.filename)[1]}"
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                        new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

                        
                        if new_ISBN != ISBN:
                            if os.path.exists(old_file_path):
                                os.rename(old_file_path, new_file_path)
                            else:
                                file.save(new_file_path)
                        else:
                            file.save(old_file_path)
                    
                    

                    # meerdere genres aan een variable toe kenne , indien nodig met for lus
                    genres = [db.session.query(Genre).filter_by(naam=name).first() for name in genre_names]
                    themas = [db.session.query(Thema).filter_by(naam=name).first() for name in thema_names]
                    auteurs = [db.session.query(Auteur).filter_by(naam=name).first() for name in auteur_names]
                    # nieuwe waardes toekennen om waardes aan te passen
                    boek.ISBN = new_ISBN
                    boek.titel = titel
                    boek.genres = genres
                    boek.themas = themas
                    boek.auteurs = auteurs
                    boek.status = status
                    boek.bvdm = bvdm
                    
                    db.session.commit()
                    flash("Boek succesvol veranderd")
                    return redirect(url_for("boeken"))
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
            
            
                
            
            boek = db.session.query(Boek).filter_by(ISBN=ISBN).first()
            return render_template(
                "boek_edit.html",
                def_ISBN=boek.ISBN,
                def_titel=boek.titel,
                # de boeken in variable steken indien nodig opnieuw for lus
                def_genres=[genre.naam for genre in boek.genres],
                def_themas=[thema.naam for thema in boek.themas],
                def_auteurs=[auteur.naam for auteur in boek.auteurs],
                genres=genres,
                themas=themas,
                auteurs=auteurs,
                def_status = boek.status,
                def_bvdm = boek.bvdm,
                
            )
    else:
        abort(404)

@app.route("/<int:ISBN>",methods=["POST", "GET"]) 
def boek(ISBN):
    if request.method == "post":
        return render_template()
    else:
        boek = db.session.query(Boek).filter_by(ISBN=ISBN).first()
        return render_template("boek.html",boek = boek)





    


@app.route("/PICT")
def PICT():
    return render_template("PICT.html")

@app.route("/taal")
def taal():
    return render_template("taal.html")

#admin page
@app.route("/admin", methods=["POST", "GET"])

def admin():
    test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if str(test.rol) == "Bibliothecaris":
        return render_template("admin.html", rol=test.rol)
    elif str(test.rol) == "Admin":
        return render_template("admin.html", rol=test.rol)
    else:
        return redirect(url_for("index"))

@app.route("/admin/gebruikers", methods=["GET"])
def gebruikers():
    # Haal alle gebruikers op uit de database
    gebruikers = db.session.query(Gebruiker).all()
    if not gebruikers:
        flash("Geen gebruikers gevonden.")
        return redirect(url_for("admin"))
    return render_template("gebruikers.html", gebruikers=gebruikers)

@app.route('/bewerk_gebruiker/<int:gebruiker_id>', methods=['GET', 'POST'])
def bewerk_gebruiker(gebruiker_id):
    gebruiker = db.session.query(Gebruiker).get(gebruiker_id)
    rol_choices = [
        ('admin', 'Admin'),
        ('bibliothecaris', 'Bibliothecaris'),
        ('ontlener', 'Ontlener')
    ]
    if request.method == 'POST':
        gebruiker.naam = request.form['naam']
        gebruiker.achternaam = request.form['achternaam']
        gebruiker.email = request.form['email']
        gebruiker.tl_nr = request.form['tl_nr']
        gebruiker.rol = request.form.get('recht')
        
        db.session.commit()
        return redirect(url_for('gebruikers'))  # Terug naar de gebruikerslijst

    return render_template('bewerk_gebruiker.html', gebruiker=gebruiker, rol_choices=rol_choices)

# je hebt het nodig voor het programma te runnen.
if __name__ == "__main__":
    app.run(debug=True)
