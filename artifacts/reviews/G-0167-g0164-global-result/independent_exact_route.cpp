// G-0167 clean-room exact route.
//
// This implementation receives only declarative records and query directions.  It does not link,
// import, or execute any G-0164/G-0117 producer code.  Its hinge route is a top-down completion
// count over partial vertex injections; its linear route is a separate memoized suffix aggregate.

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

constexpr int kDim = 11;
using Direction = std::array<int, kDim>;

std::uint64_t factorial(int n) {
    std::uint64_t out = 1;
    for (int value = 2; value <= n; ++value) out *= static_cast<std::uint64_t>(value);
    return out;
}

struct Record {
    int sequence = -1;
    int active = 0;
    int mass = 0;
    std::array<std::array<int, kDim>, kDim> edge_weight{};
};

Record read_record() {
    Record record;
    if (!(std::cin >> record.sequence >> record.active >> record.mass)) {
        throw std::runtime_error("could not read record header");
    }
    if (record.sequence < 0 || record.active < 0 || record.active > kDim ||
        record.mass < 0 || record.mass > 5) {
        throw std::runtime_error("record header outside frozen domain");
    }
    for (int sign : {-1, 1}) {
        for (int index = 0; index < record.mass; ++index) {
            int left = -1, right = -1;
            std::cin >> left >> right;
            if (!std::cin || left < 0 || left >= right || right >= record.active) {
                throw std::runtime_error("invalid compact loopless edge");
            }
            record.edge_weight[left][right] += sign;
            record.edge_weight[right][left] += sign;
        }
    }
    return record;
}

bool active_direction(const Direction& direction) {
    int prefix = 0;
    for (int index = 0; index < kDim - 1; ++index) {
        prefix += direction[index];
        if (prefix < 0) return true;
    }
    return false;
}

void validate_direction(const Direction& direction) {
    if (std::accumulate(direction.begin(), direction.end(), 0) != 0) {
        throw std::runtime_error("query direction does not sum to zero");
    }
    auto first = std::find_if(direction.begin(), direction.end(), [](int value) {
        return value != 0;
    });
    if (first == direction.end() || *first <= 0) {
        throw std::runtime_error("query direction is not first-positive");
    }
    int divisor = 0;
    for (int value : direction) divisor = std::gcd(divisor, std::abs(value));
    if (divisor != 1 || !active_direction(direction)) {
        throw std::runtime_error("query direction is nonprimitive or inactive");
    }
}

class ExactRecordRoute {
  public:
    explicit ExactRecordRoute(const Record& record)
        : record_(record), states_(1 << record.active), full_(states_ - 1),
          potentials_(record.active, std::vector<int>(states_, 0)),
          count_value_((kDim + 1) * states_), count_stamp_(count_value_.size(), 0),
          linear_value_((kDim + 1) * states_ * 3),
          linear_stamp_(linear_value_.size(), 0) {
        for (int vertex = 0; vertex < record_.active; ++vertex) {
            for (int mask = 0; mask < states_; ++mask) {
                int value = 0;
                for (int other = 0; other < record_.active; ++other) {
                    if ((mask >> other) & 1) value += record_.edge_weight[vertex][other];
                }
                potentials_[vertex][mask] = value;
            }
        }
    }

    std::int64_t hinge(const Direction& direction) {
        validate_direction(direction);
        std::uint64_t weighted = 0;
        int maximum = 0;
        for (int coordinate : direction) maximum = std::max(maximum, std::abs(coordinate));
        for (int scale = -5; scale <= 5; ++scale) {
            if (scale == 0 || maximum * std::abs(scale) > record_.mass) continue;
            direction_ = &direction;
            scale_ = scale;
            if (++count_epoch_ == 0) {
                std::fill(count_stamp_.begin(), count_stamp_.end(), 0);
                count_epoch_ = 1;
            }
            const std::uint64_t count = matching_suffix(0, 0);
            weighted += static_cast<std::uint64_t>(std::abs(scale)) * count;
        }
        weighted *= factorial(kDim - record_.active);
        if (weighted > static_cast<std::uint64_t>(INT64_MAX)) {
            throw std::runtime_error("hinge coefficient exceeds int64");
        }
        return static_cast<std::int64_t>(weighted);
    }

    std::array<std::int64_t, kDim> linear() {
        if (++linear_epoch_ == 0) {
            std::fill(linear_stamp_.begin(), linear_stamp_.end(), 0);
            linear_epoch_ = 1;
        }
        const LinearAggregate aggregate = negative_suffix(0, 0, 0);
        const std::int64_t inactive_multiplier =
            static_cast<std::int64_t>(factorial(kDim - record_.active));
        std::array<std::int64_t, kDim> output{};
        for (int rank = 0; rank < kDim; ++rank) {
            const std::int64_t base = static_cast<std::int64_t>(2 * 5 * rank) *
                                      static_cast<std::int64_t>(factorial(kDim - 2));
            output[rank] = base + aggregate.coordinate_sum[rank] * inactive_multiplier;
        }
        return output;
    }

