# Runtime architecture

## Per-turn pipeline

```text
Kaggle Observation
        |
        v
build_state() ------------------------- shared, read-only contract
        |
        +--------------------+
        |                    |
        v                    v
analyze_farm()       analyze_economy()
FarmFeatures         EconomyFeatures
        |                    |
        +---------+----------+
                  v
        RuleBasedStrategy.decide()
        - select production target
        - combine capacity with value
        - call Farm planner for units
        - accept/reject Economy quotes
                  |
                  v
           fuse_decisions()
        hard validation only
                  |
                  v
         to_kaggle_action()
                  |
                  v
        {farmer, hands, market}
```

Farm and Economy analysis are conceptually parallel and must not import each
other. Python currently invokes them sequentially, but both are pure reads of
the same immutable `GameState`, so their call order has no semantic meaning.

## Contracts

- `GameState`: normalized observation; opponent private state never exists.
- `FarmFeatures`: tasks, empty land, workload and physical utilization.
- `EconomyFeatures`: crop opportunities, direct market candidates, investment
  quotes, demand, prices, visible opponent supply and spendable cash.
- `StrategyPlan`: selected production target plus unit and market intentions.
- `FinalDecision`: validated commands ready for serialization.

## Why Shared Strategy exists

Some decisions cannot belong solely to one specialist:

- `BUY_SEED`: Economy ranks/costs the crop; Farm reports planting capacity.
- `HIRE`: Economy quotes Fibonacci cost; Farm reports whether work exists.
- `BUY_LAND`: Economy evaluates capital/time; Farm reports utilization.
- Animals: Economy ranks purchase/payback; Farm must build, place, feed and
  collect products.
- Fertilizer: Economy values it; Farm schedules pickup and application.

Shared Strategy combines these signals. Decision Fusion stays after Strategy
because it is a safety gate, not an advisor.

## Environment ordering constraint

The interpreter applies existing unit actions, then processes ordered market
queues, town demand, refresh and observations. Therefore a seed, animal,
fertilizer product or hand purchased this turn cannot be assumed available to
the current turn's unit planner.

See [team roles](team-roles.md) for ownership and handoff rules.
