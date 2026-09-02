#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Rational {
    pub numerator: i128,
    pub denominator: i128,
}

fn gcd(mut left: i128, mut right: i128) -> i128 {
    left = left.abs();
    right = right.abs();
    while right != 0 {
        (left, right) = (right, left % right);
    }
    left
}

pub fn gcd_u128(mut left: u128, mut right: u128) -> u128 {
    while right != 0 {
        (left, right) = (right, left % right);
    }
    left
}

pub fn lcm_u128(left: u128, right: u128) -> Option<u128> {
    left.checked_div(gcd_u128(left, right))?.checked_mul(right)
}

fn integer_sqrt(value: u128) -> u128 {
    if value < 2 {
        return value;
    }
    let mut low = 1_u128;
    let mut high = 1_u128 << ((128 - value.leading_zeros() as usize).div_ceil(2));
    while low + 1 < high {
        let middle = (low + high) / 2;
        if middle <= value / middle {
            low = middle;
        } else {
            high = middle;
        }
    }
    low
}

pub fn reconstruct(residue: u128, modulus: u128) -> Option<Rational> {
    if modulus < 2 || modulus > i128::MAX as u128 {
        return None;
    }
    if residue == 0 {
        return Some(Rational { numerator: 0, denominator: 1 });
    }
    let bound = integer_sqrt(modulus / 2) as i128;
    let (mut old_r, mut r) = (modulus as i128, (residue % modulus) as i128);
    let (mut old_t, mut t) = (0_i128, 1_i128);
    while r.abs() > bound {
        if r == 0 {
            return None;
        }
        let quotient = old_r / r;
        (old_r, r) = (r, old_r - quotient * r);
        (old_t, t) = (t, old_t - quotient * t);
    }
    if t == 0 || t.abs() > bound || gcd(r, t) != 1 {
        return None;
    }
    let (numerator, denominator) = if t < 0 { (-r, -t) } else { (r, t) };
    if denominator <= 0 {
        return None;
    }
    let congruence = (numerator - (residue as i128) * denominator).rem_euclid(modulus as i128);
    (congruence == 0).then_some(Rational { numerator, denominator })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn inverse_mod(value: i128, modulus: i128) -> i128 {
        let (mut old_r, mut r) = (value, modulus);
        let (mut old_s, mut s) = (1_i128, 0_i128);
        while r != 0 {
            let quotient = old_r / r;
            (old_r, r) = (r, old_r - quotient * r);
            (old_s, s) = (s, old_s - quotient * s);
        }
        old_s.rem_euclid(modulus)
    }

    #[test]
    fn reconstructs_signed_fraction_and_zero() {
        let modulus = 65_521_u128.pow(4);
        for expected in [
            Rational { numerator: 17, denominator: 123_457 },
            Rational { numerator: -31, denominator: 33_554_432 },
            Rational { numerator: 0, denominator: 1 },
        ] {
            let residue = if expected.numerator == 0 {
                0
            } else {
                (expected.numerator * inverse_mod(expected.denominator, modulus as i128))
                    .rem_euclid(modulus as i128) as u128
            };
            assert_eq!(reconstruct(residue, modulus), Some(expected));
        }
    }
}
