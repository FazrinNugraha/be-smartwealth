# SmartWealth — Backend API

SmartWealth is a multi-asset investment portfolio tracker with AI-powered insights and stock price prediction. This repository contains the backend service that powers all features through a REST API.

---

## Background

Many Indonesian investors hold assets across different instruments — stocks, crypto, mutual funds, and gold — but have no single place to monitor everything at once. On top of that, most existing apps don't provide personalized analysis based on each user's actual portfolio condition.

SmartWealth solves two core problems: **a unified view of all assets** and **actionable investment insights powered by AI**.

---

## What Problems It Solves

- No single platform to track all investment asset types together
- No automatic analysis of portfolio health based on the user's risk profile
- No machine learning-based price prediction for IDX stocks
- Asset prices are not refreshed automatically, leaving data stale

---

## Features

### Authentication
- Register and log in with email and password
- Sign in with Google OAuth 2.0
- JWT access tokens (expire in 15 minutes) and refresh tokens (expire in 7 days)
- Automatic refresh token rotation for secure session management

### Asset and Transaction Management
- Create, read, update, and delete investment assets across categories: stocks, crypto, mutual funds, bonds, gold, property, and cash
- Record buy and sell transactions per asset
- Automatic calculation of average buy price, unrealized P&L, and ROI

### Dashboard and Portfolio
- Summary of total portfolio value, total capital invested, and profit/loss
- Asset allocation breakdown by category in percentages
- Daily portfolio value history for trend charts

### Real-time Prices
- IDX and global stock prices fetched from Yahoo Finance via `yfinance`
- Crypto prices fetched from the CoinGecko API
- Background job refreshes all prices every 5 minutes automatically

### AI Insights (Gemini AI)
- Portfolio analysis powered by Google Gemini 2.5 Flash
- Outputs a portfolio summary, SWOT analysis, step-by-step action plan, and risk assessment
- Responses are cached in the database for 6 hours to avoid unnecessary API calls

### Rule-based Insights
- A fallback analysis engine that runs financial rules against the portfolio when AI is unavailable
- Checks for: concentration risk, emergency fund adequacy, risk profile mismatch, large losses, and diversification
- Produces a health score (0–100) and a portfolio status label

### IDX Stock Price Prediction
- Machine learning model using LightGBM with quantile regression
- Trained on the last 3 years of historical data from Yahoo Finance
- Uses 40+ technical indicators as features: RSI, MACD, Bollinger Bands, ATR, Stochastic Oscillator, OBV, and more
- Returns lower, median, and upper price predictions for 1–7 business days ahead
- In-memory cache per ticker with a 1-hour TTL

### Background Jobs
- **Price Updater**: Refreshes prices for all assets held by active users every 5 minutes
- **Wealth Snapshot**: Saves a daily snapshot of each user's total portfolio value at midnight for historical charts

---

## Tech Stack

| Category | Technology |
|---|---|
| Framework | FastAPI |
| Server | Uvicorn (ASGI) |
| Database | PostgreSQL (Neon.tech, serverless) |
| ORM | SQLAlchemy (async) |
| Database Driver | asyncpg |
| Schema Migrations | Alembic |
| Validation & Config | Pydantic v2, pydantic-settings |
| Authentication | JWT (python-jose), bcrypt (passlib) |
| AI Model | Google Gemini 2.5 Flash (google-generativeai) |
| Stock Data | yfinance, curl_cffi (anti-bot bypass) |
| Crypto Data | CoinGecko API (via httpx) |
| ML Model | LightGBM, scikit-learn |
| Technical Analysis | ta (Technical Analysis library) |
| Data Processing | pandas, numpy |
| Background Jobs | APScheduler (AsyncIOScheduler) |
| Testing | pytest |

---

## Project Structure

