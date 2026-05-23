# Queue System Results Review

## Overview
This document analyzes and reviews the results from the Python and C++ queueing system runs.

## Environment
- OS: Linux
- Shell: zsh
- Project: hospital-queue-simulation

## Python Result (Raw Output)
```text
==================================================
  ER QUEUE SIMULATION (SEQUENTIAL)
==================================================
Total Patients Generated: 10,000
Random Seed             : 42
Treatment Work          : First 1,000 primes per patient
--------------------------------------------------
Generating patients... Done.
Building priority queue... Done.

Simulation Started...

Simulation Complete.

Total Execution Time: 26.00 seconds

Average Wait Time per Priority:
  - Priority 1 ( Resuscitation): 0.0000s  [2,040 patients]
  - Priority 2 (      Emergent): 0.0000s  [1,967 patients]
  - Priority 3 (        Urgent): 0.0000s  [1,920 patients]
  - Priority 4 (   Less Urgent): 0.0043s  [2,057 patients]
  - Priority 5 (    Non-Urgent): 0.0154s  [2,016 patients]

Throughput: 385 patients/second
==================================================
```

## C++ Result (Raw Output)
```text
==================================================
  ER QUEUE SIMULATION (SEQUENTIAL)
==================================================
Total Patients Generated: 10,000
Random Seed             : 42
Treatment Work          : First 1,000 primes per patient
--------------------------------------------------
Generating patients... Done.
Building priority queue... Done.

Simulation Started...

Simulation Complete.

Total Execution Time: 2.35 seconds

Average Wait Time per Priority:
  - Priority 1 ( Resuscitation): 0.0000s  [1,948 patients]
  - Priority 2 (      Emergent): 0.0000s  [1,995 patients]
  - Priority 3 (        Urgent): 0.0000s  [2,012 patients]
  - Priority 4 (   Less Urgent): 0.0005s  [2,026 patients]
  - Priority 5 (    Non-Urgent): 0.0000s  [2,019 patients]

Throughput: 4,252 patients/second
==================================================
```

## Summary of Key Metrics
| Metric | Python | C++ | Notes |
|---|---:|---:|---|
| Total Patients | 10,000 | 10,000 | |
| Random Seed | 42 | 42 | |
| Treatment Work | First 1,000 primes per patient | First 1,000 primes per patient | |
| Total Execution Time (s) | 26.00 | 2.35 | |
| Throughput (patients/s) | 385 | 4,252 | |

## Wait Time by Priority

- Python:
  - P1: 0.0000s [2,040]
  - P2: 0.0000s [1,967]
  - P3: 0.0000s [1,920]
  - P4: 0.0043s [2,057]
  - P5: 0.0154s [2,016]

- C++:
  - P1: 0.0000s [1,948]
  - P2: 0.0000s [1,995]
  - P3: 0.0000s [2,012]
  - P4: 0.0005s [2,026]
  - P5: 0.0000s [2,019]

## Comparative Analysis
- Performance: C++ completes in 2.35s vs Python at 26.00s, roughly 11x faster; throughput scales accordingly (4,252 vs 385 patients/s).
- Queue behavior: both runs show near-zero waits for higher priorities and slightly higher waits for lower priorities, consistent with priority + FIFO scheduling.
- Priority fairness: no signs of starvation; lower priorities wait longer as expected, but still minimal overall.
- Any anomalies: patient counts by priority differ between Python and C++, likely due to different RNG implementations despite the same seed.

## Likely Causes of Differences
- C++ CPU performance and compiler optimizations reduce the cost of the prime calculation compared to Python.
- Different RNG algorithms (Python Mersenne Twister vs C++ standard library distributions) yield different priority mixes.
- Timing granularity and steady clock behavior can make tiny waits appear as zero in the faster C++ run.

## Recommendations
- If matching patient distributions is required, serialize the generated patients from one language and reuse them in the other.
- Capture multiple runs and average timings to reduce noise from system load.
- Record compiler flags and Python version when reporting comparisons.

## Reproduction Steps
1. python er_queue_sequential.py 10000
2. ./er_queue_sequential 10000
