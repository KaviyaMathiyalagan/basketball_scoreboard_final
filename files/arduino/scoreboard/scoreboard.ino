/*
  Basketball Scoreboard — Arduino + 74HC595 + LED Dot Matrix
  ===========================================================
  Receives serial packets from arduino_bridge.py on the PC.

  PACKET FORMAT (sent from PC):
    S,<score_a>,<score_b>,<clock_int>,<clock_tenths>,<quarter>,<poss>\n
    Example: S,16,3,45,6,3,A

  HARDWARE SETUP:
  ─────────────────────────────────────────────────────────────
  Two 74HC595 ICs controlling one 8×8 LED matrix (common cathode rows):

    74HC595 #1 (ROW control) — shift reg U1
      QA-QH → Row 0–7 (via 220Ω resistors to LED matrix row pins)

    74HC595 #2 (COL control) — shift reg U2, QA = active LOW (common cathode)
      QA-QH → Col 0–7 (direct to LED matrix column pins)

  Daisy-chain: U2 DS ← U1 Q7'(overflow out)
               Or wire as two independent registers (see DATA_PIN2 below)

  Arduino pins:
    DATA_PIN  (DS)    → U1 pin 14  (SER / DS)
    CLK_PIN   (SHCP)  → U1 pin 11  (SRCLK)   also to U2 pin 11
    LATCH_PIN (STCP)  → U1 pin 12  (RCLK)    also to U2 pin 12
    DATA_PIN2 (DS2)   → U2 pin 14  (if NOT daisy-chained)

  ─────────────────────────────────────────────────────────────
  For chained (daisy-chain) setup:
    U1 Q7' (pin 9) → U2 DS (pin 14)
    Both share CLK and LATCH from Arduino
    Use shiftOut twice: first column byte, then row byte

  ─────────────────────────────────────────────────────────────
  This code uses a 3×5 pixel font to display 2 digits per row.
  Display layout on 8×8 matrix:
    Cols 0-2: digit 1 (tens)   Cols 4-6: digit 2 (units)
    Row 0-4: upper digit pair   Row 5-7: used for quarter / status
*/

// ── Pin definitions ──────────────────────────────────────────
#define DATA_PIN   8   // DS of first 74HC595
#define CLK_PIN    7   // SHCP (clock)
#define LATCH_PIN  6   // STCP (latch)
// If daisy-chained, U2 uses the same DATA/CLK/LATCH — no DATA_PIN2 needed
// If independent, uncomment:
// #define DATA_PIN2  9   // DS of second 74HC595 (column control)

// ── Display mode ──────────────────────────────────────────────
// Choose what to show on the 8×8 matrix by cycling every 2 seconds:
//   MODE 0 = Score A  (large 2-digit)
//   MODE 1 = Score B  (large 2-digit)
//   MODE 2 = Clock    (SS or MM:SS)
//   MODE 3 = Quarter  (Q1 / Q2 …)
#define CYCLE_MS 2000

// ── 3×5 font for digits 0-9 and letters Q,A,B ─────────────────
// Each digit = 5 bytes, each byte = 3 bits wide (bits 7,6,5 used)
// Bit 7 = leftmost pixel
const byte FONT3x5[][5] = {
  // 0
  {0b11100000, 0b10100000, 0b10100000, 0b10100000, 0b11100000},
  // 1
  {0b01000000, 0b11000000, 0b01000000, 0b01000000, 0b11100000},
  // 2
  {0b11100000, 0b00100000, 0b11100000, 0b10000000, 0b11100000},
  // 3
  {0b11100000, 0b00100000, 0b11100000, 0b00100000, 0b11100000},
  // 4
  {0b10100000, 0b10100000, 0b11100000, 0b00100000, 0b00100000},
  // 5
  {0b11100000, 0b10000000, 0b11100000, 0b00100000, 0b11100000},
  // 6
  {0b11100000, 0b10000000, 0b11100000, 0b10100000, 0b11100000},
  // 7
  {0b11100000, 0b00100000, 0b01000000, 0b01000000, 0b01000000},
  // 8
  {0b11100000, 0b10100000, 0b11100000, 0b10100000, 0b11100000},
  // 9
  {0b11100000, 0b10100000, 0b11100000, 0b00100000, 0b11100000},
};

// ── Game state ────────────────────────────────────────────────
int  scoreA    = 0;
int  scoreB    = 0;
int  clockSecs = 0;
int  clockTen  = 0;
int  quarter   = 1;
char poss      = 'N';

// ── Display buffer: 8 rows, each row = 8 bits (1 per col) ─────
byte frameBuffer[8];

// ── Timing ────────────────────────────────────────────────────
unsigned long lastCycle = 0;
int displayMode = 0;

// ────────────────────────────────────────────────────────────
void setup() {
  pinMode(DATA_PIN,  OUTPUT);
  pinMode(CLK_PIN,   OUTPUT);
  pinMode(LATCH_PIN, OUTPUT);
  Serial.begin(9600);
  clearBuffer();
  showNumber(0, 0);   // initial blank
}

// ────────────────────────────────────────────────────────────
void loop() {
  readSerial();
  cycleModes();
  scanMatrix();   // continuously refresh at ~500Hz (1ms per row × 8)
}

