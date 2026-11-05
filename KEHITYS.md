# Budjetti Home Assistantiin: kehitysohje

Home Assistant -integraatio (HACS, custom component) Budjetti-taustapalvelulle. Repo on **julkinen**:
ei salaisuuksia, API-avaimia, sisäisiä osoitteita eikä henkilötietoja (esimerkeissä `192.168.1.20`,
testeissä `budjetti.test`).

## Kokonaisuus

| Repo | Mitä | Näkyvyys |
|---|---|---|
| `budjetti-homeassistant` (tämä) | HA-integraatio ja Lovelace-kortit | julkinen |
| `budjetti` | FastAPI-taustapalvelu (budjetti-backend), tietokanta, kuitin luku | yksityinen |
| `tekoalyapuri` | Botti, joka käyttää samaa Budjettia | yksityinen |

Integraatio puhuu vain Budjetin REST-rajapinnalle (alla). Botti ei liity tähän repoon suoraan.
Rajapintamuutokset tehdään Budjettiin, ja tänne vain, jos integraatio käyttää niitä.

## Rakenne

```
custom_components/budjetti/
  __init__.py       asennus: palvelut, websocket, kortin JS (staattinen polku + add_extra_js_url)
  api.py            BudjettiClient: REST-kutsut ja virheluokat (Auth / NotFound / muu)
  coordinator.py    päivitys 60 s välein + tapahtumat budjetti_budget_threshold ja budjetti_large_expense
  sensor.py         anturit (menot, tulot, saldo, kokonaisbudjetti, ennuste, seuraava maksu, kategoriat)
  config_flow.py    asetus (osoite + API-avain), reauth, options (ison kulun raja)
  services.py       palvelut add_transaction / set_budget / delete_transaction
  websocket.py      korttien komennot budjetti/month|save|delete|set_budget|scan|receipt
  frontend/budjetti-card.js   kortit budjetti-card ja budjetti-mini-card (yksi tiedosto, ei build-vaihetta)
  strings.json, translations/en.json, translations/fi.json   strings.json = en.json
tests/              pytest-testit; Budjetti mockataan HTTP-tasolla (tests/conftest.py: FakeBudjetti)
scripts/asenna-testit.sh   testiriippuvuuksien asennus
```

## Komennot

```bash
python3.13 -m venv .venv && . .venv/bin/activate
scripts/asenna-testit.sh            # HA 2026.2.3 (requirements_test.txt)
scripts/asenna-testit.sh vanhin     # HA 2025.3.4 = hacs.json-vähimmäisversio (requirements_test_min.txt)
python -m pytest -q                 # kaikki testit
python -m pytest -q --cov=custom_components.budjetti --cov-report=term-missing
node --check custom_components/budjetti/frontend/budjetti-card.js
```

Eri HA-versiot kannattaa asentaa eri venveihin. CI (`.github/workflows/validate.yml`) ajaa jokaisesta
pushista: hassfest, HACS-tarkistus, VERSION = manifest.json, testit molemmilla HA-versioilla ja kortin
JS-syntaksin.

## Julkaisu

**Varoitus: kun `VERSION` muuttuu `main`-haarassa, `release.yml` luo heti julkaisun `vX.Y.Z` ja HACS
tarjoaa päivitystä kaikille käyttäjille.** Siksi:

- Kehitä omassa haarassa. Yhdistä mainiin vasta, kun testit ovat vihreät ja muutos on hyväksytty.
- Nosta `VERSION` ja `manifest.json` (aina samaksi) vain, kun ajonaikainen koodi muuttuu.
  Pelkät testit/dokumentit eivät vaadi versiota.
- Julkaisun teksti on viimeisimmän commitin viesti, joten mainiin tuleva commit kirjoitetaan muotoon
  `vX.Y.Z: Muutokset lyhyesti`.
- Kirjaa muutos `CHANGELOG.md`:hen ja `PAIVITYKSET.md`:n Tehdyt-osioon (toimintatapa siellä).
- Testaa lopuksi oikeassa Home Assistantissa se, mitä testit eivät kata (kortti, kamera), ja merkitse
  se PAIVITYKSET.md:hen.

## Rajapintasopimus Budjettiin

Kaikki pyynnöt: `Authorization: Bearer <API-avain>`, rahasummat sentteinä (int), kuukausi `YYYY-MM`.
Virhe: `{"detail": "teksti"}`. 401 → reauth-kulku, 404/405 → `BudjettiNotFoundError`, muu → `BudjettiError`.

| Kutsu | Käyttäjä | Kentät, joihin integraatio nojaa |
|---|---|---|
| `GET /api/health` | koordinaattori | `version` (laitteen ohjelmistoversio) |
| `GET /api/auth/me` | config flow | `id`, `username`, `email` |
| `GET /api/summary?month=` | anturit, tapahtumat, kortti | `expense_cents`, `income_cents`, `net_cents`, `total_budget_cents` (voi olla null), `categories[]`: `category`, `spent_cents`, `budget_cents` (voi olla null) |
| `GET /api/overview?month=` | anturi Ennuste | `forecast.projected_expense_cents`, `forecast.projected_net_cents` |
| `GET /api/recurring/upcoming?month=` | anturi Seuraava maksu, kortti | **Budjetti ≥ 0.4.0.** `items[]`: `name`, `date`, `amount_cents`, `type`, `category`; `expense_cents`, `net_after_cents` (null sallittu), `next` (null tai `name`, `date`, `amount_cents`, `category`). 404/405 → tyhjä tulos |
| `GET /api/transactions?month=` | iso kulu -tapahtuma, kortti | `id` (kasvava), `date`, `amount_cents` (hyvitys negatiivinen), `type` (`expense`/`income`), `category`, `note`, `recurring_id`, `has_receipt`, `item_count` |
| `GET /api/categories` | kortti | `name`, `type` |
| `GET /api/budgets?month=` | kortti | `category`, `amount_cents` |
| `POST /api/transactions`, `PUT/DELETE /api/transactions/{id}` | palvelut, kortti | runko `date`, `amount_cents`, `type`, `category`, `note`; vastaus sisältää `id` |
| `GET/PUT /api/transactions/{id}/items` | kortti | `name`, `price_cents`, `item_category` |
| `GET/PUT /api/transactions/{id}/receipt` | kortti | kuva (multipart-kenttä `file`) |
| `PUT /api/budgets/{kategoria}?month=&only=true` | palvelu, kortti | runko `amount_cents`; kategoria `Yhteensä` = kokonaisbudjetti |
| `POST /api/receipt/scan` | kortti | multipart `file`; vastaus esitäyttää lomakkeen |

Vähimmäisversio on Budjetti 0.3.0 (tulevat maksut 0.4.0). Jos Budjetin rajapinta muuttuu, päivitä
tämä taulukko, `tests/conftest.py`:n FakeBudjetti ja README:n vaatimukset.

## Tapoja

- Koodi, kommentit, commitit ja dokumentit suomeksi; HA:n käännöksissä `strings.json` = `en.json`.
- Ulkoinen rajapinta mockataan testeissä aina (`FakeBudjetti`); testit eivät saa ottaa verkkoyhteyttä.
- Tapahtumien tila tallentuu HA:n Storeen avaimella `budjetti.<entry_id>`; muutokset sen muotoon
  pitää tehdä niin, että vanha tallennettu tila toimii.
