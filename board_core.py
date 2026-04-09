"""
共通コード: データ読み書き + カンバン描画
app.py / pages/*.py から参照
"""
import json
import base64
import requests
import streamlit as st
from pathlib import Path
from datetime import datetime

# --- GitHub設定 ---
REPO = "Ren-japan/line-team"
BRANCH = "main"
DATA_PATH_PREFIX = "data"

# --- ローカルパス ---
DATA_DIR = Path(__file__).parent / "data"
TASKS_FILE = DATA_DIR / "tasks.json"

# --- チーム全体の列 ---
TEAM_COLUMNS = {
    "todo": {"label": "📌 TODO", "color": "#94A3B8"},
    "in_progress": {"label": "🔵 進行中", "color": "#2563EB"},
    "watching": {"label": "⏳ 観測中", "color": "#D97706"},
    "done": {"label": "✅ 完了", "color": "#059669"},
}

# --- 個人ボードの列（AI視点） ---
PERSONAL_COLUMNS = {
    "todo": {"label": "🙋 自分ボール", "color": "#D97706"},
    "in_progress": {"label": "🤖 AI進行中", "color": "#2563EB"},
    "watching": {"label": "⏳ 結果待ち", "color": "#94A3B8"},
    "done": {"label": "✅ 完了", "color": "#059669"},
}

PEOPLE_COLORS = {
    "Ren": "#D97706",
    "Kate": "#EC4899",
    "Rinon": "#8B5CF6",
    "Noa": "#10B981",
}

COL_KEYS = ["todo", "in_progress", "watching", "done"]

# --- CSS ---
COMMON_CSS = """
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }

    /* カンバンカード */
    .task-card {
        background: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        border-left: 4px solid;
        cursor: pointer;
        transition: box-shadow 0.2s;
    }
    .task-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .task-title {
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 4px;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    .task-purpose {
        font-size: 0.75rem;
        color: #78716C;
        margin-bottom: 6px;
        line-height: 1.4;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    .task-meta {
        font-size: 0.7rem;
        color: #A8A29E;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .task-impact {
        font-size: 0.72rem;
        color: #059669;
        font-weight: 600;
    }
    .task-assignee {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .avatar-dot {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 0.6rem;
        font-weight: 700;
        flex-shrink: 0;
    }
    .approval-badge {
        display: inline-block;
        background: #FEF3C7;
        color: #D97706;
        font-size: 0.6rem;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 8px;
        margin-left: 4px;
    }
    .deadline-badge {
        font-size: 0.68rem;
        color: #A8A29E;
    }
    .task-note-preview {
        font-size: 0.68rem;
        color: #A8A29E;
        margin-top: 4px;
        font-style: italic;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* カラムヘッダー */
    .col-header {
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 2px solid #E7E5E4;
        white-space: nowrap;
    }
    .col-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        color: white;
        font-size: 0.65rem;
        font-weight: 700;
        margin-right: 6px;
    }

    /* ヘッダー・タブの見切れ防止 */
    h2, h1 {
        white-space: nowrap;
        overflow: visible;
    }
    div[data-testid="stTabs"] button {
        white-space: nowrap;
        overflow: visible;
    }

    /* チーム稼働バー */
    .team-bar {
        background: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 0.78rem;
        color: #78716C;
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        align-items: center;
        margin-bottom: 12px;
    }
    .team-bar-item {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .team-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }

    /* ···ボタン（カード直下、右寄せ、小さく） */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        float: right;
        padding: 0 6px;
        font-size: 0.75rem;
        min-height: 0;
        height: 22px;
        line-height: 22px;
        border: none;
        background: transparent;
        color: #A8A29E;
        margin-top: -8px;
        margin-bottom: 4px;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        color: #292524;
        background: #F5F5F4;
        border-radius: 4px;
    }

    /* ダイアログ内 */
    .detail-label {
        font-size: 0.75rem;
        color: #A8A29E;
        margin-bottom: 2px;
    }
    .detail-value {
        font-size: 0.88rem;
        color: #292524;
        margin-bottom: 12px;
    }
    .note-line {
        font-size: 0.8rem;
        color: #57534E;
        padding: 4px 0;
        border-bottom: 1px solid #F5F5F4;
    }
</style>
"""


