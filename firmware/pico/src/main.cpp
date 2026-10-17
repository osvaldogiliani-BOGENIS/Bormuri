// Bormuri, coprocessore Pico 2: LED base e testa, filo di luci, ventola.
// Protocollo (una riga ASCII per comando), vedi bormuri/lights/link.py:
//   S <STATO>  L <0-255>  F <0-100>  B <0-255>  W <0-255>  P

#include <Arduino.h>
#include <FastLED.h>

constexpr uint8_t PIN_LED_BASE = 2;
constexpr uint8_t PIN_LED_HEAD = 3;
constexpr uint8_t PIN_STRING = 15;
constexpr uint8_t PIN_FAN = 16;

constexpr uint16_t NUM_BASE = 130;
constexpr uint16_t NUM_HEAD = 6;
constexpr uint32_t PWM_FREQ = 25000;     // richiesto dalle ventole PWM a 4 fili
constexpr uint32_t LINK_TIMEOUT_MS = 10000;
constexpr bool FAN_INVERTED = true;      // il transistor open-drain inverte il segnale

CRGB base[NUM_BASE];
CRGB head[NUM_HEAD];

enum class Scene { Riposo, Ascolto, Pensiero, Parla, Muto, Sicura };

Scene scene = Scene::Riposo;
uint8_t voiceLevel = 0;
uint8_t stringLevel = 180;
uint8_t fanPercent = 40;
uint32_t lastMessageMs = 0;
String line;

void setFan(uint8_t percent) {
  uint32_t duty = map(constrain(percent, 0, 100), 0, 100, 0, 255);
  analogWrite(PIN_FAN, FAN_INVERTED ? 255 - duty : duty);
}

void setString(uint8_t level) { analogWrite(PIN_STRING, level); }

Scene parseScene(const String &name) {
  if (name == "ASCOLTO") return Scene::Ascolto;
  if (name == "PENSIERO") return Scene::Pensiero;
  if (name == "PARLA") return Scene::Parla;
  if (name == "MUTO") return Scene::Muto;
  return Scene::Riposo;
}

void handle(const String &cmd) {
  if (cmd.length() == 0) return;
  char op = cmd[0];
  String arg = cmd.length() > 2 ? cmd.substring(2) : String();
  arg.trim();
  switch (op) {
    case 'S': scene = parseScene(arg); break;
    case 'L': voiceLevel = constrain(arg.toInt(), 0, 255); break;
    case 'F': fanPercent = constrain(arg.toInt(), 0, 100); setFan(fanPercent); break;
    case 'B': FastLED.setBrightness(constrain(arg.toInt(), 0, 255)); break;
    case 'W': stringLevel = constrain(arg.toInt(), 0, 255); setString(stringLevel); break;
    case 'P': Serial.println("OK"); break;
    default: return;
  }
  if (scene == Scene::Sicura) scene = Scene::Riposo;  // il Pi è tornato
  lastMessageMs = millis();
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      line.trim();
      handle(line);
      line = "";
    } else if (line.length() < 32) {
      line += c;
    }
  }
}

// --- Scene ---------------------------------------------------------------

void drawRiposo(uint32_t t) {
  uint8_t v = beatsin8(6, 20, 120);  // respiro lento
  fill_solid(base, NUM_BASE, CHSV(140, 200, v));
  fill_solid(head, NUM_HEAD, CHSV(150, 255, v));
}

void drawAscolto(uint32_t t) {
  fadeToBlackBy(base, NUM_BASE, 40);
  uint16_t pos = beatsin16(30, 0, NUM_BASE - 1);  // scansione avanti e indietro
  base[pos] = CRGB(0, 80, 255);
  fill_solid(head, NUM_HEAD, CRGB(0, 60, 255));
}

void drawPensiero(uint32_t t) {
  fadeToBlackBy(base, NUM_BASE, 60);
  for (uint8_t k = 0; k < 4; k++) {
    base[(t / 15 + k * NUM_BASE / 4) % NUM_BASE] = CRGB(255, 90, 0);  // arancio che rincorre
  }
  fill_solid(head, NUM_HEAD, CHSV(20, 255, beatsin8(40, 60, 255)));
}

void drawParla(uint32_t t) {
  uint8_t v = scale8(voiceLevel, 235) + 20;  // rosso che pulsa con la voce
  fill_solid(base, NUM_BASE, CRGB(v, 0, 0));
  fill_solid(head, NUM_HEAD, CRGB(255, 0, 0));
}

void drawMuto(uint32_t t) {
  fill_solid(base, NUM_BASE, CRGB(10, 0, 0));
  fill_solid(head, NUM_HEAD, CRGB(40, 0, 0));
}

void drawSicura(uint32_t t) {
  fill_solid(base, NUM_BASE, CRGB(8, 8, 8));
  fill_solid(head, NUM_HEAD, CRGB::Black);
}

// --- Setup e loop ----------------------------------------------------------

void setup() {
  Serial.begin(115200);
  analogWriteFreq(PWM_FREQ);
  analogWriteRange(255);
  pinMode(PIN_STRING, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  setFan(fanPercent);
  setString(stringLevel);

  FastLED.addLeds<WS2812B, PIN_LED_BASE, GRB>(base, NUM_BASE);
  FastLED.addLeds<WS2812B, PIN_LED_HEAD, GRB>(head, NUM_HEAD);
  FastLED.setBrightness(102);  // 40%: il Pi lo conferma con "B" all'avvio
  FastLED.setMaxPowerInVoltsAndMilliamps(5, 3000);
  lastMessageMs = millis();
}

void loop() {
  readSerial();
  uint32_t now = millis();

  if (now - lastMessageMs > LINK_TIMEOUT_MS && scene != Scene::Sicura) {
    scene = Scene::Sicura;  // il Pi non risponde: luci basse, ventola al massimo
    setFan(100);
  }

  switch (scene) {
    case Scene::Riposo: drawRiposo(now); break;
    case Scene::Ascolto: drawAscolto(now); break;
    case Scene::Pensiero: drawPensiero(now); break;
    case Scene::Parla: drawParla(now); break;
    case Scene::Muto: drawMuto(now); break;
    case Scene::Sicura: drawSicura(now); break;
  }
  FastLED.show();
  delay(16);  // ~60 fps
}
