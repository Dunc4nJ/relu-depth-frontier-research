#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include <omp.h>

namespace {

constexpr int kN = 9;
using I128 = __int128_t;
using DirectionKey = std::uint32_t;

struct Edge {
  int first;
  int second;
};

struct Term {
  long long scaled_coefficient;
  std::vector<Edge> left;
  std::vector<Edge> right;
};

struct Semantic {
  std::array<long long, kN> linear{};
  std::unordered_map<DirectionKey, long long> hinges;
  std::uint64_t injection_leaves = 0;
  std::uint64_t represented_permutations = 0;
};

[[noreturn]] void fail(const std::string& message) {
  throw std::runtime_error(message);
}

std::string to_string_i128(I128 value) {
  if (value == 0) {
    return "0";
  }
  const bool negative = value < 0;
  __uint128_t magnitude = negative ? static_cast<__uint128_t>(-(value + 1)) + 1
                                   : static_cast<__uint128_t>(value);
  std::string digits;
  while (magnitude != 0) {
    digits.push_back(static_cast<char>('0' + magnitude % 10));
    magnitude /= 10;
  }
  if (negative) {
    digits.push_back('-');
  }
  std::reverse(digits.begin(), digits.end());
  return digits;
}

DirectionKey encode_direction(const std::array<int, kN>& direction) {
  DirectionKey key = 0;
  for (const int value : direction) {
    if (value < -4 || value > 4) {
      fail("primitive direction escaped degree-four digit range");
    }
    key = key * 9U + static_cast<DirectionKey>(value + 4);
  }
  return key;
}

std::array<int, kN> decode_direction(DirectionKey key) {
  std::array<int, kN> direction{};
  for (int index = kN - 1; index >= 0; --index) {
    direction[index] = static_cast<int>(key % 9U) - 4;
    key /= 9U;
  }
  return direction;
}

bool nonpositive_on_ordered_cone(const std::array<int, kN>& direction) {
  int total = 0;
  for (const int value : direction) {
    total += value;
  }
  if (total != 0) {
    fail("direction is not translation invariant");
  }
  int prefix = 0;
  for (int index = 0; index + 1 < kN; ++index) {
    prefix += direction[index];
    if (prefix < 0) {
      return false;
    }
  }
  return true;
}

class OrbitEnumerator {
 public:
  explicit OrbitEnumerator(const Term& term) : term_(term) {
    std::array<bool, kN> present{};
    for (const auto& side : {term_.left, term_.right}) {
      for (const Edge edge : side) {
        present[edge.first] = true;
        present[edge.second] = true;
      }
    }
    for (int vertex = 0; vertex < kN; ++vertex) {
      if (present[vertex]) {
        active_.push_back(vertex);
      }
    }
    factorial_[0] = 1;
    for (int value = 1; value <= kN; ++value) {
      factorial_[value] = factorial_[value - 1] * value;
    }
    inactive_multiplicity_ = factorial_[kN - static_cast<int>(active_.size())];
    position_.fill(-1);
  }

  Semantic run() {
    enumerate(0, 0U);
    result_.represented_permutations =
        result_.injection_leaves * static_cast<std::uint64_t>(inactive_multiplicity_);
    if (result_.represented_permutations != static_cast<std::uint64_t>(factorial_[kN])) {
      fail("injection census does not represent all 9! permutations");
    }
    return std::move(result_);
  }

 private:
  void enumerate(std::size_t active_index, std::uint16_t used_ranks) {
    if (active_index == active_.size()) {
      accumulate_leaf();
      return;
    }
    const int vertex = active_[active_index];
    for (int rank = 0; rank < kN; ++rank) {
      const std::uint16_t bit = static_cast<std::uint16_t>(1U << rank);
      if ((used_ranks & bit) != 0U) {
        continue;
      }
      position_[vertex] = rank;
      enumerate(active_index + 1, static_cast<std::uint16_t>(used_ranks | bit));
    }
    position_[vertex] = -1;
  }

