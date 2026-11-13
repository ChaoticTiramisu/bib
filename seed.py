"""Vul de database met testdata.

Herhaalbaar: bestaande rijen worden niet gedupliceerd. Boeken worden op ISBN
herkend, gebruikers op e-mailadres en auteurs/genres/thema's op naam.

Gebruik:
    ./env/bin/python seed.py
"""

from datetime import date, timedelta

from flask_bcrypt import generate_password_hash

from database import (
    Auteur,
    Boek,
    Exemplaar,
    Gebruiker,
    Genre,
    Locatie,
    Reservatie,
    Session,
    Thema,
    engine,
)
from services.exemplaren import synchroniseer, zorg_voor_exemplaren


def get_or_create(session, model, defaults=None, **filters):
    """Zoek een rij of maak hem aan. Geeft (object, aangemaakt) terug."""
    obj = session.query(model).filter_by(**filters).first()
    if obj is not None:
        return obj, False
    obj = model(**filters, **(defaults or {}))
    session.add(obj)
    session.flush()
    return obj, True


def isbn13(prefix12):
    """Maak een geldig ISBN-13 van de eerste 12 cijfers."""
    if len(prefix12) != 12 or not prefix12.isdigit():
        raise ValueError("prefix12 moet uit precies 12 cijfers bestaan")
    som = sum((3 if i % 2 else 1) * int(cijfer) for i, cijfer in enumerate(prefix12))
    return prefix12 + str((10 - som % 10) % 10)


LOCATIES = [
    "A - Volwassenen",
    "B - Jeugd",
    "C - Naslagwerken",
    "D - Strips",
]

GEBRUIKERS = [
    ("Sofie", "Declerck", "bib@example.com", "bib123", "bibliothecaris", True),
    ("Jan", "Peeters", "jan@example.com", "jan123", "ontlener", True),
    ("Emma", "De Smet", "emma@example.com", "emma123", "ontlener", True),
    ("Noah", "Janssens", "noah@example.com", "noah123", "ontlener", True),
    ("Lotte", "Vermeulen", "lotte@example.com", "lotte123", "ontlener", True),
    ("Bram", "Claes", "bram@example.com", "bram123", "ontlener", False),
]

