# Before-and-After Comparison: Baseline vs Probabilistic Reorder Policy

Monte Carlo simulation, 200 replications per SKU, 365 simulated days per replication. 95% confidence intervals (t-distribution, across the 200 replications) are shown in brackets alongside each mean.

| SKU | Policy | Stockout units/yr (95% CI) | Expired units/yr (95% CI) | Fill rate | Cycle service level (95% CI) | Total cost/yr (95% CI) | Orders placed/yr | Workload overflow events |
|---|---|---|---|---|---|---|---|---|
| MED-INS-01 | baseline | 516.6 [497.8, 535.4] | 0.0 [0.0, 0.0] | 0.943 | 0.930 [0.928, 0.933] (target 0.98) | ₹554,597 [₹553,013, ₹556,181] | 25.5 | 0.00 |
| MED-INS-01 | probabilistic | 148.8 [142.2, 155.5] | 0.0 [0.0, 0.0] | 0.984 | 0.983 [0.983, 0.984] (target 0.98) | ₹567,875 [₹566,788, ₹568,962] | 46.3 | 0.00 |
| SUT-GEN-02 | baseline | 418.3 [402.5, 434.0] | 0.0 [0.0, 0.0] | 0.971 | 0.959 [0.958, 0.961] (target 0.95) | ₹267,685 [₹266,776, ₹268,594] | 26.1 | 0.00 |
| SUT-GEN-02 | probabilistic | 167.7 [161.1, 174.3] | 0.0 [0.0, 0.0] | 0.988 | 0.987 [0.987, 0.988] (target 0.95) | ₹260,626 [₹260,038, ₹261,214] | 30.4 | 0.00 |
| BLD-BAG-03 | baseline | 450.9 [433.9, 467.8] | 0.0 [0.0, 0.0] | 0.918 | 0.906 [0.903, 0.909] (target 0.97) | ₹266,737 [₹264,733, ₹268,740] | 24.9 | 0.00 |
| BLD-BAG-03 | probabilistic | 103.9 [97.9, 109.9] | 0.0 [0.0, 0.0] | 0.981 | 0.981 [0.980, 0.982] (target 0.97) | ₹258,730 [₹257,886, ₹259,575] | 34.5 | 0.00 |
| PPE-GLV-04 | baseline | 554.6 [530.2, 579.1] | 0.0 [0.0, 0.0] | 0.975 | 0.963 [0.961, 0.964] (target 0.93) | ₹203,205 [₹202,601, ₹203,809] | 26.1 | 24.14 |
| PPE-GLV-04 | probabilistic | 188.9 [179.5, 198.3] | 0.0 [0.0, 0.0] | 0.991 | 0.991 [0.990, 0.991] (target 0.93) | ₹199,979 [₹199,540, ₹200,417] | 25.1 | 23.26 |
| ANT-BIO-05 | baseline | 466.5 [447.4, 485.6] | 0.0 [0.0, 0.0] | 0.929 | 0.919 [0.916, 0.922] (target 0.99) | ₹293,260 [₹289,828, ₹296,692] | 25.1 | 0.00 |
| ANT-BIO-05 | probabilistic | 88.1 [82.0, 94.2] | 0.0 [0.0, 0.0] | 0.987 | 0.987 [0.986, 0.988] (target 0.99) | ₹270,356 [₹269,194, ₹271,519] | 30.6 | 0.00 |
| PLT-CON-06 | baseline | 1073.3 [1065.9, 1080.7] | 3127.3 [3114.2, 3140.3] | 0.632 | 0.633 [0.632, 0.635] (target 0.96) | ₹727,424 [₹725,808, ₹729,040] | 45.2 | 0.00 |
| PLT-CON-06 | probabilistic | 201.8 [195.3, 208.2] | 1042.1 [1030.9, 1053.4] | 0.931 | 0.927 [0.925, 0.929] (target 0.96) | ₹376,415 [₹374,749, ₹378,080] | 94.3 | 0.00 |

## Error analysis (target vs measured cycle service level)

| SKU | Policy | Target service level | Measured service level (95% CI) | Error (measured − target) |
|---|---|---|---|---|
| MED-INS-01 | baseline | 0.98 | 0.930 [0.928, 0.933] | -0.050 |
| MED-INS-01 | probabilistic | 0.98 | 0.983 [0.983, 0.984] | +0.003 |
| SUT-GEN-02 | baseline | 0.95 | 0.959 [0.958, 0.961] | +0.009 |
| SUT-GEN-02 | probabilistic | 0.95 | 0.987 [0.987, 0.988] | +0.037 |
| BLD-BAG-03 | baseline | 0.97 | 0.906 [0.903, 0.909] | -0.064 |
| BLD-BAG-03 | probabilistic | 0.97 | 0.981 [0.980, 0.982] | +0.011 |
| PPE-GLV-04 | baseline | 0.93 | 0.963 [0.961, 0.964] | +0.033 |
| PPE-GLV-04 | probabilistic | 0.93 | 0.991 [0.990, 0.991] | +0.061 |
| ANT-BIO-05 | baseline | 0.99 | 0.919 [0.916, 0.922] | -0.071 |
| ANT-BIO-05 | probabilistic | 0.99 | 0.987 [0.986, 0.988] | -0.003 |
| PLT-CON-06 | baseline | 0.96 | 0.633 [0.632, 0.635] | -0.327 |
| PLT-CON-06 | probabilistic | 0.96 | 0.927 [0.925, 0.929] | -0.033 |

## Headline result (with 95% confidence intervals)

- Portfolio-wide stockout units/yr: baseline 3480 → probabilistic 899 — **74.2% reduction, 95% CI [73.3%, 75.0%]**
- Portfolio-wide expired (wasted) units/yr: baseline 3127 → probabilistic 1042 — **66.7% change, 95% CI [66.3%, 67.0%]**
- Portfolio-wide total cost/yr: baseline ₹2,312,908 → probabilistic ₹1,933,981 — **16.4% change, 95% CI [16.1%, 16.6%]**

The confidence intervals above are computed from paired Monte Carlo replications (each replication index represents the same simulated random year under both policies), which is why they can be fairly narrow even though individual-SKU outcomes vary.