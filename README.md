# ER Queue Simulation

Sequential and parallel ER queue simulations with priority scheduling.

This project provides:
- A sequential baseline (single doctor)
- A parallel version (multiple doctors using multiprocessing)
- Deterministic patient generation via a fixed random seed

## How to Run

Sequential (default 10,000 patients):

```bash
python er_queue_sequential.py
python er_queue_sequential.py 100000
python er_queue_sequential.py 1000000
```

Parallel (default 10,000 patients and 4 doctors):

```bash
python er_queue_parallel.py
python er_queue_parallel.py 100000
python er_queue_parallel.py 1000000
```

Custom doctor count (parallel only):

```bash
python er_queue_parallel.py 100000 8
```

### Arguments

- `er_queue_sequential.py [patients]`
- `er_queue_parallel.py [patients] [doctors]`

Both scripts validate that inputs are positive integers.

## What the Simulation Does

- Generates patients with triage priorities 1-5 and random arrival times over an 8-hour window
- Orders patients by priority, then arrival time (FIFO for ties)
- Simulates treatment with a CPU-bound prime-number workload
- Reports performance metrics (execution time, throughput) and per-priority stats
- Parallel version also reports per-doctor workload balance

## Expected Output

Output is deterministic for a given patient count because the random seed is fixed.

### Sequential (example format)

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

Total Execution Time: 12.34 seconds

Average Wait Time per Priority:
  - Priority 1 (Resuscitation): 0.1234s  [1,987 patients]
  - Priority 2 (      Emergent): 0.2345s  [2,011 patients]
  - Priority 3 (        Urgent): 0.3456s  [2,002 patients]
  - Priority 4 (   Less Urgent): 0.4567s  [2,009 patients]
  - Priority 5 (    Non-Urgent): 0.5678s  [1,991 patients]

Throughput: 810 patients/second
==================================================
```

### Parallel (example format)

```text
==========================================================
  ER QUEUE SIMULATION (PARALLEL)
==========================================================
Total Patients Generated  : 10,000
Number of Doctors (Procs) : 4
Random Seed               : 42
Treatment Work            : First 1,000 primes per patient
Parallelism Framework     : multiprocessing.Process + Queue
----------------------------------------------------------
Generating patients... Done.
Sorting patients by priority... Done.

Simulation Started...

Simulation Complete.

Total Execution Time: 15.36 seconds

Doctor Workload Distribution:
  - Doctor  1 handled:    2,525 patients
  - Doctor  2 handled:    2,489 patients
  - Doctor  3 handled:    2,490 patients
  - Doctor  4 handled:    2,496 patients

  Workload balance: 98.6%  (max spread: 36 patients across 4 doctors)

Throughput: 651 patients/second
==========================================================
```

Numbers will vary by machine performance but the format remains the same.

## Project Files

- `er_queue_sequential.py`: single-doctor baseline
- `er_queue_parallel.py`: multi-doctor parallel simulation
