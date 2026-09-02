mod modular;
mod rational;
mod synthetic;

use std::env;
use std::fs;
use std::path::PathBuf;

fn value<T: std::str::FromStr>(arguments: &[String], name: &str) -> Result<T, String> {
    let position = arguments
        .iter()
        .position(|argument| argument == name)
        .ok_or_else(|| format!("missing {name}"))?;
    arguments
        .get(position + 1)
        .ok_or_else(|| format!("missing value for {name}"))?
        .parse()
        .map_err(|_| format!("invalid value for {name}"))
}

fn synthetic_command(arguments: &[String]) -> Result<(), String> {
    let output: PathBuf = value(arguments, "--output")?;
    let config = synthetic::SyntheticConfig {
        rank: value(arguments, "--rank")?,
        union_rows: value(arguments, "--union-rows")?,
        planted_support: value(arguments, "--support")?,
        denominator_block: value(arguments, "--denominator-block")?,
        prime: value(arguments, "--prime")?,
        lu_block: value(arguments, "--lu-block")?,
        row_tile: value(arguments, "--row-tile")?,
        threads: value(arguments, "--threads")?,
        seed: value(arguments, "--seed")?,
        max_steps: value(arguments, "--max-steps")?,
        reconstruct_every: value(arguments, "--reconstruct-every")?,
    };
    let report = synthetic::run(&config)?;
    let encoded = serde_json::to_string_pretty(&report).map_err(|error| error.to_string())? + "\n";
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(&output, &encoded).map_err(|error| error.to_string())?;
    print!("{encoded}");
    Ok(())
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    let result = match arguments.get(1).map(String::as_str) {
        Some("synthetic") => synthetic_command(&arguments[2..]),
        _ => Err("usage: max11-lift-large synthetic --rank N --union-rows M --support S --denominator-block B --prime P --lu-block B --row-tile T --threads N --seed S --max-steps K --reconstruct-every K --output FILE".to_string()),
    };
    if let Err(error) = result {
        eprintln!("ERROR: {error}");
        std::process::exit(2);
    }
}
