# Model Prediksi Saham IDX - Dokumentasi Teknis

Dokumentasi lengkap tentang model prediksi saham yang dibangun di `stock_prediction_colab.ipynb`.

## Ringkasan

Service prediksi harga saham Indonesia (semua ticker IDX yang ada di Yahoo Finance) untuk horizon 1-7 hari ke depan. Model dilatih on-the-fly setiap kali ada request, menghasilkan prediksi berupa arah pergerakan (naik/turun/sideways) dan rentang harga (lower bound, median, upper bound).

## Pendekatan Model

### Algoritma: LightGBM Quantile Regression

Memilih **gradient boosting (LightGBM)** dengan **quantile loss** alih-alih neural network atau ARIMA. Pertimbangan:

| Aspek            | Alasan                                                                                         |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| Akurasi          | Gradient boosting outperform LSTM untuk financial time series jangka pendek dengan data harian |
| Latency          | Training cepat (detik), tidak perlu GPU                                                        |
| Interpretability | Bisa lihat feature importance kalau perlu debug                                                |
| Resource         | Berjalan di CPU biasa, model file kecil                                                        |
| Quantile native  | LightGBM support quantile loss out-of-the-box untuk hasilkan range                             |

### Strategi: Multi-step Direct Forecasting

Untuk setiap ticker, dilatih **21 model terpisah**:

- 7 horizon (1, 2, 3, 4, 5, 6, 7 hari) × 3 quantile (0.1, 0.5, 0.9) = 21 model

Pendekatan **direct multi-step forecasting**: tiap horizon punya model sendiri yang langsung prediksi h hari ke depan. Lebih akurat dari recursive forecasting (predict 1 hari, masukin sebagai input, predict lagi) yang error-nya numpuk.

### Target Variable: Log Return

```
target_h = log(close[t+h] / close[t])
```

Bukan harga absolut. Alasannya:

1. **Stationary**: log return relatif lebih stabil distribusinya dibanding harga absolut yang trending
2. **Symmetric**: 10% naik dan 10% turun di-treat simetris (log scale)
3. **Standard practice** di financial modeling

Saat inference, di-convert balik:

```
predicted_price = last_close * exp(predicted_log_return)
```

### Quantile Regression untuk Range Harga

Untuk hasilkan range harga (bukan single point estimate), pakai **quantile loss**:

| Quantile | Output      | Interpretasi                                                   |
| -------- | ----------- | -------------------------------------------------------------- |
| 0.1      | Lower bound | Harga konservatif/pesimis (10% kemungkinan harga di bawah ini) |
| 0.5      | Median      | Estimate tengah (titik tengah sebaran prediksi)                |
| 0.9      | Upper bound | Harga optimis (10% kemungkinan harga di atas ini)              |

Ini lebih honest dibanding single number karena pasar saham noisy. User dapat **interval ~80%** kemungkinan harga akan jatuh di rentang `[lower, upper]`.

**Quantile crossing fix**: kadang gradient boosting hasilkan `lower > median > upper` yang inkonsisten karena tiap quantile dilatih terpisah. Output di-sort untuk pastikan `lower ≤ median ≤ upper`.

### Direction Classification

Direction (naik/turun/sideways) ditentukan dari median price:

```
pct_change = (median_predicted - last_close) / last_close * 100

if pct_change > 0.5%   -> "naik"
if pct_change < -0.5%  -> "turun"
else                   -> "sideways"
```

Threshold 0.5% untuk classify sebagai sideways karena pergerakan di bawah threshold itu biasanya cuma noise pasar harian, bukan signal arah yang jelas.

## Feature Engineering

Total 45 feature di-extract dari OHLCV (Open, High, Low, Close, Volume). Semua feature **dinormalisasi terhadap close price** supaya model bisa generalize across saham dengan range harga berbeda (BBCA Rp 9000-an vs GOTO Rp 50-an).

### 1. Returns

