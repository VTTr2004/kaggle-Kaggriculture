# Repository rules for coding agents and both team members

These rules apply to the entire repository. A nested `AGENTS.md` adds stricter
rules for its directory.

## Source of truth

1. The installed `kaggle_environments` interpreter and the official
   `Kaggle/kaggle-environments` source are authoritative for mechanics.
2. The Kaggle competition overview explains goals/evaluation but can lag the
   interpreter. When prose and code disagree, write a regression test against
   the installed environment and follow the interpreter used for submission.
3. Never guess action names, observation fields, turn order, price curves, crop
   ages, or inventory behavior.

## Non-negotiable runtime rules

- `main.py` stays at the submission root and exports `agent`.
- The runtime remains deterministic, stateless between calls, standard-library
  only, and safe when the agent plays an imported copy of itself.
- Never write logs/files, install packages, call the network, or train a model
  inside `agent()`.
- Invalid input loses one turn with `PASS`; it must not crash an episode.
- Unit actions use only official operations. Market output has at most
  `maxMarketOrdersPerTurn` ordered entries.
- Purchases and hires are processed after existing unit actions; resources
  bought this turn cannot be assumed available to unit planning this turn.

## Ownership boundaries

### Person 1 — Farm

Owns `kaggriculture_agent/farm/` and `tests/test_farm.py`.

- Board/task extraction, lifecycle urgency and physical farm capacity.
- Unit inventory logistics, scheduling, assignment and pathfinding.
- Farmer/hand operation intentions: move, plant, water, harvest, fertilize,
  structures, feed, care, fertilizer collection, pickup/place/drop and dig.
- Reports workload/capacity; does not price investments or emit market orders.

### Person 2 — Economy

Owns `kaggriculture_agent/economy/` and `tests/test_economy.py`.

- Economy snapshot, current market, town demand and public opponent supply.
- Price functions/forecasts, crop/animal/product unit economics and risk.
- Cash, shed pressure, liquidation and quotes for market investments.
- Emits economic opportunities/market candidates; never chooses coordinates,
  paths or farmer/hand operations.

### Shared integration

Both review changes to `models.py`, `domain.py`, `state.py`, `features.py`,
`strategy/`, `fusion.py`, `execution.py`, `agent.py`, `main.py` and integration
tests.

- Shared Strategy is the only layer allowed to combine Farm capacity with
  Economy value. Examples: seed quantity, accepting a hire quote, or buying land
  only when utilization justifies it.
- Decision Fusion does not invent strategy. It only enforces hard invariants:
  cash, seed/shed quantities, order count, valid operations and one action per
  existing unit.
- Farm and Economy must not import each other.

## Verification gates

Run before handoff:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python tools/build_submission.py
```

For strategy changes, also run at least one full 720-turn match, mirror
self-play, and the same multi-seed benchmark used for the previous version.
