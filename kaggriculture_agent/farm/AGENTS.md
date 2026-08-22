# Farm Intelligence rules — Person 1

Read the repository-root `AGENTS.md` first.

## Mission

Convert `GameState` plus a shared production directive into physically feasible
unit work. Optimize survival, timing, travel and labor utilization.

## Owns

- Parsing own public board tiles and own per-unit inventories.
- Crop/animal urgency, harvest timing, weeds, structures and shed logistics.
- Empty/occupied capacity, workload signals, target assignment and routing.
- `FarmTask`, `FarmFeatures` production and `UnitIntent` planning.

## Must not own

- Current/future price, demand, profit, ROI, cash allocation or opponent market
  prediction.
- `SELL`, `BUY_*`, `HIRE` or `BUY_LAND` market orders.
- Choosing the economically best crop/animal. Farm may report whether a shared
  choice is feasible and then execute it.

## Required behavior

- Use `tiles[y][x]`; movement is `NORTH/SOUTH/EAST/WEST`.
- Locked tiles are traversable but cannot receive tile actions.
- New plants need same-day watering; prevent two units consuming one seed.
- All existing hands receive exactly one action every turn.
- Required carried items must be checked before planning `FEED`, `FERTILIZE` or
  `PLACE`.
- Keep analysis and planning pure; no global episode memory.

Add focused tests to `tests/test_farm.py` for every mechanic changed.
