#include <cublas_v2.h>
#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

thread_local std::string last_error;

struct Observation {
  uint64_t gemm_calls;
  uint64_t scalar_products;
  double pack_seconds;
  double gemm_seconds;
  double modular_reduce_seconds;
  double transfer_seconds;
  uint64_t host_to_device_bytes;
  uint64_t device_to_host_bytes;
  uint64_t peak_allocated_bytes;
};

struct Context {
  size_t rows;
  uint32_t prime;
  uint64_t reciprocal;
  size_t block_size;
  size_t panel_size;
  size_t max_batch;
  size_t rank = 0;
  cublasHandle_t handle = nullptr;
  cudaEvent_t event_start = nullptr;
  cudaEvent_t event_stop = nullptr;
  std::vector<uint32_t *> basis_segments;
  uint32_t *matrix = nullptr;
  double *dense = nullptr;
  double *source = nullptr;
  double *coefficients = nullptr;
  size_t *pivots = nullptr;
  uint32_t *panel = nullptr;
  size_t *panel_pivots = nullptr;
  uint64_t allocated_bytes = 0;
  uint64_t peak_allocated_bytes = 0;
};

void check_cuda(cudaError_t status, const char *operation) {
  if (status != cudaSuccess) {
    throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
  }
}

void check_cublas(cublasStatus_t status, const char *operation) {
  if (status != CUBLAS_STATUS_SUCCESS) {
    throw std::runtime_error(std::string(operation) + ": cuBLAS status " +
                             std::to_string(static_cast<int>(status)));
  }
}

template <class T> void allocate(Context &ctx, T **pointer, size_t count) {
  if (count == 0 || count > SIZE_MAX / sizeof(T)) {
    throw std::runtime_error("invalid CUDA allocation size");
  }
  check_cuda(cudaMalloc(reinterpret_cast<void **>(pointer), count * sizeof(T)), "cudaMalloc");
  ctx.allocated_bytes += count * sizeof(T);
  ctx.peak_allocated_bytes = std::max(ctx.peak_allocated_bytes, ctx.allocated_bytes);
}

void ensure_basis_segment(Context &ctx, size_t segment) {
  while (ctx.basis_segments.size() <= segment) {
    uint32_t *storage = nullptr;
    allocate(ctx, &storage, ctx.rows * ctx.block_size);
    ctx.basis_segments.push_back(storage);
  }
}

void zero_observation(Observation &observation, const Context &ctx) {
  std::memset(&observation, 0, sizeof(observation));
  observation.peak_allocated_bytes = ctx.peak_allocated_bytes;
}

void event_start(Context &ctx) {
  check_cuda(cudaEventRecord(ctx.event_start), "cudaEventRecord(start)");
}

double event_stop(Context &ctx, const char *operation) {
  check_cuda(cudaEventRecord(ctx.event_stop), "cudaEventRecord(stop)");
  check_cuda(cudaEventSynchronize(ctx.event_stop), operation);
  float milliseconds = 0.0F;
  check_cuda(cudaEventElapsedTime(&milliseconds, ctx.event_start, ctx.event_stop),
             "cudaEventElapsedTime");
  return static_cast<double>(milliseconds) / 1000.0;
}

template <class F> double transfer_time(F operation) {
  const auto started = std::chrono::steady_clock::now();
  operation();
  return std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
}

__global__ void u32_to_f64(const uint32_t *input, double *output, size_t count) {
  const size_t index = blockIdx.x * static_cast<size_t>(blockDim.x) + threadIdx.x;
  if (index < count) {
    output[index] = static_cast<double>(input[index]);
  }
}

__global__ void gather_matrix_coefficients(const uint32_t *matrix, size_t rows,
                                           size_t columns, const size_t *pivots,
                                           size_t pivot_start, size_t count,
                                           double *output) {
  const size_t index = blockIdx.x * static_cast<size_t>(blockDim.x) + threadIdx.x;
  const size_t entries = count * columns;
  if (index < entries) {
    const size_t column = index / count;
    const size_t local = index - column * count;
    output[index] = static_cast<double>(matrix[column * rows + pivots[pivot_start + local]]);
  }
}

__global__ void gather_basis_coefficients(const uint32_t *basis, size_t rows,
                                          size_t old_columns, const size_t *pivots,
                                          size_t new_columns, double *output) {
  const size_t index = blockIdx.x * static_cast<size_t>(blockDim.x) + threadIdx.x;
  const size_t entries = old_columns * new_columns;
  if (index < entries) {
    const size_t old_column = index / new_columns;
    const size_t new_column = index - old_column * new_columns;
    output[index] = static_cast<double>(basis[old_column * rows + pivots[new_column]]);
  }
}

