"""
NodeMCU WiFi Bridge Server
===========================
Run this on the PC (hotspot host) alongside the Streamlit app.
NodeMCU connects to your PC hotspot and talks to this server.

Install:  pip install flask
Run:      python nodemcu_server.py

Endpoints:
  GET  /state  → returns live game state as compact JSON
  POST /ping   → NodeMCU heartbeat (keeps "connected" status alive)
  GET  /ip     → shows your PC's hotspot IP (for setup)
"""

from flask import Flask, jsonify, request
import json, os, time, socket

app = Flask(__name__)

BASE_DIR    = os.path.dirname(__file__)
STATE_FILE  = os.path.join(BASE_DIR, "state.json")
STATUS_FILE = os.path.join(BASE_DIR, "nodemcu_status.json")

PORT = 8765   # NodeMCU will connect to http://<PC_IP>:8765


# ── Helpers ──────────────────────────────────────────────────
def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def write_status(data):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)


def read_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"last_ping": 0, "ip": ""}


def parse_clock(s):
    try:
        s = str(s)
        if ":" in s:
            parts = s.split(":")
            return int(parts[0]) * 60 + float(parts[1])
        return float(s)
    except Exception:
        return 0.0


# ── Routes ───────────────────────────────────────────────────
@app.route("/state", methods=["GET"])
def get_state():
    """Returns compact game state for NodeMCU to display."""
    s = load_state()
    clock = parse_clock(s.get("game_clock", "0"))
    clock_int    = int(clock)
    clock_tenths = int((clock % 1) * 10)
    return jsonify({
        "sa":  s.get("team_a", {}).get("score", 0),
        "sb":  s.get("team_b", {}).get("score", 0),
        "na":  s.get("team_a", {}).get("name", "A"),
        "nb":  s.get("team_b", {}).get("name", "B"),
        "ci":  clock_int,
        "ct":  clock_tenths,
        "q":   s.get("quarter", 1),
        "run": 1 if s.get("clock_running") else 0,
        "ot":  1 if s.get("overtime") else 0,
        "go":  1 if s.get("game_over") else 0,
        "pos": s.get("possession", "N"),
        "fa":  s.get("team_a", {}).get("fouls", 0),
        "fb":  s.get("team_b", {}).get("fouls", 0),
    })


@app.route("/ping", methods=["POST"])
def ping():
    """NodeMCU heartbeat — call every 2 seconds to stay 'connected'."""
    client_ip = request.remote_addr
    write_status({"last_ping": time.time(), "ip": client_ip})
    return jsonify({"ok": True})


@app.route("/ip", methods=["GET"])
def show_ip():
    """Returns PC hotspot IP — open this in browser during setup."""
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return jsonify({"pc_ip": ip, "port": PORT,
                    "url": f"http://{ip}:{PORT}/state"})


# ── Startup ──────────────────────────────────────────────────
if __name__ == "__main__":
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"

    print("=" * 55)
    print("  NodeMCU WiFi Bridge Server")
    print("=" * 55)
    print(f"  PC Hotspot IP : {ip}")
    print(f"  State URL     : http://{ip}:{PORT}/state")
    print(f"  Ping URL      : http://{ip}:{PORT}/ping")
    print()
    print("  >> Set this IP in your NodeMCU sketch:")
    print(f'     const char* SERVER_IP = "{ip}";')
    print("=" * 55)
    print()

    app.run(host="0.0.0.0", port=PORT, debug=False)
