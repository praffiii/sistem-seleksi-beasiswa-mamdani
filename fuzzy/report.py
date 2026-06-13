"""Generate a per-applicant PDF calculation report (six Mamdani steps)."""

import io

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from fuzzy.plots import plot_aggregation

INPUT_VARS = ("IPK", "Penghasilan", "Tanggungan", "Prestasi")
NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _fig_to_png_bytes(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    return buffer


def build_pdf(trace, applicant_name="Pelamar"):
    """Render the trace into PDF bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Laporan Perhitungan Prioritas Beasiswa", **NEXT_LINE)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Pelamar: {applicant_name}", **NEXT_LINE)
    pdf.ln(2)

    # Step 1: inputs
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Input (setelah validasi & clamp)", **NEXT_LINE)
    pdf.set_font("Helvetica", "", 10)
    for var in INPUT_VARS:
        pdf.cell(0, 6, f"   {var}: {trace.inputs[var]}", **NEXT_LINE)

    # Step 2: fuzzification
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Fuzzifikasi (derajat keanggotaan)", **NEXT_LINE)
    pdf.set_font("Helvetica", "", 10)
    for var in INPUT_VARS:
        parts = ", ".join(
            f"{label}={degree:.3f}"
            for label, degree in trace.degrees[var].items()
        )
        pdf.cell(0, 6, f"   {var}: {parts}", **NEXT_LINE)

    # Step 3-4: fired rules with alpha
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "3-4. Rule menyala & implikasi (alpha)", **NEXT_LINE)
    pdf.set_font("Helvetica", "", 10)
    for alpha, consequent in sorted(trace.fired, key=lambda item: -item[0]):
        pdf.cell(
            0,
            6,
            f"   alpha={alpha:.3f} -> {consequent}",
            **NEXT_LINE,
        )

    # Step 5: aggregation plot
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "5. Agregasi (area output)", **NEXT_LINE)
    figure = plot_aggregation(trace)
    png = _fig_to_png_bytes(figure)
    pdf.image(png, w=150)

    # Step 6: defuzzification result
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "6. Defuzzifikasi (centroid)", **NEXT_LINE)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"   Skor Prioritas: {trace.score:.2f}", **NEXT_LINE)
    pdf.cell(0, 7, f"   Label: {trace.label}", **NEXT_LINE)

    output = pdf.output()
    return bytes(output)
