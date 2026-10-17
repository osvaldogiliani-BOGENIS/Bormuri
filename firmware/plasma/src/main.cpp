// Bormuri, Pimoroni Plasma 2350: bocca OLED, catena LED, pulsante, temperatura.
// Protocollo (una riga ASCII per comando), vedi bormuri/lights/link.py.
//   PC -> Plasma:  S <STATO>   L <0-255>   M <128 cifre esadecimali>|M   B <0-255>   P
//   Plasma -> PC:  CIAO bormuri-plasma <versione>   BTN CORTO|LUNGO   T <gradi C>   OK

#include <Arduino.h>
#include <Wire.h>
#include <FastLED.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define FIRMWARE_VERSION "2"

// --- Pin della Plasma 2350 (da verificare col pinout Pimoroni) ------------
constexpr uint8_t PIN_LED_DATA = 15;  // morsetto DA, già traslato a 5 V
constexpr uint8_t PIN_SDA = 20;       // presa Qw/ST
constexpr uint8_t PIN_SCL = 21;
constexpr uint8_t PIN_STATUS_R = 16;  // LED RGB sulla scheda, attivo basso
constexpr uint8_t PIN_STATUS_G = 17;
constexpr uint8_t PIN_STATUS_B = 18;

// --- Catena LED unica, in ordine di collegamento -------------------------
constexpr uint16_t NUM_BASE = 130;   // barre e pulsantiere della base
constexpr uint16_t NUM_HEAD = 6;     // antenna e parabola, oltre il collo
constexpr uint16_t NUM_STRING = 50;  // filo di luci lato Borg, in fondo
constexpr uint16_t NUM_LEDS = NUM_BASE + NUM_HEAD + NUM_STRING;
constexpr uint16_t HEAD_START = NUM_BASE;
constexpr uint16_t STRING_START = NUM_BASE + NUM_HEAD;
#define COLOR_ORDER RGB  // i pixel WS2811 da 12 mm di solito sono RGB

// --- Periferiche Qwiic -----------------------------------------------------
constexpr uint8_t OLED_ADDR = 0x3C;
constexpr uint8_t TMP117_ADDR = 0x48;
constexpr uint8_t BUTTON_ADDR = 0x6F;
constexpr uint8_t BUTTON_STATUS_REG = 0x03;  // bit 2 = premuto
constexpr uint32_t I2C_HZ = 400000;          // abbassare a 100000 se il QwiicBus dà errori

constexpr uint8_t MOUTH_W = 128;
constexpr uint8_t MOUTH_H = 32;

constexpr uint32_t LINK_TIMEOUT_MS = 10000;
constexpr uint32_t LONG_PRESS_MS = 2000;
constexpr uint32_t TEMP_PERIOD_MS = 5000;
constexpr float HOT_C = 50.0;
constexpr uint8_t DEFAULT_BRIGHTNESS = 102;  // 40%

CRGB leds[NUM_LEDS];
Adafruit_SSD1306 oled(MOUTH_W, MOUTH_H, &Wire, -1);
bool oledOk = false;

enum class Scene { Riposo, Ascolto, Pensiero, Parla, Muto, Riunione, Autonoma };

Scene scene = Scene::Autonoma;  // finché il PC non si fa sentire
uint8_t voiceLevel = 0;
uint8_t brightness = DEFAULT_BRIGHTNESS;
uint8_t mouth[MOUTH_W];  // semi-altezza dell'onda per colonna, 0..15
bool mouthFromPc = false;
bool mouthDirty = true;
uint32_t lastMessageMs = 0;
float temperatureC = NAN;
String line;

// --- Uscite di stato ---------------------------------------------------------

void setStatusLed(bool r, bool g, bool b) {
  digitalWrite(PIN_STATUS_R, !r);
  digitalWrite(PIN_STATUS_G, !g);
  digitalWrite(PIN_STATUS_B, !b);
}

void applyBrightness() {
  bool hot = !isnan(temperatureC) && temperatureC > HOT_C;
  FastLED.setBrightness(hot ? brightness / 2 : brightness);
}

