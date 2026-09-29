"""
End-to-end measurable experiment: baseline fixed-ROP policy vs the
probabilistic reorder policy, across a representative set of hospital
critical-consumable SKUs with different demand, lead-time, reliability,
and shelf-life profiles.

Outputs:
  - data/experiment_results.csv   (per-SKU, per-policy aggregated KPIs)
  - data/experiment_raw.csv       (per-replication raw KPIs, for error bars)
  - docs/before_after_comparison.md (summary table + narrative)
  - a PNG chart comparing stockouts / waste / cost / service level
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.schema import SKUConfig, WorkforceConfig, SimulationConfig
from src.policy_baseline import compute_baseline_params, decide_order as baseline_decide
from src.policy_probabilistic import compute_probabilistic_params, decide_order as prob_decide
from src.simulation import run_monte_carlo

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

# Representative SKU portfolio -- deliberately varied to stress-test both
# policies across realistic hospital consumable archetypes.
SKUS = [
    SKUConfig(
        sku_id="MED-INS-01", name="Insulin vials (cold chain)",
        demand_mean_per_day=25, demand_std_per_day=6,
        lead_time_mean_days=6, lead_time_std_days=2,
        supplier_fill_rate=0.90, partial_fill_fraction=0.5, late_extra_days=4,
        shelf_life_days=60, order_cost_fixed=800, holding_cost_per_unit_day=1.2,
        stockout_cost_per_unit=120, unit_cost=45, waste_cost_per_unit=45,
        target_service_level=0.98,
    ),
    SKUConfig(
        sku_id="SUT-GEN-02", name="Surgical suture packs",
        demand_mean_per_day=40, demand_std_per_day=10,
        lead_time_mean_days=4, lead_time_std_days=1,
        supplier_fill_rate=0.97, partial_fill_fraction=0.7, late_extra_days=2,
        shelf_life_days=365, order_cost_fixed=400, holding_cost_per_unit_day=0.15,
        stockout_cost_per_unit=60, unit_cost=15, waste_cost_per_unit=15,
        target_service_level=0.95,
    ),
    SKUConfig(
        sku_id="BLD-BAG-03", name="Blood collection bags",
        demand_mean_per_day=15, demand_std_per_day=5,
        lead_time_mean_days=7, lead_time_std_days=3,
        supplier_fill_rate=0.80, partial_fill_fraction=0.5, late_extra_days=5,
        shelf_life_days=42, order_cost_fixed=600, holding_cost_per_unit_day=0.8,
        stockout_cost_per_unit=150, unit_cost=30, waste_cost_per_unit=30,
        target_service_level=0.97,
    ),
    SKUConfig(
        sku_id="PPE-GLV-04", name="Sterile gloves (boxes)",
        demand_mean_per_day=60, demand_std_per_day=15,
        lead_time_mean_days=3, lead_time_std_days=1,
        supplier_fill_rate=0.93, partial_fill_fraction=0.6, late_extra_days=2,
        shelf_life_days=730, order_cost_fixed=300, holding_cost_per_unit_day=0.05,
        stockout_cost_per_unit=25, unit_cost=8, waste_cost_per_unit=8,
        target_service_level=0.93,
    ),
    SKUConfig(
        sku_id="ANT-BIO-05", name="Emergency antibiotics",
        demand_mean_per_day=18, demand_std_per_day=9,
        lead_time_mean_days=5, lead_time_std_days=2.5,
        supplier_fill_rate=0.75, partial_fill_fraction=0.55, late_extra_days=6,
        shelf_life_days=180, order_cost_fixed=700, holding_cost_per_unit_day=0.6,
        stockout_cost_per_unit=200, unit_cost=25, waste_cost_per_unit=25,
        target_service_level=0.99,
    ),
    SKUConfig(
        sku_id="PLT-CON-06", name="Platelet concentrate (very short shelf-life)",
        demand_mean_per_day=8, demand_std_per_day=3,
        lead_time_mean_days=3, lead_time_std_days=1,
        supplier_fill_rate=0.92, partial_fill_fraction=0.6, late_extra_days=2,
        shelf_life_days=5,  # platelets expire fast -- classic excess-inventory trap
        order_cost_fixed=350, holding_cost_per_unit_day=1.5,
        stockout_cost_per_unit=180, unit_cost=60, waste_cost_per_unit=60,
        target_service_level=0.96,
    ),
]

WORKFORCE = WorkforceConfig(workers_available=2, max_units_receivable_per_worker_per_day=400)
SIM_CFG = SimulationConfig(n_days=365, n_replications=200, random_seed=42)


def confidence_interval_95(arr):
    """95% confidence interval for the mean, via the t-distribution
    (appropriate since we have a finite sample of Monte Carlo replications,
    not the full population). Falls back to the point estimate when there is
    no variance across replications (e.g. a metric that is always 0), since
    the t-interval is undefined (zero standard error) in that case."""
    arr = np.asarray(arr, dtype=float)
    n = len(arr)
    m = arr.mean()
    se = stats.sem(arr) if n >= 2 else 0.0
    if n < 2 or se == 0.0 or np.isnan(se):
        return m, m, m
    lo, hi = stats.t.interval(0.95, df=n - 1, loc=m, scale=se)
    return m, lo, hi


def run_all():
    raw_rows = []
    summary_rows = []

    for sku in SKUS:
        baseline_params = compute_baseline_params(sku)
        prob_params = compute_probabilistic_params(sku)

        baseline_results = run_monte_carlo(sku, WORKFORCE, SIM_CFG, baseline_decide, baseline_params)
        prob_results = run_monte_carlo(sku, WORKFORCE, SIM_CFG, prob_decide, prob_params)

        for policy_name, results in [("baseline", baseline_results), ("probabilistic", prob_results)]:
            for i, r in enumerate(results):
                row = {"sku_id": sku.sku_id, "policy": policy_name, "replication": i, **r}
                raw_rows.append(row)

        def agg(results, key):
            vals = np.array([r[key] for r in results])
            m, lo, hi = confidence_interval_95(vals)
            return m, vals.std(), lo, hi

        for policy_name, results in [("baseline", baseline_results), ("probabilistic", prob_results)]:
            row = {"sku_id": sku.sku_id, "sku_name": sku.name, "policy": policy_name,
                   "target_service_level": sku.target_service_level}
            for key in ["stockout_units", "expired_units", "fill_rate", "cycle_service_level",
                        "total_cost", "orders_placed", "workload_overflow_events"]:
                m, s, lo, hi = agg(results, key)
                row[f"{key}_mean"] = m
                row[f"{key}_std"] = s
                row[f"{key}_ci95_lo"] = lo
                row[f"{key}_ci95_hi"] = hi
            summary_rows.append(row)

    raw_df = pd.DataFrame(raw_rows)
    summary_df = pd.DataFrame(summary_rows)

    raw_df.to_csv(os.path.join(OUT_DIR, "experiment_raw.csv"), index=False)
    summary_df.to_csv(os.path.join(OUT_DIR, "experiment_results.csv"), index=False)

    return raw_df, summary_df


def portfolio_reduction_ci(raw_df: pd.DataFrame, metric: str):
    """95% CI for the portfolio-wide % reduction in `metric`, using paired
    Monte Carlo replications.

    Each SKU's baseline and probabilistic runs share the same underlying
    random draws at a given replication index (both are generated from a
    fresh RNG seeded identically per call -- see src/simulation.py's
    run_monte_carlo), so replication i's baseline total and replication i's
    probabilistic total, summed across all SKUs, represent "the same
    simulated year" under each policy. This lets us compute a per-replication
    portfolio-wide % reduction and report its 95% CI, rather than just a
    single point-estimate reduction with no uncertainty bound.
    """
    pivot_base = raw_df[raw_df.policy == "baseline"].pivot_table(
        index="replication", columns="sku_id", values=metric, aggfunc="first")
    pivot_prob = raw_df[raw_df.policy == "probabilistic"].pivot_table(
        index="replication", columns="sku_id", values=metric, aggfunc="first")

    portfolio_base = pivot_base.sum(axis=1)
    portfolio_prob = pivot_prob.sum(axis=1)

    with np.errstate(divide="ignore", invalid="ignore"):
        reduction_pct = np.where(portfolio_base > 0,
                                  (1 - portfolio_prob / portfolio_base) * 100, np.nan)
    reduction_pct = reduction_pct[~np.isnan(reduction_pct)]

    m, lo, hi = confidence_interval_95(reduction_pct)
    return m, lo, hi


def make_chart(summary_df: pd.DataFrame):
    skus = summary_df["sku_id"].unique()
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Baseline (fixed ROP) vs Probabilistic Policy — Monte Carlo mean over 200 reps/SKU, 365 days",
                 fontsize=12, fontweight="bold")

    metrics = [
        ("stockout_units_mean", "Avg. stockout units / year (lower is better)", axes[0, 0]),
        ("expired_units_mean", "Avg. expired (wasted) units / year (lower is better)", axes[0, 1]),
        ("cycle_service_level_mean", "Cycle service level achieved (higher is better)", axes[1, 0]),
        ("total_cost_mean", "Avg. total annual cost (₹, lower is better)", axes[1, 1]),
    ]

    x = np.arange(len(skus))
    width = 0.35
    for metric, title, ax in metrics:
        baseline_vals = [summary_df[(summary_df.sku_id == s) & (summary_df.policy == "baseline")][metric].values[0] for s in skus]
        prob_vals = [summary_df[(summary_df.sku_id == s) & (summary_df.policy == "probabilistic")][metric].values[0] for s in skus]
        ax.bar(x - width/2, baseline_vals, width, label="Baseline (fixed ROP)", color="#C0432B")
        ax.bar(x + width/2, prob_vals, width, label="Probabilistic policy", color="#2E7D5B")
        ax.set_xticks(x)
        ax.set_xticklabels(skus, rotation=20, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "before_after_comparison.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def write_markdown_report(summary_df: pd.DataFrame, raw_df: pd.DataFrame):
    lines = ["# Before-and-After Comparison: Baseline vs Probabilistic Reorder Policy\n",
             "Monte Carlo simulation, 200 replications per SKU, 365 simulated days per replication. "
             "95% confidence intervals (t-distribution, across the 200 replications) are shown in "
             "brackets alongside each mean.\n",
             "| SKU | Policy | Stockout units/yr (95% CI) | Expired units/yr (95% CI) | Fill rate | Cycle service level (95% CI) | Total cost/yr (95% CI) | Orders placed/yr | Workload overflow events |",
             "|---|---|---|---|---|---|---|---|---|"]
    for _, row in summary_df.iterrows():
        lines.append(
            f"| {row.sku_id} | {row.policy} | "
            f"{row.stockout_units_mean:.1f} [{row.stockout_units_ci95_lo:.1f}, {row.stockout_units_ci95_hi:.1f}] | "
            f"{row.expired_units_mean:.1f} [{row.expired_units_ci95_lo:.1f}, {row.expired_units_ci95_hi:.1f}] | "
            f"{row.fill_rate_mean:.3f} | "
            f"{row.cycle_service_level_mean:.3f} [{row.cycle_service_level_ci95_lo:.3f}, {row.cycle_service_level_ci95_hi:.3f}] "
            f"(target {row.target_service_level:.2f}) | "
            f"₹{row.total_cost_mean:,.0f} [₹{row.total_cost_ci95_lo:,.0f}, ₹{row.total_cost_ci95_hi:,.0f}] | "
            f"{row.orders_placed_mean:.1f} | {row.workload_overflow_events_mean:.2f} |"
        )

    lines.append("\n## Error analysis (target vs measured cycle service level)\n")
    lines.append("| SKU | Policy | Target service level | Measured service level (95% CI) | Error (measured − target) |")
    lines.append("|---|---|---|---|---|")
    for _, row in summary_df.iterrows():
        err = row.cycle_service_level_mean - row.target_service_level
        lines.append(f"| {row.sku_id} | {row.policy} | {row.target_service_level:.2f} | "
                      f"{row.cycle_service_level_mean:.3f} [{row.cycle_service_level_ci95_lo:.3f}, {row.cycle_service_level_ci95_hi:.3f}] | {err:+.3f} |")

    lines.append("\n## Headline result (with 95% confidence intervals)\n")
    base_stockout = summary_df[summary_df.policy == "baseline"]["stockout_units_mean"].sum()
    prob_stockout = summary_df[summary_df.policy == "probabilistic"]["stockout_units_mean"].sum()
    base_waste = summary_df[summary_df.policy == "baseline"]["expired_units_mean"].sum()
    prob_waste = summary_df[summary_df.policy == "probabilistic"]["expired_units_mean"].sum()
    base_cost = summary_df[summary_df.policy == "baseline"]["total_cost_mean"].sum()
    prob_cost = summary_df[summary_df.policy == "probabilistic"]["total_cost_mean"].sum()

    stockout_red_m, stockout_red_lo, stockout_red_hi = portfolio_reduction_ci(raw_df, "stockout_units")
    waste_red_m, waste_red_lo, waste_red_hi = portfolio_reduction_ci(raw_df, "expired_units")
    cost_red_m, cost_red_lo, cost_red_hi = portfolio_reduction_ci(raw_df, "total_cost")

    lines.append(f"- Portfolio-wide stockout units/yr: baseline {base_stockout:.0f} → probabilistic {prob_stockout:.0f} "
                 f"— **{stockout_red_m:.1f}% reduction, 95% CI [{stockout_red_lo:.1f}%, {stockout_red_hi:.1f}%]**")
    lines.append(f"- Portfolio-wide expired (wasted) units/yr: baseline {base_waste:.0f} → probabilistic {prob_waste:.0f} "
                 f"— **{waste_red_m:.1f}% change, 95% CI [{waste_red_lo:.1f}%, {waste_red_hi:.1f}%]**")
    lines.append(f"- Portfolio-wide total cost/yr: baseline ₹{base_cost:,.0f} → probabilistic ₹{prob_cost:,.0f} "
                 f"— **{cost_red_m:.1f}% change, 95% CI [{cost_red_lo:.1f}%, {cost_red_hi:.1f}%]**")
    lines.append(
        "\nThe confidence intervals above are computed from paired Monte Carlo replications "
        "(each replication index represents the same simulated random year under both policies), "
        "which is why they can be fairly narrow even though individual-SKU outcomes vary."
    )

    with open(os.path.join(DOCS_DIR, "before_after_comparison.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    print("Running Monte Carlo experiment across", len(SKUS), "SKUs x 2 policies x", SIM_CFG.n_replications, "reps...")
    raw_df, summary_df = run_all()
    chart_path = make_chart(summary_df)
    write_markdown_report(summary_df, raw_df)
    print("Done.")
    print("Summary CSV:", os.path.join(OUT_DIR, "experiment_results.csv"))
    print("Chart:", chart_path)
    print("Report:", os.path.join(DOCS_DIR, "before_after_comparison.md"))
    print("\n" + summary_df[["sku_id", "policy", "stockout_units_mean", "expired_units_mean",
                              "fill_rate_mean", "cycle_service_level_mean", "total_cost_mean"]].to_string(index=False))
