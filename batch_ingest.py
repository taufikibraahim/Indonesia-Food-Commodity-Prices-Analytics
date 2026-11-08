import os
import re

import pandas as pd
from sqlalchemy import create_engine, text, types

# 1. Koneksi database
engine = create_engine("postgresql://root:root@pgdatabase:5432/food_prices")

# 2. Definisikan Base Directory sesuai struktur hirarki Anda
# Ini merujuk ke folder 'dataset/data_komoditas_pangan'
base_dir = os.path.join("dataset", "data_komoditas_pangan")

# Daftar nama folder target di dalam base_dir
kategori_pasar = ["pasar_modern", "pasar_tradisional", "produsen"]

print("Memulai Pipeline Ingesti Batch...")

# buat tabel di database jika belum ada
with engine.begin() as conn:
    conn.execute(
        text("""
        CREATE TABLE IF NOT EXISTS national_prices (
            tanggal DATE,
            provinsi VARCHAR(100),
            harga BIGINT,
            komoditas VARCHAR(50),
            tipe_pasar VARCHAR(50),
            CONSTRAINT unique_price_record UNIQUE (tanggal, provinsi, komoditas, tipe_pasar)
        );
    """)
    )
    print("Tabel utama siap dengan perlindungan Kunci Unik (Anti-Duplikat).")

# 3. Loop ke-1: Membuka setiap folder kategori
for folder_name in kategori_pasar:
    # Gabungkan base_dir dengan nama folder untuk membuat jalur lengkap
    # Hasilnya: 'dataset/data_komoditas_pangan/pasar_modern'
    folder_path = os.path.join(base_dir, folder_name)

    # Memanipulasi nama folder menjadi Tipe Pasar (tetap menggunakan folder_name)
    tipe_pasar = folder_name.replace("_", " ").title()

    # Cek apakah folder dengan jalur lengkap tersebut ada
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} tidak ditemukan. Lewati.")
        continue

    # 4. Loop ke-2: Membaca setiap file CSV di dalam folder tersebut
    for file_name in os.listdir(
        folder_path
    ):  # <--- Perhatikan ini menggunakan folder_path
        if file_name.endswith(".csv"):
            # Ekstraksi Regex Nama Komoditas (Tetap)
            match = re.search(r"final_komoditas_[a-z]+_(.*)_2022_2026\.csv", file_name)

            if match:
                komoditas_mentah = match.group(1)
                komoditas = komoditas_mentah.replace("_", " ").title()
            else:
                komoditas = file_name.replace(".csv", "").title()

            # Gabungkan folder_path dan file_name menjadi path lengkap file CSV
            # Hasil: 'dataset/data_komoditas_pangan/pasar_modern/final_komoditas_modern_bawang_merah_2022_2026.csv'
            file_path = os.path.join(folder_path, file_name)

            print(f"Memproses: {komoditas} - {tipe_pasar}")

            # -------------------------------------------------------------
            df = pd.read_csv(file_path)
            df_long = df.melt(
                id_vars=["Date_Param"], var_name="provinsi", value_name="harga"
            )
            df_long.rename(columns={"Date_Param": "tanggal"}, inplace=True)
            df_long["tanggal"] = pd.to_datetime(df_long["tanggal"], errors="coerce")
            df_long["harga"] = (
                df_long["harga"].astype(str).str.replace(r"[^0-9]", "", regex=True)
            )
            df_long["harga"] = pd.to_numeric(df_long["harga"], errors="coerce")
            df_long["komoditas"] = komoditas
            df_long["tipe_pasar"] = tipe_pasar
            df_long.dropna(subset=["harga"], inplace=True)
            df_long.to_sql(
                name="temp_prices",
                con=engine,
                if_exists="replace",
                index=False,
                dtype={
                    "tanggal": types.Date(),
                    "provinsi": types.VARCHAR(100),
                    "harga": types.BigInteger(),
                    "komoditas": types.VARCHAR(50),
                    "tipe_pasar": types.VARCHAR(50),
                },
            )

            # Lakukan UPSERT dari Tabel Sementara ke Tabel Utama menggunakan SQL Murni
            with engine.begin() as conn:
                upsert_query = text("""
                    INSERT INTO national_prices (tanggal, provinsi, harga, komoditas, tipe_pasar)
                    SELECT tanggal, provinsi, harga, komoditas, tipe_pasar 
                    FROM temp_prices
                    ON CONFLICT (tanggal, provinsi, komoditas, tipe_pasar) 
                    DO UPDATE SET harga = EXCLUDED.harga;
                """)
                conn.execute(upsert_query)

print("✅ SELURUH DATA BERHASIL DI-MIGRASI KE POSTGRESQL!")
