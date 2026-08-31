#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

constexpr int kN = 11;
constexpr int kMaximumStates = 1 << kN;
constexpr std::uint64_t kPrime1 = 1'000'000'007ULL;
constexpr std::uint64_t kPrime2 = 1'000'000'009ULL;
constexpr std::array<char, 8> kInputMagic{'G', '1', '1', '8', 'A', 'B', '1', '\0'};
constexpr std::array<char, 8> kOutputMagic{'G', '1', '1', '8', 'A', 'O', '1', '\0'};

using Direction = std::array<std::int8_t, kN>;

struct Record {
    std::uint8_t declared_active = 0;
    std::uint8_t signed_mass = 0;
    std::array<std::int8_t, kN * kN> weights{};

    std::int8_t at(int row, int column) const {
        return weights[static_cast<std::size_t>(row * kN + column)];
    }
};

struct Term {
    std::uint32_t sequence = 0;
    std::uint64_t coefficient_p1 = 0;
    std::uint64_t coefficient_p2 = 0;
};

struct Input {
    std::vector<Record> records;
    std::vector<Direction> directions;
    std::vector<Term> terms;
    std::uint64_t target_scale_p1 = 0;
    std::uint64_t target_scale_p2 = 0;
};

struct IncrementTable {
    int active = 0;
    int inactive = 0;
    int states = 0;
    std::array<int, kN> vertices{};
    std::array<std::array<std::int8_t, kMaximumStates>, kN> values{};
};

struct NormalForm {
    std::map<Direction, std::int64_t> hinges;
    std::array<std::int64_t, kN> linear{};
    std::size_t raw_words = 0;
};

struct GlobalSummary {
    std::uint64_t labelled_permutations = 0;
    std::size_t raw_histogram_entries = 0;
    std::size_t hinge_entries_processed = 0;
    std::size_t aggregate_hinge_support = 0;
    std::size_t nonzero_hinge_directions = 0;
    std::array<std::array<std::uint64_t, kN>, 2> linear_residues{};
    std::vector<std::pair<Direction, std::array<std::uint64_t, 2>>> selected;
    std::vector<std::array<std::uint64_t, 2>> accumulated_residues;
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string& message) {
    if (!condition) {
        fail(message);
    }
}

std::uint64_t factorial(int value) {
    std::uint64_t result = 1;
    for (int factor = 2; factor <= value; ++factor) {
        result *= static_cast<std::uint64_t>(factor);
    }
    return result;
}

std::uint32_t read_u32(std::istream& stream) {
    std::array<unsigned char, 4> bytes{};
    stream.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    require(stream.good(), "truncated u32");
    std::uint32_t result = 0;
    for (int index = 0; index < 4; ++index) {
        result |= static_cast<std::uint32_t>(bytes[index]) << (8 * index);
    }
    return result;
}

std::uint64_t read_u64(std::istream& stream) {
    std::array<unsigned char, 8> bytes{};
    stream.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    require(stream.good(), "truncated u64");
    std::uint64_t result = 0;
    for (int index = 0; index < 8; ++index) {
        result |= static_cast<std::uint64_t>(bytes[index]) << (8 * index);
    }
    return result;
}

void write_u32(std::ostream& stream, std::uint32_t value) {
    for (int index = 0; index < 4; ++index) {
        stream.put(static_cast<char>((value >> (8 * index)) & 0xffU));
    }
}

void write_i64(std::ostream& stream, std::int64_t value) {
    const auto unsigned_value = static_cast<std::uint64_t>(value);
    for (int index = 0; index < 8; ++index) {
        stream.put(static_cast<char>((unsigned_value >> (8 * index)) & 0xffU));
    }
}

void validate_direction(const Direction& direction) {
    int sum = 0;
    int divisor = 0;
    int first = 0;
    bool saw_first = false;
    bool active = false;
    int prefix = 0;
    for (int index = 0; index < kN; ++index) {
        const int value = static_cast<int>(direction[index]);
        sum += value;
        divisor = std::gcd(divisor, std::abs(value));
        if (!saw_first && value != 0) {
            first = value;
            saw_first = true;
        }
        if (index + 1 < kN) {
            prefix += value;
            active = active || prefix < 0;
        }
    }
    require(sum == 0, "direction is not zero-sum");
    require(saw_first && first > 0, "direction is not first-positive");
    require(divisor == 1, "direction is not primitive");
    require(active, "direction is not active on the ordered cone");
}

