# Plan: schoolbibliotheek-site

Dit plan beschrijft wat de site nog nodig heeft om dagelijks bruikbaar te zijn in
een schoolbibliotheek, met **barcode-scannen als speerpunt**. Het bouwt voort op
de huidige Flask-app (28 routes, rollen, reserveringen, covers, CSV-import,
healthcheck en tests).

## 1. Uitgangspunten

- **Primaire scanner:** USB/Bluetooth-scanner in HID-modus (keyboard wedge).
  De scanner typt de code en stuurt Enter; er is geen driver of SDK nodig.
- **Fallback:** camera-scannen via de browser op tablet/telefoon.
- **Een school, één vestiging.** Meerdere vestigingen zijn een latere uitbreiding.
- **Privacy:** alleen leerlinggegevens die strikt nodig zijn; AVG/GDPR-proof.
- **Bestaande stack blijft:** Flask, SQLAlchemy, Bootstrap 5, HTMX, SQLite lokaal
  en PostgreSQL als de school dat wil.

## 2. Waar staan we nu?

| Onderdeel | Nu | Nog nodig |
|---|---|---|
| Boek toevoegen | Handmatig formulier; veld `aantal` wordt genegeerd | Scan ISBN → metadata → opslaan |
| Exemplaren | Alleen tellers `aantal` / `beschikbaar_aantal` | Individuele exemplaren met eigen barcode |
| Leden | Naam, e-mail, rol | Studentnummer, klas, lidkaart-barcode |
| Uitlenen | Reserveringen met datums | Echte uitleenadministratie met inname en verlengen |
| Te laat | Overzichtspagina | Automatische herinneringen en boeteregistratie |
| Rapportage | Alleen overdue | Dashboards, export, populaire boeken |
| Zoeken | Titel/auteur/ISBN/filters | Scanveld, beschikbaarheid per exemplaar |
| Beveiliging | bcrypt, rollen | CSRF, rate limiting, wachtwoord-reset |
| Backups | Handmatige zip via `setup.py` | Automatisch + geteste restore |
| Deployment | Dev-server / gunicorn | Reverse proxy, HTTPS, logging, monitoring |
| Tests | 7 smoketests | Uitgebreidere route- en servicetests |

## 3. Barcode-scannen: ontwerp

### 3.1 Soorten codes

| Code | Doel | Formaat |
|---|---|---|
| ISBN | Boek titel herkennen | EAN-13, begint met 978/979 (soms ISBN-10) |
| Exemplaar-barcode | Fysiek exemplaar | Code 128, bijv. `BIB-000123` |
| Lidkaart | Leerling herkennen | Bestaande schoolkaart of `LID-2026-0001` |

### 3.2 Scanflows

**A. Boek toevoegen (kernvraag)**

```
Scan ISBN
  → normaliseer (ISBN-10 → ISBN-13, controlecijfer checken)
  → bestaat het boek al?
       ja  → "Exemplaar toevoegen" (aantal +1, nieuwe exemplaar-barcode)
       nee → metadata ophalen (Google Books → Open Library fallback)
  → preview met titel, auteur, cover, uitgever, jaar, pagina's
  → bibliothecaris controleert / past aan
  → opslaan + cover downloaden + label printen
```

**B. Uitlenen**

```
Scan lidkaart → scan exemplaar-barcode → leentermijn automatisch (bijv. 14 dagen)
```

**C. Innemen**

```
Scan exemplaar-barcode → uitlening sluiten → exemplaar weer beschikbaar
```

**D. Inventaris**

```
Scan alle boeken in een kast → vergelijk met database → rapport "ontbreekt / staat verkeerd"
```

### 3.3 UX-eisen voor de scanmodus

- Groot, altijd gefocust invoerveld; opnieuw focussen na elke scan.
- Enter als scheidingsteken; ondersteun ook Tab (instelbaar).
- Hoorbare piep bij succes, fouttoon bij onbekende/invalid code.
- Dubbele scans binnen 2 seconden negeren.
- Laatste 5 scans zichtbaar met status (nieuw / bestaand / fout).
- Handmatige invoer blijft mogelijk als de scanner niet werkt.
- Duidelijke foutmelding bij: ongeldig ISBN, API-time-out, netwerk weg.
- Geen pagina-herlaadactie nodig; gebruik HTMX of fetch.

### 3.4 Technisch ontwerp

**Backend**

- `services/isbn_lookup.py`
  - `normaliseer_isbn(code)` → ISBN-13 of fout.
  - `zoek_metadata(isbn)` → Google Books, daarna Open Library.
  - `zoek_cover(isbn)` → cover-URL of `None`.
  - Cache: tabel `isbn_cache` of JSON-bestand met TTL (bijv. 30 dagen).
