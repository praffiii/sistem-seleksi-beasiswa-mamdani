import pytest

from fuzzy.ranking import rank_applicants, select_top_n


def test_rank_orders_by_score_desc():
    applicants = [
        {
            "nama": "Low",
            "IPK": 0.0,
            "Penghasilan": 10.0,
            "Tanggungan": 0.0,
            "Prestasi": 0.0,
        },
        {
            "nama": "High",
            "IPK": 4.0,
            "Penghasilan": 0.0,
            "Tanggungan": 6.0,
            "Prestasi": 10.0,
        },
    ]
    ranked = rank_applicants(applicants)
    assert [row["nama"] for row in ranked] == ["High", "Low"]
    assert ranked[0]["score"] > ranked[1]["score"]
    assert ranked[0]["rank"] == 1


def test_tie_break_prefers_higher_ipk():
    # Both IPKs have full Tinggi membership, so the scores tie and IPK decides.
    applicant_a = {
        "nama": "A",
        "IPK": 3.5,
        "Penghasilan": 5.0,
        "Tanggungan": 3.0,
        "Prestasi": 6.0,
    }
    applicant_b = {
        "nama": "B",
        "IPK": 3.9,
        "Penghasilan": 5.0,
        "Tanggungan": 3.0,
        "Prestasi": 6.0,
    }
    ranked = rank_applicants([applicant_a, applicant_b])
    assert ranked[0]["score"] == pytest.approx(ranked[1]["score"])
    assert ranked[0]["nama"] == "B"


def test_select_top_n():
    applicants = [
        {
            "nama": name,
            "IPK": ipk,
            "Penghasilan": 3.0,
            "Tanggungan": 3.0,
            "Prestasi": 6.0,
        }
        for name, ipk in [("A", 3.9), ("B", 3.0), ("C", 2.2)]
    ]
    ranked = rank_applicants(applicants)
    top = select_top_n(ranked, 2)
    assert len(top) == 2
    assert top[0]["rank"] == 1 and top[1]["rank"] == 2
