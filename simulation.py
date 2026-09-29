"""
Discrete-event-ish, day-stepped Monte Carlo simulation engine.

Simulates, for a single SKU, one policy, over n_days:
  - stochastic daily demand
  - FEFO (first-expiry-first-out) consumption from dated batches
  - stochastic, unreliable supplier lead times (late/partial delivery events)
  - a hard workforce receiving-capacity constraint (safety: no unsafe
    "efficiency" from dumping unlimited units on staff in one day)
  - expiry/waste of unconsumed batches
  - stockouts (unmet demand, lost/backordered -- modeled as lost sales,
    typical for a critical-consumable hospital context)

Returns a dict of KPIs per replication so `experiments/run_experiment.py`
can aggregate distributions (not just single-run point estimates).
"""

from dataclasses import dataclass, field
import numpy as np

from src.schema import SKUConfig, WorkforceConfig, SimulationConfig
from src.demand_distributions import sample_demand


@dataclass
class Batch:
    quantity: float
    expiry_day: int  # absolute simulation day index on which it expires


@dataclass
class PendingOrder:
    arrival_day: int
    quantity: float


@dataclass
class DayResult:
    day: int
    on_hand: float
    demand: float
    fulfilled: float
    stockout_units: float
    expired_units: float
    order_placed: float
    orders_in_flight: int


