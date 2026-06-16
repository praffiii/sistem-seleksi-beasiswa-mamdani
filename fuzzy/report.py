"""Generate the full per-applicant Mamdani calculation report as a PDF."""

import io
import struct

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

# Classic LaTeX look (Computer Modern) for every rasterized formula.
matplotlib.rcParams["mathtext.fontset"] = "cm"

# All math is rendered at one fixed font size and DPI, then placed at its
# natural size. This keeps every formula the SAME visual scale on the page.
MATH_FONTSIZE = 13
MATH_DPI = 220
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from fuzzy.derivation import build_defuzzification_derivation
from fuzzy.engine import INPUT_VARS, load_rules
from fuzzy.explain import mf_degree_latex
from fuzzy.membership import INPUT_SETS, OUTPUT_SETS
from fuzzy.plots import plot_aggregation, plot_membership

NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}
PAGE_WIDTH = 170
PLOT_HEIGHT = 85
VAR_UNITS = {
    "IPK": "",
    "Penghasilan": "juta/bulan",
    "Tanggungan": "orang",
    "Prestasi": "skor",
}
VERDICT = {
    "Tinggi": "prioritas kuat untuk menerima beasiswa.",
    "Sedang": "prioritas menengah; bergantung pada kuota.",
    "Rendah": "prioritas rendah.",
}


def _fig_to_png_bytes(fig):
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight",
        transparent=True,
    )
    buffer.seek(0)
    return buffer


def _safe_text(value):
    """Keep core-font PDF text valid even when a name contains Unicode."""
    return str(value).encode("latin-1", errors="replace").decode("latin-1")


def _num(value):
    return f"{value:g}"


def _ensure_space(pdf, height):
    if pdf.get_y() + height > pdf.h - pdf.b_margin:
        pdf.add_page()


def _heading(pdf, text, level=1):
    height = 9 if level == 1 else 7
    _ensure_space(pdf, height + 2)
    pdf.set_font("Helvetica", "B", 13 if level == 1 else 11)
    pdf.cell(0, height, _safe_text(text), **NEXT_LINE)


