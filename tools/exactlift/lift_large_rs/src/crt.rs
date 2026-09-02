pub fn inverse_mod(value: u128, modulus: u32) -> Option<u32> {
    let (mut old_r, mut r) = ((value % modulus as u128) as i64, modulus as i64);
    let (mut old_s, mut s) = (1_i64, 0_i64);
    while r != 0 {
        let quotient = old_r / r;
        (old_r, r) = (r, old_r - quotient * r);
        (old_s, s) = (s, old_s - quotient * s);
    }
    (old_r == 1).then(|| old_s.rem_euclid(modulus as i64) as u32)
}

pub fn combine(residue: u128, modulus: u128, next: u32, prime: u32) -> Option<u128> {
    let inverse = inverse_mod(modulus, prime)? as u128;
    let current_mod_prime = (residue % prime as u128) as u32;
    let delta = (next as u64 + prime as u64 - current_mod_prime as u64) % prime as u64;
    let multiplier = delta as u128 * inverse % prime as u128;
    residue.checked_add(modulus.checked_mul(multiplier)?)
}

pub fn is_prime(value: u32) -> bool {
    if value < 2 {
        return false;
    }
    let mut divisor = 2_u32;
    while divisor as u64 * divisor as u64 <= value as u64 {
        if value % divisor == 0 {
            return value == divisor;
        }
        divisor += if divisor == 2 { 1 } else { 2 };
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn crt_combines_named_primes() {
        let value = 9_876_543_210_u128;
        let mut residue = 0_u128;
        let mut modulus = 1_u128;
        for prime in [65_521, 65_519, 65_497] {
            assert!(is_prime(prime));
            residue = combine(residue, modulus, (value % prime as u128) as u32, prime).unwrap();
            modulus *= prime as u128;
        }
        assert_eq!(residue, value);
    }
}
