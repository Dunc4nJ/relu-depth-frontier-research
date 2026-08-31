// Outcome-blind modular pivot proposer for G-0140 Stage C.
//
// Input is the transpose of the logical matrix M, row-major: each of the
// 163,740 rows is one complete family column reduced to [0, prime).  PLUQ row
// pivots therefore name candidate column indices of M.  This program never
// makes an exact-rank, dependence, completeness, membership, or terminal
// decision; its sorted output is only a work-order proposal for the exact-Q
// certifier in complete_matrix_rank_selector_v1.py.

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <fflas-ffpack/ffpack/ffpack.h>
#include <givaro/modular.h>

namespace {

constexpr const char* kRole = "WORK_ORDER_PROPOSAL_ONLY_NEVER_A_DECISION";

std::size_t parse_size(const char* raw, const char* label) {
    const std::string text(raw);
    std::size_t consumed = 0;
    const auto value = std::stoull(text, &consumed);
    if (consumed != text.size() || value == 0) {
        throw std::runtime_error(std::string("invalid ") + label);
    }
    if (value > std::numeric_limits<std::size_t>::max()) {
        throw std::runtime_error(std::string("oversized ") + label);
    }
    return static_cast<std::size_t>(value);
}

std::size_t checked_product(std::size_t left, std::size_t right, const char* label) {
    if (right != 0 && left > std::numeric_limits<std::size_t>::max() / right) {
        throw std::runtime_error(std::string(label) + " overflow");
    }
    return left * right;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 7) {
            throw std::runtime_error(
                "usage: ffpack_modular_pivots INPUT_I32 OUTPUT_U32 "
                "TRANSPOSE_ROWS TRANSPOSE_COLUMNS PRIME THREADS");
        }
        const std::filesystem::path input_path(argv[1]);
        const std::filesystem::path output_path(argv[2]);
        const auto rows = parse_size(argv[3], "transpose rows");
        const auto columns = parse_size(argv[4], "transpose columns");
        const auto prime = parse_size(argv[5], "prime");
        const auto threads = parse_size(argv[6], "threads");
        const std::uint32_t endian_probe = 0x01020304U;
        const auto* endian_bytes =
            reinterpret_cast<const unsigned char*>(&endian_probe);
        if (endian_bytes[0] != 0x04U || endian_bytes[1] != 0x03U ||
            endian_bytes[2] != 0x02U || endian_bytes[3] != 0x01U) {
            throw std::runtime_error(
                "native i32le/u32le contract requires a little-endian runtime");
        }
        if (prime >= (std::uint64_t{1} << 31)) {
            throw std::runtime_error("prime must fit positive signed i32");
        }
        if (std::filesystem::exists(output_path)) {
            throw std::runtime_error("refusing to overwrite output");
        }
        const auto input_values = checked_product(rows, columns, "matrix entry count");
        const auto expected_bytes =
            checked_product(input_values, sizeof(std::int32_t), "input byte count");
        if (!std::filesystem::is_regular_file(input_path) ||
            std::filesystem::is_symlink(input_path) ||
            std::filesystem::file_size(input_path) != expected_bytes) {
            throw std::runtime_error("input size/regular-file contract failed");
        }

        std::vector<std::int32_t> input(input_values);
        {
            std::ifstream source(input_path, std::ios::binary);
            source.read(reinterpret_cast<char*>(input.data()),
                        static_cast<std::streamsize>(expected_bytes));
            if (!source || source.peek() != std::ifstream::traits_type::eof()) {
                throw std::runtime_error("input read failed");
            }
        }
        for (const auto residue : input) {
            if (residue < 0 || static_cast<std::size_t>(residue) >= prime) {
                throw std::runtime_error("input contains a noncanonical residue");
            }
        }

        using Field = Givaro::Modular<double>;
        Field field(static_cast<double>(prime));
        std::vector<Field::Element> matrix(input_values);
        for (std::size_t index = 0; index < input_values; ++index) {
            matrix[index] = static_cast<double>(input[index]);
        }
        input.clear();
        input.shrink_to_fit();

        std::vector<std::size_t> row_permutation(rows);
        std::vector<std::size_t> column_permutation(columns);
        const auto started = std::chrono::steady_clock::now();
        std::size_t rank = 0;
        {
            FFLAS::ParSeqHelper::Parallel<FFLAS::CuttingStrategy::Recursive,
                                         FFLAS::StrategyParameter::Threads>
                parallel(threads);
            PAR_BLOCK {
                rank = FFPACK::PLUQ(field,
                                    FFLAS::FflasNonUnit,
                                    rows,
                                    columns,
                                    matrix.data(),
                                    columns,
                                    row_permutation.data(),
                                    column_permutation.data(),
                                    parallel);
            }
        }
        const auto finished = std::chrono::steady_clock::now();
        if (rank > std::min(rows, columns)) {
            throw std::runtime_error("FFPACK rank exceeds matrix dimensions");
        }

        std::vector<std::size_t> mathematical_row_permutation(rows);
        FFPACK::LAPACKPerm2MathPerm(
            mathematical_row_permutation.data(), row_permutation.data(), rows);
        std::vector<std::uint32_t> pivot_rows;
        pivot_rows.reserve(rank);
        for (std::size_t index = 0; index < rank; ++index) {
            const auto pivot = mathematical_row_permutation[index];
            if (pivot >= rows || pivot > std::numeric_limits<std::uint32_t>::max()) {
                throw std::runtime_error("pivot row outside u32 matrix axis");
            }
            pivot_rows.push_back(static_cast<std::uint32_t>(pivot));
        }
        std::sort(pivot_rows.begin(), pivot_rows.end());
        if (std::adjacent_find(pivot_rows.begin(), pivot_rows.end()) != pivot_rows.end()) {
            throw std::runtime_error("duplicate FFPACK pivot row");
        }

        {
            std::ofstream destination(output_path, std::ios::binary | std::ios::out);
            destination.write(
                reinterpret_cast<const char*>(pivot_rows.data()),
                static_cast<std::streamsize>(pivot_rows.size() * sizeof(std::uint32_t)));
            destination.flush();
            if (!destination) {
                throw std::runtime_error("output write failed");
            }
        }

        const auto seconds = std::chrono::duration_cast<std::chrono::duration<double>>(
                                 finished - started)
                                 .count();
        std::cout << "{\"schema\":\"max11-g0140-ffpack-modular-pivots-v1\""
                  << ",\"role\":\"" << kRole << "\""
                  << ",\"matrix_layout\":\"row_major_transpose_family_columns\""
                  << ",\"byte_order\":\"little_endian_runtime_asserted\""
                  << ",\"transpose_rows\":" << rows
                  << ",\"transpose_columns\":" << columns
                  << ",\"prime\":" << prime
                  << ",\"threads\":" << threads
                  << ",\"rank\":" << rank
                  << ",\"factor_seconds\":" << seconds << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
