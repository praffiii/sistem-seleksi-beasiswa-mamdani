import pytest

from fuzzy.derivation import build_defuzzification_derivation
from fuzzy.engine import (
    DEFAULT_RULES_PATH,
    evaluate_rules,
    fuzzify,
    infer,
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


def test_infer_high_priority_composite_moment():
    trace = infer(
        {
            "IPK": 4.0,
            "Penghasilan": 0.0,
            "Tanggungan": 6.0,
            "Prestasi": 10.0,
        }
    )
    assert trace.score == pytest.approx(84.44, abs=0.2)
    assert trace.label == "Tinggi"


def test_infer_low_priority_composite_moment():
    # IPK=0 Rendah, income=10 Tinggi, tang=0 Rendah, prestasi=0 Rendah -> Rendah
    trace = infer(
        {
            "IPK": 0.0,
            "Penghasilan": 10.0,
            "Tanggungan": 0.0,
            "Prestasi": 0.0,
        }
    )
    assert trace.score == pytest.approx(15.56, abs=0.2)
    assert trace.label == "Rendah"


def test_reference_case_composite_moment_regions():
    trace = infer(
        {
            "IPK": 3.20,
            "Penghasilan": 4.0,
            "Tanggungan": 4.0,
            "Prestasi": 7.0,
        }
    )

    assert trace.score == pytest.approx(64.17, abs=0.01)
    assert trace.clip_heights["Sedang"] == pytest.approx(0.5)
    assert trace.clip_heights["Tinggi"] == pytest.approx(0.5)
    assert trace.clip_heights["Rendah"] == pytest.approx(0.0)
    assert len(trace.regions) == 5

    expected = [
        ("Sedang", "Rising triangle", 20.0, 35.0, 3.75, 112.50),
        ("Sedang", "Plateau rectangle", 35.0, 65.0, 15.00, 750.00),
        ("Sedang", "Falling triangle", 65.0, 80.0, 3.75, 262.50),
        ("Tinggi", "Rising triangle", 60.0, 70.0, 2.50, 166.67),
        ("Tinggi", "Plateau rectangle", 70.0, 100.0, 15.00, 1275.00),
    ]
    for region, expected_region in zip(trace.regions, expected):
        output_label, shape, z_start, z_end, area, moment = expected_region
        assert region["output_label"] == output_label
        assert region["shape"] == shape
        assert region["z_start"] == pytest.approx(z_start, abs=0.01)
        assert region["z_end"] == pytest.approx(z_end, abs=0.01)
        assert region["A"] == pytest.approx(area, abs=0.01)
        assert region["M"] == pytest.approx(moment, abs=0.01)

    assert sum(region["A"] for region in trace.regions) == pytest.approx(40.00)
    assert sum(region["M"] for region in trace.regions) == pytest.approx(
        2566.67,
        abs=0.01,
    )


def test_reference_case_derivation_cut_points_and_bounds():
    trace = infer(
        {
            "IPK": 3.20,
            "Penghasilan": 4.0,
            "Tanggungan": 4.0,
            "Prestasi": 7.0,
        }
    )
    derivation = build_defuzzification_derivation(trace)

    cuts = {
        (group["label"], edge["edge"]): edge["z"]
        for group in derivation["cut_points"]
        for edge in group["edges"]
    }
    assert cuts[("Sedang", "rising")] == pytest.approx(35.0)
    assert cuts[("Sedang", "falling")] == pytest.approx(65.0)
    assert cuts[("Tinggi", "rising")] == pytest.approx(70.0)
    assert ("Tinggi", "falling") not in cuts

    expected_bounds = [
        (68.06, -44.44),
        (1056.25, 306.25),
        (2844.44, 2581.94),
        (-1633.33, -1800.00),
        (2500.00, 1225.00),
    ]
    for region, (upper, lower) in zip(derivation["regions"], expected_bounds):
        assert region["moment"]["upper_eval"] == pytest.approx(upper, abs=0.01)
        assert region["moment"]["lower_eval"] == pytest.approx(lower, abs=0.01)

    assert [region["list_label"] for region in derivation["regions"]] == [
        "A1 = Segitiga naik Sedang (z = 20 hingga z = 35)",
        "A2 = Persegi panjang datar Sedang (z = 35 hingga z = 65)",
        "A3 = Segitiga turun Sedang (z = 65 hingga z = 80)",
        "A4 = Segitiga naik Tinggi (z = 60 hingga z = 70)",
        "A5 = Persegi panjang datar Tinggi (z = 70 hingga z = 100)",
    ]

    assert "112.50 + 750.00 + 262.50 + 166.67 + 1275.00" in derivation[
        "moment_sum_latex"
    ]
    assert "3.75 + 15.00 + 3.75 + 2.50 + 15.00" in derivation[
        "area_sum_latex"
    ]
    assert derivation["crisp_latex"].endswith("= 64.17")


def test_trace_carries_all_steps():
    trace = infer(
        {
            "IPK": 3.5,
            "Penghasilan": 2.0,
            "Tanggungan": 4.0,
            "Prestasi": 7.0,
        }
    )
    assert set(trace.degrees) == {
        "IPK",
        "Penghasilan",
        "Tanggungan",
        "Prestasi",
    }
    assert len(trace.fired) >= 1
    assert set(trace.clip_heights) == {"Rendah", "Sedang", "Tinggi"}
    assert len(trace.xs) == 1001
    assert trace.agg == []
    assert len(trace.regions) >= 1
    assert 0.0 <= trace.score <= 100.0


def test_pdf_report_is_nonempty_pdf():
    from fuzzy.report import build_pdf

    trace = infer(
        {
            "IPK": 3.5,
            "Penghasilan": 2.0,
            "Tanggungan": 4.0,
            "Prestasi": 7.0,
        }
    )
    data = build_pdf(trace, applicant_name="Test")
    assert isinstance(data, (bytes, bytearray))
    assert data[:4] == b"%PDF"
    assert len(data) > 1000