void validate_record(const Record& record) {
    require(record.declared_active <= kN, "declared active count exceeds 11");
    require(record.signed_mass <= 5, "signed mass exceeds five");
    int active = 0;
    for (int row = 0; row < kN; ++row) {
        require(record.at(row, row) == 0, "record has a loop");
        bool nonzero = false;
        for (int column = 0; column < kN; ++column) {
            require(record.at(row, column) == record.at(column, row), "record is not symmetric");
            require(std::abs(static_cast<int>(record.at(row, column))) <= 5,
                    "record weight exceeds degree envelope");
            nonzero = nonzero || record.at(row, column) != 0;
        }
        active += nonzero ? 1 : 0;
    }
    require(active == record.declared_active, "record active count drift");
}

Input read_input(const std::string& path) {
    std::ifstream stream(path, std::ios::binary);
    require(stream.good(), "cannot open input descriptor");
    std::array<char, 8> magic{};
    stream.read(magic.data(), static_cast<std::streamsize>(magic.size()));
    require(stream.good() && magic == kInputMagic, "bad input magic");
    const std::uint32_t records = read_u32(stream);
    const std::uint32_t directions = read_u32(stream);
    const std::uint32_t terms = read_u32(stream);
    const std::uint32_t n = read_u32(stream);
    require(n == kN, "input dimension drift");

    Input input;
    input.target_scale_p1 = read_u64(stream);
    input.target_scale_p2 = read_u64(stream);
    require(input.target_scale_p1 < kPrime1 && input.target_scale_p2 < kPrime2,
            "target residue outside field");
    input.records.resize(records);
    for (Record& record : input.records) {
        char active = 0;
        char mass = 0;
        stream.get(active);
        stream.get(mass);
        require(stream.good(), "truncated record header");
        record.declared_active = static_cast<std::uint8_t>(active);
        record.signed_mass = static_cast<std::uint8_t>(mass);
        stream.read(reinterpret_cast<char*>(record.weights.data()),
                    static_cast<std::streamsize>(record.weights.size()));
        require(stream.good(), "truncated record matrix");
        validate_record(record);
    }
    input.directions.resize(directions);
    for (Direction& direction : input.directions) {
        stream.read(reinterpret_cast<char*>(direction.data()),
                    static_cast<std::streamsize>(direction.size()));
        require(stream.good(), "truncated direction");
        validate_direction(direction);
    }
    input.terms.resize(terms);
    std::uint32_t previous = 0;
    bool have_previous = false;
    for (Term& term : input.terms) {
        term.sequence = read_u32(stream);
        term.coefficient_p1 = read_u64(stream);
        term.coefficient_p2 = read_u64(stream);
        require(term.sequence < records, "term sequence outside record census");
        require(term.coefficient_p1 < kPrime1 && term.coefficient_p2 < kPrime2,
                "coefficient residue outside field");
        require(!have_previous || previous < term.sequence, "term sequences are not increasing");
        previous = term.sequence;
        have_previous = true;
    }
    require(stream.peek() == std::char_traits<char>::eof(), "trailing bytes in input descriptor");
    return input;
}

IncrementTable make_increment_table(const Record& record) {
    IncrementTable table;
    for (int vertex = 0; vertex < kN; ++vertex) {
        bool nonzero = false;
        for (int other = 0; other < kN; ++other) {
            nonzero = nonzero || record.at(vertex, other) != 0;
        }
        if (nonzero) {
            table.vertices[table.active++] = vertex;
        }
    }
    require(table.active == record.declared_active, "increment-table active count drift");
    table.inactive = kN - table.active;
    table.states = 1 << table.active;
    for (int local_vertex = 0; local_vertex < table.active; ++local_vertex) {
        const int vertex = table.vertices[local_vertex];
        for (int mask = 1; mask < table.states; ++mask) {
            const int bit = mask & -mask;
            const int other_local = std::countr_zero(static_cast<unsigned int>(bit));
            const int other = table.vertices[other_local];
            const int value = static_cast<int>(table.values[local_vertex][mask ^ bit])
                + static_cast<int>(record.at(vertex, other));
            require(value >= -5 && value <= 5, "increment outside [-5,5]");
            table.values[local_vertex][mask] = static_cast<std::int8_t>(value);
        }
    }
    return table;
}

