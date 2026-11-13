from flask_bcrypt import generate_password_hash

import app as app_module
from database import Boek, Gebruiker, Session, engine


def login(client, email="test@example.com", wachtwoord="test123"):
    return client.post(
        "/login",
        data={"login_email": email, "login_paswoord": wachtwoord},
        follow_redirects=False,
    )


def nep_metadata(isbn):
    return {
        "isbn": isbn,
        "titel": "Testboek",
        "auteurs": ["Auteur Test"],
        "beschrijving": "Beschrijving",
        "paginas": 123,
        "uitgever": "Uitgever",
        "jaar": "2024",
        "genres": ["Roman"],
        "cover_url": None,
        "bron": "test",
    }


def test_scanpagina_laadt(client):
    login(client)
    response = client.get("/adminworkspace/scan")
    assert response.status_code == 200
    assert "Boek scannen" in response.get_data(as_text=True)


def test_api_isbn_geeft_metadata(client, monkeypatch):
    login(client)
    monkeypatch.setattr(app_module, "zoek_metadata", nep_metadata)

    response = client.get("/api/isbn/9780262033848")
    assert response.status_code == 200

    data = response.get_json()
    assert data["bestaat"] is False
    assert data["titel"] == "Testboek"
    assert data["auteurs"] == ["Auteur Test"]


def test_api_isbn_weigert_ongeldige_code(client):
    login(client)

    response = client.get("/api/isbn/12345")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_scan_boek_opslaan(client):
    login(client)

    response = client.post(
        "/adminworkspace/scan",
        json={
            "isbn": "9780132350884",
            "titel": "Scanboek",
            "auteurs": "Auteur Een, Auteur Twee",
            "genres": "Roman, Thriller",
            "beschrijving": "Een gescand boek.",
            "aantal": 2,
            "locatie": "A - Volwassenen",
            "paginas": 321,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "nieuw"

    with Session(engine) as session:
        boek = session.query(Boek).filter_by(ISBN="9780132350884").one()
        assert boek.titel == "Scanboek"
        assert boek.aantal == 2
        assert boek.beschikbaar_aantal == 2
        assert boek.aantal_bladzijden == 321
        assert {auteur.naam for auteur in boek.auteurs} == {"Auteur Een", "Auteur Twee"}
        assert {genre.naam for genre in boek.genres} == {"Roman", "Thriller"}


def test_bestaand_isbn_voegt_exemplaren_toe(client):
    login(client)

    eerste = client.post(
        "/adminworkspace/scan",
        json={"isbn": "9789021000015", "titel": "Bestaand boek", "aantal": 1},
    )
    assert eerste.status_code == 200
    assert eerste.get_json()["status"] == "nieuw"

    tweede = client.post(
        "/adminworkspace/scan",
        json={"isbn": "9789021000015", "aantal": 3},
    )
    assert tweede.status_code == 200
    data = tweede.get_json()
    assert data["status"] == "bestaat"
    assert data["aantal"] == 4
    assert data["beschikbaar"] == 4

    api = client.get("/api/isbn/9789021000015")
    assert api.status_code == 200
    assert api.get_json()["bestaat"] is True


def test_scan_vereist_titel_bij_nieuw_boek(client):
    login(client)

    response = client.post(
        "/adminworkspace/scan",
        json={"isbn": "9789021000022", "titel": ""},
    )
    assert response.status_code == 400
    assert "Titel" in response.get_json()["error"]


def test_scan_geen_toegang_voor_ontlener(client):
    with Session(engine) as session:
        if not session.query(Gebruiker).filter_by(email="ontlener@example.com").first():
            session.add(
                Gebruiker(
                    naam="Ontlener",
                    achternaam="Test",
                    email="ontlener@example.com",
                    paswoord=generate_password_hash("ontlener123").decode("utf-8"),
                    rol="ontlener",
                    actief=True,
                )
            )
            session.commit()

    login(client, "ontlener@example.com", "ontlener123")

    assert client.get("/adminworkspace/scan").status_code == 302
    assert client.get("/api/isbn/9780262033848").status_code == 403
    assert (
        client.post(
            "/adminworkspace/scan",
            json={"isbn": "9780262033848", "titel": "Mag niet"},
        ).status_code
        == 403
    )
