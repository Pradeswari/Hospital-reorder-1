"""
Probabilistic reorder policy.

Unlike the baseline (src/policy_baseline.py), this policy explicitly models:
  1. Demand uncertainty            (Normal(mean, std) per day)
  2. Lead-time uncertainty         (Normal(mean, std) per order)
  3. Supplier reliability          (probability an order arrives late/partial)
  4. A target cycle service level  (management's service commitment, not a guess)

It derives a reorder point (ROP) and order-up-to level (S) from these
inputs using standard probabilistic inventory theory (safety stock via
the demand-during-lead-time distribution), extended with a mixture term
for supplier unreliability. Order quantities are further constrained by
economic order quantity (cost-balanced) AND hard safety/workload ceilings.

Reference logic (documented for the "why this approach" requirement):
  - Var(D_LT) = E[LT] * Var(demand) + E[demand]^2 * Var(LT)
    (combined demand + lead-time uncertainty, Silver/Pyke/Peterson formulation)
  - Supplier unreliability is modelled as a two-point mixture on lead time:
    with prob (1 - fill_rate) the order is late by `late_extra_days`.
    This adds Var_reliability = fill_rate*(1-fill_rate)*late_extra_days^2
    to the effective lead-time variance -- an unreliable supplier
    inflates the safety stock requirement even if its AVERAGE lead time
    looks fine.
"""

from dataclasses import dataclass
from scipy.stats import norm
import math

from src.schema import SKUConfig


@dataclass
class ProbabilisticPolicyParams:
    reorder_point: float
    order_up_to: float
    order_quantity_eoq: float
    safety_stock: float
    effective_lead_time_mean: float
    effective_lead_time_std: float
    z_score: float


def effective_lead_time(sku: SKUConfig) -> tuple[float, float]:
    """Mean and std of the *effective* time-to-full-replenishment,
    folding in supplier reliability as a two-point mixture."""
    p = sku.supplier_fill_rate
    mean_eff = sku.lead_time_mean_days + (1 - p) * sku.late_extra_days
    var_eff = (sku.lead_time_std_days ** 2) + p * (1 - p) * (sku.late_extra_days ** 2)
    return mean_eff, math.sqrt(var_eff)


def demand_during_leadtime(sku: SKUConfig, lt_mean: float, lt_std: float) -> tuple[float, float]:
    """Mean and std of total demand accumulated during the (uncertain) lead time."""
    mean_dlt = sku.demand_mean_per_day * lt_mean
    var_dlt = lt_mean * (sku.demand_std_per_day ** 2) + (sku.demand_mean_per_day ** 2) * (lt_std ** 2)
    return mean_dlt, math.sqrt(max(var_dlt, 0.0))


def economic_order_quantity(sku: SKUConfig) -> float:
    """Classic EOQ: balances fixed ordering cost against holding cost."""
    annual_demand = sku.demand_mean_per_day * 365
    if sku.holding_cost_per_unit_day <= 0:
        return sku.demand_mean_per_day * 14
    annual_holding_cost_per_unit = sku.holding_cost_per_unit_day * 365
    eoq = math.sqrt((2 * annual_demand * sku.order_cost_fixed) / annual_holding_cost_per_unit)
    return max(eoq, sku.demand_mean_per_day)  # never order less than ~1 day of demand


def compute_probabilistic_params(sku: SKUConfig) -> ProbabilisticPolicyParams:
    lt_mean, lt_std = effective_lead_time(sku)
    dlt_mean, dlt_std = demand_during_leadtime(sku, lt_mean, lt_std)

    z = norm.ppf(sku.target_service_level)
    safety_stock = max(z * dlt_std, 0.0)

    rop = dlt_mean + safety_stock
    eoq = economic_order_quantity(sku)

    # Fairness/safety/expiry guardrail: never target more stock than can be
    # consumed within its shelf life (prevents "efficiency" gained by hoarding
    # that would just convert into future waste).
    max_sensible_cover = sku.demand_mean_per_day * sku.shelf_life_days * 0.8
    order_qty = min(eoq, max_sensible_cover, sku.max_units_per_order)

    order_up_to = rop + order_qty

    return ProbabilisticPolicyParams(
        reorder_point=rop,
        order_up_to=order_up_to,
        order_quantity_eoq=order_qty,
        safety_stock=safety_stock,
        effective_lead_time_mean=lt_mean,
        effective_lead_time_std=lt_std,
        z_score=z,
    )


def decide_order(inventory_position: float, params: ProbabilisticPolicyParams) -> float:
    """
    inventory_position = on_hand + on_order - backorders
    Order-up-to (S) policy: when IP falls to/below ROP, order up to S.
    """
    if inventory_position <= params.reorder_point:
        return max(params.order_up_to - inventory_position, 0.0)
    return 0.0