# ============================================
# GitHub API
# ============================================
def get_github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        import os
        return os.environ.get("GITHUB_TOKEN", "")


def github_read(filename):
    token = get_github_token()
    if not token:
        return None, None
    url = f"https://api.github.com/repos/{REPO}/contents/{DATA_PATH_PREFIX}/{filename}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, params={"ref": BRANCH})
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return None, None


def github_write(filename, content_dict, sha, message="update tasks"):
    token = get_github_token()
    if not token:
        return False
    url = f"https://api.github.com/repos/{REPO}/contents/{DATA_PATH_PREFIX}/{filename}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    content_str = json.dumps(content_dict, ensure_ascii=False, indent=2) + "\n"
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": encoded, "sha": sha, "branch": BRANCH}
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code == 200


# ============================================
# データ読み書き
# ============================================
def load_json(filename):
    data, _ = github_read(filename)
    if data:
        return data
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tasks():
    data, sha = github_read("tasks.json")
    if data:
        st.session_state["tasks_sha"] = sha
        return data
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(data, user="App"):
    data["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data["updated_by"] = user
    sha = st.session_state.get("tasks_sha")
    if sha:
        if github_write("tasks.json", data, sha, f"update: task updated by {user}"):
            return
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def next_id(tasks):
    max_num = 0
    for t in tasks:
        tid = t.get("id", "")
        if tid.startswith("t"):
            try:
                num = int(tid[1:])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"t{max_num + 1}"


# ============================================
# タスク詳細ダイアログ
# ============================================
def show_task_detail(task, columns_def, team_members, key_prefix):
    """タスク詳細の編集UIを描画（st.dialogの中で呼ぶ）"""
    pk = f"{key_prefix}{task['id']}"
    assignee = task.get("assignee", "")

    # 詳細表示
    if task.get("purpose"):
        st.markdown(f'<div class="detail-label">📌 目的</div><div class="detail-value">{task["purpose"]}</div>', unsafe_allow_html=True)
    if task.get("impact"):
        st.markdown(f'<div class="detail-label">📊 インパクト</div><div class="detail-value" style="color:#059669;font-weight:600">{task["impact"]}</div>', unsafe_allow_html=True)
    if task.get("description"):
        st.markdown(f'<div class="detail-label">📝 詳細</div><div class="detail-value">{task["description"]}</div>', unsafe_allow_html=True)

    st.divider()

    # 操作フォーム
    current_idx = COL_KEYS.index(task["column"]) if task["column"] in COL_KEYS else 0
    new_status = st.selectbox("ステータス", COL_KEYS, index=current_idx,
        format_func=lambda x: columns_def[x]["label"], key=f"st_{pk}")

    member_names = [""] + [m["name"] for m in team_members]
    current_assignee_idx = member_names.index(assignee) if assignee in member_names else 0
    new_assignee = st.selectbox("担当者", member_names, index=current_assignee_idx, key=f"as_{pk}")

    new_note = st.text_input("メモ追加", key=f"no_{pk}", placeholder="メモを入力...")

    # コメント履歴
    if task.get("notes"):
        st.markdown('<div class="detail-label">💬 メモ履歴</div>', unsafe_allow_html=True)
        # 改行 or " / " で分割して1行ずつ表示
        raw_notes = task["notes"].replace(" / ", "\n")
        for line in raw_notes.split("\n"):
            if line.strip():
                st.markdown(f'<div class="note-line">{line.strip()}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ボタン
    btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
    with btn_col1:
        if st.button("💾 保存", key=f"sv_{pk}", type="primary", use_container_width=True):
            fresh_data = load_tasks()
            for t in fresh_data["tasks"]:
                if t["id"] == task["id"]:
                    if new_status != t["column"]:
                        t["column"] = new_status
                    if new_assignee != t.get("assignee", ""):
                        t["assignee"] = new_assignee
                    if new_note:
                        timestamp = datetime.now().strftime("%m/%d %H:%M")
                        note_line = f"[{timestamp}] {new_note}"
                        existing = t.get("notes", "")
                        t["notes"] = (existing + "\n" + note_line) if existing else note_line
                    break
            save_tasks(fresh_data, new_assignee or "App")
            st.rerun()
    with btn_col2:
        pass
    with btn_col3:
        if st.button("🗑", key=f"del_{pk}"):
            fresh_data = load_tasks()
            fresh_data["tasks"] = [t for t in fresh_data["tasks"] if t["id"] != task["id"]]
            save_tasks(fresh_data, "App")
            st.rerun()

    # メタ情報
    st.caption(f"作成: {task.get('created_by', '')} · {task.get('created_at', '')}")


# ============================================
# カンバン描画
# ============================================
def render_kanban(task_list, columns_def, team_members, key_prefix="", use_owner=True):
    cols = st.columns(4)
    for i, col_key in enumerate(COL_KEYS):
        col_info = columns_def[col_key]
        col_tasks = [t for t in task_list if t["column"] == col_key]
        with cols[i]:
            st.markdown(
                f'<div class="col-header">'
                f'<span class="col-count" style="background:{col_info["color"]}">{len(col_tasks)}</span>'
                f'{col_info["label"]}</div>',
                unsafe_allow_html=True
            )
            for task in col_tasks:
                render_card(task, col_info, columns_def, team_members, key_prefix, use_owner=use_owner)


def render_card(task, col_info, columns_def, team_members, key_prefix, use_owner=True):
    # チーム全体ボードではowner表示、マイボードではassignee表示
    display_name = task.get("owner", task.get("assignee", "")) if use_owner else task.get("assignee", "")
    assignee_color = PEOPLE_COLORS.get(display_name, "#A8A29E")
    initial = display_name[0].upper() if display_name else ""

    approval_html = '<span class="approval-badge">🔒 承認待ち</span>' if task.get("needs_approval") else ""
    deadline_html = f'<span class="deadline-badge">{task["deadline"]}</span>' if task.get("deadline") else ""
    impact_html = f'<div class="task-impact">{task["impact"]}</div>' if task.get("impact") else ""
    assignee_html = f'<span class="task-assignee"><span class="avatar-dot" style="background:{assignee_color}">{initial}</span>{display_name}</span>' if display_name else ""

    # コメントプレビュー（最新1行）
    note_preview = ""
    if task.get("notes"):
        lines = [l.strip() for l in task["notes"].split("\n") if l.strip()]
        if lines:
            note_preview = f'<div class="task-note-preview">💬 {lines[-1]}</div>'

    # 詳細ダイアログ
    pk = f"{key_prefix}{task['id']}"

    @st.dialog(f"{task['id']}: {task['title']}", width="large")
    def open_detail():
        show_task_detail(task, columns_def, team_members, key_prefix)

    # カード + 右下に ··· ボタン
    st.markdown(
        f'<div class="task-card" style="border-left-color:{col_info["color"]}">'
        f'<div class="task-title">{task["title"]}{approval_html}</div>'
        f'{"<div class=task-purpose>" + task["purpose"] + "</div>" if task.get("purpose") else ""}'
        f'{impact_html}'
        f'{note_preview}'
        f'<div class="task-meta">{assignee_html}{deadline_html}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    if st.button("···", key=f"open_{pk}"):
        open_detail()


def render_team_bar(tasks, members):
    team_items = ""
    for m in members:
        color = PEOPLE_COLORS.get(m["name"], "#666")
        active_count = len([t for t in tasks if t.get("assignee") == m["name"] and t["column"] in ("todo", "in_progress")])
        status_text = f"{active_count}件" if active_count > 0 else "—"
        team_items += f'<div class="team-bar-item"><span class="team-dot" style="background:{color}"></span>{m["name"]}: {status_text}</div>'
    st.markdown(f'<div class="team-bar">{team_items}</div>', unsafe_allow_html=True)


def render_add_form(members):
    st.markdown("### 新しいタスクを追加")
    with st.form("add_task_form"):
        title = st.text_input("タイトル *", placeholder="例: ED精力剤PU 3本目")
        purpose = st.text_input("目的", placeholder="例: 追加率11%にする")
        fc1, fc2 = st.columns(2)
        with fc1:
            member_names = [""] + [m["name"] for m in members]
            assignee = st.selectbox("担当者", member_names)
        with fc2:
            deadline = st.text_input("期限", placeholder="例: 4/15")
        impact = st.text_input("期待インパクト", placeholder="例: +50人/月")
        description = st.text_area("詳細", placeholder="詳細な説明...")
        needs_approval = st.checkbox("Renの承認が必要")
        submitted = st.form_submit_button("タスクを追加")
        if submitted:
            if not title:
                st.error("タイトルは必須です")
            else:
                fresh_data = load_tasks()
                new_id = next_id(fresh_data["tasks"])
                fresh_data["tasks"].append({
                    "id": new_id, "title": title, "column": "todo",
                    "assignee": assignee, "purpose": purpose, "impact": impact,
                    "description": description, "deadline": deadline,
                    "needs_approval": needs_approval,
                    "created_by": assignee or "App",
                    "created_at": datetime.now().strftime("%Y-%m-%d"), "notes": "",
                })
                save_tasks(fresh_data, assignee or "App")
                st.rerun()


def get_personal_tasks(all_tasks, name):
    """ownerベースでフィルタ。マイボード用。"""
    my_tasks = [t for t in all_tasks if t.get("owner") == name]
    watching = [t for t in all_tasks if t["column"] == "watching"]
    my_ids = {t["id"] for t in my_tasks}
    for wt in watching:
        if wt["id"] not in my_ids:
            my_tasks.append(wt)
    return my_tasks


def get_personal_tasks_by_ball(all_tasks, name):
    """ownerベースでフィルタし、ballで分類した辞書を返す。"""
    my_tasks = get_personal_tasks(all_tasks, name)
    return {
        "me": [t for t in my_tasks if t.get("ball") == "me" and t["column"] != "done"],
        "ai": [t for t in my_tasks if t.get("ball") == "ai" and t["column"] != "done"],
        "waiting": [t for t in my_tasks if t.get("ball") == "waiting" or t["column"] == "watching"],
        "done": [t for t in my_tasks if t["column"] == "done"],
    }


def render_personal_kanban(all_tasks, name, team_members, key_prefix=""):
    """マイボード：ballベースで4列表示"""
    ball_columns = {
        "me": {"label": "🙋 自分ボール", "color": "#D97706"},
        "ai": {"label": "🤖 AI進行中", "color": "#2563EB"},
        "waiting": {"label": "⏳ 結果待ち", "color": "#94A3B8"},
        "done": {"label": "✅ 完了", "color": "#059669"},
    }
    ball_keys = ["me", "ai", "waiting", "done"]

    by_ball = get_personal_tasks_by_ball(all_tasks, name)

    cols = st.columns(4)
    for i, bk in enumerate(ball_keys):
        col_info = ball_columns[bk]
        col_tasks = by_ball.get(bk, [])
        with cols[i]:
            st.markdown(
                f'<div class="col-header">'
                f'<span class="col-count" style="background:{col_info["color"]}">{len(col_tasks)}</span>'
                f'{col_info["label"]}</div>',
                unsafe_allow_html=True
            )
            for task in col_tasks:
                render_card(task, col_info, ball_columns, team_members, key_prefix, use_owner=False)
