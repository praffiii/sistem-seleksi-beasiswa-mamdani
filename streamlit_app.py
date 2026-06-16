"""Sistem Seleksi Penerima Beasiswa - Metode Mamdani (Streamlit UI)."""

import io

import pandas as pd
import streamlit as st

from fuzzy.engine import INPUT_VARS, infer, load_rules
from fuzzy.derivation import build_defuzzification_derivation
from fuzzy.explain import mf_definition_latex, mf_degree_latex
from fuzzy.membership import INPUT_SETS, OUTPUT_SETS
from fuzzy.plots import plot_aggregation, plot_membership
from fuzzy.ranking import rank_applicants, select_top_n
from fuzzy.report import build_pdf

st.set_page_config(page_title="Seleksi Beasiswa - Mamdani", layout="wide")
RULES = load_rules()

# Accessible label styling: light tint background + dark same-hue ink.
# Verified WCAG AA contrast: Rendah 5.72:1, Sedang 5.40:1, Tinggi 4.82:1.
# (White text on saturated fills failed: 2.87 / 1.83 / 3.35 — do not use.)
LABEL_STYLE = {
    "Rendah": {"bg": "#fdecea", "ink": "#b3261e"},
    "Sedang": {"bg": "#fff3e0", "ink": "#8a5a00"},
    "Tinggi": {"bg": "#e7f6ea", "ink": "#1f7a33"},
}
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


def render_header():
    st.title("Sistem Seleksi Penerima Beasiswa")
    st.caption(
        "Metode Mamdani — fuzzifikasi, inferensi, dan defuzzifikasi "
        "ditampilkan langkah demi langkah."
    )


def render_hero(trace):
    style = LABEL_STYLE.get(trace.label, {"bg": "#eeeeee", "ink": "#333333"})
    col_score, col_label, col_gauge = st.columns([1, 1, 2])
    col_score.metric("Skor Prioritas", f"{trace.score:.2f}")
    col_label.markdown(
        "<div style='margin-top:8px'>Label<br>"
        f"<span style='background:{style['bg']};color:{style['ink']};"
        f"border:1px solid {style['ink']};padding:4px 14px;border-radius:14px;"
        "font-size:20px;font-weight:700'>"
        f"{trace.label}</span></div>",
        unsafe_allow_html=True,
    )
    fraction = min(max(trace.score / 100.0, 0.0), 1.0)
    col_gauge.progress(fraction, text=f"{trace.score:.0f} / 100")


def render_summary(trace):
    st.markdown(
        "**Alur:** Input → Fuzzifikasi → Inferensi → Agregasi "
        "→ Defuzzifikasi → Skor"
    )
    st.write(
        f"Skor **{trace.score:.2f}** → **{trace.label}** — "
        f"{VERDICT.get(trace.label, '')}"
    )
    st.write(
        f"Aturan menyala: **{len(trace.fired_detail)}** dari "
        f"{len(RULES)} rule."
    )


def render_fuzzification(trace):
    st.caption(
        "Setiap nilai input dipetakan ke derajat keanggotaan tiap "
        "himpunan fuzzy."
    )
    for var in INPUT_VARS:
        x = trace.inputs[var]
        unit = VAR_UNITS[var]
        st.subheader(f"{var} = {x:g} {unit}".strip())
        st.pyplot(plot_membership(var, value=x, degrees=trace.degrees[var]))
        col_definition, col_degree = st.columns(2)
        with col_definition:
            st.markdown("**Definisi himpunan:**")
            for label, params in INPUT_SETS[var].items():
                st.latex(mf_definition_latex(label, params))
        with col_degree:
            st.markdown("**Hasil fuzzifikasi:**")
            for label, params in INPUT_SETS[var].items():
                latex, _ = mf_degree_latex(label, params, x)
                st.latex(latex)
        st.divider()


def _render_one_rule(fired_rule):
    antecedent = " AND ".join(
        f"{var} {fired_rule.antecedent[var]}" for var in INPUT_VARS
    )
    prefix = f"**{fired_rule.rule_id}** — " if fired_rule.rule_id else ""
    st.markdown(
        f"{prefix}**IF** {antecedent} **THEN** Prioritas {fired_rule.consequent}"
    )
    numbers = ", ".join(f"{fired_rule.degrees[var]:.2f}" for var in INPUT_VARS)
    st.latex(rf"\alpha = \min({numbers}) = {fired_rule.alpha:.2f}")
    st.markdown("---")


