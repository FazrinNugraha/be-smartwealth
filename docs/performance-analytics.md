# Performance Analytics Dashboard

Dokumen ini menjelaskan perubahan yang dibuat untuk mengganti grafik `Wealth History`
yang sebelumnya terasa kosong menjadi dashboard performance yang lebih interaktif:
portfolio chart, multi-line asset chart, winners/losers, daily return badge, dan
payload yang siap dipakai frontend.

## Ringkasan Perubahan

Backend:

- Menambahkan endpoint `GET /api/v1/dashboard/performance-analytics`.
- Menambahkan fetch harga historis per asset di `price_service`.
- Menambahkan builder analytics di `dashboard_service`.
- Tetap mempertahankan endpoint lama `GET /dashboard/wealth-history` agar tidak
  breaking untuk UI atau flow lama.

Frontend:

- Menambahkan API helper `getPerformanceAnalytics(period)`.
- Mengganti dashboard chart utama menjadi:
  - `Portfolio Performance`
  - `Asset Performance` multi-line chart, dihitung dari harga beli user
  - `Market Performance` sparkline area cards, dihitung dari harga awal periode
  - `Winners` dan `Losers`
  - tabel detail asset dengan daily return, ROI, dan weight.

## File Yang Diubah

Backend:

- `be/app/routers/dashboard.py`
- `be/app/services/dashboard_service.py`
- `be/app/services/price_service.py`

Frontend:

- `fe/src/api/dashboard.ts`
- `fe/src/pages/DashboardPage.tsx`
- `fe/src/index.css`

## Endpoint Baru

```http
GET /api/v1/dashboard/performance-analytics?period=30d
Authorization: Bearer <access_token>
```

Period yang didukung:

- `7d`
- `30d`
- `90d`
- `1y`
- `all`

Endpoint ini berada di:

```text
be/app/routers/dashboard.py
```

Handler:

```python
@router.get("/performance-analytics")
async def get_performance_analytics(...)
```

Router hanya menangani:

- membaca query `period`
- mengambil `current_user`
- inject `db`
- meneruskan request ke service:

```python
dashboard_service.get_performance_analytics(db, str(current_user.id), period)
```

## Alur Data Backend

### 1. Ambil asset user dan harga terbaru

Service utama:

```text
be/app/services/dashboard_service.py
get_performance_analytics()
```

Langkah pertama memakai helper existing:

```python
assets, prices, rate = await _fetch_assets_with_prices(db, user_id)
```

Helper ini mengambil:

- semua `UserAsset` aktif milik user
- kurs USD/IDR
- harga terbaru tiap asset

Harga terbaru diambil paralel memakai `asyncio.gather`, jadi beberapa asset tidak
diproses satu per satu secara lambat.

Sumber data:

- saham ID/US: `yfinance`
- crypto: `CoinGecko`
- gold: `yfinance` symbol `GC=F`, lalu dikonversi ke IDR/gram
- cash: static `1`

Harga terbaru tetap memakai cache existing di tabel:

```text
asset_prices
```

TTL cache harga saat ini:

```python
CACHE_TTL_MINUTES = 5
```

### 2. Build metric dasar per asset

Setelah harga terbaru ada, backend membuat metric standar:

```python
_build_asset_metric(asset, current_price, usd_idr_rate)
```

Field utama yang dihasilkan:

- `asset_id`
- `symbol`
- `asset_name`
- `asset_type`
- `currency`
- `quantity`
- `avg_buy_price`
- `current_price`
- `total_invested`
- `current_value`
- `unrealized_pnl`
- `total_invested_idr`
- `current_value_idr`
- `unrealized_pnl_idr`
- `roi`

ROI dihitung dari:

```text
((current_value - total_invested) / total_invested) * 100
```

### 3. Build portfolio history

Portfolio chart memakai tabel existing:

```text
wealth_history
```

Helper:

```python
_build_portfolio_history(db, user_id, period, current_total_idr)
```

Flow:

1. Ambil snapshot `wealth_history` sesuai period.
2. Sort ascending berdasarkan `snapshot_date`.
3. Tambahkan current snapshot hari ini dari hasil hitung real-time.
4. Hitung:
   - `start_value`
   - `end_value`
   - `change`
   - `change_percentage`
   - `return_percentage` per titik chart

Kenapa current snapshot ditambahkan?

Karena `wealth_history` hanya direkam harian oleh background job. Tanpa current
snapshot, chart bisa terasa telat atau kosong sampai job berikutnya jalan.

### 4. Ambil harga historis tiap asset

Helper public baru:

```text
be/app/services/price_service.py
get_price_history()
```

