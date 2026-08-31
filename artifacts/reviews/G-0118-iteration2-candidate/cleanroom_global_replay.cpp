#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

constexpr int kGlobalN = 11;
constexpr std::uint64_t kPrime1 = 1'000'000'007ULL;
constexpr std::uint64_t kPrime2 = 1'000'000'009ULL;
constexpr int kBranchEdges = 5;

using Direction = std::array<std::int8_t, kGlobalN>;

struct Graph {
    int n = 0;
    std::array<std::array<std::int8_t, kGlobalN>, kGlobalN> weights{};
};

struct Term {
    int sequence = -1;
    std::uint64_t coefficient_mod_p1 = 0;
    std::uint64_t coefficient_mod_p2 = 0;
    int declared_active_vertices = 0;
    int signed_mass = 0;
    Graph graph;
};

struct NormalForm {
    std::map<Direction, std::int64_t> hinges;
    std::array<std::int64_t, kGlobalN> linear{};
    std::size_t raw_histogram_entries = 0;
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

std::uint64_t factorial(int n) {
    std::uint64_t value = 1;
    for (int i = 2; i <= n; ++i) {
        value *= static_cast<std::uint64_t>(i);
    }
    return value;
}

std::uint64_t encode_append(std::uint64_t code, int increment) {
    if (increment < -5 || increment > 5) {
        fail("raw back-degree increment outside [-5,5]");
    }
    return code * 11ULL + static_cast<std::uint64_t>(increment + 5);
}

std::array<int, kGlobalN> decode_word(std::uint64_t code, int n) {
    std::array<int, kGlobalN> word{};
    for (int index = n - 1; index >= 0; --index) {
        word[index] = static_cast<int>(code % 11ULL) - 5;
        code /= 11ULL;
    }
    if (code != 0) {
        fail("raw-word code overflow/length mismatch");
    }
    return word;
}

void add_edge(Graph& graph, int u, int v, int sign) {
    if (u < 0 || v < 0 || u >= graph.n || v >= graph.n) {
        fail("edge endpoint outside graph range");
    }
    if (u == v) {
        fail("the G-0118 selected family is required to be loopless");
    }
    const int uv = static_cast<int>(graph.weights[u][v]) + sign;
    const int vu = static_cast<int>(graph.weights[v][u]) + sign;
    if (uv < -5 || uv > 5 || vu < -5 || vu > 5) {
        fail("signed edge multiplicity outside supported degree-five range");
    }
    graph.weights[u][v] = static_cast<std::int8_t>(uv);
    graph.weights[v][u] = static_cast<std::int8_t>(vu);
}

int active_vertex_count(const Graph& graph) {
    int active = 0;
    for (int vertex = 0; vertex < graph.n; ++vertex) {
        bool nonzero = false;
        for (int other = 0; other < graph.n; ++other) {
            nonzero = nonzero || graph.weights[vertex][other] != 0;
        }
        active += nonzero ? 1 : 0;
    }
    return active;
}

std::unordered_map<std::uint64_t, std::uint32_t> subset_histogram(
    const Graph& graph
) {
    if (graph.n <= 0 || graph.n > kGlobalN) {
        fail("unsupported graph order");
    }
    const int state_count = 1 << graph.n;
    const int full = state_count - 1;

    std::vector<std::array<std::int8_t, kGlobalN>> increments(state_count);
    for (int mask = 0; mask < state_count; ++mask) {
        for (int vertex = 0; vertex < graph.n; ++vertex) {
            int value = static_cast<int>(graph.weights[vertex][vertex]);
            for (int other = 0; other < graph.n; ++other) {
                if ((mask & (1 << other)) != 0) {
                    value += static_cast<int>(graph.weights[vertex][other]);
                }
            }
            if (value < -5 || value > 5) {
                fail("precomputed back-degree increment outside [-5,5]");
            }
            increments[mask][vertex] = static_cast<std::int8_t>(value);
        }
    }

    std::vector<std::unordered_map<std::uint64_t, std::uint32_t>> states(state_count);
    states[0].emplace(0ULL, 1U);
    for (int mask = 0; mask < full; ++mask) {
        if (states[mask].empty()) {
            continue;
        }
        auto current = std::move(states[mask]);
        for (const auto& [code, count] : current) {
            for (int vertex = 0; vertex < graph.n; ++vertex) {
                if ((mask & (1 << vertex)) != 0) {
                    continue;
                }
                const int next_mask = mask | (1 << vertex);
                const std::uint64_t next_code = encode_append(
                    code, static_cast<int>(increments[mask][vertex])
                );
                auto [position, inserted] = states[next_mask].try_emplace(next_code, count);
                if (!inserted) {
                    const std::uint64_t updated =
                        static_cast<std::uint64_t>(position->second) + count;
                    if (updated > factorial(graph.n)) {
                        fail("histogram multiplicity overflow");
                    }
                    position->second = static_cast<std::uint32_t>(updated);
                }
            }
        }
    }

    std::uint64_t census = 0;
    for (const auto& [code, count] : states[full]) {
        (void)code;
        census += count;
    }
    if (census != factorial(graph.n)) {
        fail("subset histogram does not reconcile to n!");
    }
    return std::move(states[full]);
}

NormalForm normal_form(const Graph& graph, int branch_edges) {
    NormalForm result;
    const auto histogram = subset_histogram(graph);
    result.raw_histogram_entries = histogram.size();

    if (branch_edges != 0) {
        if (graph.n != kGlobalN || branch_edges != kBranchEdges) {
            fail("base-linear formula is frozen only for the 11-variable degree-five family");
        }
        const std::int64_t nine_factorial =
            static_cast<std::int64_t>(factorial(kGlobalN - 2));
        for (int rank = 0; rank < graph.n; ++rank) {
            result.linear[rank] =
                static_cast<std::int64_t>(2 * branch_edges * rank) * nine_factorial;
        }
    }

    for (const auto& [code, multiplicity_u32] : histogram) {
        const auto word = decode_word(code, graph.n);
        const int sum = std::accumulate(word.begin(), word.begin() + graph.n, 0);
        if (sum != 0) {
            fail("raw word is not zero-sum");
        }

        int first = -1;
        for (int index = 0; index < graph.n; ++index) {
            if (word[index] != 0) {
                first = index;
                break;
            }
        }
        if (first < 0) {
            continue;
        }

        int scale = 0;
        for (int index = 0; index < graph.n; ++index) {
            scale = std::gcd(scale, std::abs(word[index]));
        }
        if (scale <= 0 || scale > 5) {
            fail("invalid primitive-direction scale");
        }

        const bool negative_orientation = word[first] < 0;
        Direction direction{};
        for (int index = 0; index < graph.n; ++index) {
            const int oriented = negative_orientation ? -word[index] : word[index];
            direction[index] = static_cast<std::int8_t>(oriented / scale);
        }
        if (direction[first] <= 0) {
            fail("primitive orientation is not first-positive");
        }

        bool active = false;
        int prefix = 0;
        for (int index = 0; index + 1 < graph.n; ++index) {
            prefix += static_cast<int>(direction[index]);
            active = active || prefix < 0;
        }

        const std::int64_t multiplicity = static_cast<std::int64_t>(multiplicity_u32);
        if (negative_orientation) {
            for (int index = 0; index < graph.n; ++index) {
                result.linear[index] += multiplicity * word[index];
            }
        }
        if (active) {
            result.hinges[direction] += multiplicity * scale;
        }
    }
    return result;
}

std::unordered_map<std::uint64_t, std::uint32_t> literal_histogram(
    const Graph& graph
) {
    if (graph.n > 8) {
        fail("literal self-test histogram is intentionally bounded to n<=8");
    }
    std::vector<int> order(graph.n);
    std::iota(order.begin(), order.end(), 0);
    std::unordered_map<std::uint64_t, std::uint32_t> result;
    do {
        int mask = 0;
        std::uint64_t code = 0;
        for (const int vertex : order) {
            int increment = static_cast<int>(graph.weights[vertex][vertex]);
            for (int other = 0; other < graph.n; ++other) {
                if ((mask & (1 << other)) != 0) {
                    increment += static_cast<int>(graph.weights[vertex][other]);
                }
            }
            code = encode_append(code, increment);
            mask |= 1 << vertex;
        }
        ++result[code];
    } while (std::next_permutation(order.begin(), order.end()));
    return result;
}

std::int64_t evaluate_raw_histogram(
    const Graph& graph,
    const std::unordered_map<std::uint64_t, std::uint32_t>& histogram,
    const std::array<std::int64_t, kGlobalN>& x
) {
    std::int64_t value = 0;
    for (const auto& [code, count] : histogram) {
        const auto word = decode_word(code, graph.n);
        std::int64_t dot = 0;
        for (int index = 0; index < graph.n; ++index) {
            dot += static_cast<std::int64_t>(word[index]) * x[index];
        }
        value += static_cast<std::int64_t>(count) * std::max<std::int64_t>(dot, 0);
    }
    return value;
}

std::int64_t evaluate_normal_form(
    const NormalForm& form,
    int n,
    const std::array<std::int64_t, kGlobalN>& x,
    bool include_linear
) {
    std::int64_t value = 0;
    for (const auto& [direction, coefficient] : form.hinges) {
        std::int64_t dot = 0;
        for (int index = 0; index < n; ++index) {
            dot += static_cast<std::int64_t>(direction[index]) * x[index];
        }
        value += coefficient * std::max<std::int64_t>(dot, 0);
    }
    if (include_linear) {
        for (int index = 0; index < n; ++index) {
            value += form.linear[index] * x[index];
        }
    }
    return value;
}

Graph relabel_graph(const Graph& graph, const std::vector<int>& old_to_new) {
    if (static_cast<int>(old_to_new.size()) != graph.n) {
        fail("bad relabelling size");
    }
    Graph result;
    result.n = graph.n;
    for (int old_u = 0; old_u < graph.n; ++old_u) {
        for (int old_v = 0; old_v < graph.n; ++old_v) {
            result.weights[old_to_new[old_u]][old_to_new[old_v]] =
                graph.weights[old_u][old_v];
        }
    }
    return result;
}

void run_self_test() {
    Graph graph;
    graph.n = 5;
    add_edge(graph, 0, 1, -1);
    add_edge(graph, 1, 2, -1);
    add_edge(graph, 0, 2, +1);
    add_edge(graph, 3, 4, +1);

    const auto dynamic = subset_histogram(graph);
    const auto literal = literal_histogram(graph);
    if (dynamic != literal) {
        fail("planted literal-permutation differential did not match subset DP");
    }

    const NormalForm form = normal_form(graph, 0);
    const std::array<std::array<std::int64_t, kGlobalN>, 3> probes{{
        {{-3, -1, 2, 6, 11, 0, 0, 0, 0, 0, 0}},
        {{0, 1, 3, 7, 12, 0, 0, 0, 0, 0, 0}},
        {{-8, -2, -1, 4, 15, 0, 0, 0, 0, 0, 0}},
    }};
    bool omission_caught = false;
    for (const auto& x : probes) {
        const std::int64_t expected = evaluate_raw_histogram(graph, literal, x);
        const std::int64_t observed = evaluate_normal_form(form, graph.n, x, true);
        if (expected != observed) {
            fail("normal form failed literal ordered-point evaluation");
        }
        omission_caught = omission_caught ||
            evaluate_normal_form(form, graph.n, x, false) != expected;
    }
    if (!omission_caught) {
        fail("linear-correction omission plant escaped");
    }

    const std::vector<int> permutation{4, 1, 2, 3, 0};
    const NormalForm relabelled = normal_form(relabel_graph(graph, permutation), 0);
    if (relabelled.hinges != form.hinges || relabelled.linear != form.linear) {
        fail("vertex relabelling changed the full-orbit normal form");
    }

    Graph mutant = graph;
    add_edge(mutant, 3, 4, -1);
    add_edge(mutant, 2, 3, +1);
    const NormalForm mutated = normal_form(mutant, 0);
    if (mutated.hinges == form.hinges && mutated.linear == form.linear) {
        fail("equality-destroying edge mutant escaped");
    }

    std::cout
        << "{\"schema\":\"g0118-iteration2-cleanroom-global-self-test-v1\","
        << "\"result\":\"PASS\","
        << "\"literal_permutations\":" << factorial(graph.n) << ","
        << "\"raw_words\":" << literal.size() << ","
        << "\"active_hinges\":" << form.hinges.size() << ","
        << "\"linear_correction_omission_rejected\":true,"
        << "\"vertex_relabelling_invariant\":true,"
        << "\"edge_mutant_rejected\":true}\n";
}

std::uint64_t normalize_mod(std::int64_t value, std::uint64_t prime) {
    const std::int64_t signed_prime = static_cast<std::int64_t>(prime);
    std::int64_t reduced = value % signed_prime;
    if (reduced < 0) {
        reduced += signed_prime;
    }
    return static_cast<std::uint64_t>(reduced);
}

void add_product_mod(
    std::uint64_t& accumulator,
    std::uint64_t coefficient,
    std::int64_t value,
    std::uint64_t prime
) {
    const std::uint64_t value_mod = normalize_mod(value, prime);
    const std::uint64_t product = (coefficient * value_mod) % prime;
    accumulator += product;
    if (accumulator >= prime) {
        accumulator %= prime;
    }
}

std::vector<Term> read_input(
    std::uint64_t& target_scale_p1,
    std::uint64_t& target_scale_p2
) {
    std::string token;
    if (!(std::cin >> token) || token != "G0118_GLOBAL_INPUT_V1") {
        fail("bad or missing input magic");
    }
    std::uint64_t prime1 = 0;
    std::uint64_t prime2 = 0;
    if (!(std::cin >> token >> prime1 >> prime2 >> target_scale_p1 >> target_scale_p2)
        || token != "primes") {
        fail("bad primes line");
    }
    if (prime1 != kPrime1 || prime2 != kPrime2) {
        fail("global replay prime drift");
    }
    if (target_scale_p1 >= prime1 || target_scale_p2 >= prime2) {
        fail("target scale residue outside prime field");
    }

    std::size_t term_count = 0;
    if (!(std::cin >> token >> term_count) || token != "terms" || term_count == 0) {
        fail("bad term census line");
    }
    std::vector<Term> terms;
    terms.reserve(term_count);
    for (std::size_t index = 0; index < term_count; ++index) {
        Term term;
        int negative_count = 0;
        int positive_count = 0;
        term.graph.n = kGlobalN;
        if (!(std::cin >> token >> term.sequence >> term.coefficient_mod_p1
              >> term.coefficient_mod_p2 >> term.declared_active_vertices
              >> term.signed_mass >> negative_count >> positive_count)
            || token != "term") {
            fail("malformed term header");
        }
        if (term.coefficient_mod_p1 >= kPrime1 || term.coefficient_mod_p2 >= kPrime2) {
            fail("coefficient residue outside prime field");
        }
        if (term.signed_mass <= 0 || term.signed_mass > kBranchEdges
            || negative_count != term.signed_mass
            || positive_count != term.signed_mass) {
            fail("signed-mass/edge-count disagreement");
        }
        for (int edge_index = 0; edge_index < negative_count; ++edge_index) {
            int u = -1;
            int v = -1;
            if (!(std::cin >> token >> u >> v) || token != "negative") {
                fail("malformed negative edge");
            }
            add_edge(term.graph, u, v, -1);
        }
        for (int edge_index = 0; edge_index < positive_count; ++edge_index) {
            int u = -1;
            int v = -1;
            if (!(std::cin >> token >> u >> v) || token != "positive") {
                fail("malformed positive edge");
            }
            add_edge(term.graph, u, v, +1);
        }
        if (active_vertex_count(term.graph) != term.declared_active_vertices) {
            fail("declared active-vertex census disagrees with signed graph");
        }
        if (!terms.empty() && term.sequence <= terms.back().sequence) {
            fail("term sequences are not strictly increasing");
        }
        terms.push_back(std::move(term));
    }
    if (!(std::cin >> token) || token != "end") {
        fail("missing input terminator");
    }
    if (std::cin >> token) {
        fail("trailing data after input terminator");
    }
    return terms;
}

void print_direction(const Direction& direction) {
    std::cout << '[';
    for (int index = 0; index < kGlobalN; ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << static_cast<int>(direction[index]);
    }
    std::cout << ']';
}

void print_linear(const std::array<std::int64_t, kGlobalN>& linear) {
    std::cout << '[';
    for (int index = 0; index < kGlobalN; ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << linear[index];
    }
    std::cout << ']';
}

void print_mod_vector(const std::array<std::uint64_t, kGlobalN>& values) {
    std::cout << '[';
    for (int index = 0; index < kGlobalN; ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << values[index];
    }
    std::cout << ']';
}

void run_global() {
    std::uint64_t target_scale_p1 = 0;
    std::uint64_t target_scale_p2 = 0;
    const std::vector<Term> terms = read_input(target_scale_p1, target_scale_p2);

    const auto started = std::chrono::steady_clock::now();
    std::map<Direction, std::array<std::uint64_t, 2>> aggregate_hinges;
    std::array<std::uint64_t, kGlobalN> linear_p1{};
    std::array<std::uint64_t, kGlobalN> linear_p2{};
    std::size_t raw_histogram_entries = 0;
    std::size_t atom_hinge_entries = 0;
    std::vector<std::pair<int, std::array<std::int64_t, kGlobalN>>> term_linears;
    term_linears.reserve(terms.size());

    for (std::size_t index = 0; index < terms.size(); ++index) {
        const Term& term = terms[index];
        const NormalForm form = normal_form(term.graph, kBranchEdges);
        raw_histogram_entries += form.raw_histogram_entries;
        atom_hinge_entries += form.hinges.size();
        term_linears.emplace_back(term.sequence, form.linear);

        for (const auto& [direction, value] : form.hinges) {
            auto& residual = aggregate_hinges[direction];
            add_product_mod(
                residual[0], term.coefficient_mod_p1, value, kPrime1
            );
            add_product_mod(
                residual[1], term.coefficient_mod_p2, value, kPrime2
            );
        }
        for (int coordinate = 0; coordinate < kGlobalN; ++coordinate) {
            add_product_mod(
                linear_p1[coordinate],
                term.coefficient_mod_p1,
                form.linear[coordinate],
                kPrime1
            );
            add_product_mod(
                linear_p2[coordinate],
                term.coefficient_mod_p2,
                form.linear[coordinate],
                kPrime2
            );
        }

        if (index == 0 || (index + 1) % 10 == 0 || index + 1 == terms.size()) {
            std::cerr << "clean-room global replay term " << (index + 1) << '/'
                      << terms.size() << " sequence=" << term.sequence
                      << " raw_words=" << form.raw_histogram_entries
                      << " active_hinges=" << form.hinges.size() << '\n';
        }
    }

    const std::uint64_t target_factorial = factorial(kGlobalN);
    const std::uint64_t target_p1 =
        (target_scale_p1 * (target_factorial % kPrime1)) % kPrime1;
    const std::uint64_t target_p2 =
        (target_scale_p2 * (target_factorial % kPrime2)) % kPrime2;
    linear_p1[kGlobalN - 1] =
        (linear_p1[kGlobalN - 1] + kPrime1 - target_p1) % kPrime1;
    linear_p2[kGlobalN - 1] =
        (linear_p2[kGlobalN - 1] + kPrime2 - target_p2) % kPrime2;

    std::size_t nonzero_hinges = 0;
    bool have_first_hinge = false;
    Direction first_hinge{};
    std::array<std::uint64_t, 2> first_hinge_residues{};
    for (const auto& [direction, residues] : aggregate_hinges) {
        if (residues[0] == 0 && residues[1] == 0) {
            continue;
        }
        ++nonzero_hinges;
        if (!have_first_hinge) {
            have_first_hinge = true;
            first_hinge = direction;
            first_hinge_residues = residues;
        }
    }
    int first_linear = -1;
    for (int coordinate = 0; coordinate < kGlobalN; ++coordinate) {
        if (linear_p1[coordinate] != 0 || linear_p2[coordinate] != 0) {
            first_linear = coordinate;
            break;
        }
    }
    const bool globally_zero = !have_first_hinge && first_linear < 0;

    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started
    ).count();

