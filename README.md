# Corporate Escaper — Rekomendasi Paket Trip

Aplikasi Streamlit untuk merekomendasikan paket trip (Mentawai, Gili, Nusa Penida)
berdasarkan budget, jumlah peserta (pax), dan preferensi lainnya, menggunakan model
klasifikasi (Random Forest).

## Menjalankan secara lokal

1. Install dependency:
   ```bash
   pip install -r requirements.txt
   ```
2. Pastikan file model berikut ada di root folder:
   - `model_rekomendasi_rf.pkl`
   - `nama_kelas_paket_rf.pkl`
   - `logo.png` (opsional)
3. Jalankan:
   ```bash
   streamlit run app.py
   ```
4. Buka `http://localhost:8501` di browser.

## Fitur

- Rekomendasi paket trip berbasis AI (Random Forest) sesuai destinasi, budget, dan pax
- Validasi real-time budget vs pax
- Loading skeleton saat memproses rekomendasi
- Perbandingan side-by-side antar paket
- Salin ringkasan paket ke clipboard untuk dibagikan
