#include <flint/flint.h>
#include <flint/nmod_mat.h>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

std::uint64_t parse_u64(const char* text, const char* label) {
    std::size_t used = 0;
    const std::string value(text);
    const auto parsed = std::stoull(value, &used, 10);
    if (used != value.size()) {
        throw std::runtime_error(std::string("invalid ") + label);
    }
    return parsed;
}

ulong reduce_signed(std::int64_t value, ulong prime) {
    if (value >= 0) {
        return static_cast<ulong>(static_cast<std::uint64_t>(value) % prime);
    }
    const auto magnitude = static_cast<unsigned __int128>(-(static_cast<__int128>(value)));
    const auto remainder = static_cast<ulong>(magnitude % prime);
    return remainder == 0 ? 0 : prime - remainder;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 5) {
            throw std::runtime_error("usage: rank_mod_flint MATRIX.i64le ROWS COLS PRIME");
        }
        static_assert(sizeof(std::int64_t) == 8);
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "This verifier requires a little-endian host"
#endif
        const std::string path(argv[1]);
        const auto rows_u = parse_u64(argv[2], "row count");
        const auto cols_u = parse_u64(argv[3], "column count");
        const auto prime_u = parse_u64(argv[4], "prime");
        if (rows_u > static_cast<std::uint64_t>(std::numeric_limits<slong>::max()) ||
            cols_u > static_cast<std::uint64_t>(std::numeric_limits<slong>::max()) ||
            prime_u < 2 || prime_u > static_cast<std::uint64_t>(std::numeric_limits<ulong>::max())) {
            throw std::runtime_error("dimension or modulus out of range");
        }
        const auto rows = static_cast<slong>(rows_u);
        const auto cols = static_cast<slong>(cols_u);
        const auto prime = static_cast<ulong>(prime_u);
        const auto cells = static_cast<unsigned __int128>(rows_u) * cols_u;
        const auto bytes = cells * sizeof(std::int64_t);
        if (bytes > static_cast<unsigned __int128>(std::numeric_limits<std::streamoff>::max())) {
            throw std::runtime_error("input size out of range");
        }

        std::ifstream input(path, std::ios::binary | std::ios::ate);
        if (!input) {
            throw std::runtime_error("cannot open matrix");
        }
        if (input.tellg() != static_cast<std::streamoff>(bytes)) {
            throw std::runtime_error("matrix byte count mismatch");
        }
        input.seekg(0);

        nmod_mat_t matrix;
        nmod_mat_init(matrix, rows, cols, prime);
        for (slong row = 0; row < rows; ++row) {
            for (slong column = 0; column < cols; ++column) {
                std::int64_t value = 0;
                input.read(reinterpret_cast<char*>(&value), sizeof(value));
                if (!input) {
                    nmod_mat_clear(matrix);
                    throw std::runtime_error("short matrix read");
                }
                nmod_mat_entry(matrix, row, column) = reduce_signed(value, prime);
            }
        }
        char extra = 0;
        if (input.read(&extra, 1)) {
            nmod_mat_clear(matrix);
            throw std::runtime_error("trailing matrix bytes");
        }

        const slong rank = nmod_mat_rank(matrix);
        nmod_mat_clear(matrix);
        flint_cleanup();
        std::cout << "{\"rows\":" << rows << ",\"columns\":" << cols
                  << ",\"prime\":" << prime << ",\"rank_mod_prime\":" << rank << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "rank_mod_flint: " << error.what() << '\n';
        return 2;
    }
}
