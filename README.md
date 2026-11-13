School bib project om samen te werken.

Project klonen en dan setup.py runnen om alle dependecies te installeren. Creëert ook virtuele omgeving om geen conflicten te maken met al geïnstalleerde pakketen

## Draaien

```bash
source env/bin/activate
python app.py
```

Zonder de omgeving te activeren (handig als de terminal of VS Code de
verkeerde interpreter pakt):

```bash
./run.sh
```

Standaard wordt een lokale SQLite-database gebruikt (`instance/bib.db`).

## Configuratie

Kopieer `.env.example` naar `.env` en pas de waarden aan. Het `.env`-bestand
wordt niet in git opgenomen. Belangrijkste variabelen:

| Variabele | Betekenis |
|---|---|
| `SECRET_KEY` | Geheime sleutel voor sessies en cookies |
| `DATABASE_URL` | Database-URL; standaard SQLite |
| `FLASK_DEBUG` | `1` = debug/reloader aan, `0` = uit |
| `HOST` / `PORT` | Adres en poort van de server |

Voor PostgreSQL:

```bash
DATABASE_URL="postgresql+psycopg2://gebruiker:wachtwoord@localhost/bibdb"
```

Wachtwoorden worden met bcrypt gehasht. Bestaande platte-tekstwachtwoorden
worden bij de eerste geslaagde login automatisch geüpgraded.

Gebruik Python 3.12 of 3.13 voor de virtuele omgeving; dat is de combinatie
waarmee de app getest is.

## VS Code

`.vscode/settings.json` zet `env/bin/python` als standaardinterpreter. Toont de
statusbalk toch een andere versie, kies dan eenmalig
**Python: Select Interpreter → `./env/bin/python`**.

- **F5** start `app.py` met de venv (`.vscode/launch.json`).
- **Ctrl+Shift+B** voert de taak "Run Flask app (venv)" uit.
- Nieuwe terminals activeren de venv automatisch.

Werkt de terminal-activatie toch niet, gebruik dan `./run.sh`: dat start de app
rechtstreeks met `env/bin/python`, zonder `source activate`.

## Testdata

Vul de database met voorbeeldboeken, auteurs, genres, thema's, locaties,
gebruikers en reservaties:

```bash
./env/bin/python seed.py
```

Het script is herhaalbaar: bestaande rijen worden bijgewerkt, niet gedupliceerd.

| Rol | E-mail | Wachtwoord |
|---|---|---|
| admin | admin@example.com | admin123 |
| bibliothecaris | bib@example.com | bib123 |
| ontlener | jan@example.com | jan123 |
| ontlener | emma@example.com | emma123 |

`bram@example.com` is een geblokkeerde gebruiker om dat scenario te testen.

### Covers

Haal echte covers op via Open Library en genereer een fallback voor titels
zonder cover:

```bash
./env/bin/python fetch_covers.py
```

De afbeeldingen komen in `static/upload/<ISBN>.jpg`; boeken zonder cover
gebruiken `static/upload/default_cover.png`. Het script heeft ImageMagick
(`magick` of `convert`) nodig om afbeeldingen te schalen en fallbacks te maken.

## Boeken scannen

Open `/adminworkspace/scan`, of klik op **Boek scannen** in Boek Beheer.

- Een USB- of Bluetooth-scanner in HID-modus typt de ISBN en drukt Enter; er is
  geen driver of SDK nodig.
- ISBN-10 en ISBN-13 worden allebei ondersteund.
- Metadata komt van Google Books, met Open Library als fallback. Zet optioneel
  `GOOGLE_BOOKS_API_KEY` in `.env` voor een hogere quota.
- Bestaat het boek al, dan kun je meteen extra exemplaren toevoegen.
- Geen scanner bij de hand? Typ of plak de ISBN in hetzelfde veld.

## Exemplaren, labels en inventaris

Bij het toevoegen of scannen van een boek worden automatisch fysieke
exemplaren aangemaakt, elk met een eigen barcode (`BIB-000001`, ...).

- `/adminworkspace/exemplaren` — overzicht van exemplaren per boek.
- **Labels printen** via het boekdetail of het exemplarenoverzicht. De labels
  gebruiken Code 128 en zijn A4-printbaar.
- `/adminworkspace/inventaris` — scan exemplaar-barcodes; elk gescand exemplaar
  wordt als aanwezig geregistreerd.

Bestaande boeken eenmalig voorzien van exemplaren:

```bash
./env/bin/python scripts/backfill_exemplaren.py
```

Het script is herhaalbaar en slaat boeken met bestaande exemplaren over.

## Tests en codekwaliteit

```bash
./env/bin/pip install -r requirements-dev.txt
./env/bin/python -m pytest
./env/bin/ruff check .
```

De tests gebruiken een tijdelijke SQLite-database en raken `instance/bib.db`
niet aan.

## Healthcheck

`GET /healthz` geeft `{"status":"ok","database":"ok"}` (HTTP 200) zolang de
app en de database bereikbaar zijn. Bij een databasefout volgt HTTP 503.
