# Budjetti Home Assistantiin

Home Assistant -integraatio Budjetti-sovellukselle (budjetti-backend). Budjetti on erillinen
itse ylläpidettävä palvelu, jonka lähdekoodi ei ole julkinen; integraatio tarvitsee toimivan
Budjetti-palvelimen ja siitä luodun API-avaimen.

- **Budjettikortti**: kuukauden menot, tulot ja saldo, budjetit palkkeina, viimeisimmät tapahtumat.
  Tapahtumien lisäys, muokkaus ja poisto, budjettien muutos napauttamalla.
- **📷 Kuitti**: avaa puhelimen kameran, Budjetti lukee kuitin (kauppa, summa, päivä, kategoria,
  tuoterivit) ja täyttää lomakkeen. Tallennettaessa kuva ja tuoterivit tallentuvat budjettiin.
- **Anturit** automaatioihin: menot, tulot ja saldo tässä kuussa, kokonaisbudjettia jäljellä,
  menoennuste kuun loppuun sekä jokaisen kategorian käyttö (budjetti ja käyttöaste attribuutteina).
- **Palvelut**: `budjetti.add_transaction`, `budjetti.set_budget`, `budjetti.delete_transaction`.

Kortti ja palvelut kulkevat Home Assistantin kautta, joten ne toimivat myös etänä (Zima Client,
Nabu Casa) ilman suoraa yhteyttä budjettiin.

## Vaatimukset

- Home Assistant 2025.3 tai uudempi ja [HACS](https://hacs.xyz).
- Budjetti v0.4.0 tai uudempi, jonka Home Assistant tavoittaa (esim. `http://192.168.1.20:8000`).
- Kuitin lukuun Budjetissa asetettu `ANTHROPIC_API_KEY`. Ilman sitä kortin muut toiminnot toimivat.

## Asennus

1. HACS → ⋮ → **Custom repositories** → `https://github.com/MatvaZ/budjetti-homeassistant`, tyyppi
   **Integration** → **Add**. Etsi "Budjetti" ja asenna. Käynnistä Home Assistant uudelleen.
2. Luo API-avain: Budjetti-sovellus → **Tili** → **API-avaimet** → nimi "Home Assistant" → **Luo avain**.
3. Asetukset → Laitteet ja palvelut → **Lisää integraatio** → Budjetti. Anna osoite ja API-avain.
4. Lisää kortti näkymään: muokkaa näkymää → **Lisää kortti** → "Budjetti" (tai YAML: `type: custom:budjetti-card`).

Kortin asetukset (valinnaiset):

```yaml
type: custom:budjetti-card
transactions: 8        # montako tapahtumaa näytetään
entry_id: abc123...    # vain jos budjetteja on useita
```

## Esimerkki: ilmoitus kun ruokabudjetista on käytetty 80 %

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.budjetti_ruoka
    attribute: percent
    above: 79
actions:
  - action: notify.mobile_app_puhelin
    data:
      message: "Ruokabudjetista käytetty {{ state_attr('sensor.budjetti_ruoka', 'percent') }} %"
```

Anturien nimet näkyvät kohdassa Asetukset → Laitteet ja palvelut → Budjetti.

## Kortit

- **Budjetti** (`budjetti-card`): koko kuukausi. Näkyvät osiot, tapahtumien määrä ja otsikko valitaan kortin muokkauksessa.
- **Budjetti (pieni)** (`budjetti-mini-card`): saldo, menot ja pikalisäys, esim. puhelimen etusivulle tai seinätablettiin.

## Seuraava maksu

Anturi **Seuraava maksu** kertoo seuraavan toistuvan menon summan. Attribuutit: `name`, `date`, `payment_category`, `upcoming_this_month` ja `net_after_upcoming`.

## Tapahtumat automaatioille

| Tapahtuma | Milloin | Tiedot |
|---|---|---|
| `budjetti_budget_threshold` | Budjetista on käytetty vähintään 80 % tai 100 % | `category`, `threshold`, `percent`, `spent`, `budget`, `month` |
| `budjetti_large_expense` | Kirjataan iso kulu (oletus 100 €, raja vaihdetaan integraation asetuksista) | `id`, `amount`, `category`, `note`, `date`, `recurring` |

Kokonaisbudjetin kategoria on `Yhteensä`. Sama raja ilmoitetaan kerran kuussa. Vanhoista kirjauksista ei ilmoiteta asennuksen jälkeen.

```yaml
automation:
  - alias: Budjetti ylittyi
    triggers:
      - trigger: event
        event_type: budjetti_budget_threshold
        event_data:
          threshold: 100
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.event.data.category }}: budjetti ylittyi ({{ trigger.event.data.spent }} / {{ trigger.event.data.budget }} €)"
```

## Päivitykset ja versiointi

Versio on `VERSION`-tiedostossa (sama `manifest.json`:ssa), muoto MAJOR.MINOR.PATCH. Kun versio
muuttuu `main`-haarassa, GitHub Actions tekee julkaisun ja HACS ilmoittaa päivityksestä.
Muutokset versioittain: [CHANGELOG.md](CHANGELOG.md).

## Kehitys

Testit ajetaan Python 3.13:lla ilman oikeaa Home Assistantia tai Budjettia (rajapinta mockataan):

```bash
python3.13 -m venv .venv && . .venv/bin/activate
scripts/asenna-testit.sh          # tai: scripts/asenna-testit.sh vanhin  (HA 2025.3)
python -m pytest -q
node --check custom_components/budjetti/frontend/budjetti-card.js
```

Kehitys tehdään omassa haarassa: versiomuutos `main`-haarassa julkaisee version heti HACSiin.
Tarkemmat ohjeet: [KEHITYS.md](KEHITYS.md).
