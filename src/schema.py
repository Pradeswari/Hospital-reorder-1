"""
Data schema for the hospital consumables reorder system.

These dataclasses ARE the data schema deliverable in executable form.
Every field maps 1:1 to a row/column described in docs/data_schema.md.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SKUConfig:
    """A single critical consumable (SKU) tracked by the hospital pharmacy/store."""

    sku_id: str
    name: str

    # Demand model: daily demand ~ Normal(mean, std), truncated at 0, rounded,
    # by default. `demand_distribution` selects an alternative shape for
    # sensitivity analysis (see src/demand_distributions.py):
    #   "normal"    - Normal(mean, std), truncated >=0, rounded (default)
    #   "poisson"   - Poisson(mean); appropriate for low-volume, "lumpy" demand
    #                 (demand_std_per_day is ignored -- Poisson ties variance to the mean)
    #   "gamma"     - Gamma(shape, scale) matched to (mean, std); continuous,
    #                 right-skewed, never negative -- for demand with an
    #                 occasional large spike
    #   "empirical" - resampled with replacement from `empirical_demand_samples`
    #                 (a real historical daily-demand series, if available)
    demand_mean_per_day: float
    demand_std_per_day: float

    # Lead time model: supplier lead time in days ~ Normal(mean, std), truncated at 1.
    lead_time_mean_days: float
    lead_time_std_days: float

    # Supplier reliability: probability a given order arrives complete & on-time
    # (i.e. NOT subject to a reliability failure event -> delay/partial fill).
    supplier_fill_rate: float  # e.g. 0.95 = 95% of orders arrive complete & as scheduled

    # When a reliability failure occurs, the fraction of ordered units actually
    # delivered on the original ETA (the rest arrive `late_extra_days` later).
    partial_fill_fraction: float = 0.6
    late_extra_days: float = 3.0

    # Shelf life from the day stock is received (FEFO consumption assumed).
    shelf_life_days: int = 90

    # Costs (₹ or any consistent currency unit)
    order_cost_fixed: float = 500.0       # cost per purchase order placed (admin/logistics)
    holding_cost_per_unit_day: float = 0.5
    stockout_cost_per_unit: float = 50.0   # clinical/operational cost of an unmet unit-day of demand
    unit_cost: float = 20.0
    waste_cost_per_unit: float = 20.0      # cost of a unit that expires unused (~= unit_cost)

    # Service commitment
    target_service_level: float = 0.95  # target probability of NOT stocking out in a lead-time window (cycle service level)

    # Safety / workload
    max_units_per_order: int = 5000     # physical/handling ceiling per single order (safety + storage cap)
    min_order_interval_days: int = 1    # cannot place two orders back-to-back same day (review cadence)

    # Demand distribution for sensitivity analysis (see src/demand_distributions.py):
    #   "normal"    - Normal(mean, std), truncated >=0, rounded (default; used throughout
    #                 the main experiment for higher-volume, steadier-consumption items)
    #   "poisson"   - Poisson(mean); appropriate for low-volume, "lumpy" demand
    #                 (demand_std_per_day is ignored -- Poisson ties variance to the mean)
    #   "gamma"     - Gamma(shape, scale) matched to (mean, std); continuous,
    #                 right-skewed, never negative -- models an occasional large spike
    #   "empirical" - resampled with replacement from `empirical_demand_samples`
    #                 (a real historical daily-demand series, if available)
    demand_distribution: str = "normal"
    empirical_demand_samples: Optional[list] = None


@dataclass
class WorkforceConfig:
    """Constraints on the staff who receive, pick, and shelve stock."""

    workers_available: int = 2
    max_units_receivable_per_worker_per_day: int = 400  # safe manual-handling throughput
    max_order_lines_per_worker_per_day: int = 15         # cognitive load cap on distinct SKU put-aways

    @property
    def daily_receiving_capacity(self) -> int:
        return self.workers_available * self.max_units_receivable_per_worker_per_day


@dataclass
class SimulationConfig:
    n_days: int = 365
    n_replications: int = 200
    random_seed: Optional[int] = 42
