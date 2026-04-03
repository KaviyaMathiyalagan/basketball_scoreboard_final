/*
  =====================================================================
  Basketball Scoreboard — NodeMCU + 16×32 LED Matrix (HUB12, 1/8 scan)
  HIVE · Sri Ramakrishna Institute of Technology
  =====================================================================

  DISPLAY: Cycles through screens every 2–3 seconds:
    Screen 1 → Team A name   (e.g. "SRIT")
    Screen 2 → Team A score  (e.g.  "16")
    Screen 3 → Team B name   (e.g. "SREC")
    Screen 4 → Team B score  (e.g.  "03")
    Screen 5 → Clock         (e.g. "12:34" or "45.6")
    Screen 6 → Quarter       (e.g.  "Q 3")

  WIRING:
    Panel OE  (Pin 1)  → NodeMCU D1
    Panel A   (Pin 2)  → NodeMCU D2
    Panel B   (Pin 4)  → NodeMCU D3
    Panel L   (Pin 10) → NodeMCU D4   ← C address
    Panel F   (Pin 6)  → NodeMCU D5   ← CLK
    Panel S   (Pin 8)  → NodeMCU D8   ← STB
    Panel R   (Pin 12) → NodeMCU D7   ← DATA
    Any N pin          → NodeMCU GND + 5V supply GND
    5V supply (+)      → Panel VCC

  LIBRARY: ArduinoJson v6.x
*/

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#include <WiFiClient.h>

// ── WiFi & Server ─────────────────────────────────────────────────────
const char* WIFI_SSID   = "Kavz";
const char* WIFI_PASS   = "kavz_1318";
const char* SERVER_IP   = "172.16.50.85";
const int   SERVER_PORT = 8765;

// ── HUB12 Pins ────────────────────────────────────────────────────────
#define PIN_OE   D0
#define PIN_A    D1
#define PIN_B    D2
#define PIN_C    D3
#define PIN_CLK  D4
#define PIN_STB  D5
#define PIN_DATA D6

// ── Matrix: 16 rows × 32 cols, 1/8 scan ──────────────────────────────
#define ROWS          16
#define COLS          32
#define BYTES_PER_ROW  4
#define SCAN_LINES     8

byte fb[ROWS][BYTES_PER_ROW];