Flow per asset type:

#### Saham ID dan Saham US

```python
fetch_stock_price_history(symbol, period)
```

Memakai:

```python
yf.Ticker(symbol).history(period=..., interval="1d")
```

Contoh symbol:

- `BBCA.JK`
- `AAPL`
- `MSFT`

#### Crypto

```python
fetch_crypto_price_history(symbol, period)
```

Memakai CoinGecko:

```http
GET /coins/{symbol}/market_chart?vs_currency=usd&days=<days>
```

Untuk crypto, CoinGecko bisa mengembalikan beberapa titik intraday. Backend
menyederhanakan data menjadi satu harga terakhir per tanggal UTC.

#### Gold

Gold memakai harga historis `GC=F` dari yfinance dalam USD/troy ounce.

Lalu dikonversi:

```text
IDR per gram = (gold_usd_per_oz * usd_idr_rate) / 31.1035
```

#### Cash

Cash dibuat flat:

```text
price = 1
```

Jadi chart cash tidak naik turun.

#### Asset type lain

Untuk `mutual_fund`, `bond`, `property`, atau asset yang belum punya provider
historis, backend mengembalikan array kosong. Service dashboard lalu fallback ke
satu titik current price agar UI tetap tidak crash.

### 5. Build asset performance series

Helper:

```python
_build_asset_performance_series(...)
```

Untuk setiap asset, backend membentuk data chart:

- `date`
- `price`
- `current_value`
- `current_value_idr`
- `roi`
- `period_return_percentage`
- `position_return_percentage`

Perhitungan:

```text
period_return_percentage = (price_on_date - first_price_in_period) / first_price_in_period * 100
```

`period_return_percentage` dipakai untuk chart **Market Performance**. Baseline
field ini adalah harga pertama yang tersedia di periode chart.

```text
position_return_percentage = (price_on_date - avg_buy_price) / avg_buy_price * 100
```

`position_return_percentage` dipakai untuk chart **Asset Performance**. Baseline
field ini adalah harga beli rata-rata user, jadi garisnya menjawab posisi
investasi user sedang untung atau rugi berapa persen di tiap tanggal.

Daily change:

```text
daily_change_percentage = (latest_price - previous_price) / previous_price * 100
```

Weight:

```text
weight_percentage = current_value_idr / total_portfolio_idr * 100
```

Contribution:

```text
contribution_percentage = asset_unrealized_pnl_idr / total_pnl_idr * 100
```

### 6. Build winners dan losers

Backend sort asset berdasarkan `roi`:

```python
winners = sorted(asset_series, key=lambda x: Decimal(x["roi"]), reverse=True)[:5]
losers = sorted(asset_series, key=lambda x: Decimal(x["roi"]))[:5]
```

Ini dipakai frontend untuk panel ringkas:

- asset paling untung
- asset paling rugi

## Response Shape

Contoh response singkat:

```json
{
  "period": "30d",
  "currency": "IDR",
  "portfolio": {
    "data": [
      {
        "date": "2026-05-12",
        "total_value": "1250000.00",
        "return_percentage": "0.00"
      },
      {
        "date": "2026-05-25",
        "total_value": "1350000.00",
        "return_percentage": "8.00"
      }
    ],
    "start_value": "1250000.00",
    "end_value": "1350000.00",
    "change": "100000.00",
    "change_percentage": "8.00"
  },
  "assets": [
    {
      "asset_id": "uuid",
      "symbol": "BBCA.JK",
      "asset_name": "Bank Central Asia",
      "asset_type": "stock_id",
      "currency": "IDR",
      "quantity": "100.00000000",
      "avg_buy_price": "8500.00000000",
      "current_price": "9000.00",
      "current_value": "900000.00",
      "current_value_idr": "900000.00",
      "unrealized_pnl_idr": "50000.00",
      "roi": "5.88",
      "daily_change_percentage": "0.64",
      "period_return_percentage": "3.20",
      "position_return_percentage": "5.88",
      "weight_percentage": "40.00",
      "contribution_percentage": "55.00",
      "data": [
        {
          "date": "2026-05-12",
          "price": "8720.00",
          "current_value": "872000.00",
          "current_value_idr": "872000.00",
          "roi": "2.59",
          "period_return_percentage": "0.00",
          "position_return_percentage": "2.59"
        },
        {
          "date": "2026-05-25",
          "price": "9000.00",
          "current_value": "900000.00",
          "current_value_idr": "900000.00",
          "roi": "5.88",
          "period_return_percentage": "3.21",
          "position_return_percentage": "5.88"
        }
      ]
    }
  ],
  "movers": {
    "winners": [],
    "losers": []
  },
  "summary": {
    "total_invested": "1200000.00",
    "current_value": "1350000.00",
    "total_unrealized_pnl": "150000.00",
    "average_roi": "12.50",
    "asset_count": 3
  },
  "metadata": {
    "portfolio_source": "wealth_history_plus_current_snapshot",
    "asset_source": "market_price_history",
    "supports": [
      "portfolio_line_chart",
      "asset_position_performance_chart",
      "market_performance_chart",
      "winners_losers",
      "allocation_vs_return"
    ]
  }
}
```