void clearMouth() {
  memset(mouth, 0, sizeof(mouth));
  mouthDirty = true;
}

// --- Protocollo seriale ---------------------------------------------------

Scene parseScene(const String &name) {
  if (name == "ASCOLTO") return Scene::Ascolto;
  if (name == "PENSIERO") return Scene::Pensiero;
  if (name == "PARLA") return Scene::Parla;
  if (name == "MUTO") return Scene::Muto;
  if (name == "RIUNIONE") return Scene::Riunione;
  return Scene::Riposo;
}

int hexNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return 0;
}

void parseMouth(const String &arg) {
  mouthFromPc = arg.length() > 0;  // "M" da solo = silenzio, linea di riposo
  for (uint8_t x = 0; x < MOUTH_W; x++) {
    mouth[x] = x < arg.length() ? hexNibble(arg[x]) : 0;
  }
  mouthDirty = true;
}

void handle(const String &cmd) {
  if (cmd.length() == 0) return;
  char op = cmd[0];
  String arg = cmd.length() > 2 ? cmd.substring(2) : String();
  arg.trim();
  if (scene == Scene::Autonoma) {  // il PC è tornato: via l'onda di riposo
    scene = Scene::Riposo;
    clearMouth();
  }
  switch (op) {
    case 'S': scene = parseScene(arg); break;
    case 'L': voiceLevel = constrain(arg.toInt(), 0, 255); break;
    case 'M': parseMouth(arg); break;
    case 'B': brightness = constrain(arg.toInt(), 0, 255); applyBrightness(); break;
    case 'P': Serial.println("OK"); break;
    default: return;
  }
  lastMessageMs = millis();
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      line.trim();
      handle(line);
      line = "";
    } else if (line.length() < 160) {  // "M " + 128 cifre ci stanno
      line += c;
    }
  }
}

// --- Qwiic: pulsante e temperatura ------------------------------------------

