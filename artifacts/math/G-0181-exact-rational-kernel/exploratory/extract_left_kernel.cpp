#include <flint/flint.h>
#include <flint/nmod_mat.h>

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static std::int64_t read_i64le(std::istream &in) {
    unsigned char b[8];
    in.read(reinterpret_cast<char *>(b), 8);
    if (!in) throw std::runtime_error("short matrix read");
    std::uint64_t u = 0;
    for (int k = 7; k >= 0; --k) u = (u << 8) | b[k];
    std::int64_t x;
    std::memcpy(&x, &u, sizeof(x));
    return x;
}

static void write_u32le(std::ostream &out, std::uint32_t u) {
    unsigned char b[4];
    for (int k = 0; k < 4; ++k) b[k] = static_cast<unsigned char>(u >> (8 * k));
    out.write(reinterpret_cast<const char *>(b), 4);
}

static ulong reduce_signed(std::int64_t x, ulong p) {
    if (x >= 0) return static_cast<ulong>(static_cast<std::uint64_t>(x) % p);
    std::uint64_t mag = std::uint64_t(0) - static_cast<std::uint64_t>(x);
    ulong r = static_cast<ulong>(mag % p);
    return r == 0 ? 0 : p - r;
}

int main(int argc, char **argv) {
    if (argc != 8) {
        std::cerr << "usage: MATRIX ROWS COLS PIVOT_COLUMNS_TXT PRIME OUTPUT_U32LE EXPECTED_NULLITY\n";
        return 2;
    }
    try {
        const std::string matrix_path = argv[1];
        const slong rows = std::stol(argv[2]);
        const slong cols = std::stol(argv[3]);
        const std::string pivots_path = argv[4];
        const ulong prime = std::stoull(argv[5]);
        const std::string output_path = argv[6];
        const slong expected_nullity = std::stol(argv[7]);

        std::ifstream pin(pivots_path);
        if (!pin) throw std::runtime_error("could not open pivot list");
        std::vector<slong> pivots;
        for (slong x; pin >> x;) {
            if (x < 0 || x >= cols) throw std::runtime_error("pivot out of range");
            if (!pivots.empty() && x <= pivots.back()) throw std::runtime_error("pivots not strictly increasing");
            pivots.push_back(x);
        }
        if (pivots.empty()) throw std::runtime_error("empty pivot list");

        // The selected pivot columns of A form a row-rank witness.  A left
        // kernel vector is therefore exactly a right-kernel vector of their
        // transpose, whose shape is rank(A) x rows(A).
        nmod_mat_t transpose;
        nmod_mat_init(transpose, static_cast<slong>(pivots.size()), rows, prime);
        std::ifstream in(matrix_path, std::ios::binary);
        if (!in) throw std::runtime_error("could not open matrix");
        for (slong i = 0; i < rows; ++i) {
            std::size_t next = 0;
            for (slong j = 0; j < cols; ++j) {
                std::int64_t x = read_i64le(in);
                if (next < pivots.size() && pivots[next] == j) {
                    nmod_mat_entry(transpose, static_cast<slong>(next), i) = reduce_signed(x, prime);
                    ++next;
                }
            }
            if (next != pivots.size()) throw std::runtime_error("failed to load every pivot in row");
        }
        char extra;
        if (in.read(&extra, 1)) throw std::runtime_error("matrix has trailing bytes");

        nmod_mat_t basis;
        nmod_mat_init(basis, rows, expected_nullity, prime);
        slong nullity = nmod_mat_nullspace(basis, transpose);
        if (nullity != expected_nullity) {
            throw std::runtime_error("unexpected nullity " + std::to_string(nullity));
        }

        std::ofstream out(output_path, std::ios::binary | std::ios::trunc);
        if (!out) throw std::runtime_error("could not create output");
        for (slong i = 0; i < rows; ++i) {
            for (slong j = 0; j < nullity; ++j) {
                ulong x = nmod_mat_entry(basis, i, j);
                if (x >= (ulong(1) << 32)) throw std::runtime_error("entry does not fit u32");
                write_u32le(out, static_cast<std::uint32_t>(x));
            }
        }
        if (!out) throw std::runtime_error("basis write failed");

        std::cout << "rank_witness_columns=" << pivots.size()
                  << " rows=" << rows
                  << " nullity=" << nullity
                  << " prime=" << prime
                  << " output_bytes=" << (std::uint64_t(rows) * std::uint64_t(nullity) * 4)
                  << "\n";
        nmod_mat_clear(basis);
        nmod_mat_clear(transpose);
        flint_cleanup_master();
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