## Alur Data Frontend

Urutan chart di dashboard:

1. `Portfolio Performance`
   - memakai `portfolio.data[].return_percentage`
   - baseline adalah total portfolio pada titik awal periode
2. `Your Asset Performance`
   - memakai `assets[].data[].position_return_percentage`
   - baseline adalah `avg_buy_price` user
   - selalu memakai data `30d`, supaya chart personal tidak berubah saat user
     mengganti range portfolio
   - header menampilkan `Total P/L`, `Avg ROI`, dan baseline `Avg buy`
   - tampilan diberi konteks profit/loss: area atas `0%` berarti profit, area
     bawah `0%` berarti loss
3. `Market Performance`
   - memakai `assets[].data[].period_return_percentage`
   - baseline adalah harga market pertama di periode chart
   - selalu memakai data `30d`
   - header menampilkan best dan worst market mover dalam 30 hari terakhir
   - tampil sebagai **sparkline area cards**, satu kartu mini chart per asset
   - kartu hijau berarti return market periode tersebut positif, kartu merah
     berarti negatif

### 1. API helper

File:

```text
fe/src/api/dashboard.ts
```

Helper baru:

```ts
export const getPerformanceAnalytics = async (period: string = '30d') => {
  const response = await apiClient.get(`/dashboard/performance-analytics?period=${period}`);
  return response.data;
};
```

### 2. Initial load dashboard

File:

```text
fe/src/pages/DashboardPage.tsx
```

Saat dashboard pertama dibuka:

```ts
const [summaryData, analyticsData] = await Promise.all([
  getSummary(),
  getPerformanceAnalytics(period),
]);

const performanceData = period === '30d'
  ? analyticsData
  : await getPerformanceAnalytics('30d');
```

`getSummary()` masih dipakai untuk:

- total net worth
- allocation donut
- fallback summary

`getPerformanceAnalytics()` dipakai untuk:

- portfolio chart
- asset performance chart dari harga beli user
- market performance chart dari harga awal periode
- movers
- tabel detail asset performance

Frontend menyimpan dua payload analytics:

- `analytics`: mengikuti period yang dipilih user untuk `Portfolio Performance`
- `performanceAnalytics`: selalu `30d` untuk `Your Asset Performance` dan
  `Market Performance`

### 3. Saat user ganti period

User bisa klik:

- `7d`
- `30d`
- `90d`
- `1y`
- `all`

State:

```ts
const [period, setPeriod] = useState<Period>('30d');
```

Effect:

```ts
useEffect(() => { loadAnalytics(period); }, [period]);
```

Jadi saat period berubah, frontend hanya reload analytics, bukan semua dashboard.

### 4. Portfolio chart transform

Backend mengirim:

```json
{
  "date": "2026-05-25",
  "total_value": "1350000.00",
  "return_percentage": "8.00"
}
```

Frontend mengubahnya menjadi:

```ts
{
  date: shortDate(point.date),
  returnValue: Number(point.return_percentage ?? 0),
  totalValue: Number(point.total_value),
}
```

Dipakai oleh:

```tsx
<AreaChart data={portfolioData}>
  <Area dataKey="returnValue" />
</AreaChart>
```

Tooltip tetap menampilkan:

- total value dalam IDR
- return percentage

### 5. Multi-line asset chart transform

Backend mengirim data nested per asset:

```json
{
  "asset_id": "asset-1",
  "symbol": "BBCA.JK",
  "data": [
    {
      "date": "2026-05-25",
      "period_return_percentage": "3.21",
      "position_return_percentage": "5.88"
    }
  ]
}
```

Recharts multi-line lebih enak jika data dibuat row per tanggal:

```ts
{
  date: '25 Mei',
  'asset-1': 3.21,
  'asset-2': -1.40
}
```

Transform dilakukan dengan memilih metric yang ingin digambar:

```ts
const buildAssetChartData = (
  metric: 'period_return_percentage' | 'position_return_percentage',
) => {
  const rows = new Map<string, Record<string, string | number>>();

  assets.forEach((asset) => {
    asset.data.forEach((point) => {
      const key = point.date;
      const row = rows.get(key) ?? { date: shortDate(point.date) };
      row[asset.asset_id] = Number(point[metric] ?? 0);
      rows.set(key, row);
    });
  });

  return Array.from(rows.entries())
    .sort(([a], [b]) => new Date(a).getTime() - new Date(b).getTime())
    .map(([, row]) => row);
};
```

Chart **Asset Performance** memakai:

```ts
buildAssetChartData('position_return_percentage')
```

Chart **Market Performance** memakai data yang sama, tetapi tidak digambar sebagai
multi-line chart. FE merendernya sebagai **sparkline area cards**, satu kartu per
asset:

```ts
asset.data.map((point) => ({
  date: shortDate(point.date),
  value: Number(point.period_return_percentage ?? 0),
  price: Number(point.price),
}))
```

Nilai utama di kanan atas kartu memakai:

```ts
asset.period_return_percentage
```

Lalu render line per asset:

```tsx
{visibleAssetList.map((asset) => (
  <Line
    key={asset.asset_id}
    dataKey={asset.asset_id}
    name={asset.symbol}
  />
))}
```

### 6. Toggle asset visibility

State:

```ts
const [visibleAssets, setVisibleAssets] = useState<Record<string, boolean>>({});
```

Default:

- 6 asset pertama visible
- asset berikutnya hidden dulu agar chart tidak terlalu ramai

User bisa klik chip symbol asset untuk show/hide line.

### 7. Winners dan losers

Frontend langsung memakai:

```ts
analytics.movers.winners
analytics.movers.losers
```

Tanpa perlu sort ulang di client.

### 8. Tabel asset detail

Tabel memakai field dari `analytics.assets`:

- `current_price`
- `current_value`
- `current_value_idr`
- `daily_change_percentage`
- `roi`
- `weight_percentage`

Badge harian seperti contoh gambar memakai:

```ts
daily_change_percentage
```

Jika null, tampil `-`.

## Kenapa Endpoint Baru, Bukan Ganti Wealth History Langsung?

Endpoint lama:

```http
GET /dashboard/wealth-history
```

Hanya punya:

- date
- total_value

Itu cukup untuk satu line chart sederhana, tapi tidak cukup untuk:

- grafik per asset
- daily change per asset
- winners/losers
- weight asset
- return percentage per period

Karena itu dibuat endpoint baru:

```http
GET /dashboard/performance-analytics
```

Endpoint lama tetap aman untuk backward compatibility.

## Limitasi Saat Ini

### 1. Harga historis belum disimpan di database

Saat ini harga historis asset diambil dari provider saat dashboard dibuka:

- saham: yfinance
- crypto: CoinGecko
- gold: yfinance `GC=F`

Ini sudah cukup untuk UI sekarang, tapi untuk production lebih baik dibuat tabel:

```text
asset_price_history
```

Kolom yang disarankan:

- `id`
- `symbol`
- `asset_type`
- `price`
- `currency`
- `price_date`
- `source`
- `created_at`

Lalu background job `price_updater` bisa menyimpan snapshot harga berkala.

### 2. Provider bisa rate limit

CoinGecko free API dan yfinance bisa gagal atau lambat. Saat ini fallback-nya:

- jika historical data kosong, UI tetap mendapat satu titik current price
- endpoint tidak crash karena asset yang gagal fetch tidak menggagalkan seluruh
  dashboard

### 3. Wealth history tetap bergantung background job

Portfolio chart memakai:

```text
wealth_history + current snapshot
```

Jika user baru pertama kali memakai aplikasi, history lama belum ada. Chart akan
mulai kaya setelah snapshot harian berjalan beberapa hari.

## Rekomendasi Lanjutan

Untuk membuat fitur ini makin stabil dan cepat:

1. Tambahkan tabel `asset_price_history`.
2. Ubah `price_updater_job` agar setiap update juga insert historical snapshot.
3. Tambahkan cache response analytics per user dan period, misalnya TTL 5 menit.
4. Tambahkan query param `symbols` jika nanti chart ingin filter dari backend.
5. Tambahkan endpoint khusus:

```http
GET /dashboard/asset-performance/{asset_id}
```

Untuk detail halaman per asset.

## Checklist Verifikasi

Yang sudah diverifikasi:

- Backend AST parse OK.
- Import backend OK.
- Frontend `npm run build` sukses.
- FE dev server berjalan di `http://127.0.0.1:5173`.
- Backend health OK di `http://127.0.0.1:8000/api/v1/health`.