__global__ void f64_to_residue(const double *input, uint32_t *output, size_t count,
                               uint32_t prime, uint64_t reciprocal) {
  const size_t index = blockIdx.x * static_cast<size_t>(blockDim.x) + threadIdx.x;
  if (index >= count) {
    return;
  }
  const int64_t integer = __double2ll_rn(input[index]);
  const bool negative = integer < 0;
  const uint64_t magnitude = negative ? static_cast<uint64_t>(-integer)
                                      : static_cast<uint64_t>(integer);
  const uint64_t quotient = __umul64hi(magnitude, reciprocal);
  uint64_t remainder = magnitude - quotient * static_cast<uint64_t>(prime);
  if (remainder >= prime) {
    remainder -= prime;
  }
  output[index] = negative && remainder != 0 ? prime - static_cast<uint32_t>(remainder)
                                             : static_cast<uint32_t>(remainder);
}

dim3 blocks_for(size_t count) {
  constexpr size_t threads = 256;
  return dim3(static_cast<unsigned int>((count + threads - 1) / threads));
}

void pack_product(Context &ctx, const uint32_t *target, size_t columns,
                  const uint32_t *source, size_t source_columns,
                  const size_t *coefficient_pivots, size_t coefficient_pivot_start,
                  bool coefficients_from_matrix, Observation &observation) {
  constexpr unsigned int threads = 256;
  event_start(ctx);
  u32_to_f64<<<blocks_for(ctx.rows * columns), threads>>>(target, ctx.dense,
                                                          ctx.rows * columns);
  u32_to_f64<<<blocks_for(ctx.rows * source_columns), threads>>>(
      source, ctx.source, ctx.rows * source_columns);
  if (coefficients_from_matrix) {
    gather_matrix_coefficients<<<blocks_for(source_columns * columns), threads>>>(
        target, ctx.rows, columns, coefficient_pivots, coefficient_pivot_start,
        source_columns, ctx.coefficients);
  } else {
    gather_basis_coefficients<<<blocks_for(source_columns * columns), threads>>>(
        target, ctx.rows, columns, coefficient_pivots, source_columns,
        ctx.coefficients);
  }
  check_cuda(cudaGetLastError(), "CUDA packing kernels");
  observation.pack_seconds += event_stop(ctx, "CUDA packing synchronization");
}

void gemm_and_reduce(Context &ctx, uint32_t *target, size_t columns,
                     size_t source_columns, Observation &observation) {
  const double alpha = -1.0;
  const double beta = 1.0;
  event_start(ctx);
  check_cublas(cublasDgemm(ctx.handle, CUBLAS_OP_N, CUBLAS_OP_N,
                           static_cast<int>(ctx.rows), static_cast<int>(columns),
                           static_cast<int>(source_columns), &alpha, ctx.source,
                           static_cast<int>(ctx.rows), ctx.coefficients,
                           static_cast<int>(source_columns), &beta, ctx.dense,
                           static_cast<int>(ctx.rows)),
               "cublasDgemm");
  observation.gemm_seconds += event_stop(ctx, "cuBLAS dgemm synchronization");

  constexpr unsigned int threads = 256;
  event_start(ctx);
  f64_to_residue<<<blocks_for(ctx.rows * columns), threads>>>(
      ctx.dense, target, ctx.rows * columns, ctx.prime, ctx.reciprocal);
  check_cuda(cudaGetLastError(), "f64_to_residue");
  observation.modular_reduce_seconds += event_stop(ctx, "CUDA residue reduction synchronization");
  observation.gemm_calls += 1;
  observation.scalar_products +=
      static_cast<uint64_t>(ctx.rows) * columns * source_columns;
}