struct MatchingWorkspace {
    std::array<std::uint64_t, kMaximumStates> first{};
    std::array<std::uint64_t, kMaximumStates> second{};
    std::vector<int> first_masks;
    std::vector<int> second_masks;

    MatchingWorkspace() {
        first_masks.reserve(kMaximumStates);
        second_masks.reserve(kMaximumStates);
    }

    std::uint64_t count(const IncrementTable& table, const Direction& direction, int scale) {
        auto* current = &first;
        auto* next = &second;
        auto* current_masks = &first_masks;
        auto* next_masks = &second_masks;
        require(current_masks->empty() && next_masks->empty(), "matching workspace is dirty");
        (*current)[0] = 1;
        current_masks->push_back(0);
        for (int rank = 0; rank < kN; ++rank) {
            const int expected = scale * static_cast<int>(direction[rank]);
            for (const int mask : *current_masks) {
                const std::uint64_t ways = (*current)[mask];
                (*current)[mask] = 0;
                const int placed = std::popcount(static_cast<unsigned int>(mask));
                require(placed <= rank, "injection mask/rank drift");
                const int inactive_used = rank - placed;
                auto add = [&](int destination, std::uint64_t value) {
                    if ((*next)[destination] == 0) {
                        next_masks->push_back(destination);
                    }
                    (*next)[destination] += value;
                };
                if (expected == 0 && inactive_used < table.inactive) {
                    add(mask, ways);
                }
                for (int vertex = 0; vertex < table.active; ++vertex) {
                    const int bit = 1 << vertex;
                    if ((mask & bit) == 0
                        && static_cast<int>(table.values[vertex][mask]) == expected) {
                        add(mask | bit, ways);
                    }
                }
            }
            current_masks->clear();
            std::swap(current, next);
            std::swap(current_masks, next_masks);
        }
        const int full = table.states - 1;
        const std::uint64_t result = (*current)[full];
        for (const int mask : *current_masks) {
            (*current)[mask] = 0;
        }
        current_masks->clear();
        require(next_masks->empty(), "matching next-mask workspace is dirty");
        return result;
    }
};

std::int64_t targeted_hinge_price(
    const IncrementTable& table,
    const Direction& direction,
    MatchingWorkspace& workspace
) {
    int maximum = 0;
    for (const std::int8_t coordinate : direction) {
        maximum = std::max(maximum, std::abs(static_cast<int>(coordinate)));
    }
    require(maximum > 0, "zero direction reached targeted price");
    const int maximum_scale = 5 / maximum;
    std::uint64_t unlabelled = 0;
    for (int scale = -maximum_scale; scale <= maximum_scale; ++scale) {
        if (scale != 0) {
            unlabelled += static_cast<std::uint64_t>(std::abs(scale))
                * workspace.count(table, direction, scale);
        }
    }
    const std::uint64_t labelled = unlabelled * factorial(table.inactive);
    require(labelled <= static_cast<std::uint64_t>(INT64_MAX), "hinge price overflow");
    return static_cast<std::int64_t>(labelled);
}

