"""Show-your-work LaTeX builders for the Mamdani walkthrough UI.

Pure string helpers. Given membership-function params (a, b, c, d) and a crisp
input x, they return LaTeX whose active branch mirrors fuzzy.membership.trapmf
exactly, so the displayed formula always matches the numeric degree.
"""

from fuzzy.membership import trapmf


def _num(value):
    """Format a number for LaTeX without trailing zeros (2.0 -> '2')."""
    return f"{value:g}"


def mf_degree_latex(label, params, x):
    """LaTeX for one membership degree with numbers plugged in.

    Returns (latex_string, numeric_value). The branch chosen here follows the
    exact if-ladder order of trapmf, so value == trapmf(x, params).
    """
    a, b, c, d = params
    value = trapmf(x, params)
    if x < a:
        body = "0"
    elif x < b:
        body = (
            rf"\frac{{{_num(x)} - {_num(a)}}}{{{_num(b)} - {_num(a)}}} "
            rf"= {value:.2f}"
        )
    elif x <= c:
        body = "1"
    elif x < d:
        body = (
            rf"\frac{{{_num(d)} - {_num(x)}}}{{{_num(d)} - {_num(c)}}} "
            rf"= {value:.2f}"
        )
    else:
        body = "0"
    latex = rf"\mu_{{\text{{{label}}}}}({_num(x)}) = {body}"
    return latex, value


def mf_definition_latex(label, params):
    """Full piecewise definition of one fuzzy set as a LaTeX cases block."""
    a, b, c, d = params
    rows = []
    if a < b:
        rows.append(
            (
                rf"\frac{{x - {_num(a)}}}{{{_num(b)} - {_num(a)}}}",
                rf"{_num(a)} < x < {_num(b)}",
            )
        )
    rows.append(("1", rf"{_num(b)} \le x \le {_num(c)}"))
    if c < d:
        rows.append(
            (
                rf"\frac{{{_num(d)} - x}}{{{_num(d)} - {_num(c)}}}",
                rf"{_num(c)} < x < {_num(d)}",
            )
        )
    rows.append(("0", r"\text{lainnya}"))
    body = r" \\ ".join(rf"{expr} & {cond}" for expr, cond in rows)
    return rf"\mu_{{\text{{{label}}}}}(x) = \begin{{cases}} {body} \end{{cases}}"
