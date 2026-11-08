{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('bapanas', 'national_prices') }}
),

renamed_and_casted AS (
    SELECT
        MD5(tanggal::TEXT || provinsi || komoditas || tipe_pasar) AS id,
        tanggal::DATE AS tanggal,
        TRIM(provinsi) AS provinsi,
        TRIM(komoditas) AS komoditas,
        TRIM(tipe_pasar) AS tipe_pasar,
        harga::NUMERIC AS harga_mentah,
        CASE
            WHEN harga < 0 OR harga > 500000 THEN NULL
            ELSE harga::NUMERIC
        END AS harga_bersih
    FROM source
)

SELECT * FROM renamed_and_casted
WHERE harga_bersih IS NOT NULL