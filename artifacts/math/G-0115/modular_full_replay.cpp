// Parallel complete-coordinate modular replay for the G-0115 CEGIS cache.

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <vector>

#include <omp.h>

namespace {

std::size_t parse_size(const char* raw, const char* label, bool allow_zero = false) {
    const std::string text(raw);
    std::size_t consumed = 0;
    const auto value = std::stoull(text, &consumed);
    if (consumed != text.size() || (!allow_zero && value == 0))
        throw std::runtime_error(std::string("invalid ") + label);
    return static_cast<std::size_t>(value);
}

template <typename T>
std::vector<T> read_exact(const std::filesystem::path& path) {
    if (!std::filesystem::is_regular_file(path)) throw std::runtime_error("input is not a regular file");
    const auto bytes = std::filesystem::file_size(path);
    if (bytes % sizeof(T) != 0) throw std::runtime_error("input element-size contract failed");
    std::vector<T> values(bytes / sizeof(T));
    std::ifstream source(path, std::ios::binary);
    source.read(reinterpret_cast<char*>(values.data()), static_cast<std::streamsize>(bytes));
    if (!source || source.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("input read failed");
    return values;
}

std::uint64_t positive_mod(std::int32_t value, std::uint64_t prime) {
    const auto wide = static_cast<std::int64_t>(value);
    const auto residue = wide % static_cast<std::int64_t>(prime);
    return static_cast<std::uint64_t>(residue < 0 ? residue + static_cast<std::int64_t>(prime) : residue);
}

class Mapping {
  public:
    Mapping(const std::filesystem::path& path, std::size_t minimum_bytes) {
        descriptor_ = ::open(path.c_str(), O_RDONLY);
        if (descriptor_ < 0) throw std::runtime_error("matrix open failed");
        struct stat status {};
        if (::fstat(descriptor_, &status) != 0 || status.st_size < 0 ||
            static_cast<std::size_t>(status.st_size) < minimum_bytes)
            throw std::runtime_error("matrix file-size contract failed");
        bytes_ = static_cast<std::size_t>(status.st_size);
        mapping_ = ::mmap(nullptr, bytes_, PROT_READ, MAP_PRIVATE, descriptor_, 0);
        if (mapping_ == MAP_FAILED) throw std::runtime_error("matrix mmap failed");
    }

    ~Mapping() {
        if (mapping_ != MAP_FAILED) ::munmap(mapping_, bytes_);
        if (descriptor_ >= 0) ::close(descriptor_);
    }

    Mapping(const Mapping&) = delete;
    Mapping& operator=(const Mapping&) = delete;

    const std::byte* bytes() const { return static_cast<const std::byte*>(mapping_); }

  private:
    int descriptor_ = -1;
    void* mapping_ = MAP_FAILED;
    std::size_t bytes_ = 0;
};

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 11) {
            throw std::runtime_error(
                "usage: modular_full_replay MATRIX_NPY OFFSET ROWS COLUMNS SUPPORT_U32 "
                "TARGET_U32 OUTPUT_U32 PRIME THREADS EXPECTED_SUPPORT");
        }
        const std::filesystem::path matrix_path(argv[1]);
        const auto offset = parse_size(argv[2], "matrix offset", true);
        const auto rows = parse_size(argv[3], "matrix rows");
        const auto columns = parse_size(argv[4], "matrix columns");
        const std::filesystem::path support_path(argv[5]);
        const std::filesystem::path target_path(argv[6]);
        const std::filesystem::path output_path(argv[7]);
        const auto prime = parse_size(argv[8], "prime");
        const auto threads = parse_size(argv[9], "threads");
        const auto expected_support = parse_size(argv[10], "expected support", true);
        if (std::filesystem::exists(output_path)) throw std::runtime_error("refusing to overwrite output");

        const auto support = read_exact<std::uint32_t>(support_path);
        const auto target = read_exact<std::uint32_t>(target_path);
        if (support.size() != 2 * expected_support) throw std::runtime_error("support census drift");
        if (target.size() != columns) throw std::runtime_error("target census drift");
        for (std::size_t index = 0; index < expected_support; ++index) {
            if (support[2 * index] >= rows || support[2 * index + 1] >= prime)
                throw std::runtime_error("support value outside contract");
        }
        for (const auto value : target)
            if (value >= prime) throw std::runtime_error("target value outside field");

        const auto matrix_bytes = rows * columns * sizeof(std::int32_t);
        Mapping mapping(matrix_path, offset + matrix_bytes);
        const auto* matrix = reinterpret_cast<const std::int32_t*>(mapping.bytes() + offset);
        std::vector<std::uint8_t> is_residual(columns, 0);
        const auto started = std::chrono::steady_clock::now();
        omp_set_num_threads(static_cast<int>(threads));
#pragma omp parallel for schedule(static)
        for (std::int64_t coordinate = 0; coordinate < static_cast<std::int64_t>(columns); ++coordinate) {
            std::uint64_t observed = 0;
            for (std::size_t index = 0; index < expected_support; ++index) {
                const auto row = static_cast<std::size_t>(support[2 * index]);
                const auto coefficient = static_cast<std::uint64_t>(support[2 * index + 1]);
                observed += positive_mod(matrix[row * columns + static_cast<std::size_t>(coordinate)], prime) * coefficient;
                if ((index & 1023U) == 1023U) observed %= prime;
            }
            is_residual[static_cast<std::size_t>(coordinate)] = (observed % prime) != target[static_cast<std::size_t>(coordinate)];
        }
        const auto finished = std::chrono::steady_clock::now();

        std::vector<std::uint32_t> residual;
        residual.reserve(columns);
        for (std::size_t coordinate = 0; coordinate < columns; ++coordinate)
            if (is_residual[coordinate]) residual.push_back(static_cast<std::uint32_t>(coordinate));
        {
            std::ofstream destination(output_path, std::ios::binary | std::ios::out);
            destination.write(reinterpret_cast<const char*>(residual.data()),
                              static_cast<std::streamsize>(residual.size() * sizeof(std::uint32_t)));
            destination.flush();
            if (!destination) throw std::runtime_error("residual output write failed");
        }
        const auto seconds = std::chrono::duration_cast<std::chrono::duration<double>>(finished - started).count();
        std::cout << "{\"schema\":\"g0115-modular-full-replay-v1\",\"rows\":" << rows
                  << ",\"columns\":" << columns << ",\"support\":" << expected_support
                  << ",\"prime\":" << prime << ",\"threads\":" << threads
                  << ",\"residual_coordinates\":" << residual.size()
                  << ",\"seconds\":" << seconds << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
