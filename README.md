# Indonesia Food Commodity Price Analytics

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-FF694B?logo=dbt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![Kestra](https://img.shields.io/badge/Kestra-6047EC)

Pipeline ELT untuk harga 10 komoditas pangan strategis di 34 provinsi Indonesia (2022-2026):ingestion idempoten ke PostgresSQL, tranformasi berlapis dengan dbt, orkestrasi dengan Kestra, dan dashboard Streamlit untuk analisis volatilitas harga.

> Proyek portofolio data engineering. Data bersifat **statis (historis)**, bukan aliran data real-time.

## Ringkasan

|         |                                                                                     |
| ------- | ----------------------------------------------------------------------------------- |
| Cakupan | 10 komoditas, 34 provinsi, 3 tipe pasar (Pasar Modern, Pasar Tradisional, Produsen) |
| Periode | Januari 2022 sampai <tanggal akhir data, isi dari datamu>                           |
| Volume  | 1.354.641 baris harga harian                                                        |
| Stack   | Python, PostgreSQL, dbt, Kestra, Docker Compose, Streamlit                          |

## Pertanyaan yang Dijawab

- Komoditas dan provinsi mana yang paling volatil?
- Bagaimana pergerakan harga rata-rata bulanan dan tren musimannya?
- Seberapa besar disparitas harga antar provinsi?

## Arsitektur

```
Dataset Kaggle (CSV, format wide)
        |
        v
batch_ingest.py  (melt ke format long, validasi, upsert)
        |
        v
PostgreSQL: national_prices  (raw)
        |
        v   dbt
stg_bapanas_prices            rename, cast, normalisasi teks
        |
int_bapanas_prices_flagged    penanda anomali harga
        |
int_bapanas_prices_enriched   harga_berubah, hari_sejak_perubahan, jeda_hari
        |
mart_daily_volatility         volatilitas harian
mart_monthly_commodity_trend  tren bulanan
mart_latest_price_snapshot    harga terakhir per seri
        |
        v
Dashboard Streamlit

Orkestrasi: Kestra menjalankan ingestion lalu dbt build (manual)
```

| Lapisan       | Alat                               | Fungsi                                                 |
| ------------- | ---------------------------------- | ------------------------------------------------------ |
| Ingestion     | Python (pandas, SQLAlchemy)        | Membaca CSV, mengubah ke format long, upsert idempoten |
| Penyimpanan   | PostgreSQL 13                      | Tabel mentah `national_prices`                         |
| Transformasi  | dbt (staging, intermediate, marts) | Pembersihan, penanda anomali, metrik volatilitas       |
| Orkestrasi    | Kestra                             | Alur ingestion lalu `dbt build`                        |
| Visualisasi   | Streamlit + Plotly                 | Dashboard interaktif                                   |
| Infrastruktur | Docker Compose                     | PostgreSQL, pgAdmin, Kestra                            |

## Sumber Data

- **Dataset:** [Indonesia PIHPS Food Commodity Prices Dataset](https://www.kaggle.com/datasets/muhyusuf1112/indonesia-commodity-price-based-piphs-source) oleh muhyusuf1112 di Kaggle.
- **Sumber asli:** Pusat Informasi Harga Pangan Strategis (PIHPS), Bank Indonesia (`bi.go.id/hargapangan`).
- **Lisensi:** MIT
- **Berkas yang dipakai:** `final_komoditas_<tipe>_<komoditas>_2022_2026.csv`, berformat wide (satu kolom per provinsi). Berkas yang dipakai: final*komoditas*<tipe>\_<komoditas>\_2022_2026.csv, disediakan dalam dataset Kaggle tersebut, berformat wide (satu kolom per provinsi).

```
dataset/data_komoditas_pangan/
├── pasar_modern/
├── pasar_tradisional/
└── produsen/
```

## Cara Menjalankan

Prasyarat: Docker dan Docker Compose, Python 3.12 (untuk dashboard).

```bash
# 1. Konfigurasi
cp .env.example .env          # lalu isi nilainya

# 2. Jalankan PostgreSQL, pgAdmin, dan Kestra
docker compose up -d

# 3. Build image ingestion dan dbt
docker build -t food_price_ingestor:v1 .
docker build -f Dockerfile.dbt -t food_price_dbt:v1 .

# 4. Ingestion lalu transformasi
docker run --rm --env-file .env --network food-price-etl_default food_price_ingestor:v1
docker run --rm --env-file .env --network food-price-etl_default food_price_dbt:v1
```

Atau jalankan keduanya lewat Kestra: buka `http://localhost:8082`, impor flow dari `flows/bapanas_batch_ingestion.yml`, lalu klik **Execute**.

| Layanan    | Alamat                |
| ---------- | --------------------- |
| Kestra     | http://localhost:8082 |
| pgAdmin    | http://localhost:8081 |
| PostgreSQL | localhost:5432        |

Dashboard (membutuhkan `.streamlit/secrets.toml` berisi kredensial database):

```bash
pip install -r requirements.txt
streamlit run app.py
```

Variabel lingkungan yang dibutuhkan didaftar di `.env.example`. Berkas `.env` tidak pernah di-commit.

## Pemodelan Data

| Model                          | Layer        | Fungsi                                                                                    |
| ------------------------------ | ------------ | ----------------------------------------------------------------------------------------- |
| `stg_bapanas_prices`           | Staging      | Cerminan 1:1 tabel mentah: rename, cast tipe, `TRIM`, `INITCAP`. Tanpa JOIN atau agregasi |
| `int_bapanas_prices_flagged`   | Intermediate | Menandai anomali harga relatif terhadap median per komoditas dan tipe pasar               |
| `int_bapanas_prices_enriched`  | Intermediate | Menyaring anomali, menambah `harga_berubah`, `hari_sejak_perubahan`, `jeda_hari`          |
| `mart_daily_volatility`        | Mart         | Perubahan harga harian dan status volatilitas                                             |
| `mart_monthly_commodity_trend` | Mart         | Rata-rata harga bulanan dan perubahan month-over-month                                    |
| `mart_latest_price_snapshot`   | Mart         | Satu baris per seri (provinsi, komoditas, tipe pasar) berisi harga terakhir               |

## Temuan Kualitas Data

Pemeriksaan data (profiling) menghasilkan beberapa temuan yang memengaruhi desain pipeline.

### 1. Harga membengkak 10x saat ingestion (sudah diperbaiki)

Pembersihan awal mengubah angka desimal menjadi string lalu membuang semua karakter non-digit, sehingga `31500.0` menjadi `315000`. Kini kolom numerik diparse langsung dengan `pd.to_numeric`.

### 2. Anomali harga ditandai, tidak dibuang

Sebelumnya baris anomali dibuang diam-diam dengan batas tunggal untuk semua komoditas. Kini harga ditandai sebagai anomali bila **lebih dari 5 kali** atau **kurang dari 1/8** median komoditas pada tipe pasar yang sama. Batas bawah dibuat lebih longgar karena harga komoditas musiman seperti cabai dapat anjlok tajam saat panen.

| Komoditas   | Tipe pasar   | Alasan                                                   | Jumlah baris |
| ----------- | ------------ | -------------------------------------------------------- | ------------ |
| Gula Pasir  | Pasar Modern | Terlalu tinggi (91.000-605.500, median sekitar 16.700)   | 43           |
| Daging Sapi | Pasar Modern | Terlalu rendah (semuanya 16.900, median sekitar 166.000) | 7            |
| Daging Ayam | Pasar Modern | Terlalu rendah (semuanya 3.500, median sekitar 42.900)   | 7            |

Total 57 baris dari 1.354.641 (0,004%). Penyebab pasti tidak diketahui, sehingga baris ini ditandai dan dikecualikan dari mart tetapi tetap tersimpan.

### 3. Sebagian besar baris berisi harga yang tidak berubah dari hari sebelumnya

Pada banyak seri, harga identik selama berhari-hari hingga berminggu-minggu. Persentase hari dengan harga yang tidak berubah per tipe pasar:

| Tipe pasar        | Kisaran |
| ----------------- | ------- |
| Produsen          | 94-98%  |
| Pasar Modern      | 86-94%  |
| Pasar Tradisional | 39-88%  |

Penyebabnya belum diverifikasi. Dugaannya pengisian nilai kosong di tahap pengolahan data sumber, tetapi dugaan ini belum terbukti dan tidak dipastikan oleh deskripsi dataset. Dampaknya: saat harga berganti, selisihnya tampil seperti lonjakan satu hari padahal merupakan akumulasi beberapa hari.

Penanganan: kolom `jeda_hari` mencatat berapa hari harga sebelumnya bertahan. Perubahan setelah lebih dari 7 hari diberi label **Pembaruan Berkala**, bukan lonjakan. Ambang ini dapat diubah:

```bash
dbt build --vars "{jeda_maks_hari: 3}"
```

Hasil status volatilitas:

| Status                    | Jumlah    | Persentase |
| ------------------------- | --------- | ---------- |
| Stabil                    | 1.299.542 | 95,9%      |
| Pembaruan Berkala         | 31.300    | 2,3%       |
| Lonjakan Ekstrem (> 5%)   | 12.749    | 0,9%       |
| Penurunan Ekstrem (< -5%) | 10.993    | 0,8%       |

### 4. Perubahan pola harga pada beberapa seri

Contoh cabai rawit, Pasar Modern, Nusa Tenggara Timur: sampai Februari 2022 harga berupa angka bulat yang bertahan berminggu-minggu (15.900, 37.900, 59.900), lalu berubah setiap hari dengan angka tidak bulat. Ini menunjukkan metode pencatatan yang kemungkinan berubah, sehingga volatilitas awal dan akhir periode tidak sepenuhnya sebanding.

### 5. Cakupan data tidak merata

Jumlah baris per seri tidak seragam. Bawang Putih (Produsen) hanya sekitar 3.000 baris, sedangkan banyak seri lain sekitar 48.000-50.000.

## Pengujian

Kualitas data dijaga dengan tes dbt: `unique`, `not_null`, `accepted_values` (tipe pasar, alasan anomali, status volatilitas), dan tes singular untuk memastikan satu baris per seri pada snapshot harga terakhir.

```bash
cd bapanas_analytics
dbt build      # membangun model sekaligus menjalankan tes
```

Rekonsiliasi: jumlah baris `national_prices` (1.354.641) dikurangi 57 baris anomali sama dengan jumlah baris `mart_daily_volatility` (1.354.584).

Idempotensi: ingestion memakai constraint `UNIQUE (tanggal, provinsi, komoditas, tipe_pasar)` dan `ON CONFLICT DO UPDATE`. Menjalankannya berulang, termasuk lewat Kestra, tidak menambah baris.

## Struktur Repositori

```
.
├── batch_ingest.py             # ingestion batch
├── app.py                      # dashboard Streamlit
├── Dockerfile                  # image ingestion
├── Dockerfile.dbt              # image dbt
├── docker-compose.yml          # PostgreSQL, pgAdmin, Kestra
├── docker/dbt/profiles.yml     # profil dbt untuk container
├── flows/                      # flow Kestra
├── bapanas_analytics/          # proyek dbt
│   ├── models/{staging,intermediate,marts}/
│   └── tests/
├── .env.example
└── requirements.txt
```

## Keterbatasan

- Data statis dari dataset Kaggle, tidak ada pembaruan otomatis. Flow Kestra dijalankan manual untuk backfill.
- Penyebab harga yang tidak berubah belum diverifikasi (lihat Temuan Kualitas Data).
- Ambang anomali (5x dan 1/8 median) dan ambang jeda (7 hari) adalah keputusan yang dapat diubah, bukan kebenaran mutlak.
- Konfigurasi kredensial dirancang untuk pengembangan lokal. Untuk lingkungan produksi gunakan secret manager.
- Kestra memakai akses ke Docker socket dengan hak root, hanya cocok untuk pengembangan lokal.
- Dashboard sedang dalam proses pengembangan ulang.

## Rencana Pengembangan

- [ ] Desain ulang dashboard memakai status volatilitas dan `mart_latest_price_snapshot`
- [ ] GitHub Actions: lint, tes, dan `dbt build`
- [ ] Model dimensi (`dim_komoditas`, `dim_wilayah`, `dim_tanggal`) sebagai star schema
- [ ] Analisis musiman (Ramadan dan Idulfitri)
- [ ] Penyimpanan lapisan raw dalam format Parquet

## Author

Taufik Ibrahim, Linkedin: [taufikibraahim](https://www.linkedin.com/in/taufikibraahim)
