use std::env;

fn main() {
    println!("cargo:rustc-link-lib=openblas");
    println!("cargo:rerun-if-changed=src/cuda_backend.cu");
    if env::var_os("CARGO_FEATURE_CUDA").is_none() {
        return;
    }

    let cuda_home = env::var("CUDA_HOME").unwrap_or_else(|_| "/usr/local/cuda".to_owned());
    cc::Build::new()
        .cuda(true)
        .cpp(true)
        .file("src/cuda_backend.cu")
        .include(format!("{cuda_home}/include"))
        .flag("-O3")
        .flag("-lineinfo")
        .flag("-std=c++17")
        .compile("max11_streamrank_cuda");
    println!("cargo:rustc-link-search=native={cuda_home}/lib64");
    println!("cargo:rustc-link-lib=cublas");
    println!("cargo:rustc-link-lib=cudart");
    println!("cargo:rustc-link-lib=stdc++");
}
