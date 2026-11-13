"""Maak fysieke exemplaren aan voor boeken die er nog geen hebben.

Gebruik:
    ./env/bin/python scripts/backfill_exemplaren.py

Het script is herhaalbaar: boeken die al exemplaren hebben worden overgeslagen.
"""

import sys
from pathlib import Path

# Zorg dat de projectmap in sys.path staat wanneer dit script vanuit scripts/ draait.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import Boek, Exemplaar, Session, engine  # noqa: E402
from services.exemplaren import zorg_voor_exemplaren  # noqa: E402


def main():
    with Session(engine) as session:
        boeken = session.query(Boek).filter_by(deleted=False).all()
        totaal = 0

        for boek in boeken:
            voor = (
                session.query(Exemplaar)
                .filter_by(boek_isbn=boek.ISBN, deleted=False)
                .count()
            )
            zorg_voor_exemplaren(session, boek)
            na = (
                session.query(Exemplaar)
                .filter_by(boek_isbn=boek.ISBN, deleted=False)
                .count()
            )
            totaal += na - voor

        session.commit()
        print(f"Backfill klaar: {totaal} exemplaren aangemaakt voor {len(boeken)} boeken.")


if __name__ == "__main__":
    main()
