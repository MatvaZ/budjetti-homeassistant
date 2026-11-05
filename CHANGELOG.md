# Muutokset

Versiot vastaavat GitHub-julkaisuja (`vX.Y.Z`), jotka syntyvät, kun `VERSION` muuttuu `main`-haarassa.
Budjetti-vaatimus tarkoittaa taustapalvelun (budjetti-backend) versiota.

## 0.2.1 (julkaisematta)

- Korjattu: budjetin raja -tapahtuma (`budjetti_budget_threshold`) laukesi pyöristetyn prosentin
  perusteella, eli 100 % -raja jo 99,5 %:n käytöllä ja 80 % -raja 79,5 %:lla. Nyt raja täyttyy vasta,
  kun käyttö on oikeasti vähintään 80 % / 100 %. Tapahtuman `percent` on edelleen pyöristetty.
- Automaattiset testit (pytest, Home Assistant 2025.3.4 ja 2026.2.3) ja niiden ajo CI:ssä,
  kortin JS-syntaksin tarkistus CI:ssä.
- README: Budjetti-vaatimus tarkennettu (0.3.0, tulevat maksut 0.4.0), kuollut linkki poistettu,
  kehittäjän pika-aloitus. Uudet KEHITYS.md (kehitysohje ja rajapintasopimus) ja tämä tiedosto.

## 0.2.0 (2026-11-03)

- Kortin graafiset asetukset (Muokkaa korttia): näkyvät osiot, tapahtumien määrä, otsikko.
- Tulevat maksut korttiin (Tulossa-osio ja saldo tulevien jälkeen). Vaatii Budjetti 0.4.0;
  vanhemmalla osio jää tyhjäksi.
- Anturi Seuraava maksu.
- Tapahtumat automaatioille: `budjetti_budget_threshold` (80 % / 100 %) ja `budjetti_large_expense`
  (raja integraation asetuksista, oletus 100 €).
- Pieni kortti `budjetti-mini-card`: saldo, menot ja pikalisäys.

## 0.1.2 (2026-11-02)

- Kortin emojit ja nuolet vaihdettu mdi-kuvakkeiksi.

## 0.1.1 (2026-10-31)

- MIT-lisenssi (HACS-tarkistus).

## 0.1.0 (2026-10-31)

- Ensimmäinen versio: anturit (menot, tulot, saldo, kokonaisbudjetti, ennuste, kategoriat),
  palvelut (`add_transaction`, `set_budget`, `delete_transaction`), websocket-komennot ja budjettikortti
  (budjetit, tapahtumien lisäys/muokkaus/poisto, budjettien muutos, kuitin luku kameralla).
  Vaatii Budjetti 0.3.0.
