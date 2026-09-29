# User Guide

## 1. What this is
A prototype that decides **when and how much to reorder** for hospital
critical consumables, replacing a fixed reorder-point rule with one that
accounts for demand variability, lead-time variability, and **supplier
reliability** — while respecting shelf-life (expiry) and safe workforce
receiving capacity.

## 2. Quick start (Python repository)

```bash
cd hospital_reorder
pip install -r requirements.txt

# Run the automated test harness (policy math + edge/failure cases)
python -m pytest tests/ -v

# Run the full Monte Carlo experiment (baseline vs probabilistic, 6 SKUs)
python experiments/run_experiment.py
```

Outputs land in:
- `data/experiment_results.csv` — summary KPIs per SKU/policy
- `data/experiment_raw.csv` — per-replication raw KPIs (for your own error bars/variance analysis)
- `data/before_after_comparison.png` — comparison chart
- `docs/before_after_comparison.md` — narrative + tables (auto-generated, do not hand-edit)

## 3. Quick start (interactive dashboard)
Open the interactive artifact shared alongside this repository. No install
needed — it runs the same policy formulas in-browser.

1. Pick a SKU preset (or edit the parameters directly): demand, lead time,
   supplier fill rate, shelf life, service target.
2. Click **Run comparison** to simulate both the baseline and probabilistic
   policy on identical random demand/lead-time draws.
3. Read the results panel: stockout units, expired (wasted) units, service
   level achieved vs target, and total cost, baseline vs probabilistic.
4. Open the **Failure scenarios** tab to see the 3 built-in stress tests
   (unreliable supplier, demand surge, workforce overload) run live.

## 4. Interpreting the results
- **Cycle service level** = share of days with no stockout. Compare this to
  your `target_service_level` — the error-analysis table shows how close
  each policy actually lands to the promised target.
- **Stockout units** and **expired units** are the two failure modes this
  project set out to balance — a good policy should not just trade one for
  the other. Check both move in the right direction, not just one.
- **`workload_overflow_events`** > 0 means the *incoming* order volume
  exceeded safe daily receiving capacity at least once — a signal to revisit
  `max_units_per_order` or staffing, not a bug.

## 5. Recalibrating for a real SKU
Update the corresponding `SKUConfig` fields in `experiments/run_experiment.py`
(or the dashboard's parameter panel) using your own historical data:
- `demand_mean_per_day` / `demand_std_per_day`: from consumption history
  (e.g. trailing 90-day daily usage, mean and std. dev.)
- `lead_time_mean_days` / `lead_time_std_days`: from purchase-order-to-receipt
  records, per supplier
- `supplier_fill_rate`: share of past orders that arrived complete & on the
  originally quoted date
- `target_service_level`: set by pharmacy/clinical leadership, not derived
  automatically (see `docs/stakeholder_assumptions.md`)

Then re-run the test harness before trusting new numbers — if a new
parameter combination breaks an assumption (e.g. negative costs), the tests
should catch it.

## 6. Extending the prototype
The architecture (`docs/architecture.md`) deliberately separates policy
logic from the simulation engine. To add a third policy (e.g. a
machine-learning-based one), implement a `compute_*_params()` +
`decide_order()` pair matching the existing signatures and it can be run
through the exact same simulator and test harness with no other changes.
