{{ config(materialized='table') }}

WITH daily_prices AS (
    SELECT
        tanggal,
        provinsi,
        komoditas,
        tipe_pasar,
        harga_bersih AS harga_hari_ini,
        harga_berubah,
        jeda_hari
    FROM {{ ref('int_bapanas_prices_enriched') }}
),

volatility_calculation AS (
    SELECT
        *,
        LAG(harga_hari_ini) OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar
            ORDER BY tanggal
        ) AS harga_kemarin
    FROM daily_prices
),

with_pct AS (
    SELECT
        *,
        (harga_hari_ini - harga_kemarin) / NULLIF(harga_kemarin, 0) AS rasio_perubahan
    FROM volatility_calculation
)

SELECT
    tanggal,
    provinsi,
    komoditas,
    tipe_pasar,
    harga_hari_ini,
    harga_kemarin,
    harga_berubah,
    jeda_hari,
    COALESCE(harga_hari_ini - harga_kemarin, 0) AS selisih_harga,
    ABS(ROUND(COALESCE(rasio_perubahan, 0) * 100, 2)) AS persentase_volatilitas_absolute,
    CASE
        WHEN NOT harga_berubah OR jeda_hari IS NULL THEN 'Stabil'
        WHEN jeda_hari > {{ var('jeda_maks_hari', 7) }} THEN 'Pembaruan Berkala'
        WHEN rasio_perubahan > 0.05 THEN 'Lonjakan Ekstrem (> 5%)'
        WHEN rasio_perubahan < -0.05 THEN 'Penurunan Ekstrem (< -5%)'
        ELSE 'Stabil'
    END AS status_volatilitas
FROM with_pct