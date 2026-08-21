"""Interactive local dashboard for Kaggriculture strategy experiments."""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
packages = ROOT / ".venv" / "Lib" / "site-packages"
if packages.exists():
    sys.path.insert(0, str(packages))

from kaggle_environments import make
from main import CROPS, agent


st.set_page_config(page_title="Kaggriculture Lab", layout="wide")
st.title("Kaggriculture Lab")
st.caption("Chỉnh chiến lược → chạy mô phỏng → xem map và lịch sử từng turn")

with st.sidebar:
    st.header("Strategy")
    preferred = st.selectbox("Crop ưu tiên", list(CROPS), index=list(CROPS).index("MELON"))
    late = st.selectbox("Crop cuối mùa", list(CROPS), index=list(CROPS).index("CARROT"))
    min_days = st.slider("Số ngày tối thiểu cho crop ưu tiên", 5, 20, 12)
    sell_threshold = st.slider("Giá tối thiểu để bán", 0, 300, 0, step=5)
    reserve = st.slider("Tiền dự trữ", 0, 500, 20, step=10)
    turns = st.select_slider("Số turn", options=[24, 120, 240, 480, 720], value=720)
    opponent = st.selectbox("Đối thủ", ["random"])
    run = st.button("Chạy mô phỏng", type="primary", use_container_width=True)

config = {
    "preferred_crop": preferred,
    "late_crop": late,
    "preferred_min_days": min_days,
    "sell_threshold": sell_threshold,
    "reserve_money": reserve,
}

if run:
    with st.spinner("Đang chạy trận đấu..."):
        env = make("kaggriculture", configuration={"episodeSteps": turns}, debug=True)
        env.run([lambda obs, cfg=None: agent(obs, config), opponent])
        st.session_state["steps"] = env.steps
        st.session_state["config"] = config

steps = st.session_state.get("steps")
if not steps:
    st.info("Chọn thông số bên trái rồi bấm 'Chạy mô phỏng'.")
    st.stop()

final = steps[-1]
scores = [getattr(s, "reward", 0) or 0 for s in final]
left, mid, right = st.columns(3)
left.metric("Agent score", f"${scores[0]:,.0f}")
mid.metric("Opponent score", f"${scores[1]:,.0f}")
right.metric("Turns", len(steps))

idx = st.slider("Xem turn", 0, len(steps) - 1, len(steps) - 1)
snapshot = steps[idx][0]
obs = snapshot.observation
farm = (obs.get("farms") or [{}])[obs.get("player", 0)]
tiles = farm.get("tiles", [])

st.subheader(f"Farm map · turn {idx} · day {obs.get('day', 0)}")
legend = "`F` farmer · `M` melon · `C` carrot · `W` wheat · `T` tomato · `S` strawberry · `🌿` weed · `·` empty · `#` locked"
st.caption(legend)
rows = []
fx, fy = farm.get("farmer", [None, None])
for y, row in enumerate(tiles):
    cells = []
    for x, tile in enumerate(row):
        if (x, y) == (fx, fy):
            cells.append("F")
        elif tile == "LOCKED":
            cells.append("#")
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            cells.append("🌿")
        elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
            cells.append(tile.get("crop", "?")[0])
        else:
            cells.append("·")
    rows.append(" ".join(cells))
st.code("\n".join(rows), language="text")

history = []
for turn, states in enumerate(steps):
    state = states[0]
    obs = state.observation or {}
    history.append({
        "turn": turn,
        "day": obs.get("day", 0),
        "hour": obs.get("hour", 0),
        "money": (obs.get("farms") or [{}])[obs.get("player", 0)].get("money", 0),
        "reward": getattr(state, "reward", 0),
    })
st.subheader("Turn history")
st.dataframe(history, use_container_width=True, hide_index=True)
