{{ config(materialized='table') }}

WITH monthly_avg AS (
    SELECT 
        tahun,
        bulan,
        periode,
        provinsi,
        komoditas,
        tipe_pasar,
        ROUND(AVG(harga_bersih) , 2) AS avg_harga
    FROM {{ ref('int_bapanas_prices_enriched') }}
    GROUP BY 1, 2, 3, 4, 5, 6
),

mom_calculation AS (
    SELECT
        tahun,
        bulan,
        periode,
        provinsi,
        komoditas,
        tipe_pasar,
        avg_harga,
        LAG(avg_harga) OVER (
            PARTITION BY provinsi, komoditas, tipe_pasar 
            ORDER BY tahun, bulan
        ) AS avg_harga_bulan_sebelumnya
    FROM monthly_avg
)

SELECT 
    tahun,
    bulan,
    periode,
    provinsi,
    komoditas,
    tipe_pasar,
    avg_harga,
    avg_harga_bulan_sebelumnya,
    CASE 
        WHEN avg_harga_bulan_sebelumnya IS NULL THEN 0
        ELSE ROUND((((avg_harga - avg_harga_bulan_sebelumnya) / avg_harga_bulan_sebelumnya) * 100), 2)
    END AS presentase_perubahan_avg_harga
FROM mom_calculation
ORDER BY provinsi, komoditas, tipe_pasar, tahun DESC, bulan DESC