# (basis-ISBN, titel, auteur(s), genres, thema's, locatie, aantal, pagina's,
#  afwezig, boek van de maand, beschrijving)
BOEKEN = [
    (
        "978902100001",
        "De engelenmaker",
        ["Stefan Brijs"],
        ["Roman", "Historische roman"],
        ["Identiteit", "Geschiedenis"],
        "A - Volwassenen",
        3,
        456,
        False,
        True,
        "Een arts keert terug naar zijn geboortedorp en wordt geconfronteerd met een duister familieverleden.",
    ),
    (
        "978902100002",
        "De helaasheid der dingen",
        ["Dimitri Verhulst"],
        ["Roman", "Humor"],
        ["Samenleving", "Gezin"],
        "A - Volwassenen",
        2,
        288,
        False,
        False,
        "Een jonge man blikt terug op zijn opgroeien in een marginale Vlaamse familie.",
    ),
    (
        "978902100003",
        "Kom hier dat ik u kus",
        ["Griet Op de Beeck"],
        ["Roman"],
        ["Liefde", "Identiteit"],
        "A - Volwassenen",
        3,
        384,
        False,
        False,
        "Mona zoekt haar hele leven naar de liefde en erkenning van haar vader.",
    ),
    (
        "978902100004",
        "Het smelt",
        ["Lize Spit"],
        ["Roman", "Thriller"],
        ["Vriendschap", "Verlies"],
        "A - Volwassenen",
        2,
        480,
        False,
        True,
        "Eva keert terug naar haar dorp en rekent af met een gebeurtenis uit haar jeugd.",
    ),
    (
        "978902100005",
        "Wildevrouw",
        ["Jeroen Olyslaegers"],
        ["Historische roman"],
        ["Geschiedenis", "Vrijheid"],
        "A - Volwassenen",
        2,
        512,
        False,
        False,
        "Antwerpen in de zestiende eeuw: een drukker vertelt over liefde, geloof en verraad.",
    ),
    (
        "978902100006",
        "Zomerhuis",
        ["Suzanne Vermeer"],
        ["Thriller"],
        ["Geheim", "Spanning"],
        "A - Volwassenen",
        4,
        320,
        False,
        False,
        "Een vakantie in een afgelegen zomerhuis loopt uit op een nachtmerrie.",
    ),
    (
        "978902100007",
        "De Da Vinci Code",
        ["Dan Brown"],
        ["Thriller"],
        ["Geheim", "Geschiedenis"],
        "A - Volwassenen",
        3,
        480,
        False,
        False,
        "Een symbologe en een historicus ontrafelen een eeuwenoud geheim.",
    ),
    (
        "978902100008",
        "Project Hail Mary",
        ["Andy Weir"],
        ["Sciencefiction"],
        ["Technologie", "Avontuur"],
        "A - Volwassenen",
        2,
        512,
        False,
        False,
        "Een astronaut wordt alleen wakker op een ruimteschip en moet de aarde redden.",
    ),
    (
        "978902100009",
        "Dune",
        ["Frank Herbert"],
        ["Sciencefiction", "Fantasy"],
        ["Avontuur", "Macht"],
        "A - Volwassenen",
        2,
        688,
        False,
        False,
        "Op de woestijnplaneet Arrakis strijdt een jonge erfgenaam om macht en overleving.",
    ),
    (
        "978902100010",
        "Harry Potter en de steen der wijzen",
        ["J.K. Rowling"],
        ["Fantasy", "Jeugdboek"],
        ["Magie", "Vriendschap"],
        "B - Jeugd",
        5,
        336,
        False,
        False,
        "Harry Potter ontdekt op zijn elfde dat hij een tovenaar is en begint op Zweinstein.",
    ),
    (
        "978902100011",
        "Het",
        ["Stephen King"],
        ["Thriller"],
        ["Vriendschap", "Angst"],
        "A - Volwassenen",
        1,
        1138,
        True,
        False,
        "Zeven vrienden nemen het op tegen een kwaadaardige kracht in hun stad.",
    ),
    (
        "978902100012",
        "Sapiens",
        ["Yuval Noah Harari"],
        ["Non-fictie"],
        ["Geschiedenis", "Samenleving"],
        "C - Naslagwerken",
        3,
        464,
        False,
        False,
        "Een beknopte geschiedenis van de mensheid, van jager-verzamelaar tot nu.",
    ),
    (
        "978902100013",
        "De meeste mensen deugen",
        ["Rutger Bregman"],
        ["Non-fictie"],
        ["Samenleving", "Hoop"],
        "C - Naslagwerken",
        2,
        528,
        False,
        False,
        "Een nieuwe geschiedenis van de mens, met vertrouwen in plaats van wantrouwen.",
    ),
    (
        "978902100014",
        "De avond is ongemak",
        ["Marieke Lucas Rijneveld"],
        ["Roman"],
        ["Verlies", "Identiteit"],
        "A - Volwassenen",
        2,
        288,
        False,
        False,
        "Een boerenfamilie probeert om te gaan met de dood van een kind.",
    ),
    (
        "978902100015",
        "Het is de liefde die we niet begrijpen",
        ["Bart Moeyaert"],
        ["Jeugdboek", "Roman"],
        ["Liefde", "Vriendschap"],
        "B - Jeugd",
        3,
        160,
        False,
        False,
        "Drie verhalen over verlangen, afscheid en volwassen worden.",
    ),
    (
        "978902100016",
        "Oeroeg",
        ["Hella S. Haasse"],
        ["Roman", "Historische roman"],
        ["Geschiedenis", "Vriendschap"],
        "A - Volwassenen",
        2,
        128,
        False,
        False,
        "Twee vrienden groeien op in Nederlands-Indië en raken van elkaar verwijderd.",
    ),
    (
        "978902100017",
        "Artemis Fowl",
        ["Eoin Colfer"],
        ["Jeugdboek", "Fantasy"],
        ["Avontuur", "Technologie"],
        "B - Jeugd",
        3,
        288,
        False,
        False,
        "Een briljante jonge crimineel ontdekt een verborgen wereld van elfen.",
    ),
    (
        "978902100018",
        "Het oneindige verhaal",
        ["Michael Ende"],
        ["Fantasy", "Jeugdboek"],
        ["Avontuur", "Verbeelding"],
        "B - Jeugd",
        2,
        400,
        False,
        False,
        "Bastiaan duikt in een boek en belandt in een wereld die zijn verbeelding nodig heeft.",
    ),
]

# (ISBN-basis, e-mail gebruiker, start over x dagen, eind over y dagen, afgehaald)
RESERVATIES = [
    ("978902100001", "jan@example.com", -10, 11, True),
    ("978902100004", "lotte@example.com", -30, -9, True),  # te laat
    ("978902100008", "emma@example.com", 3, 17, False),
    ("978902100010", "noah@example.com", 1, 14, False),
    ("978902100012", "bram@example.com", -5, 5, True),
]


