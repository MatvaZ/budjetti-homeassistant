# Päivityslista

Toimintatapa: Matias sanoo mitä listaan lisätään. Kohtia toteutetaan vasta kun hän käskee. Toteutuksen jälkeen kohta siirretään Tehdyt-osioon (versio merkitään) ja muutos viedään GitHubiin; HACS ilmoittaa päivityksestä. Versiointi kuten muissa projekteissa (`VERSION` = `manifest.json`).

## Avoimet

(ei avoimia kohtia)

## Tehdyt

- [x] v0.2.0: Kortin graafiset asetukset, tulevat maksut korttiin, Seuraava maksu -anturi, automaatioiden tapahtumat (budjetin raja, iso kulu) ja pieni kortti. Tulevat maksut vaativat Budjetti v0.4.0 (2026-11-03)
- [x] v0.1.2: Kortin emojit ja nuolet mdi-kuvakkeiksi (2026-11-02)
- [x] Kortti korttihaussa: ei vaatinut muutosta. Kortti ei näkynyt, koska sivu oli auki ennen integraation asennusta; sivun päivitys korjasi. Testattu HA 2026.2.3 ja 2026.10.4 (2026-10-31)
- [x] v0.1.1: MIT-lisenssi (HACS-tarkistus) (2026-10-31)
- [x] v0.1.0: Integraatio (anturit, palvelut, websocket) ja budjettikortti: budjetit, tapahtumien lisäys/muokkaus/poisto, budjettien muutos, kuitin luku kameralla Clauden avulla. Testattu: asennus HACS:llä, kortti, kamera ja kuitin luku (2026-10-31)