- Nieuwe routes:
  - `GET /adminworkspace/scan` → scanpagina.
  - `GET /api/isbn/<isbn>` → JSON metadata (voor live preview).
  - `POST /adminworkspace/scan` → boek/exemplaar opslaan.
  - `POST /api/exemplaren/scan` → uitleen/inname/inventaris.
- Bestaande add-logica uit `app.py` verplaatsen naar een functie
  `maak_boek_van_metadata(...)` zodat formulier en scan dezelfde code gebruiken.
- Cover: hergebruik de bestaande `fetch_covers.py`-logica of download direct
  naar `static/upload/<ISBN>.jpg`, met de bestaande fallback.
- **Bug meteen fixen:** het formulierveld `aantal` wordt nu niet opgeslagen.

**Frontend**

- `templates/scan.html` + `static/js/scan.js`.
- Autofocus, Enter-listener, audio via Web Audio API, duplicate-lock.
- HTMX-partial voor de preview, zodat de pagina niet herlaadt.
- Optioneel later: camera-scan met `@zxing/browser` (vereist HTTPS).

**Validatie**

- ISBN-13-controlecijfer; ISBN-10 omzetten.
- Bestaande ISBN's detecteren en omleiden naar "exemplaar toevoegen".
- Rate limiting op de metadata-API om quota te sparen.

### 3.5 Acceptatiecriteria voor de scan-MVP

- [ ] Een echte ISBN scannen vult binnen 2 seconden titel, auteur, cover en
      pagina's in.
- [ ] Onbekende ISBN valt terug op handmatige invoer zonder dataverlies.
- [ ] Bestaande ISBN biedt "exemplaar toevoegen" aan in plaats van een duplicaat.
- [ ] Scanner, toetsenbord en plakken werken alle drie.
- [ ] Cover wordt opgeslagen of er verschijnt een nette fallback.
- [ ] Tests met gemockte metadata-API; `ruff` en `pytest` groen.

**Inspanning:** 2–3 dagen.

## 4. Datamodel uitbreiden

Het huidige model telt exemplaren, maar een bibliotheek moet elk fysiek boek
kunnen volgen. Voorgesteld model:

```
Boek 1 ─── * Exemplaar 1 ─── * Uitlening * ─── 1 Gebruiker
  │
  └── * Reservatie (op titelniveau)
```

**Nieuwe/uitgebreide tabellen**

- `exemplaren`: `id`, `boek_isbn`, `barcode` (uniek), `status`
  (beschikbaar/uitgeleend/verloren/herstel), `locatie_id`, `aankoopdatum`,
  `conditie`, `deleted`.
- `uitleningen`: `id`, `exemplaar_id`, `gebruiker_id`, `start_date`,
  `due_date`, `returned_at`, `verlengingen`, `deleted`.
- `gebruikers`: `studentnummer` (uniek, optioneel), `klas`, `kaart_barcode`
  (uniek, optioneel).
- `boeken`: `uitgever`, `publicatiejaar`, `taal`, `editie`.
- `isbn_cache`: `isbn`, `bron`, `payload` (JSON), `fetched_at`.

**Migratie**

1. Alembic activeren (Flask-Migrate is al geïnstalleerd).
2. Nieuwe tabellen aanmaken.
3. Voor elk bestaand boek `aantal` exemplaren genereren met barcodes
   `BIB-<volgnummer>`.
4. `beschikbaar_aantal` omzetten naar "aantal exemplaren met status beschikbaar".
5. Oude tellers tijdelijk als afgeleide waarden houden; daarna verwijderen.

**Barcode-afspraken**

- Titel: ISBN-13 (EAN-13) op de achterkant van het boek.
- Exemplaar: eigen Code 128-label, zodat twee kopieën van hetzelfde boek
  apart te scannen zijn.
- Lid: bij voorkeur de bestaande schoolkaart; anders een geprinte lidkaart.

**Inspanning:** 3–5 dagen inclusief migratie en testdata.

## 5. Roadmap in fases

