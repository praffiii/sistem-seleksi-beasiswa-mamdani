"""Batch ranking and top-N selection over the Mamdani engine."""

from fuzzy.engine import infer, load_rules


def rank_applicants(applicants, rules=None):
    """Score every applicant and return a list sorted best-first.

    Each input dict must carry the four input keys (IPK, Penghasilan,
    Tanggungan, Prestasi) plus any identifier fields (e.g. 'nama').
    Returns new dicts with added 'score', 'label', and 'rank'.
    Tie-break: score desc, IPK desc, income asc, achievement desc, input order.
    """
    if rules is None:
        rules = load_rules()
    scored = []
    for index, applicant in enumerate(applicants):
        trace = infer(applicant, rules)
        row = dict(applicant)
        row["score"] = trace.score
        row["label"] = trace.label
        row["_index"] = index
        scored.append(row)
    scored.sort(
        key=lambda row: (
            -row["score"],
            -float(row["IPK"]),
            float(row["Penghasilan"]),
            -float(row["Prestasi"]),
            row["_index"],
        )
    )
    for rank, row in enumerate(scored, start=1):
        row["rank"] = rank
        del row["_index"]
    return scored


def select_top_n(ranked, n):
    """Return the first n already-ranked applicants (the quota)."""
    return ranked[:max(0, int(n))]
