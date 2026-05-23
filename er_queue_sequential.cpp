#include <array>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <queue>
#include <random>
#include <string>
#include <vector>

namespace {
constexpr int RANDOM_SEED = 42;
constexpr int MIN_PRIORITY = 1;
constexpr int MAX_PRIORITY = 5;

const std::array<std::string, 6> PRIORITY_LABELS = {
    "",
    "Resuscitation",
    "Emergent",
    "Urgent",
    "Less Urgent",
    "Non-Urgent",
};

struct Patient {
    int priority;
    double arrival_time;
    int patient_id;
    double wait_time;
};

struct PatientCompare {
    bool operator()(const Patient& left, const Patient& right) const {
        if (left.priority != right.priority) {
            return left.priority > right.priority;
        }
        return left.arrival_time > right.arrival_time;
    }
};

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

std::priority_queue<Patient, std::vector<Patient>, PatientCompare> build_priority_queue(
    const std::vector<Patient>& patients) {
    std::priority_queue<Patient, std::vector<Patient>, PatientCompare> queue;
    for (const auto& patient : patients) {
        queue.push(patient);
    }
    return queue;
}

void treat_patient(const Patient& patient) {
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
    std::cout << "\n";
    std::cout << std::string(50, '=') << "\n";
    std::cout << "  ER QUEUE SIMULATION (SEQUENTIAL)\n";
    std::cout << std::string(50, '=') << "\n";
    std::cout << "Total Patients Generated: " << format_with_commas(patient_count) << "\n";
    std::cout << "Random Seed             : " << RANDOM_SEED << "\n";
    std::cout << "Treatment Work          : First 1,000 primes per patient\n";
    std::cout << std::string(50, '-') << "\n";

    std::cout << "Generating patients..." << std::flush;
    auto patients = generate_patients(patient_count);
    std::cout << " Done.\n";

    std::cout << "Building priority queue..." << std::flush;
    auto queue = build_priority_queue(patients);
    std::cout << " Done.\n";

    std::cout << "\n";
    std::cout << "Simulation Started...\n\n";

    std::vector<std::vector<double>> wait_times_by_priority(MAX_PRIORITY + 1);
    size_t patients_treated = 0;

    auto simulation_start = std::chrono::steady_clock::now();
    auto current_clock = simulation_start;

    while (!queue.empty()) {
        auto patient = queue.top();
        queue.pop();

        auto normalised_arrival = simulation_start +
            std::chrono::duration<double>(patient.arrival_time);
        double wait_time = 0.0;
        if (current_clock > normalised_arrival) {
            wait_time = std::chrono::duration<double>(current_clock - normalised_arrival).count();
        }
        patient.wait_time = wait_time;
        wait_times_by_priority[patient.priority].push_back(wait_time);

        treat_patient(patient);
        ++patients_treated;

        current_clock = std::chrono::steady_clock::now();
    }

    auto simulation_end = std::chrono::steady_clock::now();
    double total_time =
        std::chrono::duration<double>(simulation_end - simulation_start).count();
    double throughput = total_time > 0.0
        ? static_cast<double>(patients_treated) / total_time
        : 0.0;

    std::cout << "Simulation Complete.\n\n";
    std::cout << "Total Execution Time: " << std::fixed << std::setprecision(2)
              << total_time << " seconds\n\n";
    std::cout << "Average Wait Time per Priority:\n";

    for (int priority = MIN_PRIORITY; priority <= MAX_PRIORITY; ++priority) {
        const auto& times = wait_times_by_priority[priority];
        if (!times.empty()) {
            double sum = 0.0;
            for (double value : times) {
                sum += value;
            }
            double average = sum / static_cast<double>(times.size());
            std::cout << "  - Priority " << priority << " (" << std::setw(14)
                      << PRIORITY_LABELS[priority] << "): " << std::fixed
                      << std::setprecision(4) << average << "s  ["
                      << format_with_commas(times.size()) << " patients]\n";
        } else {
            std::cout << "  - Priority " << priority << ": no patients\n";
        }
    }

    auto throughput_value = static_cast<unsigned long long>(std::llround(throughput));
    std::cout << "\nThroughput: " << format_with_commas(throughput_value)
              << " patients/second\n";
    std::cout << std::string(50, '=') << "\n\n";
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
            std::cout << "[ERROR] Patient count must be a positive integer. Got: "
                      << argv[1] << "\n";
            return 1;
        }
    }

    run_simulation(patient_count);
    return 0;
}
