import heapq
import random
import time
import sys
import math
import multiprocessing
from multiprocessing import Process, Queue
from dataclasses import dataclass, field
from typing import List, Dict


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

RANDOM_SEED = 42   
PRIORITY_LABELS = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
}
_SENTINEL = None


# ─────────────────────────────────────────────
#  PATIENT DATA CLASS
# ─────────────────────────────────────────────

@dataclass(order=True)
class Patient:
    """
    Same Patient definition as Phase 1.
    Sort key: (priority, arrival_time) — Priority 1 is always served first;
    ties broken by earliest arrival (FIFO).
    """
    priority:     int
    arrival_time: float
    patient_id:   int   = field(compare=False)
    wait_time:    float = field(default=0.0, compare=False)


# ─────────────────────────────────────────────
#  PATIENT GENERATOR
# ─────────────────────────────────────────────

def generate_patients(n: int) -> List[Patient]:
    """
    Generate N patients. Uses RANDOM_SEED=42 and the exact same logic as
    Ian's generator so both phases process identical patient sets.
    This is the "Golden Rule" from the spec.
    """
    random.seed(RANDOM_SEED)
    simulation_window = 8 * 3600  # 8-hour ER shift in seconds

    patients = []
    for i in range(n):
        priority     = random.randint(1, 5)
        arrival_time = random.uniform(0, simulation_window)
        patients.append(Patient(
            priority=priority,
            arrival_time=arrival_time,
            patient_id=i + 1,
        ))
    return patients


# ─────────────────────────────────────────────
#  TREATMENT COMPUTATION
# ─────────────────────────────────────────────

def _compute_treatment() -> None:
    """
    CPU-bound treatment simulation: find the first 1,000 prime numbers
    using trial division.

    This is the EXACT algorithm Ian uses in Phase 1, and the same one
    Noel must use in C++. Keeping it identical ensures that any difference
    in execution time between Phase 1 and Phase 2 is purely due to
    parallelism, and any difference between Python and C++ is purely
    due to language performance.

    DO NOT use time.sleep() — sleep yields the CPU and does not measure
    actual computation speed.
    """
    limit        = 1_000
    primes_found = 0
    candidate    = 2

    while primes_found < limit:
        is_prime = True
        for divisor in range(2, int(math.isqrt(candidate)) + 1):
            if candidate % divisor == 0:
                is_prime = False
                break
        if is_prime:
            primes_found += 1
        candidate += 1


# ─────────────────────────────────────────────
#  DOCTOR WORKER PROCESS
# ─────────────────────────────────────────────

def doctor_worker(
    doctor_id:    int,
    work_queue:   Queue,   # shared input  — (priority, arrival_time, patient_id) tuples
    result_queue: Queue,   # shared output — (doctor_id, patient_id, priority) tuples
) -> None:
    """
    A single doctor process.

    Pulls patients from work_queue one at a time, performs CPU-bound
    treatment, then reports the result to result_queue.

    Queue.get() blocks until a patient is available, and is safe to call
    from multiple processes simultaneously — no manual Lock needed here.
    The queue's internal pipe handles concurrent access.

    When the main process has no more patients, it pushes one _SENTINEL
    (None) per doctor. On receiving a sentinel, the doctor exits cleanly.

    Lock placement note:
        We do NOT hold any lock during _compute_treatment(). The lock (inside
        Queue's implementation) is held only for the microseconds it takes to
        pop a patient off the queue. Treatment (milliseconds of CPU work) runs
        fully in parallel across all doctor processes. This is the core design
        that gives us a real speedup.
    """
    patients_treated = 0

    while True:
        item = work_queue.get()       # blocks until a patient or sentinel arrives

        if item is _SENTINEL:         # our signal to stop
            break

        priority, arrival_time, patient_id = item

        # ── CPU-bound treatment (runs in parallel across all doctor processes) ──
        _compute_treatment()
        patients_treated += 1

        # Report result back to main process
        result_queue.put((doctor_id, patient_id, priority))

    # Final report: tell main how many patients this doctor handled
    result_queue.put(("DONE", doctor_id, patients_treated))


# ─────────────────────────────────────────────
#  PARALLEL SIMULATION RUNNER
# ─────────────────────────────────────────────