| Fase | Onderwerp | Resultaat | Duur |
|---|---|---|---|
| 0 | Fundament | App factory/blueprints, Alembic, CSRF, bredere tests | 2–3 dagen |
| 1 | **Scan → boek toevoegen** | ISBN scannen, metadata, preview, opslaan, cover | 2–3 dagen |
| 2 | Exemplaren & labels | Copy-records, barcodelabels, inventaris-scannen | 3–4 dagen |
| 3 | Uitlenen & innemen | Lidkaart + exemplaar scannen, leentermijn, verlengen, inname | 4–5 dagen |
| 4 | Communicatie & rapporten | E-mailherinneringen, dashboards, CSV-export | 3–4 dagen |
| 5 | Hardening & deployment | HTTPS, backups, monitoring, AVG, performance | 2–3 dagen |

Totaal: ongeveer **4–6 weken** deeltijd, afhankelijk van hoeveel er parallel
gewerkt wordt.

**Status:** fase 1 (scan → boek toevoegen) en fase 2 (exemplaren, labels en
inventaris) zijn geïmplementeerd. Zie `services/isbn_lookup.py`,
`services/exemplaren.py`, `/adminworkspace/scan`, `/adminworkspace/exemplaren`,
`/adminworkspace/boek/<ISBN>/labels` en `/adminworkspace/inventaris`.

## 6. Nice-to-haves, geprioriteerd

### Must (voor echt dagelijks gebruik)

- Scan → boek toevoegen.
- Exemplaren met eigen barcode.
- Uitlenen en innemen met scanner.
- Lidkaarten / studentnummers.
- Leentermijnen, verlengen, te-laat-signalering.
- Automatische backups + geteste restore.
- CSRF en veilige sessies.

### Should (veel waarde, later)

- E-mailherinneringen vóór en na de vervaldatum.
- Rapportage: populairste boeken, achterstallig, voorraad per locatie.
- Bulk-import en bulk-scan (meerdere boeken in één keer).
- Labelprint: Code 128/QR via browser of PDF.
- Camera-scannen op tablet/telefoon.
- Boekmetadata verrijken met uitgever, jaar en taal.

### Could (nice, maar niet urgent)

- PWA / offline scanmodus.
- Zelfbedieningskiosk voor leerlingen.
- Leeslijsten, reviews en aanbevelingen.
- Koppeling met het schoolsysteem (SIS) voor leerlingen.
- Meerdere vestigingen.
- Boetebetalingen of een digitaal leenpasje.

### Won't (bewust niet nu)

- Volledig commercieel bibliotheeksysteem (ILS) nabouwen.
- Native mobiele app.
- Betaalde boekendatabanken zonder licentie.

## 7. Beveiliging, privacy en beheer

- **AVG:** minimum aan leerlinggegevens, duidelijke bewaartermijn, export- en
  verwijderfunctie, toegang per rol, audit-log van wie wat wijzigt.
- **Auth:** bcrypt (gedaan), CSRF, rate limiting op login en scan-API,
  wachtwoord-reset via e-mail, sessie-time-out.
- **Backups:** dagelijkse dump van database + uploads, minimaal één restore-test
  per maand.
- **Deployment:** gunicorn achter nginx, HTTPS, `FLASK_DEBUG=0`,
  `SECRET_KEY` uit `.env`, `/healthz` als monitor.
- **Logging:** fouten loggen, geen wachtwoorden of volledige leerlingdata loggen.

## 8. Concrete eerste sprint (aanbevolen)

**Doel:** een werkende scan-to-add-MVP op de experimental branch.

1. `services/isbn_lookup.py` met ISBN-normalisatie, Google Books en Open Library.
2. `GET /api/isbn/<isbn>` + `templates/scan.html` + `static/js/scan.js`.
3. Add-logica uit `app.py` extraheren en hergebruiken.
4. `aantal`-veld fixen en bestaande ISBN → "exemplaar toevoegen".
5. Tests met gemockte API's; README bijwerken.
6. Handmatige test met een echte USB-scanner en minimaal 10 ISBN's.

**Definition of done:** een bibliothecaris scant een boek, controleert de
preview, slaat het op en ziet het direct terug in de catalogus — zonder iets
over te typen.

## 9. Beslissingen die we moeten nemen

1. **Scanner:** USB HID als primair (aanbevolen) of meteen camera?
2. **Exemplaren:** nu invoeren (aanbevolen, vóór uitleen) of tellers laten staan?
3. **Lidkaarten:** bestaande schoolkaart hergebruiken of eigen labels printen?
4. **Metadata-bron:** Google Books met API-key (betere Nederlandse data) of
   alleen Open Library (geen key, minder volledig)?
5. **Hosting:** schoolserever met PostgreSQL of lokaal SQLite?
6. **E-mail:** welke SMTP-server mag de school gebruiken voor herinneringen?
7. **Bewaartermijn:** hoe lang mogen uitleen- en leerlinggegevens bewaard blijven?