bool readRegister(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

void pollButton(uint32_t now) {
  static bool down = false;
  static bool longSent = false;
  static uint32_t downSince = 0;
  uint8_t status;
  if (!readRegister(BUTTON_ADDR, BUTTON_STATUS_REG, &status, 1)) return;
  bool pressed = status & 0x04;
  if (pressed && !down) {
    down = true;
    longSent = false;
    downSince = now;
  } else if (pressed && !longSent && now - downSince >= LONG_PRESS_MS) {
    longSent = true;
    Serial.println("BTN LUNGO");
  } else if (!pressed && down) {
    down = false;
    if (!longSent) Serial.println("BTN CORTO");
  }
}

void pollTemperature(uint32_t now) {
  static uint32_t last = 0;
  if (now - last < TEMP_PERIOD_MS) return;
  last = now;
  uint8_t raw[2];
  if (!readRegister(TMP117_ADDR, 0x00, raw, 2)) return;
  temperatureC = int16_t((raw[0] << 8) | raw[1]) * 0.0078125f;
  applyBrightness();
  Serial.print("T ");
  Serial.println(temperatureC, 1);
}

// --- Bocca ----------------------------------------------------------------

void idleMouth(uint32_t t) {
  // Da sola: un'onda leggera che respira, così la bocca non sembra spenta.
  uint8_t amp = beatsin8(8, 1, 4);
  for (uint8_t x = 0; x < MOUTH_W; x++) {
    mouth[x] = scale8(sin8(x * 6 + t / 8), amp);
  }
  mouthDirty = true;
}

void drawMouth() {
  if (!oledOk || !mouthDirty) return;
  oled.clearDisplay();
  const int mid = MOUTH_H / 2;
  for (uint8_t x = 0; x < MOUTH_W; x++) {
    int h = mouth[x];
    oled.drawFastVLine(x, mid - h, 2 * h + 1, SSD1306_WHITE);  // h = 0: linea di riposo
  }
  oled.display();
  mouthDirty = false;
}

// --- Scene luci -------------------------------------------------------------

void fillHead(const CRGB &c) { fill_solid(leds + HEAD_START, NUM_HEAD, c); }
void fillString(const CRGB &c) { fill_solid(leds + STRING_START, NUM_STRING, c); }

void drawRiposo(uint32_t t) {
  uint8_t v = beatsin8(6, 20, 120);  // respiro lento
  fill_solid(leds, NUM_BASE, CHSV(140, 200, v));
  fillHead(CHSV(150, 255, v));
  fillString(CHSV(160, 120, v));
}

void drawAscolto(uint32_t t) {
  fadeToBlackBy(leds, NUM_BASE, 40);
  leds[beatsin16(30, 0, NUM_BASE - 1)] = CRGB(0, 80, 255);  // scansione blu
  fillHead(CRGB(0, 60, 255));
  fillString(CRGB(0, 40, 200));
}

void drawPensiero(uint32_t t) {
  fadeToBlackBy(leds, NUM_BASE, 60);
  for (uint8_t k = 0; k < 4; k++) {
    leds[(t / 15 + k * NUM_BASE / 4) % NUM_BASE] = CRGB(255, 90, 0);  // arancio che rincorre
  }
  fillHead(CHSV(20, 255, beatsin8(40, 60, 255)));
  fadeToBlackBy(leds + STRING_START, NUM_STRING, 30);
  leds[STRING_START + (t / 40) % NUM_STRING] = CRGB(255, 90, 0);
}

void drawParla(uint32_t t) {
  uint8_t v = scale8(voiceLevel, 235) + 20;  // rosso che pulsa con la voce
  fill_solid(leds, NUM_BASE, CRGB(v, 0, 0));
  fillHead(CRGB(255, 0, 0));
  fillString(CRGB(v, v / 4, v / 4));
}

void drawMuto(uint32_t t) {
  fill_solid(leds, NUM_BASE, CRGB(10, 0, 0));
  fillHead(CRGB(40, 0, 0));
  fillString(CRGB::Black);
}

void drawRiunione(uint32_t t) {
  // "In onda": un pixel rosso pieno, il resto discreto per non disturbare in camera.
  fill_solid(leds, NUM_BASE, CRGB(20, 0, 0));
  leds[0] = CRGB(255, 0, 0);
  fillHead(CRGB(80, 0, 0));
  fillString(CRGB(8, 8, 12));
}

// --- Setup e loop ----------------------------------------------------------

void setup() {
  Serial.begin(115200);
  pinMode(PIN_STATUS_R, OUTPUT);
  pinMode(PIN_STATUS_G, OUTPUT);
  pinMode(PIN_STATUS_B, OUTPUT);
  setStatusLed(false, false, true);

  Wire.setSDA(PIN_SDA);
  Wire.setSCL(PIN_SCL);
  Wire.begin();
  Wire.setClock(I2C_HZ);
  oledOk = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);

  FastLED.addLeds<WS2812B, PIN_LED_DATA, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setMaxPowerInVoltsAndMilliamps(5, 3000);
  applyBrightness();

  Serial.println("CIAO bormuri-plasma " FIRMWARE_VERSION);
}

void loop() {
  readSerial();
  uint32_t now = millis();

  if (scene != Scene::Autonoma && now - lastMessageMs > LINK_TIMEOUT_MS) {
    scene = Scene::Autonoma;  // PC spento o programma chiuso: si va avanti da soli
    mouthFromPc = false;
  }
  bool alone = scene == Scene::Autonoma;
  setStatusLed(false, !alone, alone);

  pollButton(now);
  pollTemperature(now);

  switch (scene) {
    case Scene::Riposo: drawRiposo(now); break;
    case Scene::Ascolto: drawAscolto(now); break;
    case Scene::Pensiero: drawPensiero(now); break;
    case Scene::Parla: drawParla(now); break;
    case Scene::Muto: drawMuto(now); break;
    case Scene::Riunione: drawRiunione(now); break;
    case Scene::Autonoma: drawRiposo(now); break;
  }
  if (alone) idleMouth(now);
  drawMouth();
  FastLED.show();
  delay(16);  // ~60 fps
}
