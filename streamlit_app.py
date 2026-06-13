"""Sistem Seleksi Penerima Beasiswa - Metode Mamdani (Streamlit UI)."""

import io

import pandas as pd
import streamlit as st

from fuzzy.engine import INPUT_VARS, infer, load_rules
from fuzzy.plots import plot_aggregation, plot_membership
from fuzzy.ranking import rank_applicants, select_top_n
from fuzzy.report import build_pdf

st.set_page_config(page_title="Seleksi Beasiswa - Mamdani", layout="wide")
RULES = load_rules()

st.title("Sistem Seleksi Penerima Beasiswa (Metode Mamdani)")
mode = st.sidebar.radio("Mode", ["Satu Pelamar", "Batch Ranking"])

if mode == "Satu Pelamar":
    st.sidebar.header("Input Pelamar")
    nama = st.sidebar.text_input("Nama", "Pelamar")
    ipk = st.sidebar.slider("IPK", 0.0, 4.0, 3.0, 0.01)
    penghasilan = st.sidebar.slider(
        "Penghasilan (juta/bulan)",
        0.0,
        10.0,
        4.0,
        0.1,
    )
    tanggungan = st.sidebar.slider("Jumlah Tanggungan", 0, 6, 2, 1)
    prestasi = st.sidebar.slider(
        "Prestasi Non-Akademik",
        0.0,
        10.0,
        5.0,
        0.1,
    )

    trace = infer(
        {
            "IPK": ipk,
            "Penghasilan": penghasilan,
            "Tanggungan": float(tanggungan),
            "Prestasi": prestasi,
        },
        RULES,
    )

    column_score, column_label = st.columns(2)
    column_score.metric("Skor Prioritas", f"{trace.score:.2f}")
    column_label.metric("Label", trace.label)

    st.pyplot(plot_aggregation(trace))

    with st.expander("1. Input (setelah validasi & clamp)"):
        st.json(trace.inputs)
    with st.expander("2. Fuzzifikasi (derajat keanggotaan)"):
        st.dataframe(pd.DataFrame(trace.degrees).T)
    with st.expander("3-4. Rule menyala & alpha"):
        st.dataframe(
            pd.DataFrame(
                [
                    {"alpha": alpha, "output": consequent}
                    for alpha, consequent in sorted(
                        trace.fired,
                        key=lambda item: -item[0],
                    )
                ]
            )
        )
    with st.expander("5. Agregasi & 6. Defuzzifikasi"):
        st.write(
            f"Centroid score = **{trace.score:.2f}** -> **{trace.label}**"
        )
    with st.expander("Grafik membership input"):
        for var in INPUT_VARS:
            st.pyplot(plot_membership(var))

    pdf_bytes = build_pdf(trace, applicant_name=nama)
    st.download_button(
        "Unduh Laporan Perhitungan (PDF)",
        data=pdf_bytes,
        file_name=f"laporan_{nama}.pdf",
        mime="application/pdf",
    )

else:
    st.header("Batch Ranking")
    st.caption(
        "Unggah CSV dengan kolom: nama, ipk, penghasilan, tanggungan, prestasi"
    )
    uploaded = st.file_uploader("CSV pelamar", type="csv")
    quota = st.number_input("Kuota (top-N)", min_value=1, value=3, step=1)

    if uploaded is not None:
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
        selected_names = {
            row["nama"] for row in select_top_n(ranked, quota)
        }
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
        st.dataframe(table, use_container_width=True)
        csv_buffer = io.StringIO()
        table.to_csv(csv_buffer, index=False)
        st.download_button(
            "Unduh Hasil Ranking (CSV)",
            data=csv_buffer.getvalue(),
            file_name="hasil_ranking.csv",
            mime="text/csv",
        )