std::array<std::int64_t, kN> independent_linear_vector(const IncrementTable& table) {
    using Counts = std::array<std::uint64_t, 3>;
    std::array<Counts, kMaximumStates> first{};
    std::array<Counts, kMaximumStates> second{};
    std::vector<int> first_masks;
    std::vector<int> second_masks;
    first_masks.reserve(table.states);
    second_masks.reserve(table.states);
    first[0][0] = 1;
    first_masks.push_back(0);
    auto* current = &first;
    auto* next = &second;
    auto* current_masks = &first_masks;
    auto* next_masks = &second_masks;
    std::array<__int128, kN> correction{};

    for (int rank = 0; rank < kN; ++rank) {
        for (const int mask : *current_masks) {
            const Counts counts = (*current)[mask];
            (*current)[mask] = Counts{};
            const int placed = std::popcount(static_cast<unsigned int>(mask));
            require(placed <= rank, "linear mask/rank drift");
            const int inactive_used = rank - placed;
            auto add = [&](int destination, int status, std::uint64_t value) {
                const bool empty = (*next)[destination] == Counts{};
                if (empty) {
                    next_masks->push_back(destination);
                }
                (*next)[destination][status] += value;
            };
            for (int status = 0; status < 3; ++status) {
                const std::uint64_t ways = counts[status];
                if (ways == 0) {
                    continue;
                }
                if (inactive_used < table.inactive) {
                    add(mask, status, ways);
                }
                for (int vertex = 0; vertex < table.active; ++vertex) {
                    const int bit = 1 << vertex;
                    if ((mask & bit) != 0) {
                        continue;
                    }
                    const int increment = static_cast<int>(table.values[vertex][mask]);
                    int new_status = status;
                    if (status == 0 && increment != 0) {
                        new_status = increment > 0 ? 1 : 2;
                    }
                    const int new_mask = mask | bit;
                    add(new_mask, new_status, ways);
                    if (new_status == 2) {
                        const int remaining_slots = kN - rank - 1;
                        const int remaining_active = table.active
                            - std::popcount(static_cast<unsigned int>(new_mask));
                        const int remaining_inactive = remaining_slots - remaining_active;
                        require(remaining_inactive >= 0, "negative remaining inactive count");
                        const std::uint64_t completions = factorial(remaining_slots)
                            / factorial(remaining_inactive);
                        correction[rank] += static_cast<__int128>(ways)
                            * static_cast<__int128>(increment)
                            * static_cast<__int128>(completions);
                    }
                }
            }
        }
        current_masks->clear();
        std::swap(current, next);
        std::swap(current_masks, next_masks);
    }
    const int full = table.states - 1;
    const std::uint64_t injections = std::accumulate(
        (*current)[full].begin(), (*current)[full].end(), 0ULL
    );
    require(injections * factorial(table.inactive) == factorial(kN),
            "linear injection census drift");
    const __int128 inactive_multiplier = static_cast<__int128>(factorial(table.inactive));
    std::array<std::int64_t, kN> result{};
    for (int rank = 0; rank < kN; ++rank) {
        const __int128 base = static_cast<__int128>(10 * rank)
            * static_cast<__int128>(factorial(kN - 2));
        const __int128 value = base + correction[rank] * inactive_multiplier;
        require(value >= INT64_MIN && value <= INT64_MAX, "linear coordinate overflow");
        result[rank] = static_cast<std::int64_t>(value);
    }
    return result;
}

Direction normalize_word(
    const std::array<int, kN>& word,
    int& scale,
    bool& negative,
    bool& active
) {
    int sum = 0;
    int first = -1;
    scale = 0;
    for (int index = 0; index < kN; ++index) {
        sum += word[index];
        if (first < 0 && word[index] != 0) {
            first = index;
        }
        scale = std::gcd(scale, std::abs(word[index]));
    }
    require(sum == 0, "raw word is not zero-sum");
    Direction direction{};
    if (first < 0) {
        negative = false;
        active = false;
        scale = 0;
        return direction;
    }
    require(scale > 0 && scale <= 5, "bad primitive scale");
    negative = word[first] < 0;
    int prefix = 0;
    active = false;
    for (int index = 0; index < kN; ++index) {
        const int oriented = negative ? -word[index] : word[index];
        const int value = oriented / scale;
        require(value >= INT8_MIN && value <= INT8_MAX, "direction coordinate overflow");
        direction[index] = static_cast<std::int8_t>(value);
        if (index + 1 < kN) {
            prefix += value;
            active = active || prefix < 0;
        }
    }
    require(direction[first] > 0, "normalization orientation drift");
    return direction;
}

std::uint64_t encode_append(std::uint64_t code, int increment) {
    require(increment >= -5 && increment <= 5, "raw increment outside [-5,5]");
    return code * 11ULL + static_cast<std::uint64_t>(increment + 5);
}

