/*
  SIMPLE ON/OFF TEST — NodeMCU 16×32 HUB12
  ==========================================
  Every 3 seconds alternates ALL OFF → ALL ON
  Serial Monitor 115200 baud.

  If panel shows:
    ALL OFF then ALL ON → wiring is correct, inversion fixed
    ALL ON  always      → OE pin issue or address issue
    No change           → data not reaching panel
*/

#define PIN_OE   D0
#define PIN_A    D1
#define PIN_B    D2
#define PIN_C    D3
#define PIN_CLK  D4
#define PIN_STB  D5
#define PIN_DATA D6

#define SCAN_LINES     8
#define BYTES_PER_ROW  4

byte scanStep = 0;
bool allOn = false;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_OE,   OUTPUT);
  pinMode(PIN_A,    OUTPUT);
  pinMode(PIN_B,    OUTPUT);
  pinMode(PIN_C,    OUTPUT);
  pinMode(PIN_CLK,  OUTPUT);
  pinMode(PIN_STB,  OUTPUT);
  pinMode(PIN_DATA, OUTPUT);

  // Force OE HIGH immediately (disable output)
  digitalWrite(PIN_OE, HIGH);
  digitalWrite(PIN_STB, LOW);
  digitalWrite(PIN_CLK, LOW);

  Serial.println("Simple ON/OFF test");
  Serial.println("Watch panel — should alternate OFF and ON every 3 seconds");
}

void loop() {
  // Toggle every 3 seconds
  static unsigned long lastToggle = 0;
  if (millis() - lastToggle > 3000) {
    lastToggle = millis();
    allOn = !allOn;
    Serial.println(allOn ? "ALL ON" : "ALL OFF");
  }

  // Continuously scan all 8 row steps
  scanRow(allOn);
}

void scanRow(bool on) {
  static unsigned long t = 0;
  if (micros() - t < 1000) return;
  t = micros();

  digitalWrite(PIN_OE, HIGH);   // disable output while shifting

  // active-LOW panel:
  //   shift 0x00 = all LEDs ON
  //   shift 0xFF = all LEDs OFF
  byte val = on ? 0x00 : 0xFF;

  // Shift 8 bytes (4 bytes top row + 4 bytes bottom row)
  for (int b = 0; b < BYTES_PER_ROW; b++) shiftByte(val);
  for (int b = 0; b < BYTES_PER_ROW; b++) shiftByte(val);

  // Latch
  digitalWrite(PIN_STB, HIGH);
  delayMicroseconds(1);
  digitalWrite(PIN_STB, LOW);

  // Set row address
  digitalWrite(PIN_A, (scanStep >> 0) & 1);
  digitalWrite(PIN_B, (scanStep >> 1) & 1);
  digitalWrite(PIN_C, (scanStep >> 2) & 1);

  // Enable output
  digitalWrite(PIN_OE, LOW);

  scanStep = (scanStep + 1) % SCAN_LINES;
}

inline void shiftByte(byte b) {
  for (int i = 7; i >= 0; i--) {
    digitalWrite(PIN_DATA, (b >> i) & 1);
    digitalWrite(PIN_CLK, HIGH);
    delayMicroseconds(1);
    digitalWrite(PIN_CLK, LOW);
  }
}
