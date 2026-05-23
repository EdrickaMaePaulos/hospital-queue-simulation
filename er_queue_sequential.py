import heapq
import random
import time
import sys
import math
from dataclasses import dataclass, field
from typing import List, Tuple

RANDOM_SEED = 42          
PRIORITY_LABELS = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
}


# ─────────────────────────────────────────────
#  PATIENT DATA CLASS
# ─────────────────────────────────────────────

@dataclass(order=True)
class Patient:
    """
    Represents a single ER patient.

    The dataclass is ordered so that heapq can compare patients.
    Sort key is (priority, arrival_time) — lower priority number = higher urgency,
    and among equal priorities, earlier arrival is seen first (FIFO).
    """
    priority: int                          # 1–5 (1 is most urgent)
    arrival_time: float                    # simulated timestamp in seconds
    patient_id: int = field(compare=False) # unique ID, excluded from ordering
    wait_time: float = field(default=0.0, compare=False)  # filled in after treatment


# ─────────────────────────────────────────────
#  PATIENT GENERATOR
# ─────────────────────────────────────────────

def generate_patients(n: int) -> List[Patient]:
    """
    Generate N patients with:
      - Unique sequential patient IDs (P0001, P0002, …)
      - Random triage priority (1–5)
      - Simulated arrival time (seconds from simulation start, spread over 8 hours)

    """
    random.seed(RANDOM_SEED)

    patients = []
    simulation_window = 8 * 3600  # 8-hour ER shift in seconds

    for i in range(n):
        priority = random.randint(1, 5)
        # Arrivals distributed across the shift; not guaranteed monotonic —
        # the queue will sort them correctly regardless.
        arrival_time = random.uniform(0, simulation_window)
        patients.append(Patient(
            priority=priority,
            arrival_time=arrival_time,
            patient_id=i + 1,
        ))

    return patients


# ─────────────────────────────────────────────
#  PRIORITY QUEUE BUILDER
# ─────────────────────────────────────────────

def build_priority_queue(patients: List[Patient]) -> list:
    """
    Push all patients into a min-heap.

    heapq in Python is a min-heap, and Patient ordering is (priority, arrival_time),
    so Priority-1 patients with the earliest arrival bubble to the top.
    This satisfies the spec:
      • Lower number = higher urgency = served first
      • FIFO among same-priority patients (earlier arrival_time wins)
    """
    heap = []
    for patient in patients:
        heapq.heappush(heap, patient)
    return heap


# ─────────────────────────────────────────────
#  TREATMENT COMPUTATION
#  (CPU-bound math loop)
# ─────────────────────────────────────────────

def treat_patient(patient: Patient) -> None:
    """
    Simulate treatment with a CPU-bound mathematical operation.

    We calculate the first 1,000 prime numbers using a trial-division
    sieve. This is the EXACT same algorithm that Noel must implement in C++
    so that both simulations spend the same amount of CPU work per patient,
    making execution-time comparisons fair.

    DO NOT use time.sleep() here — sleep yields the CPU and does not
    reflect actual computation performance.
    """
    limit = 1_000
    primes_found = 0
    candidate = 2

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
#  SEQUENTIAL SIMULATION RUNNER
# ─────────────────────────────────────────────

def run_simulation(n_patients: int) -> None:
    """
    Main simulation loop.

    A single 'doctor' (the main thread) pulls patients from the priority
    queue one at a time and treats them sequentially. This is the Phase 1
    baseline that Phase 2 (Edricka's parallel version) will improve upon.
    """

    print()
    print("=" * 50)
    print("  ER QUEUE SIMULATION (SEQUENTIAL)")
    print("=" * 50)
    print(f"Total Patients Generated: {n_patients:,}")
    print(f"Random Seed             : {RANDOM_SEED}")
    print(f"Treatment Work          : First 1,000 primes per patient")
    print("-" * 50)

    # ── Step 1: Generate patients ──────────────────
    print("Generating patients...", end=" ", flush=True)
    patients = generate_patients(n_patients)
    print("Done.")

    # ── Step 2: Build priority queue ───────────────
    print("Building priority queue...", end=" ", flush=True)
    queue = build_priority_queue(patients)
    print("Done.")

    # ── Step 3: Run sequential treatment ───────────
    print()
    print("Simulation Started...")
    print()

    # Metric accumulators
    wait_times_by_priority: dict[int, List[float]] = {p: [] for p in range(1, 6)}
    patients_treated = 0

    simulation_start = time.perf_counter()
    current_clock = simulation_start  # tracks when the doctor becomes free

    while queue:
        patient = heapq.heappop(queue)

        # The doctor becomes available at current_clock.
        # The patient's wait = max(0, current_clock - their simulated arrival).
        # (We normalise arrival_time relative to simulation_start for metric purposes.)
        normalised_arrival = simulation_start + patient.arrival_time
        wait = max(0.0, current_clock - normalised_arrival)
        patient.wait_time = wait
        wait_times_by_priority[patient.priority].append(wait)

        # Treat the patient (CPU-bound work)
        treat_patient(patient)
        patients_treated += 1

        # Doctor is now free
        current_clock = time.perf_counter()

    simulation_end = time.perf_counter()

    # ── Step 4: Compute & print metrics ───────────
    total_time = simulation_end - simulation_start
    throughput = patients_treated / total_time if total_time > 0 else 0

    print("Simulation Complete.")
    print()
    print(f"Total Execution Time: {total_time:.2f} seconds")
    print()
    print("Average Wait Time per Priority:")
    for priority in range(1, 6):
        times = wait_times_by_priority[priority]
        if times:
            avg = sum(times) / len(times)
            label = PRIORITY_LABELS[priority]
            print(f"  - Priority {priority} ({label:>14}): {avg:.4f}s  [{len(times):,} patients]")
        else:
            print(f"  - Priority {priority}: no patients")

    print()
    print(f"Throughput: {throughput:,.0f} patients/second")
    print("=" * 50)
    print()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Accept optional CLI argument for patient count
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
            if n <= 0:
                raise ValueError
        except ValueError:
            print(f"[ERROR] Patient count must be a positive integer. Got: {sys.argv[1]}")
            sys.exit(1)
    else:
        n = 10_000  # sensible default for a quick test run

    run_simulation(n)
