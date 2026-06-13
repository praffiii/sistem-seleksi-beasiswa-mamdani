"""Mamdani inference engine for scholarship priority scoring."""

import csv
from dataclasses import dataclass
from pathlib import Path

from fuzzy.membership import DOMAINS, INPUT_SETS, trapmf

INPUT_VARS = ("IPK", "Penghasilan", "Tanggungan", "Prestasi")

DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "rulebase_beasiswa_81_rules.csv"
)

# CSV header label -> internal variable name.
_CSV_COLUMNS = {
    "IPK": "IPK",
    "Penghasilan Orang Tua": "Penghasilan",
    "Jumlah Tanggungan": "Tanggungan",
    "Prestasi Non-Akademik": "Prestasi",
}
_CSV_OUTPUT_COLUMN = "Prioritas Beasiswa"

# Variables whose upper bound is a hard impossibility rather than a fuzzy cap.
HARD_UPPER = {"IPK"}


@dataclass(frozen=True)
class Rule:
    antecedent: dict
    consequent: str


def load_rules(path=DEFAULT_RULES_PATH):
    """Read the rule base CSV into a list of Rule objects."""
    rules = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            antecedent = {
                var: row[column].strip()
                for column, var in _CSV_COLUMNS.items()
            }
            consequent = row[_CSV_OUTPUT_COLUMN].strip()
            rules.append(Rule(antecedent=antecedent, consequent=consequent))
    return rules


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


def evaluate_rules(degrees, rules):
    """Return [(alpha, consequent_label)] for every rule with alpha > 0.

    alpha = MIN of the four antecedent membership degrees (AND = MIN).
    """
    fired = []
    for rule in rules:
        alpha = min(
            degrees[var][label]
            for var, label in rule.antecedent.items()
        )
        if alpha > 0.0:
            fired.append((alpha, rule.consequent))
    return fired
