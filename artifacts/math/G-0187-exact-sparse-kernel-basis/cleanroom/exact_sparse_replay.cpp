#include <algorithm>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

using i64 = std::int64_t;
using i128 = __int128_t;
using u128 = __uint128_t;

static std::vector<i64> read_i64(const std::string& path, std::size_t count) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open " + path);
    std::vector<i64> values(count);
    input.read(reinterpret_cast<char*>(values.data()),
               static_cast<std::streamsize>(count * sizeof(i64)));
    if (input.gcount() != static_cast<std::streamsize>(count * sizeof(i64)))
        throw std::runtime_error("short read " + path);
    char trailing;
    if (input.read(&trailing, 1)) throw std::runtime_error("trailing bytes " + path);
    return values;
}

static void write_i128(const std::string& path, const std::vector<i128>& values) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("cannot create " + path);
    output.write(reinterpret_cast<const char*>(values.data()),
                 static_cast<std::streamsize>(values.size() * sizeof(i128)));
    if (!output) throw std::runtime_error("write failed " + path);
}

static std::string decimal(u128 value) {
    if (!value) return "0";
    std::string result;
    while (value) {
        result.push_back(static_cast<char>('0' + value % 10));
        value /= 10;
    }
    std::reverse(result.begin(), result.end());
    return result;
}

int main(int argc, char** argv) {
    if (argc != 8) {
        std::cerr << "usage: exact_sparse_replay A.i64 C.i64 residual.i128 mutant.i128 summary.json rows cols basis\n";
        return 2;
    }
    const std::string matrix_path = argv[1];
    const std::string coefficient_path = argv[2];
    const std::string residual_path = argv[3];
    const std::string mutant_path = argv[4];
    const std::string summary_path = argv[5];
    const std::size_t rows = std::stoull(argv[6]);
    const std::size_t cols = std::stoull(argv[7]);
    constexpr std::size_t basis = 478;
    constexpr std::size_t mutant_row = 821;
    static_assert(std::endian::native == std::endian::little,
                  "certificate byte streams require a little-endian host");
    for (const char* output : {argv[3], argv[4], argv[5]}) {
        if (std::filesystem::exists(output))
            throw std::runtime_error(std::string("refusing to overwrite ") + output);
    }

    const auto matrix = read_i64(matrix_path, rows * cols);
    const auto coefficients = read_i64(coefficient_path, rows * basis);

    i64 max_abs_matrix = 0;
    for (i64 value : matrix) {
        if (value == std::numeric_limits<i64>::min())
            throw std::runtime_error("INT64_MIN matrix entry");
        max_abs_matrix = std::max(max_abs_matrix, static_cast<i64>(std::llabs(value)));
    }

    std::vector<std::vector<std::pair<std::size_t, i64>>> terms(basis);
    std::vector<u128> sum_abs(basis, 0);
    for (std::size_t row = 0; row < rows; ++row) {
        for (std::size_t column = 0; column < basis; ++column) {
            const i64 value = coefficients[row * basis + column];
            if (!value) continue;
            if (value == std::numeric_limits<i64>::min())
                throw std::runtime_error("INT64_MIN coefficient");
            terms[column].emplace_back(row, value);
            sum_abs[column] += static_cast<u128>(std::llabs(value));
        }
    }
    u128 maximum_bound = 0;
    for (u128 value : sum_abs)
        maximum_bound = std::max(maximum_bound, value * static_cast<u128>(max_abs_matrix));
    const u128 signed_i128_limit = (static_cast<u128>(1) << 127) - 1;
    if (maximum_bound > signed_i128_limit)
        throw std::runtime_error("certified accumulation bound exceeds signed i128");

    std::vector<i128> residual(basis * cols, 0);
#pragma omp parallel for schedule(dynamic, 1)
    for (std::int64_t raw_column = 0; raw_column < static_cast<std::int64_t>(basis); ++raw_column) {
        const std::size_t column = static_cast<std::size_t>(raw_column);
        i128* output = residual.data() + column * cols;
        for (const auto& [row, coefficient] : terms[column]) {
            const i64* source = matrix.data() + row * cols;
            for (std::size_t coordinate = 0; coordinate < cols; ++coordinate)
                output[coordinate] += static_cast<i128>(coefficient) * source[coordinate];
        }
    }

    std::size_t residual_nonzero = 0;
    std::size_t first_basis = basis;
    std::size_t first_coordinate = cols;
    for (std::size_t column = 0; column < basis; ++column) {
        for (std::size_t coordinate = 0; coordinate < cols; ++coordinate) {
            if (residual[column * cols + coordinate]) {
                ++residual_nonzero;
                if (first_basis == basis) {
                    first_basis = column;
                    first_coordinate = coordinate;
                }
            }
        }
    }
    write_i128(residual_path, residual);

    std::vector<i128> mutant(cols, 0);
    for (const auto& [row, coefficient] : terms[0]) {
        const i64* source = matrix.data() + row * cols;
        for (std::size_t coordinate = 0; coordinate < cols; ++coordinate)
            mutant[coordinate] += static_cast<i128>(coefficient) * source[coordinate];
    }
    const i64* added = matrix.data() + mutant_row * cols;
    std::size_t mutant_nonzero = 0;
    bool mutant_equals_added_row = true;
    for (std::size_t coordinate = 0; coordinate < cols; ++coordinate) {
        mutant[coordinate] += static_cast<i128>(added[coordinate]);
        if (mutant[coordinate]) ++mutant_nonzero;
        if (mutant[coordinate] != static_cast<i128>(added[coordinate]))
            mutant_equals_added_row = false;
    }
    if (!mutant_nonzero || !mutant_equals_added_row)
        throw std::runtime_error("hostile mutant control failed");
    write_i128(mutant_path, mutant);

    std::ofstream summary(summary_path, std::ios::trunc);
    if (!summary) throw std::runtime_error("cannot create summary");
    summary << "{\n"
            << "  \"basis_vectors\": " << basis << ",\n"
            << "  \"coordinates_per_vector\": " << cols << ",\n"
            << "  \"equations_checked\": " << basis * cols << ",\n"
            << "  \"first_nonzero_basis\": " << (first_basis == basis ? -1 : static_cast<long long>(first_basis)) << ",\n"
            << "  \"first_nonzero_coordinate\": " << (first_coordinate == cols ? -1 : static_cast<long long>(first_coordinate)) << ",\n"
            << "  \"maximum_abs_matrix_entry\": " << max_abs_matrix << ",\n"
            << "  \"maximum_signed_accumulation_bound\": \"" << decimal(maximum_bound) << "\",\n"
            << "  \"mutant_equals_added_row\": " << (mutant_equals_added_row ? "true" : "false") << ",\n"
            << "  \"mutant_nonzero_coordinates\": " << mutant_nonzero << ",\n"
            << "  \"mutated_basis_column\": 0,\n"
            << "  \"mutated_output_row\": " << mutant_row << ",\n"
            << "  \"residual_nonzero_coordinates\": " << residual_nonzero << ",\n"
            << "  \"signed_i128_safe\": true\n"
            << "}\n";
    if (!summary) throw std::runtime_error("summary write failed");

    std::cout << "residual_nonzero=" << residual_nonzero
              << " mutant_nonzero=" << mutant_nonzero
              << " max_bound=" << decimal(maximum_bound) << "\n";
    return residual_nonzero ? 1 : 0;
}
