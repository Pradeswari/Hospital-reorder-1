# Error Handling and Input Validation

The project validates configuration inputs before simulation and policy calculations. The goal is to fail early with clear validation errors instead of silently accepting invalid operational assumptions.

## SKU configuration

Validation covers:

- non-empty SKU and name
- non-negative demand mean and demand standard deviation
- positive lead-time mean and non-negative lead-time standard deviation
- supplier fill rate between 0 and 1
- partial-fill fraction between 0 and 1
- non-negative late-delivery extra days
- positive shelf life
- non-negative cost parameters
- service target strictly between 0 and 1
- positive order-size and order-interval limits
- supported demand distributions: normal, poisson, gamma, or empirical
- non-negative empirical demand samples

## Workforce configuration

The workforce configuration requires:

- workers available > 0
- receiving capacity per worker per day > 0
- order-line capacity per worker per day > 0

## Simulation configuration

Simulation settings require:

- number of days > 0
- number of replications > 0

These checks make invalid or impossible configurations explicit at the configuration boundary and are exercised by the automated test suite.
