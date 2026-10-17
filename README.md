# Bormuri

Codice del busto animatronico **Bormuri** (alieno namecciano mezzo Borg).

Bormuri è sempre collegato al PC con un solo cavo USB. Il PC fa da cervello e
vede Bormuri come webcam, microfono e altoparlante standard. Nella base una
**Pimoroni Plasma 2350** pilota bocca, luci e pulsante, e continua da sola
quando il PC è spento.

| Parte | Hardware | Codice |
|---|---|---|
| Bocca | OLED 0,91" 128×32 SSD1306 Qwiic, nel collo via QwiicBus e cavo di rete | `firmware/plasma/`, `bormuri/display/mouth.py` |
| Luci | una catena di pixel WS2811/WS2812 da 12 mm: base → testa → filo di luci Borg | `firmware/plasma/` |
| Pulsante e temperatura | SparkFun Qwiic Button, sensore TMP117 | `firmware/plasma/` |
| Ventola | Noctua 5 V dalla porta USB dell'hub, velocità fissa | nessuno |
| Occhio, orecchio, voce | camera Arducam USB, microfono USB, scheda audio USB + PAM8403 | `bormuri/` (programma del PC) |

Schema e collegamenti: [hardware/cablaggio.md](hardware/cablaggio.md).

## Stato

- **Firmware Plasma 2350**: pronto da caricare, compila con PlatformIO.
- **Programma del PC**: da fare più avanti. Il pacchetto `bormuri/` contiene già
  il protocollo verso la Plasma (`bormuri/lights/link.py`), la bocca
  sincronizzata con la voce e lo scheletro di ascolto, voce e Claude, ancora nella
  forma pensata per il Raspberry Pi: va adattato al PC Windows.

## Firmware della Plasma

```bash
pip install platformio
cd firmware/plasma && pio run -t upload   # la prima volta tieni premuto BOOT collegando l'USB
pio device monitor                         # prova: scrivi "S ASCOLTO" e invio
```

## Bocca sincronizzata

Mentre Bormuri parla, il PC calcola l'altezza dell'onda **dagli stessi campioni
che manda all'altoparlante**, con il ritardo d'uscita compensato, e la manda alla
Plasma 30 volte al secondo (`M` + 128 cifre esadecimali). La Plasma la disegna
sull'OLED. Per vedere l'effetto senza hardware:

```bash
pip install -e '.[dev]'
python -m bormuri.display.mouth demo.wav --terminal
```

## Test

```bash
pytest
```

I test girano su qualunque computer: nessun pezzo di hardware è richiesto.
