# Review 3 Changes

This document records the changes made in response to the Review 2 feedback.

## 1. More granular testing

Added explicit boundary tests for:

- supplier fill-rate bounds
- service-level bounds
- negative demand inputs
- workforce capacity bounds
- simulation-day bounds

## 2. Input validation

Expanded `src/schema.py` validation for SKU, workforce, and simulation configuration values so invalid inputs fail early.

## 3. Documentation

Added dedicated documentation for:

- testing and CI: `docs/testing.md`
- error handling and validation: `docs/error_handling.md`
- final validation and scope: `docs/final_validation.md`

## 4. Reproducibility

The GitHub Actions workflow runs the test harness across Python 3.10–3.13 and also executes the main experiment and sensitivity-analysis scripts as smoke tests.

## 5. Scope clarification

The README and validation documentation distinguish the current Python simulation/dashboard prototype from production interfaces such as REST APIs and external databases.
