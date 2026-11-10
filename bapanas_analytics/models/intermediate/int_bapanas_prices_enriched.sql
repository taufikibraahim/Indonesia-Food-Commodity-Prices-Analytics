{{ config(materialized='table') }}

WITH clean AS (
    SELECT * FROM {{ ref('int_bapanas_prices_flagged') }}
    WHERE NOT is_anomali
),

changes AS (
    SELECT
        *,
        harga_mentah IS DISTINCT FROM LAG(harga_mentah) OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar ORDER BY tanggal
        ) AS harga_berubah
    FROM clean
),

runs AS (
    SELECT
        *,
        SUM(harga_berubah::INT) OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar ORDER BY tanggal
        ) AS run_id
    FROM changes
),

run_dates AS (
    SELECT
        *,
        MIN(tanggal) OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar, run_id
        ) AS tanggal_awal_harga
    FROM runs
)

SELECT
    id,
    tanggal,
    EXTRACT(YEAR FROM tanggal)::INT AS tahun,
    EXTRACT(MONTH FROM tanggal)::INT AS bulan,
    TO_CHAR(tanggal, 'YYYY-MM') AS periode,
    provinsi,
    komoditas,
    tipe_pasar,
    harga_mentah,
    harga_mentah AS harga_bersih,
    harga_berubah,
    tanggal - tanggal_awal_harga AS hari_sejak_perubahan,
    CASE
        WHEN harga_berubah THEN
            tanggal - LAG(tanggal_awal_harga) OVER (
                PARTITION BY provinsi, komoditas, tipe_pasar ORDER BY tanggal
            )
    END AS jeda_hari
FROM run_dates