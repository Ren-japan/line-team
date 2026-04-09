# Star Team — チームタスク管理

## このリポジトリの目的

チーム全員のタスクを1つのDB（`data/tasks.json`）で管理する。
各メンバーのClaude Codeから読み書きして、git経由で同期する。

## あなたの役割

このリポジトリでClaude Codeを使うメンバーは4人:
- **Ren** — オーナー。判断・承認を行う
- **Noah** — 常駐メンバー。PU設置・CSV投入など実行の主力
- **Kate** — 週3勤務。SNS運用 + リサーチ + LINE導線
- **Rinon** — 週1勤務。品質チェック・依頼書確認

あなたはメンバーの代わりにタスク管理を手伝うアシスタント。
**やること: タスクの確認・更新・追加 + git操作の代行。**

## タスク操作

### manage.py を使う（推奨）

```bash
# タスク一覧
python3 manage.py list

# 自分のタスクだけ
python3 manage.py list --assignee Noah

# タスク詳細
python3 manage.py show t3

# ステータス変更
python3 manage.py update t3 --column done

# メモ追加
python3 manage.py note t3 "CSV 300件投入完了"

# タスク追加
python3 manage.py add --title "タイトル" --purpose "目的" --assignee Noah --created-by Noah
```

### tasks.jsonを直接編集してもOK

`data/tasks.json` を直接読み書きしても問題ない。
構造さえ壊さなければ、manage.py経由でなくてもよい。

### 列（column）の意味

| 列 | 意味 | 説明 |
|----|------|------|
| `todo` | 📌 TODO | まだ着手してない |
| `in_progress` | 🔵 進行中 | 作業中 |
| `watching` | ⏳ 観測中 | データ蓄積待ち等 |
| `done` | ✅ 完了 | 終わった |

### 承認フラグ（needs_approval）

`"needs_approval": true` のタスクはRenの承認が必要。
メンバーが勝手に着手・完了にしない。

## タスク更新後の手順（必ずやること）

```bash
# 1. ボードHTMLを再生成
python3 build_board.py

# 2. gitで共有
git add data/tasks.json team-board.html
git commit -m "update: t3を完了に更新 (Noah)"
git push
```

**コミットメッセージの形式:** `update: 何をしたか (誰が)`

## 作業開始時（毎回やること）

```bash
git pull    # 他のメンバーの変更を取り込む
```

これをやらずに作業すると、コンフリクトが起きる。

## ルール

1. **自分のタスクだけ編集する。** 他人のタスクを勝手に変えない
2. **作業前にgit pull。** 必ず最新にしてから編集する
3. **data/tasks.json 以外のファイルは基本触らない。** manage.py等のコードを変更しない
4. **担当者（assignee）= 今ボールを持ってる人、1人だけ。** 曖昧にしない
5. **困ったらRenに聞く。** 判断が必要なことは自分で決めない

## 環境変数（任意）

```bash
export STAR_TEAM_USER="Noah"   # 自分の名前を設定
```

設定しておくと、manage.py の `--created-by` を省略できる。
`.zshrc` や `.bashrc` に書いておくと毎回設定しなくて済む。

## ファイル構成

```
star-team/
├── CLAUDE.md          ← これ。Claude Code用の説明
├── manage.py          ← タスク管理CLI
├── build_board.py     ← tasks.json → HTML変換
├── team-board.html    ← ブラウザで見るボード
├── data/
│   ├── tasks.json     ← タスクDB（みんなで編集する）
│   ├── team.json      ← メンバー情報
│   ├── goals.json     ← GOAL設定（Ren管理）
│   └── channels.json  ← チャネル情報（Ren管理）
└── docs/
    ├── onboarding.html        ← メンバー向けオンボーディング（ステップ式）
    └── ren-setup-guide.md     ← Ren用手順（.gitignoreで除外）
```
