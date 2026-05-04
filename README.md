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

- `FIRST_GAME_DATE`: 空文字の場合だけ試合実行日時で上書き。すでに値がある場合は保持
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

## Can't Stop サンプル

`cant_stop/` 以下に、テンプレート機構を流用した別 simulator のサンプルを追加しています。

```text
cant_stop/
    master.py                  4人用の親プログラム
    protocol.py                親子通信JSONのtype名、生成関数、応答検証
    simulator.py               Can't Stop のゲームロジック
    gui.py                     background.png の上にレーンを描画する補助GUI
    live_view.py               進行中のイベントを受け取って盤面をリアルタイム表示
    view_result.py             結果JSONから最終盤面を表示する補助スクリプト
    view_replay.py             結果JSONのイベント列から盤面リプレイを表示する補助スクリプト
    background.png             GUI背景画像
    players/
        cautious_player.py     75%でターン終了する慎重派
        aggressive_player.py   25%でターン終了する過激派
        theory_player.py       6/7/8にポーンがある時だけ継続寄りになる理論派
        random_player.py       すべてランダムに決める適当派
        human_player.py        人間操作用の暫定雛形
        human_tk_player.py     別ウィンドウで操作する人間プレイヤー
```

実行例:

```powershell
python cant_stop\master.py --player1 cant_stop\players\cautious_player.py --player2 cant_stop\players\aggressive_player.py --player3 cant_stop\players\theory_player.py --player4 cant_stop\players\random_player.py --seed 123 --casual_match
```

大量実行やデバッグ用の主な追加引数:

- `--silent`: 子プレイヤーの stderr ログを表示しない
- `--no_result_json`: `results/` の結果JSONを作らず、`game.log` への1行追記だけ行う
- `--trace_json`: 親子間のJSON通信を stderr にミラー表示する

短く動作確認したい時:

```powershell
python cant_stop\master.py --player1 cant_stop\players\cautious_player.py --player2 cant_stop\players\aggressive_player.py --player3 cant_stop\players\theory_player.py --player4 cant_stop\players\random_player.py --seed 123 --step 20 --casual_match
```

リアルタイム観戦:

```powershell
python cant_stop\live_view.py --player1 cant_stop\players\cautious_player.py --player2 cant_stop\players\aggressive_player.py --player3 cant_stop\players\theory_player.py --player4 cant_stop\players\random_player.py --seed 123 --delay 350 --casual_match
```

`--delay` はイベント表示間隔のミリ秒です。短く試す場合は `--step 30` も併用できます。右側のプレイヤー一覧では、現在手番のプレイヤー名に下線を表示します。ゲーム終了後は `Esc` で画面を閉じられます。

人間プレイヤーを1人混ぜる例:

```powershell
python cant_stop\live_view.py --player1 cant_stop\players\cautious_player.py --player2 cant_stop\players\aggressive_player.py --player3 cant_stop\players\theory_player.py --player4 cant_stop\players\human_tk_player.py --seed 123 --timeout 600 --delay 350 --casual_match
```

`human_tk_player.py` は親との stdin/stdout JSON Lines 通信を維持しつつ、選択操作だけ別Tkinterウィンドウで行います。人間の入力待ちがあるため、`--timeout` は長めに指定してください。
自分の手番以外では操作情報を隠し、ボタンを無効化します。バースト時はGUIに表示され、`live_view.py` では既定で0.5秒停止します。停止時間は `--burst_pause` で調整できます。

2ポーン配置済みで、選んだ出目ペアのどちらのレーンも新規配置可能な場合は、親が追加で `choose_column` を要求します。`theory_player.py` は7に近いレーンを選び、その他のbotはランダムに選びます。`human_tk_player.py` ではレーン選択ボタンが表示されます。

親子通信のJSON形式は `cant_stop/protocol.py` に集約しています。`choose_pair`、`choose_column`、`decide_continue` の応答は、simulator側で必要項目と値の妥当性を検証します。botを追加するときは、`protocol.make_*_response(...)` を使うと type名やキー名のtypoを避けやすくなります。

結果JSONの最終盤面をGUI表示する例:

```powershell
python cant_stop\view_result.py results\cant_stop_result_YYYYMMDD_HHMMSS.json
```

結果JSONのリプレイをGUI表示する例:

```powershell
python cant_stop\view_replay.py results\cant_stop_result_YYYYMMDD_HHMMSS.json --delay 350
```

リプレイ操作:
- `Space`: 再生/一時停止
- `Right` / `Left`: 1イベント進む/戻る
- `Home` / `End`: 先頭/末尾へ移動
- `Esc`: 閉じる

GUIは `cant_stop/background.png` を背景にして、2〜12の11本レーンを左から順に描画します。

## Can't Stop 大会実行

ルート直下の `league_match.py` で、4人の全席順を回す大会を実行できます。1ラウンドにつき `4 * 3 * 2 * 1 = 24` 試合を実行し、`--round n` の場合は seed `0` から `n - 1` まで繰り返します。

```powershell
python league_match.py --players codex.py brain.py theory_player.py random_player.py --round 3 --casual_match --no_result_json
```

`--players` は4名必須です。指定パスが見つからない場合は `cant_stop/players/` 配下のファイル名として解決します。

大会中は既存の `game.log` と `results/` を `.save/` に退避し、大会結果は `tournament_results_YYYYMMDD_HHMMSS/` に保存します。終了後は退避した通常実行用の `game.log` と `results/` を元の場所へ戻します。

大会結果は `game.log` から勝利数と取得ポイントを集計します。優勝判定は勝利数、次にポイント数で比較し、同点の場合は複数プレイヤーを同点優勝として表示します。
