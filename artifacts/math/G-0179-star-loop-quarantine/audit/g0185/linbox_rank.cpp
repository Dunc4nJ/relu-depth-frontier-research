#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <givaro/modular.h>
#include <fflas-ffpack/ffpack/ffpack.h>

namespace {

std::uint64_t read_u64_le(const unsigned char *b) {
    std::uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= std::uint64_t(b[i]) << (8 * i);
    return value;
}

std::int64_t decode_i64(std::uint64_t bits) {
    if ((bits >> 63) == 0) return static_cast<std::int64_t>(bits);
    const std::uint64_t magnitude = (~bits) + 1;
    if (magnitude == (std::uint64_t{1} << 63)) return std::numeric_limits<std::int64_t>::min();
    return -static_cast<std::int64_t>(magnitude);
}

}  // namespace

int main(int argc, char **argv) {
    try {
        if (argc != 4) {
            std::cerr << "usage: linbox_rank MATRIX N PRIME\n";
            return 2;
        }
        const std::filesystem::path path(argv[1]);
        const std::size_t n = std::stoull(argv[2]);
        const std::uint64_t prime = std::stoull(argv[3]);
        if (n == 0 || prime < 2) throw std::runtime_error("invalid dimension or prime");
        const std::uintmax_t expected = std::uintmax_t(n) * n * 8;
        if (std::filesystem::file_size(path) != expected) throw std::runtime_error("size mismatch");

        using Field = Givaro::Modular<double>;
        Field field(static_cast<double>(prime));
        std::vector<double> matrix(n * n);
        std::ifstream input(path, std::ios::binary);
        if (!input) throw std::runtime_error("open failed");
        unsigned char bytes[8];
        std::uint64_t zero = 0, positive = 0, negative = 0;
        for (std::size_t i = 0; i < n; ++i) {
            for (std::size_t j = 0; j < n; ++j) {
                input.read(reinterpret_cast<char *>(bytes), 8);
                if (input.gcount() != 8) throw std::runtime_error("short read");
                const std::int64_t value = decode_i64(read_u64_le(bytes));
                if (value == 0) ++zero;
                else if (value > 0) ++positive;
                else ++negative;
                std::int64_t residue = value % static_cast<std::int64_t>(prime);
                if (residue < 0) residue += static_cast<std::int64_t>(prime);
                matrix[i * n + j] = static_cast<double>(residue);
            }
        }
        if (input.peek() != std::char_traits<char>::eof()) throw std::runtime_error("trailing data");
        const std::size_t rank = FFPACK::Rank(field, n, n, matrix.data(), n);
        std::cout << "{\"library\":\"FFLAS-FFPACK\",\"prime\":" << prime
                  << ",\"dimension\":" << n << ",\"rank_mod_prime\":" << rank
                  << ",\"sign_counts\":{\"negative\":" << negative << ",\"zero\":" << zero
                  << ",\"positive\":" << positive << "}}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "linbox_rank: " << error.what() << '\n';
        return 1;
    }
}
