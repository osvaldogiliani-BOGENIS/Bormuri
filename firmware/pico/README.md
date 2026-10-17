# Firmware Pico 2

Riceve dal Pi 5, via USB seriale, i comandi descritti in
`bormuri/lights/link.py` e pilota:

| Uscita | Pin | Tramite |
|---|---|---|
| Catena LED base (~130 WS2812B) | GP2 | 74AHCT125 (3,3→5 V), 330 Ω, 1000 µF |
| Catena LED testa (3–6 WS2812B) | GP3 | 74AHCT125, 330 Ω |
| Filo di luci lato Borg | GP15 PWM | MOSFET logic-level (AO3400) |
| Ventola posteriore 80 mm | GP16 PWM 25 kHz | transistor open-drain sull'ingresso PWM |

Se il Pi tace per più di 10 secondi il Pico va in modalità sicura:
luci al minimo e ventola al massimo.

```bash
pio run -t upload        # con il Pico in BOOTSEL al primo caricamento
pio device monitor       # prova a mano: scrivi "S ASCOLTO" e invio
```
