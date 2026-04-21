"""Kate の個人ボード"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from board_core import *

st.set_page_config(page_title="Kate — LINE Team", page_icon="🟡", layout="wide", initial_sidebar_state="collapsed")
st.markdown(COMMON_CSS, unsafe_allow_html=True)

MY_NAME = "Kate"

data = load_tasks()
tasks = data["tasks"]
team = load_json("team.json")
members = team["members"]

st.markdown("## 🟡 Kate")
render_team_bar(tasks, members)

tab_team, tab_me, tab_add = st.tabs(["📋 チーム全体", "🟡 マイボード", "➕ タスク追加"])

with tab_team:
    render_kanban(tasks, TEAM_COLUMNS, members, key_prefix="kt_", use_owner=True)

with tab_me:
    my_tasks = get_personal_tasks(tasks, MY_NAME)
    active = len([t for t in my_tasks if t["column"] in ("todo", "in_progress")])
    st.caption(f"アクティブ {active}件")
    render_personal_kanban(tasks, MY_NAME, members, key_prefix="km_")

with tab_add:
    render_add_form(members)
