import joblib
import streamlit as st
import pandas as pd
import numpy as np

# =====================================================================
# 1. SETTING HALAMAN & LOAD MODEL RANDOM FOREST
# =====================================================================
st.set_page_config(page_title="Corporate Escaper RecSys", layout="centered")

@st.cache_resource
def load_rf_model():
    # Mengambil file model Random Forest dan list nama paketnya
    model = joblib.load("model_rekomendasi_rf.pkl")
    classes = joblib.load("nama_kelas_paket_rf.pkl")
    return model, classes

try:
    # SOLUSI ERROR: Kita pecah isi tuple-nya ke dua variabel berbeda (model dan classes)
    model_rf, classes_rf = load_rf_model()
except Exception as e:
    st.error("Gagal memuat model AI. Pastikan file 'model_rekomendasi_rf.pkl' dan 'nama_kelas_paket_rf.pkl' ada di folder yang sama.")

# =====================================================================
# 2. UI UTAMA (INPUT BERSIH & SIMPEL)
# =====================================================================
# Dropdown Utama Destinasi
destinasi = st.selectbox("Mau liburan ke mana?", ["All", "Gili", "Mentawai", "Nusa Penida"])

# Input Universal Tanpa Dropdown Tambahan yang Membingungkan
budget = st.number_input("Masukkan Total Budget Kelompok Anda (IDR)", min_value=100000, value=24000000, step=100000)
pax = st.number_input("Jumlah Peserta (Pax)", min_value=1, value=10)

# Input Dokumentasi Drone
drone = st.radio("Butuh dokumentasi Drone?", ["Yes", "No"])
drone_user = 1 if drone == "Yes" else 0

# Tampilkan informasi durasi pelengkap di UI berdasarkan destinasi secara rapi
if destinasi == "Mentawai":
    durasi = st.selectbox("Durasi Trip (Satuan: Hari)", ["3 Hari 2 Malam", "Fleksibel"])
    titik_kumpul = st.selectbox("Titik Keberangkatan", ["Mentawai", "Padang", "Pekanbaru"])
elif destinasi in ["Gili", "Nusa Penida"]:
    if destinasi == "Nusa Penida":
        durasi = st.selectbox("Durasi Trip (Satuan: Jam)", ["4 Jam Snorkeling Trip"])
    else:
        durasi = st.selectbox("Durasi Trip (Satuan: Jam)", ["1 Jam", "2 Jam", "4 Jam", "All Day (12 Jam)"])
    titik_kumpul = "Lokal"
else: # All
    durasi = st.selectbox("Durasi Trip (Satuan: Jam/Hari)", ["Fleksibel Jam / Hari", "3 Hari 2 Malam", "4 Jam"])
    titik_kumpul = st.selectbox("Titik Keberangkatan (Khusus Mentawai)", ["Fleksibel (Tanpa Tambahan)", "Padang", "Pekanbaru"])

# Set list destinasi target untuk looping di backend
if destinasi == "All":
    destinasi_final_list = ["Mentawai", "Gili", "Nusa Penida"]
else:
    destinasi_final_list = [destinasi]

st.markdown("<br>", unsafe_allow_html=True)

