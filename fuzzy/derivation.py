"""Shared defuzzification derivation builders for UI and PDF output."""

from fractions import Fraction

from fuzzy.membership import OUTPUT_SETS


SHAPE_LABELS = {
    "Rising triangle": "Segitiga naik",
    "Plateau rectangle": "Persegi panjang datar",
    "Falling triangle": "Segitiga turun",
}


def _num(value):
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"


def _alpha(value):
    return f"{value:.2f}"


def _label_latex(label):
    return rf"\mathrm{{{label}}}"


def _fraction_latex(value, variable):
    fraction = Fraction(value).limit_denominator(100000)
    numerator = fraction.numerator
    denominator = fraction.denominator
    sign = "-" if numerator < 0 else "+"
    numerator = abs(numerator)

    if denominator == 1:
        if numerator == 1:
            term = variable
        else:
            term = rf"{numerator}{variable}"
    elif numerator == 1:
        term = rf"\frac{{{variable}}}{{{denominator}}}"
    else:
        term = rf"\frac{{{numerator}{variable}}}{{{denominator}}}"
    return sign, term


def _polynomial_latex(coefficients):
    terms = []
    for power, coefficient in coefficients:
        variable = f"z^{power}"
        sign, term = _fraction_latex(coefficient, variable)
        terms.append((sign, term))
    if not terms:
        return "0"

    first_sign, first_term = terms[0]
    latex = f"-{first_term}" if first_sign == "-" else first_term
    for sign, term in terms[1:]:
        latex += rf" {sign} {term}"
    return latex


def _mu_latex(region):
    return region["mu_latex"]


def _edge_latex(kind, params, height, cut_point):
    a, b, c, d = params
    if kind == "rising":
        denominator = b - a
        expression = rf"\frac{{z - {_num(a)}}}{{{_num(denominator)}}}"
        edge_label = "sisi naik"
    else:
        denominator = d - c
        expression = rf"\frac{{{_num(d)} - z}}{{{_num(denominator)}}}"
        edge_label = "sisi turun"
    equation = rf"{expression} = {_alpha(height)} \Rightarrow z = {_num(cut_point)}"
    return {
        "edge": kind,
        "edge_label": edge_label,
        "expression_latex": expression,
        "equation_latex": equation,
        "z": cut_point,
    }


def _piecewise_lines(label, params, height):
    a, b, c, d = params
    z_left = a + height * (b - a)
    z_right = d - height * (d - c)
    prefix = rf"\mu_{{{_label_latex(label)}}}(z)"
    lines = []
    has_rising = a < b
    has_falling = c < d

    if has_rising:
        lines.append(rf"{prefix} = 0,\quad z \leq {_num(a)}")

    if has_rising:
        lines.append(
            rf"{prefix} = \frac{{z - {_num(a)}}}{{{_num(b - a)}}},\quad "
            rf"{_num(a)} < z \leq {_num(z_left)}"
        )
    if z_left < z_right:
        lines.append(
            rf"{prefix} = {_alpha(height)},\quad "
            rf"{_num(z_left)} < z \leq {_num(z_right)}"
        )
    if c < d:
        lines.append(
            rf"{prefix} = \frac{{{_num(d)} - z}}{{{_num(d - c)}}},\quad "
            rf"{_num(z_right)} < z \leq {_num(d)}"
        )
        lines.append(rf"{prefix} = 0,\quad z > {_num(d)}")
    if has_rising and has_falling:
        lines = [
            rf"{prefix} = 0,\quad z \leq {_num(a)}\quad "
            rf"\mathrm{{atau}}\quad z > {_num(d)}"
        ] + lines[1:-1]
    return lines


