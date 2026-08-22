# Kaggriculture Agent

Codebase cho team 2 người, bám theo pipeline:

```text
Observation -> State Model
                  |
        +---------+----------+
        |                    |
  Farm Intelligence   Economy Intelligence
  (Person 1)          (Person 2)
        |                    |
        +---------+----------+
                  |
         Strategic Features
                  |
   Shared Strategy (Rule -> ML -> RL -> Self-play)
                  |
           Decision Fusion
                  |
        +---------+----------+
        |                    |
  Farm execution      Market execution
```

Baseline hiện tại là deterministic rule-based, hỗ trợ farmer + farm hands,
dynamic crop scoring, watering/harvest/weed scheduling, buying/selling, hiring
và land expansion. Không có mutable global episode state nên có thể self-play
hai agent trong cùng Python process.

## Cài đặt

Yêu cầu Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

## Chạy và kiểm tra

```bash
pytest
python tools/run_match.py --opponent starter --seed 20260822
python tools/benchmark.py --opponent starter --seeds 20260820:20260830
```

Replay mặc định được ghi vào `replays/`. Chạy smoke test ngắn bằng
`--steps 120`; khi so sánh strategy phải dùng đủ 720 turns và cùng tập seed.

## Chia việc 2 người

| Phạm vi | Person 1 — Farm Intelligence | Person 2 — Economy Intelligence |
|---|---|---|
| Thư mục sở hữu | `kaggriculture_agent/farm/` | `kaggriculture_agent/economy/` |
| Bài toán | rules, scheduling, pathfinding, farm ML | rules/math, optimization, market model, economy ML |
| Input cố định | `GameState` | `GameState` |
| Output cố định | `FarmFeatures` | `EconomyFeatures` |
| Test riêng | `tests/test_farm.py` | `tests/test_economy.py` |

Các file shared (`models.py`, `features.py`, `strategy/`, `fusion.py`) nên đổi
qua PR nhỏ và cần cả hai review vì đây là contract tích hợp. Chi tiết dependency
rule và quy trình branch/merge nằm ở [docs/architecture.md](docs/architecture.md).

## Cấu trúc

```text
main.py                         # entry point bắt buộc của Kaggle
kaggriculture_agent/
  state.py                      # Observation -> GameState
  models.py                     # contract giữa các module
  domain.py                     # constant chính thức
  farm/                         # Person 1
  economy/                      # Person 2
  features.py                   # merge hai nhánh intelligence
  strategy/                     # shared rule/ML/RL/self-play policy
  fusion.py                     # resolve budget/resource/invariant
  execution.py                  # serialize Kaggle action
tools/
  run_match.py                  # một trận + replay
  benchmark.py                  # nhiều seed + win rate
  build_submission.py           # tạo artifacts/submission.tar.gz
tests/                           # unit + integration contract tests
```

## Đóng gói và submit

Kaggle yêu cầu `main.py` ở root archive và export hàm `agent`:

```bash
python tools/build_submission.py
tar -tzf artifacts/submission.tar.gz
kaggle competitions submit kaggriculture \
  -f artifacts/submission.tar.gz \
  -m "modular rule baseline v1"
```

Trước khi submit, chạy `pytest` và benchmark đủ 720 turns. Luật, observation và
action chính thức: [Kaggriculture environment](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture).
