"""Shared policy: reconcile Farm capacity with Economy value signals."""

from __future__ import annotations

from ..farm import plan_unit_actions
from ..models import (
    AgentSettings,
    CropOpportunity,
    MarketIntent,
    StrategicFeatures,
    StrategyPlan,
)


class RuleBasedStrategy:
    """Integration policy; domain-specific analysis stays in Farm/Economy."""

    def __init__(self, settings: AgentSettings | None = None):
        self.settings = settings or AgentSettings()

    @staticmethod
    def _select_crop(features: StrategicFeatures) -> CropOpportunity | None:
        for opportunity in features.economy.crop_opportunities:
            if opportunity.feasible and opportunity.expected_profit > 0:
                return opportunity
        return None

    def _integrate_market_intents(
        self, features: StrategicFeatures, crop: CropOpportunity | None
    ) -> tuple[MarketIntent, ...]:
        """Combine economic quotes with physical farm constraints."""
        state = features.state
        farm = features.farm
        economy = features.economy
        intents = list(economy.market_intents)

        # HIRE and BUY_LAND are market orders, but accepting them is a shared
        # decision: Economy owns their cost; Farm owns workload/utilization.
        for investment in economy.investment_intents:
            if investment.command[0] == "HIRE":
                has_farm_work = bool(farm.tasks or farm.empty_tiles)
                if has_farm_work:
                    intents.append(investment)
            elif investment.command[0] == "BUY_LAND" and farm.utilization >= 0.80:
                intents.append(investment)

        # Seed amount depends on both Economy's crop ranking/cash and Farm's
        # physical planting capacity, so it belongs at this integration layer.
        if crop is not None:
            current_hands = len(state.me.get("hands", ()) or ())
            current_seeds = int((state.private.get("seeds", {}) or {}).get(crop.crop, 0) or 0)
            expected_units = 1 + max(current_hands, self.settings.target_hands)
            plant_capacity = min(
                farm.unlocked_tile_count,
                expected_units * self.settings.max_plants_per_unit,
            )
            committed = farm.plant_count + current_seeds
            needed = max(0, plant_capacity - committed)
            desired_buffer = max(2, expected_units * self.settings.seed_buffer_per_unit)
            quantity = min(needed, max(0, desired_buffer - current_seeds), 6)
            affordable = int(economy.spendable_cash // crop.seed_cost)
            quantity = min(quantity, affordable)
            if quantity > 0:
                intents.append(
                    MarketIntent(
                        ("BUY_SEED", crop.crop, quantity),
                        760.0,
                        estimated_cost=float(quantity * crop.seed_cost),
                        reason=f"fund shared production target {crop.crop}",
                    )
                )
        return tuple(intents)

    def decide(self, features: StrategicFeatures) -> StrategyPlan:
        crop = self._select_crop(features)
        selected_crop = crop.crop if crop else None
        return StrategyPlan(
            selected_crop=selected_crop,
            unit_intents=plan_unit_actions(features.state, features.farm, selected_crop),
            market_intents=self._integrate_market_intents(features, crop),
            notes=(f"phase={features.phase}", f"crop={selected_crop or 'none'}"),
        )