def simulate_one_run(
    sku: SKUConfig,
    workforce: WorkforceConfig,
    sim_cfg: SimulationConfig,
    decide_order_fn,
    policy_params,
    rng: np.random.Generator,
    record_trace: bool = False,
) -> dict:
    on_hand_batches: list[Batch] = []
    pending_orders: list[PendingOrder] = []
    last_order_day = -sku.min_order_interval_days

    total_demand = 0.0
    total_fulfilled = 0.0
    total_stockout_units = 0.0
    total_expired_units = 0.0
    total_orders_placed = 0
    total_order_cost = 0.0
    total_holding_cost = 0.0
    total_unit_purchase_cost = 0.0
    stockout_days = 0
    workload_overflow_events = 0  # times an arrival exceeded safe daily receiving capacity

    trace: list[DayResult] = []

    for day in range(sim_cfg.n_days):
        # 1. Receive any orders arriving today, capped by safe workforce capacity.
        arrivals_today = [o for o in pending_orders if o.arrival_day == day]
        pending_orders = [o for o in pending_orders if o.arrival_day != day]
        incoming_qty = sum(o.quantity for o in arrivals_today)

        capacity = workforce.daily_receiving_capacity
        if incoming_qty > capacity:
            workload_overflow_events += 1
            # SAFETY RULE: never force staff to receive/shelve more than safe
            # capacity in one day. Overflow is deferred to the next day rather
            # than "processed anyway" -- efficiency is never bought by unsafe
            # assignment.
            deferred = incoming_qty - capacity
            incoming_qty = capacity
            pending_orders.append(PendingOrder(arrival_day=day + 1, quantity=deferred))

        if incoming_qty > 0:
            on_hand_batches.append(Batch(quantity=incoming_qty, expiry_day=day + sku.shelf_life_days))
            total_unit_purchase_cost += incoming_qty * sku.unit_cost

        # 2. Expire batches whose shelf life has ended.
        still_good = []
        expired_today = 0.0
        for b in on_hand_batches:
            if b.expiry_day <= day:
                expired_today += b.quantity
            else:
                still_good.append(b)
        on_hand_batches = still_good
        total_expired_units += expired_today

        # 3. Realize today's demand and fulfill FEFO (earliest expiry first).
        # `sample_demand` dispatches on sku.demand_distribution (normal by
        # default; poisson/gamma/empirical available for sensitivity analysis
        # -- see src/demand_distributions.py).
        demand_today = sample_demand(sku, rng)
        total_demand += demand_today

        on_hand_batches.sort(key=lambda b: b.expiry_day)
        remaining_demand = demand_today
        for b in on_hand_batches:
            if remaining_demand <= 0:
                break
            take = min(b.quantity, remaining_demand)
            b.quantity -= take
            remaining_demand -= take
        on_hand_batches = [b for b in on_hand_batches if b.quantity > 1e-9]

        fulfilled_today = demand_today - remaining_demand
        stockout_today = remaining_demand
        total_fulfilled += fulfilled_today
        total_stockout_units += stockout_today
        if stockout_today > 0:
            stockout_days += 1

        on_hand_total = sum(b.quantity for b in on_hand_batches)
        total_holding_cost += on_hand_total * sku.holding_cost_per_unit_day

        # 4. Review inventory position and decide whether to order.
        inventory_position = on_hand_total + sum(o.quantity for o in pending_orders)
        order_qty = 0.0
        can_order = (day - last_order_day) >= sku.min_order_interval_days
        if can_order:
            order_qty = decide_order_fn(inventory_position, policy_params)
            order_qty = min(order_qty, sku.max_units_per_order)

        if order_qty > 0:
            last_order_day = day
            total_orders_placed += 1
            total_order_cost += sku.order_cost_fixed

            # Supplier reliability realization: with prob (1-fill_rate) the
            # delivery is a late/partial event.
            reliable = rng.random() < sku.supplier_fill_rate
            lt = max(1, round(rng.normal(sku.lead_time_mean_days, sku.lead_time_std_days)))
            if reliable:
                pending_orders.append(PendingOrder(arrival_day=day + lt, quantity=order_qty))
            else:
                on_time_qty = order_qty * sku.partial_fill_fraction
                late_qty = order_qty - on_time_qty
                late_lt = lt + sku.late_extra_days
                pending_orders.append(PendingOrder(arrival_day=day + lt, quantity=on_time_qty))
                pending_orders.append(PendingOrder(arrival_day=day + late_lt, quantity=late_qty))

        if record_trace:
            trace.append(DayResult(
                day=day, on_hand=on_hand_total, demand=demand_today,
                fulfilled=fulfilled_today, stockout_units=stockout_today,
                expired_units=expired_today, order_placed=order_qty,
                orders_in_flight=len(pending_orders),
            ))

    service_level_fill_rate = (total_fulfilled / total_demand) if total_demand > 0 else 1.0
    service_level_cycle = 1 - (stockout_days / sim_cfg.n_days)
    total_cost = total_order_cost + total_holding_cost + total_unit_purchase_cost + \
        total_stockout_units * sku.stockout_cost_per_unit + total_expired_units * sku.waste_cost_per_unit

    result = {
        "total_demand": total_demand,
        "total_fulfilled": total_fulfilled,
        "stockout_units": total_stockout_units,
        "stockout_days": stockout_days,
        "expired_units": total_expired_units,
        "orders_placed": total_orders_placed,
        "order_cost": total_order_cost,
        "holding_cost": total_holding_cost,
        "purchase_cost": total_unit_purchase_cost,
        "stockout_cost": total_stockout_units * sku.stockout_cost_per_unit,
        "waste_cost": total_expired_units * sku.waste_cost_per_unit,
        "total_cost": total_cost,
        "fill_rate": service_level_fill_rate,
        "cycle_service_level": service_level_cycle,
        "workload_overflow_events": workload_overflow_events,
    }
    if record_trace:
        result["trace"] = trace
    return result


def run_monte_carlo(sku: SKUConfig, workforce: WorkforceConfig, sim_cfg: SimulationConfig,
                     decide_order_fn, policy_params) -> list[dict]:
    rng = np.random.default_rng(sim_cfg.random_seed)
    results = []
    for rep in range(sim_cfg.n_replications):
        rep_rng = np.random.default_rng(rng.integers(0, 2**32 - 1))
        results.append(simulate_one_run(sku, workforce, sim_cfg, decide_order_fn, policy_params, rep_rng))
    return results
