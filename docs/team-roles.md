# Team roles: Farm Intelligence and Economy Intelligence

This division follows the competition's two coupled problems: physical farm
operations and dynamic economic allocation. The win condition is final bank
coins; unsold goods do not count, while farm operations determine which goods
can exist in time to sell.

## Shared input: Observation and State Model

Kaggle calls `agent(observation, configuration)` every turn. `state.py` converts
the observation into `GameState` once.

| Information | Visibility | Primary consumer |
|---|---|---|
| Own tiles, farmer/hands, unlocked land | Public | Farm |
| Own shed, seeds, unit inventories | Private to us | Both for different reasons |
| Opponent tiles, money, hands, land | Public | Economy supply/risk model |
| Opponent shed, seeds, inventories | Hidden | Nobody; never infer as fact |
| Market prices and inventory | Shared | Economy |
| Town unlocked shops | Shared | Economy |
| Day/hour/remaining season | Shared | Both |

## Person 1: Farm Intelligence

### Goal

Convert available land, labor and carried items into timely products while
minimizing crop death, animal escape, wasted actions and travel.

### Own responsibilities

1. Parse the own-farm board into tasks.
2. Model crop lifecycle: plant, daily water, fertilize, peak harvest and decay.
3. Model animal lifecycle: structure, placement, feed, care, production and
   fertilizer collection.
4. Model shed access and unit inventories: pickup, place and drop.
5. Report empty space, utilization, urgent workload and labor demand.
6. Assign unique targets to farmer/hands and perform pathfinding.
7. Produce `UnitIntent` for every existing unit.

### Explicitly not responsible for

- Predicting price or town demand.
- Choosing a crop because it is profitable.
- Deciding how much cash to reserve.
- Emitting `SELL`, `BUY_*`, `HIRE` or `BUY_LAND`.

### Input/output contract

```text
analyze_farm(GameState) -> FarmFeatures
plan_unit_actions(GameState, FarmFeatures, selected_crop) -> UnitIntent[]
```

`selected_crop` is a directive from Shared Strategy. Farm may reject it as
physically infeasible, but must not replace it using price logic.

### Initial backlog

1. Complete crop urgency and harvest boundary tests.
2. Add shed pickup/drop routing.
3. Add animal setup/feed/care state machine.
4. Add fertilizer logistics.
5. Replace greedy assignment with reservation-aware scheduling/search.
6. Export workload/labor features for better hire decisions.

## Person 2: Economy Intelligence

### Goal

Convert observable supply, demand, prices, inventory and time into comparable
economic opportunities and market candidates.

### Own responsibilities

1. Build `EconomySnapshot` from own private economy data, shared market/town and
   opponent public farm signals.
2. Reproduce official price curves and estimate multi-unit order proceeds.
3. Forecast town demand, including duplicate shops and 2x single-product shops.
4. Rank crop, animal, fertilizer and product opportunities by profit, payback,
   time feasibility and market risk.
5. Estimate visible opponent future supply without pretending to see private
   inventory.
6. Manage shed pressure and sell/hold/final-liquidation policy.
7. Quote seed, animal, wheat/feed, fertilizer, hire and land investments.
8. Produce `MarketIntent` candidates with cost, priority and explanation.

### Explicitly not responsible for

- Choosing map coordinates or routes.
- Assigning farmer/hands.
- Issuing `WATER`, `HARVEST`, `FEED`, `BUILD_*` or other unit operations.
- Assuming that a financially attractive investment has enough physical labor
  or land; Shared Strategy checks `FarmFeatures`.

### Input/output contract

```text
build_economy_snapshot(GameState) -> EconomySnapshot
analyze_economy(GameState, AgentSettings) -> EconomyFeatures
```

### Initial backlog

1. Split exact price functions into `pricing.py` with interpreter parity tests.
2. Split town demand forecasting into `demand.py`.
3. Split crop unit economics into `crop_model.py`.
4. Add sell/hold/liquidation policy with multi-unit price impact.
5. Add animal/feed/fertilizer payback model.
6. Add public opponent supply forecast.
7. Add investment quotes for `BUY_PRODUCT` and `BUY_ANIMAL`.
8. Only then collect replay datasets and attempt ML price forecasting.

## Shared Strategy: both review

Shared Strategy owns decisions requiring both physical and economic facts.

| Decision | Economy provides | Farm provides | Shared Strategy decides |
|---|---|---|---|
| Production crop | Profit/risk ranking | Empty space/workload | Selected crop and seed quantity |
| Hire hands | Next hire costs | Work and travel pressure | Number of quotes to accept |
| Buy land | Cost/payback horizon | Current utilization | Whether to unlock now |
| Start animals | Animal/feed ROI | Structure/labor capacity | Animal count and timing |
| Use fertilizer | Product value/yield gain | Available unit/item path | Which plants and when |
| Sell inventory | Price/demand/shed risk | Incoming harvest pressure | Normally accept; resolve conflicts |

Shared Strategy must not duplicate price curves or pathfinding. It combines
already-computed features and emits intentions.

## Decision Fusion: neither person's strategy

Fusion performs hard validation only:

- Cash cannot go negative under accepted order sequence.
- Cannot sell more than own shed quantity.
- Cannot consume more existing seeds than available this turn.
- Cannot exceed market order cap.
- Exactly one action is returned for farmer and every existing hand.
- Invalid/duplicate commands are rejected deterministically.

If Fusion starts deciding which crop is profitable or which target is nearest,
logic has leaked from Economy or Farm and must be moved back.

## Pull request workflow

1. Work only inside the owned module and its focused tests when possible.
2. A contract change in `models.py` requires both people to review.
3. Record before/after results using the same full-season seeds.
4. Run unit tests, real-environment integration, full match and mirror self-play.
5. Keep `main` always buildable as a multi-file Kaggle submission.

## Authoritative references

- [Kaggriculture competition overview](https://www.kaggle.com/competitions/kaggriculture/overview)
- [Official environment rules](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md)
- [Official interpreter](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py)