# =====================================================================
# 3. PROSES PREDIKSI & VALIDASI ATURAN BISNIS DI BACKEND
# =====================================================================
if st.button("Cari Rekomendasi Paket Terbaik 🚀", use_container_width=True):
    dict_predictions = {}
    
    for dest_item in destinasi_final_list:
        
        # --- MAPPING ONE-HOT ENCODING UNTUK RANDOM FOREST ---
        # Mengonversi teks destinasi menjadi flag binary 0 dan 1 agar dibaca seragam oleh RF
        dest_gili = 1 if dest_item.lower() == "gili" else 0
        dest_mentawai = 1 if dest_item.lower() == "mentawai" else 0
        dest_nusa_penida = 1 if dest_item.lower() == "nusa penida" else 0
        
        # Buat DataFrame awal dengan susunan kolom rill sesuai data training Random Forest kemarin
        input_raw = pd.DataFrame([{
            'pax': pax, 
            'total_price': budget, 
            'add_drone': drone_user, 
            'price_per_pax': budget / pax,
            'dest_gili': dest_gili, 
            'dest_mentawai': dest_mentawai, 
            'dest_nusa penida': dest_nusa_penida
        }])
        
        # Ambil probabilitas awal dari Random Forest menggunakan variable model hasil un-boxing tuple
        probabilitas = model_rf.predict_proba(input_raw)[0]
        nama_paket = classes_rf
        
        for paket, skor in zip(nama_paket, probabilitas):
            paket_original_name = str(paket).strip()
            paket_clean = paket_original_name.lower()
            
            # Variabel penampung detail tipe paket dan catatan biaya tambahan rill
            tipe_detail_paket = "Standar Paket"
            catatan_tambahan = []
            
            # --- 1. TENTUKAN LOKASI ASLI PAKET ---
            if "mentawai" in paket_clean or "private trip" in paket_clean:
                lokasi_asli_paket = "Mentawai"
            elif paket_original_name in ["Paddle Board", "Kayaking", "Horse Riding", "Snorkeling Gili"]:
                lokasi_asli_paket = "Gili"
            elif "nusa penida" in paket_clean or "package" in paket_clean:
                lokasi_asli_paket = "Nusa Penida"
            else:
                lokasi_asli_paket = dest_item
            
            # --- 2. VALIDASI OTOMATIS BIAYA TRANSPORTASI MENTAWAI ---
            biaya_transportasi = 0
            if lokasi_asli_paket == "Mentawai":
                if "padang" in titik_kumpul.lower(): 
                    biaya_transportasi = 600000
                    catatan_tambahan.append(f"Tiket Keberangkatan Padang: Rp{biaya_transportasi:,} / pax")
                elif "pekanbaru" in titik_kumpul.lower(): 
                    biaya_transportasi = 1050000
                    catatan_tambahan.append(f"Tiket Keberangkatan Pekanbaru: Rp{biaya_transportasi:,} / pax")

            # --- 3. SIMULASI AUTOMATION VALIDASI SELURUH PAKET ---
            is_valid_budget = True
            biaya_drone_paket = 0
            
            # A. Simulasi Validasi Aturan Paket Gili
            if lokasi_asli_paket == "Gili":
                
                # Skenario Kayaking
                if paket_original_name == "Kayaking":
                    if drone_user == 1:
                        biaya_drone_paket = 150000
                        catatan_tambahan.append(f"Dokumentasi Drone (Tarif Lokal): Rp{biaya_drone_paket:,} / grup")
                    budget_bersih_paket = budget - biaya_drone_paket
                    
                    if "all day" in durasi.lower():
                        if budget_bersih_paket >= (550000 * pax):
                            tipe_detail_paket = "All Day (Tipe Perahu: Double)"
                        elif budget_bersih_paket >= 500000:
                            tipe_detail_paket = "All Day (Tipe Perahu: Single)"
                        else:
                            is_valid_budget = False
                    else:
                        tipe_detail_paket = f"{durasi} Trip"
                        if budget_bersih_paket < 100000: is_valid_budget = False
                        
                # Skenario Paddle Board
                elif paket_original_name == "Paddle Board":
                    if drone_user == 1:
                        biaya_drone_paket = 150000
                        catatan_tambahan.append(f"Dokumentasi Drone (Tarif Lokal): Rp{biaya_drone_paket:,} / grup")
                    budget_bersih_paket = budget - biaya_drone_paket
                    tipe_detail_paket = f"{durasi} Trip"
                    if budget_bersih_paket < 100000: is_valid_budget = False
                    
                # Skenario Snorkeling Gili
                elif paket_original_name == "Snorkeling Gili":
                    budget_bersih_paket = budget
                    if drone_user == 1:
                        catatan_tambahan.append("Dokumentasi Drone: GRATIS / Include GoPro")
                    
                    harga_private_per_pax = 9999999
                    if pax == 2: harga_private_per_pax = 550000
                    elif 3 <= pax <= 4: harga_private_per_pax = 450000
                    elif 5 <= pax <= 6: harga_private_per_pax = 350000
                    elif 7 <= pax <= 8: harga_private_per_pax = 300000
                    elif pax >= 9: harga_private_per_pax = 250000
                    
                    if budget_bersih_paket >= (harga_private_per_pax * pax) and pax >= 2:
                        tipe_detail_paket = f"Private Snorkeling (Tarif Berjenjang: Rp{harga_private_per_pax:,}/pax)"
                    elif budget_bersih_paket >= (150000 * pax):
                        tipe_detail_paket = "Public Snorkeling Trip (Rp150k/pax)"
                    else:
                        is_valid_budget = False
                        
                # Skenario Horse Riding
                elif paket_original_name == "Horse Riding":
                    budget_bersih_paket = budget
                    if drone_user == 1:
                        catatan_tambahan.append("Dokumentasi Drone: Tidak tersedia untuk Horse Riding")
                    
                    if budget_bersih_paket >= (450000 * pax):
                        tipe_detail_paket = "Peak Season - Durasi 60 Menit"
                    elif budget_bersih_paket >= (400000 * pax):
                        tipe_detail_paket = "Normal Season - Durasi 60 Menit"
                    elif budget_bersih_paket >= (300000 * pax):
                        tipe_detail_paket = "Peak Season - Durasi 30 Menit"
                    elif budget_bersih_paket >= (250000 * pax):
                        tipe_detail_paket = "Normal Season - Durasi 30 Menit"
                    else:
                        is_valid_budget = False
            
            # B. Simulasi Validasi Aturan Paket Selain Gili (Mentawai & Nusa Penida)
            else:
                if drone_user == 1 and lokasi_asli_paket == "Mentawai":
                    biaya_drone_paket = 300000
                    catatan_tambahan.append(f"Biaya Tambahan Dokumentasi Drone: Rp{biaya_drone_paket:,}")
                
                budget_bersih_paket = budget - (biaya_transportasi * pax) - biaya_drone_paket
                price_per_pax_bersih = budget_bersih_paket / pax
                
                if budget_bersih_paket <= 0:
                    is_valid_budget = False
                    
                # Aturan Validasi Nusa Penida
                if lokasi_asli_paket == "Nusa Penida":
                    if drone_user == 1:
                        catatan_tambahan.append("Dokumentasi Drone: GRATIS / Sudah Include")
                    if price_per_pax_bersih >= 1350000:
                        tipe_detail_paket = "Paket 2 Eksklusif (Rp1.350k/person)"
                    elif price_per_pax_bersih >= 800000:
                        tipe_detail_paket = "Paket 1 Standar (Rp800k/person)"
                    else:
                        is_valid_budget = False
                        
                # Aturan Validasi Mentawai
                if lokasi_asli_paket == "Mentawai":
                    price_per_pax_gross = budget / pax  # Gunakan budget kotor untuk cek Family Gathering
                    if price_per_pax_bersih < 1800000:
                        is_valid_budget = False
                    else:
                        # Family Gathering dicek dari budget kotor (harga 2.4jt/pax sudah all-in termasuk transport)
                        if pax >= 10 and price_per_pax_gross >= 2400000:
                            tipe_detail_paket = "Family Gathering Rombongan Besar"
                        elif pax >= 2:
                            tipe_detail_paket = f"Mentawai Private Trip ({pax} Pax)"
                        elif pax == 1:
                            tipe_detail_paket = "Mentawai Open Trip (Solo Traveler)"

            # --- 4. PREDIKSI UTK RE-CALCULATE OLEH RANDOM FOREST ---
            if is_valid_budget:
                price_per_pax_bersih = budget_bersih_paket / pax
                
                # Setup dummy pasca kalkulasi operasional backend
                fixed_gili = 1 if lokasi_asli_paket.lower() == "gili" else 0
                fixed_mentawai = 1 if lokasi_asli_paket.lower() == "mentawai" else 0
                fixed_nusa_penida = 1 if lokasi_asli_paket.lower() == "nusa penida" else 0
                
                input_user_fixed = pd.DataFrame([{
                    'pax': pax,
                    'total_price': budget_bersih_paket,
                    'add_drone': drone_user,
                    'price_per_pax': price_per_pax_bersih,
                    'dest_gili': fixed_gili,
                    'dest_mentawai': fixed_mentawai,
                    'dest_nusa penida': fixed_nusa_penida
                }])
                
                idx_paket = list(classes_rf).index(paket)
                skor_fixed = model_rf.predict_proba(input_user_fixed)[0][idx_paket]
                
                # --- OVERRIDE NAMA STRUKTUR UTAMA MENTAWAI ---
                if lokasi_asli_paket == "Mentawai":
                    price_per_pax_gross = budget / pax
                    if pax >= 10 and price_per_pax_gross >= 2400000:
                        if "private" in paket_clean:
                            paket_original_name = "Family Gathering"
                            skor_fixed = 0.99
                    elif pax >= 2:
                        if "private" in paket_clean:
                            paket_original_name = "Mentawai Private Trip"
                            skor_fixed = max(skor_fixed, 0.95)
                    elif pax == 1:
                        if "open" in paket_clean:
                            paket_original_name = "Mentawai Open Trip"
                            skor_fixed = 0.99
                        elif "private" in paket_clean:
                            skor_fixed = 0.00
                
                # --- JIKA LOLOS FILTER DROP-DOWN UTAMA, SIMPAN KE HASIL ---
                lolos_filter = False
                if destinasi == "All":
                    lolos_filter = True
                elif destinasi == lokasi_asli_paket:
                    lolos_filter = True
                    
                if lolos_filter:
                    nama_gabungan_hasil = f"{paket_original_name} — Tipe: {tipe_detail_paket}"
                    dict_predictions[nama_gabungan_hasil] = (skor_fixed, lokasi_asli_paket, catatan_tambahan)

    # Susun ranking berdasarkan kecocokan probabilitas tertinggi
    hasil_urut = sorted(dict_predictions.items(), key=lambda x: x[1][0], reverse=True)
    
    # Tampilkan Hasil ke Layar User
    if len(hasil_urut) > 0:
        st.success(f"### Hasil Analisis Rekomendasi Pintar (Random Forest):")
        st.write(f"Berikut adalah Top-3 paket terdekat yang paling sesuai dengan budget dan kriteria kelompok Anda:")
        
        for i, (paket_info, (skor, loc, rincian_notes)) in enumerate(hasil_urut[:3], 1):
            with st.container(border=True):
                st.write(f"**{i}. {paket_info} ({loc})**")
                st.progress(float(skor))
                st.write(f"Tingkat Kecocokan AI: `{skor * 100:.2f}%`")
                
                # --- BERI RINCIAN NOTIFIKASI BIAYA TAMBAHAN DI SINI ---
                if rincian_notes:
                    st.markdown("<p style='margin-bottom: -5px; font-weight: bold; font-size: 13px; color: #555;'>📋 Rincian Kalkulasi Tambahan:</p>", unsafe_allow_html=True)
                    for note in rincian_notes:
                        st.markdown(f"<p style='margin: 0px; font-size: 13px; color: #666;'>• {note}</p>", unsafe_allow_html=True)
    else:
        st.error("❌ **Budget Tidak Mencukupi!** Setelah dihitung otomatis oleh sistem di latar belakang, budget Anda tidak mencukupi untuk mengambil paket apa pun di destinasi ini. Silakan coba naikkan nominal budget Anda.")