| Feature                                  | Formula                       | Tujuan                                         |
| ---------------------------------------- | ----------------------------- | ---------------------------------------------- |
| `return_1`, `return_2`, ..., `return_10` | `close.pct_change(n)`         | Capture momentum jangka pendek                 |
| `log_return_1`                           | `log(close / close.shift(1))` | Log version untuk stabilitas numerik           |
| `open_gap`                               | `open / close.shift(1) - 1`   | Capture gap pembukaan vs close hari sebelumnya |
| `intraday_return`                        | `close / open - 1`            | Capture tekanan beli/jual intraday             |

### 2. Lagged Price Ratios

```
price_ratio_n = close[t-n] / close[t]
```

Lag 1, 2, 3, 5, 10, 20 hari. Ratio (bukan absolute) supaya scale-invariant.

### 3. Rolling Statistics

Window 5, 10, 20 hari, semua dinormalisasi terhadap close:

- `roll_mean_w` - moving average
- `roll_std_w` - rolling standard deviation
- `roll_min_w` - rolling minimum
- `roll_max_w` - rolling maximum

### 4. Volatility

```
volatility_w = std(log_return_1) over rolling window w
```

Window 5, 10, 20. Capture fluktuasi pasar.

### 5. Technical Indicators

Pakai library `ta` (Technical Analysis):

| Indicator       | Window    | Apa Yang Diukur                               |
| --------------- | --------- | --------------------------------------------- |
| RSI             | 14        | Momentum (overbought > 70, oversold < 30)     |
| MACD            | 12/26/9   | Trend-following momentum (macd, signal, diff) |
| Bollinger Bands | 20, 2 std | Volatility & posisi relatif (pband, wband)    |
| ATR             | 14        | Average True Range, volatility absolut        |
| Stochastic      | 14        | Momentum vs price range (%K, %D)              |
| OBV             | -         | On-Balance Volume, smart money indicator      |

### 6. Volume Features

- `vol_ratio_5`, `vol_ratio_20` - rasio volume terhadap rata-rata 5/20 hari
- `vol_change_1` - perubahan volume hari ini vs kemarin
- `obv_norm` - normalisasi OBV via 5-day pct change

### 7. Calendar Features

- `dow` - day of week (Senin biasa beda dari Jumat)
- `dom` - day of month (akhir bulan ada window dressing effect)
- `month` - month (capture seasonality tahunan)

## Hyperparameters

Sensible defaults yang sudah cukup untuk MVP. Tidak ada hyperparameter tuning per ticker (overkill untuk on-the-fly).

```python
{
    "objective": "quantile",
    "alpha": <0.1 | 0.5 | 0.9>,
    "metric": "quantile",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "n_estimators": 300
}
```

## Data Pipeline

### Sumber Data: yfinance (Yahoo Finance)

- Period default: **3 tahun history**
- Adjustment: `auto_adjust=True` untuk handle stock split & dividend
- Granularity: daily (close-to-close)
- Suffix `.JK` otomatis ditambahkan untuk ticker IDX (BBCA → BBCA.JK)

### Anti-rate-limit

Yahoo Finance sering memblokir request dengan User-Agent default Python. Untuk bypass:

1. **`curl_cffi` session** yang impersonate Chrome browser
2. **Retry logic** 3x dengan exponential backoff
3. **`Ticker.history()`** instead of `yf.download()` (lebih reliable per single ticker)

### Validasi Data

Saham dianggap **tidak bisa diprediksi** kalau:

- Ticker tidak ada di yfinance (error 404)
- Data history < 252 baris (~1 tahun trading day) - saham baru IPO atau likuiditas rendah (error 422)

## Output Format

Schema response saat sukses:

```json
{
  "ticker": "BBCA.JK",
  "last_close": 9500,
  "last_close_date": "2026-05-26",
  "horizon_days": 2,
  "prediction_date": "2026-05-28",
  "direction": "turun",
  "predicted_price": {
    "lower": 9350,
    "median": 9420,
    "upper": 9510
  },
  "change_percent": {
    "lower": -1.58,
    "median": -0.84,
    "upper": 0.11
  },
  "generated_at": "2026-05-26T10:30:00Z",
  "disclaimer": "Prediksi ini ... bukan rekomendasi investasi ..."
}
```