std::array<int, kN> decode_word(std::uint64_t code) {
    std::array<int, kN> word{};
    for (int index = kN - 1; index >= 0; --index) {
        word[index] = static_cast<int>(code % 11ULL) - 5;
        code /= 11ULL;
    }
    require(code == 0, "encoded word length drift");
    return word;
}

std::unordered_map<std::uint64_t, std::uint32_t> raw_histogram(const Record& record) {
    std::array<std::array<std::int8_t, kN>, kMaximumStates> increments{};
    for (int mask = 1; mask < kMaximumStates; ++mask) {
        const int bit = mask & -mask;
        const int other = std::countr_zero(static_cast<unsigned int>(bit));
        for (int vertex = 0; vertex < kN; ++vertex) {
            const int value = static_cast<int>(increments[mask ^ bit][vertex])
                + static_cast<int>(record.at(vertex, other));
            require(value >= -5 && value <= 5, "full increment outside [-5,5]");
            increments[mask][vertex] = static_cast<std::int8_t>(value);
        }
    }
    std::vector<std::unordered_map<std::uint64_t, std::uint32_t>> states(kMaximumStates);
    states[0].emplace(0ULL, 1U);
    for (int mask = 0; mask + 1 < kMaximumStates; ++mask) {
        if (states[mask].empty()) {
            continue;
        }
        auto current = std::move(states[mask]);
        for (const auto& [code, count] : current) {
            for (int vertex = 0; vertex < kN; ++vertex) {
                const int bit = 1 << vertex;
                if ((mask & bit) != 0) {
                    continue;
                }
                const int destination = mask | bit;
                const std::uint64_t next_code = encode_append(
                    code, static_cast<int>(increments[mask][vertex])
                );
                auto [position, inserted] = states[destination].try_emplace(next_code, count);
                if (!inserted) {
                    const std::uint64_t updated = static_cast<std::uint64_t>(position->second) + count;
                    require(updated <= factorial(kN), "histogram count overflow");
                    position->second = static_cast<std::uint32_t>(updated);
                }
            }
        }
    }
    std::uint64_t census = 0;
    for (const auto& entry : states.back()) {
        census += entry.second;
    }
    require(census == factorial(kN), "raw histogram census drift");
    return std::move(states.back());
}

NormalForm full_normal_form(const Record& record) {
    NormalForm form;
    const auto histogram = raw_histogram(record);
    form.raw_words = histogram.size();
    for (int rank = 0; rank < kN; ++rank) {
        form.linear[rank] = static_cast<std::int64_t>(10 * rank * factorial(kN - 2));
    }
    for (const auto& [code, multiplicity_u32] : histogram) {
        const auto word = decode_word(code);
        int scale = 0;
        bool negative = false;
        bool active = false;
        const Direction direction = normalize_word(word, scale, negative, active);
        if (scale == 0) {
            continue;
        }
        const std::int64_t multiplicity = static_cast<std::int64_t>(multiplicity_u32);
        if (negative) {
            for (int rank = 0; rank < kN; ++rank) {
                form.linear[rank] += multiplicity * static_cast<std::int64_t>(word[rank]);
            }
        }
        if (active) {
            form.hinges[direction] += multiplicity * static_cast<std::int64_t>(scale);
        }
    }
    return form;
}

void add_modular_product(
    std::uint64_t& accumulator,
    std::uint64_t coefficient,
    std::int64_t value,
    std::uint64_t prime
) {
    std::int64_t reduced = value % static_cast<std::int64_t>(prime);
    if (reduced < 0) {
        reduced += static_cast<std::int64_t>(prime);
    }
    const std::uint64_t product = coefficient * static_cast<std::uint64_t>(reduced) % prime;
    accumulator = (accumulator + product) % prime;
}

