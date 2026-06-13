import matplotlib

matplotlib.use("Agg")

from fuzzy.plots import plot_membership


def test_plot_membership_backward_compatible():
    figure = plot_membership("IPK")
    assert figure is not None


def test_plot_membership_with_value_and_degrees():
    figure = plot_membership(
        "IPK",
        value=3.6,
        degrees={"Rendah": 0.0, "Sedang": 0.0, "Tinggi": 0.7},
    )
    assert figure is not None
    # The vertical input marker should be present as an extra line.
    plain = plot_membership("IPK")
    assert len(figure.axes[0].lines) > len(plain.axes[0].lines)