def _paragraph(pdf, text, height=5):
    pdf.set_font("Helvetica", "", 9)
    lines = max(1, len(str(text)) // 90 + 1)
    _ensure_space(pdf, lines * height + 1)
    pdf.multi_cell(0, height, _safe_text(text), **NEXT_LINE)


def _png_size(data):
    """Read (width, height) in pixels straight from a PNG's IHDR chunk."""
    return struct.unpack(">II", data[16:24])


def _math_image(latex):
    """Render one mathtext expression at a fixed font size; return PNG buffer."""
    with plt.rc_context({"text.usetex": False}):
        figure = plt.figure(figsize=(0.01, 0.01))
        figure.text(0, 0, f"${latex}$", fontsize=MATH_FONTSIZE, ha="left")
        buffer = io.BytesIO()
        figure.savefig(
            buffer,
            format="png",
            dpi=MATH_DPI,
            bbox_inches="tight",
            pad_inches=0.02,
            transparent=True,
        )
        plt.close(figure)
    buffer.seek(0)
    return buffer


def _add_math(pdf, latex):
    """Place a formula at its NATURAL size so every formula matches scale."""
    png = _math_image(latex)
    width_px, height_px = _png_size(png.getvalue())
    width = width_px / MATH_DPI * 25.4
    height = height_px / MATH_DPI * 25.4
    if width > PAGE_WIDTH:
        scale = PAGE_WIDTH / width
        width *= scale
        height *= scale
    _ensure_space(pdf, height + 2.5)
    png.seek(0)
    x = pdf.l_margin + 4
    y = pdf.get_y()
    pdf.image(png, x=x, y=y, w=width, h=height)
    pdf.set_y(y + height + 2.5)


def _add_plot(pdf, figure):
    png = _fig_to_png_bytes(figure)
    plt.close(figure)
    _ensure_space(pdf, PLOT_HEIGHT + 4)
    y = pdf.get_y()
    pdf.image(
        png,
        x=pdf.l_margin,
        y=y,
        w=PAGE_WIDTH,
        h=PLOT_HEIGHT,
    )
    pdf.set_y(y + PLOT_HEIGHT + 3)


def _render_defuzzification_table(pdf, trace):
    widths = [30, 44, 36, 25, 35]
    headers = ["Output set", "Shape", "z-range", "A", "M"]
    row_height = 6

    _ensure_space(pdf, row_height * (len(trace.regions) + 2) + 4)
    pdf.set_font("Helvetica", "B", 8)
    for header, width in zip(headers, widths):
        pdf.cell(width, row_height, _safe_text(header), border=1)
    pdf.ln(row_height)

    pdf.set_font("Helvetica", "", 8)
    for region in trace.regions:
        values = [
            region["output_label"],
            region["shape"],
            f"{region['z_start']:.2f}-{region['z_end']:.2f}",
            f"{region['A']:.2f}",
            f"{region['M']:.2f}",
        ]
        for value, width in zip(values, widths):
            pdf.cell(width, row_height, _safe_text(value), border=1)
        pdf.ln(row_height)

    total_area = sum(region["A"] for region in trace.regions)
    total_moment = sum(region["M"] for region in trace.regions)
    pdf.set_font("Helvetica", "B", 8)
    totals = ["Sum", "", "", f"{total_area:.2f}", f"{total_moment:.2f}"]
    for value, width in zip(totals, widths):
        pdf.cell(width, row_height, _safe_text(value), border=1)
    pdf.ln(row_height + 2)
    return total_area, total_moment


def _definition_branches(label, params):
    """Return mathtext-safe lines equivalent to mf_definition_latex()."""
    a, b, c, d = params
    prefix = rf"\mu_{{\mathrm{{{label}}}}}(x)"
    branches = []
    has_rising = a < b
    has_falling = c < d
    if has_rising:
        branches.append(rf"{prefix} = 0,\quad x \leq {_num(a)}")
        branches.append(
            rf"{prefix} = \frac{{x - {_num(a)}}}"
            rf"{{{_num(b)} - {_num(a)}}},\quad "
            rf"{_num(a)} < x \leq {_num(b)}"
        )
    if b < c:
        if c == d:
            branches.append(rf"{prefix} = 1,\quad x \geq {_num(b)}")
        else:
            branches.append(
                rf"{prefix} = 1,\quad {_num(b)} \leq x \leq {_num(c)}"
            )
    if c < d:
        branches.append(
            rf"{prefix} = \frac{{{_num(d)} - x}}"
            rf"{{{_num(d)} - {_num(c)}}},\quad "
            rf"{_num(c)} < x \leq {_num(d)}"
        )
        branches.append(rf"{prefix} = 0,\quad x > {_num(d)}")
    if has_rising and has_falling:
        branches = [
            rf"{prefix} = 0,\quad x \leq {_num(a)}\quad "
            rf"\mathrm{{atau}}\quad x > {_num(d)}"
        ] + branches[1:-1]
    return branches


def _render_summary(pdf, trace):
    _heading(pdf, "Ringkasan")
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0,
        9,
        f"Skor Prioritas: {trace.score:.2f}",
        **NEXT_LINE,
    )
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, f"Label: {_safe_text(trace.label)}", **NEXT_LINE)
    _paragraph(
        pdf,
        f"Skor {trace.score:.2f} -> {trace.label} - "
        f"{VERDICT.get(trace.label, '')}",
    )
    _paragraph(
        pdf,
        f"Aturan menyala: {len(trace.fired_detail)} dari "
        f"{len(load_rules())} rule.",
    )
    _add_math(
        pdf,
        r"\mathrm{Input}\rightarrow\mathrm{Fuzzifikasi}\rightarrow"
        r"\mathrm{Inferensi}\rightarrow\mathrm{Agregasi}\rightarrow"
        r"\mathrm{Defuzzifikasi}\rightarrow\mathrm{Skor}",
    )


def _render_fuzzification(pdf, trace):
    pdf.add_page()
    _heading(pdf, "1-2. Fuzzifikasi")
    _paragraph(
        pdf,
        "Setiap nilai input dipetakan ke derajat keanggotaan tiap "
        "himpunan fuzzy.",
    )

    for index, var in enumerate(INPUT_VARS):
        if index:
            pdf.add_page()
        value = trace.inputs[var]
        unit = VAR_UNITS[var]
        _heading(
            pdf,
            f"{var} = {value:g} {unit}".strip(),
            level=2,
        )
        _paragraph(pdf, "Definisi himpunan:")
        for label, params in INPUT_SETS[var].items():
            for branch in _definition_branches(label, params):
                _add_math(pdf, branch)

        _paragraph(pdf, "Hasil fuzzifikasi:")
        for label, params in INPUT_SETS[var].items():
            latex, _ = mf_degree_latex(label, params, value)
            _add_math(pdf, latex)

        _paragraph(pdf, "Plot keanggotaan:")
        _add_plot(
            pdf,
            plot_membership(
                var,
                value=value,
                degrees=trace.degrees[var],
            ),
        )