GlobalSummary replay_global(const Input& input, int threads) {
    const auto started = std::chrono::steady_clock::now();
    std::vector<NormalForm> forms(input.terms.size());
    std::atomic<std::size_t> next{0};
    std::vector<std::thread> workers;
    for (int worker = 0; worker < threads; ++worker) {
        workers.emplace_back([&]() {
            while (true) {
                const std::size_t index = next.fetch_add(1);
                if (index >= input.terms.size()) {
                    break;
                }
                forms[index] = full_normal_form(input.records[input.terms[index].sequence]);
            }
        });
    }
    for (auto& worker : workers) {
        worker.join();
    }

    std::map<Direction, std::array<std::uint64_t, 2>> aggregate;
    GlobalSummary summary;
    for (std::size_t index = 0; index < input.terms.size(); ++index) {
        const Term& term = input.terms[index];
        const NormalForm& form = forms[index];
        summary.raw_histogram_entries += form.raw_words;
        summary.hinge_entries_processed += form.hinges.size();
        for (const auto& [direction, value] : form.hinges) {
            auto& residues = aggregate[direction];
            add_modular_product(residues[0], term.coefficient_p1, value, kPrime1);
            add_modular_product(residues[1], term.coefficient_p2, value, kPrime2);
        }
        for (int coordinate = 0; coordinate < kN; ++coordinate) {
            add_modular_product(
                summary.linear_residues[0][coordinate], term.coefficient_p1,
                form.linear[coordinate], kPrime1
            );
            add_modular_product(
                summary.linear_residues[1][coordinate], term.coefficient_p2,
                form.linear[coordinate], kPrime2
            );
        }
    }
    const std::uint64_t target1 = input.target_scale_p1 * (factorial(kN) % kPrime1) % kPrime1;
    const std::uint64_t target2 = input.target_scale_p2 * (factorial(kN) % kPrime2) % kPrime2;
    summary.linear_residues[0][kN - 1] =
        (summary.linear_residues[0][kN - 1] + kPrime1 - target1) % kPrime1;
    summary.linear_residues[1][kN - 1] =
        (summary.linear_residues[1][kN - 1] + kPrime2 - target2) % kPrime2;

    summary.aggregate_hinge_support = aggregate.size();
    for (const auto& [direction, residues] : aggregate) {
        if (residues != std::array<std::uint64_t, 2>{0, 0}) {
            ++summary.nonzero_hinge_directions;
            if (summary.selected.size() < 32) {
                summary.selected.emplace_back(direction, residues);
            }
        }
    }
    require(input.directions.size() >= 4, "missing accumulated directions");
    for (int index = 0; index < 4; ++index) {
        const auto position = aggregate.find(input.directions[index]);
        summary.accumulated_residues.push_back(
            position == aggregate.end()
                ? std::array<std::uint64_t, 2>{0, 0}
                : position->second
        );
    }
    summary.labelled_permutations = static_cast<std::uint64_t>(input.terms.size()) * factorial(kN);
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started
    ).count();
    std::cerr << "clean-room global replay finished in " << elapsed << " seconds\n";
    return summary;
}

std::pair<std::vector<std::int64_t>, std::vector<std::int64_t>> price_all(
    const Input& input,
    int threads
) {
    const std::size_t records = input.records.size();
    const std::size_t directions = input.directions.size();
    std::vector<std::int64_t> hinges(directions * records);
    std::vector<std::int64_t> linears(records * kN);
    std::atomic<std::size_t> next{0};
    std::atomic<std::size_t> completed{0};
    std::vector<std::thread> workers;
    for (int worker = 0; worker < threads; ++worker) {
        workers.emplace_back([&]() {
            MatchingWorkspace workspace;
            while (true) {
                const std::size_t sequence = next.fetch_add(1);
                if (sequence >= records) {
                    break;
                }
                const IncrementTable table = make_increment_table(input.records[sequence]);
                for (std::size_t direction = 0; direction < directions; ++direction) {
                    hinges[direction * records + sequence] = targeted_hinge_price(
                        table, input.directions[direction], workspace
                    );
                }
                const auto linear = independent_linear_vector(table);
                std::copy(linear.begin(), linear.end(), linears.begin() + sequence * kN);
                const std::size_t done = completed.fetch_add(1) + 1;
                if (done % 10'000 == 0 || done == records) {
                    std::cerr << "clean-room exact pricing " << done << '/' << records << '\n';
                }
            }
        });
    }
    for (auto& worker : workers) {
        worker.join();
    }
    return {std::move(hinges), std::move(linears)};
}

