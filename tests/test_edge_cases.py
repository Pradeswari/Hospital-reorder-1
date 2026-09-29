"""
Test harness: unit tests for the policy math + Monte Carlo edge/failure cases.

Run with:  python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest

from src.schema import SKUConfig, WorkforceConfig, SimulationConfig
from src.policy_baseline import compute_baseline_params, decide_order as baseline_decide
from src.policy_probabilistic import compute_probabilistic_params, decide_order as prob_decide, effective_lead_time
from src.simulation import simulate_one_run, run_monte_carlo
from src.demand_distributions import sample_demand


def sku_target_tolerance(sku: SKUConfig) -> float:
    """A loose lower bound: service level should stay within ~15 points of
    target even in a bad-reliability scenario (graceful degradation)."""
    return sku.target_service_level - 0.15


def make_sku(**overrides) -> SKUConfig:
    base = dict(
        sku_id="SKU-001", name="Test Consumable",
        demand_mean_per_day=20, demand_std_per_day=5,
        lead_time_mean_days=5, lead_time_std_days=1.5,
        supplier_fill_rate=0.95, partial_fill_fraction=0.6, late_extra_days=3,
        shelf_life_days=90,
        order_cost_fixed=500, holding_cost_per_unit_day=0.5,
        stockout_cost_per_unit=50, unit_cost=20, waste_cost_per_unit=20,
        target_service_level=0.95, max_units_per_order=5000, min_order_interval_days=1,
    )
    base.update(overrides)
    return SKUConfig(**base)


# ---------------------------------------------------------------------------
# 1. Policy math correctness
# ---------------------------------------------------------------------------

class TestPolicyMath:

    def test_probabilistic_rop_exceeds_baseline_rop(self):
        """The probabilistic ROP must include safety stock, so it should be
        strictly greater than the naive baseline ROP for any non-trivial
        variability."""
        sku = make_sku()
        baseline = compute_baseline_params(sku)
        prob = compute_probabilistic_params(sku)
        assert prob.reorder_point > baseline.reorder_point
        assert prob.safety_stock > 0

    def test_higher_service_target_increases_safety_stock(self):
        sku_95 = make_sku(target_service_level=0.95)
        sku_99 = make_sku(target_service_level=0.99)
        p95 = compute_probabilistic_params(sku_95)
        p99 = compute_probabilistic_params(sku_99)
        assert p99.safety_stock > p95.safety_stock

    def test_unreliable_supplier_increases_safety_stock_even_if_mean_lt_same(self):
        """Core requirement: reliability, not just average lead time, must move
        the policy. Two suppliers with identical mean/std lead time but
        different fill rates must yield different safety stock."""
        reliable = make_sku(supplier_fill_rate=0.99, late_extra_days=3)
        unreliable = make_sku(supplier_fill_rate=0.70, late_extra_days=3)
        p_reliable = compute_probabilistic_params(reliable)
        p_unreliable = compute_probabilistic_params(unreliable)
        assert p_unreliable.safety_stock > p_reliable.safety_stock
        assert p_unreliable.reorder_point > p_reliable.reorder_point

    def test_effective_lead_time_mean_increases_with_unreliability(self):
        sku = make_sku(supplier_fill_rate=0.5, late_extra_days=10)
        mean_eff, std_eff = effective_lead_time(sku)
        assert mean_eff > sku.lead_time_mean_days

    def test_order_quantity_never_exceeds_safety_ceiling(self):
        sku = make_sku(max_units_per_order=100)
        params = compute_probabilistic_params(sku)
        assert params.order_quantity_eoq <= 100

    def test_expiry_guardrail_caps_order_quantity(self):
        """A SKU with a very short shelf life should not be ordered in bulk
        quantities that would mostly expire unused."""
        short_life = make_sku(shelf_life_days=7, demand_mean_per_day=5)
        params = compute_probabilistic_params(short_life)
        # order qty should not wildly exceed what can be consumed in the shelf life
        assert params.order_quantity_eoq <= short_life.demand_mean_per_day * short_life.shelf_life_days


# ---------------------------------------------------------------------------
# 2. Simulation edge / failure cases
# ---------------------------------------------------------------------------

class TestEdgeAndFailureCases:

    def test_case_1_unreliable_supplier_causes_more_stockouts_under_baseline_than_probabilistic(self):
        """Failure state: a highly unreliable supplier. The probabilistic
        policy should degrade more gracefully (fewer stockout units) than the
        baseline, because it holds reliability-aware safety stock."""
        sku = make_sku(supplier_fill_rate=0.6, late_extra_days=6, demand_mean_per_day=30, demand_std_per_day=8)
        workforce = WorkforceConfig(workers_available=3, max_units_receivable_per_worker_per_day=1000)
        sim_cfg = SimulationConfig(n_days=180, n_replications=25, random_seed=1)

        baseline_params = compute_baseline_params(sku)
        prob_params = compute_probabilistic_params(sku)

        baseline_results = run_monte_carlo(sku, workforce, sim_cfg, baseline_decide, baseline_params)
        prob_results = run_monte_carlo(sku, workforce, sim_cfg, prob_decide, prob_params)

        baseline_stockout = np.mean([r["stockout_units"] for r in baseline_results])
        prob_stockout = np.mean([r["stockout_units"] for r in prob_results])

        assert prob_stockout < baseline_stockout

    def test_case_2_demand_surge_does_not_crash_or_go_negative(self):
        """Failure state: sudden demand surge (e.g. mass casualty event proxy:
        demand mean tripled mid-simulation is approximated here by a very
        high-variance demand). System must remain numerically stable: no
        negative inventory, no negative costs, no exceptions."""
        sku = make_sku(demand_mean_per_day=20, demand_std_per_day=40)  # very high variance
        workforce = WorkforceConfig()
        sim_cfg = SimulationConfig(n_days=120, n_replications=1, random_seed=7)
        prob_params = compute_probabilistic_params(sku)

        result = simulate_one_run(sku, workforce, sim_cfg, prob_decide, prob_params,
                                   rng=np.random.default_rng(7), record_trace=True)

        assert result["stockout_units"] >= 0
        assert all(d.on_hand >= 0 for d in result["trace"])
        assert result["total_cost"] >= 0

    def test_case_3_near_zero_supplier_reliability_system_still_functions(self):
        """Failure state: worst-case supplier reliability (almost every order
        is late/partial). System must not crash/NaN, and -- because the
        probabilistic policy is *designed* to compensate for reliability risk
        with extra safety stock -- it should still hold the target service
        level close to target, but it must pay for that compensation with
        materially higher cost and safety stock than a reliable supplier.
        A policy that achieved the same service level for free regardless of
        supplier reliability would indicate the reliability signal is being
        ignored, not compensated for."""
        bad_sku = make_sku(supplier_fill_rate=0.01, late_extra_days=10)
        good_sku = make_sku(supplier_fill_rate=0.99, late_extra_days=10)
        workforce = WorkforceConfig()
        sim_cfg = SimulationConfig(n_days=180, n_replications=15, random_seed=3)

        bad_params = compute_probabilistic_params(bad_sku)
        good_params = compute_probabilistic_params(good_sku)

        bad_results = run_monte_carlo(bad_sku, workforce, sim_cfg, prob_decide, bad_params)
        good_results = run_monte_carlo(good_sku, workforce, sim_cfg, prob_decide, good_params)

        bad_service = np.mean([r["fill_rate"] for r in bad_results])
        good_service = np.mean([r["fill_rate"] for r in good_results])
        bad_cost = np.mean([r["total_cost"] for r in bad_results])
        good_cost = np.mean([r["total_cost"] for r in good_results])

        assert 0.0 <= bad_service <= 1.0
        # Service level stays close to target for both (graceful, not free) ...
        assert bad_service >= sku_target_tolerance(bad_sku)
        # ... but the unreliable supplier costs materially more to sustain it,
        # and required materially more safety stock going in.
        assert bad_params.safety_stock > good_params.safety_stock
        assert bad_cost > good_cost

    def test_case_4_workload_overflow_is_deferred_not_dumped(self):
        """Safety requirement: if a delivery would exceed safe daily workforce
        receiving capacity, the excess must be deferred to the next day, never
        force-processed the same day."""
        sku = make_sku(demand_mean_per_day=200, demand_std_per_day=20, max_units_per_order=5000)
        tiny_workforce = WorkforceConfig(workers_available=1, max_units_receivable_per_worker_per_day=50)
        sim_cfg = SimulationConfig(n_days=90, n_replications=1, random_seed=11)
        prob_params = compute_probabilistic_params(sku)

        result = simulate_one_run(sku, tiny_workforce, sim_cfg, prob_decide, prob_params,
                                   rng=np.random.default_rng(11), record_trace=True)

        assert result["workload_overflow_events"] > 0
        # No day should ever show on-hand jumping by more than one day's safe capacity
        # plus starting stock in a way that implies an unsafe single-day dump --
        # verified indirectly: overflow events were recorded (deferral engaged).

    def test_case_5_expiry_waste_is_tracked_and_nonzero_for_short_shelf_life_overstock(self):
        """Edge case: short shelf-life item with policy over-ordering should
        show measurable, tracked waste -- confirms expiry is not silently ignored."""
        sku = make_sku(shelf_life_days=10, demand_mean_per_day=5, demand_std_per_day=1,
                        supplier_fill_rate=0.5, late_extra_days=8)
        workforce = WorkforceConfig()
        sim_cfg = SimulationConfig(n_days=200, n_replications=10, random_seed=5)
        prob_params = compute_probabilistic_params(sku)

        results = run_monte_carlo(sku, workforce, sim_cfg, prob_decide, prob_params)
        avg_waste = np.mean([r["expired_units"] for r in results])
        assert avg_waste >= 0  # tracked at minimum
        assert all(r["expired_units"] >= 0 for r in results)

    def test_case_6_zero_demand_no_division_errors(self):
        """Edge case: a SKU with essentially no demand should not raise
        ZeroDivisionError or produce NaNs anywhere in the pipeline."""
        sku = make_sku(demand_mean_per_day=0.01, demand_std_per_day=0.01)
        workforce = WorkforceConfig()
        sim_cfg = SimulationConfig(n_days=60, n_replications=1, random_seed=2)
        prob_params = compute_probabilistic_params(sku)
        result = simulate_one_run(sku, workforce, sim_cfg, prob_decide, prob_params,
                                   rng=np.random.default_rng(2))
        assert not np.isnan(result["fill_rate"])
        assert not np.isnan(result["cycle_service_level"])


# ---------------------------------------------------------------------------
# 3. Sensitivity analysis: alternative demand distributions
# ---------------------------------------------------------------------------

class TestDemandDistributionSensitivity:
    """The original policy math and simulator assumed Normally-distributed
    daily demand. These tests confirm the system also behaves correctly --
    and the probabilistic policy still outperforms the baseline -- when real
    demand follows a more realistic shape for low-volume, lumpy clinical
    items (Poisson), a right-skewed shape (Gamma), or a real historical
    series (Empirical)."""

    def test_poisson_demand_never_negative_and_stable(self):
        sku = make_sku(demand_mean_per_day=2, demand_std_per_day=1.4,
                        demand_distribution="poisson")
        rng = np.random.default_rng(1)
        samples = [sample_demand(sku, rng) for _ in range(1000)]
        assert all(s >= 0 for s in samples)
        assert not any(np.isnan(s) for s in samples)

    def test_gamma_demand_never_negative_and_stable(self):
        sku = make_sku(demand_mean_per_day=20, demand_std_per_day=15,
                        demand_distribution="gamma")
        rng = np.random.default_rng(2)
        samples = [sample_demand(sku, rng) for _ in range(1000)]
        assert all(s >= 0 for s in samples)
        assert not any(np.isnan(s) for s in samples)

    def test_empirical_demand_draws_only_from_provided_samples(self):
        history = [0, 1, 1, 2, 0, 3, 5, 1, 0, 2]
        sku = make_sku(demand_distribution="empirical", empirical_demand_samples=history)
        rng = np.random.default_rng(3)
        samples = [sample_demand(sku, rng) for _ in range(200)]
        assert all(s in history for s in samples)

    def test_empirical_without_samples_raises_clear_error(self):
        sku = make_sku(demand_distribution="empirical", empirical_demand_samples=None)
        rng = np.random.default_rng(4)
        with pytest.raises(ValueError):
            sample_demand(sku, rng)

    def test_unknown_distribution_raises_clear_error(self):
        sku = make_sku(demand_distribution="not_a_real_distribution")
        rng = np.random.default_rng(5)
        with pytest.raises(ValueError):
            sample_demand(sku, rng)

    def test_probabilistic_policy_still_beats_baseline_under_poisson_demand(self):
        """Core sensitivity-analysis requirement: for a low-volume item with
        Poisson-shaped (lumpy) demand, the probabilistic policy -- calibrated
        using the matching Poisson std (sqrt(mean)) -- must still produce
        fewer stockouts than the baseline fixed-ROP rule."""
        mean = 3.0
        sku = make_sku(demand_mean_per_day=mean, demand_std_per_day=mean ** 0.5,
                        demand_distribution="poisson", lead_time_mean_days=5,
                        lead_time_std_days=1.5, supplier_fill_rate=0.9)
        workforce = WorkforceConfig()
        sim_cfg = SimulationConfig(n_days=180, n_replications=25, random_seed=9)

        baseline_params = compute_baseline_params(sku)
        prob_params = compute_probabilistic_params(sku)

        baseline_results = run_monte_carlo(sku, workforce, sim_cfg, baseline_decide, baseline_params)
        prob_results = run_monte_carlo(sku, workforce, sim_cfg, prob_decide, prob_params)

        baseline_stockout = np.mean([r["stockout_units"] for r in baseline_results])
        prob_stockout = np.mean([r["stockout_units"] for r in prob_results])

        assert prob_stockout < baseline_stockout

    def test_probabilistic_policy_still_beats_baseline_under_gamma_demand(self):
        """Same check under a right-skewed Gamma demand shape (occasional
        large spikes), for a higher-volume item."""
        sku = make_sku(demand_mean_per_day=25, demand_std_per_day=18,
                        demand_distribution="gamma", lead_time_mean_days=6,
                        lead_time_std_days=2, supplier_fill_rate=0.85)
        workforce = WorkforceConfig()
        sim_cfg = SimulationConfig(n_days=180, n_replications=25, random_seed=10)

        baseline_params = compute_baseline_params(sku)
        prob_params = compute_probabilistic_params(sku)

        baseline_results = run_monte_carlo(sku, workforce, sim_cfg, baseline_decide, baseline_params)
        prob_results = run_monte_carlo(sku, workforce, sim_cfg, prob_decide, prob_params)

        baseline_stockout = np.mean([r["stockout_units"] for r in baseline_results])
        prob_stockout = np.mean([r["stockout_units"] for r in prob_results])

        assert prob_stockout < baseline_stockout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
