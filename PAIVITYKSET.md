# Päivityslista

Toimintatapa: Matias sanoo mitä listaan lisätään. Kohtia toteutetaan vasta kun hän käskee. Toteutuksen jälkeen kohta siirretään Tehdyt-osioon (versio merkitään) ja muutos viedään GitHubiin; HACS ilmoittaa päivityksestä. Versiointi kuten muissa projekteissa (`VERSION` = `manifest.json`).

## Avoimet

(ei avoimia kohtia)

## Tehdyt

- [x] v0.2.1: Kehityskunto ja v0.2.0:n tarkistus (2026-11-05)
  - Korjattu bugi: budjetin raja -tapahtuma laukesi pyöristetyn prosentin mukaan (100 % jo 99,5 %:lla, 80 % jo 79,5 %:lla). Nyt verrataan tarkkaan käyttöön.
  - Lisätty pytest-testit (72 kpl) ja niiden ajo CI:hin, kortin JS-syntaksin tarkistus CI:hin, testi VERSION = manifest.json (CI-tarkistus oli jo olemassa). Vähimmäisvaatimukseksi Budjetti v0.4.0 (0.3.x ei enää käytössä), yksityisen repon linkki poistettu, kuitin luvun teksteistä palveluntarjoajan nimi pois. Uudet KEHITYS.md ja CHANGELOG.md.
  - Todennettu automaattisilla testeillä HA 2025.3.4:llä ja 2026.2.3:lla, Budjetti mockattuna (ei oikeaa palvelinta): config flow, reauth ja asetukset (ison kulun raja); anturien arvot ja attribuutit, uudet kategoriat; tapahtumat (80/100 %, kokonaisbudjetti, kerran kuussa, uusi kuu, ei toistoa uudelleenkäynnistyksessä, ei ilmoituksia asennuksen jälkeen vanhoista; iso kulu, raja ja 0 = pois); api-virheet (401 → reauth, yhteysvirhe → yritetään uudelleen); vanha Budjetti ilman tulevia maksuja (404/405 → tyhjä, Seuraava maksu tuntematon, muu toimii); palvelut ja korttien websocket-komennot; kortin JS:n syntaksi.
  - Ei todennettu (julkaistu omistajan päätöksellä ennen käsin testausta), testattava oikeassa Home Assistantissa: kortin graafinen editori ja pieni kortti, Tulossa-osion näkyminen kortilla, Seuraava maksu -anturi oikeaa Budjetti 0.4.x:ää vasten, tapahtumien laukeaminen ja automaatio oikeassa HA:ssa, ison kulun rajan muutos asetuksista, kortin uusi teksti "Luetaan kuittia…".
- [x] v0.2.0: Kortin graafiset asetukset, tulevat maksut korttiin, Seuraava maksu -anturi, automaatioiden tapahtumat (budjetin raja, iso kulu) ja pieni kortti. Tulevat maksut vaativat Budjetti v0.4.0 (2026-11-03)
- [x] v0.1.2: Kortin emojit ja nuolet mdi-kuvakkeiksi (2026-11-02)
- [x] Kortti korttihaussa: ei vaatinut muutosta. Kortti ei näkynyt, koska sivu oli auki ennen integraation asennusta; sivun päivitys korjasi. Testattu HA 2026.2.3 ja 2026.10.4 (2026-10-31)
- [x] v0.1.1: MIT-lisenssi (HACS-tarkistus) (2026-10-31)
- [x] v0.1.0: Integraatio (anturit, palvelut, websocket) ja budjettikortti: budjetit, tapahtumien lisäys/muokkaus/poisto, budjettien muutos, kuitin luku kameralla. Testattu: asennus HACS:llä, kortti, kamera ja kuitin luku (2026-10-31)
