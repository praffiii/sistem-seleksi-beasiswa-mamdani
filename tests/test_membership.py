import matplotlib
import pytest

matplotlib.use("Agg")

from fuzzy.engine import infer
from fuzzy.membership import trapmf, INPUT_SETS, OUTPUT_SETS, DOMAINS
from fuzzy.plots import plot_aggregation, plot_membership


def test_left_shoulder_flat_at_start():
    # IPK Rendah (0,0,2,2.75): flat 1.0 from 0..2
    assert trapmf(0.0, (0, 0, 2, 2.75)) == 1.0
    assert trapmf(2.0, (0, 0, 2, 2.75)) == 1.0


def test_left_shoulder_ramp_down():
    # halfway down the 2..2.75 ramp
    assert trapmf(2.375, (0, 0, 2, 2.75)) == pytest.approx(0.5)
    assert trapmf(2.75, (0, 0, 2, 2.75)) == 0.0


def test_right_shoulder_flat_at_end():
    # IPK Tinggi (2.75,3.5,4,4): flat 1.0 from 3.5..4
    assert trapmf(4.0, (2.75, 3.5, 4, 4)) == 1.0
    assert trapmf(3.5, (2.75, 3.5, 4, 4)) == 1.0
    assert trapmf(2.75, (2.75, 3.5, 4, 4)) == 0.0


def test_triangle_as_trapezoid_peak():
    # IPK Sedang (2,2.75,2.75,3.5): peak 1.0 at 2.75
    assert trapmf(2.75, (2, 2.75, 2.75, 3.5)) == 1.0
    assert trapmf(2.375, (2, 2.75, 2.75, 3.5)) == pytest.approx(0.5)


def test_outside_support_is_zero():
    assert trapmf(-1.0, (0, 0, 2, 2.75)) == 0.0
    assert trapmf(5.0, (2, 2.75, 2.75, 3.5)) == 0.0


def test_params_present_and_shaped():
    assert set(INPUT_SETS) == {"IPK", "Penghasilan", "Tanggungan", "Prestasi"}
    for var, sets in INPUT_SETS.items():
        assert set(sets) == {"Rendah", "Sedang", "Tinggi"}
        for params in sets.values():
            assert len(params) == 4
    assert set(OUTPUT_SETS) == {"Rendah", "Sedang", "Tinggi"}
    assert DOMAINS["Prioritas"] == (0, 100)


def test_plots_return_figures():
    trace = infer(
        {
            "IPK": 3.5,
            "Penghasilan": 2.0,
            "Tanggungan": 4.0,
            "Prestasi": 7.0,
        }
    )
    figure_aggregation = plot_aggregation(trace)
    figure_membership = plot_membership("IPK")
    assert figure_aggregation is not None and figure_membership is not None
