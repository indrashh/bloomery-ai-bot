import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import re
from datetime import datetime

# 1. KONFIGURASI TAMPILAN KHUSUS WIDGET
st.set_page_config(page_title="Bloomery", layout="centered", initial_sidebar_state="collapsed")

# CSS Khusus untuk menghilangkan border, header, dan merapikan padding agar pas di dalam Iframe HTML
st.markdown("""
<style>
    header {visibility: hidden; height: 0px !important;}
    footer {visibility: hidden; height: 0px !important;}
    .block-container { padding: 1rem 1rem 5rem 1rem !important; max-width: 100%; margin: 0; }
    [data-testid="collapsedControl"] { display: none; } /* Sembunyikan ikon hamburger menu */
    
    /* Modifikasi Chat Bubble */
    .stChatMessage { background-color: #FFFDD0; border-radius: 12px; padding: 12px; margin-bottom: 8px; border: 1px solid #FFB6C1; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #FFFFFF; } /* Chat User */
    
    /* Modifikasi Tombol & Expander */
    div.stButton > button { background-color: #B76E79; color: white; border-radius: 8px; width: 100%; border: none;}
    div.stButton > button:hover { background-color: #9A5A64; color: white;}
    .streamlit-expanderHeader { font-size: 14px !important; color: #B76E79 !important; }
</style>
""", unsafe_allow_html=True)

# 2. INISIALISASI DATABASE SQLITE
def init_db():
    conn = sqlite3.connect('bloomery.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, nama TEXT, harga INTEGER, kategori TEXT, warna TEXT, bunga TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, whatsapp TEXT, produk TEXT, tanggal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_msg TEXT, bot_reply TEXT, tanggal TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        dummies = [
            ("Graduation Pink Rose", 150000, "wisuda", "pink", "mawar"),
            ("Red Elegance Anniversary", 350000, "anniversary", "merah", "mawar"),
            ("Yellow Cheer Up", 120000, "ulang tahun", "kuning", "matahari"),
            ("White Lily Wedding", 500000, "pernikahan", "putih", "lily"),
            ("Valentine Pink Tulip", 250000, "valentine", "pink", "tulip"),
            ("Graduation Blue Hydrangea", 200000, "wisuda", "biru", "hydrangea"),
            ("Rustic Wedding Mix", 450000, "pernikahan", "coklat", "mix"),
            ("Birthday Pastel Peony", 280000, "ulang tahun", "pastel", "peony")
        ]
        c.executemany("INSERT INTO products (nama, harga, kategori, warna, bunga) VALUES (?, ?, ?, ?, ?)", dummies)
        conn.commit()
    return conn

conn = init_db()

# Menghapus kata AI pada sapaan awal
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Halo! Saya Asisten Florist Bloomery. Acara apa yang sedang Anda siapkan? (Cth: Buket wisuda warna pink)"}]

# 3. ROUTING VIEW (Memisahkan Tampilan HTML Iframe vs Tampilan Admin)
# Mengambil parameter dari URL (contoh: ?view=admin)
view_mode = st.query_params.get("view", "chatbot")

if view_mode == "admin":
    # ==========================================
    # HALAMAN KHUSUS ADMIN (FULL SCREEN)
    # ==========================================
    st.markdown("<h2 style='color:#B76E79;'>📊 Dashboard Admin Bloomery</h2>", unsafe_allow_html=True)
    df_leads = pd.read_sql("SELECT * FROM leads", conn)
    df_chats = pd.read_sql("SELECT * FROM chat_history", conn)
    
    col1, col2 = st.columns(2)
    col1.metric("Leads Pesanan Masuk", len(df_leads))
    col2.metric("Total Interaksi Chat", len(df_chats))
    
    st.markdown("---")
    if not df_leads.empty:
        st.write("**Statistik Produk Paling Diminati**")
        lead_counts = df_leads['produk'].value_counts().reset_index()
        lead_counts.columns = ['Produk', 'Jumlah']
        fig = px.pie(lead_counts, values='Jumlah', names='Produk', hole=0.5, color_discrete_sequence=['#FFB6C1', '#B76E79', '#FFFDD0'])
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("**Daftar Kontak Pelanggan (Leads)**")
        st.dataframe(df_leads[['tanggal', 'nama', 'whatsapp', 'produk']], hide_index=True)
        
        csv_leads = df_leads.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data Excel (CSV)", csv_leads, "leads_pelanggan.csv", "text/csv")
    else:
        st.info("Belum ada data pesanan yang masuk.")