### Field Description

| Field                    | Type                  | Description                                               |
| ------------------------ | --------------------- | --------------------------------------------------------- |
| `ticker`                 | string                | Ticker dengan suffix `.JK`                                |
| `last_close`             | number                | Harga close terakhir (acuan)                              |
| `last_close_date`        | string (YYYY-MM-DD)   | Tanggal close terakhir                                    |
| `horizon_days`           | int                   | Jumlah hari prediksi (1-7)                                |
| `prediction_date`        | string (YYYY-MM-DD)   | Tanggal prediksi (skip weekend, tidak handle libur bursa) |
| `direction`              | enum                  | `naik` \| `turun` \| `sideways`                           |
| `predicted_price.lower`  | number                | Lower bound (quantile 10%)                                |
| `predicted_price.median` | number                | Median estimate (quantile 50%)                            |
| `predicted_price.upper`  | number                | Upper bound (quantile 90%)                                |
| `change_percent.*`       | number                | Persentase perubahan vs `last_close`                      |
| `generated_at`           | string (ISO 8601 UTC) | Timestamp prediksi dibuat                                 |
| `disclaimer`             | string                | Disclaimer wajib ditampilkan di FE                        |

## Limitasi Model

Penting di-aware sebelum integrasi ke produk:

1. **Akurasi terbatas**: prediksi saham inherently noisy. Jangan jual ke user sebagai "akurat 100%".
2. **Out-of-sample performance bervariasi** per ticker dan kondisi pasar. Saham volatile (small cap) biasanya lebih sulit diprediksi dari blue chip.
3. **No regime change handling**: model tidak detect black swan event atau perubahan struktur pasar (krisis, kebijakan baru, dll).
4. **No corporate action awareness** beyond stock split/dividend adjustment dari yfinance.
5. **Calendar simplification**: `prediction_date` cuma skip weekend, tidak handle hari libur bursa Indonesia.
6. **Latency**: ~5-10 detik per request karena training on-the-fly. Tidak cocok untuk high-throughput / real-time trading.
7. **No model evaluation per request**: tidak ada metrics seperti MAE/MAPE di response. Kalau perlu, harus tambah backtesting endpoint terpisah.
8. **Kemungkinan bias overfitting** karena tidak ada validation split selama training (semua data dipakai untuk fit).

## Cara Integrasi ke FastAPI

### Struktur Modul yang Direkomendasikan

```
your-fastapi-project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + endpoint
│   ├── predictor.py         # Logic prediksi (copy dari notebook)
│   ├── schemas.py           # Pydantic models untuk request/response
│   └── exceptions.py        # Custom exception classes
├── requirements.txt
└── README.md
```

### Yang Perlu Di-extract dari Notebook

Pindahkan ke `predictor.py`:

1. Config constants (`HISTORY_PERIOD`, `MIN_DATA_POINTS`, `MAX_HORIZON`, `QUANTILES`, `DISCLAIMER`)
2. `normalize_ticker()`
3. `_make_yf_session()` & `fetch_stock_data()` (Cell 5)
4. `build_features()` (Cell 6)
5. `StockPredictor` class (Cell 7)
6. `_next_business_date()` & `format_prediction()` (Cell 8)
7. `predict_stock()` entry point (Cell 9)

### Endpoint yang Disarankan

| Method | Path                                     | Description             | Latency |
| ------ | ---------------------------------------- | ----------------------- | ------- |
| GET    | `/health`                                | Health check            | <10ms   |
| GET    | `/api/v1/predictions/{ticker}?horizon=N` | Prediksi harga (N=1..7) | 5-10s   |

### Contoh Request/Response

**Request:**

```
GET /api/v1/predictions/BBCA?horizon=2
```

**Success (200):**

```json
{
  "ticker": "BBCA.JK",
  "last_close": 9500,
  ...
}
```

**Error - Ticker tidak ditemukan (404):**

```json
{
  "error_code": "TICKER_NOT_FOUND",
  "message": "Tidak ada data untuk WBSAA.JK...",
  "details": { "ticker": "WBSAA.JK" }
}
```

