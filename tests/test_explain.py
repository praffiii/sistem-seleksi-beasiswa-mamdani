import pytest

from fuzzy.explain import mf_degree_latex, mf_definition_latex
from fuzzy.membership import INPUT_SETS


def test_degree_rising_branch_matches_value():
    latex, value = mf_degree_latex("Sedang", INPUT_SETS["IPK"]["Sedang"], 2.375)
    assert value == pytest.approx(0.5)
    assert "0.50" in latex
    assert r"\frac" in latex


def test_degree_zero_outside_support():
    latex, value = mf_degree_latex("Tinggi", INPUT_SETS["IPK"]["Tinggi"], 2.0)
    assert value == 0.0
    assert latex.strip().endswith("= 0")


def test_degree_plateau_is_one():
    latex, value = mf_degree_latex("Rendah", INPUT_SETS["IPK"]["Rendah"], 1.0)
    assert value == 1.0
    assert latex.strip().endswith("= 1")


def test_right_shoulder_plateau_at_top_mirrors_trapmf():
    # Tinggi (2.75,3.5,4,4) at x=4 must be 1.0, same as trapmf's branch order.
    latex, value = mf_degree_latex("Tinggi", INPUT_SETS["IPK"]["Tinggi"], 4.0)
    assert value == 1.0
    assert latex.strip().endswith("= 1")


def test_definition_contains_cases_and_fraction():
    latex = mf_definition_latex("Sedang", INPUT_SETS["IPK"]["Sedang"])
    assert "begin{cases}" in latex
    assert r"\frac" in latex
