{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('bapanas', 'national_prices') }}
)

SELECT 
    MD5(tanggal::TEXT || provinsi || komoditas || tipe_pasar) AS id,
    tanggal::DATE AS tanggal,
    TRIM(provinsi) AS provinsi,
    INITCAP(TRIM(komoditas)) AS komoditas,
    INITCAP(TRIM(tipe_pasar)) AS tipe_pasar,
    harga::NUMERIC AS harga_mentah
FROM source