void write_output(
    const std::string& path,
    std::size_t records,
    std::size_t directions,
    const std::vector<std::int64_t>& hinges,
    const std::vector<std::int64_t>& linears
) {
    require(hinges.size() == records * directions, "hinge output size drift");
    require(linears.size() == records * kN, "linear output size drift");
    std::ofstream stream(path, std::ios::binary | std::ios::trunc);
    require(stream.good(), "cannot open output stream");
    stream.write(kOutputMagic.data(), static_cast<std::streamsize>(kOutputMagic.size()));
    write_u32(stream, static_cast<std::uint32_t>(records));
    write_u32(stream, static_cast<std::uint32_t>(directions));
    write_u32(stream, kN);
    for (const std::int64_t value : hinges) {
        write_i64(stream, value);
    }
    for (const std::int64_t value : linears) {
        write_i64(stream, value);
    }
    require(stream.good(), "failed to write output stream");
}

void print_direction(const Direction& direction) {
    std::cout << '[';
    for (int index = 0; index < kN; ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << static_cast<int>(direction[index]);
    }
    std::cout << ']';
}

void print_residues(const std::array<std::uint64_t, 2>& residues) {
    std::cout << '[' << residues[0] << ',' << residues[1] << ']';
}

void print_global_json(
    const GlobalSummary& global,
    std::size_t records,
    std::size_t directions,
    std::size_t terms,
    double pricing_seconds
) {
    std::cout << '{';
    std::cout << "\"schema\":\"g0118-iteration4-batch-cleanroom-cpp-v1\",";
    std::cout << "\"result\":\"PASS\",";
    std::cout << "\"records\":" << records << ',';
    std::cout << "\"directions_priced\":" << directions << ',';
    std::cout << "\"terms\":" << terms << ',';
    std::cout << "\"pricing_wall_seconds\":" << pricing_seconds << ',';
    std::cout << "\"global\":{";
    std::cout << "\"labelled_permutations\":" << global.labelled_permutations << ',';
    std::cout << "\"raw_histogram_entries\":" << global.raw_histogram_entries << ',';
    std::cout << "\"hinge_entries_processed\":" << global.hinge_entries_processed << ',';
    std::cout << "\"aggregate_hinge_support\":" << global.aggregate_hinge_support << ',';
    std::cout << "\"nonzero_hinge_directions\":" << global.nonzero_hinge_directions << ',';
    std::cout << "\"linear_residues\":[";
    for (int prime = 0; prime < 2; ++prime) {
        if (prime != 0) {
            std::cout << ',';
        }
        std::cout << '[';
        for (int coordinate = 0; coordinate < kN; ++coordinate) {
            if (coordinate != 0) {
                std::cout << ',';
            }
            std::cout << global.linear_residues[prime][coordinate];
        }
        std::cout << ']';
    }
    std::cout << "],\"accumulated_residues\":[";
    for (std::size_t index = 0; index < global.accumulated_residues.size(); ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        print_residues(global.accumulated_residues[index]);
    }
    std::cout << "],\"selected\":[";
    for (std::size_t index = 0; index < global.selected.size(); ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << "{\"direction\":";
        print_direction(global.selected[index].first);
        std::cout << ",\"residues\":";
        print_residues(global.selected[index].second);
        std::cout << '}';
    }
    std::cout << "]}}\n";
}

