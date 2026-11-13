"""Haal boekcovers op en zet ze in static/upload/<ISBN>.jpg.

Eerst wordt een echte cover gezocht via Open Library (titel + auteur). Lukt dat
niet, dan wordt een nette fallback-cover met titel en auteur gemaakt. Zo heeft
elk boek altijd een afbeelding.

Gebruik:
    ./env/bin/python fetch_covers.py
"""

import json
import os
import shutil
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from database import Boek, Session, engine

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(PROJECT_DIR, "static", "upload")
MAGICK = shutil.which("magick") or shutil.which("convert") or "convert"
USER_AGENT = "Schoolbib-coverfetch/1.0 (educatief schoolproject)"

SEARCH_URL = "https://openlibrary.org/search.json"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg?default=false"

# Voor boeken waarvan Open Library vooral de Engelstalige uitgave kent.
ALTERNATIEVE_TITELS = {
    "Harry Potter en de steen der wijzen": (
        "Harry Potter and the Philosopher's Stone",
        "J.K. Rowling",
    ),
    "De Da Vinci Code": ("The Da Vinci Code", "Dan Brown"),
    "Het": ("It", "Stephen King"),
    "Het oneindige verhaal": ("The Neverending Story", "Michael Ende"),
}

KLEUREN = [
    ("#1e3a8a", "#0f172a"),
    ("#7c2d12", "#1c1917"),
    ("#065f46", "#052e16"),
    ("#6b21a8", "#1e1b4b"),
    ("#9f1239", "#4c0519"),
    ("#0e7490", "#083344"),
]


def normaliseer(tekst):
    """Kleine letters, zonder accenten en leestekens, voor titelvergelijking."""
    tekst = unicodedata.normalize("NFKD", tekst)
    tekst = "".join(c for c in tekst if not unicodedata.combining(c))
    tekst = "".join(c if c.isalnum() else " " for c in tekst.lower())
    return " ".join(tekst.split())


def zoek_cover(titel, auteur):
    """Zoek een Open Library-cover-id dat bij titel en auteur past."""
    params = {
        "title": titel,
        "limit": 5,
        "fields": "title,author_name,cover_i",
    }
    if auteur:
        params["author"] = auteur
    url = SEARCH_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        resultaat = json.load(response)

    gezocht_titel = normaliseer(titel)
    for doc in resultaat.get("docs", []):
        cover_id = doc.get("cover_i")
        doc_titel = normaliseer(doc.get("title", ""))
        if not cover_id or not doc_titel:
            continue
        if gezocht_titel in doc_titel or doc_titel in gezocht_titel:
            return cover_id
    return None


def download_cover(cover_id, doel):
    """Download een cover en schaal hem terug naar maximaal 600x900."""
    url = COVER_URL.format(cover_id=cover_id)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if len(data) < 5000:
        raise ValueError("afbeelding is te klein")

    tijdelijk = doel + ".tmp"
    with open(tijdelijk, "wb") as bestand:
        bestand.write(data)
    try:
        subprocess.run(
            [MAGICK, tijdelijk, "-resize", "600x900>", "-strip", "-quality", "86", doel],
            check=True,
            capture_output=True,
        )
    finally:
        if os.path.exists(tijdelijk):
            os.remove(tijdelijk)


def maak_fallback(titel, auteur, doel):
    """Teken een eenvoudige cover met een kleurverloop, titel en auteur."""
    kleur_boven, kleur_onder = KLEUREN[sum(map(ord, titel)) % len(KLEUREN)]
    opdracht = [
        MAGICK,
        "-size", "600x900", f"gradient:{kleur_boven}-{kleur_onder}",
        "(", "-background", "none", "-fill", "#f8fafc", "-pointsize", "46",
         "-gravity", "center", "-size", "500x", f"caption:{titel}", ")",
        "-gravity", "center", "-geometry", "+0-120", "-composite",
        "(", "-background", "none", "-fill", "#cbd5e1", "-pointsize", "30",
         "-gravity", "center", "-size", "500x", f"caption:{auteur}", ")",
        "-gravity", "center", "-geometry", "+0+140", "-composite",
        "-strip", "-quality", "88", doel,
    ]
    subprocess.run(opdracht, check=True, capture_output=True)


def maak_default_cover(doel):
    """Neutrale cover voor boeken zonder afbeelding."""
    subprocess.run(
        [
            MAGICK,
            "-size", "600x900", "gradient:#334155-#0f172a",
            "-gravity", "center", "-fill", "#94a3b8", "-pointsize", "40",
            "-annotate", "+0-40", "Schoolbib",
            "-fill", "#64748b", "-pointsize", "24",
            "-annotate", "+0+40", "Geen cover beschikbaar",
            "-strip", "-quality", "88", doel,
        ],
        check=True,
        capture_output=True,
    )


def main():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    maak_default_cover(os.path.join(UPLOAD_DIR, "default_cover.png"))

    with Session(engine) as session:
        boeken = (
            session.query(Boek)
            .filter_by(deleted=False)
            .order_by(Boek.titel)
            .all()
        )
        if not boeken:
            print("Geen boeken gevonden. Voer eerst seed.py uit.")
            return

        gevonden = 0
        for index, boek in enumerate(boeken, start=1):
            auteur = boek.auteurs[0].naam if boek.auteurs else ""
            doel = os.path.join(UPLOAD_DIR, f"{boek.ISBN}.jpg")
            cover_id = None
            try:
                cover_id = zoek_cover(boek.titel, auteur)
                if not cover_id and boek.titel in ALTERNATIEVE_TITELS:
                    alternatief, alternatieve_auteur = ALTERNATIEVE_TITELS[boek.titel]
                    cover_id = zoek_cover(alternatief, alternatieve_auteur)
            except (urllib.error.URLError, TimeoutError, ValueError) as fout:
                print(f"[{index}/{len(boeken)}] zoeken mislukt voor '{boek.titel}': {fout}")

            if cover_id:
                try:
                    download_cover(cover_id, doel)
                    gevonden += 1
                    print(f"[{index}/{len(boeken)}] cover  {boek.titel} (Open Library #{cover_id})")
                    time.sleep(0.3)
                    continue
                except (urllib.error.URLError, TimeoutError, ValueError, subprocess.CalledProcessError) as fout:
                    print(f"[{index}/{len(boeken)}] download mislukt voor '{boek.titel}': {fout}")

            maak_fallback(boek.titel, auteur, doel)
            print(f"[{index}/{len(boeken)}] fallback {boek.titel}")

    print(f"\nKlaar: {gevonden} echte covers, {len(boeken) - gevonden} fallbacks.")
    print(f"Opgeslagen in: {UPLOAD_DIR}")


if __name__ == "__main__":
    main()
