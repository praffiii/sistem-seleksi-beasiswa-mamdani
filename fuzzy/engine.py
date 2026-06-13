"""Mamdani inference engine for scholarship priority scoring."""

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fuzzy.membership import DOMAINS, INPUT_SETS, OUTPUT_SETS, trapmf

INPUT_VARS = ("IPK", "Penghasilan", "Tanggungan", "Prestasi")
OUTPUT_LO, OUTPUT_HI = DOMAINS["Prioritas"]
STEP = 0.1

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


@dataclass
class Trace:
    inputs: dict
    degrees: dict
    fired: list
    clip_heights: dict
    xs: list
    agg: list
    score: float
    label: str


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


def _clip_heights(fired):
    """Max firing strength per output label after aggregation."""
    heights = {label: 0.0 for label in OUTPUT_SETS}
    for alpha, consequent in fired:
        if alpha > heights[consequent]:
            heights[consequent] = alpha
    return heights


def _aggregate(xs, clip_heights):
    """Aggregate output memberships using MIN implication and MAX."""
    agg = []
    for x in xs:
        value = 0.0
        for label, params in OUTPUT_SETS.items():
            clipped = min(clip_heights[label], trapmf(x, params))
            if clipped > value:
                value = clipped
        agg.append(value)
    return agg


def _centroid(xs, agg):
    xs_array = np.asarray(xs)
    agg_array = np.asarray(agg)
    denominator = agg_array.sum()
    if denominator == 0.0:
        return float((OUTPUT_LO + OUTPUT_HI) / 2.0)
    return float((xs_array * agg_array).sum() / denominator)


def output_label(score):
    """Return the output set with highest membership at the crisp score."""
    best_label, best_degree = "Rendah", -1.0
    for label, params in OUTPUT_SETS.items():
        degree = trapmf(score, params)
        if degree > best_degree:
            best_label, best_degree = label, degree
    return best_label


def infer(inputs, rules=None):
    """Run the full Mamdani pipeline for one applicant."""
    if rules is None:
        rules = load_rules()
    clamped = validate_and_clamp(inputs)
    degrees = fuzzify(clamped)
    fired = evaluate_rules(degrees, rules)
    clip_heights = _clip_heights(fired)
    xs = [
        round(OUTPUT_LO + index * STEP, 4)
        for index in range(int((OUTPUT_HI - OUTPUT_LO) / STEP) + 1)
    ]
    agg = _aggregate(xs, clip_heights)
    score = _centroid(xs, agg)
    return Trace(
        inputs=clamped,
        degrees=degrees,
        fired=fired,
        clip_heights=clip_heights,
        xs=xs,
        agg=agg,
        score=score,
        label=output_label(score),
    )
