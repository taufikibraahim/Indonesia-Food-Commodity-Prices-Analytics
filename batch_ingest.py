import os
import re

import pandas as pd
from sqlalchemy import create_engine, text, types

# 1. Koneksi database
engine = create_engine("postgresql://root:root@pgdatabase:5432/food_prices")

# 2. Definisikan Base Directory sesuai struktur hirarki Anda
base_dir = os.path.join("dataset", "data_komoditas_pangan")

# Daftar nama folder target di dalam base_dir
kategori_pasar = ["pasar_modern", "pasar_tradisional", "produsen"]


def parse_harga(seri: pd.Series) -> pd.Series:
    """Ubah kolom harga menjadi angka Rupiah utuh (float, NaN jika tidak valid).

    - Kolom yang sudah numerik (float/int) dipakai apa adanya.
    - Kolom teks dibersihkan: 'Rp', spasi, dan pemisah ribuan format Indonesia
      ('31.500' atau '31,500') dibuang, sedangkan tanda minus dipertahankan.
    """
    if pd.api.types.is_numeric_dtype(seri):
        return pd.to_numeric(seri, errors="coerce")

    bersih = (
        seri.astype(str)
        .str.strip()
        .str.replace(r"(?i)rp", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
        .str.replace(r"[.,](?=\d{3}(?:\D|$))", "", regex=True)  # pemisah ribuan
        .str.replace(r"[^0-9\-]", "", regex=True)
        .replace("", pd.NA)
    )
    return pd.to_numeric(bersih, errors="coerce")


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
    folder_path = os.path.join(base_dir, folder_name)
    tipe_pasar = folder_name.replace("_", " ").title()

    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} tidak ditemukan. Lewati.")
        continue

    # 4. Loop ke-2: Membaca setiap file CSV di dalam folder tersebut
    for file_name in sorted(os.listdir(folder_path)):
        if not file_name.endswith(".csv"):
            continue

        match = re.search(r"final_komoditas_[a-z]+_(.*)_2022_2026\.csv", file_name)
        if match:
            komoditas = match.group(1).replace("_", " ").title()
        else:
            komoditas = file_name.replace(".csv", "").title()

        file_path = os.path.join(folder_path, file_name)
        print(f"Memproses: {komoditas} - {tipe_pasar}")

        df = pd.read_csv(file_path)
        df_long = df.melt(
            id_vars=["Date_Param"], var_name="provinsi", value_name="harga"
        )
        df_long.rename(columns={"Date_Param": "tanggal"}, inplace=True)
        df_long["tanggal"] = pd.to_datetime(df_long["tanggal"], errors="coerce")
        df_long["harga"] = parse_harga(df_long["harga"])
        df_long["komoditas"] = komoditas
        df_long["tipe_pasar"] = tipe_pasar
        df_long = df_long.dropna(subset=["tanggal", "harga"])
        df_long["harga"] = df_long["harga"].round().astype("int64")

        sebelum = len(df_long)
        df_long = df_long.drop_duplicates(
            subset=["tanggal", "provinsi", "komoditas", "tipe_pasar"], keep="last"
        )
        if len(df_long) < sebelum:
            print(f"  ! {sebelum - len(df_long)} baris ganda dibuang")

        print(
            f"  harga min={df_long['harga'].min():,} "
            f"maks={df_long['harga'].max():,} baris={len(df_long):,}"
        )

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

        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO national_prices (tanggal, provinsi, harga, komoditas, tipe_pasar)
                SELECT tanggal, provinsi, harga, komoditas, tipe_pasar
                FROM temp_prices
                ON CONFLICT (tanggal, provinsi, komoditas, tipe_pasar)
                DO UPDATE SET harga = EXCLUDED.harga;
            """)
            )

print("✅ SELURUH DATA BERHASIL DI-MIGRASI KE POSTGRESQL!")
