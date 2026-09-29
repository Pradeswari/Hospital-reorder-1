# Sensitivity Analysis: Alternative Demand Distributions

The main experiment (`experiments/run_experiment.py`) assumes daily demand follows a Normal distribution for every SKU. This analysis checks whether the probabilistic policy's advantage over the baseline still holds when real demand follows a shape that is arguably more realistic for certain hospital consumables: **Poisson** (a low-volume, rare-use item), **Gamma** (a higher-volume but right-skewed/spiky item), and **Empirical** (resampled directly from a real historical daily-demand log, with no parametric assumption at all).

150 Monte Carlo replications, 365 simulated days, 95% confidence intervals (t-distribution) shown for every figure.

| Scenario | Distribution | Policy | Stockout units/yr (95% CI) | Expired units/yr (95% CI) | Service level (95% CI) | Total cost/yr (95% CI) |
|---|---|---|---|---|---|---|
| RARE-ANTV-07 | normal | baseline | 69.9 (66.7–73.2) | 0.0 (0.0–0.0) | 0.935 (0.932–0.937) | ₹217,972 (₹216,806–₹219,138) |
| RARE-ANTV-07 | normal | probabilistic | 15.9 (14.7–17.1) | 0.0 (0.0–0.0) | 0.987 (0.986–0.988) | ₹228,356 (₹227,458–₹229,253) |
| RARE-ANTV-07 | poisson | baseline | 69.3 (66.2–72.4) | 0.0 (0.0–0.0) | 0.935 (0.932–0.938) | ₹216,507 (₹215,390–₹217,623) |
| RARE-ANTV-07 | poisson | probabilistic | 15.2 (14.1–16.2) | 0.0 (0.0–0.0) | 0.987 (0.986–0.988) | ₹226,563 (₹225,621–₹227,505) |
| ANT-BIO-SPIKY-08 | normal | baseline | 808.9 (773.2–844.6) | 0.0 (0.0–0.0) | 0.910 (0.906–0.914) | ₹420,633 (₹414,764–₹426,503) |
| ANT-BIO-SPIKY-08 | normal | probabilistic | 169.9 (157.2–182.5) | 0.0 (0.0–0.0) | 0.983 (0.982–0.984) | ₹359,156 (₹356,719–₹361,592) |
| ANT-BIO-SPIKY-08 | gamma | baseline | 786.2 (749.2–823.2) | 0.0 (0.0–0.0) | 0.907 (0.904–0.911) | ₹410,499 (₹404,449–₹416,548) |
| ANT-BIO-SPIKY-08 | gamma | probabilistic | 166.4 (153.6–179.2) | 0.0 (0.0–0.0) | 0.981 (0.980–0.982) | ₹352,801 (₹350,481–₹355,121) |
| RARE-ANTV-EMP-09 | normal | baseline | 72.9 (70.3–75.6) | 0.0 (0.0–0.0) | 0.909 (0.906–0.912) | ₹155,778 (₹154,700–₹156,856) |
| RARE-ANTV-EMP-09 | normal | probabilistic | 10.9 (10.0–11.8) | 0.0 (0.0–0.0) | 0.989 (0.988–0.990) | ₹158,206 (₹157,308–₹159,103) |
| RARE-ANTV-EMP-09 | empirical | baseline | 62.4 (59.3–65.5) | 0.0 (0.0–0.0) | 0.920 (0.917–0.923) | ₹142,559 (₹141,310–₹143,808) |
| RARE-ANTV-EMP-09 | empirical | probabilistic | 9.5 (8.6–10.4) | 0.0 (0.0–0.0) | 0.988 (0.987–0.989) | ₹147,748 (₹146,730–₹148,767) |

## Finding

- **Case A — Poisson (low-volume, lumpy demand):** stockout units/yr fall from 69 (baseline) to 15 (probabilistic), a 78.1% reduction, confirming the qualitative result holds under this non-Normal demand shape too.
- **Case B — Gamma (spiky, right-skewed demand):** stockout units/yr fall from 786 (baseline) to 166 (probabilistic), a 78.8% reduction, confirming the qualitative result holds under this non-Normal demand shape too.
- **Case C — Empirical (real historical demand log):** stockout units/yr fall from 62 (baseline) to 9 (probabilistic), a 84.8% reduction, confirming the qualitative result holds under this non-Normal demand shape too.

## Interpretation

The probabilistic policy's advantage over the fixed baseline does **not** depend on demand actually being Normally distributed. Because the policy's safety-stock formula is driven by the SKU's own configured mean and standard deviation (not by an assumption that demand is symmetric or bell-shaped), it continues to correctly size safety stock even when the true demand-generating process is a skewed count process (Poisson), a right-skewed continuous process (Gamma), or an arbitrary real historical pattern (Empirical). This is expected from the underlying theory — the demand-during-lead-time variance formula relies only on the first two moments (mean, variance) of demand, not on its full distributional shape — and this analysis confirms it empirically rather than just asserting it.

**Caveat:** for the Poisson case specifically, at very low means (e.g. mean < 1 unit/day) the Normal-based safety-stock formula can be conservative (over-order) because it cannot represent the sharp lower bound at zero the way Poisson does. For extremely low-volume items, a Poisson-aware safety-stock formula (not just a Poisson-aware simulator) would be a natural next refinement — noted in the risk register as a residual limitation.