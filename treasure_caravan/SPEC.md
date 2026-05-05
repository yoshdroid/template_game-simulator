# Treasure Caravan 実装仕様

## 1. 概要

`Treasure Caravan` は4人用の push-your-luck ゲームです。

各プレイヤーは拠点から砂漠のルートへ出発し、奥へ進みながら財宝を採掘します。財宝は拠点へ帰還するまで未確定です。危険判定に失敗すると遭難し、その遠征で持っていた未確定財宝をすべて失って拠点へ戻ります。

今回の試作では妨害ルールは導入しません。プレイヤー同士は完全情報で同じ盤面を見ますが、直接攻撃や他プレイヤーの移動阻害はありません。

## 2. プレイヤー

- 4人固定
- プレイヤー色は `red`, `green`, `blue`, `yellow`
- 1プレイヤーにつき1つの子プロセスを起動する
- 子プロセスとは JSON Lines で通信する

## 3. ルート

```python
ROUTES = {
    "oasis":  {"name": "Oasis Road",   "length": 5, "risk": 0, "treasure": [1, 2, 2, 3, 4]},
    "ruins":  {"name": "Ruins Trail",  "length": 6, "risk": 1, "treasure": [2, 3, 4, 5, 6, 8]},
    "mirage": {"name": "Mirage Dunes", "length": 7, "risk": 2, "treasure": [3, 4, 6, 8, 10, 12, 15]},
}
```

`depth` は1始まりです。たとえば `mirage` の `depth=3` は財宝価値 `6` です。

## 4. プレイヤー状態

```python
{
    "location": "base" | "route",
    "route": None | "oasis" | "ruins" | "mirage",
    "depth": int,
    "cargo": int,       # 未確定財宝
    "banked": int,      # 確定得点
    "heat": int,        # 遠征中の危険蓄積
    "dug_sites": list,  # この遠征で採掘済みの "route:depth"
    "busts": int,
}
```

拠点にいるとき:

- `location = "base"`
- `route = None`
- `depth = 0`
- `cargo = 0`
- `heat = 0`
- `dug_sites = []`

## 5. アクション

### `depart`

拠点にいるときだけ選べます。

```json
{"action": "depart", "route": "oasis"}
```

効果:

- 指定ルートの `depth=1` へ移動
- `cargo = 0`
- `heat = 0`
- `dug_sites = []`
- 危険判定なし

### `advance`

ルート上にいて、現在ルートの最深部でないときだけ選べます。

効果:

- `depth += 1`
- `heat += 1`
- 危険判定あり

### `dig`

ルート上にいて、現在地点をこの遠征でまだ掘っていないときだけ選べます。

効果:

- 現在地点の財宝価値を `cargo` に加算
- 現在地点を `dug_sites` に追加
- `heat += 2`
- 危険判定あり

### `rest`

ルート上にいるときだけ選べます。

効果:

- `heat = max(0, heat - 3)`
- 危険判定なし

### `return`

ルート上にいるときだけ選べます。

効果:

- `banked += cargo`
- 拠点へ戻る
- `cargo = 0`
- `heat = 0`
- `dug_sites = []`
- 危険判定なし

## 6. 危険判定

`advance` または `dig` の後に行います。

```python
danger_score = route.risk + depth + heat + cargo // 5
roll = randint(1, 20)
bust = roll <= danger_score
```

遭難した場合:

- その遠征の `cargo` をすべて失う
- 拠点へ戻る
- `heat = 0`
- `dug_sites = []`
- `busts += 1`

## 7. 終了条件と勝者判定

各アクション後に終了判定を行います。

即時終了:

- いずれかのプレイヤーの `banked >= 40`

最大アクション終了:

- 全体アクション数が `max_actions` に到達
- 初期値は `200`

勝者判定:

1. `banked` が最も高い
2. 同点なら `cargo` が高い
3. それも同点なら `busts` が少ない
4. それも同点なら `winner_index = None`

## 8. JSON通信

### `hello`

親から子:

```json
{"type": "hello", "player_index": 0, "color": "red"}
```

子から親:

```json
{"type": "hello", "player_name": "sample", "version": "1.0"}
```

### `choose_action`

親から子:

```json
{
  "type": "choose_action",
  "player_index": 0,
  "state": {},
  "legal_actions": [
    {"action": "depart", "route": "oasis"},
    {"action": "depart", "route": "ruins"},
    {"action": "depart", "route": "mirage"}
  ]
}
```

子から親:

```json
{"type": "choose_action", "action": {"action": "depart", "route": "ruins"}}
```

親は `legal_actions` に含まれていないアクションを不正として拒否します。

### 通知イベント

親は必要に応じて以下を子へ通知します。

- `turn_start`
- `action_result`
- `bust`
- `return`
- `final`
- `bye`

## 9. 結果出力

結果JSON:

```text
results/treasure_caravan_result_YYYYMMDD_HHMMSS.json
```

`game.log`:

```text
YYYYMMDD_HHMMSS treasure_caravan winner: <winner> A 42 vs. B 31 vs. C 20 vs. D 18
```

## 10. 初期AI

- `random_player.py`: 合法手からランダム選択
- `cautious_player.py`: `oasis` と早めの帰還を好む
- `greedy_player.py`: `mirage` と採掘を好み、大きな荷物まで粘る
- `expected_value_player.py`: 次アクション後の簡易期待値で選ぶ

## 11. 今後の拡張候補

- `gui.py` / `live_view.py` によるリアルタイム観戦
- 結果JSONからのリプレイ
- 大会実行スクリプト
- 妨害ルール
- ルート、財宝、危険判定値のバランス調整
