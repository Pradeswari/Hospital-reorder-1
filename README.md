# Probabilistic Reorder Policy for Hospital Critical Consumables

![Tests](https://github.com/Pradeswari/Hospital-reorder-1/actions/workflows/tests.yml/badge.svg)

**CoE Capstone Project** — a probabilistic reorder policy incorporating
lead-time uncertainty and supplier reliability for a hospital managing
critical consumables with expiry dates, benchmarked against the hospital's
current fixed reorder-point rule.

## Problem
The hospital's current reorder rules ignore supplier reliability and
lead-time uncertainty, leading to stockouts of critical items and/or
excess inventory that expires unused.

## Result (headline)
Across a 6-SKU representative portfolio, 200 paired Monte Carlo replications
each, 365 simulated days, with 95% confidence intervals:

| Metric | Baseline (fixed ROP) | Probabilistic policy | Change (95% CI) |
|---|---|---|---|
| Stockout units/yr (portfolio) | 3,480 | 899 | **−74.2% [73.3%, 75.0%]** |
| Expired (wasted) units/yr (portfolio) | 3,127 | 1,042 | **−66.7% [66.3%, 67.0%]** |
| Total cost/yr (portfolio) | ₹2,312,908 | ₹1,933,981 | **−16.4% [16.1%, 16.6%]** |

Full breakdown, per-SKU numbers, and target-vs-measured service-level error
analysis: [`docs/before_after_comparison.md`](docs/before_after_comparison.md).

**Sensitivity analysis**: the result above assumes Normal-distributed demand.
We separately confirmed the same qualitative advantage holds when demand is
Poisson (low-volume, lumpy), Gamma (spiky, right-skewed), or drawn from a real
historical log (Empirical) — see
[`docs/sensitivity_analysis.md`](docs/sensitivity_analysis.md).

## Repository structure
```
hospital_reorder/
├── src/
│   ├── schema.py                 # data schema (SKUConfig, WorkforceConfig, SimulationConfig)
│   ├── policy_baseline.py        # fixed reorder-point rule (current practice)
│   ├── policy_probabilistic.py   # probabilistic policy (lead-time + reliability aware)
│   └── simulation.py             # day-stepped Monte Carlo engine (FEFO, expiry, workforce cap)
│   └── demand_distributions.py   # Normal/Poisson/Gamma/Empirical demand sampling (sensitivity analysis)
├── tests/
│   └── test_edge_cases.py        # policy, edge/failure, distribution-sensitivity, and input-boundary validation tests
├── experiments/
│   ├── run_experiment.py           # baseline vs probabilistic, 6-SKU Monte Carlo comparison, with 95% CIs
│   └── run_sensitivity_analysis.py # same comparison under Poisson/Gamma/Empirical demand
├── .github/workflows/tests.yml   # CI: runs the full test harness + both experiments on every push/PR
├── data/                         # generated: experiment_results.csv, experiment_raw.csv, sensitivity_results.csv, chart
├── docs/
│   ├── architecture.md           # architecture + component diagram (mermaid)
│   ├── data_schema.md
│   ├── risk_register.md
│   ├── stakeholder_assumptions.md
│   ├── user_guide.md
│   ├── before_after_comparison.md  # generated report, with 95% confidence intervals
│   └── sensitivity_analysis.md     # generated report: does the result hold under non-Normal demand?
└── requirements.txt
```

## Run it
```bash
pip install -r requirements.txt
python -m pytest tests/ -v                       # automated test harness
python experiments/run_experiment.py              # full experiment + report + chart (with 95% CIs)
python experiments/run_sensitivity_analysis.py    # sensitivity analysis (Poisson/Gamma/Empirical demand)
```

Continuous integration runs all three of the above automatically on every
push and pull request — see `.github/workflows/tests.yml` and the Actions
tab on GitHub.

An interactive, no-install dashboard version (same policy math, live
parameter controls, and the 3 built-in failure scenarios) is provided
alongside this repository.

## Why this approach (short version)
The baseline rule sets a reorder point from *average* demand and *average*
lead time only — it has no way to react to variability or an unreliable
supplier, so it either stocks out (when reality is worse than average) or
overstocks perishable items (when using a blanket safety margin). The
probabilistic policy instead derives its reorder point from the full
demand-during-lead-time distribution, folds supplier reliability in as a
mixture model (an unreliable supplier inflates required safety stock even
if its *average* lead time looks fine), balances order size against holding
cost via EOQ, and caps orders so they can never exceed what a short shelf
life can realistically absorb — all while the simulator enforces a hard
safe-workforce-capacity ceiling on receiving, so gains are never bought by
unsafe staff workload. See `docs/architecture.md` and
`docs/stakeholder_assumptions.md` for the full reasoning and its limits.


## Review 3 documentation

Review 3 adds explicit input-boundary validation and supporting documentation:

- [Testing and CI](docs/testing.md)
- [Error handling and input validation](docs/error_handling.md)
- [Final validation](docs/final_validation.md)
- [Review 3 changes](docs/review3_changes.md)

The project is a Python simulation and decision-support prototype with a dashboard artifact. It does not claim to provide a REST API or external production database.
