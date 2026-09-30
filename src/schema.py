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

    def __post_init__(self):
        """Validate safety-critical and simulation inputs at construction time."""
        if not self.sku_id or not self.name:
            raise ValueError("sku_id and name must be non-empty")
        if self.demand_mean_per_day < 0 or self.demand_std_per_day < 0:
            raise ValueError("demand mean/std must be >= 0")
        if self.lead_time_mean_days <= 0 or self.lead_time_std_days < 0:
            raise ValueError("lead-time mean must be > 0 and std must be >= 0")
        if not 0.0 <= self.supplier_fill_rate <= 1.0:
            raise ValueError("supplier_fill_rate must be between 0 and 1")
        if not 0.0 <= self.partial_fill_fraction <= 1.0:
            raise ValueError("partial_fill_fraction must be between 0 and 1")
        if self.late_extra_days < 0:
            raise ValueError("late_extra_days must be >= 0")
        if self.shelf_life_days <= 0:
            raise ValueError("shelf_life_days must be > 0")
        if self.order_cost_fixed < 0 or self.holding_cost_per_unit_day < 0:
            raise ValueError("order/holding costs must be >= 0")
        if self.stockout_cost_per_unit < 0 or self.unit_cost < 0 or self.waste_cost_per_unit < 0:
            raise ValueError("unit costs must be >= 0")
        if not 0.0 < self.target_service_level < 1.0:
            raise ValueError("target_service_level must be between 0 and 1")
        if self.max_units_per_order <= 0 or self.min_order_interval_days <= 0:
            raise ValueError("order limits/interval must be positive")
        allowed = {"normal", "poisson", "gamma", "empirical"}
        if self.demand_distribution not in allowed:
            raise ValueError(f"demand_distribution must be one of {sorted(allowed)}")
        if self.empirical_demand_samples is not None and any(x < 0 for x in self.empirical_demand_samples):
            raise ValueError("empirical demand samples must be >= 0")


@dataclass
class WorkforceConfig:
    """Constraints on the staff who receive, pick, and shelve stock."""

    workers_available: int = 2
    max_units_receivable_per_worker_per_day: int = 400  # safe manual-handling throughput
    max_order_lines_per_worker_per_day: int = 15         # cognitive load cap on distinct SKU put-aways

    def __post_init__(self):
        if self.workers_available <= 0:
            raise ValueError("workers_available must be > 0")
        if self.max_units_receivable_per_worker_per_day <= 0:
            raise ValueError("receiving capacity must be > 0")
        if self.max_order_lines_per_worker_per_day <= 0:
            raise ValueError("order-line capacity must be > 0")

    @property
    def daily_receiving_capacity(self) -> int:
        return self.workers_available * self.max_units_receivable_per_worker_per_day


@dataclass
class SimulationConfig:
    n_days: int = 365
    n_replications: int = 200
    random_seed: Optional[int] = 42

    def __post_init__(self):
        if self.n_days <= 0 or self.n_replications <= 0:
            raise ValueError("n_days and n_replications must be > 0")
