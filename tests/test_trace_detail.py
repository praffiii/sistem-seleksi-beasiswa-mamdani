import pytest

from fuzzy.engine import INPUT_VARS, infer


def test_fired_detail_alpha_is_min_of_degrees():
    trace = infer(
        {"IPK": 2.375, "Penghasilan": 0.0, "Tanggungan": 0.0, "Prestasi": 0.0}
    )
    assert len(trace.fired_detail) >= 1
    for fired_rule in trace.fired_detail:
        assert set(fired_rule.antecedent) == set(INPUT_VARS)
        assert set(fired_rule.degrees) == set(INPUT_VARS)
        assert fired_rule.alpha == pytest.approx(min(fired_rule.degrees.values()))


def test_fired_detail_matches_fired_exactly():
    trace = infer(
        {"IPK": 3.5, "Penghasilan": 2.0, "Tanggungan": 4.0, "Prestasi": 7.0}
    )
    derived = [(fr.alpha, fr.consequent) for fr in trace.fired_detail]
    assert derived == trace.fired