void upload_panel(Context &ctx, const uint32_t *host_panel, size_t panel_columns,
                  size_t rank_before, Observation &observation) {
  size_t copied = 0;
  while (copied < panel_columns) {
    const size_t rank = rank_before + copied;
    const size_t segment = rank / ctx.block_size;
    const size_t offset = rank % ctx.block_size;
    const size_t count = std::min(panel_columns - copied, ctx.block_size - offset);
    ensure_basis_segment(ctx, segment);
    const size_t bytes = ctx.rows * count * sizeof(uint32_t);
    observation.transfer_seconds += transfer_time([&] {
      check_cuda(cudaMemcpy(ctx.basis_segments[segment] + offset * ctx.rows,
                            host_panel + copied * ctx.rows, bytes,
                            cudaMemcpyHostToDevice),
                 "upload panel basis");
    });
    observation.host_to_device_bytes += bytes;
    copied += count;
  }
  ctx.rank = rank_before + panel_columns;
  observation.peak_allocated_bytes = ctx.peak_allocated_bytes;
}

} // namespace

extern "C" {

const char *max11_cuda_last_error() { return last_error.c_str(); }

int max11_cuda_create(size_t rows, uint32_t prime, size_t block_size,
                      size_t panel_size, size_t max_batch, void **result) {
  try {
    auto *ctx = new Context{};
    ctx->rows = rows;
    ctx->prime = prime;
    ctx->reciprocal = UINT64_MAX / prime + uint64_t{UINT64_MAX % prime == prime - 1};
    ctx->block_size = block_size;
    ctx->panel_size = panel_size;
    ctx->max_batch = max_batch;
    check_cublas(cublasCreate(&ctx->handle), "cublasCreate");
    check_cublas(cublasSetPointerMode(ctx->handle, CUBLAS_POINTER_MODE_HOST),
                 "cublasSetPointerMode");
    check_cublas(cublasSetMathMode(ctx->handle, CUBLAS_DEFAULT_MATH),
                 "cublasSetMathMode");
    check_cuda(cudaEventCreate(&ctx->event_start), "cudaEventCreate(start)");
    check_cuda(cudaEventCreate(&ctx->event_stop), "cudaEventCreate(stop)");
    allocate(*ctx, &ctx->matrix, rows * max_batch);
    allocate(*ctx, &ctx->dense, rows * std::max(max_batch, block_size));
    allocate(*ctx, &ctx->source, rows * block_size);
    allocate(*ctx, &ctx->coefficients, block_size * max_batch);
    allocate(*ctx, &ctx->pivots, rows);
    allocate(*ctx, &ctx->panel, rows * panel_size);
    allocate(*ctx, &ctx->panel_pivots, panel_size);
    *result = ctx;
    return 0;
  } catch (const std::exception &error) {
    last_error = error.what();
    return 1;
  }
}

int max11_cuda_destroy(void *raw) {
  auto *ctx = static_cast<Context *>(raw);
  if (ctx == nullptr) {
    return 0;
  }
  for (auto *segment : ctx->basis_segments) {
    cudaFree(segment);
  }
  cudaFree(ctx->matrix);
  cudaFree(ctx->dense);
  cudaFree(ctx->source);
  cudaFree(ctx->coefficients);
  cudaFree(ctx->pivots);
  cudaFree(ctx->panel);
  cudaFree(ctx->panel_pivots);
  if (ctx->event_start != nullptr) {
    cudaEventDestroy(ctx->event_start);
  }
  if (ctx->event_stop != nullptr) {
    cudaEventDestroy(ctx->event_stop);
  }
  if (ctx->handle != nullptr) {
    cublasDestroy(ctx->handle);
  }
  delete ctx;
  return 0;
}

int max11_cuda_reduce_existing(void *raw, uint32_t *host_matrix, size_t columns,
                               const size_t *host_pivots, size_t rank,
                               Observation *observation) {
  try {
    auto &ctx = *static_cast<Context *>(raw);
    zero_observation(*observation, ctx);
    if (columns == 0 || columns > ctx.max_batch || rank != ctx.rank) {
      throw std::runtime_error("CUDA reduce shape/rank mismatch");
    }
    const size_t matrix_bytes = ctx.rows * columns * sizeof(uint32_t);
    const size_t pivot_bytes = rank * sizeof(size_t);
    observation->transfer_seconds += transfer_time([&] {
      check_cuda(cudaMemcpy(ctx.matrix, host_matrix, matrix_bytes, cudaMemcpyHostToDevice),
                 "upload batch matrix");
      if (rank != 0) {
        check_cuda(cudaMemcpy(ctx.pivots, host_pivots, pivot_bytes,
                              cudaMemcpyHostToDevice),
                   "upload pivot rows");
      }
    });
    observation->host_to_device_bytes += matrix_bytes + pivot_bytes;

    for (size_t start = 0; start < rank; start += ctx.block_size) {
      const size_t count = std::min(ctx.block_size, rank - start);
      const size_t segment = start / ctx.block_size;
      pack_product(ctx, ctx.matrix, columns, ctx.basis_segments.at(segment), count,
                   ctx.pivots, start, true, *observation);
      gemm_and_reduce(ctx, ctx.matrix, columns, count, *observation);
    }

    observation->transfer_seconds += transfer_time([&] {
      check_cuda(cudaMemcpy(host_matrix, ctx.matrix, matrix_bytes, cudaMemcpyDeviceToHost),
                 "download reduced batch matrix");
    });
    observation->device_to_host_bytes += matrix_bytes;
    observation->peak_allocated_bytes = ctx.peak_allocated_bytes;
    return 0;
  } catch (const std::exception &error) {
    last_error = error.what();
    return 1;
  }
}

int max11_cuda_apply_panel(void *raw, uint32_t *host_matrix, size_t total_columns,
                           size_t future_start, const uint32_t *host_panel,
                           const size_t *host_panel_pivots, size_t panel_columns,
                           size_t rank_before, uint32_t *host_basis_tail,
                           Observation *prior_observation,
                           Observation *future_observation) {
  try {
    auto &ctx = *static_cast<Context *>(raw);
    zero_observation(*prior_observation, ctx);
    zero_observation(*future_observation, ctx);
    if (total_columns > ctx.max_batch || future_start > total_columns ||
        panel_columns == 0 || panel_columns > ctx.panel_size || rank_before != ctx.rank) {
      throw std::runtime_error("CUDA panel shape/rank mismatch");
    }

    const size_t panel_bytes = ctx.rows * panel_columns * sizeof(uint32_t);
    const size_t panel_pivot_bytes = panel_columns * sizeof(size_t);
    auto &panel_transfer_observation =
        rank_before % ctx.block_size == 0 ? *future_observation : *prior_observation;
    panel_transfer_observation.transfer_seconds += transfer_time([&] {
      check_cuda(cudaMemcpy(ctx.panel, host_panel, panel_bytes, cudaMemcpyHostToDevice),
                 "upload panel");
      check_cuda(cudaMemcpy(ctx.panel_pivots, host_panel_pivots, panel_pivot_bytes,
                            cudaMemcpyHostToDevice),
                 "upload panel pivots");
    });
    panel_transfer_observation.host_to_device_bytes += panel_bytes + panel_pivot_bytes;

    const size_t old_columns = rank_before % ctx.block_size;
    if (old_columns != 0) {
      const size_t new_columns =
          std::min(panel_columns, ctx.block_size - old_columns);
      const size_t segment = rank_before / ctx.block_size;
      auto *basis = ctx.basis_segments.at(segment);
      pack_product(ctx, basis, old_columns, ctx.panel, new_columns,
                   ctx.panel_pivots, 0, false, *prior_observation);
      gemm_and_reduce(ctx, basis, old_columns, new_columns, *prior_observation);
      const size_t bytes = ctx.rows * old_columns * sizeof(uint32_t);
      prior_observation->transfer_seconds += transfer_time([&] {
        check_cuda(cudaMemcpy(host_basis_tail, basis, bytes, cudaMemcpyDeviceToHost),
                   "download maintained basis tail");
      });
      prior_observation->device_to_host_bytes += bytes;
    }

    upload_panel(ctx, host_panel, panel_columns, rank_before, panel_transfer_observation);

    const size_t future_columns = total_columns - future_start;
    if (future_columns != 0) {
      auto *future = ctx.matrix + future_start * ctx.rows;
      pack_product(ctx, future, future_columns, ctx.panel, panel_columns,
                   ctx.panel_pivots, 0, true, *future_observation);
      gemm_and_reduce(ctx, future, future_columns, panel_columns, *future_observation);
      const size_t bytes = ctx.rows * future_columns * sizeof(uint32_t);
      future_observation->transfer_seconds += transfer_time([&] {
        check_cuda(cudaMemcpy(host_matrix + future_start * ctx.rows, future, bytes,
                              cudaMemcpyDeviceToHost),
                   "download panel-reduced future matrix");
      });
      future_observation->device_to_host_bytes += bytes;
    }
    prior_observation->peak_allocated_bytes = ctx.peak_allocated_bytes;
    future_observation->peak_allocated_bytes = ctx.peak_allocated_bytes;
    return 0;
  } catch (const std::exception &error) {
    last_error = error.what();
    return 1;
  }
}

} // extern "C"
