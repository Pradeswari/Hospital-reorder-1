"""
Demand distribution sampling.

This module exists to answer the sensitivity-analysis question directly:
"does the probabilistic policy still outperform the baseline if real demand
does NOT look like a Normal distribution?"

The main simulation (src/simulation.py) was originally built assuming daily
demand ~ Normal(mean, std). That is a reasonable approximation for
high-volume, steady-consumption items (e.g. gloves), but a poor one for
low-volume, "lumpy" clinical demand (e.g. a rare specialist drug used 0-2
times most days, occasionally more). This module adds three alternative,
more realistic shapes so the policy can be stress-tested against them:

  - Poisson:   natural for a count of discrete, relatively rare daily events.
               Cannot go negative; variance is tied to the mean (variance = mean),
               so `demand_std_per_day` is not used for this distribution.
  - Gamma:     continuous, right-skewed, never negative. Parameters are
               moment-matched to the SKU's own (mean, std), so an existing
               SKU config can be tested under a "spikier" shape without
               having to re-derive new parameters by hand.
  - Empirical: resamples directly from a real historical daily-demand series
               (`empirical_demand_samples`), when one is available, instead
               of assuming any parametric shape at all.

All three still return a non-negative, rounded integer number of units, so
they can be dropped into the existing simulation loop with no other changes.
"""

import numpy as np
from src.schema import SKUConfig


def sample_demand(sku: SKUConfig, rng: np.random.Generator) -> float:
    dist = getattr(sku, "demand_distribution", "normal")

    if dist == "normal":
        val = rng.normal(sku.demand_mean_per_day, sku.demand_std_per_day)
        return max(0.0, round(val))

    if dist == "poisson":
        # Poisson is parameterized by its mean alone (lambda); variance = mean.
        # This intentionally does NOT use demand_std_per_day -- that is the
        # point of the sensitivity test: a Poisson-shaped SKU with the same
        # mean has a *different* (usually lower, for low means) variance
        # profile than the Normal assumption implied.
        lam = max(sku.demand_mean_per_day, 0.0)
        return float(rng.poisson(lam))

    if dist == "gamma":
        mean = max(sku.demand_mean_per_day, 1e-6)
        std = max(sku.demand_std_per_day, 1e-6)
        # Moment-match Gamma(shape=k, scale=theta) to (mean, std):
        #   mean = k*theta ,  var = k*theta^2  =>  k = mean^2/var, theta = var/mean
        var = std ** 2
        k = (mean ** 2) / var
        theta = var / mean
        val = rng.gamma(shape=k, scale=theta)
        return max(0.0, round(val))

    if dist == "empirical":
        samples = sku.empirical_demand_samples
        if not samples:
            raise ValueError(
                f"SKU {sku.sku_id}: demand_distribution='empirical' requires "
                f"empirical_demand_samples to be a non-empty list of historical "
                f"daily demand values."
            )
        val = rng.choice(samples)
        return max(0.0, round(float(val)))

    raise ValueError(f"Unknown demand_distribution '{dist}' for SKU {sku.sku_id}")