// ── 5×7 font — digits 0–9 and letters A–Z ────────────────────────────
// Each char = 7 rows, 5 cols. Bits 7–3 of each byte = 5 pixel columns.
const byte FONT5x7[][7] = {
  // 0–9
  {0b11111000,0b10001000,0b10001000,0b10001000,0b10001000,0b10001000,0b11111000}, // 0
  {0b00100000,0b01100000,0b00100000,0b00100000,0b00100000,0b00100000,0b01110000}, // 1
  {0b11111000,0b00001000,0b00001000,0b11111000,0b10000000,0b10000000,0b11111000}, // 2
  {0b11111000,0b00001000,0b00001000,0b11111000,0b00001000,0b00001000,0b11111000}, // 3
  {0b10001000,0b10001000,0b10001000,0b11111000,0b00001000,0b00001000,0b00001000}, // 4
  {0b11111000,0b10000000,0b10000000,0b11111000,0b00001000,0b00001000,0b11111000}, // 5
  {0b11111000,0b10000000,0b10000000,0b11111000,0b10001000,0b10001000,0b11111000}, // 6
  {0b11111000,0b00001000,0b00010000,0b00100000,0b01000000,0b01000000,0b01000000}, // 7
  {0b11111000,0b10001000,0b10001000,0b11111000,0b10001000,0b10001000,0b11111000}, // 8
  {0b11111000,0b10001000,0b10001000,0b11111000,0b00001000,0b00001000,0b11111000}, // 9
  // A–Z (index 10–35)
  {0b01110000,0b10001000,0b10001000,0b11111000,0b10001000,0b10001000,0b10001000}, // A
  {0b11110000,0b10001000,0b10001000,0b11110000,0b10001000,0b10001000,0b11110000}, // B
  {0b01111000,0b10000000,0b10000000,0b10000000,0b10000000,0b10000000,0b01111000}, // C
  {0b11110000,0b10001000,0b10001000,0b10001000,0b10001000,0b10001000,0b11110000}, // D
  {0b11111000,0b10000000,0b10000000,0b11110000,0b10000000,0b10000000,0b11111000}, // E
  {0b11111000,0b10000000,0b10000000,0b11110000,0b10000000,0b10000000,0b10000000}, // F
  {0b01111000,0b10000000,0b10000000,0b10011000,0b10001000,0b10001000,0b01111000}, // G
  {0b10001000,0b10001000,0b10001000,0b11111000,0b10001000,0b10001000,0b10001000}, // H
  {0b11111000,0b00100000,0b00100000,0b00100000,0b00100000,0b00100000,0b11111000}, // I
  {0b11111000,0b00010000,0b00010000,0b00010000,0b00010000,0b10010000,0b01100000}, // J
  {0b10001000,0b10010000,0b10100000,0b11000000,0b10100000,0b10010000,0b10001000}, // K
  {0b10000000,0b10000000,0b10000000,0b10000000,0b10000000,0b10000000,0b11111000}, // L
  {0b10001000,0b11011000,0b10101000,0b10101000,0b10001000,0b10001000,0b10001000}, // M
  {0b10001000,0b11001000,0b10101000,0b10011000,0b10001000,0b10001000,0b10001000}, // N
  {0b01110000,0b10001000,0b10001000,0b10001000,0b10001000,0b10001000,0b01110000}, // O
  {0b11110000,0b10001000,0b10001000,0b11110000,0b10000000,0b10000000,0b10000000}, // P
  {0b01110000,0b10001000,0b10001000,0b10001000,0b10101000,0b10010000,0b01101000}, // Q
  {0b11110000,0b10001000,0b10001000,0b11110000,0b10100000,0b10010000,0b10001000}, // R
  {0b01111000,0b10000000,0b10000000,0b01110000,0b00001000,0b00001000,0b11110000}, // S
  {0b11111000,0b00100000,0b00100000,0b00100000,0b00100000,0b00100000,0b00100000}, // T
  {0b10001000,0b10001000,0b10001000,0b10001000,0b10001000,0b10001000,0b01110000}, // U
  {0b10001000,0b10001000,0b10001000,0b10001000,0b10001000,0b01010000,0b00100000}, // V
  {0b10001000,0b10001000,0b10101000,0b10101000,0b10101000,0b11011000,0b10001000}, // W
  {0b10001000,0b10001000,0b01010000,0b00100000,0b01010000,0b10001000,0b10001000}, // X
  {0b10001000,0b10001000,0b01010000,0b00100000,0b00100000,0b00100000,0b00100000}, // Y
  {0b11111000,0b00001000,0b00010000,0b00100000,0b01000000,0b10000000,0b11111000}, // Z
  // special: colon (index 36), dot (37), space (38)
  {0b00000000,0b00100000,0b00100000,0b00000000,0b00100000,0b00100000,0b00000000}, // :
  {0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b01000000,0b01000000}, // .
  {0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000,0b00000000}, // space
};

// Convert char to FONT5x7 index
int charIndex(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'Z') return 10 + (c - 'A');
  if (c >= 'a' && c <= 'z') return 10 + (c - 'a');
  if (c == ':') return 36;
  if (c == '.') return 37;
  return 38; // space
}

// ── Game state ────────────────────────────────────────────────────────
char nameA[16] = "TEAM A";
char nameB[16] = "TEAM B";
int  scoreA=0, scoreB=0, clockSecs=0, clockTen=0, quarter=1;
bool running=false, gameOver=false;

