import streamlit as st
import json
import os
import time
from datetime import datetime

# ───── ADDED: PDF GENERATION ─────
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── ADDED: custom Flowable for jury signature block ──
from reportlab.platypus import Flowable as _Flowable

class JurySignature(_Flowable):
    """Draws a signature line + name + label + date, right-aligned on the page."""
    def __init__(self, name, date_str, line_w=6*cm):
        _Flowable.__init__(self)
        self.name     = name
        self.date_str = date_str
        self.line_w   = line_w
        self.width    = line_w
        self.height   = 1.8 * cm

    def draw(self):
        c = self.canv
        c.saveState()
        # Signature line
        c.setStrokeColor(colors.HexColor("#333333"))
        c.setLineWidth(0.8)
        c.line(0, 0.9 * cm, self.line_w, 0.9 * cm)
        # Jury name in italic above the line
        c.setFont("Helvetica-BoldOblique", 11)
        c.setFillColor(colors.HexColor("#1a1a4a"))
        c.drawRightString(self.line_w, 0.9 * cm + 0.35 * cm, self.name)
        # "Jury Signature" label below the line
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawRightString(self.line_w, 0.9 * cm - 0.45 * cm, "Jury Signature")
        # Date below the label
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#888888"))
        c.drawRightString(self.line_w, 0.9 * cm - 0.85 * cm, self.date_str)
        c.restoreState()
# ───── END ADDED ─────
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state.json")