def _render_inference(pdf, trace):
    pdf.add_page()
    _heading(pdf, "3-4. Inferensi dan Implikasi")
    _paragraph(
        pdf,
        "alpha = MIN derajat keanggotaan keempat anteseden. Implikasi "
        "memotong himpunan output pada nilai alpha. Rule diurutkan dari "
        "alpha terbesar; ID rule sesuai rule base CSV.",
    )

    ordered = sorted(trace.fired_detail, key=lambda fired: -fired.alpha)
    for fired_rule in ordered:
        _ensure_space(pdf, 25)
        antecedent = " AND ".join(
            f"{var} {fired_rule.antecedent[var]}" for var in INPUT_VARS
        )
        label = f"{fired_rule.rule_id}: " if fired_rule.rule_id else ""
        _paragraph(
            pdf,
            f"{label}IF {antecedent} "
            f"THEN Prioritas {fired_rule.consequent}",
        )
        numbers = ", ".join(
            f"{fired_rule.degrees[var]:.2f}" for var in INPUT_VARS
        )
        _add_math(
            pdf,
            rf"\alpha = \min({numbers}) = {fired_rule.alpha:.2f}",
        )

    _heading(pdf, "Implikasi (tinggi potong tiap output)", level=2)
    for label, height in trace.clip_heights.items():
        _add_math(
            pdf,
            rf"\mathrm{{clip}}_{{\mathrm{{{label}}}}} = {height:.2f}",
        )


def _render_defuzzification(pdf, trace):
    derivation = build_defuzzification_derivation(trace)
    pdf.add_page()
    _heading(pdf, "5-6. Agregasi dan Defuzzifikasi")
    _paragraph(
        pdf,
        "Defuzzifikasi memakai Composite Moment. Setiap himpunan output "
        "terpotong dihitung terpisah, sehingga area yang saling tumpang "
        "tindih tetap ikut dihitung pada masing-masing himpunan.",
    )
    _add_plot(pdf, plot_aggregation(trace))

    _heading(pdf, "1. Komposisi MAX per output set", level=2)
    for composition in derivation["compositions"]:
        if not composition["active"]:
            _paragraph(
                pdf,
                f"{composition['label']}: mu = 0, tidak ada area fuzzy "
                "dan tidak ikut diperhitungkan dalam defuzzifikasi.",
            )
            continue
        _paragraph(
            pdf,
            f"{composition['label']}: " + ", ".join(composition["rules_text"]),
        )
        _add_math(pdf, composition["max_latex"])

    _heading(pdf, "2. Pencarian titik potong", level=2)
    for cut_group in derivation["cut_points"]:
        _paragraph(pdf, cut_group["label"])
        for edge in cut_group["edges"]:
            _paragraph(pdf, edge["edge_label"])
            _add_math(pdf, edge["expression_latex"])
            _add_math(pdf, edge["equation_latex"])

    _heading(pdf, "3. Fungsi hasil komposisi", level=2)
    for function_group in derivation["functions"]:
        _paragraph(pdf, function_group["label"])
        for line in function_group["lines"]:
            _add_math(pdf, line)

    _heading(pdf, "4. Daftar region defuzzifikasi", level=2)
    for region in derivation["regions"]:
        _paragraph(pdf, region["list_label"])

    _render_defuzzification_table(pdf, trace)

    _heading(pdf, "5. Momen tiap region", level=2)
    for region in derivation["regions"]:
        _paragraph(pdf, f"{region['moment']['symbol']} - {region['title']}")
        _add_math(pdf, region["moment"]["setup_latex"])
        _add_math(pdf, region["moment"]["antiderivative_latex"])
        _add_math(pdf, region["moment"]["upper_latex"])
        _add_math(pdf, region["moment"]["lower_latex"])
        _add_math(pdf, region["moment"]["result_latex"])

    _heading(pdf, "6. Luas tiap region", level=2)
    for region in derivation["regions"]:
        _add_math(pdf, region["area_latex"])

    _heading(pdf, "7. Nilai crisp", level=2)
    _add_math(pdf, derivation["moment_sum_latex"])
    _add_math(pdf, derivation["area_sum_latex"])
    _add_math(pdf, derivation["crisp_latex"])

    _heading(pdf, "Penentuan label", level=2)
    label_latex, _ = mf_degree_latex(
        trace.label,
        OUTPUT_SETS[trace.label],
        trace.score,
    )
    _add_math(pdf, label_latex)
    _paragraph(pdf, f"Label akhir: {trace.label}")


def build_pdf(trace, applicant_name="Pelamar"):
    """Render a complete Streamlit-equivalent walkthrough into PDF bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(20, 18, 20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0,
        10,
        "Sistem Seleksi Penerima Beasiswa",
        **NEXT_LINE,
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        6,
        "Laporan langkah demi langkah - Metode Mamdani",
        **NEXT_LINE,
    )
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0,
        8,
        f"Pelamar: {_safe_text(applicant_name)}",
        **NEXT_LINE,
    )
    pdf.ln(2)

    _render_summary(pdf, trace)
    _render_fuzzification(pdf, trace)
    _render_inference(pdf, trace)
    _render_defuzzification(pdf, trace)

    return bytes(pdf.output())