**Error - Data tidak cukup (422):**

```json
{
  "error_code": "INSUFFICIENT_DATA",
  "message": "Data WBSA.JK hanya 33 baris (minimal 252)...",
  "details": {
    "ticker": "WBSA.JK",
    "actual_rows": 33,
    "required_rows": 252
  }
}
```

**Error - Horizon invalid (400):**

```json
{
  "error_code": "INVALID_HORIZON",
  "message": "Horizon harus 1..7, dapat 10",
  "details": { "horizon": 10, "max_horizon": 7 }
}
```

### Error Code Mapping (untuk FE)

Saran custom exception class dengan structured error code, supaya FE React kamu bisa map error ke UX yang tepat:

| Error Code          | HTTP Status | Penyebab                     | UX Suggestion di FE                                                 |
| ------------------- | ----------- | ---------------------------- | ------------------------------------------------------------------- |
| `TICKER_NOT_FOUND`  | 404         | Ticker tidak ada di yfinance | "Kode saham tidak valid. Cek lagi (contoh: BBCA, TLKM)."            |
| `INSUFFICIENT_DATA` | 422         | History < 1 tahun            | "Saham ini baru IPO atau likuiditas rendah, belum bisa diprediksi." |
| `INVALID_HORIZON`   | 400         | Horizon di luar 1-7          | Validate di FE sebelum submit                                       |
| `RATE_LIMITED`      | 503         | yfinance throttle            | "Server sibuk, coba lagi sebentar."                                 |
| `INTERNAL_ERROR`    | 500         | Bug server                   | "Terjadi kesalahan. Tim sudah dinotifikasi."                        |

### Hal Yang Perlu Diperhatikan

1. **CORS**: pastikan allow origin domain FE React kamu (misal `http://localhost:3000`, atau domain production)
2. **Timeout**: set timeout request di FE minimal 15-20 detik karena latency 5-10 detik
3. **Loading state**: tampilin loading indicator yang jelas di FE karena user akan menunggu beberapa detik
4. **Rate limiting**: pertimbangkan tambah rate limit per IP di FastAPI (pakai `slowapi`) supaya user tidak spam request
5. **Caching (optional, post-MVP)**: kalau traffic naik, cache result per `(ticker, horizon, date)` selama 1-24 jam
6. **Logging**: log tiap request (ticker, horizon, latency, success/error) untuk monitoring
7. **Disclaimer**: WAJIB tampilkan disclaimer di FE setiap kali prediksi muncul

### Dependencies untuk FastAPI Service

```
fastapi
uvicorn[standard]
pydantic
yfinance
curl_cffi
lightgbm
ta
pandas
numpy
```

### Cara Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Akses Swagger UI di `http://localhost:8000/docs` untuk test endpoint interaktif.

## Pengembangan Selanjutnya

Kalau MVP sudah running dan kamu mau iterate:

1. **Caching**: tambahkan in-memory cache (`cachetools`) atau Redis dengan TTL 1-24 jam per ticker untuk kurangi latency dan beban yfinance
2. **Backtest endpoint**: `/backtest/{ticker}` yang return historical accuracy (MAE, MAPE, directional accuracy) supaya user tahu reliability model
3. **Confidence score**: hitung skor confidence berdasarkan width interval prediksi atau historical hit rate
4. **Feature importance**: expose feature importance per prediksi untuk transparency
5. **Hyperparameter tuning**: per-ticker tuning kalau mau akurasi lebih baik (tradeoff: latency naik)
6. **Model comparison**: tambah baseline (Prophet, ARIMA) dan tampilkan ensemble
7. **Multi-source data**: kombinasi yfinance dengan IDX official, RTI, atau Stockbit API
8. **Macro features**: tambah feature dari indeks (IHSG, JCI), forex (USD/IDR), atau sektor
9. **Sentiment analysis**: scrape news / social media untuk feature sentiment
10. **Alert system**: kasih webhook/email kalau prediksi extreme (misal predicted change > 10%)
