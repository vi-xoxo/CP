import joblib
import streamlit as st
import pandas as pd
import base64
import json
import time

# =====================================================================
# 0. HELPER
# =====================================================================
def get_image_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

logo_base64 = get_image_base64("logo.png")

def estimate_min_harga_pax(destinasi, pax):
    """Estimasi kasar harga/pax termurah yang tersedia untuk destinasi & jumlah
    peserta tertentu — dipakai untuk peringatan real-time Budget vs Pax."""
    if destinasi == "Mentawai":
        if pax >= 7:
            return 1800000
        elif pax >= 5:
            return 2000000
        elif pax >= 3:
            return 2300000
        else:
            return 3000000
    elif destinasi == "Nusa Penida":
        return 800000
    elif destinasi == "Gili":
        return 100000
    else:  # "All"
        return 100000

def render_skeleton_cards(n=2):
    """Skeleton placeholder cards shown briefly while rekomendasi sedang diproses,
    supaya user tahu sistem sedang bekerja, bukan hang."""
    st.markdown(
        '<div class="loading-caption"><span class="loading-dot"></span>'
        'Menyusun paket rekomendasi terbaik untuk Anda...</div>',
        unsafe_allow_html=True
    )
    for _ in range(n):
        st.markdown("""
        <div class="skeleton-card">
            <div class="sk-line w30"></div>
            <div class="sk-line w50"></div>
            <div class="sk-line w70"></div>
            <div class="sk-bar"></div>
            <div class="sk-line w40"></div>
        </div>
        """, unsafe_allow_html=True)

def render_notes_accordion(title, rows):
    """Render the 'catatan minimal pax' box as a collapsible accordion
    (closed by default) so it doesn't take up too much space on small screens."""
    rows_html = "".join([f'<div class="notes-row">{r}</div>' for r in rows])
    st.markdown(f"""
    <details class="notes-box">
        <summary class="notes-title">{title}<span class="notes-chevron">&#9662;</span></summary>
        <div class="notes-body">{rows_html}</div>
    </details>
    """, unsafe_allow_html=True)

