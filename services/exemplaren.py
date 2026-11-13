"""Beheer van fysieke exemplaren, barcodes en beschikbaarheid."""

from datetime import UTC, date, datetime

from barcode import Code128
from barcode.writer import SVGWriter

from database import Exemplaar

BARCODE_PREFIX = "BIB"


def actieve_exemplaren(session, boek):
    return (
        session.query(Exemplaar)
        .filter_by(boek_isbn=boek.ISBN, deleted=False)
        .order_by(Exemplaar.id)
        .all()
    )


def synchroniseer(session, boek):
    """Werk de tellers op het boek bij op basis van de echte exemplaren."""
    exemplaren = actieve_exemplaren(session, boek)
    boek.aantal = len(exemplaren)
    boek.beschikbaar_aantal = sum(1 for e in exemplaren if e.status == "beschikbaar")
    return boek


def maak_exemplaren(session, boek, aantal, status="beschikbaar"):
    """Maak nieuwe exemplaren met een unieke barcode."""
    gemaakte = []
    for _ in range(max(0, int(aantal))):
        exemplaar = Exemplaar(
            boek=boek,
            barcode="",
            status=status,
            locatie_id=boek.locatie_id,
            aankoopdatum=date.today(),
        )
        session.add(exemplaar)
        session.flush()
        exemplaar.barcode = f"{BARCODE_PREFIX}-{exemplaar.id:06d}"
        gemaakte.append(exemplaar)
    synchroniseer(session, boek)
    return gemaakte


def zorg_voor_exemplaren(session, boek):
    """Eenmalige backfill: maak exemplaren op basis van de oude tellers."""
    bestaand = actieve_exemplaren(session, boek)
    if bestaand:
        synchroniseer(session, boek)
        return bestaand

    totaal = max(0, int(boek.aantal or 0))
    beschikbaar = min(totaal, max(0, int(boek.beschikbaar_aantal or 0)))
    maak_exemplaren(session, boek, beschikbaar, status="beschikbaar")
    maak_exemplaren(session, boek, totaal - beschikbaar, status="uitgeleend")
    return actieve_exemplaren(session, boek)


def kies_beschikbaar(session, boek):
    return (
        session.query(Exemplaar)
        .filter_by(boek_isbn=boek.ISBN, status="beschikbaar", deleted=False)
        .order_by(Exemplaar.id)
        .first()
    )


def kies_uitgeleend(session, boek):
    return (
        session.query(Exemplaar)
        .filter_by(boek_isbn=boek.ISBN, status="uitgeleend", deleted=False)
        .order_by(Exemplaar.id)
        .first()
    )


def reconcileer_totaal(session, boek, gewenst):
    """Breng het aantal exemplaren naar het gewenste totaal."""
    gewenst = max(0, int(gewenst))
    actief = actieve_exemplaren(session, boek)

    if gewenst > len(actief):
        maak_exemplaren(session, boek, gewenst - len(actief))
    elif gewenst < len(actief):
        te_verwijderen = len(actief) - gewenst
        beschikbaar = [e for e in actief if e.status == "beschikbaar"]
        if len(beschikbaar) < te_verwijderen:
            raise ValueError(
                "Er zijn niet genoeg beschikbare exemplaren om te verwijderen."
            )
        for exemplaar in beschikbaar[:te_verwijderen]:
            exemplaar.deleted = True

    synchroniseer(session, boek)


def markeer_aanwezig(session, exemplaar):
    exemplaar.laatst_gezien = datetime.now(UTC)
    return exemplaar


def barcode_svg(code):
    """Genereer een Code 128-barcode als inline SVG."""
    barcode = Code128(code, writer=SVGWriter())
    return barcode.render(
        writer_options={
            "module_width": 0.33,
            "module_height": 12,
            "quiet_zone": 2,
            "font_size": 8,
            "text_distance": 3,
        }
    ).decode("utf-8")
