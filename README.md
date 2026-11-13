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

Standaard wordt een lokale SQLite-database gebruikt (`instance/bib.db`). Om de
Postgres-server te gebruiken, zet je `DATABASE_URL` voor je de app start:

```bash
export DATABASE_URL="postgresql+psycopg2://gebruiker:wachtwoord@localhost/bibdb"
python app.py
```

Gebruik Python 3.12 of 3.13 voor de virtuele omgeving: SQLAlchemy 2.0.25 werkt
niet op Python 3.14.

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