def render_inference(trace):
    st.caption(
        "α = MIN derajat keanggotaan keempat anteseden. Implikasi memotong "
        "himpunan output pada nilai α. Rule diurutkan dari α terbesar; "
        "ID rule sesuai rule base CSV."
    )
    ordered = sorted(trace.fired_detail, key=lambda fr: -fr.alpha)
    for fired_rule in ordered:
        _render_one_rule(fired_rule)
    st.markdown("**Implikasi (tinggi potong tiap output):**")
    for label, height in trace.clip_heights.items():
        st.latex(rf"\text{{clip}}_{{\text{{{label}}}}} = {height:.2f}")


def render_defuzzification(trace):
    derivation = build_defuzzification_derivation(trace)
    st.caption(
        "Defuzzifikasi memakai Composite Moment: tiap himpunan output "
        "terpotong dihitung terpisah, termasuk area yang saling tumpang tindih."
    )
    st.pyplot(plot_aggregation(trace))

    st.subheader("1. Komposisi MAX per output set")
    for composition in derivation["compositions"]:
        if not composition["active"]:
            st.markdown(
                f"**{composition['label']}**: μ = 0, tidak ada area fuzzy "
                "dan tidak ikut diperhitungkan dalam defuzzifikasi."
            )
            continue
        st.markdown(
            f"**{composition['label']}**: "
            + ", ".join(composition["rules_text"])
        )
        st.latex(composition["max_latex"])

    st.subheader("2. Pencarian titik potong")
    for cut_group in derivation["cut_points"]:
        with st.expander(cut_group["label"], expanded=True):
            for edge in cut_group["edges"]:
                st.markdown(f"**{edge['edge_label']}**")
                st.latex(edge["expression_latex"])
                st.latex(edge["equation_latex"])

    st.subheader("3. Fungsi hasil komposisi")
    for function_group in derivation["functions"]:
        with st.expander(function_group["label"], expanded=True):
            for line in function_group["lines"]:
                st.latex(line)

    st.subheader("4. Daftar region defuzzifikasi")
    for region in derivation["regions"]:
        st.markdown(region["list_label"])

    rows = [
        {
            "Output set": region["output_label"],
            "Shape": region["shape"],
            "z-range": f"{region['z_start']:.2f}-{region['z_end']:.2f}",
            "A": region["A"],
            "M": region["M"],
        }
        for region in trace.regions
    ]
    total_area = sum(region["A"] for region in trace.regions)
    total_moment = sum(region["M"] for region in trace.regions)
    rows.append(
        {
            "Output set": "Σ",
            "Shape": "",
            "z-range": "",
            "A": total_area,
            "M": total_moment,
        }
    )
    st.dataframe(
        pd.DataFrame(rows).style.format({"A": "{:.2f}", "M": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("5. Momen tiap region")
    for region in derivation["regions"]:
        with st.expander(
            f"{region['moment']['symbol']} - {region['title']}",
            expanded=True,
        ):
            st.latex(region["moment"]["setup_latex"])
            st.latex(region["moment"]["antiderivative_latex"])
            st.latex(region["moment"]["upper_latex"])
            st.latex(region["moment"]["lower_latex"])
            st.latex(region["moment"]["result_latex"])

    st.subheader("6. Luas tiap region")
    for region in derivation["regions"]:
        st.latex(region["area_latex"])

    st.subheader("7. Nilai crisp")
    st.latex(derivation["moment_sum_latex"])
    st.latex(derivation["area_sum_latex"])
    st.latex(derivation["crisp_latex"])
    st.markdown("**Penentuan label:**")
    label_latex, _ = mf_degree_latex(
        trace.label, OUTPUT_SETS[trace.label], trace.score
    )
    st.latex(label_latex)
    st.write(f"Label akhir: **{trace.label}**")


def render_walkthrough(trace):
    tab_summary, tab_fuzz, tab_inference, tab_defuzz = st.tabs(
        [
            "Ringkasan",
            "1·2 Fuzzifikasi",
            "3·4 Inferensi",
            "5·6 Defuzzifikasi",
        ]
    )
    with tab_summary:
        render_summary(trace)
    with tab_fuzz:
        render_fuzzification(trace)
    with tab_inference:
        render_inference(trace)
    with tab_defuzz:
        render_defuzzification(trace)


def render_single_applicant():
    with st.container(border=True):
        st.markdown("**Input Pelamar**")
        nama = st.text_input("Nama", "Pelamar")
        row_top = st.columns(2)
        ipk = row_top[0].slider("IPK", 0.0, 4.0, 3.0, 0.01)
        penghasilan = row_top[1].slider(
            "Penghasilan (juta/bln)", 0.0, 10.0, 4.0, 0.1
        )
        row_bottom = st.columns(2)
        tanggungan = row_bottom[0].slider("Tanggungan", 0, 6, 2, 1)
        prestasi = row_bottom[1].slider("Prestasi", 0.0, 10.0, 5.0, 0.1)

    trace = infer(
        {
            "IPK": ipk,
            "Penghasilan": penghasilan,
            "Tanggungan": float(tanggungan),
            "Prestasi": prestasi,
        },
        RULES,
    )
    render_hero(trace)
    render_walkthrough(trace)
    st.download_button(
        "Unduh Laporan Perhitungan (PDF)",
        data=build_pdf(trace, applicant_name=nama),
        file_name=f"laporan_{nama}.pdf",
        mime="application/pdf",
    )


def render_batch():
    st.markdown("**Seleksi Batch**")
    st.caption(
        "Unggah CSV dengan kolom: nama, ipk, penghasilan, tanggungan, prestasi"
    )
    col_upload, col_quota = st.columns([2, 1])
    uploaded = col_upload.file_uploader("CSV pelamar", type="csv")
    quota = col_quota.number_input("Kuota (top-N)", min_value=1, value=3, step=1)

    if uploaded is None:
        return

    dataframe = pd.read_csv(uploaded)
    applicants = [
        {
            "nama": row["nama"],
            "IPK": row["ipk"],
            "Penghasilan": row["penghasilan"],
            "Tanggungan": row["tanggungan"],
            "Prestasi": row["prestasi"],
        }
        for _, row in dataframe.iterrows()
    ]
    ranked = rank_applicants(applicants, RULES)
    selected_names = {row["nama"] for row in select_top_n(ranked, quota)}
    table = pd.DataFrame(
        [
            {
                "Rank": row["rank"],
                "Nama": row["nama"],
                "Skor": round(row["score"], 2),
                "Label": row["label"],
                "Lolos": row["nama"] in selected_names,
            }
            for row in ranked
        ]
    )

    def highlight_passing(row):
        tint = "background-color: #e8f5e9" if row["Lolos"] else ""
        return [tint] * len(row)

    st.dataframe(
        table.style.apply(highlight_passing, axis=1),
        use_container_width=True,
    )

    csv_buffer = io.StringIO()
    table.to_csv(csv_buffer, index=False)
    st.download_button(
        "Unduh Hasil Ranking (CSV)",
        data=csv_buffer.getvalue(),
        file_name="hasil_ranking.csv",
        mime="text/csv",
    )

    st.divider()
    st.markdown("**Lihat perhitungan langkah demi langkah:**")
    names = [row["nama"] for row in ranked]
    chosen = st.selectbox("Pilih pelamar", names)
    chosen_row = next(row for row in ranked if row["nama"] == chosen)
    trace = infer(
        {
            "IPK": chosen_row["IPK"],
            "Penghasilan": chosen_row["Penghasilan"],
            "Tanggungan": float(chosen_row["Tanggungan"]),
            "Prestasi": chosen_row["Prestasi"],
        },
        RULES,
    )
    render_hero(trace)
    render_walkthrough(trace)


render_header()
mode = st.radio(
    "Mode",
    ["Analisis Satu Pelamar", "Seleksi Batch"],
    horizontal=True,
    label_visibility="collapsed",
)
st.divider()

if mode == "Analisis Satu Pelamar":
    render_single_applicant()
else:
    render_batch()
