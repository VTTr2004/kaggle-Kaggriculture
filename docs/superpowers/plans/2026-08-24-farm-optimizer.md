# Farm Forecast Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone farm optimizer that uses official crop lifecycle rules, current tile state, and a future price forecast supplied by the economy module to choose seed quantities and planting days.

**Architecture:** Keep price forecasting outside the farm package. The farm package receives a normalized `price_forecast[crop][day_offset]`, simulates crop revenue and occupancy over a finite horizon, and searches integer crop allocations with a small brute-force/greedy search. Existing plants are treated as occupied state and are never discarded by the optimizer unless an explicit replacement plan beats their remaining value.

**Tech Stack:** Python 3.11, dataclasses, pytest; no new runtime dependencies.

**Spec:** Approved farm-only design in the conversation; official rules source: `https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py`.

## Global Constraints

- The economy module owns price prediction; farm only consumes a forecast.
- Official crop rules are copied from the Kaggriculture environment source and kept in a focused farm module.
- Plant counts and planting days are integer decisions.
- The existing demo agent remains runnable; integration is additive until the teammate's forecast function is available.
- Every production behavior is introduced with a failing test first.

### Task 1: Define farm planning contracts and official crop rules

**Files:**
- Create: `kaggriculture_agent/farm/planner.py`
- Test: `tests/test_farm_planner.py`

**Interfaces:**
- `CropRule`: immutable crop lifecycle data.
- `PlantState`: current crop tile state needed by the simulator.
- `FarmPlan`: integer seed targets and day-indexed planting choices.
- `PriceForecast`: mapping-like input of crop to future prices.

- [x] Write failing tests for official crop rules and `days_until_first_yield`.
- [x] Run `pytest tests/test_farm_planner.py -v` and confirm missing-module failure.
- [x] Add immutable rules and the lifecycle helper with the official source URL in the module docstring.
- [x] Run the focused tests and confirm they pass.

### Task 2: Simulate existing and candidate crops

**Files:**
- Modify: `kaggriculture_agent/farm/planner.py`
- Test: `tests/test_farm_planner.py`

**Interfaces:**
- `project_crop(rule, planted_day, current_day, horizon_days, prices) -> CropProjection`.
- `CropProjection`: expected harvest events, total units, revenue, and occupied days.

- [x] Write failing tests for one-time crops, ongoing crops, and insufficient remaining days.
- [x] Run the focused tests and confirm the new behavior is absent.
- [x] Implement the smallest projection model matching official day/interval/max-yield behavior.
- [x] Run the focused tests and confirm they pass.

### Task 3: Search integer crop allocations

**Files:**
- Modify: `kaggriculture_agent/farm/planner.py`
- Test: `tests/test_farm_planner.py`

**Interfaces:**
- `optimize_farm_plan(current_day, remaining_days, free_tiles, price_forecast, existing_plants=(), candidate_crops=...) -> FarmPlan`.

- [x] Write failing tests proving that the optimizer chooses the higher forecast-value crop, respects free-tile capacity, and changes its choice when the forecast changes.
- [x] Run the focused tests and confirm the optimizer is missing.
- [x] Implement integer allocation enumeration for the small crop set and return a deterministic tie-break.
- [x] Add a conservative validity rule that rejects plans whose first harvest is beyond the horizon.
- [x] Run the focused tests and confirm they pass.

### Task 4: Validate without changing the demo agent

**Files:**
- Modify: `docs/architecture.md` only if the new public farm interface needs a short note.
- Test: existing `tests/` suite.

- [ ] Run `pytest` for the full suite; blocked because `kaggle_environments` is not installed in this runtime.
- [x] Run `pytest --ignore=tests/test_environment_integration.py` for the available suite.
- [x] Run `ruff check .`.
- [x] Review the diff to confirm no market analysis code was changed and the existing agent contract remains intact.

### Task 5: Add a shallow economy test stub

**Files:**
- Create: `kaggriculture_agent/economy/mock_forecast.py`
- Modify: `kaggriculture_agent/economy/__init__.py`
- Test: `tests/test_mock_forecast.py`

**Interfaces:**
- `random_price_forecast(crops, horizon_days, seed, base_prices, volatility) -> dict[str, tuple[float, ...]]`.

- [x] Write a failing test proving the stub is reproducible and returns one series per crop.
- [x] Run the focused test and confirm the stub is missing.
- [x] Implement only a seeded random-walk generator; do not add market mechanics or ML.
- [x] Run the focused test and confirm it passes.