def _region_derivation(region, index):
    shape_label = SHAPE_LABELS[region["shape"]]
    title = (
        f"{shape_label} {region['output_label']} "
        f"z={_num(region['z_start'])}..{_num(region['z_end'])}"
    )
    antiderivative = _polynomial_latex(region["antiderivative_coefficients"])
    mu = _mu_latex(region)
    moment_symbol = f"M_{index}"
    area_symbol = f"A_{index}"
    area_symbol_plain = area_symbol.replace("_", "")
    list_label = (
        f"{area_symbol_plain} = {shape_label} {region['output_label']} "
        f"(z = {_num(region['z_start'])} hingga z = {_num(region['z_end'])})"
    )

    moment = {
        "symbol": moment_symbol,
        "setup_latex": (
            rf"{moment_symbol} = \int_{{{_num(region['z_start'])}}}"
            rf"^{{{_num(region['z_end'])}}} z \cdot {mu}\, dz"
        ),
        "antiderivative_latex": (
            rf"{moment_symbol} = \left[{antiderivative}\right]"
            rf"_{{{_num(region['z_start'])}}}^{{{_num(region['z_end'])}}}"
        ),
        "upper_eval": region["upper_eval"],
        "lower_eval": region["lower_eval"],
        "upper_latex": (
            rf"\mathrm{{Batas\ atas}}\ z={_num(region['z_end'])}: "
            rf"{antiderivative} = {_alpha(region['upper_eval'])}"
        ),
        "lower_latex": (
            rf"\mathrm{{Batas\ bawah}}\ z={_num(region['z_start'])}: "
            rf"{antiderivative} = {_alpha(region['lower_eval'])}"
        ),
        "result_latex": (
            rf"{moment_symbol} = {_alpha(region['upper_eval'])} - "
            rf"({_alpha(region['lower_eval'])}) = {_alpha(region['M'])}"
        ),
    }

    if region["area_formula"] == "triangle":
        area_latex = (
            rf"{area_symbol} = \frac{{1}}{{2}} \times {_num(region['base'])} "
            rf"\times {_alpha(region['height'])} = {_alpha(region['A'])}"
        )
    else:
        area_latex = (
            rf"{area_symbol} = {_num(region['base'])} \times "
            rf"{_alpha(region['height'])} = {_alpha(region['A'])}"
        )

    return {
        "index": index,
        "title": title,
        "list_label": list_label,
        "shape_label": shape_label,
        "area_symbol": area_symbol,
        "moment": moment,
        "area_latex": area_latex,
        "region": region,
    }


def build_defuzzification_derivation(trace):
    """Build display-ready Composite Moment derivation from a trace."""
    compositions = []
    cut_points = []
    functions = []

    for label, params in OUTPUT_SETS.items():
        rules = [
            fired_rule
            for fired_rule in trace.fired_detail
            if fired_rule.consequent == label
        ]
        height = trace.clip_heights.get(label, 0.0)
        alphas = [fired_rule.alpha for fired_rule in rules]
        rules_text = [
            f"{fired_rule.rule_id or 'Rule'} ({_alpha(fired_rule.alpha)})"
            for fired_rule in rules
        ]
        max_latex = (
            rf"\mathrm{{{label}}}: \max("
            + ", ".join(_alpha(alpha) for alpha in alphas)
            + rf") = {_alpha(height)}"
            if alphas
            else rf"\mathrm{{{label}}}: \mu = 0"
        )
        compositions.append(
            {
                "label": label,
                "height": height,
                "alphas": alphas,
                "rules_text": rules_text,
                "max_latex": max_latex,
                "active": height > 0.0,
            }
        )
        if height <= 0.0:
            continue

        a, b, c, d = params
        z_left = a + height * (b - a)
        z_right = d - height * (d - c)
        label_cuts = {"label": label, "height": height, "edges": []}
        if a < b:
            label_cuts["edges"].append(_edge_latex("rising", params, height, z_left))
        if c < d:
            label_cuts["edges"].append(_edge_latex("falling", params, height, z_right))
        cut_points.append(label_cuts)
        functions.append(
            {
                "label": label,
                "lines": _piecewise_lines(label, params, height),
            }
        )

    regions = [
        _region_derivation(region, index)
        for index, region in enumerate(trace.regions, start=1)
    ]
    total_area = sum(region["A"] for region in trace.regions)
    total_moment = sum(region["M"] for region in trace.regions)
    return {
        "compositions": compositions,
        "cut_points": cut_points,
        "functions": functions,
        "regions": regions,
        "total_area": total_area,
        "total_moment": total_moment,
        "moment_sum_latex": (
            r"\sum M = "
            + " + ".join(_alpha(region["M"]) for region in trace.regions)
            + rf" = {_alpha(total_moment)}"
        ),
        "area_sum_latex": (
            r"\sum A = "
            + " + ".join(_alpha(region["A"]) for region in trace.regions)
            + rf" = {_alpha(total_area)}"
        ),
        "crisp_latex": (
            rf"Z = \frac{{\sum M}}{{\sum A}} = "
            rf"\frac{{{_alpha(total_moment)}}}{{{_alpha(total_area)}}} "
            rf"= {_alpha(trace.score)}"
        ),
    }
