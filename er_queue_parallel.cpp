#include <array>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>
#include <algorithm>
#include <numeric>
#include <omp.h>

namespace {
constexpr int RANDOM_SEED = 42;
constexpr int MIN_PRIORITY = 1;
constexpr int MAX_PRIORITY = 5;

struct Patient {
    int priority;
    double arrival_time;
    int patient_id;
    double wait_time;
};

bool compare_patients(const Patient& left, const Patient& right) {
    if (left.priority != right.priority) {
        return left.priority < right.priority; 
    }
    return left.arrival_time < right.arrival_time;
}

std::string format_with_commas(unsigned long long value) {
    std::string digits = std::to_string(value);
    for (int i = static_cast<int>(digits.size()) - 3; i > 0; i -= 3) {
        digits.insert(static_cast<size_t>(i), ",");
    }
    return digits;
}

std::vector<Patient> generate_patients(size_t count) {
    std::mt19937 rng(RANDOM_SEED);
    std::uniform_int_distribution<int> priority_dist(MIN_PRIORITY, MAX_PRIORITY);
    const double simulation_window = 8.0 * 3600.0;
    std::uniform_real_distribution<double> arrival_dist(0.0, simulation_window);

    std::vector<Patient> patients;
    patients.reserve(count);

    for (size_t i = 0; i < count; ++i) {
        patients.push_back(Patient{
            priority_dist(rng),
            arrival_dist(rng),
            static_cast<int>(i + 1),
            0.0,
        });
    }

    return patients;
}

inline void treat_patient(const Patient& patient) {
    (void)patient;
    const int limit = 1000;
    int primes_found = 0;
    int candidate = 2;

    while (primes_found < limit) {
        bool is_prime = true;
        int max_divisor = static_cast<int>(std::sqrt(candidate));
        for (int divisor = 2; divisor <= max_divisor; ++divisor) {
            if (candidate % divisor == 0) {
                is_prime = false;
                break;
            }
        }
        if (is_prime) {
            ++primes_found;
        }
        ++candidate;
    }
}

void run_simulation(size_t patient_count) {
    // Explicitly force OpenMP to spawn exactly 4 threads (Doctors)
    constexpr int target_threads = 4;
    omp_set_num_threads(target_threads);

    std::cout << "==========================================================\n";
    std::cout << "  ER QUEUE SIMULATION (PARALLEL)\n";
    std::cout << "==========================================================\n";
    std::cout << "Total Patients Generated  : " << format_with_commas(patient_count) << "\n";
    std::cout << "Number of Doctors (Procs) : " << target_threads << "\n";
    std::cout << "Random Seed               : " << RANDOM_SEED << "\n";
    std::cout << "Treatment Work            : First 1,000 primes per patient\n";
    std::cout << "Parallelism Framework     : OpenMP Dynamic Loop Multi-Threading\n";
    std::cout << "----------------------------------------------------------\n";

    std::cout << "Generating patients... Done.\n";
    std::cout << "Sorting patients by priority... ";
    std::cout.flush();
    
    auto patients = generate_patients(patient_count);
    std::sort(patients.begin(), patients.end(), compare_patients);
    
    std::cout << "Done.\n\n";
    std::cout << "Simulation Started...\n\n";

    std::vector<size_t> doctor_workload_counts(target_threads, 0);
    std::vector<std::chrono::steady_clock::time_point> thread_clocks(target_threads, std::chrono::steady_clock::now());
    
    auto simulation_start = std::chrono::steady_clock::now();

    #pragma omp parallel
    {
        int thread_id = omp_get_thread_num();
        
        #pragma omp for schedule(dynamic, 16)
        for (size_t i = 0; i < patient_count; ++i) {
            auto& patient = patients[i];
            
            auto normalised_arrival = simulation_start + 
                std::chrono::duration<double>(patient.arrival_time);
            
            double wait_time = 0.0;
            if (thread_clocks[thread_id] > normalised_arrival) {
                wait_time = std::chrono::duration<double>(
                    thread_clocks[thread_id] - normalised_arrival
                ).count();
            }
            
            patient.wait_time = wait_time;
            doctor_workload_counts[thread_id]++;

            treat_patient(patient);

            thread_clocks[thread_id] = std::chrono::steady_clock::now();
        }
    }

    auto simulation_end = std::chrono::steady_clock::now();
    std::cout << "Simulation Complete.\n\n";

    double total_time = std::chrono::duration<double>(simulation_end - simulation_start).count();
    double throughput = total_time > 0.0 ? static_cast<double>(patient_count) / total_time : 0.0;

    std::cout << "Total Execution Time: " << std::fixed << std::setprecision(2) << total_time << " seconds\n\n";
    std::cout << "Doctor Workload Distribution:\n";

    size_t max_workload = 0;
    size_t min_workload = patient_count;

    for (int t = 0; t < target_threads; ++t) {
        size_t handled = doctor_workload_counts[t];
        if (handled > max_workload) max_workload = handled;
        if (handled < min_workload) min_workload = handled;

        std::cout << "  - Doctor  " << (t + 1) << " handled:    " 
                  << std::setw(8) << format_with_commas(handled) << " patients\n";
    }

    size_t spread = max_workload - min_workload;
    double expected_per_doctor = static_cast<double>(patient_count) / target_threads;
    double balance_percentage = (1.0 - (static_cast<double>(spread) / expected_per_doctor)) * 100.0;
    if (balance_percentage < 0.0) balance_percentage = 0.0;

    std::cout << "\n  Workload balance: " << std::fixed << std::setprecision(1) << balance_percentage 
              << "%  (max spread: " << format_with_commas(spread) << " patients across " << target_threads << " doctors)\n\n";

    auto throughput_value = static_cast<unsigned long long>(std::llround(throughput));
    std::cout << "Throughput: " << format_with_commas(throughput_value) << " patients/second\n";
    std::cout << "==========================================================\n";
}
}  // namespace

int main(int argc, char* argv[]) {
    size_t patient_count = 10000; 

    if (argc > 1) {
        try {
            long long parsed = std::stoll(argv[1]);
            if (parsed <= 0) {
                throw std::invalid_argument("non-positive");
            }
            patient_count = static_cast<size_t>(parsed);
        } catch (const std::exception&) {
            std::cout << "[ERROR] Patient count must be a positive integer. Got: " << argv[1] << "\n";
            return 1;
        }
    }

    run_simulation(patient_count);
    return 0;
}