import pytest

from fuzzy.engine import fuzzify, validate_and_clamp


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