def main():
    vandaag = date.today()
    with Session(engine) as session:
        locaties = {}
        for naam in LOCATIES:
            locatie, _ = get_or_create(session, Locatie, naam=naam)
            locaties[naam] = locatie

        gebruikers = {}
        for naam, achternaam, email, paswoord, rol, actief in GEBRUIKERS:
            gebruiker, _ = get_or_create(
                session,
                Gebruiker,
                email=email,
                defaults={
                    "naam": naam,
                    "achternaam": achternaam,
                    "paswoord": generate_password_hash(paswoord).decode("utf-8"),
                    "rol": rol,
                    "actief": actief,
                },
            )
            gebruikers[email] = gebruiker

        boeken = {}
        for (
            basis,
            titel,
            auteurs,
            genres,
            themas,
            locatie_naam,
            aantal,
            pagina,
            afwezig,
            bvdm,
            beschrijving,
        ) in BOEKEN:
            isbn = isbn13(basis)
            boek, _ = get_or_create(
                session,
                Boek,
                ISBN=isbn,
                defaults={
                    "titel": titel,
                    "beschrijving": beschrijving,
                    "status": afwezig,
                    "bvdm": bvdm,
                    "aantal": aantal,
                    "beschikbaar_aantal": aantal,
                    "aantal_bladzijden": pagina,
                    "locatie": locaties[locatie_naam],
                },
            )
            # Bestaande boeken bijwerken zonder relaties te dupliceren.
            boek.titel = titel
            boek.beschrijving = beschrijving
            boek.status = afwezig
            boek.bvdm = bvdm
            boek.aantal = aantal
            boek.aantal_bladzijden = pagina
            boek.locatie = locaties[locatie_naam]

            for naam in auteurs:
                auteur, _ = get_or_create(session, Auteur, naam=naam)
                if auteur not in boek.auteurs:
                    boek.auteurs.append(auteur)
            for naam in genres:
                genre, _ = get_or_create(session, Genre, naam=naam)
                if genre not in boek.genres:
                    boek.genres.append(genre)
            for naam in themas:
                thema, _ = get_or_create(session, Thema, naam=naam)
                if thema not in boek.themas:
                    boek.themas.append(thema)

            boeken[basis] = boek

        for basis, email, start_offset, eind_offset, afgehaald in RESERVATIES:
            boek = boeken[basis]
            gebruiker = gebruikers[email]
            start = vandaag + timedelta(days=start_offset)
            eind = vandaag + timedelta(days=eind_offset)
            bestaand = (
                session.query(Reservatie)
                .filter_by(
                    boek_isbn=boek.ISBN,
                    gebruiker_id=gebruiker.id,
                    start_date=start,
                )
                .first()
            )
            if bestaand is None:
                session.add(
                    Reservatie(
                        boek_isbn=boek.ISBN,
                        gebruiker_id=gebruiker.id,
                        start_date=start,
                        end_date=eind,
                        afgehaald=afgehaald,
                    )
                )

        session.flush()

        # Beschikbaarheid afleiden uit de afgehaalde (niet-teruggebrachte) reservaties.
        for boek in boeken.values():
            uitgeleend = (
                session.query(Reservatie)
                .filter_by(boek_isbn=boek.ISBN, afgehaald=True, deleted=False)
                .count()
            )
            boek.beschikbaar_aantal = max(0, boek.aantal - uitgeleend)
            boek.gereserveerd = (
                session.query(Reservatie)
                .filter_by(boek_isbn=boek.ISBN, deleted=False)
                .count()
                > 0
            )

            bestaande_exemplaren = (
                session.query(Exemplaar)
                .filter_by(boek_isbn=boek.ISBN, deleted=False)
                .count()
            )
            if bestaande_exemplaren:
                synchroniseer(session, boek)
            else:
                zorg_voor_exemplaren(session, boek)

        session.commit()

        print(f"Locaties:   {len(LOCATIES)}")
        print(f"Gebruikers: {len(GEBRUIKERS)} extra (admin bestaat al)")
        print(f"Boeken:     {len(BOEKEN)}")
        print(f"Auteurs:    {session.query(Auteur).count()}")
        print(f"Genres:     {session.query(Genre).count()}")
        print(f"Thema's:    {session.query(Thema).count()}")
        print(f"Reservaties:{session.query(Reservatie).count()}")
        print("\nTestaccounts:")
        print("  bibliothecaris: bib@example.com / bib123")
        print("  ontlener:       jan@example.com / jan123")


if __name__ == "__main__":
    main()
