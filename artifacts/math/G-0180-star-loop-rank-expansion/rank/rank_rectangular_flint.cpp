#include <flint/flint.h>
#include <flint/nmod_mat.h>
#include <flint/ulong_extras.h>
#include <openssl/evp.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

class Sha256 {
  public:
    Sha256() : ctx_(EVP_MD_CTX_new()) {
        if (!ctx_ || EVP_DigestInit_ex(ctx_.get(), EVP_sha256(), nullptr) != 1) {
            throw std::runtime_error("could not initialize SHA-256");
        }
    }

    void update(const void *data, std::size_t size) {
        if (finished_) throw std::runtime_error("SHA-256 update after finalization");
        if (size != 0 && EVP_DigestUpdate(ctx_.get(), data, size) != 1) {
            throw std::runtime_error("SHA-256 update failed");
        }
    }

    std::string finish() {
        if (finished_) throw std::runtime_error("SHA-256 finalized twice");
        std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
        unsigned int digest_size = 0;
        if (EVP_DigestFinal_ex(ctx_.get(), digest.data(), &digest_size) != 1 || digest_size != 32) {
            throw std::runtime_error("SHA-256 finalization failed");
        }
        finished_ = true;
        std::ostringstream out;
        out << std::hex << std::setfill('0');
        for (unsigned int i = 0; i < digest_size; ++i) out << std::setw(2) << unsigned(digest[i]);
        return out.str();
    }

  private:
    struct Deleter {
        void operator()(EVP_MD_CTX *ctx) const { EVP_MD_CTX_free(ctx); }
    };
    std::unique_ptr<EVP_MD_CTX, Deleter> ctx_;
    bool finished_ = false;
};

std::string json_escape(const std::string &value) {
    std::ostringstream out;
    for (unsigned char c : value) {
        switch (c) {
            case '\"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (c < 0x20) {
                    out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(c)
                        << std::dec;
                } else {
                    out << char(c);
                }
        }
    }
    return out.str();
}

std::uint64_t parse_u64(const char *text, const char *name) {
    std::string value(text);
    if (value.empty() || value.front() == '-') throw std::runtime_error(std::string(name) + " must be nonnegative");
    std::size_t used = 0;
    unsigned long long result = 0;
    try {
        result = std::stoull(value, &used, 10);
    } catch (const std::exception &) {
        throw std::runtime_error(std::string("invalid ") + name + ": " + value);
    }
    if (used != value.size()) throw std::runtime_error(std::string("invalid ") + name + ": " + value);
    return std::uint64_t(result);
}

std::vector<slong> parse_excluded_rows(const std::string &text, slong input_rows) {
    std::vector<slong> rows;
    if (text == "-" || text.empty()) return rows;
    std::size_t start = 0;
    while (start <= text.size()) {
        const std::size_t comma = text.find(',', start);
        const std::string token = text.substr(start, comma == std::string::npos ? std::string::npos : comma - start);
        if (token.empty()) throw std::runtime_error("empty excluded-row token");
        const std::uint64_t parsed = parse_u64(token.c_str(), "excluded row");
        if (parsed >= std::uint64_t(input_rows)) throw std::runtime_error("excluded row is out of range");
        rows.push_back(slong(parsed));
        if (comma == std::string::npos) break;
        start = comma + 1;
    }
    if (!std::is_sorted(rows.begin(), rows.end())) throw std::runtime_error("excluded rows must be sorted");
    if (std::adjacent_find(rows.begin(), rows.end()) != rows.end()) {
        throw std::runtime_error("excluded rows must be unique");
    }
    return rows;
}

std::uintmax_t checked_mul(std::uintmax_t a, std::uintmax_t b, const char *label) {
    if (a != 0 && b > std::numeric_limits<std::uintmax_t>::max() / a) {
        throw std::runtime_error(std::string("size overflow computing ") + label);
    }
    return a * b;
}

ulong pow2_mod(unsigned exponent, ulong prime) {
    ulong result = 1 % prime;
    for (unsigned i = 0; i < exponent; ++i) result = ulong((std::uint64_t(result) * 2) % prime);
    return result;
}

// Interpret b as a signed two's-complement integer in little-endian order.
// First reduce the unsigned bit-pattern with a byte Horner scheme, then subtract
// 2^bits modulo p exactly when the sign bit is set.  No native signed conversion
// or narrowing occurs.  Supported widths are 64 and 128 bits.
ulong reduce_signed_le_bytes(
    const unsigned char *b, unsigned cell_bytes, ulong prime, ulong two_power_mod_prime) {
    ulong residue = 0;
    for (int i = int(cell_bytes) - 1; i >= 0; --i) {
        residue = ulong((std::uint64_t(residue) * 256 + b[i]) % prime);
    }
    if ((b[cell_bytes - 1] & 0x80U) != 0) {
        residue = residue >= two_power_mod_prime
                      ? residue - two_power_mod_prime
                      : ulong(std::uint64_t(residue) + prime - two_power_mod_prime);
    }
    return residue;
}

