import pytest

from services import isbn_lookup


def test_normaliseert_isbn13_met_streepjes():
    assert isbn_lookup.normaliseer_isbn("978-0-262-03384-8") == "9780262033848"


def test_normaliseert_isbn10_naar_isbn13():
    assert isbn_lookup.normaliseer_isbn("0-262-03384-4") == "9780262033848"


def test_weigert_ongeldig_controlecijfer():
    with pytest.raises(isbn_lookup.IsbnFout):
        isbn_lookup.normaliseer_isbn("9780262033849")


def test_weigert_te_korte_code():
    with pytest.raises(isbn_lookup.IsbnFout):
        isbn_lookup.normaliseer_isbn("12345")


def test_google_books_resultaat(monkeypatch):
    def nep_http(url):
        assert "googleapis" in url
        return {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Testboek",
                        "authors": ["Auteur Test"],
                        "description": "Een beschrijving.",
                        "pageCount": 123,
                        "publisher": "Uitgeverij",
                        "publishedDate": "2024-05-01",
                        "categories": ["Roman"],
                        "imageLinks": {"thumbnail": "https://books.google.com/cover.jpg"},
                    }
                }
            ]
        }

    monkeypatch.setattr(isbn_lookup, "_http_json", nep_http)

    resultaat = isbn_lookup.zoek_metadata("9780262033848", force=True)
    assert resultaat["titel"] == "Testboek"
    assert resultaat["auteurs"] == ["Auteur Test"]
    assert resultaat["paginas"] == 123
    assert resultaat["jaar"] == "2024"
    assert resultaat["bron"] == "google_books"


def test_open_library_fallback(monkeypatch):
    def nep_http(url):
        if "googleapis" in url:
            return {"items": []}
        return {
            "docs": [
                {
                    "title": "Open Library Boek",
                    "author_name": ["Auteur Twee"],
                    "first_publish_year": 2020,
                    "number_of_pages_median": 200,
                    "publisher": ["Uitgeverij Twee"],
                    "subject": ["Roman", "Fiction", "Large type books"],
                    "cover_i": 123456,
                }
            ]
        }

    monkeypatch.setattr(isbn_lookup, "_http_json", nep_http)

    resultaat = isbn_lookup.zoek_metadata("9780132350884", force=True)
    assert resultaat["titel"] == "Open Library Boek"
    assert resultaat["bron"] == "open_library"
    assert resultaat["cover_url"].endswith("123456-L.jpg")
    assert resultaat["genres"] == ["Roman"]


def test_lookup_fout_als_beide_bronnen_leeg_zijn(monkeypatch):
    monkeypatch.setattr(isbn_lookup, "_http_json", lambda url: {"items": [], "docs": []})

    with pytest.raises(isbn_lookup.LookupFout):
        isbn_lookup.zoek_metadata("9789021000015", force=True)


def test_cover_download_weigert_onbekende_host(tmp_path):
    resultaat = isbn_lookup.download_cover(
        "https://evil.example/cover.jpg",
        "9780262033848",
        tmp_path,
    )
    assert resultaat is None