def render_compare_table(entries):
    """Render perbandingan side-by-side untuk 2 paket terpilih."""
    a, b = entries[0], entries[1]

    def notes_html(n):
        if not n:
            return "<span style='color:var(--muted);'>—</span>"
        return "<ul>" + "".join([f"<li>{x}</li>" for x in n]) + "</ul>"

    best_a = "cmp-best" if a['pct'] >= b['pct'] else ""
    best_b = "cmp-best" if b['pct'] >= a['pct'] else ""
    st.markdown(f"""
    <div class="cmp-section">
        <div class="slabel" style="margin-top:6px;">Perbandingan Side-by-Side</div>
        <div class="cmp-table-scroll">
        <table class="cmp-table">
            <tr><th class="cmp-label">Paket</th>
                <td class="cmp-pkg-name {best_a}">{a['nama']}</td>
                <td class="cmp-pkg-name {best_b}">{b['nama']}</td></tr>
            <tr><th class="cmp-label">Lokasi</th>
                <td class="{best_a}"><span class="cmp-loc-tag">{a['lok']}</span></td>
                <td class="{best_b}"><span class="cmp-loc-tag">{b['lok']}</span></td></tr>
            <tr><th class="cmp-label">Tipe Paket</th>
                <td class="{best_a}">{a['tipe']}</td>
                <td class="{best_b}">{b['tipe']}</td></tr>
            <tr><th class="cmp-label">Kecocokan AI</th>
                <td class="{best_a}"><span class="cmp-score">{a['pct']:.1f}%</span></td>
                <td class="{best_b}"><span class="cmp-score">{b['pct']:.1f}%</span></td></tr>
            <tr><th class="cmp-label">Estimasi Total</th>
                <td class="{best_a}">Rp{a['total']:,}</td>
                <td class="{best_b}">Rp{b['total']:,}</td></tr>
            <tr><th class="cmp-label">Rincian</th>
                <td class="{best_a}">{notes_html(a['notes'])}</td>
                <td class="{best_b}">{notes_html(b['notes'])}</td></tr>
        </table>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.set_page_config(layout="wide")  # Gunakan layout wide dulu

st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 1. PAGE CONFIG (hanya dipanggil SEKALI di paling atas)
# =====================================================================
st.set_page_config(layout="wide", page_title="Corporate Escaper")

# =====================================================================
# 2. CSS GLOBAL
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary:      #113431;
    --primary-soft: #1b4d48;
    --accent:       #EAA93E;
    --accent-soft:  #f4c876;
    --dark:         #1E1E1E;
    --light:        #F4F7F6;
    --white:        #ffffff;
    --border:       #D8E6E3;
    --muted:        #6B8480;
    --text-soft:    #44605c;
    --radius-sm:    8px;
    --radius-md:    14px;
    --radius-lg:    20px;
    --shadow-sm:    0 2px 10px rgba(17,52,49,.06);
    --shadow-md:    0 10px 28px rgba(17,52,49,.10);
}

* { box-sizing: border-box; }

/* ── Sembunyikan elemen bawaan Streamlit ── */
#MainMenu, footer, header { visibility: hidden; }
header[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
}

/* ── Reset semua padding container Streamlit ── */
.stApp { background: #ffffff !important; margin-top: 0 !important; padding: 0 !important; }
div[data-testid="stAppViewContainer"]      { padding-top: 0 !important; padding-bottom: 0 !important; }
div[data-testid="stAppViewBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
section.main { padding: 0 !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }

/* ── BODY WRAPPER (padding hanya di sini, bukan di block-container) ── */
.body-wrapper {
    padding: 28px 40px;
}

/* ── section label ── */
.slabel {
    font-family: 'Inter', sans-serif;
    font-size: 9px; font-weight: 700;
    letter-spacing: 2.5px; text-transform: uppercase;
    color: var(--muted);
    margin: 0 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* ══════════════════════════════════════════════
   FORCE LIGHT MODE — tidak terpengaruh dark mode
   ══════════════════════════════════════════════ */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
section.main, .main .block-container,
section[data-testid="column"] > div {
    color-scheme: light only !important;
    forced-color-adjust: none !important;
}
@media (prefers-color-scheme: dark) {
    html, body { background: #ffffff !important; color: #1E1E1E !important; }
    .stApp { background: #ffffff !important; }
}

/* ── widget overrides ── */
div[data-testid="stSelectbox"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stRadio"] > label {
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important; font-weight: 700 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    color: #113431 !important;
}

/* ── Selectbox: latar putih, teks hitam, ikon dropdown hitam ── */
div[data-testid="stSelectbox"] > div > div {
    border: 1.5px solid #c2d6d2 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    color: #1E1E1E !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}
div[data-testid="stSelectbox"] > div > div > div,
div[data-testid="stSelectbox"] span,
div[data-testid="stSelectbox"] p {
    color: #1E1E1E !important;
}
/* ikon chevron/dropdown → hitam */
div[data-testid="stSelectbox"] svg {
    fill: #1E1E1E !important;
    color: #1E1E1E !important;
    stroke: #1E1E1E !important;
}

/* ── Text Input budget: latar putih, teks hitam ── */
/* Hilangkan border ganda bawaan BaseWeb (wrapper) agar tidak muncul
   "border tebal" di setiap sudut — hanya input asli yang punya border */
div[data-testid="stTextInput"] > div,
div[data-testid="stTextInput"] > div > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
div[data-testid="stTextInput"] > div > div > input {
    border: 1.5px solid #c2d6d2 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    color: #1E1E1E !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    -webkit-text-fill-color: #1E1E1E !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #113431 !important;
    box-shadow: none !important;
    outline: none !important;
}
div[data-testid="stTextInput"] > div > div > input::placeholder {
    color: #9ab5b1 !important;
    -webkit-text-fill-color: #9ab5b1 !important;
}

/* ── Number Input (pax): latar putih, teks hitam ── */
div[data-testid="stNumberInput"] > div,
div[data-testid="stNumberInput"] > div > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
div[data-testid="stNumberInput"] input {
    border: 1.5px solid #c2d6d2 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    color: #1E1E1E !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    -webkit-text-fill-color: #1E1E1E !important;
    box-shadow: none !important;
}
div[data-testid="stNumberInput"] input:focus {
    border-color: #113431 !important;
    box-shadow: none !important;
    outline: none !important;
}
/* Tombol +/- pax: tanpa border, hanya ikon berwarna ── */
div[data-testid="stNumberInput"] button {
    display: flex !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #113431 !important;
    border-radius: 8px !important;
}
div[data-testid="stNumberInput"] button svg {
    fill: #113431 !important;
    color: #113431 !important;
    stroke: #113431 !important;
}
div[data-testid="stNumberInput"] button:hover {
    background: #e8f0ee !important;
    border: none !important;
}
div[data-testid="stNumberInput"] button:hover svg {
    fill: #113431 !important;
    color: #113431 !important;
    stroke: #113431 !important;
}
div[data-testid="stNumberInput"] button:focus {
    outline: none !important;
    box-shadow: none !important;
}

div[data-testid="stRadio"] > div label p,
div[data-testid="stRadio"] > div label span {
    color: #113431 !important;
}
div[data-testid="stRadio"] > div { gap: 10px !important; flex-wrap: wrap; }
div[data-testid="stRadio"] > div label {
    background: #ffffff !important;
    border: 1.5px solid #c2d6d2 !important;
    border-radius: 10px !important;
    padding: 9px 16px !important;
    font-size: 12px !important;
}
div[data-testid="stRadio"] > div label:has(input:checked) {
    border-color: #113431 !important;
    background: #113431 !important;
    color: #ffffff !important;
}
div[data-testid="stRadio"] > div label:has(input:checked) p,
div[data-testid="stRadio"] > div label:has(input:checked) span {
    color: #ffffff !important;
}

/* ── CTA button ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #113431 0%, #1b4d48 100%) !important;
    color: #fff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important; font-weight: 700 !important;
    letter-spacing: 1.2px !important; text-transform: uppercase !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    height: auto !important;
    width: 100% !important;
    margin-top: 8px !important;
}

/* ── Back to Home button ── */
.home-btn-wrapper {
    margin-bottom: 20px;
}
.home-btn-wrapper a {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: transparent;
    border: 1.5px solid #113431;
    color: #113431 !important;
    font-family: 'Inter', sans-serif;
    font-size: 11px; font-weight: 700;
    letter-spacing: 1.2px; text-transform: uppercase;
    padding: 8px 18px;
    border-radius: 10px;
    text-decoration: none !important;
    transition: background 0.2s, color 0.2s;
}
.home-btn-wrapper a:hover {
    background: #113431;
    color: #EAA93E !important;
}

/* ── divider ── */
.gdivider {
    display: flex; align-items: center; gap: 10px;
    margin: 24px 0;
}
.gdivider::before, .gdivider::after {
    content: ''; flex: 1; height: 1px; background: var(--border);
}
.gdivider span { color: #EAA93E; font-size: 12px; }

/* ── budget pill ── */
.budget-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #113431;
    color: #EAA93E;
    font-family: 'Inter', sans-serif;
    font-size: 11px; font-weight: 700;
    padding: 5px 14px; border-radius: 20px;
    margin-top: 6px;
}

/* ── result cards ── */
.r-placeholder {
    height: 100%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 12px; color: var(--muted);
    text-align: center;
}
.r-placeholder-icon { font-size: 48px; opacity: .4; }
.r-placeholder-text {
    font-family: 'Inter', sans-serif;
    font-size: 13px; color: var(--muted); line-height: 1.6;
}
.rcard {
    background: #fff;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 24px 26px;
    margin-bottom: 18px;
    position: relative;
}
.rcard.top {
    border-color: #EAA93E;
    background: linear-gradient(135deg, #fffdf5 0%, #fff9e8 100%);
}
.rbadge {
    position: absolute; top: -11px; left: 22px;
    font-family: 'Inter', sans-serif;
    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 4px 12px; border-radius: 20px;
}
.rbadge.gold   { background: #EAA93E; color: #113431; }
.rbadge.silver { background: #113431; color: #fff; }
.rloc-tag {
    display: inline-block;
    background: #113431; color: #fff;
    font-family: 'Inter', sans-serif;
    font-size: 9px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; padding: 3px 10px;
    border-radius: 20px; margin: 10px 0 6px;
}
.rname {
    font-family: 'Playfair Display', serif;
    font-size: 19px; font-weight: 700; color: var(--dark);
    margin: 4px 0;
}
.rtipe {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--muted); margin-bottom: 16px;
}
.rscore-label {
    font-family: 'Inter', sans-serif;
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: var(--muted);
}
.rscore-val {
    font-family: 'Playfair Display', serif;
    font-size: 28px; font-weight: 700; color: #113431;
}
.rscore-val.gold { color: #EAA93E; }
.pbar-track {
    background: #e8eeec; border-radius: 6px; height: 6px;
    margin: 8px 0 16px; overflow: hidden;
}
.pbar-fill {
    height: 100%; border-radius: 6px;
    background: linear-gradient(90deg, #113431, #265e58);
}
.pbar-fill.gold { background: linear-gradient(90deg, #EAA93E, #c9891a); }
.rnotes-title {
    font-family: 'Inter', sans-serif;
    font-size: 9px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: var(--muted); margin-bottom: 8px;
}
.rnote {
    font-family: 'Inter', sans-serif;
    font-size: 12.5px; color: var(--text-soft);
    padding: 7px 0; border-bottom: 1px dashed #d8e6e3;
    display: flex; gap: 8px; line-height: 1.5;
}
.rnote:last-child { border-bottom: none; }

/* ── empty / error state ── */
.estate {
    text-align: center; padding: 44px 24px;
    background: #fff8f0; border: 1.5px solid #f5d89a;
    border-radius: var(--radius-lg);
}
.estate-icon  { font-size: 36px; margin-bottom: 10px; }
.estate-title {
    font-family: 'Playfair Display', serif;
    font-size: 18px; color: var(--dark); margin-bottom: 8px;
}
.estate-sub {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--muted); line-height: 1.7;
}

/* ── footer ── */
.footer {
    font-family: 'Inter', sans-serif;
    font-size: 10px; color: #aabfbc; letter-spacing: 1.2px;
    text-align: center; padding: 20px 0 10px;
    border-top: 1px solid var(--border); margin-top: 8px;
}

/* ── SECTION BADGES ── */
.panel-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: 'Inter', sans-serif;
    font-size: 9px; font-weight: 800;
    letter-spacing: 2.5px; text-transform: uppercase;
    padding: 5px 14px; border-radius: 20px; margin-bottom: 18px;
}
.panel-badge.input-badge  { background: #113431; color: #EAA93E; }
.panel-badge.output-badge { background: linear-gradient(135deg, #EAA93E, #c9891a); color: #113431; }

/* ── CATATAN MINIMAL PAX ── */
.notes-box {
    background: #fafbfa;
    border: 1px solid var(--border);
    border-left: 3px solid var(--primary);
    border-radius: var(--radius-sm);
    padding: 14px 18px; margin: 16px 0 4px;
}
.notes-title {
    font-family: 'Inter', sans-serif;
    font-size: 9px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase;
    color: var(--muted); margin-bottom: 8px;
}
.notes-row {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--text-soft);
    padding: 5px 0; border-bottom: 1px dashed #e3ece9; line-height: 1.6;
}
.notes-row:last-child { border-bottom: none; }

/* ── KOLOM KIRI & KANAN ── */
section[data-testid="column"]:nth-child(1) > div {
    background: #F4F7F6;
    border-right: 3px solid #113431;
    padding: 28px 32px !important;
    min-height: calc(100vh - 64px);
    position: relative;
}
section[data-testid="column"]:nth-child(1) > div::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #113431 0%, #EAA93E 100%);
}
section[data-testid="column"]:nth-child(2) > div {
    background: #ffffff;
    padding: 28px 32px !important;
    min-height: calc(100vh - 64px);
    position: relative;
}
section[data-testid="column"]:nth-child(2) > div::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #EAA93E 0%, #113431 100%);
}
@media (max-width: 900px) {
    section[data-testid="column"]:nth-child(1) > div,
    section[data-testid="column"]:nth-child(2) > div {
        padding: 20px 16px !important;
        min-height: auto;
        border-right: none !important;
    }
    section[data-testid="column"]:nth-child(1) > div {
        padding-bottom: 92px !important;
    }
    /* ── Sticky CTA "Temukan Paket Terbaik" di layar mobile ── */
    .element-container:has(> .cta-anchor) + .element-container:has(div[data-testid="stButton"]) {
        position: fixed !important;
        left: 0; right: 0; bottom: 0;
        z-index: 9999;
        margin: 0 !important;
        background: #ffffff;
        padding: 12px 16px calc(10px + env(safe-area-inset-bottom));
        box-shadow: 0 -6px 20px rgba(17,52,49,.14);
    }
}

/* ══════════════════════════════════════════════
   SKELETON LOADING (saat proses rekomendasi)
   ══════════════════════════════════════════════ */
.skeleton-card {
    background: #fff;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 24px 26px;
    margin-bottom: 18px;
}
.sk-line {
    height: 12px;
    border-radius: 6px;
    margin-bottom: 12px;
    background: linear-gradient(90deg, #eef3f1 25%, #e2ece8 37%, #eef3f1 63%);
    background-size: 400% 100%;
    animation: sk-shimmer 1.3s ease-in-out infinite;
}
.sk-line.w30 { width: 30%; height: 10px; }
.sk-line.w50 { width: 50%; height: 18px; }
.sk-line.w70 { width: 70%; height: 12px; }
.sk-line.w40 { width: 40%; height: 8px; margin-top: 16px; }
.sk-bar { height: 6px; border-radius: 6px; width: 100%; margin: 8px 0 16px;
    background: linear-gradient(90deg, #eef3f1 25%, #e2ece8 37%, #eef3f1 63%);
    background-size: 400% 100%; animation: sk-shimmer 1.3s ease-in-out infinite; }
@keyframes sk-shimmer {
    0%   { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.loading-caption {
    display: flex; align-items: center; gap: 10px;
    font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600;
    color: var(--muted); letter-spacing: .5px; margin-bottom: 18px;
}
.loading-dot {
    width: 9px; height: 9px; border-radius: 50%; background: var(--accent);
    animation: sk-pulse 1s ease-in-out infinite;
}
@keyframes sk-pulse {
    0%, 100% { opacity: .35; transform: scale(.8); }
    50%      { opacity: 1;   transform: scale(1.1); }
}

/* ══════════════════════════════════════════════
   UBAH KRITERIA (kembali ke panel kiri)
   ══════════════════════════════════════════════ */
.reset-criteria-wrap { display: flex; justify-content: flex-end; margin: -6px 0 16px; }
.reset-criteria-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: #fff;
    border: 1.5px solid #113431;
    color: #113431 !important;
    font-family: 'Inter', sans-serif;
    font-size: 10.5px; font-weight: 700;
    letter-spacing: 1px; text-transform: uppercase;
    padding: 7px 14px; border-radius: 20px;
    text-decoration: none !important;
    transition: background .2s, color .2s;
}
.reset-criteria-btn:hover { background: #113431; color: #fff !important; }

/* ══════════════════════════════════════════════
   COLLAPSIBLE NOTES BOX (accordion)
   ══════════════════════════════════════════════ */
details.notes-box { padding: 0; overflow: hidden; cursor: pointer; }
details.notes-box summary.notes-title {
    list-style: none;
    display: flex; align-items: center; justify-content: space-between;
    margin: 0; padding: 14px 18px;
}
details.notes-box summary.notes-title::-webkit-details-marker { display: none; }
details.notes-box summary.notes-title .notes-chevron {
    font-size: 11px; color: var(--accent); transition: transform .2s ease;
    flex-shrink: 0; margin-left: 10px;
}
details.notes-box[open] summary.notes-title .notes-chevron { transform: rotate(180deg); }
details.notes-box .notes-body { padding: 0 18px 12px; }
details.notes-box .notes-row:first-child { padding-top: 0; }

/* ══════════════════════════════════════════════
   BUDGET vs PAX — peringatan real-time
   ══════════════════════════════════════════════ */
.budget-warn {
    display: flex; gap: 10px; align-items: flex-start;
    background: #fff8e6;
    border: 1.5px solid #f3cf6b;
    border-radius: var(--radius-sm);
    padding: 12px 16px; margin: 10px 0 4px;
}
.budget-warn .bw-icon { font-size: 15px; line-height: 1.4; }
.budget-warn .bw-text {
    font-family: 'Inter', sans-serif; font-size: 12px; line-height: 1.6;
    color: #6b5410;
}
.budget-warn .bw-text b { color: #4a3a0c; }

/* ══════════════════════════════════════════════
   COPY / SHARE BUTTON di setiap card
   ══════════════════════════════════════════════ */
.rcard-actions { display: flex; gap: 8px; margin-top: 16px; }
.copy-btn {
    font-family: 'Inter', sans-serif;
    font-size: 10.5px; font-weight: 700;
    letter-spacing: .8px; text-transform: uppercase;
    background: #f4f7f6; border: 1.5px solid var(--border);
    color: #113431; border-radius: 10px;
    padding: 8px 14px; cursor: pointer;
    transition: background .2s, border-color .2s;
}
.copy-btn:hover { background: #e8f0ee; border-color: #113431; }

/* ══════════════════════════════════════════════
   PERBANDINGAN PAKET (checkbox + tabel side-by-side)
   ══════════════════════════════════════════════ */
.cmp-checkbox-wrap { margin: -10px 0 18px; }
.element-container:has(> .cmp-marker) + .element-container div[data-testid="stCheckbox"] {
    margin-top: -14px !important;
    margin-bottom: 18px !important;
}
.element-container:has(> .cmp-marker) + .element-container div[data-testid="stCheckbox"] label p {
    font-family: 'Inter', sans-serif !important;
    font-size: 11.5px !important; font-weight: 600 !important;
    color: var(--text-soft) !important; text-transform: none !important;
}
.cmp-limit-warn {
    background: #fff0ee; border: 1.5px solid #f3a98f;
    color: #8a3a26; border-radius: var(--radius-sm);
    font-family: 'Inter', sans-serif; font-size: 12px;
    padding: 10px 16px; margin: 4px 0 16px;
}
.cmp-section { margin-top: 8px; }
.cmp-table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.cmp-table {
    width: 100%; min-width: 560px; border-collapse: collapse;
    background: #fff; border: 1.5px solid var(--border);
    border-radius: var(--radius-lg); overflow: hidden;
}
.cmp-table th, .cmp-table td {
    padding: 12px 16px; text-align: left; vertical-align: top;
    border-bottom: 1px solid var(--border);
    font-family: 'Inter', sans-serif; font-size: 12.5px; color: var(--text-soft);
}
.cmp-table tr:last-child th, .cmp-table tr:last-child td { border-bottom: none; }
.cmp-table th.cmp-label {
    width: 150px; font-weight: 700; font-size: 10px; letter-spacing: 1px;
    text-transform: uppercase; color: var(--muted); background: #f8faf9;
}
.cmp-table td.cmp-pkg-name {
    font-family: 'Playfair Display', serif; font-size: 16px; font-weight: 700; color: var(--dark);
}
.cmp-table td.cmp-best { background: #fffdf5; }
.cmp-table .cmp-score { font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #113431; }
.cmp-table .cmp-loc-tag {
    display: inline-block; background: #113431; color: #fff;
    font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    padding: 3px 10px; border-radius: 20px;
}
.cmp-table ul { margin: 0; padding-left: 16px; }
.cmp-table li { padding: 3px 0; line-height: 1.5; }

::selection { background: var(--accent); color: var(--primary); }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 4. LOAD MODEL
# =====================================================================
@st.cache_resource
def load_model():
    model   = joblib.load("model_rekomendasi_rf.pkl")
    classes = joblib.load("nama_kelas_paket_rf.pkl")
    return model, classes

model_ok = False
try:
    model_cat, model_classes = load_model()
    model_ok = True
except:
    pass

# =====================================================================
# 5. TWO-COLUMN LAYOUT
# =====================================================================
col_left, col_right = st.columns([4, 5], gap="small")

# =====================================================================
# 6. INPUT PANEL (KIRI)
# =====================================================================
with col_left:
    st.markdown('<div id="kriteria-input"></div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="home-btn-wrapper">
        <a href="https://corporateescaper.infokand23.my.id/" target="_self">&#8592; Kembali ke Beranda</a>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="panel-badge input-badge">Input Kriteria Perjalanan</div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Destinasi Wisata</div>', unsafe_allow_html=True)
    destinasi = st.selectbox("Destinasi", ["All", "Gili", "Mentawai", "Nusa Penida"], label_visibility="collapsed")

    if destinasi == "Mentawai":
        render_notes_accordion("Catatan Minimal Pax — Mentawai", [
            "Open Trip — minimal 7 peserta, Rp1.800.000/pax",
            "Private 2 pax — minimal 2 peserta, Rp3.000.000/pax",
            "Private 3–4 pax — minimal 3 peserta, Rp2.300.000/pax",
            "Private 5–6 pax — minimal 5 peserta, Rp2.000.000/pax",
            "Private 7+ pax — minimal 7 peserta, Rp1.800.000/pax",
            "Family Gathering — minimal 10 peserta direkomendasikan",
        ])
    elif destinasi == "Nusa Penida":
        render_notes_accordion("Catatan Minimal Pax — Nusa Penida", [
            "Package 1 — minimal 2 peserta, Rp800.000/pax (Manta Bay, Crystal Bay, Mangrove)",
            "Package 2 — minimal 2 peserta, Rp1.350.000/pax (Manta Point, Crystal Bay, Gamat Bay)",
        ])
    elif destinasi == "Gili":
        render_notes_accordion("Catatan Minimal Pax — Gili", [
            "Snorkeling Public — minimal 1 peserta, Rp150.000/pax",
            "Snorkeling Private — minimal 1 peserta, Rp550.000/pax",
            "SUP / Kayak Single — minimal 1 peserta, mulai Rp100.000/pax",
            "Kayak Double — minimal 1 peserta (berpasangan), mulai Rp150.000/pax",
            "Horse Riding — minimal 1 peserta, mulai Rp250.000/pax",
        ])
    else:
        render_notes_accordion("Catatan Minimal Pax — Semua Destinasi", [
            "Mentawai Open Trip — min. 7 pax, Rp1.800.000/pax",
            "Mentawai Private — min. 2 pax, mulai Rp1.800.000/pax",
            "Mentawai Gathering — rekomendasi 10 pax",
            "Nusa Penida — min. 2 pax, Rp800rb–Rp1,35jt/pax (Setiap Paket Nusa Penida Sudah Include Dokumentasi Drone)",
            "Gili (semua paket) — min. 1 pax, mulai Rp100.000/pax",
        ])


    st.markdown('<div class="slabel">Budget & Peserta</div>', unsafe_allow_html=True)

    budget_raw = st.text_input(
        "Total Budget Kelompok (IDR)",
        value="1.000.000",
        placeholder="Contoh: 1.000.000"
    )
    # Parse angka dari format titik (1.000.000 → 1000000)
    try:
        budget = int(budget_raw.replace(".", "").replace(",", "").strip())
        if budget < 100000:
            st.warning("Budget minimum Rp 100.000")
            budget = 100000
    except:
        st.error("Format budget tidak valid. Contoh: 5.000.000")
        budget = 100000

    # Format ulang tampilan dengan titik pemisah ribuan
    budget_formatted = f"{budget:,}".replace(",", ".")
    if budget_raw and budget_raw.replace(".", "").replace(",", "").strip().isdigit():
        st.caption(f"Budget terdeteksi: Rp {budget_formatted}")

    pax    = st.number_input("Jumlah Peserta (Pax)", min_value=1, step=1)
    st.markdown(f'<div class="budget-pill">Rp {budget/pax:,.0f} / pax</div>', unsafe_allow_html=True)

    # ── Validasi real-time Budget vs Pax ──
    harga_pax_min_estimasi = estimate_min_harga_pax(destinasi, pax)
    if (budget / pax) < harga_pax_min_estimasi:
        st.markdown(f"""
        <div class="budget-warn">
            <div class="bw-icon">⚠️</div>
            <div class="bw-text">
                Budget <b>Rp {budget/pax:,.0f}/pax</b> tampak terlalu kecil untuk destinasi
                <b>{destinasi}</b> (estimasi mulai <b>Rp {harga_pax_min_estimasi:,.0f}/pax</b>).
                Naikkan budget, kurangi pax, atau pilih destinasi lain agar hasil pencarian lebih akurat.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="slabel">Dokumentasi Drone</div>', unsafe_allow_html=True)
    if destinasi == "Nusa Penida":
        st.markdown("""
        <div class="notes-box" style="margin-bottom:8px;">
            <div class="notes-row">✅ Drone sudah termasuk dalam semua paket Nusa Penida.</div>
        </div>
        """, unsafe_allow_html=True)
        drone_user = 0
    else:
        drone      = st.radio("Drone", ["Ya, tambahkan", "Tidak perlu"], label_visibility="collapsed", horizontal=True)
        drone_user = 1 if "Ya" in drone else 0

    st.markdown('<div class="slabel">Durasi & Keberangkatan</div>', unsafe_allow_html=True)

    if destinasi == "Mentawai":
        durasi       = st.selectbox("Durasi Trip", ["3 Hari 2 Malam", "Fleksibel"])
        titik_kumpul = st.selectbox("Titik Keberangkatan", ["Padang", "Pekanbaru", "Mentawai (Lokal)"])
    elif destinasi == "Nusa Penida":
        durasi       = st.selectbox("Pilihan Paket", ["Package 1 (Manta Bay)", "Package 2 (Manta Point)"])
        titik_kumpul = "Lokal"
    elif destinasi == "Gili":
        durasi       = st.selectbox("Durasi / Sesi", ["1 Hour", "2 Hours", "4 Hours", "All Day", "Normal Price", "Peak Season Price"])
        titik_kumpul = "Lokal"
    else:
        durasi       = st.selectbox("Durasi Preferensi", ["Fleksibel", "1 Hour", "2 Hours", "4 Hours", "All Day"])
        titik_kumpul = st.selectbox("Titik Keberangkatan (Mentawai)", ["Padang", "Pekanbaru", "Mentawai (Lokal)"])

    if destinasi == "All":
        destinasi_final_list = ["Mentawai", "Gili", "Nusa Penida"]
    else:
        destinasi_final_list = [destinasi]

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="cta-anchor"></div>', unsafe_allow_html=True)
    cari = st.button("Temukan Paket Terbaik", use_container_width=True)

# =====================================================================
# 7. OUTPUT PANEL (KANAN)
# =====================================================================
with col_right:
    st.markdown('<div class="panel-badge output-badge">Hasil Rekomendasi</div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">3 Paket Paling di Rekomendasikan</div>', unsafe_allow_html=True)

    if cari:
        st.session_state['show_results'] = True

    show_results = st.session_state.get('show_results', False)

    if not show_results:
        st.markdown("""
        <div class="r-placeholder" style="margin-top:40px;">
            <div class="r-placeholder-icon"></div>
            <div class="r-placeholder-text">
                Isi kriteria perjalanan Anda di panel kiri,<br>
                lalu klik <strong>Temukan Paket Terbaik</strong><br>
                untuk melihat rekomendasi.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Tombol Ubah Kriteria — scroll kembali ke panel kiri ──
        st.markdown("""
        <div class="reset-criteria-wrap">
            <a class="reset-criteria-btn" href="#kriteria-input">&#8634; Ubah Kriteria</a>
        </div>
        """, unsafe_allow_html=True)

        # ── Loading skeleton — hanya tampil sesaat setelah tombol cari diklik,
        #    bukan setiap kali widget lain (mis. checkbox bandingkan) di-toggle ──
        result_area = st.empty()
        if cari:
            with result_area.container():
                render_skeleton_cards()
            time.sleep(0.45)

        dict_predictions = {}

        for dest_item in destinasi_final_list:
            is_gili     = 1 if dest_item.lower() == "gili" else 0
            is_mentawai = 1 if dest_item.lower() == "mentawai" else 0
            is_nusa     = 1 if dest_item.lower() == "nusa penida" else 0

            df_awal = pd.DataFrame([{
                'pax': pax, 'total_price': budget, 'add_drone': drone_user,
                'price_per_pax': budget / pax,
                'dest_gili': is_gili, 'dest_mentawai': is_mentawai, 'dest_nusa penida': is_nusa
            }])
            df_awal      = df_awal[['pax','total_price','add_drone','price_per_pax','dest_gili','dest_mentawai','dest_nusa penida']]
            probabilitas = model_cat.predict_proba(df_awal)[0]
            nama_paket   = model_classes

            # --- INJEKSI FAMILY GATHERING ---
            if dest_item.lower() == "mentawai":
                biaya_drone_g = (300000 * pax) if drone_user == 1 else 0
                if "pekanbaru" in titik_kumpul.lower():
                    harga_g = 2850000
                elif "padang" in titik_kumpul.lower():
                    harga_g = 3000000
                else:
                    harga_g = 2400000
                total_g = (harga_g * pax) + biaya_drone_g
                notes_g = []
                if drone_user == 1:
                    notes_g.append(f"Add-on Drone: Rp300.000 × {pax} pax = Rp{biaya_drone_g:,}")
                notes_g.append(f"Tarif Gathering (Start {titik_kumpul}): Rp{harga_g:,} / pax")
                notes_g.append(f"Total minimum: Rp{total_g:,}")
                if budget >= total_g:
                    skor_g = 0.99 if pax >= 10 else 0.75
                    dict_predictions["Family Gathering||Mentawai"] = (skor_g, "Mentawai", f"Family Gathering (Start {titik_kumpul})", notes_g, total_g)

            # --- LOOP PAKET MODEL ---
            for paket, skor in zip(nama_paket, probabilitas):
                pname  = str(paket).strip()
                pclean = pname.lower()
                if "gathering" in pclean:
                    continue

                tipe_detail = "Standar Paket"
                catatan     = []
                is_valid    = True
                biaya_total = 0

                if "mentawai" in pclean or "private trip" in pclean or "open trip" in pclean:
                    lok = "Mentawai"
                elif pname in ["Paddle Board", "Kayaking", "Horse Riding", "Snorkeling Gili"]:
                    lok = "Gili"
                elif "nusa penida" in pclean or "package" in pclean:
                    lok = "Nusa Penida"
                else:
                    lok = dest_item

                # === MENTAWAI ===
                if lok == "Mentawai":
                    drone_cost = (300000 * pax) if drone_user == 1 else 0
                    if drone_user == 1:
                        catatan.append(f"Drone: Rp300.000 × {pax} pax = Rp{drone_cost:,}")
                    extra = 1050000 if "pekanbaru" in titik_kumpul.lower() else (600000 if "padang" in titik_kumpul.lower() else 0)
                    if extra > 0:
                        catatan.append(f"Extra Meeting Point {titik_kumpul}: Rp{extra:,} / pax")

                    if "open" in pclean:
                        pname       = "Mentawai Open Trip"
                        tipe_detail = "Open Trip (min. 7 peserta)"
                        if pax < 7:
                            is_valid = False
                            catatan.append("Minimal 7 peserta untuk Open Trip")
                        biaya_total = ((1800000 + extra) * pax) + drone_cost
                        catatan.append("Tarif: Rp1.800.000 / pax")
                    else:
                        pname       = "Mentawai Private Trip"
                        hb          = 3000000 if pax == 2 else (2300000 if 3 <= pax <= 4 else (2000000 if 5 <= pax <= 6 else 1800000))
                        tipe_detail = f"Private Trip — Rp{hb:,}/pax untuk {pax} pax"
                        biaya_total = ((hb + extra) * pax) + drone_cost
                        catatan.append(f"Base Private ({pax} pax): Rp{hb:,} / pax")

                    catatan.append(f"Total minimum: Rp{biaya_total:,}")
                    if budget < biaya_total:
                        is_valid = False

                # === NUSA PENIDA ===
                elif lok == "Nusa Penida":
                    if pax < 2:
                        is_valid = False
                        catatan.append("Minimal 2 peserta")
                    if "2" in durasi or "exklusif" in pclean:
                        tipe_detail = "Package 2 — Manta Point, Crystal Bay, Gamat Bay"
                        hp = 1350000
                    else:
                        tipe_detail = "Package 1 — Manta Bay, Crystal Bay, Mangrove Point"
                        hp = 800000
                    biaya_total = hp * pax
                    catatan.append(f"Tarif: Rp{hp:,} × {pax} pax = Rp{biaya_total:,}")
                    if budget < biaya_total:
                        is_valid = False

                # === GILI ===
                elif lok == "Gili":
                    drone_g = 0
                    if drone_user == 1:
                        drone_g = 150000
                        catatan.append(f"Drone (lokal grup): Rp{drone_g:,}")

                    if "snorkeling" in pclean:
                        if "public" in pclean or "public" in durasi.lower():
                            tipe_detail = "Public Snorkeling Trip"
                            biaya_total = (150000 * pax) + drone_g
                            catatan.append(f"Tarif Public: Rp150.000 × {pax} pax")
                        else:
                            tipe_detail = "Private Snorkeling Trip"
                            biaya_total = (550000 * pax) + drone_g
                            catatan.append(f"Tarif Private: Rp550.000 × {pax} pax")
                    elif "paddle" in pclean or "kayak" in pclean:
                        if "1" in durasi:   jl, hs, hd = "1 Hour",   100000, 150000
                        elif "2" in durasi: jl, hs, hd = "2 Hours",  180000, 250000
                        elif "4" in durasi: jl, hs, hd = "4 Hours",  300000, 350000
                        else:               jl, hs, hd = "All Day",  500000, 550000
                        if "double" in pclean:
                            tipe_detail = f"Double Kayak — {jl}"
                            biaya_total = (hd * pax) + drone_g
                            catatan.append(f"Double Kayak {jl}: Rp{hd:,} × {pax} pax")
                        elif "kayak" in pclean:
                            tipe_detail = f"Single Kayak — {jl}"
                            biaya_total = (hs * pax) + drone_g
                            catatan.append(f"Single Kayak {jl}: Rp{hs:,} × {pax} pax")
                        else:
                            tipe_detail = f"Stand-Up Paddle Board — {jl}"
                            biaya_total = (hs * pax) + drone_g
                            catatan.append(f"SUP {jl}: Rp{hs:,} × {pax} pax")
                    elif "horse" in pclean or "riding" in pclean:
                        is_pk = "peak" in durasi.lower()
                        ml    = "30 Mins" if "30" in durasi else "60 Mins"
                        hk    = (300000 if "30" in durasi else 450000) if is_pk else (250000 if "30" in durasi else 400000)
                        tipe_detail = f"Horse Riding {ml} — {'Peak Season' if is_pk else 'Normal'}"
                        biaya_total = hk * pax
                        catatan.append(f"Horse Riding {ml}: Rp{hk:,} × {pax} pax")
                        if drone_user == 1:
                            catatan.append("ℹ️ Drone tidak tersedia untuk Horse Riding")

                    if biaya_total > 0 and budget < biaya_total:
                        is_valid = False

                if is_valid:
                    gf  = 1 if lok.lower() == "gili" else 0
                    mf  = 1 if lok.lower() == "mentawai" else 0
                    nf  = 1 if lok.lower() == "nusa penida" else 0
                    inp = pd.DataFrame([{
                        'pax': pax, 'total_price': budget, 'add_drone': drone_user,
                        'price_per_pax': budget/pax,
                        'dest_gili': gf, 'dest_mentawai': mf, 'dest_nusa penida': nf
                    }])
                    inp     = inp[['pax','total_price','add_drone','price_per_pax','dest_gili','dest_mentawai','dest_nusa penida']]
                    idx_p   = list(model_classes).index(paket)
                    sf      = model_cat.predict_proba(inp)[0][idx_p]
                    if lok == "Mentawai" and pax >= 10 and "private" in pclean:
                        sf = 0.85
                    lolos = (destinasi == "All") or (destinasi == lok)
                    if lolos:
                        dict_predictions[f"{pname}||{lok}"] = (sf, lok, tipe_detail, catatan, biaya_total)

        hasil_urut = sorted(dict_predictions.items(), key=lambda x: x[1][0], reverse=True)

        with result_area.container():
            if len(hasil_urut) == 0:
                st.markdown("""
                <div class="estate">
                    <div class="estate-icon"></div>
                    <div class="estate-title">Tidak Ada Paket yang Cocok</div>
                    <div class="estate-sub">Budget atau jumlah peserta belum memenuhi syarat minimum.<br>
                    Coba naikkan budget, kurangi peserta, atau pilih destinasi lain.</div>
                </div>""", unsafe_allow_html=True)
            else:
                card_entries = []
                n_cards = len(hasil_urut[:3])

                for i, (key, (skor, lok, tipe, notes, biaya_total)) in enumerate(hasil_urut[:3], 1):
                    nama_display = key.split("||")[0]
                    pct      = skor * 100
                    is_top   = (i == 1)
                    card_cls = "rcard top" if is_top else "rcard"
                    badge_cls= "rbadge gold" if is_top else "rbadge silver"
                    badge_txt= "Best Match" if is_top else f"# {i}"
                    sc_cls   = "rscore-val gold" if is_top else "rscore-val"
                    bar_cls  = "pbar-fill gold" if is_top else "pbar-fill"

                    notes_html = ""
                    if notes:
                        items      = "".join([f'<div class="rnote"><span>→</span><span>{n}</span></div>' for n in notes])
                        notes_html = f'<div class="rnotes-title" style="margin-top:14px;">Rincian Kalkulasi</div>{items}'

                    # ── Ringkasan teks untuk tombol Salin / Share ──
                    summary_lines = [f"{nama_display} — {lok}", tipe, f"Tingkat Kecocokan AI: {pct:.1f}%"]
                    if biaya_total:
                        summary_lines.append(f"Estimasi Total: Rp{biaya_total:,}")
                    if notes:
                        summary_lines.append("")
                        summary_lines.append("Rincian:")
                        summary_lines += [f"- {n}" for n in notes]
                    summary_lines.append("")
                    summary_lines.append("via Corporate Escaper")
                    summary_text = "\n".join(summary_lines).replace("'", "’")
                    js_payload   = json.dumps(summary_text)
                    copy_btn_html = (
                        '<div class="rcard-actions">'
                        "<button type=\"button\" class=\"copy-btn\" onclick='navigator.clipboard.writeText("
                        + js_payload +
                        ").then(()=>{const t=this.innerHTML;this.innerHTML=\"&#10003;&nbsp;Tersalin!\";"
                        "setTimeout(()=>{this.innerHTML=t;},1800);})'>"
                        "&#128203;&nbsp;Salin Ringkasan</button>"
                        '</div>'
                    )

                    st.markdown(f"""
                    <div class="{card_cls}">
                        <div class="{badge_cls}">{badge_txt}</div>
                        <div class="rloc-tag">{lok}</div>
                        <div class="rname">{nama_display}</div>
                        <div class="rtipe">{tipe}</div>
                        <div class="rscore-label">Tingkat Kecocokan AI</div>
                        <div class="{sc_cls}">{pct:.1f}%</div>
                        <div class="pbar-track">
                            <div class="{bar_cls}" style="width:{min(pct,100):.1f}%"></div>
                        </div>
                        {notes_html}
                        {copy_btn_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Perbandingan Side-by-Side: pilih maks. 2 paket ──
                    st.markdown('<div class="cmp-marker"></div>', unsafe_allow_html=True)
                    st.checkbox(f'Pilih "{nama_display}" untuk dibandingkan', key=f"cmp_select_{i}")

                    card_entries.append({
                        "nama": nama_display, "lok": lok, "tipe": tipe,
                        "pct": pct, "notes": notes, "total": biaya_total,
                    })

                selected_idx = [j for j in range(1, n_cards + 1) if st.session_state.get(f"cmp_select_{j}", False)]
                if len(selected_idx) > 2:
                    st.markdown("""
                    <div class="cmp-limit-warn">⚠️ Pilih maksimal 2 paket untuk dibandingkan — hapus salah satu centang di atas.</div>
                    """, unsafe_allow_html=True)
                elif len(selected_idx) == 2:
                    chosen = [card_entries[idx - 1] for idx in selected_idx]
                    render_compare_table(chosen)