// ── Serial parsing ────────────────────────────────────────────
char serialBuf[64];
int  serialIdx = 0;

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      serialBuf[serialIdx] = '\0';
      parsePacket(serialBuf);
      serialIdx = 0;
    } else if (serialIdx < 63) {
      serialBuf[serialIdx++] = c;
    }
  }
}

void parsePacket(const char* buf) {
  // Format: S,scoreA,scoreB,clockInt,clockTenths,quarter,poss
  if (buf[0] != 'S') return;
  int sa, sb, ci, ct, q;
  char p;
  if (sscanf(buf, "S,%d,%d,%d,%d,%d,%c", &sa, &sb, &ci, &ct, &q, &p) == 6) {
    scoreA    = sa;
    scoreB    = sb;
    clockSecs = ci;
    clockTen  = ct;
    quarter   = q;
    poss      = p;
  }
}

// ── Cycle through display modes every CYCLE_MS ms ─────────────
void cycleModes() {
  if (millis() - lastCycle < CYCLE_MS) return;
  lastCycle = millis();
  displayMode = (displayMode + 1) % 4;
  renderMode();
}

void renderMode() {
  clearBuffer();
  switch (displayMode) {
    case 0: showNumber(scoreA, 0); break;   // Score A (rows 0-4)
    case 1: showNumber(scoreB, 0); break;   // Score B (rows 0-4)
    case 2: showClock();           break;   // Clock
    case 3: showQuarter();         break;   // Quarter
  }
}

// ── Draw a 2-digit number using 3×5 font ──────────────────────
// Digit 1 (tens) at cols 0-2, digit 2 (units) at cols 4-6
// rowOffset = starting row in framebuffer
void showNumber(int num, int rowOffset) {
  num = constrain(num, 0, 99);
  int tens  = num / 10;
  int units = num % 10;
  for (int r = 0; r < 5; r++) {
    byte tensCol  = (FONT3x5[tens][r]  >> 5) & 0x07;   // bits 7-5 → bits 2-0
    byte unitsCol = (FONT3x5[units][r] >> 5) & 0x07;
    // place tens at cols 0-2, units at cols 4-6
    frameBuffer[rowOffset + r] = (tensCol << 5) | (unitsCol << 1);
  }
}

// ── Show clock as SS (last minute) or MM:SS ───────────────────
void showClock() {
  if (clockSecs < 60) {
    // Show seconds (2 digits) in top half, tenths as a single pixel row
    showNumber(clockSecs, 0);
    // Bottom row: tenths indicator bar (n out of 8 pixels lit)
    frameBuffer[6] = (0xFF << (8 - clockTen)) & 0xFF;
  } else {
    int mins = clockSecs / 60;
    int secs = clockSecs % 60;
    // Mins on rows 0-4 (left digit pair), secs on rows (can't fit both)
    // Alternate: show MM on top half, SS on bottom half (scaled)
    showNumber(mins, 0);
    // Show seconds compactly in rows 5-7 using tiny 2×3 font (optional)
    // For simplicity: blink indicator in row 7 at 1Hz
    if ((millis() / 500) % 2) {
      frameBuffer[7] = 0b10000001;   // colon blink dots
    }
    // Overwrite bottom half with seconds
    // (rows 4-7 reused for secs — shift seconds display down)
    for (int r = 0; r < 4; r++) {
      int srcRow = r + 1;   // rows 1-4 of secs digit
      byte sR    = (FONT3x5[secs / 10][srcRow] >> 5) & 0x07;
      byte uR    = (FONT3x5[secs % 10][srcRow] >> 5) & 0x07;
      frameBuffer[4 + r] = (sR << 5) | (uR << 1);
    }
  }
}

// ── Show quarter Q1–Q4 / OT ───────────────────────────────────
void showQuarter() {
  // Display current quarter number large in center
  int q = constrain(quarter, 1, 9);
  showNumber(q, 1);   // center vertically a bit
}

// ── Clear display buffer ──────────────────────────────────────
void clearBuffer() {
  memset(frameBuffer, 0, sizeof(frameBuffer));
}

// ── Matrix scan: send one row at a time to 74HC595 ────────────
// Call this in loop() — handles its own 1ms timing per row
byte currentRow = 0;

void scanMatrix() {
  static unsigned long lastRowTime = 0;
  if (micros() - lastRowTime < 1000) return;   // 1ms per row = ~125Hz refresh
  lastRowTime = micros();

  // Row select: active HIGH on 74HC595 #1 (one-hot encoding)
  byte rowSel = (1 << currentRow);

  // Column data: active HIGH (common cathode: LOW = LED on, so invert)
  byte colData = ~frameBuffer[currentRow];

  // Latch LOW → shift out → Latch HIGH
  digitalWrite(LATCH_PIN, LOW);
  shiftOut(DATA_PIN, CLK_PIN, MSBFIRST, colData);   // U2 (columns) first in chain
  shiftOut(DATA_PIN, CLK_PIN, MSBFIRST, rowSel);    // U1 (rows) second
  digitalWrite(LATCH_PIN, HIGH);

  currentRow = (currentRow + 1) % 8;
}
