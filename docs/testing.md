# Testing

## Automated test coverage

The project uses pytest for policy logic, simulation behavior, and edge/failure cases.

The Review 3 update expands the existing test suite with explicit input-boundary validation tests. These checks cover invalid supplier reliability, invalid service targets, negative demand inputs, invalid workforce capacity, and invalid simulation settings.

## Continuous integration

GitHub Actions runs the test harness on pushes and pull requests to `main`. The workflow tests Python 3.10, 3.11, 3.12, and 3.13, installs the project requirements, runs:

```text
python -m pytest tests/ -v
```

It also runs the baseline-vs-probabilistic experiment and sensitivity-analysis scripts as smoke tests.

## Test focus

The test suite covers:

- probabilistic reorder-policy calculations
- baseline policy behavior
- demand and lead-time related behavior
- supplier reliability and partial-fill cases
- FEFO/expiry behavior
- workforce receiving-capacity constraints
- zero-demand and other stability cases
- input-boundary validation

For a local run:

```bash
python -m pytest tests/ -v
```
