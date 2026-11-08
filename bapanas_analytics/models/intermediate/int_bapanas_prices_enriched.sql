{{ config(materialized='view') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_bapanas_prices') }}
),

enriched AS (
    SELECT 
        id,
        tanggal,
        EXTRACT(YEAR FROM tanggal)::INT AS tahun,
        EXTRACT(MONTH FROM tanggal)::INT AS bulan,
        TO_CHAR(tanggal, 'YYYY-MM') AS periode,
        provinsi,
        TRIM(INITCAP(komoditas)) AS komoditas,
        TRIM(INITCAP(tipe_pasar)) AS tipe_pasar,
        ROUND(harga_mentah / 10) AS harga_mentah,
        ROUND(harga_bersih / 10) AS harga_bersih
    FROM staging
)

SELECT * FROM enriched