// Algebraically independent limb decomposition used as an exhaustive conversion
// cross-check for every selected cell.
ulong reduce_signed_le_limbs(
    const unsigned char *b, unsigned cell_bytes, ulong prime, ulong two_power_mod_prime) {
    std::array<std::uint32_t, 4> limbs{};
    const unsigned limb_count = cell_bytes / 4;
    for (unsigned limb = 0; limb < limb_count; ++limb) {
        std::uint32_t value = 0;
        for (unsigned byte = 0; byte < 4; ++byte) {
            value |= std::uint32_t(b[4 * limb + byte]) << (8 * byte);
        }
        limbs[limb] = value;
    }
    const ulong base = pow2_mod(32, prime);
    ulong residue = 0;
    for (int limb = int(limb_count) - 1; limb >= 0; --limb) {
        residue = ulong((std::uint64_t(residue) * base + (std::uint64_t(limbs[limb]) % prime)) % prime);
    }
    if ((b[cell_bytes - 1] & 0x80U) != 0) {
        residue = residue >= two_power_mod_prime
                      ? residue - two_power_mod_prime
                      : ulong(std::uint64_t(residue) + prime - two_power_mod_prime);
    }
    return residue;
}

void sha_update_u64le(Sha256 &sha, std::uint64_t value) {
    std::array<unsigned char, 8> bytes{};
    for (unsigned i = 0; i < 8; ++i) {
        bytes[i] = static_cast<unsigned char>((value >> (8 * i)) & 0xffU);
    }
    sha.update(bytes.data(), bytes.size());
}

