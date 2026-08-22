# Economy Intelligence rules — Person 2

Read the repository-root `AGENTS.md` first.

## Mission

Turn observable economic state into comparable opportunities and market
candidates that maximize the chance of finishing with the most coins.

## Owns

- `EconomySnapshot`: own private inventory, shared market/town and opponent
  public farm signals.
- Exact price curves, market inventory effects, town demand and price forecast.
- Crop/animal/product/fertilizer economics, payback time and season feasibility.
- Shed pressure, sell/hold/liquidate rules, cash reserve and investment quotes.
- Economic candidates for `SELL`, `BUY_SEED`, `BUY_PRODUCT`, `BUY_ANIMAL`,
  `HIRE` and `BUY_LAND`.

## Must not own

- Coordinates, pathfinding, task assignment or farmer/hand operations.
- Assuming access to opponent shed, seeds or unit inventories; those are private.
- Assuming an investment can be executed physically. Shared Strategy combines
  quotes with `FarmFeatures` before acceptance.

## Required behavior

- Read raw economy fields once through `build_economy_snapshot()`.
- Keep formulas pure and deterministic. Every price/demand formula needs boundary
  tests against the official interpreter.
- Account for ordered, simultaneous per-unit market processing and the `$1`
  floor when estimating multi-unit orders.
- Unsold inventory has zero final reward; force liquidation before season end.
- Duplicate town shops count independently; single-product shops consume 2x.
- Never import `kaggriculture_agent.farm`.

Add focused tests to `tests/test_economy.py` for every mechanic changed.
