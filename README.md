# SmartWealth Backend

FastAPI backend untuk SmartWealth — multi-asset portfolio tracker dengan real-time prices dan AI insights.

---

## Quick Start

```bash
# 1. Setup virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup .env (lihat .env section di bawah)

# 4. Run migrations (kalau pertama kali)
alembic upgrade head

# 5. Start server
python -m uvicorn app.main:app --reload
```

Server jalan di **http://localhost:8000**.
API docs: **http://localhost:8000/docs** (Swagger UI).

---

## Project Structure

```
be/
├── app/
│   ├── main.py              # FastAPI app, exception handlers, scheduler startup
│   ├── config.py            # Settings dari .env (Pydantic Settings)
│   ├── database.py          # Async SQLAlchemy engine & session factory
│   │
│   ├── models/              # SQLAlchemy ORM models (DB tables)
│   │   ├── user.py          #   User, RefreshToken
│   │   ├── asset.py         #   UserAsset (portfolio holdings)
│   │   ├── transaction.py   #   Transaction (BUY/SELL history)
│   │   ├── price.py         #   AssetPrice (price cache), InsightCache
│   │   └── wealth.py        #   WealthHistory (daily snapshot)
│   │
│   ├── schemas/             # Pydantic request/response models
│   │   ├── auth.py          #   Register, Login, Token, GoogleAuth
│   │   ├── user.py          #   UserResponse, UserUpdate
│   │   ├── asset.py         #   AssetCreate, AssetResponse, AssetUpdate
│   │   ├── transaction.py   #   TransactionCreate, TransactionResponse
│   │   ├── dashboard.py     #   NetWorth, Allocation, Performance, WealthHistory
│   │   └── insight.py       #   InsightResponse
│   │
│   ├── routers/             # API endpoint definitions
│   │   ├── auth.py          #   /auth/* — register, login, refresh, Google OAuth
│   │   ├── users.py         #   /users/me
│   │   ├── assets.py        #   /assets/* — CRUD assets
│   │   ├── transactions.py  #   /transactions/* — record buy/sell
│   │   ├── prices.py        #   /prices/{symbol} — fetch real-time price
│   │   ├── dashboard.py     #   /dashboard/* — net worth, allocation, performance
│   │   └── insights.py      #   /insights/* — rule-based & AI insights
│   │
│   ├── services/            # Business logic (orchestration & rules)
│   │   ├── auth_service.py        # Bcrypt, JWT, Google OAuth flow
│   │   ├── asset_service.py       # Asset CRUD logic
│   │   ├── transaction_service.py # BUY/SELL + auto recalc avg_buy_price
│   │   ├── price_service.py       # Fetch prices (yfinance, CoinGecko) + cache
│   │   ├── dashboard_service.py   # Net worth, allocation, performance + USD/IDR
│   │   ├── calculator.py          # Pure math: ROI, P&L, allocation %
│   │   ├── insight_engine.py      # Rule-based portfolio insights
│   │   └── ai_service.py          # Gemini AI integration + cache
│   │
│   ├── tasks/               # Background jobs (APScheduler)
│   │   ├── price_updater.py       # Refresh price cache every 5 min
│   │   └── wealth_snapshot.py     # Save daily net worth snapshot at 00:00
│   │
│   └── utils/               # Generic helpers
│       ├── constants.py     #   App constants
│       ├── currency.py      #   infer_currency, currency symbols
│       ├── exceptions.py    #   Custom HTTPException subclasses
│       └── security.py      #   get_current_user dependency
│
├── alembic/                 # DB migrations
│   ├── versions/            #   Migration scripts
│   └── env.py               #   Alembic config
│
├── tests/                   # Manual test scripts (jalan via `python tests/<file>.py`)
├── .env                     # Secrets — JANGAN di-commit
├── .env.example             # Template untuk .env
├── requirements.txt         # Python dependencies
└── alembic.ini              # Alembic config
```

---

## Architecture

### Request Flow

```
Client → Router → Service → Model → Database
                     ↓
              External APIs (yfinance, CoinGecko, Gemini)
```

- **Routers** hanya validate input/output dan delegate ke services
- **Services** berisi semua business logic — bisa dipanggil dari router atau task
- **Models** murni SQLAlchemy table definitions
- **Schemas** murni Pydantic untuk validation

### Performance Layer

- **Price cache** (DB): TTL 5 menit, stale-while-revalidate pattern
- **Dashboard cache** (in-memory): TTL 30 detik, invalidated saat asset/transaction berubah
- **Parallel fetching** via `asyncio.gather` — 5 asset prices dalam ~2 detik

### Security

- **Password**: bcrypt rounds=10 (~100ms), verify dijalankan di thread pool
- **JWT**: access token 15 menit, refresh token 7 hari (rotated)
- **Refresh tokens**: disimpan di DB, bisa di-revoke saat logout

---

## Environment Variables

Buat file `.env` di root `be/`:

```env
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname?sslmode=require

# JWT
JWT_SECRET_KEY=<random-256-bit-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth (optional, untuk login Google)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/callback

# Gemini AI (optional, untuk AI insights)
GEMINI_API_KEY=...

# App
APP_ENV=development
FRONTEND_URL=http://localhost:5173
```

---

## Common Commands

```bash
# Run server (auto-reload)
python -m uvicorn app.main:app --reload

# Create new migration setelah ubah model
alembic revision -m "describe_change"

# Apply migrations
alembic upgrade head

# Rollback satu migration
alembic downgrade -1

# Check current migration
alembic current
```

---

## Testing

Test scripts di `tests/` untuk manual verification:

```bash
python tests/test_db.py            # Test DB connection
python tests/test_auth_flow.py     # Register → login → protected route
python tests/test_dashboard.py     # Net worth, allocation, performance
python tests/test_ai_insights.py   # Gemini AI integration
```

API testing via Swagger UI: http://localhost:8000/docs

---

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy** — async ORM dengan asyncpg
- **Pydantic v2** — validation & settings
- **Alembic** — DB migrations
- **APScheduler** — background jobs
- **bcrypt + python-jose** — auth
- **yfinance + CoinGecko** — market data
- **Google Gemini** — AI insights