double seconds(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double>(end - start).count();
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 10) {
        std::cerr << "usage: rank_rectangular_flint MATRIX ENCODING(i64le|i128le) INPUT_ROWS INPUT_COLS COL_START COL_END "
                     "EXCLUDED_ROWS_CSV PRIME OUTPUT.json\n";
        return 2;
    }

    try {
        static_assert(sizeof(ulong) == 8, "certificate encoding requires 64-bit FLINT limbs");
        const std::filesystem::path matrix_path(argv[1]);
        const std::string encoding(argv[2]);
        unsigned cell_bytes = 0;
        if (encoding == "i64le") {
            cell_bytes = 8;
        } else if (encoding == "i128le") {
            cell_bytes = 16;
        } else {
            throw std::runtime_error("encoding must be exactly i64le or i128le");
        }
        const std::uint64_t input_rows_u = parse_u64(argv[3], "input rows");
        const std::uint64_t input_cols_u = parse_u64(argv[4], "input columns");
        const std::uint64_t col_start_u = parse_u64(argv[5], "column start");
        const std::uint64_t col_end_u = parse_u64(argv[6], "column end");
        const std::uint64_t prime_u = parse_u64(argv[8], "prime");
        const std::filesystem::path output_path(argv[9]);

        if (input_rows_u == 0 || input_cols_u == 0 ||
            input_rows_u > std::uint64_t(std::numeric_limits<slong>::max()) ||
            input_cols_u > std::uint64_t(std::numeric_limits<slong>::max())) {
            throw std::runtime_error("input dimensions must be positive and fit FLINT slong");
        }
        if (col_start_u >= col_end_u || col_end_u > input_cols_u) {
            throw std::runtime_error("require 0 <= COL_START < COL_END <= INPUT_COLS");
        }
        if (prime_u < 2 || prime_u > std::uint64_t(std::numeric_limits<ulong>::max())) {
            throw std::runtime_error("prime does not fit FLINT ulong");
        }
        const ulong prime = ulong(prime_u);
        if (!n_is_prime(prime)) throw std::runtime_error("modulus is not prime");
        if (prime != 1000003UL && prime != 1000033UL) {
            throw std::runtime_error("this certificate build permits only primes 1000003 and 1000033");
        }
        if (!std::filesystem::is_regular_file(matrix_path)) throw std::runtime_error("matrix is not a regular file");
        if (std::filesystem::exists(output_path)) throw std::runtime_error("refusing to overwrite output receipt");

        const slong input_rows = slong(input_rows_u);
        const slong input_cols = slong(input_cols_u);
        const slong col_start = slong(col_start_u);
        const slong col_end = slong(col_end_u);
        const std::vector<slong> excluded = parse_excluded_rows(argv[7], input_rows);
        const slong selected_rows = input_rows - slong(excluded.size());
        const slong selected_cols = col_end - col_start;
        if (selected_rows <= 0 || selected_cols <= 0) {
            throw std::runtime_error("selected matrix must be nonempty");
        }

        const std::uintmax_t cells = checked_mul(input_rows_u, input_cols_u, "input cells");
        const std::uintmax_t expected_bytes = checked_mul(cells, cell_bytes, "input bytes");
        const std::uintmax_t actual_bytes = std::filesystem::file_size(matrix_path);
        if (actual_bytes != expected_bytes) {
            throw std::runtime_error("matrix byte-size mismatch: expected " + std::to_string(expected_bytes) +
                                     ", found " + std::to_string(actual_bytes));
        }
        const std::uintmax_t row_bytes_u = checked_mul(input_cols_u, cell_bytes, "row bytes");
        if (row_bytes_u > std::numeric_limits<std::size_t>::max() ||
            row_bytes_u > std::uintmax_t(std::numeric_limits<std::streamsize>::max())) {
            throw std::runtime_error("row buffer is too large");
        }
        const std::size_t row_bytes = std::size_t(row_bytes_u);

        std::ifstream input(matrix_path, std::ios::binary);
        if (!input) throw std::runtime_error("could not open matrix");
        std::vector<unsigned char> row(row_bytes);
        nmod_mat_t matrix;
        nmod_mat_init(matrix, selected_rows, selected_cols, prime);

        const unsigned signed_bits = cell_bytes * 8;
        const ulong two_power_mod_prime = pow2_mod(signed_bits, prime);
        Sha256 selected_raw_sha;
        Sha256 selected_modp_sha;
        std::uint64_t negative_count = 0;
        std::uint64_t zero_count = 0;
        std::uint64_t positive_count = 0;
        std::uint64_t crosscheck_count = 0;
        std::size_t excluded_cursor = 0;
        slong selected_row = 0;
        const auto load_start = Clock::now();
        for (slong source_row = 0; source_row < input_rows; ++source_row) {
            input.read(reinterpret_cast<char *>(row.data()), std::streamsize(row.size()));
            if (input.gcount() != std::streamsize(row.size())) throw std::runtime_error("short matrix read");
            const bool skip = excluded_cursor < excluded.size() && excluded[excluded_cursor] == source_row;
            if (skip) {
                ++excluded_cursor;
                continue;
            }
            for (slong source_col = col_start; source_col < col_end; ++source_col) {
                const unsigned char *cell = row.data() + std::size_t(source_col) * cell_bytes;
                const ulong residue_a = reduce_signed_le_bytes(cell, cell_bytes, prime, two_power_mod_prime);
                const ulong residue_b = reduce_signed_le_limbs(cell, cell_bytes, prime, two_power_mod_prime);
                if (residue_a != residue_b) {
                    throw std::runtime_error("signed-integer reduction cross-check failed at source row " +
                                             std::to_string(source_row) + ", source column " +
                                             std::to_string(source_col));
                }
                const slong selected_col = source_col - col_start;
                nmod_mat_entry(matrix, selected_row, selected_col) = residue_a;
                selected_raw_sha.update(cell, cell_bytes);
                sha_update_u64le(selected_modp_sha, std::uint64_t(residue_a));
                ++crosscheck_count;
                bool zero = true;
                for (unsigned byte = 0; byte < cell_bytes; ++byte) zero = zero && cell[byte] == 0;
                if (zero) {
                    ++zero_count;
                } else if ((cell[cell_bytes - 1] & 0x80U) != 0) {
                    ++negative_count;
                } else {
                    ++positive_count;
                }
            }
            ++selected_row;
        }
        const auto load_end = Clock::now();
        if (excluded_cursor != excluded.size() || selected_row != selected_rows) {
            throw std::runtime_error("row exclusion accounting failed");
        }
        if (input.peek() != std::char_traits<char>::eof()) throw std::runtime_error("trailing matrix bytes");
        const std::uint64_t expected_selected_cells = std::uint64_t(selected_rows) * std::uint64_t(selected_cols);
        if (crosscheck_count != expected_selected_cells) throw std::runtime_error("selected-cell accounting failed");
        const std::string selected_raw_digest = selected_raw_sha.finish();
        const std::string selected_modp_digest = selected_modp_sha.finish();

        const auto rank_start = Clock::now();
        const slong rank = nmod_mat_rref(matrix);
        const auto rank_end = Clock::now();

        std::vector<slong> pivots;
        bool saw_zero_row = false;
        bool pivot_columns_reduced = true;
        for (slong i = 0; i < selected_rows; ++i) {
            slong pivot = 0;
            while (pivot < selected_cols && nmod_mat_entry(matrix, i, pivot) == 0) ++pivot;
            if (pivot == selected_cols) {
                saw_zero_row = true;
                continue;
            }
            if (saw_zero_row) throw std::runtime_error("RREF contains a nonzero row after a zero row");
            if (nmod_mat_entry(matrix, i, pivot) != 1 ||
                (!pivots.empty() && pivot <= pivots.back())) {
                throw std::runtime_error("RREF pivot scan failed");
            }
            for (slong other = 0; other < selected_rows; ++other) {
                if (other != i && nmod_mat_entry(matrix, other, pivot) != 0) {
                    pivot_columns_reduced = false;
                    break;
                }
            }
            pivots.push_back(pivot);
        }
        if (slong(pivots.size()) != rank || !pivot_columns_reduced) {
            throw std::runtime_error("RREF structural verification failed");
        }

        Sha256 rref_sha;
        for (slong i = 0; i < selected_rows; ++i) {
            for (slong j = 0; j < selected_cols; ++j) {
                const ulong value = nmod_mat_entry(matrix, i, j);
                sha_update_u64le(rref_sha, std::uint64_t(value));
            }
        }
        const std::string rref_digest = rref_sha.finish();
        nmod_mat_clear(matrix);

        const bool full_row_rank = rank == selected_rows;

        std::ofstream out(output_path, std::ios::binary | std::ios::trunc);
        if (!out) throw std::runtime_error("could not create output receipt");
        out << "{\n"
            << "  \"schema\": \"g0180.flint-signed-le-rectangular-rank-certificate.v1\",\n"
            << "  \"matrix_path\": \"" << json_escape(std::filesystem::absolute(matrix_path).string()) << "\",\n"
            << "  \"encoding\": \"" << encoding << "\",\n"
            << "  \"bytes_per_cell\": " << cell_bytes << ",\n"
            << "  \"input_rows\": " << input_rows << ",\n"
            << "  \"input_columns\": " << input_cols << ",\n"
            << "  \"input_bytes\": " << actual_bytes << ",\n"
            << "  \"coordinate_start_inclusive\": " << col_start << ",\n"
            << "  \"coordinate_end_exclusive\": " << col_end << ",\n"
            << "  \"excluded_source_rows\": [";
        for (std::size_t i = 0; i < excluded.size(); ++i) {
            if (i) out << ',';
            out << excluded[i];
        }
        out << "],\n"
            << "  \"selected_rows\": " << selected_rows << ",\n"
            << "  \"selected_columns\": " << selected_cols << ",\n"
            << "  \"selected_cells\": " << crosscheck_count << ",\n"
            << "  \"signed_encoding\": \"two's-complement little-endian, exactly " << cell_bytes << " bytes per cell\",\n"
            << "  \"reduction_method\": \"unsigned bit-pattern modulo p then subtract 2^" << signed_bits << " modulo p iff sign bit is set\",\n"
            << "  \"reduction_crosscheck\": \"byte-Horner and uint32-limb-Horner agreed on every selected cell\",\n"
            << "  \"reduction_crosscheck_cells\": " << crosscheck_count << ",\n"
            << "  \"selected_sign_counts\": {\"negative\": " << negative_count
            << ", \"zero\": " << zero_count << ", \"positive\": " << positive_count << "},\n"
            << "  \"selected_raw_cells_sha256\": \"" << selected_raw_digest << "\",\n"
            << "  \"prime\": " << prime << ",\n"
            << "  \"two_pow_signed_bits_mod_prime\": " << two_power_mod_prime << ",\n"
            << "  \"selected_modp_u64le_sha256\": \"" << selected_modp_digest << "\",\n"
            << "  \"rank_mod_prime\": " << rank << ",\n"
            << "  \"full_row_rank_mod_prime\": " << (full_row_rank ? "true" : "false") << ",\n"
            << "  \"pivot_columns_reduced\": " << (pivot_columns_reduced ? "true" : "false") << ",\n"
            << "  \"rref_modp_u64le_sha256\": \"" << rref_digest << "\",\n"
            << "  \"pivot_columns\": [";
        for (std::size_t i = 0; i < pivots.size(); ++i) {
            if (i) out << ',';
            out << pivots[i];
        }
        out << "],\n"
            << "  \"flint_version\": \"" << json_escape(flint_version) << "\",\n"
            << "  \"timings_seconds\": {\"load_and_reduce\": " << std::setprecision(17)
            << seconds(load_start, load_end) << ", \"rref\": "
            << seconds(rank_start, rank_end) << "}\n"
            << "}\n";
        out.flush();
        if (!out) throw std::runtime_error("output receipt write failed");
        flint_cleanup_master();
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "rank_rectangular_flint: " << error.what() << '\n';
        return 1;
    }
}
