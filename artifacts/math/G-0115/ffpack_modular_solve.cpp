// Dense finite-field solve adapter for the frozen G-0115 row projections.

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include <fflas-ffpack/ffpack/ffpack.h>
#include <givaro/modular.h>

namespace {

std::size_t parse_size(const char* raw, const char* label) {
    const std::string text(raw);
    std::size_t consumed = 0;
    const auto value = std::stoull(text, &consumed);
    if (consumed != text.size() || value == 0) throw std::runtime_error(std::string("invalid ") + label);
    return static_cast<std::size_t>(value);
}

std::uint64_t positive_mod(std::int32_t value, std::uint64_t prime) {
    const auto wide = static_cast<std::int64_t>(value);
    const auto residue = wide % static_cast<std::int64_t>(prime);
    return static_cast<std::uint64_t>(residue < 0 ? residue + static_cast<std::int64_t>(prime) : residue);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 7) {
            throw std::runtime_error(
                "usage: ffpack_modular_solve INPUT_I32 OUTPUT_U32 ROWS CANDIDATE_COLUMNS PRIME THREADS");
        }
        const std::filesystem::path input_path(argv[1]);
        const std::filesystem::path output_path(argv[2]);
        const auto rows = parse_size(argv[3], "rows");
        const auto columns = parse_size(argv[4], "candidate columns");
        const auto prime = parse_size(argv[5], "prime");
        const auto threads = parse_size(argv[6], "threads");
        if (std::filesystem::exists(output_path)) throw std::runtime_error("refusing to overwrite output");
        const auto input_values = rows * (columns + 1);
        const auto expected_bytes = input_values * sizeof(std::int32_t);
        if (!std::filesystem::is_regular_file(input_path) || std::filesystem::file_size(input_path) != expected_bytes)
            throw std::runtime_error("input size/regular-file contract failed");

        std::vector<std::int32_t> input(input_values);
        {
            std::ifstream source(input_path, std::ios::binary);
            source.read(reinterpret_cast<char*>(input.data()), static_cast<std::streamsize>(expected_bytes));
            if (!source || source.peek() != std::ifstream::traits_type::eof())
                throw std::runtime_error("input read failed");
        }

        using Field = Givaro::Modular<double>;
        Field field(static_cast<double>(prime));
        std::vector<Field::Element> matrix(rows * columns);
        std::vector<Field::Element> right_hand_side(rows);
        for (std::size_t row = 0; row < rows; ++row) {
            const auto offset = row * (columns + 1);
            for (std::size_t column = 0; column < columns; ++column)
                matrix[row * columns + column] = static_cast<double>(positive_mod(input[offset + column], prime));
            right_hand_side[row] = static_cast<double>(positive_mod(input[offset + columns], prime));
        }

        std::vector<std::size_t> row_permutation(rows);
        std::vector<std::size_t> column_permutation(columns);
        const auto factor_started = std::chrono::steady_clock::now();
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
        const auto factor_finished = std::chrono::steady_clock::now();
        std::vector<Field::Element> solution(columns, 0);
        int info = 0;
        FFPACK::fgetrs(field,
                       FFLAS::FflasLeft,
                       rows,
                       columns,
                       1,
                       rank,
                       matrix.data(),
                       columns,
                       row_permutation.data(),
                       column_permutation.data(),
                       solution.data(),
                       1,
                       right_hand_side.data(),
                       1,
                       &info);
        const auto solve_finished = std::chrono::steady_clock::now();

        std::vector<std::uint32_t> serialized(columns);
        std::size_t support = 0;
        for (std::size_t column = 0; column < columns; ++column) {
            const auto rounded = static_cast<std::int64_t>(solution[column]);
            const auto residue = rounded % static_cast<std::int64_t>(prime);
            serialized[column] = static_cast<std::uint32_t>(
                residue < 0 ? residue + static_cast<std::int64_t>(prime) : residue);
            support += serialized[column] != 0;
        }

        std::size_t residual_rows = 0;
        if (info == 0) {
            for (std::size_t row = 0; row < rows; ++row) {
                const auto offset = row * (columns + 1);
                std::uint64_t observed = 0;
                for (std::size_t column = 0; column < columns; ++column) {
                    observed += (positive_mod(input[offset + column], prime) * serialized[column]) % prime;
                    observed %= prime;
                }
                residual_rows += observed != positive_mod(input[offset + columns], prime);
            }
        }
        if (info == 0 && residual_rows != 0) throw std::runtime_error("native solution replay failed");

        std::vector<std::size_t> mathematical_column_permutation(columns);
        FFPACK::LAPACKPerm2MathPerm(
            mathematical_column_permutation.data(), column_permutation.data(), columns);
        std::vector<std::uint32_t> pivot_columns(rank);
        for (std::size_t index = 0; index < rank; ++index) {
            if (mathematical_column_permutation[index] >= columns)
                throw std::runtime_error("pivot column outside candidate matrix");
            pivot_columns[index] = static_cast<std::uint32_t>(mathematical_column_permutation[index]);
        }

        {
            std::ofstream destination(output_path, std::ios::binary | std::ios::out);
            destination.write(reinterpret_cast<const char*>(serialized.data()),
                              static_cast<std::streamsize>(serialized.size() * sizeof(std::uint32_t)));
            destination.write(reinterpret_cast<const char*>(pivot_columns.data()),
                              static_cast<std::streamsize>(pivot_columns.size() * sizeof(std::uint32_t)));
            destination.flush();
            if (!destination) throw std::runtime_error("output write failed");
        }

        const auto seconds = [](auto duration) {
            return std::chrono::duration_cast<std::chrono::duration<double>>(duration).count();
        };
        std::cout << "{\"schema\":\"g0115-ffpack-modular-solve-v1\",\"rows\":" << rows
                  << ",\"columns\":" << columns << ",\"prime\":" << prime
                  << ",\"threads\":" << threads << ",\"rank\":" << rank
                  << ",\"info\":" << info << ",\"target_member\":" << (info == 0 ? "true" : "false")
                  << ",\"support\":" << support << ",\"selected_replay_residual_rows\":" << residual_rows
                  << ",\"factor_seconds\":" << seconds(factor_finished - factor_started)
                  << ",\"solve_seconds\":" << seconds(solve_finished - factor_finished) << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
