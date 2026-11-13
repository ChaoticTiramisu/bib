"""ISBN-normalisatie en het ophalen van boekmetadata.

Eerst wordt Google Books geprobeerd; lukt dat niet, dan Open Library. Resultaten
worden 24 uur in het geheugen gecachet zodat herhaald scannen geen extra
API-aanroepen kost.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import config

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
USER_AGENT = "Schoolbib-scan/1.0 (educatief schoolproject)"
CACHE_SECONDEN = 24 * 60 * 60
MAX_COVER_BYTES = 5 * 1024 * 1024

_CACHE: dict[str, tuple[float, dict]] = {}

_COVER_HOSTS = (
    "books.google.com",
    "books.googleusercontent.com",
    "googleusercontent.com",
    "openlibrary.org",
    "covers.openlibrary.org",
)

# Onderwerpen die Open Library vaak meegeeft maar als genre niets toevoegen.
_GENRE_BLOCKLIST = {
    "large type books",
    "american literature",
    "english literature",
    "fiction",
    "literature",
    "juvenile fiction",
    "juvenile literature",
    "readers",
}


class IsbnFout(ValueError):
    """De ingevoerde code is geen geldig ISBN."""


class LookupFout(RuntimeError):
    """Er kon geen metadata gevonden worden."""


def _isbn13_controlecijfer(base12: str) -> str:
    som = sum((3 if i % 2 else 1) * int(cijfer) for i, cijfer in enumerate(base12))
    return str((10 - som % 10) % 10)


def is_geldig_isbn13(code: str) -> bool:
    return (
        len(code) == 13
        and code.isdigit()
        and code.startswith(("978", "979"))
        and code[-1] == _isbn13_controlecijfer(code[:12])
    )


def is_geldig_isbn10(code: str) -> bool:
    if len(code) != 10 or not re.fullmatch(r"\d{9}[\dX]", code):
        return False
    som = sum((10 - i) * (10 if cijfer == "X" else int(cijfer)) for i, cijfer in enumerate(code))
    return som % 11 == 0


def normaliseer_isbn(code: str) -> str:
    """Maak van een gescande code een geldig ISBN-13.

    Ondersteunt ISBN-10 en ISBN-13, met of zonder streepjes. Bij een ongeldige
    code wordt `IsbnFout` opgegooid.
    """
    schoon = re.sub(r"[^0-9Xx]", "", code or "").upper()
    if not schoon:
        raise IsbnFout("Geen ISBN ingevoerd.")

    if len(schoon) == 10:
        if not is_geldig_isbn10(schoon):
            raise IsbnFout("Ongeldig ISBN-10 (controlecijfer klopt niet).")
        basis = "978" + schoon[:9]
        return basis + _isbn13_controlecijfer(basis)

    if len(schoon) == 13:
        if not is_geldig_isbn13(schoon):
            raise IsbnFout("Ongeldig ISBN-13 (controlecijfer klopt niet).")
        return schoon

    raise IsbnFout("Een ISBN heeft 10 of 13 cijfers.")


def _http_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=config.ISBN_LOOKUP_TIMEOUT) as response:
        return json.load(response)


def _google_books(isbn: str) -> dict | None:
    params = {"q": f"isbn:{isbn}"}
    if config.GOOGLE_BOOKS_API_KEY:
        params["key"] = config.GOOGLE_BOOKS_API_KEY
    data = _http_json(GOOGLE_BOOKS_URL + "?" + urllib.parse.urlencode(params))

    items = data.get("items") or []
    if not items:
        return None

    info = items[0].get("volumeInfo") or {}
    titel = (info.get("title") or "").strip()
    if not titel:
        return None
    ondertitel = (info.get("subtitle") or "").strip()
    if ondertitel:
        titel = f"{titel}: {ondertitel}"

    links = info.get("imageLinks") or {}
    cover = links.get("thumbnail") or links.get("smallThumbnail")
    if cover:
        cover = cover.replace("http://", "https://").replace("&edge=curl", "")
        cover = re.sub(r"zoom=\d", "zoom=2", cover)

    return {
        "isbn": isbn,
        "titel": titel,
        "auteurs": [a for a in (info.get("authors") or []) if a],
        "beschrijving": (info.get("description") or "").strip(),
        "paginas": info.get("pageCount"),
        "uitgever": (info.get("publisher") or "").strip(),
        "jaar": (info.get("publishedDate") or "")[:4],
        "genres": [g for g in (info.get("categories") or []) if g][:5],
        "cover_url": cover,
        "bron": "google_books",
    }


def _open_library(isbn: str) -> dict | None:
    params = {
        "isbn": isbn,
        "limit": 1,
        "fields": (
            "title,subtitle,author_name,first_publish_year,"
            "number_of_pages_median,publisher,subject,cover_i"
        ),
    }
    data = _http_json(OPEN_LIBRARY_URL + "?" + urllib.parse.urlencode(params))
    docs = data.get("docs") or []
    if not docs:
        return None

    doc = docs[0]
    titel = (doc.get("title") or "").strip()
    if not titel:
        return None
    ondertitel = (doc.get("subtitle") or "").strip()
    if ondertitel:
        titel = f"{titel}: {ondertitel}"

    genres = []
    for onderwerp in doc.get("subject") or []:
        onderwerp = str(onderwerp).strip()
        if (
            onderwerp
            and len(onderwerp) <= 40
            and "_" not in onderwerp
            and not onderwerp.lower().endswith("project")
            and onderwerp.lower() not in _GENRE_BLOCKLIST
            and onderwerp not in genres
        ):
            genres.append(onderwerp)
        if len(genres) == 5:
            break

    cover_id = doc.get("cover_i")
    uitgevers = doc.get("publisher") or []
    return {
        "isbn": isbn,
        "titel": titel,
        "auteurs": [a for a in (doc.get("author_name") or []) if a],
        "beschrijving": "",
        "paginas": doc.get("number_of_pages_median"),
        "uitgever": uitgevers[0] if uitgevers else "",
        "jaar": str(doc.get("first_publish_year") or ""),
        "genres": genres,
        "cover_url": (
            f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
        ),
        "bron": "open_library",
    }


def zoek_metadata(isbn: str, *, force: bool = False) -> dict:
    """Zoek metadata voor een genormaliseerd ISBN-13."""
    nu = time.time()
    if not force and isbn in _CACHE:
        tijdstip, resultaat = _CACHE[isbn]
        if nu - tijdstip < CACHE_SECONDEN:
            return resultaat

    resultaat = None
    fouten = []

    try:
        resultaat = _google_books(isbn)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as fout:
        fouten.append(f"Google Books: {fout}")

    if not resultaat:
        try:
            resultaat = _open_library(isbn)
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as fout:
            fouten.append(f"Open Library: {fout}")

    if not resultaat:
        detail = "; ".join(fouten) if fouten else "geen resultaat"
        raise LookupFout(f"Geen metadata gevonden voor ISBN {isbn} ({detail}).")

    # Google Books heeft soms geen cover; probeer die dan bij Open Library.
    if not resultaat.get("cover_url"):
        try:
            open_library = _open_library(isbn)
            if open_library and open_library.get("cover_url"):
                resultaat["cover_url"] = open_library["cover_url"]
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            pass

    _CACHE[isbn] = (nu, resultaat)
    return resultaat


def download_cover(url: str | None, isbn: str, upload_dir) -> str | None:
    """Download een cover naar de uploadmap en geef het webpad terug."""
    if not url:
        return None

    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(
        host == toegestaan or host.endswith("." + toegestaan) for toegestaan in _COVER_HOSTS
    ):
        return None

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=config.ISBN_LOOKUP_TIMEOUT) as response:
            data = response.read(MAX_COVER_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None

    if len(data) > MAX_COVER_BYTES:
        return None
    if data.startswith(b"\xff\xd8\xff"):
        extensie = ".jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        extensie = ".png"
    else:
        return None

    doel = upload_dir / f"{isbn}{extensie}"
    doel.write_bytes(data)
    return f"/static/upload/{isbn}{extensie}"
