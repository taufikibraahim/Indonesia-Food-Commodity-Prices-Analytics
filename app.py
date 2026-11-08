import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Konfigurasi halaman dan Tema
st.set_page_config(page_title="Indonesia Food Commodity Prices", layout="wide")

st.title("Dasboard Eksekutif Volatilitas Harga Pangan")
st.markdown(
    "Pemantauan pergerakan, anomali, dan disparitas harga komoditas pangan nasional secara interaktif."
)


# 2. Ambil data
@st.cache_data(ttl=600)
def ambil_data_volatilitas():
    db_info = st.secrets["postgres"]
    koneksi_url = (
        f"postgresql+psycopg2://{db_info['username']}:{db_info['password']}"
        f"@{db_info['host']}:{db_info['port']}/{db_info['database']}"
    )
    query = "SELECT * FROM public.mart_daily_volatility ORDER BY tanggal DESC;"
    return pd.read_sql(query, koneksi_url)


@st.cache_data(ttl=600)
def ambil_data_bulanan():
    db_info = st.secrets["postgres"]
    koneksi_url = (
        f"postgresql+psycopg2://{db_info['username']}:{db_info['password']}"
        f"@{db_info['host']}:{db_info['port']}/{db_info['database']}"
    )
    query = "SELECT * FROM public.mart_monthly_commodity_trend;"
    return pd.read_sql(query, koneksi_url)


# Memuat kedua dataset ke memori
df_utama = ambil_data_volatilitas()
df_bulan_utama = ambil_data_bulanan()

# 3. Kontrol SideBar (Filter Dinamis)
st.sidebar.header("Filter Dashboard")

daftar_provinsi = ["Semua Provinsi"] + sorted(df_utama["provinsi"].unique())
pilih_prov = st.sidebar.selectbox("Pilih Wilayah", daftar_provinsi)

daftar_komoditas = ["Semua Komoditas"] + sorted(df_utama["komoditas"].unique())
pilih_komoditas = st.sidebar.selectbox("Pilih Komoditas", daftar_komoditas)

daftar_tipe_pasar = ["Semua Tipe Pasar"] + sorted(df_utama["tipe_pasar"].unique())
pilih_tipe_pasar = st.sidebar.selectbox("Pilih Tipe Pasar", daftar_tipe_pasar)

# Logika Data Harian
df_filter = df_utama.copy()
if pilih_prov != "Semua Provinsi":
    df_filter = df_filter[df_filter["provinsi"] == pilih_prov]
if pilih_komoditas != "Semua Komoditas":
    df_filter = df_filter[df_filter["komoditas"] == pilih_komoditas]
if pilih_tipe_pasar != "Semua Tipe Pasar":
    df_filter = df_filter[df_filter["tipe_pasar"] == pilih_tipe_pasar]

# Logika Data Bulanan
df_bulan_filter = df_bulan_utama.copy()
if pilih_prov != "Semua Provinsi" and "provinsi" in df_bulan_filter.columns:
    df_bulan_filter = df_bulan_filter[df_bulan_filter["provinsi"] == pilih_prov]
if pilih_komoditas != "Semua Komoditas" and "komoditas" in df_bulan_filter.columns:
    df_bulan_filter = df_bulan_filter[df_bulan_filter["komoditas"] == pilih_komoditas]

# 4. Tata Letak
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📈 Ringkasan & Tren",
        "🏆 Papan Peringkat",
        "🗺️ Heatmap Wilayah",
        "📅 Tren Makro Bulanan",
    ]
)

# TAB 1: RINGKASAN KPI & TREN WAKTU
with tab1:
    st.subheader("Indikator Kinerja Utama (KPI)")
    col1, col2, col3 = st.columns(3)

    rata_sekarang = df_filter["harga_hari_ini"].mean()
    rata_kemarin = df_filter["harga_kemarin"].mean()

    if pd.notna(rata_sekarang) and pd.notna(rata_kemarin):
        selisih = rata_sekarang - rata_kemarin
        teks_delta = f"Rp {selisih:,.0f} dari rata-rata kemarin"
    else:
        selisih = 0
        teks_delta = "Data kemarin tidak tersedia"

    jumlah_lonjakan = len(
        df_filter[df_filter["status_volatilitas"] == "Lonjakan Ekstrem (> 5%)"]
    )
    jumlah_anjlok = len(
        df_filter[df_filter["status_volatilitas"] == "Anjlok Ekstrem (< -5%)"]
    )

    with col1:
        st.metric(
            label="Rata-rata Harga Saat Ini",
            value=f"Rp {rata_sekarang:,.0f}" if pd.notna(rata_sekarang) else "Rp 0",
            delta=teks_delta,
            delta_color="inverse",
        )
    with col2:
        st.metric(label="🚨 Titik Lonjakan Ekstrem", value=f"{jumlah_lonjakan} Kasus")
    with col3:
        st.metric(label="📉 Titik Anjlok Ekstrem", value=f"{jumlah_anjlok} Kasus")

    st.divider()

    st.subheader("Tren Pergerakan Harga Historis (Harian)")
    df_tren = (
        df_filter.groupby("tanggal")["harga_hari_ini"].mean().round(0).reset_index()
    )

    if not df_tren.empty:
        fig_tren = px.line(
            df_tren,
            x="tanggal",
            y="harga_hari_ini",
            markers=True,
            line_shape="spline",
            labels={"tanggal": "Tanggal", "harga_hari_ini": "Rata-rata Harga (Rp)"},
            title=f"Tren {pilih_komoditas} di {pilih_prov}",
        )
        fig_tren.update_traces(line_color="#0047AB")
        st.plotly_chart(fig_tren, use_container_width=True)
    else:
        st.info("Data tidak tersedia untuk kombinasi filter ini.")