  std::array<int, kN> side_form(const std::vector<Edge>& side) const {
    std::array<int, kN> form{};
    for (const Edge edge : side) {
      const int rank = std::max(position_[edge.first], position_[edge.second]);
      if (rank < 0 || rank >= kN) {
        fail("active endpoint has no assigned rank");
      }
      ++form[rank];
    }
    return form;
  }

  void accumulate_leaf() {
    ++result_.injection_leaves;
    const auto left = side_form(term_.left);
    const auto right = side_form(term_.right);
    const auto& base = std::lexicographical_compare(
                           left.begin(), left.end(), right.begin(), right.end())
                           ? left
                           : right;
    const auto& other = &base == &left ? right : left;
    for (int rank = 0; rank < kN; ++rank) {
      result_.linear[rank] += static_cast<long long>(inactive_multiplicity_) * base[rank];
    }
    std::array<int, kN> direction{};
    bool nonzero = false;
    int divisor = 0;
    for (int rank = 0; rank < kN; ++rank) {
      direction[rank] = other[rank] - base[rank];
      nonzero = nonzero || direction[rank] != 0;
      divisor = std::gcd(divisor, std::abs(direction[rank]));
    }
    if (!nonzero || nonpositive_on_ordered_cone(direction)) {
      return;
    }
    if (divisor <= 0) {
      fail("nonzero direction has nonpositive gcd");
    }
    for (int& value : direction) {
      value /= divisor;
    }
    result_.hinges[encode_direction(direction)] +=
        static_cast<long long>(inactive_multiplicity_) * divisor;
  }

  const Term& term_;
  std::vector<int> active_;
  std::array<int, kN> position_{};
  std::array<long long, kN + 1> factorial_{};
  long long inactive_multiplicity_ = 0;
  Semantic result_;
};

Term read_term() {
  Term term{};
  int degree = 0;
  if (!(std::cin >> term.scaled_coefficient >> degree)) {
    fail("truncated term header");
  }
  if (degree < 1 || degree > 4) {
    fail("term degree outside 1..4");
  }
  auto read_side = [degree]() {
    std::vector<Edge> side;
    side.reserve(static_cast<std::size_t>(degree));
    for (int index = 0; index < degree; ++index) {
      Edge edge{};
      if (!(std::cin >> edge.first >> edge.second)) {
        fail("truncated edge stream");
      }
      if (edge.first < 0 || edge.first >= kN || edge.second < edge.first ||
          edge.second >= kN) {
        fail("edge endpoint/order invalid");
      }
      side.push_back(edge);
    }
    return side;
  };
  term.left = read_side();
  term.right = read_side();
  return term;
}

std::size_t nonzero_hinges(const std::unordered_map<DirectionKey, I128>& hinges) {
  std::size_t count = 0;
  for (const auto& [unused_key, value] : hinges) {
    static_cast<void>(unused_key);
    count += value != 0;
  }
  return count;
}

bool linear_is_target(const std::array<I128, kN>& linear, I128 denominator) {
  for (int rank = 0; rank < kN; ++rank) {
    const I128 expected = rank == kN - 1 ? denominator : 0;
    if (linear[rank] != expected) {
      return false;
    }
  }
  return true;
}

bool mutation_detected(
    const std::array<I128, kN>& linear,
    const std::unordered_map<DirectionKey, I128>& hinges,
    I128 denominator) {
  return !linear_is_target(linear, denominator) || nonzero_hinges(hinges) != 0;
}

void add_scaled(
    std::array<I128, kN>& linear,
    std::unordered_map<DirectionKey, I128>& hinges,
    const Semantic& semantic,
    I128 scale) {
  for (int rank = 0; rank < kN; ++rank) {
    linear[rank] += scale * semantic.linear[rank];
  }
  for (const auto& [key, value] : semantic.hinges) {
    hinges[key] += scale * value;
  }
}

void emit_direction(std::ostream& output, const std::array<int, kN>& direction) {
  output << '[';
  for (int index = 0; index < kN; ++index) {
    if (index != 0) {
      output << ',';
    }
    output << direction[index];
  }
  output << ']';
}

}  // namespace