```
be/
├── app/
│   ├── main.py              # FastAPI entry point, middleware, router registration
│   ├── config.py            # App configuration loaded from environment variables
│   ├── database.py          # Async SQLAlchemy engine and session factory
│   ├── models/              # ORM models (User, Asset, Transaction, Price, WealthHistory)
│   ├── schemas/             # Pydantic schemas for request and response validation
│   ├── routers/             # API route handlers organized by domain
│   │   ├── auth.py          # /api/v1/auth — login, register, OAuth, token refresh
│   │   ├── users.py         # /api/v1/users — user profile management
│   │   ├── assets.py        # /api/v1/assets — investment asset CRUD
│   │   ├── transactions.py  # /api/v1/transactions — transaction records
│   │   ├── prices.py        # /api/v1/prices — real-time asset prices
│   │   ├── dashboard.py     # /api/v1/dashboard — portfolio summary
│   │   ├── insights.py      # /api/v1/insights — portfolio health analysis
│   │   └── predictions.py   # /api/v1/predictions — IDX stock price prediction
│   ├── services/            # Business logic layer
│   │   ├── auth_service.py          # Login, register, JWT, OAuth flow
│   │   ├── asset_service.py         # Asset CRUD logic
│   │   ├── transaction_service.py   # Transaction logic and average price calculation
│   │   ├── dashboard_service.py     # Portfolio calculation and allocation
│   │   ├── price_service.py         # Fetch prices from yfinance and CoinGecko
│   │   ├── ai_service.py            # Gemini AI integration with caching
│   │   ├── insight_engine.py        # Rule-based portfolio analysis
│   │   ├── prediction_service.py    # LightGBM ML model for stock prediction
│   │   └── calculator.py            # Financial calculations (P&L, ROI, avg price)
│   ├── tasks/               # Scheduled background jobs
│   │   ├── price_updater.py         # Price refresh job every 5 minutes
│   │   └── wealth_snapshot.py       # Daily portfolio snapshot job
│   └── utils/               # Helper utilities and custom exceptions
├── alembic/                 # Database migration files
├── alembic.ini              # Alembic configuration
├── requirements.txt         # Python dependencies
└── tests/                   # Unit and integration tests
```

---

## Local Setup

### Prerequisites
- Python 3.12+
- A PostgreSQL database (Neon.tech is recommended for easy setup)
- A virtual environment

### Installation

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the `be/` root directory:

```env
# Database (PostgreSQL — asyncpg format)
DATABASE_URL=postgresql://user:password@host/dbname

# JWT
JWT_SECRET_KEY=your-very-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# App Settings
APP_ENV=development
FRONTEND_URL=http://localhost:5173
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Start the Server

```bash
uvicorn app.main:app --reload
```

The server runs at `http://localhost:8000`.

---

## API Documentation

Once the server is running, interactive API docs are available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create a new account |
| POST | `/api/v1/auth/login` | Log in with email and password |
| GET | `/api/v1/auth/google` | Redirect to Google OAuth |
| POST | `/api/v1/auth/refresh` | Refresh a JWT access token |
| GET | `/api/v1/dashboard/summary` | Total portfolio summary |
| GET | `/api/v1/dashboard/performance` | Per-asset performance |
| GET | `/api/v1/dashboard/allocation` | Asset allocation by category |
| GET | `/api/v1/assets` | List all assets |
| POST | `/api/v1/assets` | Add a new asset |
| GET | `/api/v1/transactions` | Transaction history |
| POST | `/api/v1/transactions` | Record a new transaction |
| GET | `/api/v1/prices/{symbol}` | Real-time price for an asset |
| GET | `/api/v1/insights` | Portfolio health score and insights |
| GET | `/api/v1/insights/ai` | AI-generated portfolio insights |
| GET | `/api/v1/predictions/{ticker}` | IDX stock price prediction |
| GET | `/api/v1/health` | API health check |
| GET | `/api/v1/health/db` | Database connectivity check |

---

## Database Schema

The database uses PostgreSQL with the following main tables:

| Table | Description |
|---|---|
| `users` | User accounts, risk profile, and currency preference |
| `refresh_tokens` | Stored refresh tokens for session management |
| `user_assets` | Investment assets owned by each user |
| `transactions` | Buy and sell transaction records per asset |
| `asset_prices` | Latest prices for each asset |
| `wealth_history` | Daily snapshots of each user's total portfolio value |
| `insight_cache` | Cached AI insight results per user (6-hour TTL) |

---

## Deployment

The backend can be deployed to any platform that supports Python ASGI apps, such as Railway, Render, or Fly.io. Make sure all environment variables above are configured on your chosen platform.

For production, set `APP_ENV=production` so that:
- SQL query logging is disabled
- Internal error messages are not exposed to clients
