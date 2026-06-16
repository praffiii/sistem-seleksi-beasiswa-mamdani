"""Mamdani inference engine for scholarship priority scoring."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

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
_CSV_ID_COLUMN = "Rule"

# Variables whose upper bound is a hard impossibility rather than a fuzzy cap.
HARD_UPPER = {"IPK"}


@dataclass(frozen=True)
class Rule:
    antecedent: dict
    consequent: str
    rule_id: str = ""    # original ID from the CSV (e.g. "R52")


@dataclass(frozen=True)
class FiredRule:
    alpha: float
    consequent: str
    antecedent: dict     # {var: label}
    degrees: dict        # {var: membership degree used for this rule}
    rule_id: str = ""    # original ID from the CSV (e.g. "R52")


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
    regions: list = field(default_factory=list)
    fired_detail: list = field(default_factory=list)


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
            rule_id = row.get(_CSV_ID_COLUMN, "").strip()
            rules.append(
                Rule(
                    antecedent=antecedent,
                    consequent=consequent,
                    rule_id=rule_id,
                )
            )
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


def evaluate_rules_detailed(degrees, rules):
    """Like evaluate_rules but keep each rule's antecedent and degrees.

    Returns [FiredRule] for every rule with alpha > 0, in rule-file order.
    """
    fired = []
    for rule in rules:
        member = {
            var: degrees[var][label]
            for var, label in rule.antecedent.items()
        }
        alpha = min(member.values())
        if alpha > 0.0:
            fired.append(
                FiredRule(
                    alpha=alpha,
                    consequent=rule.consequent,
                    antecedent=dict(rule.antecedent),
                    degrees=member,
                    rule_id=rule.rule_id,
                )
            )
    return fired


def _clip_heights(fired):
    """Max firing strength per output label after aggregation."""
    heights = {label: 0.0 for label in OUTPUT_SETS}
    for alpha, consequent in fired:
        if alpha > heights[consequent]:
            heights[consequent] = alpha
    return heights


def _format_num(value):
    return f"{value:.2f}"


def _compact_num(value):
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return _format_num(value)


def _poly_eval(coefficients, z):
    return sum(coefficient * z ** power for power, coefficient in coefficients)


def _antiderivative_text(coefficients):
    terms = []
    for power, coefficient in coefficients:
        if abs(coefficient) < 1e-12:
            continue
        sign = "-" if coefficient < 0 else "+"
        absolute = abs(coefficient)
        if power == 2:
            term = f"{_format_num(absolute)}z^2"
        elif power == 3:
            term = f"{_format_num(absolute)}z^3"
        else:
            term = f"{_format_num(absolute)}z^{power}"
        terms.append((sign, term))
    if not terms:
        return "0"
    first_sign, first_term = terms[0]
    text = f"-{first_term}" if first_sign == "-" else first_term
    for sign, term in terms[1:]:
        text += f" {sign} {term}"
    return text


def _region_formula_details(mu_text, coefficients, z_start, z_end):
    upper = _poly_eval(coefficients, z_end)
    lower = _poly_eval(coefficients, z_start)
    return {
        "mu_text": mu_text,
        "antiderivative_coefficients": coefficients,
        "antiderivative_text": _antiderivative_text(coefficients),
        "upper_eval": upper,
        "lower_eval": lower,
    }


def _triangle_region(
    output_label_name,
    shape,
    z_start,
    z_end,
    height,
    moment,
    mu_text,
    mu_latex,
    coefficients,
):
    area = 0.5 * (z_end - z_start) * height
    region = {
        "output_label": output_label_name,
        "shape": shape,
        "z_start": z_start,
        "z_end": z_end,
        "A": area,
        "M": moment,
        "area_formula": "triangle",
        "base": z_end - z_start,
        "height": height,
        "mu_latex": mu_latex,
    }
    region.update(_region_formula_details(mu_text, coefficients, z_start, z_end))
    return region


def _rectangle_region(output_label_name, z_start, z_end, height):
    area = (z_end - z_start) * height
    moment = height * (z_end ** 2 - z_start ** 2) / 2.0
    coefficients = [(2, height / 2.0)]
    region = {
        "output_label": output_label_name,
        "shape": "Plateau rectangle",
        "z_start": z_start,
        "z_end": z_end,
        "A": area,
        "M": moment,
        "area_formula": "rectangle",
        "base": z_end - z_start,
        "height": height,
    }
    region.update(
        _region_formula_details(
            _format_num(height),
            coefficients,
            z_start,
            z_end,
        )
    )
    region["mu_latex"] = _format_num(height)
    return region


def _composite_moment(clip_heights):
    """Return crisp score and independent clipped output sub-regions.

    Composite Moment integrates every clipped output set independently, so
    overlaps intentionally contribute once per fired output label.
    """
    regions = []
    for output_label_name, height in clip_heights.items():
        if height <= 0.0:
            continue

        a, b, c, d = OUTPUT_SETS[output_label_name]
        z_left = a + height * (b - a)
        z_right = d - height * (d - c)

        if a < b:
            denominator = b - a
            coefficients = [
                (3, 1.0 / (3.0 * denominator)),
                (2, -a / (2.0 * denominator)),
            ]
            moment = (
                (z_left ** 3 / 3.0 - a * z_left ** 2 / 2.0)
                - (a ** 3 / 3.0 - a * a ** 2 / 2.0)
            ) / denominator
            regions.append(
                _triangle_region(
                    output_label_name,
                    "Rising triangle",
                    a,
                    z_left,
                    height,
                    moment,
                    f"(z - {_format_num(a)}) / {_format_num(denominator)}",
                    rf"\frac{{z - {_compact_num(a)}}}{{{_compact_num(denominator)}}}",
                    coefficients,
                )
            )

        if z_left < z_right:
            regions.append(
                _rectangle_region(
                    output_label_name,
                    z_left,
                    z_right,
                    height,
                )
            )

        if c < d:
            denominator = d - c
            coefficients = [
                (2, d / (2.0 * denominator)),
                (3, -1.0 / (3.0 * denominator)),
            ]
            moment = (
                (d * d ** 2 / 2.0 - d ** 3 / 3.0)
                - (d * z_right ** 2 / 2.0 - z_right ** 3 / 3.0)
            ) / denominator
            regions.append(
                _triangle_region(
                    output_label_name,
                    "Falling triangle",
                    z_right,
                    d,
                    height,
                    moment,
                    f"({_format_num(d)} - z) / {_format_num(denominator)}",
                    rf"\frac{{{_compact_num(d)} - z}}{{{_compact_num(denominator)}}}",
                    coefficients,
                )
            )

    total_area = sum(region["A"] for region in regions)
    if total_area == 0.0:
        return float((OUTPUT_LO + OUTPUT_HI) / 2.0), regions
    total_moment = sum(region["M"] for region in regions)
    return float(total_moment / total_area), regions


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
    fired_detail = evaluate_rules_detailed(degrees, rules)
    fired = [(fr.alpha, fr.consequent) for fr in fired_detail]
    clip_heights = _clip_heights(fired)
    xs = [
        round(OUTPUT_LO + index * STEP, 4)
        for index in range(int((OUTPUT_HI - OUTPUT_LO) / STEP) + 1)
    ]
    score, regions = _composite_moment(clip_heights)
    return Trace(
        inputs=clamped,
        degrees=degrees,
        fired=fired,
        clip_heights=clip_heights,
        xs=xs,
        agg=[],
        score=score,
        label=output_label(score),
        regions=regions,
        fired_detail=fired_detail,
    )
