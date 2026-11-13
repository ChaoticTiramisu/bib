"""Schoolbibliotheek: Flask-applicatie.

Start lokaal met `./run.sh` of `python app.py`. Configuratie staat in config.py
en kan via omgevingsvariabelen of een .env-bestand overschreven worden.
"""

import os
from datetime import UTC, date, datetime, timedelta
from functools import wraps

import pandas as pd
from flask import (
    Flask,
    abort,
    flash,
    get_flashed_messages,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from sqlalchemy.sql.expression import or_
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from database import Auteur, Boek, Exemplaar, Gebruiker, Genre, Locatie, Reservatie, Thema
from services.exemplaren import (
    barcode_svg,
    kies_beschikbaar,
    kies_uitgeleend,
    maak_exemplaren,
    markeer_aanwezig,
    reconcileer_totaal,
    synchroniseer,
)
from services.isbn_lookup import (
    IsbnFout,
    LookupFout,
    download_cover,
    normaliseer_isbn,
    zoek_metadata,
)

app = Flask(__name__, instance_path=str(config.INSTANCE_DIR))
app.config.from_mapping(
    SECRET_KEY=config.SECRET_KEY,
    SQLALCHEMY_DATABASE_URI=config.DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=str(config.UPLOAD_DIR),
    MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# hier worden alle tabellen aangemaakt
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)


def controleer_wachtwoord(gebruiker, wachtwoord):
    """Controleer een wachtwoord en upgrade oude platte tekst naar bcrypt."""
    opgeslagen = gebruiker.paswoord or ""
    if opgeslagen.startswith(("$2a$", "$2b$", "$2y$")):
        return bcrypt.check_password_hash(opgeslagen, wachtwoord)
    if opgeslagen == wachtwoord:
        gebruiker.paswoord = bcrypt.generate_password_hash(wachtwoord).decode("utf-8")
        db.session.commit()
        return True
    return False


def actief_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        gebruiker = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
        if not gebruiker or gebruiker.actief == 0:
            flash("Je account is geblokkeerd, vraag je leerkracht voor meer info.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# definitie om te checken als een bepaalde waarde in een tabel zit in een bepaalde kolom
def checkContains(table_naam, column_naam, item):
    # getattr een string waarde omvormen naar een databasesyntax
    column = getattr(table_naam, column_naam)
    return db.session.query(table_naam).filter(column == item).first() is not None

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cover_path(boek):
    """Geef het pad naar de cover van een boek, of de standaardcover."""
    base = config.UPLOAD_DIR / boek.ISBN
    for extensie in (".jpg", ".jpeg", ".png"):
        if base.with_suffix(extensie).exists():
            return f"/static/upload/{boek.ISBN}{extensie}"
    return "/static/upload/default_cover.png"


def huidige_gebruiker():
    email = session.get("email")
    if not email:
        return None
    return db.session.query(Gebruiker).filter_by(email=email).first()


def is_bibliothecaris(gebruiker=None):
    gebruiker = gebruiker or huidige_gebruiker()
    return bool(gebruiker and str(gebruiker.rol).lower() in ("admin", "bibliothecaris"))


def parse_aantal(waarde, standaard=1):
    try:
        return max(1, int(waarde))
    except (TypeError, ValueError):
        return standaard


def parse_int(waarde):
    try:
        return int(waarde)
    except (TypeError, ValueError):
        return None


def iso_utc(waarde):
    """ISO-string met tijdzone, ook voor naïeve datetimes uit SQLite."""
    if waarde is None:
        return None
    if waarde.tzinfo is None:
        waarde = waarde.replace(tzinfo=UTC)
    return waarde.isoformat()


def als_lijst(waarde):
    if not waarde:
        return []
    if isinstance(waarde, str):
        items = waarde.split(",")
    else:
        items = waarde
    return [str(item).strip() for item in items if str(item).strip()]

@app.context_processor
def inject_gebruiker():
    gebruiker = None
    if 'gebruiker_id' in session:
        gebruiker = db.session.get(Gebruiker,session.get("gebruiker_id"))

    return {
        'gebruiker': gebruiker,
        'email': getattr(gebruiker, 'email', None),
        'naam': getattr(gebruiker, 'naam', None),
        'achternaam': getattr(gebruiker, 'achternaam', None),
        'rol': getattr(gebruiker, 'rol', None)
    }

# brengt je naar de hoofdpagina
@app.route("/")
def index():
    # hier word de email uit de sessie gehaald
    email = session.get('email')
    #indien er geen email is, wordt je terug gestuurd naar de inlog pagina
    if email is None:
        return redirect(url_for("login"))
    else:
    # zoeken op basis van email, welke gebruikers naam je hebt om nadien op de hoofdpagina weer te geven.
        user = db.session.query(Gebruiker).filter_by(email=email).first()
        if user is None:
            return redirect(url_for("login"))
        boek_van_de_maand = (
            db.session.query(Boek)
            .filter_by(bvdm=True, deleted=False)
            .first()
        )
        bvdm = boek_van_de_maand is not None
        isbn = boek_van_de_maand.ISBN if boek_van_de_maand else None
        bvdm_cover = cover_path(boek_van_de_maand) if boek_van_de_maand else None
    laatste_boeken = (
        db.session.query(Boek)
        .filter_by(deleted=False)
        .order_by(Boek.toegevoegd_op.desc())
        .limit(3)
        .all()
    )
    for boek in laatste_boeken:
        boek.cover_path = cover_path(boek)
    return render_template(
        "index.html",
        bvdm=bvdm,
        isbn=isbn,
        bvdm_cover=bvdm_cover,
        boeken=laatste_boeken,
    )

# 2 methodes POST en GET, POST= wanneer een gebruiker data naar jou verstuurd. Get is wanneer een gebruiker data vraagt.
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["login_email"]
        password = request.form["login_paswoord"]
        user = db.session.query(Gebruiker).filter_by(email=email, deleted=False).first()
        if user and controleer_wachtwoord(user, password):
            session['gebruiker_id'] = user.id
            session['email'] = user.email
            flash("Login succesvol", "success")
            return redirect(url_for("index"))
        else:
            flash("Paswoord incorrect of de gebruiker bestaat nog niet.", "error")
            return redirect(url_for("login"))
    # Only flash this message if it's a GET request and not a redirect
    return render_template("login.html", messages=get_flashed_messages(with_categories=True))

# methodes post en get
@app.route("/register", methods=["POST", "GET"])
def register():
    rol_choices = [(value, label) for value, label in Gebruiker.rol_list]
    #als de methode post is runt hij onderstaande commando's
    if request.method == "POST":
        register_email = request.form["register_email"]
        if not checkContains(Gebruiker,"email",register_email):

    # alle velden die de gebruiker heeft ingevuld eruit halen (post)
            register_name = request.form["name"]
            register_achternaam = request.form["achternaam"]
            register_email = request.form["register_email"]
            register_password = request.form["register_paswoord"]
            rol = request.form["recht"]

            if "@" not in register_email:
                flash("Deze email bestaat niet","error")
            else:

            
            
            # een nieuwe gebruiker toevoegen aan de database met volgende velden.
                new_gebruiker = Gebruiker(naam=register_name,achternaam = register_achternaam, email = register_email, rol = rol, paswoord = bcrypt.generate_password_hash(register_password).decode("utf-8"))
            #database voert dit uit
                db.session.add(new_gebruiker)
            # het opslaan van de veranderingen
                db.session.commit()

            flash("Registratie succesvol","success")
            return redirect(url_for("login"))
        else:
             flash("Deze email adress is al in gebruik.")
             return render_template("register.html",rol_choices=rol_choices)
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
@actief_required
def boeken():
    email = session.get('email')
    if email is None:
        return redirect(url_for("login"))
    boeken = db.session.query(Boek).filter_by(deleted=False).all()
    user = db.session.query(Gebruiker).filter_by(email=email).first()
    genres = db.session.query(Genre).filter_by(deleted=False).all()
    auteurs = db.session.query(Auteur).filter_by(deleted=False).all()
    themas = db.session.query(Thema).filter_by(deleted=False).all()
    locaties = db.session.query(Locatie).all()
    for boek in boeken:
        boek.cover_path = cover_path(boek)
    return render_template(
        "boeken.html",
        boeken=boeken,
        user=user,
        genres=genres,
        auteurs=auteurs,
        themas=themas,
        locaties=locaties
    )

@app.route("/search_partial")
@actief_required
def search_partial():
    q = request.args.get("q", "").strip()
    genre = request.args.get("genre", "")
    auteur = request.args.get("auteur", "")
    thema = request.args.get("thema", "")
    locatie = request.args.get("locatie", "")
    beschikbaar = request.args.get("beschikbaar", "")

    boeken_query = db.session.query(Boek).outerjoin(Boek.auteurs).outerjoin(Boek.genres).outerjoin(Boek.themas).outerjoin(Boek.locatie).filter(Boek.deleted.is_(False))

    if q:
        boeken_query = boeken_query.filter(
            or_(
                Boek.titel.ilike(f"%{q}%"),
                Auteur.naam.ilike(f"%{q}%"),
                Boek.ISBN.ilike(f"%{q}%"),
            )
        )
    if genre:
        boeken_query = boeken_query.filter(Genre.naam == genre)
    if auteur:
        boeken_query = boeken_query.filter(Auteur.naam == auteur)
    if thema:
        boeken_query = boeken_query.filter(Thema.naam == thema)
    if locatie:
        boeken_query = boeken_query.filter(Locatie.naam == locatie)
    if beschikbaar == "1":
        boeken_query = boeken_query.filter(Boek.beschikbaar_aantal > 0, Boek.status.is_(False))

    boeken = boeken_query.distinct().limit(20).all()
    user = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
    for boek in boeken:
        boek.cover_path = cover_path(boek)
    return render_template("partials/boeken_grid.html", boeken=boeken, user=user)


# de werkplaats waar de bibliothecaris kan bewerekn en toevoegen
@app.route("/adminworkspace", methods=["GET"])
@actief_required
def adminworkspace():
    if session.get('email') is None:
        return redirect(url_for("login"))
    
    # Fetch the logged-in user
    gebruiker = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
    if gebruiker and gebruiker.rol in ["bibliothecaris", "admin"]:
        # Haal alle genres, themas en auteurs uit de database
        genres = db.session.query(Genre.naam).filter_by(deleted = False).all()
        themas = db.session.query(Thema.naam).filter_by(deleted = False).all()
        auteurs = db.session.query(Auteur.naam).filter_by(deleted = False).all()
        locaties = db.session.query(Locatie).order_by(Locatie.naam).all()
        
        return render_template("boeken_control.html", genres=genres, themas=themas, auteurs=auteurs, locaties=locaties)
    else:
        abort(404)



#boeken toevoegen url
@app.route("/adminworkspace/tools/add", methods=["POST", "GET"])
@actief_required
def add():
    if request.method == "POST" and "genre" in request.form and "ISBN" not in request.form:
        genre_naam = request.form["genre"].lower()
        if not checkContains(Genre, "naam", genre_naam):
            new_genre = Genre(naam=genre_naam)
            db.session.add(new_genre)
            db.session.commit()
            genres = db.session.query(Genre.naam).all()
            response = make_response(render_template("partials/genres.html", genres=genres))
            response.headers['HX-Trigger'] = jsonify({"showMessage": f"Genre '{genre_naam}' succesvol toegevoegd."})
            return response
        else:
            genres = db.session.query(Genre.naam).all()
            response = make_response(render_template("partials/genres.html", genres=genres))
            response.headers['HX-Trigger'] = jsonify({"showMessage": f"Genre '{genre_naam}' zit al in de database."})
            return response

    # Handle thema addition
    elif "thema" in request.form and "ISBN" not in request.form:
        thema_naam = request.form["thema"].lower()
        if not checkContains(Thema, "naam", thema_naam):
            new_thema = Thema(naam=thema_naam)
            db.session.add(new_thema)
            db.session.commit()
            themas = db.session.query(Thema.naam).all()
            response = make_response(render_template("partials/themas.html", themas=themas))
            response.headers['HX-Trigger'] = jsonify({"showMessage": f"Thema '{thema_naam}' succesvol toegevoegd."})
            return response
        else:
            themas = db.session.query(Thema.naam).all()
            response = make_response(render_template("partials/themas.html", themas=themas))
            response.headers['HX-Trigger'] = jsonify({"showMessage": f"Thema '{thema_naam}' zit al in de database."})
            return response

    # Handle auteur addition
    elif "auteur" in request.form and "ISBN" not in request.form:
        auteur_naam = request.form["auteur"].lower()
        if not checkContains(Auteur, "naam", auteur_naam):
            new_auteur = Auteur(naam=auteur_naam)
            db.session.add(new_auteur)
            db.session.commit()
            auteurs = db.session.query(Auteur.naam).all()
            response = make_response(render_template("partials/auteurs.html", auteurs=auteurs))
            response.headers['HX-Trigger'] = jsonify({"showMessage": f"Auteur '{auteur_naam}' succesvol toegevoegd."})
            return response
        else:
            auteurs = db.session.query(Auteur.naam).all()
            response = make_response(render_template("partials/auteurs.html", auteurs=auteurs))
            response.headers['HX-Trigger'] = jsonify({"showMessage": f"Auteur '{auteur_naam}' zit al in de database."})
            return response

    # Handle book addition
    elif "ISBN" in request.form:
        ISBN_nr = request.form["ISBN"].lower()
        if not checkContains(Boek, "ISBN", ISBN_nr):
            ISBN = request.form["ISBN"]
            titel = request.form["titel"]
            beschrijving = request.form["beschrijving"]
            status = request.form.get("status") == "Afwezig"
            bvdm = request.form.get("bvdm") == "Ja"
            
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = f"{ISBN}{os.path.splitext(file.filename)[1]}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
            
            selected_genres = request.form.getlist("genres")
            selected_auteurs = request.form.getlist("auteurs")
            selected_themas = request.form.getlist("themas")
            locatie_naam = request.form.get("locatie")
            locatie = db.session.query(Locatie).filter_by(naam=locatie_naam).first()
            if not locatie and locatie_naam:
                locatie = Locatie(naam=locatie_naam)
                db.session.add(locatie)
                db.session.commit()

            genres = [db.session.query(Genre).filter_by(naam=genre_name).first() or Genre(naam=genre_name) 
                      for genre_name in selected_genres]
            auteurs = [db.session.query(Auteur).filter_by(naam=auteur_name).first() or Auteur(naam=auteur_name) 
                      for auteur_name in selected_auteurs]
            themas = [db.session.query(Thema).filter_by(naam=thema_name).first() or Thema(naam=thema_name) 
                      for thema_name in selected_themas]

            aantal = parse_aantal(request.form.get("aantal", 1))

            boek = Boek(
                titel=titel,
                ISBN=ISBN,
                beschrijving=beschrijving,
                status=status,
                bvdm=bvdm,
                aantal=aantal,
                beschikbaar_aantal=aantal,
                locatie=locatie
            )
            
            boek.genres.extend(genres)
            boek.auteurs.extend(auteurs)
            boek.themas.extend(themas)

            db.session.add(boek)
            maak_exemplaren(db.session, boek, aantal)
            db.session.commit()

            flash(f"Boek '{titel}' succesvol toegevoegd.", "success")
            return redirect(url_for("adminworkspace"))
        else:
            flash(f"Boek met ISBN '{ISBN_nr}' zit al in de database.", "error")
            return redirect(url_for("adminworkspace"))
    else:
        flash("Onbekende fout opgetreden.", "error")
        abort(404)


@app.route("/adminworkspace/scan", methods=["GET", "POST"])
@actief_required
def scan_boek():
    """Boek toevoegen door een ISBN te scannen of te typen."""
    gebruiker = huidige_gebruiker()
    if not is_bibliothecaris(gebruiker):
        if request.method == "POST":
            return jsonify(error="Geen rechten om boeken toe te voegen."), 403
        flash("Je hebt geen toegang tot de scanpagina.", "error")
        return redirect(url_for("index"))

    if request.method == "GET":
        locaties = db.session.query(Locatie).order_by(Locatie.naam).all()
        return render_template("scan.html", locaties=locaties)

    data = request.get_json(silent=True) or request.form
    try:
        isbn = normaliseer_isbn(data.get("isbn", ""))
    except IsbnFout as fout:
        return jsonify(error=str(fout)), 400

    aantal = parse_aantal(data.get("aantal", 1))

    bestaand = db.session.query(Boek).filter_by(ISBN=isbn, deleted=False).first()
    if bestaand:
        maak_exemplaren(db.session, bestaand, aantal)
        db.session.commit()
        return jsonify(
            status="bestaat",
            isbn=isbn,
            titel=bestaand.titel,
            aantal=bestaand.aantal,
            beschikbaar=bestaand.beschikbaar_aantal,
            bericht=(
                f"'{bestaand.titel}' bestond al; {aantal} exemplaar/exemplaren toegevoegd."
            ),
        )

    titel = (data.get("titel") or "").strip()
    if not titel:
        return jsonify(error="Titel is verplicht."), 400

    beschrijving = (data.get("beschrijving") or "").strip() or "Geen beschrijving beschikbaar."

    locatie_naam = (data.get("locatie") or "").strip()
    locatie = None
    if locatie_naam:
        locatie = db.session.query(Locatie).filter_by(naam=locatie_naam).first()
        if not locatie:
            locatie = Locatie(naam=locatie_naam)
            db.session.add(locatie)

    boek = Boek(
        ISBN=isbn,
        titel=titel,
        beschrijving=beschrijving,
        status=False,
        bvdm=False,
        aantal=aantal,
        beschikbaar_aantal=aantal,
        aantal_bladzijden=parse_int(data.get("paginas")),
        locatie=locatie,
    )
    db.session.add(boek)

    for naam in als_lijst(data.get("auteurs")):
        auteur = (
            db.session.query(Auteur).filter(func.lower(Auteur.naam) == naam.lower()).first()
            or Auteur(naam=naam)
        )
        boek.auteurs.append(auteur)

    for naam in als_lijst(data.get("genres")):
        genre = (
            db.session.query(Genre).filter(func.lower(Genre.naam) == naam.lower()).first()
            or Genre(naam=naam)
        )
        boek.genres.append(genre)

    maak_exemplaren(db.session, boek, aantal)
    db.session.commit()

    cover = download_cover(data.get("cover_url"), isbn, config.UPLOAD_DIR)

    return jsonify(
        status="nieuw",
        isbn=isbn,
        titel=boek.titel,
        aantal=aantal,
        cover=cover,
        bericht=f"'{boek.titel}' toegevoegd.",
    )


@app.get("/api/isbn/<string:isbn>")
def api_isbn(isbn):
    """Metadata voor een ISBN, of de bestaande boekgegevens."""
    gebruiker = huidige_gebruiker()
    if not gebruiker:
        return jsonify(error="Niet ingelogd."), 401
    if not is_bibliothecaris(gebruiker):
        return jsonify(error="Geen rechten."), 403

    try:
        genormaliseerd = normaliseer_isbn(isbn)
    except IsbnFout as fout:
        return jsonify(error=str(fout)), 400

    bestaand = db.session.query(Boek).filter_by(ISBN=genormaliseerd, deleted=False).first()
    if bestaand:
        return jsonify(
            isbn=genormaliseerd,
            bestaat=True,
            titel=bestaand.titel,
            auteurs=[auteur.naam for auteur in bestaand.auteurs],
            aantal=bestaand.aantal,
            beschikbaar=bestaand.beschikbaar_aantal,
            beschrijving=bestaand.beschrijving,
            paginas=bestaand.aantal_bladzijden,
            bron="database",
        )

    try:
        metadata = zoek_metadata(genormaliseerd)
    except LookupFout as fout:
        return jsonify(error=str(fout), isbn=genormaliseerd, bestaat=False), 404

    metadata["bestaat"] = False
    return jsonify(metadata)


@app.route("/adminworkspace/exemplaren")
@actief_required
def exemplaren_overzicht():
    gebruiker = huidige_gebruiker()
    if not is_bibliothecaris(gebruiker):
        flash("Je hebt geen toegang tot het exemplarenoverzicht.", "error")
        return redirect(url_for("index"))

    boeken = db.session.query(Boek).filter_by(deleted=False).order_by(Boek.titel).all()
    for boek in boeken:
        synchroniseer(db.session, boek)
    db.session.commit()
    return render_template("exemplaren.html", boeken=boeken)


@app.route("/adminworkspace/boek/<string:isbn>/labels")
@actief_required
def labels(isbn):
    gebruiker = huidige_gebruiker()
    if not is_bibliothecaris(gebruiker):
        flash("Je hebt geen toegang tot de labels.", "error")
        return redirect(url_for("index"))

    boek = db.session.query(Boek).filter_by(ISBN=isbn, deleted=False).first_or_404()
    exemplaren = [e for e in boek.exemplaren if not e.deleted]
    label_data = [
        {"exemplaar": exemplaar, "svg": barcode_svg(exemplaar.barcode)}
        for exemplaar in exemplaren
    ]
    return render_template("labels.html", boek=boek, labels=label_data)


@app.route("/adminworkspace/inventaris")
@actief_required
def inventaris():
    gebruiker = huidige_gebruiker()
    if not is_bibliothecaris(gebruiker):
        flash("Je hebt geen toegang tot de inventaris.", "error")
        return redirect(url_for("index"))
    return render_template("inventaris.html")


@app.get("/api/exemplaar/<string:barcode>")
def api_exemplaar(barcode):
    gebruiker = huidige_gebruiker()
    if not gebruiker:
        return jsonify(error="Niet ingelogd."), 401
    if not is_bibliothecaris(gebruiker):
        return jsonify(error="Geen rechten."), 403

    exemplaar = (
        db.session.query(Exemplaar).filter_by(barcode=barcode, deleted=False).first()
    )
    if not exemplaar:
        return jsonify(error=f"Exemplaar {barcode} niet gevonden."), 404

    boek = exemplaar.boek
    locatie = exemplaar.locatie or boek.locatie
    return jsonify(
        barcode=exemplaar.barcode,
        status=str(exemplaar.status),
        isbn=boek.ISBN,
        titel=boek.titel,
        locatie=locatie.naam if locatie else None,
        laatst_gezien=iso_utc(exemplaar.laatst_gezien),
    )


@app.post("/api/exemplaar/<string:barcode>/aanwezig")
def api_exemplaar_aanwezig(barcode):
    gebruiker = huidige_gebruiker()
    if not gebruiker:
        return jsonify(error="Niet ingelogd."), 401
    if not is_bibliothecaris(gebruiker):
        return jsonify(error="Geen rechten."), 403

    exemplaar = (
        db.session.query(Exemplaar).filter_by(barcode=barcode, deleted=False).first()
    )
    if not exemplaar:
        return jsonify(error=f"Exemplaar {barcode} niet gevonden."), 404

    markeer_aanwezig(db.session, exemplaar)
    db.session.commit()
    return jsonify(
        barcode=exemplaar.barcode,
        status=str(exemplaar.status),
        laatst_gezien=iso_utc(exemplaar.laatst_gezien),
        bericht=f"{exemplaar.barcode} gemarkeerd als aanwezig.",
    )


@app.route("/delpage", methods=["GET"])
@actief_required
def delpage():
    # Fetch all items from the database
    boeken = db.session.query(Boek).filter_by(deleted = False).all()
    genres = db.session.query(Genre).filter_by(deleted = False).all()
    themas = db.session.query(Thema).filter_by(deleted = False).all()
    auteurs = db.session.query(Auteur).filter_by(deleted = False).all()

    # Pass the items to the template
    return render_template("deletepage.html", boeken=boeken, genres=genres, themas=themas, auteurs=auteurs)

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
            results = db.session.query(table_temp).filter(table_temp.titel.ilike(f"%{q}%"),deleted = False).all()
        else:
            # zoeken op de andere argumenten
            results = db.session.query(table_temp).filter(table_temp.naam.ilike(f"%{q}%"),deleted = False).all()
    else:
        results = db.session.query(table_temp).all()

    return render_template("search_delete.html", table=table, results=results)

 

@app.route("/adminworkspace/tools/delete/<string:table>", methods=["GET"])
@actief_required
# geeft weer welke je kan verwijderen
def delete(table):
    return render_template("delete.html",table=table)

# het effectief verwijderen van een boek 
@app.route("/adminworkspace/tools/delete/<string:table>/<int:voorwerp_id>", methods=["POST","GET"])
@actief_required
def delete_voorwerp(table, voorwerp_id):
        if table not in ["boek", "genre", "auteur", "thema"]:
            abort(404)  
 
        if not voorwerp_id:
            abort(400)  
    
        if table == "boek":
            # Check if the book has any reservations
            instance = db.session.query(Boek).filter_by(ISBN=voorwerp_id,deleted = False).first()
            if instance is None:
                abort(404)
                
            # Check for active reservations
            if instance.reservaties:
                # Delete all reservations first
                for reservatie in instance.reservaties:
                    reservatie.deleted = True  
                db.session.commit()  # Commit the reservation deletions first
            
            # Now delete the book and its physical copies
            for exemplaar in instance.exemplaren:
                exemplaar.deleted = True
            instance.deleted = True
        else:
            instance = db.session.query(globals()[table.capitalize()]).filter_by(id=voorwerp_id).first()
            if instance is None:
                abort(404)
            instance.deleted = True 

        try:
            db.session.commit()
            flash(f"{table.capitalize()} with {'ISBN' if table == 'boek' else 'id'} {voorwerp_id} succesvol verwijderd", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Er is een fout opgetreden bij het verwijderen: {str(e)}", "error")
            
        return redirect(url_for("delpage")) 

# verandernde van boeken
@app.route("/adminworkspace/tools/change/<string:ISBN>", methods=["POST", "GET"])
@actief_required
def change(ISBN):
    test = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if str(test.rol).lower() in ["bibliothecaris", "admin"]:
        if request.method == "POST":
            if "ISBN" in request.form:
                # kijken als je boek daadwerkelijk bestaat
                if checkContains(Boek, "ISBN", ISBN):
                    boek = db.session.query(Boek).filter_by(ISBN=ISBN).first()
                    new_ISBN = request.form["ISBN"]
                    titel = request.form["titel"]
                    aantal_exemplaren = (
                        request.form.get("aantal")
                        or request.form.get("beschikbaar_aantal")
                        or boek.aantal
                    )
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

                    # meerdere genres aan een variable toe kennen, indien nodig met for lus
                    genres = [db.session.query(Genre).filter_by(naam=name).first() for name in genre_names]
                    themas = [db.session.query(Thema).filter_by(naam=name).first() for name in thema_names]
                    auteurs = [db.session.query(Auteur).filter_by(naam=name).first() for name in auteur_names]
                    if new_ISBN != ISBN and boek.exemplaren:
                        flash(
                            "Het ISBN kan niet gewijzigd worden zolang er exemplaren bestaan.",
                            "error",
                        )
                        return redirect(url_for("change", ISBN=ISBN))

                    # nieuwe waardes toekennen om waardes aan te passen
                    try:
                        reconcileer_totaal(db.session, boek, parse_aantal(aantal_exemplaren))
                    except ValueError as fout:
                        db.session.rollback()
                        flash(str(fout), "error")
                        return redirect(url_for("change", ISBN=ISBN))

                    boek.ISBN = new_ISBN
                    boek.titel = titel
                    boek.genres = genres
                    boek.themas = themas
                    boek.auteurs = auteurs
                    boek.status = status
                    boek.bvdm = bvdm

                    db.session.commit()
                    flash("Boek succesvol veranderd", "success")
                    return redirect(url_for("boeken"))
                else:
                    flash("Boek zit niet in de database.")
                    return redirect(url_for("index"))
            else:
                flash("Er is een fout opgetreden.")
                return redirect(url_for("index"))
        else:
            genres = db.session.query(Genre.naam).filter_by(deleted = False).all()
            themas = db.session.query(Thema.naam).filter_by(deleted = False).all()
            auteurs = db.session.query(Auteur.naam).filter_by(deleted = False).all()

            boek = db.session.query(Boek).filter_by(ISBN=ISBN,deleted = False).first()
            return render_template(
                "boek_edit.html",
                boek=boek,  # Pass the boek object to the template
                def_ISBN=boek.ISBN,
                def_titel=boek.titel,
                def_genres=[genre.naam for genre in boek.genres],
                def_themas=[thema.naam for thema in boek.themas],
                def_auteurs=[auteur.naam for auteur in boek.auteurs],
                genres=genres,
                themas=themas,
                auteurs=auteurs,
                def_status=boek.status,
                def_bvdm=boek.bvdm,
            )
    else:
        abort(404)

@app.route("/boek/<string:ISBN>")
@actief_required
def boek(ISBN):
    boek = db.session.query(Boek).filter_by(ISBN=ISBN, deleted=False).first_or_404()
    # Cover path bepalen
    boek.cover_path = cover_path(boek)
    # reserved_dates en andere context zoals je al had
    reserved_dates = [
        {
            "title": "Gereserveerd",
            "start": reservatie.start_date.strftime('%Y-%m-%d'),
            "end": (reservatie.end_date + timedelta(days=1)).strftime('%Y-%m-%d')
        }
        for reservatie in boek.reservaties
    ]
    return render_template(
        "boek.html",
        boek=boek,
        reserved_dates=reserved_dates
    )


@app.route('/boek/<string:ISBN>/reserveer', methods=['GET', 'POST'])
@actief_required
def reserveer_boek(ISBN):
    if 'email' not in session:
        return redirect(url_for('login'))
    gebruiker = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
    boek = db.session.query(Boek).filter_by(ISBN=ISBN).first_or_404()
    if boek.status:
        flash("Dit boek is momenteel afwezig en kan niet uitgeleend worden.", "error")
        return redirect(url_for('boeken'))
    if boek.beschikbaar_aantal == 0:
        flash("Er zijn geen exemplaren beschikbaar.", "error")
        return redirect(url_for('boeken'))
    if gebruiker.actief == 0:
        flash("Je account is geblokkeerd, vraag je leerkracht voor meer info.", "error")
        return render_template('index.html')
    else:
        boek = db.session.query(Boek).filter_by(ISBN=ISBN).first_or_404()
        reservations = db.session.query(Reservatie).filter_by(boek_isbn=boek.ISBN).all()

        if request.method == 'POST':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')

           
            if not start_date_str or not end_date_str:
                flash("Startdatum en einddatum zijn verplicht.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))

            try:
                
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Ongeldige datumindeling. Gebruik het formaat JJJJ-MM-DD.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))

            
            if (end_date - start_date).days > 21:
                flash("Een reservering kan niet langer dan 3 weken duren.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))
            
            if start_date < datetime.now().date():
                flash("De startdatum moet in de toekomst liggen.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))
            
            if datetime.now().date() + timedelta(days=90) < end_date:
                flash("De einddatum mag niet verder dan 3 maanden in de toekomst liggen.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))

            if end_date <= start_date:
                flash("De einddatum moet na de startdatum liggen.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))
            

            # Check for overlapping reservations
            overlapping = db.session.query(Reservatie).filter(
                Reservatie.boek_isbn == boek.ISBN,
                Reservatie.start_date <= end_date,
                Reservatie.end_date >= start_date
            ).first()

            if overlapping:
                flash("Deze periode is al gereserveerd.", "error")
                return redirect(url_for('reserveer_boek', ISBN=ISBN))

            # Create a new reservation
            new_reservation = Reservatie(
                boek_isbn=boek.ISBN,
                gebruiker_id=session.get('gebruiker_id'),
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(new_reservation)
            db.session.commit()

            flash("Boek succesvol gereserveerd!", "success")
            return redirect(url_for('reserveer_boek', ISBN=ISBN))

        reserved_dates = [
            {
                'title': 'Gereserveerd',
                'start': r.start_date.isoformat(),
                'end': (r.end_date + timedelta(days=1)).isoformat()  # Add 1 day to include the end date
            }
            for r in reservations
        ]

        # Voeg reserved_dates_flat toe:
        reserved_dates_flat = []
        for r in reservations:
            current = r.start_date
            while current <= r.end_date:
                reserved_dates_flat.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)

        return render_template(
            'reserveer_boek.html',
            boek=boek,
            reserved_dates=reserved_dates,
            reserved_dates_flat=reserved_dates_flat
        )


@app.route("/PICT")
def PICT():
    return render_template("PICT.html")

@app.route("/taal")
def taal():
    return render_template("taal.html")

@app.route("/overons")
def overons():
    return render_template("overons.html")

#admin page
@app.route("/admin", methods=["GET"])
@actief_required
def admin():
    if 'email' not in session:
        return redirect(url_for("login"))

    gebruiker = db.session.query(Gebruiker).filter_by(email=session["email"],deleted = False).first()
    if gebruiker and gebruiker.rol in ["bibliothecaris", "admin"]:
        return render_template("admin.html")

    flash("Je hebt geen toegang tot de adminpagina.", "error")
    return redirect(url_for("index"))

@app.route("/admin/gebruikers", methods=["GET"])
@actief_required
def gebruikers():
    # Haal alle gebruikers op uit de database
    gebruikers = db.session.query(Gebruiker).filter_by(deleted = False).all()
    if not gebruikers:
        flash("Geen gebruikers gevonden.")
        return redirect(url_for("admin"))
    return render_template("gebruikers.html", gebruikers=gebruikers)

@app.route('/bewerk_gebruiker/<int:gebruiker_id>', methods=['GET', 'POST'])
@actief_required
def bewerk_gebruiker(gebruiker_id):
    gebruiker = db.session.get(Gebruiker,gebruiker_id)
    rol_choices = [
        ('admin', 'Admin'),
        ('bibliothecaris', 'Bibliothecaris'),
        ('ontlener', 'Ontlener')
    ]
    if request.method == 'POST':
        gebruiker.naam = request.form['naam']
        gebruiker.achternaam = request.form['achternaam']
        gebruiker.email = request.form['email']
        gebruiker.rol = request.form.get('recht')
        gebruiker.actief = request.form.get('actief') == "on"
        
        db.session.commit()
        return redirect(url_for('gebruikers'))  # Terug naar de gebruikerslijst

    return render_template('bewerk_gebruiker.html', gebruiker=gebruiker, rol_choices=rol_choices, def_actief=gebruiker.actief)

@app.route('/verwijder_gebruiker/<int:gebruiker_id>', methods=['POST'])
@actief_required
def verwijder_gebruiker(gebruiker_id):
    # Fetch the user from the database
    gebruiker = db.session.get(Gebruiker,gebruiker_id)
    
    if not gebruiker:
        flash("Gebruiker niet gevonden.", "error")
        return redirect(url_for('gebruikers'))  # Redirect back to the users list

    try:
        # Delete the user
        gebruiker.deleted = True  
        db.session.commit()
        flash(f"Gebruiker '{gebruiker.naam} {gebruiker.achternaam}' succesvol verwijderd.", "success")
    except Exception as e:
        flash(f"Er is een fout opgetreden bij het verwijderen van de gebruiker: {str(e)}", "error")
    
    return redirect(url_for('gebruikers'))  # Redirect back to the users list

@app.route('/boek_terug_inleveren/<int:reservatie_id>', methods=['POST'])
@actief_required
def boek_terug_inleveren(reservatie_id):
    gebruiker = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
    if gebruiker.rol not in ['admin', 'bibliothecaris']:
        flash("Geen rechten om deze actie uit te voeren.", "error")
        return redirect(url_for('index'))

    reservatie = db.session.get(Reservatie,reservatie_id)
    if not reservatie or not reservatie.afgehaald:
        flash("Reservatie niet gevonden of niet afgehaald.", "error")
        return redirect(url_for('gebruiker_info', gebruiker_id=reservatie.gebruiker_id))

    boek = db.session.query(Boek).filter_by(ISBN=reservatie.boek_isbn).first()
    if boek:
        exemplaar = kies_uitgeleend(db.session, boek)
        if exemplaar:
            exemplaar.status = "beschikbaar"
        synchroniseer(db.session, boek)
        reservatie.afgehaald = False
        db.session.commit()
        if exemplaar:
            flash(
                f"Boek terug in leveren bevestigd (exemplaar {exemplaar.barcode}).",
                "success",
            )
        else:
            flash(
                "Reservatie afgesloten, maar er was geen uitgeleend exemplaar gevonden.",
                "warning",
            )
    else:
        flash("Boek niet gevonden.", "error")
    return redirect(url_for('gebruiker_info', gebruiker_id=reservatie.gebruiker_id))

@app.route('/bevestig_afhaling/<int:reservatie_id>', methods=['POST'])
@actief_required
def bevestig_afhaling(reservatie_id):
    gebruiker = db.session.query(Gebruiker).filter_by(email=session.get('email')).first()
    if gebruiker.rol not in ['admin', 'bibliothecaris']:
        flash("Geen rechten om deze actie uit te voeren.", "error")
        return redirect(url_for('index'))

    reservatie = db.session.get(Reservatie,reservatie_id)
    if not reservatie or reservatie.afgehaald:
        flash("Reservatie niet gevonden of al afgehaald.", "error")
        return redirect(url_for('gebruiker_info', gebruiker_id=reservatie.gebruiker_id))

    boek = db.session.query(Boek).filter_by(ISBN=reservatie.boek_isbn).first()
    if boek:
        exemplaar = kies_beschikbaar(db.session, boek)
        if exemplaar:
            exemplaar.status = "uitgeleend"
            synchroniseer(db.session, boek)
            reservatie.afgehaald = True
            db.session.commit()
            flash(
                f"Afhaling bevestigd (exemplaar {exemplaar.barcode}).",
                "success",
            )
        else:
            flash("Geen beschikbaar exemplaar gevonden.", "error")
    else:
        flash("Boek niet gevonden.", "error")
    return redirect(url_for('gebruiker_info', gebruiker_id=reservatie.gebruiker_id))

@app.route('/gebruiker/<int:gebruiker_id>', methods=['GET'])
@actief_required
def gebruiker_info(gebruiker_id):
    # Fetch the user from the database
    gebruiker = db.session.get(Gebruiker,gebruiker_id)
    if not gebruiker:
        flash("Gebruiker niet gevonden.", "error")
        return redirect(url_for('gebruikers'))  # Redirect back to the users list

    # Fetch the books reserved by the user
    reserveringen = db.session.query(Reservatie).filter_by(gebruiker_id=gebruiker_id).all()

    return render_template(
    'gebruiker_info.html',
    gebruiker=gebruiker,
    reserveringen=reserveringen,
    now=date.today()
)

@app.route('/verwijder_reservatie/<int:reservatie_id>', methods=['POST'])
@actief_required
def verwijder_reservatie(reservatie_id):
    if 'email' not in session:
        return redirect(url_for("login"))

    gebruiker = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if not gebruiker or gebruiker.rol not in ["bibliothecaris", "admin"]:
        flash("Je hebt geen toegang tot deze actie.", "error")
        return redirect(url_for("index"))

    # Fetch the reservation
    reservatie = db.session.get(Reservatie,reservatie_id)
    if not reservatie:
        flash("Reservatie niet gevonden.", "error")
        return redirect(url_for('gebruikers'))

    try:
        # Delete the reservation
        reservatie.deleted = True  # Mark as deleted instead of actually deleting
        db.session.commit()
        flash("Reservatie succesvol verwijderd.", "success")
    except Exception as e:
        flash(f"Er is een fout opgetreden bij het verwijderen van de reservatie: {str(e)}", "error")

    return redirect(url_for('gebruikers'))

@app.route('/admin/overdue', methods=['GET'])
@actief_required
def overdue_reservations():
    if 'email' not in session:
        return redirect(url_for("login"))

    gebruiker = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if not gebruiker or gebruiker.rol not in ["bibliothecaris", "admin"]:
        flash("Je hebt geen toegang tot deze pagina.", "error")
        return redirect(url_for("index"))

    # Fetch all overdue reservations
    today = datetime.today().date()
    query = request.args.get('q', '').strip()

    if query:
        # Filter overdue reservations by user name or email
        overdue_reservations = db.session.query(Reservatie).join(Gebruiker).filter(
            Reservatie.end_date < today,
            Reservatie.deleted.is_(False),
            or_(
                Gebruiker.naam.ilike(f"%{query}%"),
                Gebruiker.achternaam.ilike(f"%{query}%"),
                Gebruiker.email.ilike(f"%{query}%")
            )
        ).all()
    else:
        # Fetch all overdue reservations if no query is provided
        overdue_reservations = db.session.query(Reservatie).filter(
            Reservatie.end_date < today,
            Reservatie.deleted.is_(False)
        ).all()

    return render_template('overdue_reservations.html', overdue_reservations=overdue_reservations)

@app.route('/admin/cvs_import', methods=['GET', 'POST'])
@actief_required
def cvs_import():
    if 'email' not in session:
        return redirect(url_for("login"))

    gebruiker = db.session.query(Gebruiker).filter_by(email=session["email"]).first()
    if gebruiker and gebruiker.rol in ["bibliothecaris", "admin"]:
        if request.method == 'POST':
            file = request.files['file']
            if file and file.filename.endswith('.csv'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                pdf_data = pd.read_csv(file_path)
                pdf_data.to_sql('test', con=db.engine, if_exists='append', index=False)
                    

                flash("CSV-bestand succesvol geïmporteerd.", "success")
                return redirect(url_for("admin"))
            else:
                flash("Ongeldig bestandstype. Alleen CSV-bestanden zijn toegestaan.", "error")
        return render_template("cvs_import.html")
    else:
        flash("Je hebt geen toegang tot deze pagina.", "error")
        return redirect(url_for("index"))

@app.errorhandler(404)
def pagina_niet_gevonden(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def interne_serverfout(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500


@app.errorhandler(413)
def bestand_te_groot(error):
    flash("Het bestand is te groot (maximaal 5 MB).", "error")
    return redirect(request.referrer or url_for("index"))


@app.get("/healthz")
def healthz():
    """Eenvoudige healthcheck voor de server en de database."""
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db.session.rollback()
        return jsonify(status="degraded", database="error"), 503
    return jsonify(status="ok", database="ok"), 200


@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    Ensures that the database session is properly closed after each request.
    This prevents issues like stale connections or locked tables.
    """
    db.session.remove()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


