#!/usr/bin/env python3
"""tasks.json → team-board.html のデータ部分を更新するビルドスクリプト"""

import json
import os
import re

# パス定義
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "data", "tasks.json")
TEAM_FILE = os.path.join(BASE_DIR, "data", "team.json")
HTML_FILE = os.path.join(BASE_DIR, "team-board.html")

# 列の定義（固定）
COLUMNS_DEF = {
    "todo":        {"label": "📌 TODO",  "color": "#94A3B8"},
    "in_progress": {"label": "🔵 進行中", "color": "#2563EB"},
    "watching":    {"label": "⏳ 観測中", "color": "#D97706"},
    "done":        {"label": "✅ 完了",   "color": "#059669"},
}

# デフォルトの担当者定義
DEFAULT_PEOPLE = [
    {"key": "Ren",   "name": "Ren",   "initial": "R", "color": "#D97706", "statusLabel": "判断待ち"},
    {"key": "Kate",  "name": "Kate",  "initial": "K", "color": "#EC4899", "statusLabel": "作業中"},
    {"key": "Rinon", "name": "Rinon", "initial": "R", "color": "#8B5CF6", "statusLabel": "次回4/2"},
    {"key": "Noa",   "name": "Noa",   "initial": "N", "color": "#10B981", "statusLabel": "作業中"},
]

# 担当者のカラーマップ
PEOPLE_COLORS = {p["key"]: p["color"] for p in DEFAULT_PEOPLE}


def load_json(path):
    """JSONファイルを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_created_at(date_str):
    """2026-03-26 → 3/26 に変換"""
    if not date_str:
        return ""
    parts = date_str.split("-")
    if len(parts) == 3:
        m = int(parts[1])
        d = int(parts[2])
        return f"{m}/{d}"
    return date_str


def task_to_js(task):
    """タスクをJS用オブジェクト文字列に変換"""
    assignee = task.get("assignee", "") or ""
    assignee_color = PEOPLE_COLORS.get(assignee, "#A8A29E") if assignee else ""
    created_at = format_created_at(task.get("created_at", ""))

    # JSON形式で組み立て
    obj = {
        "id": task["id"],
        "title": task["title"],
        "column": task["column"],
        "assignee": assignee,
        "assignee_color": assignee_color,
        "deadline": task.get("deadline", "") or "",
        "purpose": task.get("purpose", "") or "",
        "impact": task.get("impact", "") or "",
        "description": task.get("description", "") or "",
        "created_by": task.get("created_by", "") or "",
        "created_at": created_at,
        "needs_approval": bool(task.get("needs_approval", False)),
    }
    return json.dumps(obj, ensure_ascii=False)


def build_js_data(tasks_data):
    """TASKS, COLUMNS, PEOPLE のJS定数を生成"""
    lines = []

    # TASKS配列
    task_items = []
    for t in tasks_data["tasks"]:
        task_items.append(f"  {task_to_js(t)}")
    lines.append("var TASKS = [")
    lines.append(",\n".join(task_items))
    lines.append("];")
    lines.append("")

    # COLUMNS定義
    col_items = []
    for key, val in COLUMNS_DEF.items():
        col_items.append(f'  "{key}": {json.dumps(val, ensure_ascii=False)}')
    lines.append("var COLUMNS = {")
    lines.append(",\n".join(col_items))
    lines.append("};")
    lines.append("")

    # PEOPLE定義
    people = DEFAULT_PEOPLE
    people_items = []
    for p in people:
        people_items.append(f"  {json.dumps(p, ensure_ascii=False)}")
    lines.append("var PEOPLE = [")
    lines.append(",\n".join(people_items))
    lines.append("];")

    return "\n".join(lines)


def update_html(js_data):
    """team-board.html のマーカー間をJS定数で置換"""
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # マーカーで囲まれた部分を置換
    pattern = r"// ===BUILD_MARKER_START===.*?// ===BUILD_MARKER_END==="
    replacement = f"// ===BUILD_MARKER_START===\n{js_data}\n// ===BUILD_MARKER_END==="

    new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)

    if count == 0:
        print("エラー: team-board.html にマーカー（BUILD_MARKER_START/END）が見つかりません")
        print("team-board.html に以下のマーカーを追加してください:")
        print("  // ===BUILD_MARKER_START===")
        print("  // ===BUILD_MARKER_END===")
        return False

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    return True


def build_summary(tasks_data):
    """フッター用のサマリー情報を表示"""
    tasks = tasks_data["tasks"]
    counts = {}
    for t in tasks:
        col = t["column"]
        counts[col] = counts.get(col, 0) + 1

    parts = []
    if counts.get("done", 0):
        parts.append(f"完了 {counts['done']}件")
    if counts.get("in_progress", 0):
        parts.append(f"進行中 {counts['in_progress']}件")
    if counts.get("todo", 0):
        parts.append(f"TODO {counts['todo']}件")
    if counts.get("watching", 0):
        parts.append(f"観測中 {counts['watching']}件")

    return " | ".join(parts)


def main():
    # tasks.json を読み込む
    print("tasks.json を読み込み中...")
    tasks_data = load_json(TASKS_FILE)
    task_count = len(tasks_data["tasks"])

    # JS定数を生成
    js_data = build_js_data(tasks_data)

    # HTML更新
    print("team-board.html を更新中...")
    if update_html(js_data):
        summary = build_summary(tasks_data)
        print(f"完了: {task_count}件のタスクを反映 ({summary})")
        print(f"最終更新: {tasks_data.get('last_updated', '')} by {tasks_data.get('updated_by', '')}")
    else:
        print("HTMLの更新に失敗しました")
        exit(1)


if __name__ == "__main__":
    main()