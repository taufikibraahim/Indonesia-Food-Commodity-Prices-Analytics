{{ config(materialized='view') }}

with staging AS (
    SELECT * FROM {{ ref('stg_bapanas_prices') }}
),

batas AS (
    SELECT
        komoditas,
        tipe_pasar,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY harga_mentah) AS median_harga
    FROM staging
    WHERE harga_mentah > 0
    GROUP BY 1, 2
),

flagged AS (
    SELECT
        s.*,
        b.median_harga,
        CASE
            WHEN s.harga_mentah <= 0 THEN 'harga_nol_atau_negatif'
            WHEN s.harga_mentah > b.median_harga * 5 THEN 'terlalu_tinggi'
            WHEN s.harga_mentah < b.median_harga / 8 THEN 'terlalu_rendah'
        END alasan_anomali
    FROM staging s
    LEFT JOIN batas b
        ON s.komoditas = b.komoditas AND s.tipe_pasar = b.tipe_pasar
)

SELECT 
    *,
    (alasan_anomali IS NOT NULL) AS is_anomali
FROM flagged
