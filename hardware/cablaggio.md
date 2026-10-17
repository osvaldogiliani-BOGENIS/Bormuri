# Cablaggio Bormuri

Riassunto operativo della sezione 3 del piano di costruzione
(`piano-costruzione-bormuri.md`, che resta la fonte).

## Raspberry Pi 5

| Funzione | GPIO | Pin fisico | Note |
|---|---|---|---|
| OLED SDA | GPIO2 | 3 | I2C1 a 1 MHz |
| OLED SCL | GPIO3 | 5 | |
| OLED VCC | 3,3 V | 1 | GND su pin 6 |
| I2S BCLK → MAX98357A | GPIO18 | 12 | |
| I2S LRCLK | GPIO19 | 35 | |
| I2S DIN | GPIO21 | 40 | MAX98357A VIN dal 5 V 10 A |
| Pulsante push-to-talk | GPIO17 | 11 | pull-up interno, altro capo a GND |
| Pi Camera Module 3 | CSI | CAM/DISP 0 | flat Pi 5 da 50 cm–1 m |
| Microfono mini | USB | | nella punta dell'antenna Borg |
| Pico 2 | USB | | `/dev/ttyACM0` |

`/boot/firmware/config.txt`:

```
dtparam=i2c_arm=on,i2c_arm_baudrate=1000000
dtoverlay=max98357a
```

## Raspberry Pi Pico 2

| Funzione | Pin | Tramite |
|---|---|---|
| Catena LED base (~130 px) | GP2 | 74AHCT125, 330 Ω in serie, 1000 µF all'ingresso |
| Catena LED testa (3–6 px) | GP3 | 74AHCT125, 330 Ω in serie |
| Filo di luci lato Borg | GP15 PWM | MOSFET AO3400 lato basso |
| Ventola NF-A8 5V PWM | GP16 PWM 25 kHz | transistor open-drain (logica invertita nel firmware) |

## Alimentazione

- Pi 5: alimentatore ufficiale 27 W USB-C.
- LED, filo di luci, MAX98357A, ventola: 5 V 10 A con jack, fusibile 5 A sulla linea LED.
- Masse in comune fra Pi, Pico e 5 V.
- Il caricatore Anker resta indipendente: solo il suo cavo USB-C attraversa la base,
  l'alimentatore ≥25 W sta fuori.

## Connettore al collo

GX16 8 poli (LED testa, filo di luci, OLED I2C, 5 V, GND) più passaggio separato
per il flat della camera e il cavo del microfono, dentro la colonna trasparente.
