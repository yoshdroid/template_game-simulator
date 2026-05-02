# template_game-simulator

新しいゲームシミュレータを作るための、Python製の最小テンプレートです。

親プログラム `template/master.py` がゲームマスターとして子プログラムを起動し、子プログラムとは stdin/stdout の JSON Lines で通信します。現在のサンプル simulator は「2人じゃんけん」ですが、今後は `template/simulator/` 以下を差し替えて別ゲームの開発に流用する想定です。

## 目的

- simulator 本体を差し替えながら、親子プロセス通信と試合管理の仕組みを再利用する
- 人間が追加しやすい bot 雛形を用意する
- 子プログラムの標準出力を通信専用にし、通常ログは stderr に分離する
- simulator 本体はテスト駆動で育てやすい構成にする

## 構成

```text
template/
    master.py                  親プログラム。試合管理、子プロセス起動、結果保存、ヘッダ更新を担当
    simulator/
        rps.py                 現在のサンプル simulator。2人じゃんけん
    players/
        random_player.py       ランダムに手を出す子bot雛形
        rock_player.py         常に rock を出す子bot雛形
    run_player_docker.ps1      Docker Desktop利用を想定した暫定runner
tests/
    test_rps.py                simulator のテスト
    test_summary.md            テスト一覧の日本語要約
pytest.ini                     pytest設定
```

実行時に `results/` と `game.log` が生成されます。これらは実行結果なので Git 管理対象から外しています。

## まず動かす

```powershell
python template\master.py --player1 template\players\rock_player.py --player2 template\players\random_player.py --round 2 --seed 123 --casual_match
```

主な引数:

- `--player1`, `--player2`: 起動する子プログラムのパス。現在のサンプル simulator は2人対戦のみ対応
- `--round`: 先にこの勝利数へ到達した側を最終勝者にする。デフォルトは `10`
- `--seed`: 再現用の乱数 seed。未指定時は実行日時由来の整数
- `--step`: 指定ラウンド数で途中停止するデバッグ用引数
- `--casual_match`: 子プログラムのヘッダ成績を更新しない

## テスト

```powershell
python -m pytest -q
```

`template/simulator/` 以下は、今後のゲームロジック開発でテスト駆動の中心にします。テストの日本語説明は `tests/test_summary.md` に短く残します。

## 親子間通信

通信は JSON Lines です。1行に1つの JSON を書き、flush します。

親から子へ送る例:

```json
{"type": "hello"}
{"type": "choice", "prompt": "hand", "valid": ["rock", "scissors", "paper"], "round": 1, "scores": {"p1": 0, "p2": 0}}
{"type": "result", "result": "win", "your_hand": "rock", "opponent_hand": "scissors"}
{"type": "final", "result": "win", "wins": 2, "opponent_wins": 0}
{"type": "bye"}
```

子から親へ返す例:

```json
{"type": "hello", "player_name": "random_player", "version": "1.0"}
{"type": "choice", "hand": "rock"}
{"type": "bye", "player_name": "random_player"}
```

標準出力は通信専用です。デバッグ表示や挨拶など、人間向けログは必ず stderr に出します。

## 子プログラムのヘッダ

親プログラムはゲーム開始前に子プログラムをテキストとして読み、先頭付近のグローバル変数からプレイヤー情報を取得します。通常試合では終了後に同じヘッダを書き換えます。

```python
########################################
# Player Information & Records
########################################
PLAYER_NAME = "sample_player"
VERSION = "1.0"
FIRST_GAME_DATE = ""
LAST_GAME_DATE = ""
PLAY_TIMES = 0
WIN = 0
POINT = 0
```

更新ルール:

- `LAST_GAME_DATE`: 試合実行日時で上書き
- `PLAY_TIMES`: `+1`
- `WIN`: 最終勝者なら `+1`
- `POINT`: 試合中の勝利数を加算

`--casual_match` 指定時、または同一ファイルを複数プレイヤーとして指定した時はヘッダ更新しません。

## 新しい simulator に置き換える手順

1. `template/simulator/` に新しい simulator モジュールを作る
2. simulator 側に、親が呼べる `run_match(...)` 相当の関数を用意する
3. simulator の結果を、親が扱いやすいデータ構造で返す
4. `template/master.py` の import と `run_match(...)` 呼び出し部分を新 simulator に合わせて変更する
5. 子botに送る `choice` や `result` の JSON payload を新ゲーム用に変える
6. `tests/` に simulator の判定・終了条件・不正入力処理のテストを追加する
7. `tests/test_summary.md` にテストの日本語要約を追記する

置き換え時に残すとよい共通部品:

- `PlayerProcessPort`: 子プロセスと JSON Lines 通信するための窓口
- `read_player_header(...)`: 子プログラムの成績ヘッダ読み取り
- `update_player_header(...)`: 子プログラムの成績ヘッダ更新
- `write_result_file(...)`: 結果 JSON 保存
- `append_game_log(...)`: 1行ログ追記

## 新しい子botを作る手順

1. `template/players/random_player.py` をコピーする
2. ヘッダの `PLAYER_NAME` を変更する
3. `choose_hand(...)` または `handle_message(...)` を新ゲーム用に変更する
4. 通信ではないログを `print(..., file=sys.stderr)` に出す
5. `python template\master.py --player1 ... --player2 ... --casual_match` で試す

## Docker runner について

`template/run_player_docker.ps1` は暫定の隔離実行サンプルです。

```powershell
.\template\run_player_docker.ps1 -PlayerPath .\template\players\random_player.py -Seed 123
```

現時点の `master.py` は通常のローカル Python プロセスとして子botを起動します。将来、不特定ユーザの bot を扱う段階では、`master.py` に Docker runner 経由で起動するオプションを追加してください。

## GitHub に登録する流れ

ローカルで初回コミット後、GitHub 側に空のリポジトリを作って remote を設定します。

```powershell
git remote add origin https://github.com/<ユーザー名>/<リポジトリ名>.git
git branch -M main
git push -u origin main
```

GitHub CLI を使う場合:

```powershell
gh repo create <ユーザー名>/<リポジトリ名> --private --source . --remote origin --push
```

公開リポジトリにする場合は `--private` を `--public` に変更します。
