{{ config(materialized='table') }}

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar
            ORDER BY tanggal DESC
        ) AS rn,
        MAX(tanggal) OVER () AS tanggal_data_terbaru
    FROM {{ ref('mart_daily_volatility') }}
)

SELECT
    tanggal,
    provinsi,
    komoditas,
    tipe_pasar,
    harga_hari_ini AS harga_terbaru,
    harga_kemarin AS harga_sebelumnya,
    selisih_harga,
    ROUND(
        (harga_hari_ini - harga_kemarin) / NULLIF(harga_kemarin, 0) * 100, 2
    ) AS persentase_perubahan,
    status_volatilitas,
    (tanggal = tanggal_data_terbaru) AS is_data_terkini
FROM ranked
WHERE rn = 1