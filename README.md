# Sistem Seleksi Penerima Beasiswa — Metode Mamdani

Sistem pendukung keputusan untuk seleksi awal penerima beasiswa secara objektif
menggunakan **Fuzzy Inference System (FIS) metode Mamdani**. Sistem menampilkan
seluruh proses perhitungan langkah demi langkah — fuzzifikasi, inferensi, agregasi,
hingga defuzzifikasi — lewat antarmuka web interaktif (Streamlit) dan dapat
mengekspor laporan perhitungan ke PDF.

---

## Variabel

### Input

| Variabel | Domain | Himpunan Fuzzy | Satuan |
| --- | --- | --- | --- |
| **IPK** | 0 – 4 | Rendah, Sedang, Tinggi | — |
| **Penghasilan Orang Tua** | 0 – 10 | Rendah, Sedang, Tinggi | juta/bulan |
| **Jumlah Tanggungan** | 0 – 6 | Rendah, Sedang, Tinggi | orang |
| **Prestasi Non-Akademik** | 0 – 10 | Rendah, Sedang, Tinggi | skor |

### Output

| Variabel | Domain | Himpunan Fuzzy |
| --- | --- | --- |
| **Prioritas Beasiswa** | 0 – 100 | Rendah, Sedang, Tinggi |

Seluruh fungsi keanggotaan berbentuk **trapesium** `(a, b, c, d)`; bentuk segitiga
adalah kasus khusus saat `b == c`. Parameter lengkap ada di
[`fuzzy/membership.py`](fuzzy/membership.py).

---

## Metode Mamdani (6 Langkah)

1. **Fuzzifikasi** — nilai crisp tiap input dipetakan ke derajat keanggotaan pada
   setiap himpunan fuzzy (`trapmf`).
2. **Evaluasi rule** — operator **AND = MIN** dari keempat anteseden menghasilkan
   nilai `α` (firing strength) tiap rule.
3. **Implikasi** — himpunan output dipotong (*clipping*) pada nilai `α`
   menggunakan **MIN**.
4. **Komposisi** — tiap label output (Rendah / Sedang / Tinggi) mengambil `α`
   tertinggi (**MAX**) dari semua rule yang menghasilkannya.
5. **Defuzzifikasi** — metode **Composite Moment** `Z = ΣM / ΣA`: setiap
   himpunan output terpotong didekomposisi menjadi bangun geometris (segitiga
   naik, plateau, segitiga turun); luas `A` dan momen `M` dihitung **analitik**
   (bukan sampling). Area yang saling tumpang tindih antar himpunan dihitung
   terpisah per himpunan.
6. **Penentuan label** — skor akhir dipetakan ke label dengan keanggotaan
   tertinggi (Rendah / Sedang / Tinggi).

---

## Rule Base

Rule base terdiri dari **81 rule** (kombinasi penuh 4 variabel × 3 himpunan = 3⁴),
tersimpan di [`data/rulebase_beasiswa_81_rules.csv`](data/rulebase_beasiswa_81_rules.csv).

Bobot dirancang **seimbang** — keempat variabel memberi pengaruh setara terhadap
output. Tiap label diberi skor `0/1/2`, dijumlahkan (rentang 0–8), lalu dipetakan:

- **Penghasilan di-invert** (income rendah = lebih membutuhkan = skor tinggi),
  sedangkan IPK, Tanggungan, dan Prestasi searah (semakin tinggi semakin
  prioritas).
- Total `≤ 2` → **Rendah**, `3–5` → **Sedang**, `6–8` → **Tinggi**.

Contoh rule:

- **IF** IPK Tinggi **AND** Penghasilan Rendah **AND** Tanggungan Tinggi **AND**
  Prestasi Tinggi **THEN** Prioritas Tinggi
- **IF** IPK Rendah **AND** Penghasilan Tinggi **AND** Tanggungan Rendah **AND**
  Prestasi Rendah **THEN** Prioritas Rendah

---

## Struktur Proyek

```
sistem-seleksi-penerima-beasiswa-mamdani/
├── streamlit_app.py          # Antarmuka web (UI)
├── requirements.txt
├── data/
│   ├── rulebase_beasiswa_81_rules.csv   # 81 rule fuzzy
│   └── sample_applicants.csv            # contoh data batch
├── fuzzy/
│   ├── membership.py         # fungsi keanggotaan & parameter
│   ├── engine.py             # mesin inferensi Mamdani
│   ├── ranking.py            # perangkingan & seleksi top-N (mode batch)
│   ├── explain.py            # builder rumus LaTeX (show-your-work)
│   ├── derivation.py         # penjabaran defuzzifikasi Composite Moment
│   ├── plots.py              # grafik membership & himpunan output terpotong
│   └── report.py             # ekspor laporan PDF
└── tests/                    # unit test (pytest)
```

---

## Instalasi

Disarankan menggunakan virtual environment.

```bash
# (opsional) buat & aktifkan venv
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# install dependency
pip install -r requirements.txt
```

Dependency utama: `streamlit`, `numpy`, `matplotlib`, `fpdf2`, `pandas`.

---

## Menjalankan Aplikasi

```bash
streamlit run streamlit_app.py
```

Aplikasi akan terbuka di browser (default `http://localhost:8501`).

### Mode Aplikasi

1. **Analisis Satu Pelamar** — atur IPK, penghasilan, tanggungan, dan prestasi
   lewat slider. Sistem menampilkan skor, label, serta perhitungan lengkap per
   langkah (fuzzifikasi, inferensi, defuzzifikasi) dan tombol **Unduh Laporan
   Perhitungan (PDF)**.
2. **Seleksi Batch** — unggah CSV berisi banyak pelamar, sistem merangking dan
   menyeleksi top-N sesuai kuota, lalu hasil dapat diunduh sebagai CSV.

Format CSV untuk mode batch (lihat contoh `data/sample_applicants.csv`):

```csv
nama,ipk,penghasilan,tanggungan,prestasi
Andi,3.8,2.0,4,8
Budi,2.4,6.5,1,3
```

---

## Laporan PDF

Laporan PDF mereplikasi tampilan walkthrough web secara lengkap: definisi
himpunan, rumus fuzzifikasi, rule yang menyala beserta `α`, plot keanggotaan,
plot tiap himpunan output terpotong, dan penjabaran **Composite Moment** lengkap
(komposisi MAX, pencarian titik potong, integral momen tiap region, rumus luas,
hingga `ΣM / ΣA`) — seluruh rumus dirender sebagai gambar (mathtext/Computer
Modern) dengan skala seragam.

---

## Pengujian

```bash
python3 -m pytest -q
```

Mencakup unit test untuk fungsi keanggotaan, mesin inferensi, perangkingan,
builder rumus, dan pembuatan laporan PDF.

---

## Catatan

- Input divalidasi dan di-*clamp* ke domain masing-masing variabel. IPK di atas
  batas dianggap tidak valid (error), variabel lain di-*clamp* ke nilai maksimum.
- Bila tidak ada rule yang menyala (kasus ekstrem), skor default jatuh ke titik
  tengah domain output (50).
