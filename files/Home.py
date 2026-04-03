import streamlit as st
import json
import os
import time

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

st.set_page_config(
    page_title="🏀 Basketball Scoring System",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=Orbitron:wght@700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #050510 !important; }
.main { background: #050510 !important; }
.block-container { padding: 2rem 3rem !important; }
section[data-testid="stSidebar"] { background: #070714 !important; }
section[data-testid="stSidebar"] * { color: #aaa !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding: 3rem 0 2rem 0;">
  <div style="font-family:Orbitron,monospace; font-size:3rem; font-weight:900; color:#f5a623;
       letter-spacing:0.1em; text-shadow: 0 0 30px rgba(245,166,35,0.4);">
    🏀 BASKETBALL SCORING SYSTEM
  </div>
  <div style="color:#555; font-size:1rem; letter-spacing:0.2em; text-transform:uppercase; margin-top:0.5rem;">
    Professional Game Management & Live Scoreboard
  </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a1a3a,#0d0d20); border:2px solid #1a3a6b;
         border-radius:20px; padding:2.5rem 2.5rem 1.5rem 2.5rem; text-align:center;
         box-shadow: 0 0 30px rgba(26,58,107,0.3);">
      <div style="font-size:4rem; margin-bottom:1rem;">🎮</div>
      <div style="font-family:Orbitron,monospace; font-size:1.5rem; font-weight:900; color:#6699ff; letter-spacing:0.1em;">JURY PANEL</div>
      <div style="color:#666; margin-top:0.8rem; font-size:0.9rem; line-height:1.6;">
        Full game control for referees &amp; scorekeepers.<br>
        Score buttons, foul tracking, clock management,<br>
        timeout control, violations &amp; more.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_🏀_Jury_Panel.py", label="→ Open Jury Panel", use_container_width=True)

with col2:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a2a1a,#0d1a0d); border:2px solid #1a5c1a;
         border-radius:20px; padding:2.5rem 2.5rem 1.5rem 2.5rem; text-align:center;
         box-shadow: 0 0 30px rgba(26,92,26,0.3);">
      <div style="font-size:4rem; margin-bottom:1rem;">📺</div>
      <div style="font-family:Orbitron,monospace; font-size:1.5rem; font-weight:900; color:#00ff88; letter-spacing:0.1em;">VIEWER DISPLAY</div>
      <div style="color:#666; margin-top:0.8rem; font-size:0.9rem; line-height:1.6;">
        Live scoreboard for audience &amp; display screens.<br>
        Real-time score, clock, shot clock, possession,<br>
        fouls, timeouts &amp; event ticker.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_📺_Viewer_Display.py", label="→ Open Viewer Display", use_container_width=True)

st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#070714; border:1px solid #111; border-radius:16px; padding:2rem;">
  <div style="font-family:Orbitron,monospace; font-size:1rem; font-weight:700; color:#f5a623;
       letter-spacing:0.12em; text-transform:uppercase; margin-bottom:1.2rem;">
    📖 System Features
  </div>
  <div style="display:grid; grid-template-columns: repeat(3,1fr); gap:1rem; font-size:0.85rem; color:#666; line-height:1.8;">
    <div>
      <div style="color:#88aaff; font-weight:600; margin-bottom:4px;">⏱ Clock Management</div>
      Game clock · Shot clock (24s) · Period control · Manual adjustment
    </div>
    <div>
      <div style="color:#88aaff; font-weight:600; margin-bottom:4px;">🏀 Scoring</div>
      1pt / 2pt / 3pt buttons · Free throw tracking · Score correction
    </div>
    <div>
      <div style="color:#88aaff; font-weight:600; margin-bottom:4px;">🟡 Fouls & Rules</div>
      Personal fouls · Team fouls · Foul-out tracking · FIBA compliant
    </div>
    <div>
      <div style="color:#88aaff; font-weight:600; margin-bottom:4px;">🚫 Violations</div>
      Traveling · Double dribble · 3s / 5s / 8s / 24s rules · Backcourt
    </div>
    <div>
      <div style="color:#88aaff; font-weight:600; margin-bottom:4px;">⏸ Timeouts</div>
      Per-team timeout tracking · Automatic deduction · Half-time reset
    </div>
    <div>
      <div style="color:#88aaff; font-weight:600; margin-bottom:4px;">📊 Live Feed</div>
      Event log · Score ticker · Viewer display auto-refresh every 3s
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
### 🏀 Navigation
Use the pages above to navigate.

---
**🎮 Jury Panel** → For scorekeepers

**📺 Viewer Display** → For audience screens

---
### 📖 Quick Rules
- **24s** shot clock
- **4 quarters** (10 or 12 min)
- **5 fouls** = foul out
- **3-point line** → 3 pts
- **Free throw** → 1 pt each
- **8 seconds** to half-court
- **3 seconds** in the paint
""")

st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 0.5rem 0; border-top: 1px solid #1a1a2e; margin-top: 1rem;">
  <span style="color:#444; font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase;">
    Developed by <span style="color:#f5a623; font-weight:700;">HIVE</span> &nbsp;·&nbsp;
    Sri Ramakrishna Institute of Technology
  </span>
</div>
""", unsafe_allow_html=True)