  private:
    struct LinearAggregate {
        std::uint64_t negative_count = 0;
        std::array<std::int64_t, kDim> coordinate_sum{};
    };

    const Record& record_;
    int states_;
    int full_;
    std::vector<std::vector<int>> potentials_;
    const Direction* direction_ = nullptr;
    int scale_ = 0;
    std::vector<std::uint64_t> count_value_;
    std::vector<std::uint32_t> count_stamp_;
    std::uint32_t count_epoch_ = 0;
    std::vector<LinearAggregate> linear_value_;
    std::vector<std::uint32_t> linear_stamp_;
    std::uint32_t linear_epoch_ = 0;

    std::uint64_t matching_suffix(int position, int mask) {
        if (position == kDim) return mask == full_ ? 1 : 0;
        const int slot = position * states_ + mask;
        if (count_stamp_[slot] == count_epoch_) return count_value_[slot];
        count_stamp_[slot] = count_epoch_;

        const int expected = scale_ * (*direction_)[position];
        const int placed = __builtin_popcount(static_cast<unsigned>(mask));
        const int inactive_used = position - placed;
        std::uint64_t total = 0;
        if (expected == 0 && inactive_used < kDim - record_.active) {
            total += matching_suffix(position + 1, mask);
        }
        for (int vertex = 0; vertex < record_.active; ++vertex) {
            const int bit = 1 << vertex;
            if ((mask & bit) == 0 && potentials_[vertex][mask] == expected) {
                total += matching_suffix(position + 1, mask | bit);
            }
        }
        count_value_[slot] = total;
        return total;
    }

    static int advance_sign(int status, int value) {
        if (status != 0 || value == 0) return status;
        return value > 0 ? 1 : 2;
    }

    LinearAggregate negative_suffix(int position, int mask, int status) {
        if (position == kDim) {
            LinearAggregate terminal;
            if (mask == full_ && status == 2) terminal.negative_count = 1;
            return terminal;
        }
        const int slot = (position * states_ + mask) * 3 + status;
        if (linear_stamp_[slot] == linear_epoch_) return linear_value_[slot];
        linear_stamp_[slot] = linear_epoch_;
        LinearAggregate output;

        auto include = [&](int value, int next_mask) {
            const LinearAggregate child =
                negative_suffix(position + 1, next_mask, advance_sign(status, value));
            output.negative_count += child.negative_count;
            for (int coordinate = 0; coordinate < kDim; ++coordinate) {
                output.coordinate_sum[coordinate] += child.coordinate_sum[coordinate];
            }
            output.coordinate_sum[position] +=
                static_cast<std::int64_t>(value) *
                static_cast<std::int64_t>(child.negative_count);
        };

        const int placed = __builtin_popcount(static_cast<unsigned>(mask));
        const int inactive_used = position - placed;
        if (inactive_used < kDim - record_.active) include(0, mask);
        for (int vertex = 0; vertex < record_.active; ++vertex) {
            const int bit = 1 << vertex;
            if ((mask & bit) == 0) include(potentials_[vertex][mask], mask | bit);
        }
        linear_value_[slot] = output;
        return output;
    }
};

struct ComputedRow {
    int sequence = -1;
    std::array<std::int64_t, kDim> linear{};
    std::vector<std::int64_t> hinges;
};

using BruteMap = std::map<Direction, std::int64_t>;