// ── Display cycle ─────────────────────────────────────────────────────
// Screens: 0=NameA  1=ScoreA  2=NameB  3=ScoreB  4=Clock  5=Quarter
int  screen = 0;
unsigned long lastScreen = 0;
const int SCREEN_DURATION[] = {2500, 2500, 2500, 2500, 3000, 2000}; // ms each

// ── Timing ────────────────────────────────────────────────────────────
unsigned long lastFetch=0, lastPing=0;
WiFiClient wifiClient;

// ── Scan ──────────────────────────────────────────────────────────────
byte scanStep = 0;

// ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(PIN_OE,   OUTPUT);
  pinMode(PIN_A,    OUTPUT);
  pinMode(PIN_B,    OUTPUT);
  pinMode(PIN_C,    OUTPUT);
  pinMode(PIN_CLK,  OUTPUT);
  pinMode(PIN_STB,  OUTPUT);
  pinMode(PIN_DATA, OUTPUT);
  digitalWrite(PIN_OE, HIGH);

  Serial.println("\n========================================");
  Serial.println("  HIVE Basketball Scoreboard — NodeMCU");
  Serial.println("  Sri Ramakrishna Institute of Technology");
  Serial.println("========================================");

  // Boot flash
  for (int r=0; r<ROWS; r++)
    for (int b=0; b<BYTES_PER_ROW; b++) fb[r][b]=0xFF;
  for (int i=0; i<300; i++) { scanMatrix(); delay(1); }
  clearFB();

  connectWiFi();
}

// ─────────────────────────────────────────────────────────────────────
void loop() {
  scanMatrix();

  if (WiFi.status() != WL_CONNECTED) { connectWiFi(); return; }

  unsigned long now = millis();

  if (now - lastFetch >= 500)  { lastFetch=now; fetchState(); }
  if (now - lastPing  >= 2000) { lastPing=now;  sendPing(); }

  // Advance screen
  if (now - lastScreen >= (unsigned long)SCREEN_DURATION[screen]) {
    lastScreen = now;
    screen = (screen + 1) % 6;
    renderScreen();
  }
}

// ── Render current screen ─────────────────────────────────────────────
void renderScreen() {
  clearFB();
  char buf[12];

  switch (screen) {
    case 0: // Team A name
      drawTextCentered(nameA, 4);
      break;

    case 1: // Team A score — big 2-digit centred
      sprintf(buf, "%d", scoreA);
      drawTextCentered(buf, 4);
      break;

    case 2: // Team B name
      drawTextCentered(nameB, 4);
      break;

    case 3: // Team B score
      sprintf(buf, "%d", scoreB);
      drawTextCentered(buf, 4);
      break;

    case 4: // Clock
      if (clockSecs >= 60) {
        sprintf(buf, "%02d:%02d", clockSecs/60, clockSecs%60);
      } else {
        sprintf(buf, "%02d.%d", clockSecs, clockTen);
      }
      drawTextCentered(buf, 4);
      break;

    case 5: // Quarter
      if (quarter <= 4) sprintf(buf, "Q %d", quarter);
      else              sprintf(buf, "OT%d", quarter-4);
      drawTextCentered(buf, 4);
      break;
  }
}

// ── Draw text string centred horizontally on the panel ────────────────
// startRow = top row of text (5×7 font = 7 rows tall)
void drawTextCentered(const char* text, int startRow) {
  int len = strlen(text);
  // Total width: each char = 5 cols + 1 gap, minus trailing gap
  int totalWidth = len * 6 - 1;
  int startCol = (COLS - totalWidth) / 2;
  if (startCol < 0) startCol = 0;

  for (int i = 0; i < len; i++) {
    int col = startCol + i * 6;
    drawChar(text[i], startRow, col);
  }
}

