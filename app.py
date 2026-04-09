"""
LINE Team — チーム全体ボード（管理者用、全タブ表示）
URL: line-team.streamlit.app
"""
import streamlit as st
from board_core import *

st.set_page_config(page_title="LINE Team", page_icon="📋", layout="wide", initial_sidebar_state="collapsed")
st.markdown(COMMON_CSS, unsafe_allow_html=True)

# データ
data = load_tasks()
tasks = data["tasks"]
team = load_json("team.json")
members = team["members"]

# ヘッダー
st.markdown("## 📋 LINE Team")
render_team_bar(tasks, members)

# タブ: チーム全体 + 各メンバー + タスク追加
tab_labels = ["📋 チーム全体"]
member_icons = {"Ren": "🟠", "Kate": "🟡", "Rinon": "🟣", "Noa": "🟢"}
for m in members:
    tab_labels.append(f"{member_icons.get(m['name'], '⚪')} {m['name']}")
tab_labels.append("➕ タスク追加")
all_tabs = st.tabs(tab_labels)

# チーム全体
with all_tabs[0]:
    render_kanban(tasks, TEAM_COLUMNS, members, key_prefix="team_")

# 個人タブ
for idx, m in enumerate(members):
    with all_tabs[idx + 1]:
        my_tasks = get_personal_tasks(tasks, m["name"])
        active = len([t for t in my_tasks if t["column"] != "done"])
        st.caption(f"アクティブ {active}件")
        render_kanban(my_tasks, PERSONAL_COLUMNS, members, key_prefix=f"{m['name']}_")

# タスク追加
with all_tabs[-1]:
    render_add_form(members)
