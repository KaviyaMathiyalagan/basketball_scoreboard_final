"""
Arduino Serial Bridge
Reads state.json every 200ms and sends score/clock data to Arduino over USB serial.

Install dependency:  pip install pyserial

Usage:  python arduino_bridge.py
        python arduino_bridge.py --port COM5   (override COM port)
"""

import json, time, os, argparse, math
import serial, serial.tools.list_ports

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
BAUD_RATE  = 9600
INTERVAL   = 0.2   # seconds between updates


def find_arduino_port():
    """Auto-detect Arduino on any COM port."""
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if "arduino" in desc or "ch340" in desc or "cp210" in desc or "usb serial" in desc:
            return p.device
    # fallback: return first available COM port
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def parse_clock_seconds(clock_str):
    """Convert game_clock string ('MM:SS.t' or 'SS.t') → total seconds as float."""
    try:
        s = str(clock_str)
        if ":" in s:
            parts = s.split(":")
            return int(parts[0]) * 60 + float(parts[1])
        return float(s)
    except Exception:
        return 0.0


def build_packet(state):
    """
    Build a compact ASCII packet to send to Arduino.

    Format:  S,<score_a>,<score_b>,<clock_total_secs_int>,<clock_tenths>,<quarter>,<possession>\n
    Example: S,16,3,45,6,3,A\n

    Fields:
      score_a   : Team A score  (0-999)
      score_b   : Team B score  (0-999)
      clock_int : Whole seconds remaining
      tenths    : Tenths digit (0-9)
      quarter   : Current quarter (1-4, 5+=OT)
      poss      : Possession 'A', 'B', or 'N'
    """
    score_a = state.get("team_a", {}).get("score", 0)
    score_b = state.get("team_b", {}).get("score", 0)
    clock   = parse_clock_seconds(state.get("game_clock", "0"))
    quarter = state.get("quarter", 1)
    poss    = state.get("possession", "N") or "N"

    clock_int    = int(clock)
    clock_tenths = int((clock % 1) * 10)

    return f"S,{score_a},{score_b},{clock_int},{clock_tenths},{quarter},{poss}\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=None, help="COM port e.g. COM5")
    args = parser.parse_args()

    port = args.port or find_arduino_port()
    if not port:
        print("ERROR: No Arduino found. Connect Arduino via USB or specify --port COM5")
        return

    print(f"Connecting to Arduino on {port} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)   # wait for Arduino to reset after serial connect
        print(f"Connected. Streaming game state from {STATE_FILE}\n")
    except serial.SerialException as e:
        print(f"ERROR opening serial port: {e}")
        return

    last_packet = ""
    try:
        while True:
            state = load_state()
            if state:
                packet = build_packet(state)
                if packet != last_packet:           # only send when changed
                    ser.write(packet.encode("ascii"))
                    ser.flush()
                    print(f"→ {packet.strip()}")
                    last_packet = packet
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