std::pair<std::map<Direction, std::int64_t>, std::array<std::int64_t, kN>>
literal_active_injections(const Record& record) {
    const IncrementTable table = make_increment_table(record);
    require(table.active <= 6, "literal self-test is bounded to six active vertices");
    std::map<Direction, std::int64_t> hinges;
    std::array<std::int64_t, kN> correction{};
    std::array<int, kN> word{};
    std::function<void(int, int, int)> visit = [&](int rank, int mask, int inactive_used) {
        if (rank == kN) {
            require(mask == table.states - 1 && inactive_used == table.inactive,
                    "literal injection terminal census drift");
            int scale = 0;
            bool negative = false;
            bool active = false;
            const Direction direction = normalize_word(word, scale, negative, active);
            if (scale != 0) {
                if (negative) {
                    for (int coordinate = 0; coordinate < kN; ++coordinate) {
                        correction[coordinate] += word[coordinate];
                    }
                }
                if (active) {
                    hinges[direction] += scale;
                }
            }
            return;
        }
        if (inactive_used < table.inactive) {
            word[rank] = 0;
            visit(rank + 1, mask, inactive_used + 1);
        }
        for (int vertex = 0; vertex < table.active; ++vertex) {
            const int bit = 1 << vertex;
            if ((mask & bit) == 0) {
                word[rank] = static_cast<int>(table.values[vertex][mask]);
                visit(rank + 1, mask | bit, inactive_used);
            }
        }
    };
    visit(0, 0, 0);
    const std::int64_t inactive_labels = static_cast<std::int64_t>(factorial(table.inactive));
    for (auto& [direction, coefficient] : hinges) {
        (void)direction;
        coefficient *= inactive_labels;
    }
    std::array<std::int64_t, kN> linear{};
    for (int rank = 0; rank < kN; ++rank) {
        linear[rank] = static_cast<std::int64_t>(10 * rank * factorial(kN - 2))
            + correction[rank] * inactive_labels;
    }
    return {hinges, linear};
}

void self_test() {
    Record record;
    record.declared_active = 5;
    record.signed_mass = 2;
    auto add_edge = [&](int u, int v, int sign) {
        record.weights[u * kN + v] = static_cast<std::int8_t>(
            static_cast<int>(record.weights[u * kN + v]) + sign
        );
        record.weights[v * kN + u] = static_cast<std::int8_t>(
            static_cast<int>(record.weights[v * kN + u]) + sign
        );
    };
    add_edge(0, 1, -1);
    add_edge(1, 2, -1);
    add_edge(0, 2, +1);
    add_edge(3, 4, +1);
    validate_record(record);
    const auto [literal_hinges, literal_linear] = literal_active_injections(record);
    const IncrementTable table = make_increment_table(record);
    MatchingWorkspace workspace;
    for (const auto& [direction, expected] : literal_hinges) {
        const std::int64_t observed = targeted_hinge_price(table, direction, workspace);
        require(observed == expected, "targeted hinge DP disagrees with literal injections");
    }
    require(independent_linear_vector(table) == literal_linear,
            "linear DP disagrees with literal injections");
    Record mutant = record;
    mutant.weights[0 * kN + 2] = 0;
    mutant.weights[2 * kN + 0] = 0;
    mutant.weights[0 * kN + 3] = 1;
    mutant.weights[3 * kN + 0] = 1;
    validate_record(mutant);
    const auto mutant_form = literal_active_injections(mutant);
    require(mutant_form.first != literal_hinges || mutant_form.second != literal_linear,
            "edge mutant escaped literal self-test");
    std::cout << "{\"schema\":\"g0118-batch-cleanroom-self-test-v1\","
              << "\"result\":\"PASS\",\"literal_injections\":"
              << factorial(kN) / factorial(kN - record.declared_active)
              << ",\"active_hinges\":" << literal_hinges.size()
              << ",\"targeted_dp_matches_literal\":true,"
              << "\"linear_dp_matches_literal\":true,\"edge_mutant_rejected\":true}\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            self_test();
            return 0;
        }
        require(argc == 4, "usage: cleanroom_batch_audit INPUT.bin OUTPUT.bin THREADS");
        const int threads = std::stoi(argv[3]);
        require(threads >= 1 && threads <= 64, "thread count outside [1,64]");
        const Input input = read_input(argv[1]);

        const auto price_started = std::chrono::steady_clock::now();
        auto [hinges, linears] = price_all(input, threads);
        const double pricing_seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - price_started
        ).count();
        write_output(
            argv[2], input.records.size(), input.directions.size(), hinges, linears
        );
        const GlobalSummary global = replay_global(input, threads);
        print_global_json(
            global, input.records.size(), input.directions.size(), input.terms.size(),
            pricing_seconds
        );
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "cleanroom_batch_audit: " << error.what() << '\n';
        return 1;
    }
}
