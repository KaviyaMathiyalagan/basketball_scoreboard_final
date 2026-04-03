import streamlit as st
import json
import time
import os

st.set_page_config(layout="wide")

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state.json")

# ---------- Load Game State ----------
default_state = {
    "team_a_score": 0,
    "team_b_score": 0,
    "quarter": 1,
    "game_clock": "10:00",
    "shot_clock": 24
}

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        loaded = json.load(f)
    state = {**default_state, **loaded}
else:
    state = default_state

team_a_score = state["team_a_score"]
team_b_score = state["team_b_score"]
quarter = state["quarter"]
game_clock = state["game_clock"]
shot_clock = state["shot_clock"]

# ---------- BLACK BACKGROUND ----------
st.markdown("""
<style>
.stApp{
background-color:black;
color:white;
}

.team{
font-size:60px;
font-weight:bold;
text-align:center;
}

.score{
font-size:90px;
font-weight:bold;
text-align:center;
color:#00ff9c;
}

.center-block{
text-align:center;
}

.quarter{
background:#111;
padding:8px 18px;
border-radius:8px;
display:inline-block;
font-weight:bold;
font-size:24px;
margin-bottom:10px;
}

.clock{
font-size:85px;
color:#00ff9c;
font-weight:bold;
margin:0;
line-height:1;
}

.shotclock{
font-size:36px;
color:#ff3b3b;
font-weight:bold;
margin-top:10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- MAIN LAYOUT ----------
col1, col2, col3 = st.columns([3, 2, 3])

# ---------- TEAM A ----------
with col1:
    st.markdown('<div class="team">TEAM A</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="score">{team_a_score}</div>', unsafe_allow_html=True)

# ---------- CENTER TIMER ----------
with col2:
    st.markdown(f'''
    <div class="center-block">
        <div class="quarter">QUARTER {quarter}</div>
        <div class="clock">{game_clock}</div>
        <div class="shotclock">SHOT CLOCK : {shot_clock}s</div>
    </div>
    ''', unsafe_allow_html=True)

# ---------- TEAM B ----------
with col3:
    st.markdown('<div class="team">TEAM B</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="score">{team_b_score}</div>', unsafe_allow_html=True)

# ---------- AUTO REFRESH ----------
time.sleep(1)
st.rerun()