# ───── ADDED: PDF GENERATION ─────
def generate_game_pdf(state):
    """
    Build a full game-history PDF from state and return the bytes.
    Returns None if there are no events.
    """
    events = state.get("events", [])
    # Events are stored newest-first; reverse for chronological order
    events_chrono = list(reversed(events))

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Basketball Game Report",
    )

    # ── Styles ──
    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#f5a623"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=base_styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#888888"),
        spaceAfter=14,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=base_styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#f5a623"),
        spaceBefore=14,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=base_styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#222222"),
        spaceAfter=3,
        leading=13,
    )
    info_label_style = ParagraphStyle(
        "InfoLabel",
        parent=base_styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Bold",
    )
    info_val_style = ParagraphStyle(
        "InfoVal",
        parent=base_styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#111111"),
    )
    event_style = ParagraphStyle(
        "Event",
        parent=base_styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#1a1a1a"),
        leading=12,
        spaceAfter=1,
    )
    no_events_style = ParagraphStyle(
        "NoEvents",
        parent=base_styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#cc4444"),
        alignment=TA_CENTER,
        spaceBefore=20,
        spaceAfter=20,
    )

    # ── Category colour map for event rows ──
    cat_bg = {
        "score":   colors.HexColor("#fff8e8"),
        "foul":    colors.HexColor("#fff0f0"),
        "timeout": colors.HexColor("#fffbe6"),
        "clock":   colors.HexColor("#f0f4ff"),
        "quarter": colors.HexColor("#f0fff4"),
    }

    # ── Collect game info ──
    jury_name   = state.get("jury_name", "N/A")
    ta          = state["team_a"]
    tb          = state["team_b"]
    game_date   = datetime.now().strftime("%d %B %Y")
    quarter     = state.get("quarter", 1)
    periods_played = min(quarter, 4)
    overtime    = quarter > 4
    ta_timeouts_used = 3 - ta.get("timeouts", 3)
    tb_timeouts_used = 3 - tb.get("timeouts", 3)

    # ── Build flowables ──
    story = []

    # Title
    story.append(Paragraph("BASKETBALL GAME REPORT", title_style))
    story.append(Paragraph(
        "Sri Ramakrishna Institute of Technology  |  Generated by HIVE",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor("#f5a623"), spaceAfter=12))

    # ── Game Info table ──
    story.append(Paragraph("Game Information", section_style))

    score_str = f"{ta['score']}  –  {tb['score']}"
    winner_str = (
        ta["name"] if ta["score"] > tb["score"]
        else (tb["name"] if tb["score"] > ta["score"] else "Draw")
    )
    ot_note = f" (+{quarter - 4} OT)" if overtime else ""

    info_data = [
        ["Jury",        jury_name,          "Date",          game_date],
        ["Team A",      ta["name"],          "Team B",        tb["name"]],
        ["Final Score", score_str,           "Winner",        winner_str],
        ["Periods",     f"{periods_played}{ot_note}", "Shot Clock", f"{state.get('shot_clock_option', 24)}s"],
        [f"{ta['name']} Fouls",  str(ta.get("fouls", 0)),
         f"{tb['name']} Fouls",  str(tb.get("fouls", 0))],
        [f"{ta['name']} TOs used", str(ta_timeouts_used),
         f"{tb['name']} TOs used", str(tb_timeouts_used)],
    ]

    info_table = Table(info_data, colWidths=[3.2*cm, 5.3*cm, 3.2*cm, 5.3*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ("BACKGROUND",  (2, 0), (2, -1), colors.HexColor("#f5f5f5")),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (0, -1), colors.HexColor("#555555")),
        ("TEXTCOLOR",   (2, 0), (2, -1), colors.HexColor("#555555")),
        ("TEXTCOLOR",   (1, 0), (1, -1), colors.HexColor("#111111")),
        ("TEXTCOLOR",   (3, 0), (3, -1), colors.HexColor("#111111")),
        ("BOX",         (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("INNERGRID",   (0, 0), (-1, -1), 0.3, colors.HexColor("#eeeeee")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # ── Event Timeline ──
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#dddddd"), spaceAfter=4))
    story.append(Paragraph("Full Event Timeline", section_style))

    if not events_chrono:
        story.append(Paragraph("No game history available to export.", no_events_style))
    else:
        # Table header
        ev_header = [
            Paragraph("<b>Period</b>", event_style),
            Paragraph("<b>Clock</b>",  event_style),
            Paragraph("<b>Category</b>", event_style),
            Paragraph("<b>Event</b>",  event_style),
        ]
        ev_rows = [ev_header]

        cat_label = {
            "score":   "Score",
            "foul":    "Foul",
            "timeout": "Timeout",
            "clock":   "Clock",
            "quarter": "Quarter",
        }

        row_colors = []   # track per-row background for TableStyle
        row_colors.append(colors.HexColor("#f5a623"))  # header row

        for ev in events_chrono:
            cat  = ev.get("cat", "clock")
            bg   = cat_bg.get(cat, colors.HexColor("#ffffff"))
            row_colors.append(bg)

            # Strip emojis - Helvetica cannot render unicode emoji, causes crash
            import re as _re
            msg = _re.sub(r'[^\x00-\x7F\u00C0-\u024F]+', '', ev.get("msg", "")).strip()

            ev_rows.append([
                Paragraph(ev.get("period", ""), event_style),
                Paragraph(ev.get("time",   ""), event_style),
                Paragraph(cat_label.get(cat, cat.capitalize()), event_style),
                Paragraph(msg, event_style),
            ])

        col_w = [1.4*cm, 2.0*cm, 2.0*cm, 11.6*cm]
        ev_table = Table(ev_rows, colWidths=col_w, repeatRows=1)

        # Build per-row background commands
        bg_cmds = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5a623")),
                   ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#000000")),
                   ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold")]
        for i, bg in enumerate(row_colors[1:], start=1):
            bg_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

        ev_table.setStyle(TableStyle(bg_cmds + [
            ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("INNERGRID",     (0, 0), (-1, -1), 0.2, colors.HexColor("#cccccc")),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
            # ROWBACKGROUNDS removed - per-row BACKGROUND cmds above handle colouring
        ]))
        story.append(ev_table)

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#dddddd"), spaceAfter=12))

    # ── ADDED: Jury signature block – right-aligned before footer ──
    _sig = JurySignature(jury_name, datetime.now().strftime("%d %B %Y"))
    _sig_table = Table(
        [[Paragraph("", base_styles["Normal"]), _sig]],
        colWidths=[17 * cm - 6 * cm, 6 * cm],
    )
    _sig_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(_sig_table)
    # ── END ADDED: Jury signature block ──

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}  |  "
        f"Jury: {jury_name}  |  HIVE - Sri Ramakrishna Institute of Technology",
        subtitle_style,
    ))

    # ── Page-number footer ──
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#aaaaaa"))
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buf.seek(0)
    return buf.read()
# ───── END ADDED: PDF GENERATION ─────

st.set_page_config(
    page_title="🏀 Basketball Jury Panel",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=Orbitron:wght@700;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit default header/toolbar */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }

.main { background: #0d0d0d; }
.block-container { padding: 0.5rem 2rem 1rem 2rem !important; max-width: 100% !important; }

/* Scoreboard */
.scoreboard {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 100%);
    border: 2px solid #f5a623;
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    margin-bottom: 1rem;
    box-shadow: 0 0 30px rgba(245,166,35,0.2);
}
.score-display {
    font-family: 'Orbitron', monospace;
    font-size: 4rem;
    font-weight: 900;
    color: #f5a623;
    letter-spacing: 0.1em;
    text-shadow: 0 0 20px rgba(245,166,35,0.5);
}
.team-name {
    font-size: 1.4rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
}
.clock-display {
    font-family: 'Orbitron', monospace;
    font-size: 3rem;
    font-weight: 900;
    color: #00ff88;
    text-shadow: 0 0 15px rgba(0,255,136,0.4);
}
.shot-clock {
    font-family: 'Orbitron', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: #ff4444;
    text-shadow: 0 0 10px rgba(255,68,68,0.4);
}
.quarter-badge {
    background: #f5a623;
    color: #000;
    font-weight: 900;
    font-size: 1rem;
    padding: 4px 16px;
    border-radius: 20px;
    display: inline-block;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* Section headers */
.section-header {
    background: linear-gradient(90deg, #1e3a5f, #0d0d0d);
    border-left: 4px solid #f5a623;
    color: #fff;
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 8px 16px;
    border-radius: 0 8px 8px 0;
    margin: 0.8rem 0 0.5rem 0;
}

/* Buttons */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    transition: all 0.15s ease !important;
    border: none !important;
}

/* Score buttons */
div[data-testid="column"] .stButton > button[kind="secondary"] {
    background: #1e3a5f !important;
    color: #fff !important;
}

.btn-score-1 > button { background: #2d5a27 !important; color: #fff !important; font-size: 1rem !important; }
.btn-score-2 > button { background: #1a5c8a !important; color: #fff !important; font-size: 1.1rem !important; }
.btn-score-3 > button { background: #7a3a0a !important; color: #fff !important; font-size: 1.2rem !important; }

.btn-foul > button { background: #8b1a1a !important; color: #fff !important; }
.btn-timeout > button { background: #4a3a00 !important; color: #ffd700 !important; }
.btn-undo > button { background: #333 !important; color: #aaa !important; }
.btn-danger > button { background: #6b0000 !important; color: #ff8888 !important; }
.btn-success > button { background: #1a5c1a !important; color: #88ff88 !important; }
.btn-clock > button { background: #1a3a1a !important; color: #00ff88 !important; font-size: 1.3rem !important; font-family: monospace !important; }

/* Status indicators */
.status-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
}
.status-running { background: #1a5c1a; color: #00ff88; }
.status-stopped { background: #5c1a1a; color: #ff8888; }
.status-possession { background: #1a3a5f; color: #88aaff; }

/* Foul dots */
.foul-dot {
    display: inline-block;
    width: 14px; height: 14px;
    border-radius: 50%;
    margin: 2px;
}
.foul-active { background: #ff4444; box-shadow: 0 0 6px #ff4444; }
.foul-inactive { background: #333; }

/* Event log */
.event-log {
    background: #0a0a0a;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 0.5rem;
    height: 220px;
    overflow-y: auto;
    font-size: 0.8rem;
    font-family: monospace;
}
.event-item { padding: 3px 6px; border-bottom: 1px solid #111; color: #ccc; }
.event-score { color: #f5a623; }
.event-foul { color: #ff8888; }
.event-timeout { color: #ffd700; }
.event-clock { color: #88aaff; }
.event-quarter { color: #00ff88; font-weight: bold; }

/* Stat box */
.stat-box {
    background: #111;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 0.6rem;
    text-align: center;
}
.stat-val { font-size: 1.6rem; font-weight: 900; color: #f5a623; font-family: 'Orbitron', monospace; }
.stat-lbl { font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 0.1em; }

/* Dark inputs */
.stNumberInput input, .stTextInput input, .stSelectbox select {
    background: #111 !important;
    color: #fff !important;
    border-color: #333 !important;
}
label { color: #ccc !important; font-size: 0.85rem !important; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #0a0a1a !important; }

/* Violations panel */
.violation-btn > button {
    background: #3a1a00 !important;
    color: #ffa040 !important;
    font-size: 0.8rem !important;
    padding: 6px !important;
}

/* ── FEATURE 1: Jury name badge ── */
.jury-badge {
    background: linear-gradient(90deg, #1a2a4a, #0d1a30);
    border: 1px solid #3a5a8a;
    border-radius: 8px;
    padding: 6px 14px;
    display: inline-block;
    font-size: 0.8rem;
    color: #88aaff;
    font-weight: 600;
    letter-spacing: 0.08em;
}

/* ── FEATURE 4: Break timer banner ── */
.break-banner {
    background: linear-gradient(135deg, #1a0a3a, #2a1a5a);
    border: 2px solid #aa88ff;
    border-radius: 16px;
    padding: 1.2rem;
    text-align: center;
    margin: 0.5rem 0 1rem 0;
    box-shadow: 0 0 25px rgba(170,136,255,0.25);
}
.break-timer {
    font-family: 'Orbitron', monospace;
    font-size: 2.5rem;
    font-weight: 900;
    color: #aa88ff;
    text-shadow: 0 0 15px rgba(170,136,255,0.5);
}

/* ── FEATURE 2: Shot clock selector ── */
.shot-selector button {
    background: #1a1a3a !important;
    border: 2px solid #3a3a6a !important;
    color: #aaaaff !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────
DEFAULT_STATE = {
    "team_a": {"name": "Team A", "score": 0, "fouls": 0, "timeouts": 3, "color": "#1a3a6b"},
    "team_b": {"name": "Team B", "score": 0, "fouls": 0, "timeouts": 3, "color": "#8b1a1a"},
    "quarter": 1, "game_clock": "10:00", "shot_clock": 24,
    "period_minutes": 10, "clock_running": False, "game_started": False,
    "game_over": False, "overtime": False, "possession": "A",
    "last_action": "", "events": [], "players_a": [], "players_b": [],
    "fouls_limit": 5, "team_fouls_limit": 10, "timeouts_per_half": 3,
    "shot_clock_reset": 24, "last_updated": 0,
    # ── FEATURE 1: jury name ──
    "jury_name": "",
    # ── FEATURE 2: shot clock selection ──
    "shot_clock_option": 24,
    # ── FEATURE 5: break timer ──
    "break_active": False,
    "break_seconds": 0,
    "break_label": "",
    "break_last_updated": 0,
}

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        state = dict(DEFAULT_STATE)
        state.update(data)
        if "team_a" not in data:
            state["team_a"] = dict(DEFAULT_STATE["team_a"])
        if "team_b" not in data:
            state["team_b"] = dict(DEFAULT_STATE["team_b"])
        return state
    except:
        return dict(DEFAULT_STATE)

def save_state(state):
    state["last_updated"] = time.time()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log_event(state, category, msg):
    q = state.get("quarter", 1)
    clock = state.get("game_clock", "--:--")
    label = f"Q{q}" if q <= 4 else f"OT{q-4}"
    entry = {"time": clock, "period": label, "msg": msg, "cat": category, "ts": time.time()}
    events = state.get("events", [])
    events.insert(0, entry)
    state["events"] = events[:100]

def parse_clock(s):
    try:
        s = str(s)
        if ":" in s:
            parts = s.split(":")
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(s)
    except:
        return 0.0

# ── FEATURE 4: format_clock updated – milliseconds only in last minute ──
def format_clock(seconds):
    seconds = max(0.0, float(seconds))
    if seconds <= 60.0:
        # Last minute or exactly 60s: show MM:SS.t (tenths), with MM as 00
        tenths = int((seconds % 1) * 10)
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}.{tenths}"
    else:
        # More than 1 minute: show MM:SS only (no tenths)
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"

# ─────────────────────────────────────────────
# ── FEATURE 1: Jury Name Gate ──
# Show a name-entry screen if jury_name is not yet set in session_state.
# We use session_state so the prompt only appears once per browser session
# even if state.json already has a name from a previous session.
# ─────────────────────────────────────────────
if "jury_name_entered" not in st.session_state:
    st.session_state["jury_name_entered"] = False

state = load_state()

if not st.session_state["jury_name_entered"]:
    st.markdown("""
    <div style='min-height:60vh; display:flex; flex-direction:column; align-items:center;
         justify-content:center; padding-top:6rem;'>
    <div style='font-family:Orbitron,monospace; font-size:2rem; font-weight:900; color:#f5a623;
         text-align:center; margin-bottom:2rem; text-shadow: 0 0 20px rgba(245,166,35,0.4);'>
      🏀 BASKETBALL JURY PANEL
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#aaa; font-size:1rem; margin-bottom:1.5rem;'>Please enter your name to continue</div>", unsafe_allow_html=True)

    col_c = st.columns([1, 2, 1])[1]
    with col_c:
        jury_input = st.text_input("Enter Jury Name", key="jury_name_field", placeholder="e.g. John Referee")
        if st.button("✅ Enter Jury Panel", use_container_width=True, key="jury_submit"):
            name = jury_input.strip()
            if name:
                state["jury_name"] = name
                save_state(state)
                st.session_state["jury_name_entered"] = True
                st.rerun()
            else:
                st.error("Please enter a name before continuing.")
    st.stop()

# ─────────────────────────────────────────────
# TICK CLOCK (time-based, runs on every page load)
# ─────────────────────────────────────────────

# ── FEATURE 5: Tick break timer if active ──
if state.get("break_active") and state.get("break_seconds", 0) > 0:
    elapsed = time.time() - state.get("break_last_updated", time.time())
    if elapsed > 0:
        new_break = max(0.0, state["break_seconds"] - elapsed)
        state["break_seconds"] = new_break
        state["break_last_updated"] = time.time()
        if new_break <= 0:
            state["break_active"] = False
            log_event(state, "quarter", f"Break ended – Ready for {state.get('break_label','next period')}")
        save_state(state)

if state.get("clock_running") and not state.get("game_over") and not state.get("break_active"):
    elapsed = time.time() - state.get("last_updated", time.time())
    if elapsed > 0:
        game_secs = parse_clock(state.get("game_clock", "00:00"))
        shot_secs = float(state.get("shot_clock", 24))
        game_secs = max(0.0, game_secs - elapsed)
        shot_secs = max(0.0, shot_secs - elapsed)
        state["game_clock"] = format_clock(game_secs)
        state["shot_clock"] = round(shot_secs, 1)
        if game_secs == 0.0:
            _q = state.get("quarter", 1)
            _lbl = f"QUARTER {_q}" if _q <= 4 else f"OVERTIME {_q-4}"
            state["clock_running"] = False
            log_event(state, "clock", f"End of {_lbl}")
        save_state(state)

# ─────────────────────────────────────────────
# Header  (FEATURE 1: jury name displayed here)
# ─────────────────────────────────────────────
jury_name = state.get("jury_name", "")
jury_badge_html = f'<span class="jury-badge">👤 Jury: {jury_name}</span>' if jury_name else ""

st.markdown(f"""
<div style='text-align:center; padding: 0.5rem 0 0.2rem 0;'>
  <span style='font-family:Orbitron,monospace; font-size:1.8rem; font-weight:900; color:#f5a623;
    letter-spacing:0.15em; text-shadow: 0 0 20px rgba(245,166,35,0.4);'>
    🏀 BASKETBALL JURY CONTROL PANEL
  </span><br>
  <span style='color:#666; font-size:0.78rem; letter-spacing:0.2em; text-transform:uppercase;'>
    Official Scorekeeping &amp; Game Management System
  </span>
  <br><div style='margin-top:6px;'>{jury_badge_html}</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ── FEATURE 5: Break Timer Banner (shown at top when break is active) ──
# ─────────────────────────────────────────────
if state.get("break_active") and state.get("break_seconds", 0) > 0:
    bsecs = state["break_seconds"]
    bm = int(bsecs) // 60
    bs = int(bsecs) % 60
    bt = int((bsecs % 1) * 10)
    bdisp = f"{bm}:{bs:02d}.{bt}"
    blabel = state.get("break_label", "Break")
    st.markdown(f"""
    <div class="break-banner">
      <div style='font-size:1rem; font-weight:700; color:#cc88ff; letter-spacing:0.15em;
           text-transform:uppercase; margin-bottom:4px;'>⏳ {blabel}</div>
      <div class="break-timer">{bdisp} Remaining</div>
      <div style='color:#888; font-size:0.78rem; margin-top:6px;'>
        Next quarter will be available once the break ends</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOP SCOREBOARD
# ─────────────────────────────────────────────
q = state.get("quarter", 1)
period_label = f"QUARTER {q}" if q <= 4 else f"OVERTIME {q-4}"
running_html = '<span class="status-pill status-running">⏱ CLOCK RUNNING</span>' if state.get("clock_running") else '<span class="status-pill status-stopped">⏹ CLOCK STOPPED</span>'
poss = state.get("possession", "A")
poss_name = state["team_a"]["name"] if poss == "A" else state["team_b"]["name"]

col_left, col_mid, col_right = st.columns([2, 1.4, 2])

with col_left:
    st.markdown(f"""
    <div class="scoreboard" style="border-color:#1a3a6b;">
      <div class="team-name" style="color:#6699ff;">{state['team_a']['name']}</div>
      <div class="score-display">{state['team_a']['score']}</div>
      <div style="margin-top:8px; font-size:0.8rem; color:#888;">
        {'🟡 ' * state['team_a']['fouls']}<span style="color:#888;">Fouls: {state['team_a']['fouls']}</span>
        &nbsp;|&nbsp;
        <span style="color:#ffd700;">⏸ TOs: {state['team_a']['timeouts']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_mid:
    st.markdown(f"""
    <div class="scoreboard" style="padding:1rem;">
      <div><span class="quarter-badge">{period_label}</span></div>
      <div class="clock-display" style="margin: 0.5rem 0;">{state.get('game_clock','10:00')}</div>
      <div class="shot-clock">SHOT: {int(state.get('shot_clock',24))}s</div>
      <div style="margin-top:8px;">{running_html}</div>
      <div style="margin-top:6px;"><span class="status-pill status-possession">🏀 {poss_name}</span></div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown(f"""
    <div class="scoreboard" style="border-color:#8b1a1a;">
      <div class="team-name" style="color:#ff8888;">{state['team_b']['name']}</div>
      <div class="score-display">{state['team_b']['score']}</div>
      <div style="margin-top:8px; font-size:0.8rem; color:#888;">
        {'🟡 ' * state['team_b']['fouls']}<span style="color:#888;">Fouls: {state['team_b']['fouls']}</span>
        &nbsp;|&nbsp;
        <span style="color:#ffd700;">⏸ TOs: {state['team_b']['timeouts']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
# MAIN CONTROL AREA
# ─────────────────────────────────────────────
main_col, right_panel = st.columns([3, 1.2])

with main_col:

    # ── CLOCK CONTROLS ──
    st.markdown('<div class="section-header">⏱ GAME CLOCK & PERIOD CONTROLS</div>', unsafe_allow_html=True)
    cc1, cc2, cc3, cc4, cc5 = st.columns(5)

    with cc1:
        if state.get("clock_running"):
            if st.button("⏸ PAUSE", use_container_width=True, key="pause"):
                state["clock_running"] = False
                log_event(state, "clock", f"Clock paused at {state['game_clock']}")
                save_state(state)
                st.rerun()
        else:
            if st.button("▶ START", use_container_width=True, key="start"):
                if not state.get("break_active"):
                    state["clock_running"] = True
                    state["game_started"] = True
                    log_event(state, "clock", f"Clock started at {state['game_clock']}")
                    save_state(state)
                    st.rerun()
                else:
                    st.warning("Break timer still running!")

    with cc2:
        # ── FEATURE 5: Next Period now starts break timer ──
        break_blocked = state.get("break_active", False)
        btn_label = "⏳ BREAK ACTIVE" if break_blocked else "⏭ NEXT PERIOD"
        if st.button(btn_label, use_container_width=True, key="next_q", disabled=break_blocked):
            q = state.get("quarter", 1)
            if q < 4:
                # Start break before next quarter
                if q == 2:
                    break_secs = 10 * 60  # halftime
                    blabel = "Halftime Break – 10:00"
                else:
                    break_secs = 2 * 60   # quarter break
                    blabel = f"Quarter {q} Break – 2:00"
                state["break_active"] = True
                state["break_seconds"] = float(break_secs)
                state["break_label"] = blabel
                state["break_last_updated"] = time.time()
                state["quarter"] = q + 1
                state["game_clock"] = format_clock(state.get("period_minutes", 10) * 60)
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["clock_running"] = False
                state["team_a"]["timeouts"] = state.get("timeouts_per_half", 3) if q == 2 else state["team_a"]["timeouts"]
                state["team_b"]["timeouts"] = state.get("timeouts_per_half", 3) if q == 2 else state["team_b"]["timeouts"]
                log_event(state, "quarter", f"Q{q+1} queued – {blabel} started")
            elif q == 4:
                if state["team_a"]["score"] == state["team_b"]["score"]:
                    state["quarter"] = 5
                    state["game_clock"] = "05:00"
                    state["clock_running"] = False
                    log_event(state, "quarter", "OVERTIME begins!")
                else:
                    state["game_over"] = True
                    log_event(state, "quarter", "GAME OVER!")
            else:
                state["game_over"] = True
                log_event(state, "quarter", "GAME OVER!")
            save_state(state)
            st.rerun()

    with cc3:
        if st.button("🔄 RESET SHOT CLK", use_container_width=True, key="reset_shot"):
            # ── FEATURE 2: reset to selected option, not always 24 ──
            reset_val = state.get("shot_clock_option", 24)
            state["shot_clock"] = reset_val
            log_event(state, "clock", f"Shot clock reset to {reset_val}s")
            save_state(state)
            st.rerun()

    with cc4:
        if st.button("↩ RESET PERIOD", use_container_width=True, key="reset_period"):
            mins = state.get("period_minutes", 10)
            state["game_clock"] = format_clock(mins * 60)
            state["clock_running"] = False
            save_state(state)
            st.rerun()

    with cc5:
        if st.button("⚠️ RESET GAME", use_container_width=True, key="reset_game"):
            if st.session_state.get("confirm_reset"):
                mins = state.get("period_minutes", 10)
                ta_name = state["team_a"]["name"]
                tb_name = state["team_b"]["name"]
                jury_n = state.get("jury_name", "")
                state["team_a"] = {"name": ta_name, "score": 0, "fouls": 0, "timeouts": 3, "color": "#1a3a6b"}
                state["team_b"] = {"name": tb_name, "score": 0, "fouls": 0, "timeouts": 3, "color": "#8b1a1a"}
                state["quarter"] = 1
                state["game_clock"] = format_clock(mins * 60)
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["clock_running"] = False
                state["game_started"] = False
                state["game_over"] = False
                state["events"] = []
                state["possession"] = "A"
                # ── FEATURE 5: clear break on reset ──
                state["break_active"] = False
                state["break_seconds"] = 0
                state["break_label"] = ""
                state["jury_name"] = jury_n  # preserve jury name
                log_event(state, "quarter", "Game RESET by jury")
                st.session_state["confirm_reset"] = False
                save_state(state)
                st.rerun()
            else:
                st.session_state["confirm_reset"] = True
                st.warning("Click again to confirm game reset!")

    # ── FEATURE 3: Manual Time Adjustment buttons ──
    st.markdown('<div class="section-header">🕐 MANUAL TIME ADJUSTMENT</div>', unsafe_allow_html=True)
    adj_c1, adj_c2, adj_c3, adj_c4 = st.columns(4)
    with adj_c1:
        if st.button("➕ +1 Second", use_container_width=True, key="plus_1s"):
            secs = parse_clock(state.get("game_clock", "00:00"))
            max_secs = state.get("period_minutes", 10) * 60
            secs = min(max_secs, secs + 1)
            state["game_clock"] = format_clock(secs)
            log_event(state, "clock", f"Clock +1s → {state['game_clock']}")
            save_state(state); st.rerun()
    with adj_c2:
        if st.button("➖ -1 Second", use_container_width=True, key="minus_1s"):
            secs = parse_clock(state.get("game_clock", "00:00"))
            secs = max(0, secs - 1)
            state["game_clock"] = format_clock(secs)
            log_event(state, "clock", f"Clock -1s → {state['game_clock']}")
            save_state(state); st.rerun()
    with adj_c3:
        if st.button("➕ +1 Minute", use_container_width=True, key="plus_1m"):
            secs = parse_clock(state.get("game_clock", "00:00"))
            max_secs = state.get("period_minutes", 10) * 60
            secs = min(max_secs, secs + 60)
            state["game_clock"] = format_clock(secs)
            log_event(state, "clock", f"Clock +1m → {state['game_clock']}")
            save_state(state); st.rerun()
    with adj_c4:
        if st.button("➖ -1 Minute", use_container_width=True, key="minus_1m"):
            secs = parse_clock(state.get("game_clock", "00:00"))
            secs = max(0, secs - 60)
            state["game_clock"] = format_clock(secs)
            log_event(state, "clock", f"Clock -1m → {state['game_clock']}")
            save_state(state); st.rerun()

    # Manual clock adjustment (expander – unchanged)
    with st.expander("🕐 Manual Clock Adjustment (Fine Tune)", expanded=False):
        adj1, adj2, adj3 = st.columns(3)
        with adj1:
            new_clock = st.text_input("Set Game Clock (MM:SS)", value=state.get("game_clock","10:00"), key="manual_clock")
        with adj2:
            new_shot = st.number_input("Set Shot Clock (s)", min_value=0, max_value=24, value=int(state.get("shot_clock", 24)), key="manual_shot")
        with adj3:
            st.write("")
            st.write("")
            if st.button("✅ Apply Clock", use_container_width=True, key="apply_clock"):
                state["game_clock"] = new_clock
                state["shot_clock"] = int(new_shot)
                log_event(state, "clock", f"Clock manually set to {new_clock}, shot={new_shot}s")
                save_state(state)
                st.rerun()

    # ── FEATURE 2: Shot Clock Selection (14s / 24s) ──
    st.markdown('<div class="section-header">⏳ SHOT CLOCK SELECTION</div>', unsafe_allow_html=True)
    sc_opt_col1, sc_opt_col2, sc_opt_col3 = st.columns([1, 1, 2])
    current_sc_opt = state.get("shot_clock_option", 24)
    with sc_opt_col1:
        sc_14_style = "background:#3a1a5a !important; border:2px solid #aa88ff !important; color:#aa88ff !important;" if current_sc_opt == 14 else ""
        if st.button("⏳ 14 Seconds", use_container_width=True, key="sc_14"):
            state["shot_clock_option"] = 14
            state["shot_clock"] = 14
            log_event(state, "clock", "Shot clock set to 14s mode")
            save_state(state); st.rerun()
    with sc_opt_col2:
        if st.button("⏳ 24 Seconds", use_container_width=True, key="sc_24"):
            state["shot_clock_option"] = 24
            state["shot_clock"] = 24
            log_event(state, "clock", "Shot clock set to 24s mode")
            save_state(state); st.rerun()
    with sc_opt_col3:
        selected_label = f"✅ Selected: {current_sc_opt}s shot clock"
        sc_color = "#aa88ff" if current_sc_opt == 14 else "#f5a623"
        st.markdown(f"<div style='padding:10px; color:{sc_color}; font-weight:700; font-size:0.9rem;'>{selected_label}</div>", unsafe_allow_html=True)

    # ── FEATURE 5: Manual break timer controls ──
    with st.expander("⏳ Break Timer Controls", expanded=False):
        bk1, bk2, bk3 = st.columns(3)
        with bk1:
            if st.button("⏸ Skip Break", use_container_width=True, key="skip_break"):
                state["break_active"] = False
                state["break_seconds"] = 0
                log_event(state, "quarter", "Break skipped by jury")
                save_state(state); st.rerun()
        with bk2:
            if st.button("🔁 Add 2min Break", use_container_width=True, key="add_2m_break"):
                state["break_active"] = True
                state["break_seconds"] = 2 * 60
                state["break_label"] = "Extra Break – 2:00"
                state["break_last_updated"] = time.time()
                log_event(state, "quarter", "2-minute break added manually")
                save_state(state); st.rerun()
        with bk3:
            if st.button("🔁 Add 10min Halftime", use_container_width=True, key="add_10m_break"):
                state["break_active"] = True
                state["break_seconds"] = 10 * 60
                state["break_label"] = "Halftime Break – 10:00"
                state["break_last_updated"] = time.time()
                log_event(state, "quarter", "10-minute halftime added manually")
                save_state(state); st.rerun()

    # ── SCORING ──
    st.markdown('<div class="section-header">🏀 SCORING</div>', unsafe_allow_html=True)

    scol1, scol2 = st.columns(2)

    with scol1:
        st.markdown(f"<div style='color:#6699ff; font-weight:700; text-align:center; font-size:1rem; margin-bottom:6px;'>▲ {state['team_a']['name']}</div>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            if st.button("➕1 pt", use_container_width=True, key="a1"):
                state["team_a"]["score"] += 1
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["possession"] = "B"
                log_event(state, "score", f"🔵 {state['team_a']['name']} +1 (FT) → {state['team_a']['score']}")
                save_state(state); st.rerun()
        with sc2:
            if st.button("➕2 pt", use_container_width=True, key="a2"):
                state["team_a"]["score"] += 2
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["possession"] = "B"
                log_event(state, "score", f"🔵 {state['team_a']['name']} +2 → {state['team_a']['score']}")
                save_state(state); st.rerun()
        with sc3:
            if st.button("➕3 pt", use_container_width=True, key="a3"):
                state["team_a"]["score"] += 3
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["possession"] = "B"
                log_event(state, "score", f"🔵 {state['team_a']['name']} +3 → {state['team_a']['score']}")
                save_state(state); st.rerun()
        with sc4:
            if st.button("➖1", use_container_width=True, key="am1"):
                if state["team_a"]["score"] > 0:
                    state["team_a"]["score"] -= 1
                    log_event(state, "score", f"⚠️ {state['team_a']['name']} score corrected -{1}")
                    save_state(state); st.rerun()

    with scol2:
        st.markdown(f"<div style='color:#ff8888; font-weight:700; text-align:center; font-size:1rem; margin-bottom:6px;'>▲ {state['team_b']['name']}</div>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            if st.button("➕1 pt", use_container_width=True, key="b1"):
                state["team_b"]["score"] += 1
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["possession"] = "A"
                log_event(state, "score", f"🔴 {state['team_b']['name']} +1 (FT) → {state['team_b']['score']}")
                save_state(state); st.rerun()
        with sc2:
            if st.button("➕2 pt", use_container_width=True, key="b2"):
                state["team_b"]["score"] += 2
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["possession"] = "A"
                log_event(state, "score", f"🔴 {state['team_b']['name']} +2 → {state['team_b']['score']}")
                save_state(state); st.rerun()
        with sc3:
            if st.button("➕3 pt", use_container_width=True, key="b3"):
                state["team_b"]["score"] += 3
                state["shot_clock"] = state.get("shot_clock_option", 24)
                state["possession"] = "A"
                log_event(state, "score", f"🔴 {state['team_b']['name']} +3 → {state['team_b']['score']}")
                save_state(state); st.rerun()
        with sc4:
            if st.button("➖1", use_container_width=True, key="bm1"):
                if state["team_b"]["score"] > 0:
                    state["team_b"]["score"] -= 1
                    log_event(state, "score", f"⚠️ {state['team_b']['name']} score corrected -1")
                    save_state(state); st.rerun()

    # ── FOULS & TIMEOUTS ──
    st.markdown('<div class="section-header">🟡 FOULS & TIMEOUTS</div>', unsafe_allow_html=True)

    ft1, ft2 = st.columns(2)

    with ft1:
        st.markdown(f"<div style='color:#6699ff; font-size:0.85rem; font-weight:600; margin-bottom:4px;'>{state['team_a']['name']}</div>", unsafe_allow_html=True)
        fa1, fa2 = st.columns(2)
        with fa1:
            if st.button(f"🟡 Add Foul", use_container_width=True, key="af"):
                f = state["team_a"]["fouls"]
                if f < 5:
                    state["team_a"]["fouls"] += 1
                    if state["team_a"]["fouls"] >= 5:
                        log_event(state, "foul", f"⚠️ {state['team_a']['name']} player FOULED OUT ({state['team_a']['fouls']} fouls)")
                    else:
                        log_event(state, "foul", f"🟡 {state['team_a']['name']} foul #{state['team_a']['fouls']}")
                    save_state(state); st.rerun()
                else:
                    st.warning("Max fouls reached!")
            if st.button("↩ Remove Foul", use_container_width=True, key="afr"):
                if state["team_a"]["fouls"] > 0:
                    state["team_a"]["fouls"] -= 1
                    log_event(state, "foul", f"↩ {state['team_a']['name']} foul corrected")
                    save_state(state); st.rerun()
        with fa2:
            if st.button("⏸ USE TIMEOUT", use_container_width=True, key="ato"):
                if state["team_a"]["timeouts"] > 0:
                    state["team_a"]["timeouts"] -= 1
                    state["clock_running"] = False
                    log_event(state, "timeout", f"⏸ {state['team_a']['name']} timeout called ({state['team_a']['timeouts']} left)")
                    save_state(state); st.rerun()
                else:
                    st.error("No timeouts remaining!")
            if st.button("➕ Add Timeout", use_container_width=True, key="atoa"):
                state["team_a"]["timeouts"] = min(3, state["team_a"]["timeouts"] + 1)
                save_state(state); st.rerun()

    with ft2:
        st.markdown(f"<div style='color:#ff8888; font-size:0.85rem; font-weight:600; margin-bottom:4px;'>{state['team_b']['name']}</div>", unsafe_allow_html=True)
        fb1, fb2 = st.columns(2)
        with fb1:
            if st.button(f"🟡 Add Foul", use_container_width=True, key="bf"):
                f = state["team_b"]["fouls"]
                if f < 5:
                    state["team_b"]["fouls"] += 1
                    if state["team_b"]["fouls"] >= 5:
                        log_event(state, "foul", f"⚠️ {state['team_b']['name']} player FOULED OUT ({state['team_b']['fouls']} fouls)")
                    else:
                        log_event(state, "foul", f"🟡 {state['team_b']['name']} foul #{state['team_b']['fouls']}")
                    save_state(state); st.rerun()
                else:
                    st.warning("Max fouls reached!")
            if st.button("↩ Remove Foul", use_container_width=True, key="bfr"):
                if state["team_b"]["fouls"] > 0:
                    state["team_b"]["fouls"] -= 1
                    log_event(state, "foul", f"↩ {state['team_b']['name']} foul corrected")
                    save_state(state); st.rerun()
        with fb2:
            if st.button("⏸ USE TIMEOUT", use_container_width=True, key="bto"):
                if state["team_b"]["timeouts"] > 0:
                    state["team_b"]["timeouts"] -= 1
                    state["clock_running"] = False
                    log_event(state, "timeout", f"⏸ {state['team_b']['name']} timeout called ({state['team_b']['timeouts']} left)")
                    save_state(state); st.rerun()
                else:
                    st.error("No timeouts remaining!")
            if st.button("➕ Add Timeout", use_container_width=True, key="btoa"):
                state["team_b"]["timeouts"] = min(3, state["team_b"]["timeouts"] + 1)
                save_state(state); st.rerun()

    # ── VIOLATIONS ──
    st.markdown('<div class="section-header">🚫 VIOLATIONS & RULE ENFORCEMENT</div>', unsafe_allow_html=True)

    violations = [
        ("🏃 Traveling", "traveling"),
        ("🔢 Double Dribble", "double_dribble"),
        ("3-sec Lane", "3sec_lane"),
        ("5-sec Inbound", "5sec_inbound"),
        ("8-sec Half", "8sec_half"),
        ("24-sec Shot", "24sec_shot"),
        ("🔄 Ball OOB", "oob"),
        ("🔙 Backcourt", "backcourt"),
        ("🤝 Held Ball", "held_ball"),
        ("🦶 Kicking", "kicking"),
    ]

    team_for_violation = st.selectbox("Violation charged to:", [state["team_a"]["name"], state["team_b"]["name"]], key="viol_team")
    vcols = st.columns(5)
    for idx, (label, key) in enumerate(violations):
        with vcols[idx % 5]:
            if st.button(label, use_container_width=True, key=f"viol_{key}"):
                state["clock_running"] = False
                opp = "B" if team_for_violation == state["team_a"]["name"] else "A"
                state["possession"] = opp
                log_event(state, "foul", f"🚫 {team_for_violation}: {label.replace('🏃','').replace('🔢','').replace('🔄','').replace('🔙','').replace('🤝','').replace('🦶','').strip()} violation")
                save_state(state); st.rerun()

    # ── POSSESSION ──
    st.markdown('<div class="section-header">🏀 POSSESSION & GAME EVENTS</div>', unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        if st.button(f"🏀 Poss → {state['team_a']['name']}", use_container_width=True, key="poss_a"):
            state["possession"] = "A"
            log_event(state, "clock", f"Possession: {state['team_a']['name']}")
            save_state(state); st.rerun()
    with p2:
        if st.button(f"🏀 Poss → {state['team_b']['name']}", use_container_width=True, key="poss_b"):
            state["possession"] = "B"
            log_event(state, "clock", f"Possession: {state['team_b']['name']}")
            save_state(state); st.rerun()
    with p3:
        if st.button("🎽 JUMP BALL", use_container_width=True, key="jumpball"):
            state["clock_running"] = False
            log_event(state, "clock", "Jump ball called")
            save_state(state); st.rerun()
    with p4:
        if st.button("📢 TECHNICAL FOUL", use_container_width=True, key="tech"):
            tf_team = st.session_state.get("tf_team", state["team_a"]["name"])
            log_event(state, "foul", f"🔴 TECHNICAL FOUL assessed")
            save_state(state); st.rerun()

    # ── FREE THROWS ──
    with st.expander("🎯 Free Throw Management", expanded=False):
        ft_team = st.selectbox("Shooting team:", [state["team_a"]["name"], state["team_b"]["name"]], key="ft_team")
        ft_num = st.selectbox("Free throws awarded:", [1, 2, 3], key="ft_num")
        ft_made = st.number_input("Free throws made:", min_value=0, max_value=3, value=0, key="ft_made")
        if st.button("✅ Record Free Throws", use_container_width=True, key="ft_record"):
            team_key = "team_a" if ft_team == state["team_a"]["name"] else "team_b"
            state[team_key]["score"] += int(ft_made)
            opp = "B" if team_key == "team_a" else "A"
            state["possession"] = opp
            state["shot_clock"] = state.get("shot_clock_option", 24)
            log_event(state, "score", f"🎯 {ft_team} FT: {ft_made}/{ft_num} → {state[team_key]['score']}")
            save_state(state); st.rerun()

# ─────────────────────────────────────────────
# RIGHT PANEL
# ─────────────────────────────────────────────
with right_panel:

    # ── SETUP ──
    with st.expander("⚙️ GAME SETUP", expanded=True):
        ta_name = st.text_input("Team A Name", value=state["team_a"]["name"], key="ta_name_input")
        tb_name = st.text_input("Team B Name", value=state["team_b"]["name"], key="tb_name_input")
        period_mins = st.selectbox("Period Length", [5, 8, 10, 12, 15, 20], index=2, key="period_mins")
        # ── FEATURE 1: allow jury to update their name here too ──
        new_jury_name = st.text_input("Jury Name", value=state.get("jury_name", ""), key="jury_name_update")
        if st.button("✅ Apply Setup", use_container_width=True, key="apply_setup"):
            state["team_a"]["name"] = ta_name
            state["team_b"]["name"] = tb_name
            state["period_minutes"] = int(period_mins)
            state["game_clock"] = format_clock(int(period_mins) * 60)
            if new_jury_name.strip():
                state["jury_name"] = new_jury_name.strip()
            log_event(state, "clock", f"Setup: {ta_name} vs {tb_name}, {period_mins}min periods")
            save_state(state); st.rerun()

    # ── QUICK STATS ──
    st.markdown('<div class="section-header" style="font-size:0.75rem;">📊 QUICK STATS</div>', unsafe_allow_html=True)

    diff = state["team_a"]["score"] - state["team_b"]["score"]
    diff_str = f"+{diff}" if diff > 0 else str(diff)
    diff_col = "#00ff88" if diff > 0 else ("#ff4444" if diff < 0 else "#888")

    st.markdown(f"""
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:6px 0;">
      <div class="stat-box"><div class="stat-val">{state['team_a']['score']}</div><div class="stat-lbl">{state['team_a']['name'][:8]}</div></div>
      <div class="stat-box"><div class="stat-val">{state['team_b']['score']}</div><div class="stat-lbl">{state['team_b']['name'][:8]}</div></div>
      <div class="stat-box"><div class="stat-val" style="color:{diff_col};">{diff_str}</div><div class="stat-lbl">Margin</div></div>
      <div class="stat-box"><div class="stat-val" style="color:#88aaff;">{state.get('quarter',1)}</div><div class="stat-lbl">Period</div></div>
      <div class="stat-box"><div class="stat-val" style="color:#ff8888;">{state['team_a']['fouls']}</div><div class="stat-lbl">{state['team_a']['name'][:6]} Fouls</div></div>
      <div class="stat-box"><div class="stat-val" style="color:#ff8888;">{state['team_b']['fouls']}</div><div class="stat-lbl">{state['team_b']['name'][:6]} Fouls</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── FOUL INDICATOR ──
    st.markdown('<div class="section-header" style="font-size:0.75rem;">🟡 FOUL TRACKER</div>', unsafe_allow_html=True)
    for team_key, color in [("team_a", "#6699ff"), ("team_b", "#ff8888")]:
        fouls = state[team_key]["fouls"]
        dots = ""
        for i in range(5):
            cls = "foul-active" if i < fouls else "foul-inactive"
            dots += f'<span class="foul-dot {cls}"></span>'
        st.markdown(f'<div style="color:{color}; font-size:0.78rem; font-weight:600;">{state[team_key]["name"]}</div>{dots}', unsafe_allow_html=True)
        if fouls >= 5:
            st.markdown(f'<span style="color:#ff4444; font-size:0.7rem; font-weight:700;">⛔ PLAYER FOUL OUT</span>', unsafe_allow_html=True)
        elif fouls >= 3:
            st.markdown(f'<span style="color:#ffd700; font-size:0.7rem;">⚠️ Foul trouble</span>', unsafe_allow_html=True)

    # ── EVENT LOG ──
    st.markdown('<div class="section-header" style="font-size:0.75rem;">📋 EVENT LOG</div>', unsafe_allow_html=True)
    events = state.get("events", [])
    cat_class = {"score": "event-score", "foul": "event-foul", "timeout": "event-timeout",
                 "clock": "event-clock", "quarter": "event-quarter"}
    log_html = '<div class="event-log">'
    for ev in events[:40]:
        cls = cat_class.get(ev.get("cat",""), "event-item")
        log_html += f'<div class="event-item {cls}">[{ev.get("period","?")} {ev.get("time","--:--")}] {ev.get("msg","")}</div>'
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)

    if st.button("🗑 Clear Log", use_container_width=True, key="clear_log"):
        state["events"] = []
        save_state(state); st.rerun()

    # ───── ADDED: PDF GENERATION ─────
    st.markdown('<div class="section-header" style="font-size:0.75rem;">📄 GAME REPORT</div>',
                unsafe_allow_html=True)

    if not state.get("events"):
        st.caption("⚠️ No game history available to export.")
    else:
        if st.button("📄 Generate Game History PDF", use_container_width=True, key="gen_pdf"):
            with st.spinner("Building PDF…"):
                pdf_bytes = generate_game_pdf(state)
            date_str = datetime.now().strftime("%Y-%m-%d")
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"basketball_game_report_{date_str}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf",
            )
    # ───── END ADDED: PDF GENERATION ─────

# ─────────────────────────────────────────────
# GAME OVER BANNER
# ─────────────────────────────────────────────
if state.get("game_over"):
    winner = state["team_a"]["name"] if state["team_a"]["score"] > state["team_b"]["score"] else state["team_b"]["name"]
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a5c1a,#0a2a0a); border:2px solid #00ff88;
         border-radius:16px; padding:2rem; text-align:center; margin-top:1rem;">
      <div style="font-family:Orbitron,monospace; font-size:2rem; font-weight:900; color:#00ff88;">
        🏆 GAME OVER
      </div>
      <div style="font-size:1.3rem; color:#fff; margin-top:0.5rem;">
        WINNER: <strong style="color:#f5a623;">{winner}</strong>
      </div>
      <div style="font-size:1.8rem; font-family:Orbitron,monospace; color:#f5a623; margin-top:0.3rem;">
        {state['team_a']['score']} — {state['team_b']['score']}
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding: 1rem 0 0.3rem 0; border-top: 1px solid #1a1a2e; margin-top: 0.5rem;">
  <span style="color:#444; font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase;">
    Developed by <span style="color:#f5a623; font-weight:700;">HIVE</span> &nbsp;·&nbsp;
    Sri Ramakrishna Institute of Technology
  </span>
</div>
""", unsafe_allow_html=True)

# Auto-refresh: smooth updates when clock or break is running
if (state.get("clock_running") and not state.get("game_over")) or state.get("break_active"):
    time.sleep(0.1)
    st.rerun()