    std::cout << '{';
    std::cout << "\"schema\":\"g0118-iteration2-cleanroom-global-modular-replay-v1\",";
    std::cout << "\"result\":\""
              << (globally_zero ? "GLOBAL_MODULAR_ZERO_SCREEN" : "GLOBAL_MODULAR_NONZERO")
              << "\",";
    std::cout << "\"primes\":[" << kPrime1 << ',' << kPrime2 << "],";
    std::cout << "\"terms\":" << terms.size() << ',';
    std::cout << "\"labelled_permutations\":"
              << static_cast<std::uint64_t>(terms.size()) * target_factorial << ',';
    std::cout << "\"raw_histogram_entries\":" << raw_histogram_entries << ',';
    std::cout << "\"atom_hinge_entries\":" << atom_hinge_entries << ',';
    std::cout << "\"aggregate_hinge_directions\":" << aggregate_hinges.size() << ',';
    std::cout << "\"nonzero_hinge_directions\":" << nonzero_hinges << ',';
    std::cout << "\"both_primes_global_zero\":" << (globally_zero ? "true" : "false") << ',';
    std::cout << "\"first_nonzero_hinge_direction\":";
    if (have_first_hinge) {
        print_direction(first_hinge);
    } else {
        std::cout << "null";
    }
    std::cout << ',';
    std::cout << "\"first_nonzero_hinge_residues\":";
    if (have_first_hinge) {
        std::cout << '[' << first_hinge_residues[0] << ',' << first_hinge_residues[1] << ']';
    } else {
        std::cout << "null";
    }
    std::cout << ',';
    std::cout << "\"first_nonzero_linear_coordinate\":";
    if (first_linear >= 0) {
        std::cout << first_linear;
    } else {
        std::cout << "null";
    }
    std::cout << ',';
    std::cout << "\"linear_residues\":{\"1000000007\":";
    print_mod_vector(linear_p1);
    std::cout << ",\"1000000009\":";
    print_mod_vector(linear_p2);
    std::cout << "},";
    std::cout << "\"term_linear_vectors\":[";
    for (std::size_t index = 0; index < term_linears.size(); ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << "{\"sequence\":" << term_linears[index].first << ",\"linear\":";
        print_linear(term_linears[index].second);
        std::cout << '}';
    }
    std::cout << "],";
    std::cout << "\"wall_seconds\":" << elapsed;
    std::cout << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            run_self_test();
            return 0;
        }
        if (argc != 1) {
            std::cerr << "usage: cleanroom_global_replay [--self-test]\n";
            return 2;
        }
        run_global();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "cleanroom_global_replay: " << error.what() << '\n';
        return 1;
    }
}