int main() {
  try {
    int n = 0;
    std::size_t term_count = 0;
    long long denominator = 0;
    if (!(std::cin >> n >> term_count >> denominator)) {
      fail("missing input header");
    }
    if (n != kN || term_count == 0 || denominator <= 0) {
      fail("invalid input header");
    }
    std::vector<Term> terms;
    terms.reserve(term_count);
    for (std::size_t index = 0; index < term_count; ++index) {
      terms.push_back(read_term());
    }
    std::string trailing;
    if (std::cin >> trailing) {
      fail("trailing input after term stream");
    }

    const int thread_count = omp_get_max_threads();
    std::vector<std::array<I128, kN>> thread_linear(static_cast<std::size_t>(thread_count));
    std::vector<std::unordered_map<DirectionKey, I128>> thread_hinges(
        static_cast<std::size_t>(thread_count));
    std::vector<std::uint64_t> thread_injections(static_cast<std::size_t>(thread_count), 0);
    std::vector<std::uint64_t> thread_permutations(static_cast<std::size_t>(thread_count), 0);
    Semantic first_semantic;
    int completed = 0;

#pragma omp parallel for schedule(dynamic, 1)
    for (std::int64_t index = 0; index < static_cast<std::int64_t>(terms.size()); ++index) {
      Semantic semantic = OrbitEnumerator(terms[static_cast<std::size_t>(index)]).run();
      const int thread = omp_get_thread_num();
      add_scaled(
          thread_linear[static_cast<std::size_t>(thread)],
          thread_hinges[static_cast<std::size_t>(thread)],
          semantic,
          static_cast<I128>(terms[static_cast<std::size_t>(index)].scaled_coefficient));
      thread_injections[static_cast<std::size_t>(thread)] += semantic.injection_leaves;
      thread_permutations[static_cast<std::size_t>(thread)] += semantic.represented_permutations;
      if (index == 0) {
        first_semantic = semantic;
      }
#pragma omp atomic update
      ++completed;
      if (completed % 32 == 0 || completed == static_cast<int>(terms.size())) {
#pragma omp critical(progress_output)
        { std::cerr << "LITERAL_ORBIT_REPLAY " << completed << '/' << terms.size() << '\n'; }
      }
    }

    std::array<I128, kN> total_linear{};
    std::unordered_map<DirectionKey, I128> total_hinges;
    std::uint64_t injection_leaves = 0;
    std::uint64_t represented_permutations = 0;
    for (int thread = 0; thread < thread_count; ++thread) {
      for (int rank = 0; rank < kN; ++rank) {
        total_linear[rank] += thread_linear[static_cast<std::size_t>(thread)][rank];
      }
      for (const auto& [key, value] : thread_hinges[static_cast<std::size_t>(thread)]) {
        total_hinges[key] += value;
      }
      injection_leaves += thread_injections[static_cast<std::size_t>(thread)];
      represented_permutations += thread_permutations[static_cast<std::size_t>(thread)];
    }
    const std::size_t hinge_residual_count = nonzero_hinges(total_hinges);
    const bool baseline_pass =
        linear_is_target(total_linear, static_cast<I128>(denominator)) && hinge_residual_count == 0;

    auto coefficient_mutation_linear = total_linear;
    auto coefficient_mutation_hinges = total_hinges;
    add_scaled(
        coefficient_mutation_linear,
        coefficient_mutation_hinges,
        first_semantic,
        static_cast<I128>(denominator));
    const bool coefficient_mutation_rejected = mutation_detected(
        coefficient_mutation_linear,
        coefficient_mutation_hinges,
        static_cast<I128>(denominator));

    Term pair_mutant = terms.front();
    Edge& changed_edge = pair_mutant.left.front();
    const Edge original_edge = changed_edge;
    if (changed_edge.second + 1 < kN) {
      ++changed_edge.second;
    } else if (changed_edge.first > 0) {
      --changed_edge.first;
    } else {
      changed_edge = Edge{0, 1};
    }
    if (changed_edge.first > changed_edge.second) {
      std::swap(changed_edge.first, changed_edge.second);
    }
    if (changed_edge.first == original_edge.first && changed_edge.second == original_edge.second) {
      fail("pair mutation did not change selected edge");
    }
    const Semantic pair_mutant_semantic = OrbitEnumerator(pair_mutant).run();
    auto pair_mutation_linear = total_linear;
    auto pair_mutation_hinges = total_hinges;
    add_scaled(
        pair_mutation_linear,
        pair_mutation_hinges,
        first_semantic,
        -static_cast<I128>(terms.front().scaled_coefficient));
    add_scaled(
        pair_mutation_linear,
        pair_mutation_hinges,
        pair_mutant_semantic,
        static_cast<I128>(terms.front().scaled_coefficient));
    const bool pair_mutation_rejected = mutation_detected(
        pair_mutation_linear,
        pair_mutation_hinges,
        static_cast<I128>(denominator));

    auto changed_target = total_linear;
    changed_target[0] -= static_cast<I128>(denominator);
    const bool linear_target_mutation_rejected =
        !linear_is_target(changed_target, static_cast<I128>(denominator)) || hinge_residual_count != 0;

    DirectionKey first_bad_key = 0;
    I128 first_bad_value = 0;
    if (hinge_residual_count != 0) {
      std::vector<DirectionKey> keys;
      keys.reserve(hinge_residual_count);
      for (const auto& [key, value] : total_hinges) {
        if (value != 0) {
          keys.push_back(key);
        }
      }
      std::sort(keys.begin(), keys.end());
      first_bad_key = keys.front();
      first_bad_value = total_hinges[first_bad_key];
    }

    const bool pass = baseline_pass && coefficient_mutation_rejected && pair_mutation_rejected &&
                      linear_target_mutation_rejected;
    std::cout << "{\"result\":\"" << (pass ? "PASS" : "FAIL") << "\","
              << "\"n\":" << n << ','
              << "\"terms\":" << terms.size() << ','
              << "\"threads\":" << thread_count << ','
              << "\"common_denominator\":\"" << denominator << "\","
              << "\"injection_leaves_evaluated\":" << injection_leaves << ','
              << "\"full_permutations_represented\":" << represented_permutations << ','
              << "\"linear_scaled\":[";
    for (int rank = 0; rank < kN; ++rank) {
      if (rank != 0) {
        std::cout << ',';
      }
      std::cout << '\"' << to_string_i128(total_linear[rank]) << '\"';
    }
    std::cout << "],\"hinge_residual_nonzeros\":" << hinge_residual_count << ','
              << "\"coefficient_plus_one_mutation_rejected\":"
              << (coefficient_mutation_rejected ? "true" : "false") << ','
              << "\"first_pair_edge_mutation_rejected\":"
              << (pair_mutation_rejected ? "true" : "false") << ','
              << "\"target_linear_mutation_rejected\":"
              << (linear_target_mutation_rejected ? "true" : "false");
    if (hinge_residual_count != 0) {
      std::cout << ",\"first_hinge_residual\":{\"direction\":";
      emit_direction(std::cout, decode_direction(first_bad_key));
      std::cout << ",\"scaled_value\":\"" << to_string_i128(first_bad_value) << "\"}";
    }
    std::cout << "}\n";
    return pass ? 0 : 1;
  } catch (const std::exception& error) {
    std::cerr << "literal-orbit-replay: " << error.what() << '\n';
    return 2;
  }
}