// ── Draw a single 5×7 character ───────────────────────────────────────
void drawChar(char c, int row, int col) {
  int idx = charIndex(c);
  for (int r = 0; r < 7; r++) {
    byte px = (FONT5x7[idx][r] >> 3) & 0x1F;
    for (int b = 0; b < 5; b++)
      if (px & (1 << (4-b))) setPixel(row+r, col+b);
  }
}

// ── Set pixel ─────────────────────────────────────────────────────────
void setPixel(int row, int col) {
  if (row<0||row>=ROWS||col<0||col>=COLS) return;
  fb[row][col/8] |= (0x80 >> (col%8));
}

void clearFB() { memset(fb, 0, sizeof(fb)); }

// ── 1/8 scan matrix refresh ───────────────────────────────────────────
void scanMatrix() {
  static unsigned long t = 0;
  if (micros() - t < 1000) return;
  t = micros();

  digitalWrite(PIN_OE, HIGH);

  for (int b = 0; b < BYTES_PER_ROW; b++)
    shiftByte(~fb[scanStep][b]);
  for (int b = 0; b < BYTES_PER_ROW; b++)
    shiftByte(~fb[scanStep+8][b]);

  digitalWrite(PIN_STB, HIGH);
  delayMicroseconds(1);
  digitalWrite(PIN_STB, LOW);

  digitalWrite(PIN_A, (scanStep>>0)&1);
  digitalWrite(PIN_B, (scanStep>>1)&1);
  digitalWrite(PIN_C, (scanStep>>2)&1);

  digitalWrite(PIN_OE, LOW);
  scanStep = (scanStep+1) % SCAN_LINES;
}

inline void shiftByte(byte b) {
  for (int i=7; i>=0; i--) {
    digitalWrite(PIN_DATA, (b>>i)&1);
    digitalWrite(PIN_CLK, HIGH);
    delayMicroseconds(1);
    digitalWrite(PIN_CLK, LOW);
  }
}

// ── Fetch state ───────────────────────────────────────────────────────
void fetchState() {
  String url = String("http://")+SERVER_IP+":"+SERVER_PORT+"/state";
  HTTPClient http;
  http.begin(wifiClient, url);
  http.setTimeout(800);
  if (http.GET() != 200) { http.end(); return; }
  String body = http.getString();
  http.end();

  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, body)) return;

  scoreA    = doc["sa"]|0;
  scoreB    = doc["sb"]|0;
  clockSecs = doc["ci"]|0;
  clockTen  = doc["ct"]|0;
  quarter   = doc["q"] |1;
  running   = (doc["run"]==1);
  gameOver  = (doc["go"] ==1);

  const char* na = doc["na"]|"A";
  const char* nb = doc["nb"]|"B";
  strncpy(nameA, na, 15); nameA[15]='\0';
  strncpy(nameB, nb, 15); nameB[15]='\0';

  char ck[10];
  if (clockSecs>=60) sprintf(ck,"%02d:%02d",clockSecs/60,clockSecs%60);
  else               sprintf(ck,"%02d.%d",clockSecs,clockTen);
  Serial.printf("%-6s %2d | %2d %-6s  %s  Q%d  %s\n",
    nameA,scoreA,scoreB,nameB,ck,quarter,running?"RUN":"PAUSE");
}

// ── Heartbeat ─────────────────────────────────────────────────────────
void sendPing() {
  String url = String("http://")+SERVER_IP+":"+SERVER_PORT+"/ping";
  HTTPClient http;
  http.begin(wifiClient, url);
  http.addHeader("Content-Type","application/json");
  http.POST("{}");
  http.end();
}

// ── WiFi ──────────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.printf("Connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int tries=0;
  while (WiFi.status()!=WL_CONNECTED && tries<30) {
    scanMatrix(); delay(500);
    Serial.print("."); tries++;
  }
  if (WiFi.status()==WL_CONNECTED) {
    Serial.printf("\nConnected! IP: %s\n\n", WiFi.localIP().toString().c_str());
    renderScreen();
  } else {
    Serial.println("\nFailed — retrying...");
  }
}
