# Budjetti Home Assistantiin

Home Assistant -integraatio [Budjetti](https://github.com/MatvaZ/budjetti)-sovellukselle (budjetti-backend):

- **Budjettikortti**: kuukauden menot, tulot ja saldo, budjetit palkkeina, viimeisimmät tapahtumat.
  Tapahtumien lisäys, muokkaus ja poisto, budjettien muutos napauttamalla.
- **📷 Kuitti**: avaa puhelimen kameran, Claude lukee kuitin (kauppa, summa, päivä, kategoria,
  tuoterivit) ja täyttää lomakkeen. Tallennettaessa kuva ja tuoterivit tallentuvat budjettiin.
- **Anturit** automaatioihin: menot, tulot ja saldo tässä kuussa, kokonaisbudjettia jäljellä,
  menoennuste kuun loppuun sekä jokaisen kategorian käyttö (budjetti ja käyttöaste attribuutteina).
- **Palvelut**: `budjetti.add_transaction`, `budjetti.set_budget`, `budjetti.delete_transaction`.

Kortti ja palvelut kulkevat Home Assistantin kautta, joten ne toimivat myös etänä (Zima Client,
Nabu Casa) ilman suoraa yhteyttä budjettiin.

## Vaatimukset

- Home Assistant 2025.3 tai uudempi ja [HACS](https://hacs.xyz).
- Budjetti v0.3.0 tai uudempi, jonka Home Assistant tavoittaa (esim. `http://192.168.1.20:8000`).
- Kuitin lukuun Budjetissa `ANTHROPIC_API_KEY` (Claude). Ilman sitä kortin muut toiminnot toimivat.

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

## Päivitykset ja versiointi

Versio on `VERSION`-tiedostossa (sama `manifest.json`:ssa), muoto MAJOR.MINOR.PATCH. Kun versio
muuttuu `main`-haarassa, GitHub Actions tekee julkaisun ja HACS ilmoittaa päivityksestä.
