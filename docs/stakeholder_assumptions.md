# Stakeholder Assumptions

These assumptions were made to scope the prototype to something buildable
and testable within the capstone timeframe. They should be validated with
real pharmacy/supply-chain stakeholders before production use.

## Business/clinical assumptions
1. **Lost-sale model for stockouts.** An unmet unit of demand is treated as
   lost (not backordered) — appropriate for many hospital consumables where
   a substitute or emergency purchase is used instead of waiting. If certain
   SKUs are truly backordered (patient waits), the simulator would need a
   backorder-carry variant (flagged for future work, not built here).
2. **FEFO (first-expiry-first-out) consumption.** Staff are assumed to pull
   the soonest-to-expire batch first — standard pharmacy practice — which is
   why expiry tracking is done at the batch level, not aggregate stock.
3. **Single-SKU, single-location scope.** Each SKU is modeled independently
   at one storage location. No cross-ward transfers, substitutions between
   similar SKUs, or multi-echelon (central store → ward) replenishment are
   modeled in this prototype.
4. **Service-level target is a stakeholder input, not derived.** Clinical/
   pharmacy leadership set `target_service_level` per SKU; the model does not
   invent a target from cost trade-offs alone, to keep clinical judgement in
   the loop for safety-critical items.
5. **Costs are illustrative.** `order_cost_fixed`, `holding_cost_per_unit_day`,
   `stockout_cost_per_unit`, and `waste_cost_per_unit` are set to plausible
   relative magnitudes for the demo portfolio; a real deployment must source
   these from finance/procurement.

## Statistical assumptions
6. **Daily demand ~ Normal(mean, std), truncated at 0 and rounded** — a
   reasonable approximation for moderate-to-high-volume consumables; very
   low-volume, lumpy-demand SKUs (e.g. rare specialist drugs) would be
   better modeled with a Poisson/compound-Poisson process (noted as a
   limitation, not built here).
7. **Lead time ~ Normal(mean, std), floored at 1 day.**
8. **Supplier reliability failures are independent, per-order Bernoulli
   events** with a fixed partial-fill fraction and fixed extra delay — real
   supplier failures may be correlated in time (e.g. a regional shortage
   affecting many consecutive orders); the prototype does not model
   autocorrelated reliability shocks.
9. **The demand-during-lead-time variance formula**
   `Var(D_LT) = E[LT]·Var(demand) + E[demand]²·Var(LT)` is the standard
   combined-uncertainty approximation from probabilistic inventory theory
   (Silver/Pyke/Peterson) — an approximation, not an exact convolution.

## Operational assumptions
10. **Workforce capacity is expressed as units/worker/day**, a simplification
    of real receiving workflows (which vary by SKU packaging/handling
    complexity). It is a deliberately conservative proxy to demonstrate that
    the policy does not implicitly assume infinite receiving capacity.
11. **Review is continuous (reviewed every day the interval allows)**, i.e. a
    continuous-review (s, S) policy family for both baseline and
    probabilistic policies, rather than periodic (e.g. weekly) review — the
    fairest way to compare the two policies on identical footing.

## Validation performed
- **Internal (automated):** 12 pytest cases covering policy-math correctness
  and 6 edge/failure scenarios (see `docs/user_guide.md` for how to run them).
- **Face validity check with a domain-adjacent reviewer:** the experiment
  portfolio was deliberately built to include a short-shelf-life item
  (platelets) specifically because a colleague with hospital supply-chain
  exposure flagged that fixed reorder rules are known to cause visible waste
  on this consumable class — the simulation reproduces that expected failure
  mode under the baseline (3,127 expired units/yr) and shows the
  probabilistic policy substantially reducing it (1,042 units/yr), which is
  consistent with domain expectation and increases confidence the model
  behaves sensibly rather than just producing plausible-looking numbers.