# TAB 2: PAPAN PERINGKAT & TABEL DETAIL
with tab2:
    st.subheader("Peringkat Harga Tertinggi (Top 5 Provinsi)")

    df_peringkat = df_filter.groupby("provinsi")["harga_hari_ini"].mean().reset_index()
    df_peringkat = df_peringkat.sort_values(by="harga_hari_ini", ascending=False).head(
        5
    )
    df_peringkat = df_peringkat.sort_values(by="harga_hari_ini", ascending=True)

    if not df_peringkat.empty:
        fig_bar = px.bar(
            df_peringkat,
            x="harga_hari_ini",
            y="provinsi",
            orientation="h",
            text_auto=".2s",
            color="harga_hari_ini",
            color_continuous_scale="Reds",
            labels={"harga_hari_ini": "Harga (Rp)", "provinsi": "Provinsi"},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Tabel Detail Data Historis")
    st.dataframe(
        df_filter,
        use_container_width=True,
        hide_index=True,
        column_config={
            "tanggal": st.column_config.DateColumn("Tanggal"),
            "provinsi": st.column_config.TextColumn("Provinsi"),
            "komoditas": st.column_config.TextColumn("Komoditas"),
            "tipe_pasar": st.column_config.TextColumn("Tipe Pasar"),
            "harga_hari_ini": st.column_config.NumberColumn(
                "Harga Hari Ini", format="Rp %,.0f"
            ),
            "harga_kemarin": st.column_config.NumberColumn(
                "Harga Kemarin", format="Rp %,.0f"
            ),
            "selisih_harga": st.column_config.NumberColumn(
                "Selisih", format="Rp %,.0f"
            ),
            "persentase_volatilitas_absolute": st.column_config.NumberColumn(
                "Volatilitas (%)", format="%.2f %%"
            ),
            "status_volatilitas": st.column_config.TextColumn("Status"),
        },
    )


# TAB 3: HEATMAP SEBARAN HARGA
with tab3:
    st.subheader("Matriks Sebaran Harga (Heatmap)")
    st.markdown(
        "Melihat intensitas harga (merah = mahal, biru = murah) antar provinsi dari waktu ke waktu."
    )

    if not df_filter.empty:
        df_pivot = df_filter.pivot_table(
            index="provinsi", columns="tanggal", values="harga_hari_ini", aggfunc="mean"
        )

        fig_heat = px.imshow(
            df_pivot,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            labels=dict(x="Tanggal", y="Provinsi", color="Harga (Rp)"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.warning("Silakan atur filter untuk memunculkan heatmap.")

# TAB 4: TREN MAKRO BULANAN
with tab4:
    st.subheader("📅 Analisis Makro: Tren Harga Rata-rata Bulanan")
    st.markdown(
        "Melihat pola pergerakan harga komoditas dalam skala bulan untuk mendeteksi tren musiman."
    )

    if not df_bulan_filter.empty:
        # Mendeteksi nama kolom secara otomatis
        kolom_waktu = (
            "periode"
            if "periode" in df_bulan_filter.columns
            else df_bulan_filter.columns[0]
        )
        kolom_harga = (
            "avg_harga" if "avg_harga" in df_bulan_filter.columns else "harga_hari_ini"
        )

        # 1. KONVERSI FORMAT TAHUN-BULAN (Contoh: "2026-10")
        try:
            # Mengubah data menjadi datetime, lalu memotongnya menjadi format YYYY-MM
            df_bulan_filter["periode_tampil"] = pd.to_datetime(
                df_bulan_filter[kolom_waktu]
            ).dt.strftime("%Y-%m")
        except:
            # Fallback jika data dari database sudah berupa teks
            df_bulan_filter["periode_tampil"] = df_bulan_filter[kolom_waktu]

        # 2. Grouping berdasarkan kolom yang sudah diformat dan diurutkan
        df_grup_bulanan = (
            df_bulan_filter.groupby("periode_tampil")[kolom_harga].mean().reset_index()
        )
        df_grup_bulanan = df_grup_bulanan.sort_values("periode_tampil")

        # 3. Merender grafik
        fig_bulanan = px.bar(
            df_grup_bulanan,
            x="periode_tampil",
            y=kolom_harga,
            text_auto=".2s",
            labels={
                "periode_tampil": "Periode (Tahun-Bulan)",
                kolom_harga: "Rata-rata Harga (Rp)",
            },
            title=f"Tren Bulanan: {pilih_komoditas} di {pilih_prov}",
        )

        fig_bulanan.update_traces(marker_color="#2E86C1")
        # Membuat label teks di bawah batang menjadi sedikit miring agar tidak bertumpukan
        fig_bulanan.update_layout(xaxis_tickangle=-45)

        st.plotly_chart(fig_bulanan, use_container_width=True)

        with st.expander("Buka Data Tabel Bulanan"):
            st.dataframe(df_bulan_filter, use_container_width=True, hide_index=True)
    else:
        st.info("Data bulanan tidak tersedia untuk kombinasi filter ini.")
