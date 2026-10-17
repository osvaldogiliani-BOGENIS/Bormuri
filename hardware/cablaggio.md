# Cablaggio Bormuri

Versione senza saldature con la Pimoroni Plasma 2350. Fonte:
`bormuri/scheletro/distinta-e-montaggio.md` (sezione 4) nei file del progetto.

## Schema

```
 PC ══ USB ══ piastra retro ══ hub USB 7 porte (jack 5 V)
                                 ├─ camera occhio (prolunga USB al collo)
                                 ├─ microfono antenna (prolunga USB al collo)
                                 ├─ scheda audio ── jack 3,5 ── PAM8403 ── speaker petto
                                 ├─ alimentazione PAM8403 (USB)
                                 ├─ ventola Noctua (USB, velocità fissa)
                                 └─ Plasma 2350 (USB-C)
                                       ├─ morsetti LED ── pixel base ─► pulsanti ─► (JST al collo) ─► testa ─► filo di luci Borg
                                       └─ Qw/ST ── TMP117 ── Qwiic Button ── QwiicBus ══ RJ45 al collo ══ QwiicBus ── OLED bocca
```

## Plasma 2350

| Funzione | Pin | Note |
|---|---|---|
| Dati catena LED | GP15, morsetto DA | già traslato a 5 V sulla scheda |
| 5 V e GND catena LED | morsetti +5V e GND | dal Wago, fusibile 5 A, 1000 µF all'inizio |
| I2C Qw/ST | GP20 SDA, GP21 SCL | 400 kHz; 100 kHz se il cavo del collo dà errori |
| LED di stato | GP16/17/18 | verde = PC collegato, blu = da sola |

Indirizzi I2C: OLED 0x3C, TMP117 0x48, Qwiic Button 0x6F.

**Da verificare sulla scheda vera**: i numeri dei pin (presi dal pinout della
Plasma 2040, stesso schema), il conteggio dei pixel per tratto e l'ordine dei
colori, tutti in testa a `firmware/plasma/src/main.cpp`.

## Catena LED (un solo filo dati)

| Tratto | Pixel | Costante nel firmware |
|---|---|---|
| Base (barre e pulsantiere) | ~130 | `NUM_BASE` |
| Testa (antenna, parabola) | 3–6 | `NUM_HEAD` |
| Filo di luci lato Borg | in fondo alla catena | `NUM_STRING` |

## Alimentazione

- 5 V 10 A esterno → interruttore → fusibile 10 A → Wago: hub (jack), Plasma/LED (fusibile 5 A).
- Bilancio: ~4,6 A con i LED al 40%.
- Il caricatore Anker resta indipendente: prolunga USB-C "full featured" dalla piastra.
