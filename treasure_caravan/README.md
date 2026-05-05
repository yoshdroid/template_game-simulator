# Treasure Caravan

`Treasure Caravan` は、`template_game-simulator` の親子プロセス通信、JSON Lines、AIプレイヤー差し替えの仕組みを流用して作るオリジナルの push-your-luck ゲームです。

プレイヤーは砂漠の商隊を率いて、3つのルートから1つを選んで出発します。奥へ進むほど財宝は大きくなりますが、危険度も上がります。財宝は拠点へ帰還するまで未確定で、危険判定に失敗すると持ち帰る前の荷物をすべて失います。

今回の試作では、妨害ルールは入れていません。まずは純粋な「進む、掘る、休む、帰る」の判断を遊んで確認するための実装です。

## 実行方法

```powershell
python treasure_caravan\master.py `
  --player1 random_player.py `
  --player2 cautious_player.py `
  --player3 greedy_player.py `
  --player4 expected_value_player.py `
  --seed 0
```

`--player` にパス区切りがない場合は、`treasure_caravan/players/` 以下のファイルとして扱います。

よく使うオプション:

- `--casual_match`: プレイヤーファイル先頭の戦績を更新しません。
- `--silent`: 子プレイヤーの stderr メッセージを非表示にします。
- `--no_result_json`: `results/` に結果JSONを出さず、`game.log` の1行ログだけにします。
- `--trace_json`: 親子プロセス間のJSON通信を stderr に表示します。
- `--max_actions 200`: 最大アクション数を指定します。

## GUI観戦

```powershell
python treasure_caravan\live_view.py `
  --player1 random_player.py `
  --player2 cautious_player.py `
  --player3 greedy_player.py `
  --player4 expected_value_player.py `
  --seed 0 `
  --casual_match `
  --silent
```

左側に3本のルートと各商隊の位置、右側にプレイヤーごとの `banked`, `cargo`, `heat`, `busts` と現在イベントを表示します。ゲーム終了後は `Esc` キーで画面を閉じられます。

## ルール概要

ルートは3種類です。

| route | 長さ | 危険補正 | 特徴 |
|---|---:|---:|---|
| `oasis` | 5 | 0 | 安全だが財宝は少なめ |
| `ruins` | 6 | 1 | 標準的なルート |
| `mirage` | 7 | 2 | 危険だが財宝が大きい |

手番では合法手から1つ選びます。

- `depart`: 拠点からルートへ出発します。
- `advance`: 1マス奥へ進み、危険判定を行います。
- `dig`: 現在地の財宝を未確定荷物に加え、危険判定を行います。
- `rest`: 危険蓄積である `heat` を3下げます。
- `return`: 未確定荷物 `cargo` を確定得点 `banked` に移して拠点へ戻ります。

危険判定:

```python
danger_score = route.risk + depth + heat + cargo // 5
bust = randint(1, 20) <= danger_score
```

誰かが `banked >= 40` に到達するか、最大アクション数に達するとゲーム終了です。

## ファイル構成

```text
treasure_caravan/
    README.md
    SPEC.md
    protocol.py
    simulator.py
    master.py
    gui.py
    live_view.py
    players/
        bot_base.py
        random_player.py
        cautious_player.py
        greedy_player.py
        expected_value_player.py
    assets/
        concept_treasure_caravan.png
```

## 実装メモ

- 通信は `choose_action` 中心の最小プロトコルです。
- 子プレイヤーは `legal_actions` から1つのアクションを返します。
- 結果JSONは `results/treasure_caravan_result_YYYYMMDD_HHMMSS.json` に保存します。
- `game.log` には `treasure_caravan winner: ...` の1行結果を追記します。
- GUI観戦は `treasure_caravan/live_view.py` から実行できます。
- 今後、結果JSONからのリプレイを追加する場合は、`simulator.py` の `events` を入力にできます。
