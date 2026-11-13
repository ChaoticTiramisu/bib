import io

from database import Boek, Session, engine


def login(client):
    return client.post(
        "/login",
        data={"login_email": "test@example.com", "login_paswoord": "test123"},
        follow_redirects=False,
    )


def test_formulier_slaat_aantal_op(client, tmp_path):
    login(client)
    client.application.config["UPLOAD_FOLDER"] = str(tmp_path)

    response = client.post(
        "/adminworkspace/tools/add",
        data={
            "ISBN": "9789021000039",
            "titel": "Formulierboek",
            "beschrijving": "Toegevoegd via het gewone formulier.",
            "aantal": "4",
            "locatie": "A - Volwassenen",
            "genres": ["Roman"],
            "auteurs": ["Auteur Formulier"],
            "file": (io.BytesIO(b"dummy-cover"), "cover.jpg"),
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with Session(engine) as session:
        boek = session.query(Boek).filter_by(ISBN="9789021000039").one()
        assert boek.aantal == 4
        assert boek.beschikbaar_aantal == 4
