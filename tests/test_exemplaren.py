from datetime import date, timedelta

from database import Boek, Exemplaar, Gebruiker, Reservatie, Session, engine
from services.exemplaren import reconcileer_totaal, zorg_voor_exemplaren


def login(client):
    return client.post(
        "/login",
        data={"login_email": "test@example.com", "login_paswoord": "test123"},
        follow_redirects=False,
    )


def scan_boek(client, isbn, titel, aantal=2):
    return client.post(
        "/adminworkspace/scan",
        json={"isbn": isbn, "titel": titel, "aantal": aantal},
    )


def test_scan_maakt_exemplaren_met_barcodes(client):
    login(client)
    assert scan_boek(client, "9789021000053", "Exemplaarboek", 2).status_code == 200

    with Session(engine) as session:
        boek = session.query(Boek).filter_by(ISBN="9789021000053").one()
        exemplaren = (
            session.query(Exemplaar)
            .filter_by(boek_isbn=boek.ISBN, deleted=False)
            .all()
        )
        assert len(exemplaren) == 2
        assert all(exemplaar.barcode.startswith("BIB-") for exemplaar in exemplaren)
        assert len({exemplaar.barcode for exemplaar in exemplaren}) == 2
        assert boek.aantal == 2
        assert boek.beschikbaar_aantal == 2


def test_labels_bevatten_barcodes(client):
    login(client)
    assert scan_boek(client, "9789021000060", "Labelboek", 2).status_code == 200

    response = client.get("/adminworkspace/boek/9789021000060/labels")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "<svg" in html
    assert "BIB-" in html


def test_inventaris_api_markeert_aanwezig(client):
    login(client)
    assert scan_boek(client, "9789021000077", "Inventarisboek", 1).status_code == 200

    with Session(engine) as session:
        exemplaar = session.query(Exemplaar).filter_by(boek_isbn="9789021000077").one()
        barcode = exemplaar.barcode

    response = client.get(f"/api/exemplaar/{barcode}")
    assert response.status_code == 200
    assert response.get_json()["titel"] == "Inventarisboek"

    response = client.post(f"/api/exemplaar/{barcode}/aanwezig")
    assert response.status_code == 200
    assert response.get_json()["laatst_gezien"] is not None

    with Session(engine) as session:
        exemplaar = session.query(Exemplaar).filter_by(barcode=barcode).one()
        assert exemplaar.laatst_gezien is not None


def test_afhalen_en_terugbrengen_wijzigt_exemplaarstatus(client):
    login(client)
    assert scan_boek(client, "9789021000084", "Uitleenboek", 1).status_code == 200

    with Session(engine) as session:
        boek = session.query(Boek).filter_by(ISBN="9789021000084").one()
        gebruiker = session.query(Gebruiker).filter_by(email="test@example.com").one()
        reservatie = Reservatie(
            boek_isbn=boek.ISBN,
            gebruiker_id=gebruiker.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            afgehaald=False,
        )
        session.add(reservatie)
        session.commit()
        reservatie_id = reservatie.id

    assert client.post(f"/bevestig_afhaling/{reservatie_id}").status_code == 302

    with Session(engine) as session:
        exemplaar = session.query(Exemplaar).filter_by(boek_isbn="9789021000084").one()
        boek = session.query(Boek).filter_by(ISBN="9789021000084").one()
        reservatie = session.get(Reservatie, reservatie_id)
        assert exemplaar.status == "uitgeleend"
        assert boek.beschikbaar_aantal == 0
        assert reservatie.afgehaald is True

    assert client.post(f"/boek_terug_inleveren/{reservatie_id}").status_code == 302

    with Session(engine) as session:
        exemplaar = session.query(Exemplaar).filter_by(boek_isbn="9789021000084").one()
        boek = session.query(Boek).filter_by(ISBN="9789021000084").one()
        assert exemplaar.status == "beschikbaar"
        assert boek.beschikbaar_aantal == 1


def test_backfill_maakt_exemplaren_op_basis_van_tellers():
    with Session(engine) as session:
        boek = Boek(
            ISBN="9789021000091",
            titel="Backfillboek",
            beschrijving="Backfill",
            aantal=3,
            beschikbaar_aantal=1,
            status=False,
        )
        session.add(boek)
        session.commit()

        zorg_voor_exemplaren(session, boek)
        session.commit()

        exemplaren = (
            session.query(Exemplaar)
            .filter_by(boek_isbn="9789021000091", deleted=False)
            .all()
        )
        assert len(exemplaren) == 3
        assert sum(1 for e in exemplaren if e.status == "beschikbaar") == 1
        assert sum(1 for e in exemplaren if e.status == "uitgeleend") == 2


def test_reconcileer_totaal_past_het_aantal_aan():
    with Session(engine) as session:
        boek = Boek(
            ISBN="9789021000107",
            titel="Reconcileboek",
            beschrijving="Reconcile",
            aantal=2,
            beschikbaar_aantal=2,
            status=False,
        )
        session.add(boek)
        session.commit()
        zorg_voor_exemplaren(session, boek)
        session.commit()

        reconcileer_totaal(session, boek, 4)
        session.commit()
        assert boek.aantal == 4

        reconcileer_totaal(session, boek, 1)
        session.commit()
        assert boek.aantal == 1
