#!/usr/bin/env python3
"""Known-answer controls for the project-local numerical and exact toolchain."""

from __future__ import annotations

from fractions import Fraction
from importlib.metadata import version

import cvc5
from cvc5 import Kind
from flint import fmpq
from highspy import Highs, HighsModelStatus, kHighsInf
import sympy as sp
import z3


def require(condition: bool, label: str) -> None:
    """Optimization-resistant control assertion with a diagnostic."""
    if not condition:
        raise RuntimeError(f"toolchain control failed: {label}")


def check_z3() -> None:
    x = z3.Real("z3_x")
    sat_solver = z3.Solver()
    sat_solver.add(x == z3.Q(1, 3))
    require(sat_solver.check() == z3.sat, "Z3 SAT arm")
    require(sat_solver.model().eval(x) == z3.Q(1, 3), "Z3 exact rational model")

    unsat_solver = z3.Solver()
    unsat_solver.add(x < 0, x > 0)
    require(unsat_solver.check() == z3.unsat, "Z3 UNSAT arm")


def check_cvc5() -> None:
    solver = cvc5.Solver()
    solver.setLogic("QF_LRA")
    real = solver.getRealSort()
    x = solver.mkConst(real, "cvc5_x")
    one_third = solver.mkReal(1, 3)
    solver.assertFormula(solver.mkTerm(Kind.EQUAL, x, one_third))
    require(solver.checkSat().isSat(), "cvc5 Python SAT arm")

    null_solver = cvc5.Solver()
    null_solver.setLogic("QF_LRA")
    y = null_solver.mkConst(null_solver.getRealSort(), "cvc5_y")
    zero = null_solver.mkReal(0)
    null_solver.assertFormula(null_solver.mkTerm(Kind.LT, y, zero))
    null_solver.assertFormula(null_solver.mkTerm(Kind.GT, y, zero))
    require(null_solver.checkSat().isUnsat(), "cvc5 Python UNSAT arm")


def check_exact_arithmetic() -> None:
    require(fmpq(1, 3) + fmpq(2, 3) == 1, "FLINT rational addition")
    matrix = sp.Matrix([[sp.Rational(1, 3), 1], [1, 3]])
    require(matrix.det() == 0, "SymPy exact singular determinant")
    require(Fraction(1, 7) * 7 == 1, "stdlib Fraction exact multiplication")


def check_highs() -> None:
    model = Highs()
    model.setOptionValue("output_flag", False)
    model.addVar(1.0, kHighsInf)
    model.changeColCost(0, 1.0)
    model.run()
    require(model.getModelStatus() == HighsModelStatus.kOptimal, "HiGHS optimal status")
    require(abs(model.getSolution().col_value[0] - 1.0) < 1e-12, "HiGHS planted optimum")


def check_dependency_versions() -> None:
    require(version("tqdm") == "4.70.0", "tqdm pinned version")


def main() -> None:
    check_z3()
    check_cvc5()
    check_exact_arithmetic()
    check_highs()
    check_dependency_versions()
    print("toolchain-known-answer-controls: PASS")


if __name__ == "__main__":
    main()
