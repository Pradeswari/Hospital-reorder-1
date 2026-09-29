# Data Schema

The schema is implemented as executable dataclasses in `src/schema.py` (not
just documentation) so the docs can never silently drift from the code.

## `SKUConfig` — one row per critical consumable

| Field | Type | Description |
|---|---|---|
| `sku_id` | string | Unique identifier, e.g. `MED-INS-01` |
| `name` | string | Human-readable consumable name |
| `demand_mean_per_day` | float | Mean daily consumption (units) |
| `demand_std_per_day` | float | Std. dev. of daily consumption |
| `lead_time_mean_days` | float | Mean supplier lead time (order → arrival), days |
| `lead_time_std_days` | float | Std. dev. of supplier lead time |
| `supplier_fill_rate` | float [0,1] | Probability an order arrives on-time & complete |
| `partial_fill_fraction` | float [0,1] | If a reliability failure occurs, fraction of the order delivered on the original ETA |
| `late_extra_days` | float | Extra days until the remainder of a failed order arrives |
| `shelf_life_days` | int | Days from receipt until a batch expires (FEFO consumption assumed) |
| `order_cost_fixed` | float (₹) | Fixed administrative/logistics cost per purchase order |
| `holding_cost_per_unit_day` | float (₹) | Storage/capital cost per unit held per day |
| `stockout_cost_per_unit` | float (₹) | Cost of one unit of unmet demand (clinical/operational impact) |
| `unit_cost` | float (₹) | Purchase price per unit |
| `waste_cost_per_unit` | float (₹) | Cost of one unit expiring unused |
| `target_service_level` | float [0,1] | Management's service commitment (cycle service level target) |
| `max_units_per_order` | int | Hard ceiling per single purchase order (storage/handling safety cap) |
| `min_order_interval_days` | int | Minimum days between two orders for the same SKU (review cadence) |

## `WorkforceConfig` — receiving/handling constraints

| Field | Type | Description |
|---|---|---|
| `workers_available` | int | Staff available for receiving/put-away |
| `max_units_receivable_per_worker_per_day` | int | Safe manual-handling throughput per worker per day |
| `max_order_lines_per_worker_per_day` | int | Cognitive-load cap on distinct SKU put-aways per worker per day |
| `daily_receiving_capacity` (derived) | int | `workers_available × max_units_receivable_per_worker_per_day` |

## `SimulationConfig` — experiment controls

| Field | Type | Description |
|---|---|---|
| `n_days` | int | Simulated days per replication |
| `n_replications` | int | Independent Monte Carlo replications per SKU/policy |
| `random_seed` | int/None | Seed for reproducibility |

## Simulation output record (per replication, per SKU, per policy)

| Field | Description |
|---|---|
| `total_demand`, `total_fulfilled` | Units demanded vs actually supplied from stock |
| `stockout_units` | Total unmet demand units over the run |
| `stockout_days` | Count of days with any unmet demand |
| `expired_units` | Units that expired unused (excess-inventory waste) |
| `orders_placed` | Number of purchase orders placed |
| `order_cost`, `holding_cost`, `purchase_cost`, `stockout_cost`, `waste_cost`, `total_cost` | Cost breakdown (₹) |
| `fill_rate` | `total_fulfilled / total_demand` |
| `cycle_service_level` | `1 − stockout_days / n_days` |
| `workload_overflow_events` | Count of days a delivery exceeded safe receiving capacity and was deferred |

## Data flow

`SKUConfig` + `WorkforceConfig` → policy module computes `*PolicyParams` →
`SimulationConfig` drives `run_monte_carlo()` → list of output records →
aggregated into `data/experiment_results.csv` (summary) and
`data/experiment_raw.csv` (per-replication, for error bars/variance analysis).
