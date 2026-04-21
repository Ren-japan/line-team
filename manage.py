#!/usr/bin/env python3
"""Star Team タスク管理CLI"""

import argparse
import json
import os
import sys
from datetime import datetime

# タスクDBのパス
TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tasks.json")

# 列の表示名
COLUMN_LABELS = {
    "todo": "📌 TODO",
    "in_progress": "🔵 進行中",
    "watching": "⏳ 観測中",
    "done": "✅ 完了",
}

VALID_COLUMNS = list(COLUMN_LABELS.keys())

# ball = 今このタスクのボールが誰にあるか（進行中・TODOの場合のみ意味を持つ）
BALL_LABELS = {
    "ren": "🔴 renボール",
    "ceo": "🟡 CEOボール",
    "worker": "🔵 担当者作業中",
    "external": "⏸ 外部待ち",
    "paused": "⚠️ チャット中断",
    "watching": "👀 観測中",
    "none": "— 未指定",
}
BALL_EMOJI = {
    "ren": "🔴",
    "ceo": "🟡",
    "worker": "🔵",
    "external": "⏸",
    "paused": "⚠️",
    "watching": "👀",
    "none": "  ",
}
VALID_BALLS = [b for b in BALL_LABELS.keys() if b != "none"]


def load_tasks():
    """tasks.jsonを読み込む"""
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(data, user):
    """tasks.jsonに書き込む（last_updated/updated_byを自動更新）"""
    data["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data["updated_by"] = user
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_user(args_user=None):
    """ユーザー名を取得（引数 > 環境変数）"""
    if args_user:
        return args_user
    env_user = os.environ.get("STAR_TEAM_USER")
    if env_user:
        return env_user
    return None


def next_id(tasks):
    """次のタスクIDを自動採番（t9, t10...）"""
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


def format_task_line(task):
    """タスク1行表示用のフォーマット"""
    tid = task["id"].ljust(4)
    title = task["title"]
    assignee = task.get("assignee", "") or ""
    deadline = task.get("deadline", "") or ""
    approval = "🔒承認待ち" if task.get("needs_approval") else ""
    ball = task.get("ball") or "none"
    ball_emoji = BALL_EMOJI.get(ball, "  ")

    # 期限超過判定
    overdue_mark = ""
    if deadline and task.get("column") != "done":
        try:
            d = datetime.strptime(deadline[:10], "%Y-%m-%d")
            days_over = (datetime.now() - d).days
            if days_over > 0:
                overdue_mark = f" ⚠️超過{days_over}d"
        except ValueError:
            pass

    # 各要素を組み立て
    parts = [f"  {ball_emoji} {tid}{title}"]
    if assignee:
        parts[0] = parts[0].ljust(40)
        parts.append(assignee.ljust(8))
    else:
        parts[0] = parts[0].ljust(48)
        parts.append("".ljust(8))
    if approval:
        parts.append(approval)
    if deadline:
        parts.append(f"  {deadline}")
    if overdue_mark:
        parts.append(overdue_mark)

    return "".join(parts)


def _similarity_score(a, b):
    """簡易類似度（共通トークン数ベース）"""
    import re
    def tokens(s):
        s = re.sub(r"[（）()\[\]「」【】、。,:：\-_/]+", " ", s or "")
        return {t for t in s.split() if len(t) >= 2}
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def find_similar_tasks(title, tasks, threshold=0.5):
    """類似タスクを検索"""
    hits = []
    for t in tasks:
        if t.get("column") == "done":
            continue
        score = _similarity_score(title, t.get("title", ""))
        if score >= threshold:
            hits.append((score, t))
    hits.sort(key=lambda x: -x[0])
    return hits


def cmd_list(args):
    """タスク一覧を表示"""
    data = load_tasks()
    tasks = data["tasks"]

    # フィルタ
    if args.assignee:
        tasks = [t for t in tasks if (t.get("assignee") or "").lower() == args.assignee.lower()]
    if args.column:
        if args.column not in VALID_COLUMNS:
            print(f"エラー: 無効な列 '{args.column}'。有効値: {', '.join(VALID_COLUMNS)}")
            sys.exit(1)
        tasks = [t for t in tasks if t["column"] == args.column]
    if getattr(args, "ball", None):
        if args.ball not in VALID_BALLS:
            print(f"エラー: 無効なball '{args.ball}'。有効値: {', '.join(VALID_BALLS)}")
            sys.exit(1)
        tasks = [t for t in tasks if (t.get("ball") or "none") == args.ball]

    if not tasks:
        print("該当タスクなし")
        return

    # 列ごとにグループ化して表示（進行中はballでサブグルーピング）
    ball_order = ["ren", "ceo", "worker", "external", "paused", "watching", "none"]
    for col_key in VALID_COLUMNS:
        col_tasks = [t for t in tasks if t["column"] == col_key]
        if not col_tasks:
            continue
        label = COLUMN_LABELS[col_key]
        print(f"\n{label} ({len(col_tasks)})")
        if col_key == "in_progress":
            for bkey in ball_order:
                sub = [t for t in col_tasks if (t.get("ball") or "none") == bkey]
                if not sub:
                    continue
                print(f"  — {BALL_LABELS[bkey]} ({len(sub)}) —")
                for t in sub:
                    print(format_task_line(t))
        else:
            for t in col_tasks:
                print(format_task_line(t))

    # 最終更新情報
    print(f"\n最終更新: {data.get('last_updated', '不明')} by {data.get('updated_by', '不明')}")


def cmd_add(args):
    """タスクを追加"""
    user = get_user(args.created_by)
    if not user:
        print("エラー: --created-by を指定するか、環境変数 STAR_TEAM_USER を設定してください")
        sys.exit(1)

    data = load_tasks()

    # ball必須ゲート
    ball = getattr(args, "ball", None)
    if not ball:
        print("エラー: --ball を指定してください（ren/ceo/worker/external/paused/watching）")
        sys.exit(1)
    if ball not in VALID_BALLS:
        print(f"エラー: 無効なball '{ball}'。有効値: {', '.join(VALID_BALLS)}")
        sys.exit(1)

    # 類似タスク検知（--force で回避可能）
    similar = find_similar_tasks(args.title, data["tasks"])
    if similar and not getattr(args, "force", False):
        print("⚠️ 類似タスクが見つかりました:")
        for score, t in similar[:5]:
            print(f"  ({score:.2f}) {t['id']} [{t['column']}] {t['title']}")
        print("\n対応を選べ:")
        print("  1) 既存に追記: python3 manage.py note <id> \"<内容>\"")
        print("  2) 親子化: 既存タスクを親に、--parent-id <id> で子タスク追加")
        print("  3) 別物として強行: 同じコマンドに --force を追加")
        sys.exit(2)

    new_id = next_id(data["tasks"])
    new_task = {
        "id": new_id,
        "title": args.title,
        "column": args.column or "todo",
        "assignee": args.assignee or "",
        "purpose": args.purpose or "",
        "impact": args.impact or "",
        "description": args.description or "",
        "deadline": args.deadline or "",
        "needs_approval": args.needs_approval or False,
        "created_by": user,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "notes": "",
        "ball": ball,
        "parent_id": getattr(args, "parent_id", None) or "",
    }

    data["tasks"].append(new_task)
    save_tasks(data, user)
    print(f"追加: {new_id} [{BALL_EMOJI[ball]} {ball}] — {args.title}")


def cmd_update(args):
    """タスクを更新"""
    data = load_tasks()
    task = None
    for t in data["tasks"]:
        if t["id"] == args.id:
            task = t
            break

    if not task:
        print(f"エラー: タスク '{args.id}' が見つかりません")
        sys.exit(1)

    user = get_user(args.updated_by) or data.get("updated_by", "unknown")
    changes = []

    if args.column:
        if args.column not in VALID_COLUMNS:
            print(f"エラー: 無効な列 '{args.column}'。有効値: {', '.join(VALID_COLUMNS)}")
            sys.exit(1)
        old = task["column"]
        task["column"] = args.column
        changes.append(f"列: {old} → {args.column}")

    if args.assignee is not None:
        old = task.get("assignee", "")
        task["assignee"] = args.assignee
        changes.append(f"担当: {old or '(なし)'} → {args.assignee or '(なし)'}")

    if args.title:
        task["title"] = args.title
        changes.append(f"タイトル更新")

    if args.deadline is not None:
        task["deadline"] = args.deadline
        changes.append(f"期限: {args.deadline or '(なし)'}")

    if args.purpose:
        task["purpose"] = args.purpose
        changes.append(f"目的更新")

    if args.impact is not None:
        task["impact"] = args.impact
        changes.append(f"インパクト更新")

    if args.approval is not None:
        task["needs_approval"] = args.approval
        changes.append(f"承認: {'必要' if args.approval else '不要'}")

    if args.ball is not None:
        if args.ball not in VALID_BALLS:
            print(f"エラー: 無効なball '{args.ball}'。有効値: {', '.join(VALID_BALLS)}")
            sys.exit(1)
        old = task.get("ball", "none")
        task["ball"] = args.ball
        changes.append(f"ball: {old} → {args.ball}")

    if args.parent_id is not None:
        task["parent_id"] = args.parent_id
        changes.append(f"親ID: {args.parent_id or '(なし)'}")

    if not changes:
        print("変更項目がありません")
        return

    save_tasks(data, user)
    print(f"更新: {args.id} — {task['title']}")
    for c in changes:
        print(f"  {c}")


def cmd_note(args):
    """タスクにメモを追記"""
    data = load_tasks()
    task = None
    for t in data["tasks"]:
        if t["id"] == args.id:
            task = t
            break

    if not task:
        print(f"エラー: タスク '{args.id}' が見つかりません")
        sys.exit(1)

    # 既存メモがあれば改行で追記
    timestamp = datetime.now().strftime("%m/%d %H:%M")
    new_note = f"[{timestamp}] {args.message}"
    existing = task.get("notes", "")
    if existing:
        task["notes"] = existing + "\n" + new_note
    else:
        task["notes"] = new_note

    user = get_user() or data.get("updated_by", "unknown")
    save_tasks(data, user)
    print(f"メモ追記: {args.id} — {task['title']}")
    print(f"  {new_note}")


def cmd_show(args):
    """タスクの詳細を表示"""
    data = load_tasks()
    task = None
    for t in data["tasks"]:
        if t["id"] == args.id:
            task = t
            break

    if not task:
        print(f"エラー: タスク '{args.id}' が見つかりません")
        sys.exit(1)

    col_label = COLUMN_LABELS.get(task["column"], task["column"])
    approval = " 🔒承認待ち" if task.get("needs_approval") else ""

    print(f"{'─' * 50}")
    print(f"  {task['id']}  {task['title']}{approval}")
    print(f"{'─' * 50}")
    print(f"  ステータス: {col_label}")
    print(f"  担当:       {task.get('assignee') or '—'}")
    print(f"  期限:       {task.get('deadline') or '—'}")
    print(f"  作成:       {task.get('created_by', '')} ({task.get('created_at', '')})")
    print()
    print(f"  📌 目的")
    print(f"  {task.get('purpose') or '—'}")
    print()
    if task.get("impact"):
        print(f"  📊 インパクト")
        print(f"  {task['impact']}")
        print()
    if task.get("description"):
        print(f"  📝 詳細")
        print(f"  {task['description']}")
        print()
    if task.get("notes"):
        print(f"  💬 メモ")
        for line in task["notes"].split("\n"):
            print(f"  {line}")
    print()


def cmd_delete(args):
    """タスクを削除"""
    data = load_tasks()
    task = None
    for t in data["tasks"]:
        if t["id"] == args.id:
            task = t
            break

    if not task:
        print(f"エラー: タスク '{args.id}' が見つかりません")
        sys.exit(1)

    data["tasks"] = [t for t in data["tasks"] if t["id"] != args.id]
    user = get_user(args.deleted_by) or data.get("updated_by", "unknown")
    save_tasks(data, user)
    print(f"削除: {args.id} — {task['title']}")


def cmd_overdue(args):
    """期限超過タスクを一覧表示（死亡疑い検知）"""
    data = load_tasks()
    now = datetime.now()
    hits = []
    for t in data["tasks"]:
        if t.get("column") == "done":
            continue
        dl = t.get("deadline", "")
        if not dl:
            continue
        try:
            d = datetime.strptime(dl[:10], "%Y-%m-%d")
        except ValueError:
            continue
        days_over = (now - d).days
        if days_over > 0:
            hits.append((days_over, t))

    if not hits:
        print("✅ 期限超過タスクなし")
        return

    hits.sort(key=lambda x: -x[0])
    print(f"⚠️ 期限超過タスク {len(hits)} 件")
    for days, t in hits:
        status = "💀死亡疑い" if days > 7 else ("🔶要レビュー" if days > 3 else "🟡超過")
        ball = t.get("ball") or "none"
        print(f"  {status} 超過{days}d {BALL_EMOJI.get(ball,'  ')} {t['id']} [{t['column']}] {t['title']}  (期限: {t.get('deadline','')})")
    print("\n対応:")
    print("  生きてる → python3 manage.py update <id> --deadline <新期限>")
    print("  死んだ   → python3 manage.py delete <id>")


def main():
    parser = argparse.ArgumentParser(description="Star Team タスク管理CLI")
    sub = parser.add_subparsers(dest="command", help="サブコマンド")

    # list
    p_list = sub.add_parser("list", help="タスク一覧")
    p_list.add_argument("--assignee", help="担当者でフィルタ")
    p_list.add_argument("--column", help="列でフィルタ（todo/in_progress/watching/done）")
    p_list.add_argument("--ball", help="ballでフィルタ（ren/ceo/worker/external/paused/watching）")

    # add
    p_add = sub.add_parser("add", help="タスク追加")
    p_add.add_argument("--title", required=True, help="タスクタイトル")
    p_add.add_argument("--ball", required=True, help="ボール所在（ren/ceo/worker/external/paused/watching）")
    p_add.add_argument("--assignee", help="担当者")
    p_add.add_argument("--purpose", help="目的（ゴール状態）")
    p_add.add_argument("--impact", help="期待インパクト")
    p_add.add_argument("--description", help="詳細説明")
    p_add.add_argument("--deadline", help="期限")
    p_add.add_argument("--column", help="列（デフォルト: todo）")
    p_add.add_argument("--needs-approval", dest="needs_approval", action="store_true", help="承認必要フラグ")
    p_add.add_argument("--created-by", dest="created_by", help="作成者（未指定時は環境変数STAR_TEAM_USER）")
    p_add.add_argument("--parent-id", dest="parent_id", help="親タスクID（親子構造化する時）")
    p_add.add_argument("--force", action="store_true", help="類似検知を無視して強行")

    # update
    p_update = sub.add_parser("update", help="タスク更新")
    p_update.add_argument("id", help="タスクID（例: t3）")
    p_update.add_argument("--column", help="列を変更")
    p_update.add_argument("--assignee", help="担当者を変更")
    p_update.add_argument("--title", help="タイトルを変更")
    p_update.add_argument("--deadline", help="期限を変更")
    p_update.add_argument("--purpose", help="目的を変更")
    p_update.add_argument("--impact", help="インパクトを変更")
    p_update.add_argument("--approval", type=lambda x: x.lower() in ("true", "1", "yes"), help="承認フラグ（true/false）")
    p_update.add_argument("--ball", help="ボール所在を変更（ren/ceo/worker/external/paused/watching）")
    p_update.add_argument("--parent-id", dest="parent_id", help="親タスクIDを設定/変更")
    p_update.add_argument("--updated-by", dest="updated_by", help="更新者")

    # note
    p_note = sub.add_parser("note", help="メモ追記")
    p_note.add_argument("id", help="タスクID")
    p_note.add_argument("message", help="メモ内容")

    # show
    p_show = sub.add_parser("show", help="タスク詳細表示")
    p_show.add_argument("id", help="タスクID")


    # delete
    p_delete = sub.add_parser("delete", help="タスク削除")
    p_delete.add_argument("id", help="タスクID（例: t3）")
    p_delete.add_argument("--deleted-by", dest="deleted_by", help="削除者")

    # overdue
    sub.add_parser("overdue", help="期限超過タスクを表示（死亡疑い検知）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # コマンド実行
    commands = {
        "list": cmd_list,
        "add": cmd_add,
        "update": cmd_update,
        "note": cmd_note,
        "show": cmd_show,
        "delete": cmd_delete,
        "overdue": cmd_overdue,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
