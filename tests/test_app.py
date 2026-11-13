from database import Gebruiker, Session, engine


def login(client, email="test@example.com", wachtwoord="test123"):
    return client.post(
        "/login",
        data={"login_email": email, "login_paswoord": wachtwoord},
        follow_redirects=False,
    )


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_niet_ingelogd_gaat_naar_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_en_boekenlijst(client):
    assert login(client).status_code == 302

    response = client.get("/boeken")
    assert response.status_code == 200


def test_fout_wachtwoord(client):
    response = login(client, wachtwoord="verkeerd")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_platte_tekst_wachtwoord_wordt_gehasht(client):
    with Session(engine) as session:
        if not session.query(Gebruiker).filter_by(email="legacy@example.com").first():
            session.add(
                Gebruiker(
                    naam="Legacy",
                    achternaam="Gebruiker",
                    email="legacy@example.com",
                    paswoord="legacy123",
                    rol="ontlener",
                    actief=True,
                )
            )
            session.commit()

    assert login(client, "legacy@example.com", "legacy123").status_code == 302

    with Session(engine) as session:
        gebruiker = session.query(Gebruiker).filter_by(email="legacy@example.com").one()
        assert gebruiker.paswoord.startswith("$2b$")


def test_registratie_hasht_wachtwoord(client):
    response = client.post(
        "/register",
        data={
            "name": "Nieuw",
            "achternaam": "Lid",
            "register_email": "nieuw@example.com",
            "register_paswoord": "nieuw123",
            "recht": "ontlener",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with Session(engine) as session:
        gebruiker = session.query(Gebruiker).filter_by(email="nieuw@example.com").one()
        assert gebruiker.paswoord.startswith("$2b$")


def test_onbekende_pagina_geeft_404(client):
    response = client.get("/deze-pagina-bestaat-niet")
    assert response.status_code == 404
    assert b"404" in response.data