std::pair<std::array<std::int64_t, kDim>, BruteMap> brute_form(const Record& record) {
    std::array<std::int64_t, kDim> linear{};
    for (int rank = 0; rank < kDim; ++rank) {
        linear[rank] = static_cast<std::int64_t>(2 * 5 * rank) *
                       static_cast<std::int64_t>(factorial(kDim - 2));
    }
    BruteMap hinges;
    std::array<int, kDim> word{};
    const std::int64_t multiplier = static_cast<std::int64_t>(factorial(kDim - record.active));

    std::function<void(int, int)> visit = [&](int position, int mask) {
        if (position == kDim) {
            auto first = std::find_if(word.begin(), word.end(), [](int value) {
                return value != 0;
            });
            if (first == word.end()) return;
            if (*first < 0) {
                for (int rank = 0; rank < kDim; ++rank) linear[rank] += word[rank] * multiplier;
            }
            int divisor = 0;
            for (int value : word) divisor = std::gcd(divisor, std::abs(value));
            Direction direction{};
            const int sign = *first > 0 ? 1 : -1;
            for (int rank = 0; rank < kDim; ++rank) direction[rank] = sign * word[rank] / divisor;
            if (active_direction(direction)) hinges[direction] += divisor * multiplier;
            return;
        }
        const int placed = __builtin_popcount(static_cast<unsigned>(mask));
        if (position - placed < kDim - record.active) {
            word[position] = 0;
            visit(position + 1, mask);
        }
        for (int vertex = 0; vertex < record.active; ++vertex) {
            const int bit = 1 << vertex;
            if (mask & bit) continue;
            int value = 0;
            for (int other = 0; other < record.active; ++other) {
                if ((mask >> other) & 1) value += record.edge_weight[vertex][other];
            }
            word[position] = value;
            visit(position + 1, mask | bit);
        }
    };
    visit(0, 0);
    return {linear, hinges};
}

void self_test() {
    Record record;
    record.sequence = 0;
    record.active = 6;
    record.mass = 3;
    auto add = [&](int left, int right, int sign) {
        record.edge_weight[left][right] += sign;
        record.edge_weight[right][left] += sign;
    };
    add(0, 1, -1);
    add(1, 2, -1);
    add(3, 4, -1);
    add(0, 2, 1);
    add(2, 5, 1);
    add(4, 5, 1);

    const auto [literal_linear, literal_hinges] = brute_form(record);
    if (literal_hinges.empty()) throw std::runtime_error("self-test fixture has no hinge");
    ExactRecordRoute route(record);
    if (route.linear() != literal_linear) throw std::runtime_error("linear self-test mismatch");
    for (const auto& [direction, expected] : literal_hinges) {
        if (route.hinge(direction) != expected) {
            throw std::runtime_error("hinge self-test mismatch");
        }
    }

    Record mutant = record;
    mutant.edge_weight[0][2] -= 1;
    mutant.edge_weight[2][0] -= 1;
    mutant.edge_weight[0][3] += 1;
    mutant.edge_weight[3][0] += 1;
    if (brute_form(mutant) == std::make_pair(literal_linear, literal_hinges)) {
        throw std::runtime_error("edge mutant escaped self-test");
    }
    std::cout << "SELF_TEST_PASS\n";
}

void compute_matrix() {
    int direction_count = 0;
    std::cin >> direction_count;
    if (!std::cin || direction_count <= 0 || direction_count > 2000) {
        throw std::runtime_error("invalid direction count");
    }
    std::vector<Direction> directions(direction_count);
    for (Direction& direction : directions) {
        for (int& coordinate : direction) std::cin >> coordinate;
        if (!std::cin) throw std::runtime_error("truncated direction input");
        validate_direction(direction);
    }
    if (!std::is_sorted(directions.begin(), directions.end()) ||
        std::adjacent_find(directions.begin(), directions.end()) != directions.end()) {
        throw std::runtime_error("directions must be unique and sorted");
    }

    int record_count = 0;
    std::cin >> record_count;
    if (!std::cin || record_count <= 0 || record_count > 400) {
        throw std::runtime_error("invalid record count");
    }
    std::vector<Record> records;
    records.reserve(record_count);
    for (int index = 0; index < record_count; ++index) records.push_back(read_record());

    std::vector<ComputedRow> output(record_count);
#pragma omp parallel for schedule(dynamic, 1)
    for (int index = 0; index < record_count; ++index) {
        try {
            ExactRecordRoute route(records[index]);
            ComputedRow row;
            row.sequence = records[index].sequence;
            row.linear = route.linear();
            row.hinges.reserve(directions.size());
            for (const Direction& direction : directions) row.hinges.push_back(route.hinge(direction));
            output[index] = std::move(row);
        } catch (const std::exception& error) {
#pragma omp critical
            { std::cerr << "worker error for record " << records[index].sequence << ": " << error.what() << "\n"; }
            std::abort();
        }
    }

    std::cout << "AUDIT_EXACT_ROUTE_V1 " << record_count << ' ' << direction_count << '\n';
    for (const ComputedRow& row : output) {
        std::cout << "R " << row.sequence;
        for (std::int64_t value : row.linear) std::cout << ' ' << value;
        for (std::int64_t value : row.hinges) std::cout << ' ' << value;
        std::cout << '\n';
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: independent_exact_route --self-test|--matrix");
        const std::string mode(argv[1]);
        if (mode == "--self-test") self_test();
        else if (mode == "--matrix") compute_matrix();
        else throw std::runtime_error("unknown mode");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "independent exact route: " << error.what() << '\n';
        return 1;
    }
}
