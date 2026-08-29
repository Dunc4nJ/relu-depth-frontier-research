#!/usr/bin/env python3
from fractions import Fraction
import json
import pathlib
from cache_contract import load_columns, n9_metadata, write_result

ROOT = pathlib.Path('/data/projects/relu-depth-frontier-research')
CERT = ROOT / 'literature/repos/max-relu-certificates/certificates/certificate_9_4.json'

certificate = json.loads(CERT.read_text())
columns, _ = load_columns('n9_columns', n9_metadata(), 337, required=True)
assert len(certificate['terms']) == len(columns)

linear = [Fraction() for _ in range(9)]
hinges = {}
for term, (term_linear, term_hinges) in zip(certificate['terms'], columns):
    coefficient = Fraction(term['coefficient'])
    for index, value in enumerate(term_linear):
        linear[index] += coefficient * value
    for direction, value in term_hinges.items():
        hinges[direction] = hinges.get(direction, Fraction()) + coefficient * value

nonzero_hinges = {direction: value for direction, value in hinges.items() if value}
print('published_MAX9_linear', [str(value) for value in linear])
print('published_MAX9_nonzero_hinges', len(nonzero_hinges))
assert linear == [Fraction()] * 8 + [Fraction(1)]
assert not nonzero_hinges
print('published_MAX9_cached_exact_verification OK')
write_result('n9_cached_verify',{'linear':[str(value) for value in linear],'nonzero_hinges':len(nonzero_hinges),'verified':True})