def run_simulation(n_patients: int, n_doctors: int) -> None:
    """
    Main parallel simulation orchestrator.

    Steps:
      1. Generate patients (same as Phase 1).
      2. Sort patients by (priority, arrival_time) — this is the priority queue.
      3. Push all patients into a multiprocessing.Queue (the shared "waiting room").
      4. Spawn N doctor processes; each pulls from the queue independently.
      5. Collect results and compute metrics.
    """

    print()
    print("=" * 58)
    print("  ER QUEUE SIMULATION (PARALLEL)")
    print("=" * 58)
    print(f"Total Patients Generated  : {n_patients:,}")
    print(f"Number of Doctors (Procs) : {n_doctors}")
    print(f"Random Seed               : {RANDOM_SEED}")
    print(f"Treatment Work            : First 1,000 primes per patient")
    print(f"Parallelism Framework     : multiprocessing.Process + Queue")
    print("-" * 58)

    # ── Step 1: Generate patients ───────────────────────────
    print("Generating patients...", end=" ", flush=True)
    patients = generate_patients(n_patients)
    print("Done.")

    # ── Step 2: Sort into priority order (the priority queue) ──
    # heapq.nsmallest returns all patients sorted by (priority, arrival_time).
    # We push them into the Queue in this order so that Priority-1 patients
    # enter the queue first and are available to doctors immediately.
    print("Sorting patients by priority...", end=" ", flush=True)
    sorted_patients = heapq.nsmallest(
        len(patients),
        patients,
        key=lambda p: (p.priority, p.arrival_time)
    )
    print("Done.")

    # ── Step 3: Set up shared queues ────────────────────────
    # maxsize=0 means unlimited — the queue grows as needed.
    # For very large N, you may tune maxsize to limit memory usage.
    work_queue   = Queue()   # main → doctors: (priority, arrival_time, patient_id)
    result_queue = Queue()   # doctors → main: (doctor_id, patient_id, priority) or DONE

    # Push all patients into the work queue
    for p in sorted_patients:
        work_queue.put((p.priority, p.arrival_time, p.patient_id))

    # Push one sentinel per doctor so each doctor knows when to stop
    for _ in range(n_doctors):
        work_queue.put(_SENTINEL)

    # ── Step 4: Spawn doctor processes ──────────────────────
    print()
    print("Simulation Started...")
    print()

    simulation_start = time.perf_counter()

    processes = []
    for doc_id in range(1, n_doctors + 1):
        p = Process(
            target=doctor_worker,
            args=(doc_id, work_queue, result_queue),
            name=f"Doctor-{doc_id}",
            daemon=True,   # auto-killed if main process exits unexpectedly
        )
        p.start()
        processes.append(p)

    # ── Step 5: Collect results from doctors ────────────────
    # We drain result_queue as doctors produce results.
    # Each doctor sends one ("DONE", doc_id, count) when its loop ends.
    doctor_counts:    Dict[int, int] = {d: 0 for d in range(1, n_doctors + 1)}
    doctors_finished = 0
    total_processed  = 0

    while doctors_finished < n_doctors:
        item = result_queue.get()     # blocks until a result or DONE arrives
        tag  = item[0]

        if tag == "DONE":
            _, doc_id, count = item
            doctors_finished += 1
        else:
            doc_id, patient_id, priority = item
            doctor_counts[doc_id] += 1
            total_processed += 1

    # ── Step 6: Wait for all processes to exit cleanly ──────
    for p in processes:
        p.join()

    simulation_end = time.perf_counter()

    # ── Step 7: Compute & print metrics ─────────────────────
    total_time = simulation_end - simulation_start
    throughput  = total_processed / total_time if total_time > 0 else 0

    print("Simulation Complete.")
    print()
    print(f"Total Execution Time: {total_time:.2f} seconds")
    print()

    print("Doctor Workload Distribution:")
    max_count = max(doctor_counts.values()) if doctor_counts else 1
    for doc_id in range(1, n_doctors + 1):
        count = doctor_counts[doc_id]
        print(f"  - Doctor {doc_id:>2} handled: {count:>8,} patients ")

    # Workload balance metric
    counts = list(doctor_counts.values())
    if len(counts) > 1:
        imbalance   = max(counts) - min(counts)
        avg_load    = sum(counts) / len(counts)
        balance_pct = (1 - imbalance / avg_load) * 100 if avg_load > 0 else 100
        print(
            f"\n  Workload balance: {balance_pct:.1f}%  "
            f"(max spread: {imbalance:,} patients across {n_doctors} doctors)"
        )

    print()
    print(f"Throughput: {throughput:,.0f} patients/second")
    print("=" * 58)
    print()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # REQUIRED on Windows and macOS: without this guard, child processes
    # re-import this module and recursively spawn more processes (a "fork bomb").
    # On Linux (fork-based), it's harmless but still good practice.
    multiprocessing.freeze_support()

    # ── Parse CLI arguments ──────────────────────
    n_patients = 10_000   # default
    n_doctors  = 4        # default

    if len(sys.argv) >= 2:
        try:
            n_patients = int(sys.argv[1])
            if n_patients <= 0:
                raise ValueError
        except ValueError:
            print(f"[ERROR] Patient count must be a positive integer. Got: {sys.argv[1]}")
            sys.exit(1)

    if len(sys.argv) >= 3:
        try:
            n_doctors = int(sys.argv[2])
            if n_doctors <= 0:
                raise ValueError
        except ValueError:
            print(f"[ERROR] Doctor count must be a positive integer. Got: {sys.argv[2]}")
            sys.exit(1)

    # Advisory warning if doctor count exceeds available cores
    cpu_cores = multiprocessing.cpu_count()
    if n_doctors > cpu_cores:
        print(
            f"[WARN] {n_doctors} doctors requested but only {cpu_cores} CPU cores "
            f"available. Performance may plateau or degrade beyond core count."
        )

    run_simulation(n_patients, n_doctors)
