"""Mamdani inference engine for scholarship priority scoring."""

from fuzzy.membership import DOMAINS, INPUT_SETS, trapmf

INPUT_VARS = ("IPK", "Penghasilan", "Tanggungan", "Prestasi")

# Variables whose upper bound is a hard impossibility rather than a fuzzy cap.
HARD_UPPER = {"IPK"}


def validate_and_clamp(inputs):
    """Validate raw inputs and return a new dict clamped to fuzzy domains."""
    validated = {}
    for var in INPUT_VARS:
        if var not in inputs:
            raise ValueError(f"Missing input: {var}")

        value = float(inputs[var])
        lo, hi = DOMAINS[var]
        if value < lo:
            raise ValueError(f"{var}={value} below minimum {lo}")
        if value > hi:
            if var in HARD_UPPER:
                raise ValueError(f"{var}={value} above maximum {hi}")
            value = hi

        validated[var] = value

    return validated


def fuzzify(inputs):
    """Map crisp inputs to membership degrees for every input fuzzy set."""
    validated = validate_and_clamp(inputs)
    return {
        var: {
            label: trapmf(validated[var], params)
            for label, params in INPUT_SETS[var].items()
        }
        for var in INPUT_VARS
    }