else:
    # ==========================================
    # HALAMAN WIDGET CHATBOT (UNTUK IFRAME HTML)
    # ==========================================
    st.markdown("<h4 style='text-align:center; color:#B76E79; margin-top:-20px;'>🌸 Asisten Bloomery</h4>", unsafe_allow_html=True)
    
    # Form Lead diletakkan di dalam Expander paling atas agar tidak tertutup input chat
    with st.expander("📝 Formulir Pemesanan Buket"):
        with st.form("lead_form", clear_on_submit=False):
            nama_lead = st.text_input("Nama Lengkap")
            wa_lead = st.text_input("Nomor WhatsApp Anda")
            produk_lead = st.text_input("Buket yang Diinginkan")
            
            if st.form_submit_button("Pesan via WhatsApp 📱"):
                if nama_lead and wa_lead and produk_lead:
                    # 1. Tetap simpan ke database untuk arsip/dashboard admin Anda
                    conn.cursor().execute("INSERT INTO leads (nama, whatsapp, produk, tanggal) VALUES (?, ?, ?, ?)",
                                          (nama_lead, wa_lead, produk_lead, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    
                    # 2. Susun template pesan untuk dikirim ke WA Anda
                    pesan_wa = f"Halo Bloomery! 🌸%0A%0ASaya ingin memesan buket:%0A👤 Nama: {nama_lead}%0A📞 Nomor Kontak: {wa_lead}%0A💐 Pesanan: {produk_lead}%0A%0AMohon info ketersediaan dan total harganya ya. Terima kasih!"
                    
                    # 3. Buat link menuju WA Anda (081226397647)
                    link_wa = f"https://wa.me/6281226397647?text={pesan_wa}"
                    
                    # 4. Tampilkan tombol hijau untuk langsung buka WhatsApp
                    st.success("Formulir berhasil diisi!")
                    st.markdown(f'<a href="{link_wa}" target="_blank" style="background-color:#25D366; color:white; padding:10px 20px; text-decoration:none; border-radius:8px; display:block; text-align:center; font-weight:bold;">Lanjutkan ke WhatsApp ➔</a>', unsafe_allow_html=True)
                else:
                    st.error("Mohon lengkapi formulir terlebih dahulu.")
                    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

    # Render History Chat
    chat_container = st.container(height=350)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    # NLP & SQL Engine
    def get_ai_recommendation(user_input):
        df = pd.read_sql("SELECT * FROM products", conn)
        text = user_input.lower()
        
        budget_match = re.search(r'\b(\d+)(?:\s*(?:ribu|rb|k))?\b', text.replace('.', ''))
        max_budget = int(budget_match.group(1)) * 1000 if budget_match and int(budget_match.group(1)) < 1000 else \
                     int(budget_match.group(1)) if budget_match else None
        
        if 'wisuda' in text: df = df[df['kategori'] == 'wisuda']
        elif 'anniversary' in text: df = df[df['kategori'] == 'anniversary']
        elif 'ulang tahun' in text or 'ultah' in text: df = df[df['kategori'] == 'ulang tahun']
        elif 'pernikahan' in text: df = df[df['kategori'] == 'pernikahan']
        elif 'valentine' in text: df = df[df['kategori'] == 'valentine']
        
        for w in ['pink', 'merah', 'putih', 'kuning', 'biru', 'pastel']:
            if w in text: df = df[df['warna'].str.contains(w)]
        for b in ['mawar', 'lily', 'tulip', 'peony', 'matahari', 'mix']:
            if b in text: df = df[df['bunga'].str.contains(b)]
                
        if max_budget: df = df[df['harga'] <= max_budget]
        
        if df.empty:
            # Menghilangkan kata AI pada respon gagal pencarian
            return "Maaf, saya tidak menemukan buket tersebut. Boleh coba ubah budget atau warnanya?"
        else:
            res = "**Berikut rekomendasi terbaik kami:**\n\n"
            for _, r in df.head(3).iterrows():
                res += f"✨ **{r['nama']}** (Rp {r['harga']:,})\n"
            res += "\n*Isi formulir pemesanan di bagian atas jika berminat.*"
            return res

    # Input User (otomatis selalu di bawah, hanya ADA SATU blok)
    if prompt := st.chat_input("Ketik pesan Anda..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        bot_reply = get_ai_recommendation(prompt)
        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
        
        conn.cursor().execute("INSERT INTO chat_history (user_msg, bot_reply, tanggal) VALUES (?, ?, ?)", 
                              (prompt, bot_reply, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        st.rerun()
