# Firmware Plasma 2350

La Pimoroni Plasma 2350 sta nella base, collegata all'hub USB. Riceve dal PC,
via USB seriale, i comandi descritti in `bormuri/lights/link.py` e pilota tutto
senza saldature:

| Cosa | Dove sulla Plasma | Collegamento |
|---|---|---|
| Catena LED unica: base → pulsanti → testa → filo di luci Borg | morsetti DATA (GP15), 5V, GND | pixel 12 mm e filo WS2812 con spine JST |
| OLED bocca 128×32 SSD1306 | Qw/ST (I2C GP20/GP21) | QwiicBus + cavo di rete RJ45 nel collo |
| Sensore temperatura TMP117 | Qw/ST, indirizzo 0x48 | cavo Qwiic in catena |
| Pulsante nascosto SparkFun Qwiic Button | Qw/ST, indirizzo 0x6F | cavo Qwiic in catena |
| LED RGB di stato sulla scheda | GP16/17/18 | verde = PC collegato, blu = da sola |

La ventola Noctua prende corrente da una porta USB dell'hub e gira a velocità
fissa: il firmware non la controlla. Legge però la temperatura della base, la
manda al PC e, se supera 50 °C, abbassa la luminosità dei LED.

Se il PC tace per più di 10 secondi (spento o programma chiuso) la Plasma
continua da sola: luci in respiro lento e un'onda leggera in bocca.

**Da verificare sulla scheda vera**: pin della Plasma 2350 e numero di pixel
per tratto (`NUM_BASE`, `NUM_HEAD`, `NUM_STRING` in `src/main.cpp`), ordine
colori dei pixel (`COLOR_ORDER`).

```bash
pio run -t upload        # la prima volta tieni premuto BOOT mentre colleghi l'USB
pio device monitor       # prova a mano: scrivi "S ASCOLTO" e invio
```
