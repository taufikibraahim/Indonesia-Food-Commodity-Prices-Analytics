-- Tes gagal bila ada seri yang muncul lebih dari satu baris
SELECT provinsi, komoditas, tipe_pasar
FROM {{ ref('mart_latest_price_snapshot') }}
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1