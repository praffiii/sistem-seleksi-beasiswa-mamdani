import pytest

from fuzzy.engine import (
    DEFAULT_RULES_PATH,
    evaluate_rules,
    fuzzify,
    load_rules,
    validate_and_clamp,
)


def test_clamp_income_above_domain():
    # Income 15 is possible but capped at full Tinggi (domain max 10).
    clamped = validate_and_clamp(
        {
            "IPK": 3.0,
            "Penghasilan": 15.0,
            "Tanggungan": 2.0,
            "Prestasi": 5.0,
        }
    )
    assert clamped["Penghasilan"] == 10.0


def test_reject_impossible_ipk():
    with pytest.raises(ValueError):
        validate_and_clamp(
            {
                "IPK": 4.2,
                "Penghasilan": 2.0,
                "Tanggungan": 2.0,
                "Prestasi": 5.0,
            }
        )


def test_reject_negative():
    with pytest.raises(ValueError):
        validate_and_clamp(
            {
                "IPK": 3.0,
                "Penghasilan": -1.0,
                "Tanggungan": 2.0,
                "Prestasi": 5.0,
            }
        )


def test_fuzzify_split_membership():
    # IPK 2.375 sits halfway between Rendah and Sedang.
    memberships = fuzzify(
        {
            "IPK": 2.375,
            "Penghasilan": 0.0,
            "Tanggungan": 0.0,
            "Prestasi": 0.0,
        }
    )
    assert memberships["IPK"]["Rendah"] == pytest.approx(0.5)
    assert memberships["IPK"]["Sedang"] == pytest.approx(0.5)
    assert memberships["IPK"]["Tinggi"] == 0.0
    assert memberships["Penghasilan"]["Rendah"] == 1.0


def test_load_rules_count_and_shape():
    rules = load_rules(DEFAULT_RULES_PATH)
    assert len(rules) == 81
    rule = rules[0]
    assert rule.antecedent == {
        "IPK": "Rendah",
        "Penghasilan": "Rendah",
        "Tanggungan": "Rendah",
        "Prestasi": "Rendah",
    }
    assert rule.consequent == "Rendah"


def test_all_consequents_valid():
    rules = load_rules(DEFAULT_RULES_PATH)
    assert {rule.consequent for rule in rules} == {"Rendah", "Sedang", "Tinggi"}


def test_single_rule_fires_at_full_strength():
    # IPK=4 Tinggi, income=0 Rendah, tang=6 Tinggi, prestasi=10 Tinggi
    # -> exactly one matching rule (all degrees 1.0), alpha = 1.0
    degrees = fuzzify(
        {
            "IPK": 4.0,
            "Penghasilan": 0.0,
            "Tanggungan": 6.0,
            "Prestasi": 10.0,
        }
    )
    fired = evaluate_rules(degrees, load_rules(DEFAULT_RULES_PATH))
    assert len(fired) == 1
    alpha, consequent = fired[0]
    assert alpha == pytest.approx(1.0)
    assert consequent == "Tinggi"


def test_firing_strength_is_min_of_antecedents():
    # IPK 2.375 -> Rendah 0.5 / Sedang 0.5; others fully one set.
    degrees = fuzzify(
        {
            "IPK": 2.375,
            "Penghasilan": 0.0,
            "Tanggungan": 0.0,
            "Prestasi": 0.0,
        }
    )
    fired = evaluate_rules(degrees, load_rules(DEFAULT_RULES_PATH))
    # Two rules fire (IPK Rendah and IPK Sedang branches), each alpha 0.5.
    assert len(fired) == 2
    assert all(alpha == pytest.approx(0.5) for alpha, _ in fired)
