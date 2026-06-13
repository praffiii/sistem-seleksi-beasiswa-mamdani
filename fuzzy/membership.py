"""Fuzzy membership functions and locked parameters for the scholarship model.

Every fuzzy set is a trapezoid (a, b, c, d). A triangle is the special case
b == c (single-point peak). Parameters are read directly from the assignment's
membership-function graphs.
"""


def trapmf(x, params):
    """Trapezoidal membership degree of x in [0, 1].

    params = (a, b, c, d) with a <= b <= c <= d.
    Left shoulder: a == b. Right shoulder: c == d. Triangle: b == c.
    """
    a, b, c, d = params
    if x < a:
        return 0.0
    if x < b:                       # rising edge (b > a guaranteed here)
        return (x - a) / (b - a)
    if x <= c:                      # plateau (covers triangle peak when b == c)
        return 1.0
    if x < d:                       # falling edge (d > c guaranteed here)
        return (d - x) / (d - c)
    return 0.0


DOMAINS = {
    "IPK": (0.0, 4.0),
    "Penghasilan": (0.0, 10.0),
    "Tanggungan": (0.0, 6.0),
    "Prestasi": (0.0, 10.0),
    "Prioritas": (0.0, 100.0),
}

INPUT_SETS = {
    "IPK": {
        "Rendah": (0.0, 0.0, 2.0, 2.75),
        "Sedang": (2.0, 2.75, 2.75, 3.5),
        "Tinggi": (2.75, 3.5, 4.0, 4.0),
    },
    "Penghasilan": {
        "Rendah": (0.0, 0.0, 2.0, 5.0),
        "Sedang": (2.0, 5.0, 5.0, 8.0),
        "Tinggi": (5.0, 8.0, 10.0, 10.0),
    },
    "Tanggungan": {
        "Rendah": (0.0, 0.0, 1.0, 3.0),
        "Sedang": (1.0, 3.0, 3.0, 5.0),
        "Tinggi": (3.0, 5.0, 6.0, 6.0),
    },
    "Prestasi": {
        "Rendah": (0.0, 0.0, 3.0, 6.0),
        "Sedang": (3.0, 6.0, 6.0, 9.0),
        "Tinggi": (6.0, 9.0, 10.0, 10.0),
    },
}

OUTPUT_SETS = {
    "Rendah": (0.0, 0.0, 20.0, 40.0),
    "Sedang": (20.0, 50.0, 50.0, 80.0),
    "Tinggi": (60.0, 80.0, 100.0, 100.0),
}
