# Bormuri

Codice del busto animatronico **Bormuri** (alieno namecciano mezzo Borg).
Il cervello è un Raspberry Pi 5; un Raspberry Pi Pico 2 fa da coprocessore per
LED della base, filo di luci lato Borg e ventola posteriore.

| Parte | Hardware | Modulo |
|---|---|---|
| Occhio Borg | Pi Camera Module 3 (CSI) | `bormuri/vision/` |
| Orecchio | microfono USB mini nell'antenna Borg | `bormuri/audio/capture.py`, `wakeword.py`, `stt.py` |
| Voce | Piper TTS → MAX98357A (I2S) → speaker 50 mm nel petto | `bormuri/audio/tts.py`, `playback.py` |
| Bocca | OLED 0,91" 128×32 SSD1306 (I2C) | `bormuri/display/mouth.py` |
| Cervello | API Claude | `bormuri/brain/llm.py` |
| Luci e ventola | Pico 2 via USB seriale | `bormuri/lights/`, `firmware/pico/` |

Schema e pin: [hardware/cablaggio.md](hardware/cablaggio.md).

## Come funziona

`bormuri/main.py` è una macchina a stati asyncio:

```
RIPOSO ──"Ehi Bormuri"/pulsante──► ASCOLTO ──fine frase──► PENSIERO ──risposta──► PARLA ──► RIPOSO
```

A ogni cambio di stato il Pi manda al Pico una riga di testo (`S PARLA`) e il
Pico cambia scena luci. Mentre Bormuri parla, la forma d'onda in bocca è
calcolata **dagli stessi campioni che vanno allo speaker**, letti con il
ritardo d'uscita compensato: è sincronizzata per costruzione.

## Installazione sul Pi

Raspberry Pi OS Bookworm 64 bit.

```bash
sudo apt install python3-venv python3-picamera2 python3-opencv libportaudio2 i2c-tools
python3 -m venv --system-site-packages .venv   # system-site per picamera2
. .venv/bin/activate
pip install -e '.[pi]'
```

`/boot/firmware/config.txt`:

```
dtparam=i2c_arm=on,i2c_arm_baudrate=1000000
dtoverlay=max98357a
```

La chiave API va in una variabile d'ambiente, mai nel repository:

```bash
echo 'ANTHROPIC_API_KEY=...' | sudo tee /etc/bormuri.env
```

## Primo traguardo (Fase 1 al banco)

```bash
python -m bormuri.display.mouth demo.wav            # OLED + speaker
python -m bormuri.display.mouth demo.wav --terminal # senza hardware
```

Poi l'intero robot: `python -m bormuri` (oppure `systemd/bormuri.service`).

## Firmware Pico

```bash
cd firmware/pico && pio run -t upload
```

## Test

```bash
pip install -e '.[dev]' && pytest
```

I test girano su qualunque computer: nessun pezzo di hardware è richiesto.
