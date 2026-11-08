{{ config(materialized='table') }}

WITH daily_prices AS (
    SELECT 
        tanggal,
        provinsi,
        komoditas,
        tipe_pasar,
        harga_bersih AS harga_hari_ini
    FROM {{ ref('int_bapanas_prices_enriched') }}
),

volatility_calculation AS (
    SELECT
        tanggal,
        provinsi,
        komoditas,
        tipe_pasar,
        harga_hari_ini,
        LAG(harga_hari_ini) OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar 
            ORDER BY tanggal 
        ) AS harga_kemarin
    FROM daily_prices
)

SELECT 
    tanggal,
    provinsi,
    komoditas,
    tipe_pasar,
    harga_hari_ini,
    harga_kemarin,
    CASE
        WHEN harga_kemarin IS NULL THEN 0
        ELSE (harga_hari_ini - harga_kemarin)
    END AS selisih_harga,
    ABS(CASE 
        WHEN harga_kemarin IS NULL OR harga_kemarin = 0 THEN 0
        ELSE ROUND((((harga_hari_ini - harga_kemarin) / harga_kemarin) * 100), 2)
    END) AS persentase_volatilitas_absolute,
    CASE 
        WHEN (harga_hari_ini - harga_kemarin) / NULLIF(harga_kemarin, 0) > 0.05 THEN 'Lonjakan Ekstrem (> 5%)'
        WHEN (harga_hari_ini - harga_kemarin) / NULLIF(harga_kemarin, 0) < -0.05 THEN 'Penurunan Ekstrem (< -5%)'
        ELSE 'Stabil'
    END AS status_volatilitas
FROM volatility_calculation
ORDER BY tanggal DESC, persentase_volatilitas_absolute DESC