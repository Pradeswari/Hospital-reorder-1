"""
Baseline policy: classic fixed reorder-point / order-up-to rule.

This is the industry-default rule the hospital currently uses:
    ROP = mean_demand * mean_lead_time  (no safety stock for variability,
                                          no adjustment for supplier reliability)
    Order-up-to level Q = ROP + fixed_order_qty (a static multiple of average demand)

It reorders a fixed quantity whenever on-hand + on-order inventory drops
at or below the fixed reorder point. It does NOT look at lead-time
variance or supplier reliability at all -- which is exactly the gap
the probabilistic policy in policy_probabilistic.py is built to close.
"""

from dataclasses import dataclass
from src.schema import SKUConfig


@dataclass
class BaselinePolicyParams:
    reorder_point: float
    order_quantity: float


def compute_baseline_params(sku: SKUConfig, cover_days: float = 14.0) -> BaselinePolicyParams:
    """
    Standard fixed ROP used by the hospital today:
      ROP = average demand over average lead time (NO safety stock)
      Order quantity = average demand over a fixed `cover_days` cycle (EOQ-like heuristic)
    """
    rop = sku.demand_mean_per_day * sku.lead_time_mean_days
    order_qty = sku.demand_mean_per_day * cover_days
    return BaselinePolicyParams(reorder_point=rop, order_quantity=order_qty)


def decide_order(inventory_position: float, params: BaselinePolicyParams) -> float:
    """
    inventory_position = on_hand + on_order - backorders
    Returns quantity to order (0 if no order triggered).
    """
    if inventory_position <= params.reorder_point:
        return params.order_quantity
    return 0.0
