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

**Core**

![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)

**Database & ORM**

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-6BA81E?style=for-the-badge&logo=alembic&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)

**Authentication**

![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Google OAuth](https://img.shields.io/badge/Google_OAuth_2.0-4285F4?style=for-the-badge&logo=google&logoColor=white)

**AI & Machine Learning**

![Google Gemini](https://img.shields.io/badge/Google_Gemini_2.5_Flash-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-02569B?style=for-the-badge&logo=lightgbm&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)

**Data & Market APIs**

![pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Yahoo Finance](https://img.shields.io/badge/Yahoo_Finance-6001D2?style=for-the-badge&logo=yahoo&logoColor=white)
![CoinGecko](https://img.shields.io/badge/CoinGecko_API-8DC63F?style=for-the-badge&logo=coingecko&logoColor=white)

**Background Jobs & Testing**

![APScheduler](https://img.shields.io/badge/APScheduler-4A4A4A?style=for-the-badge&logo=clockify&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

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

## How It Works

### System Architecture

SmartWealth follows a clean layered architecture where every request passes through a defined set of responsibilities before touching the database.

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
└────────────────────────────┬────────────────────────────────┘
                             │  HTTPS REST API
┌────────────────────────────▼────────────────────────────────┐
│                   FastAPI (Backend API)                     │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   │
│  │  Router  │──▶│ Service  │──▶│  Model   │──▶│  DB   │   │
│  │  Layer   │   │  Layer   │   │  Layer   │   │ Session │   │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘   │
│                      │                                      │
│         ┌────────────┼────────────┐                         │
│         ▼            ▼            ▼                         │
│   Gemini AI     Yahoo Finance  CoinGecko                    │
│   (insights)    (stock prices) (crypto prices)              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           APScheduler (Background Jobs)             │    │
│  │   Price Updater (every 5 min) │ Wealth Snapshot (daily)  │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│              PostgreSQL on Neon.tech (serverless)           │
└─────────────────────────────────────────────────────────────┘
```

### Request Data Flow

Here is what happens step by step when the frontend makes an API call:

1. **Router** — FastAPI receives the HTTP request, validates the JWT token via a dependency, and routes it to the correct handler function
2. **Service Layer** — the handler delegates all business logic to a service (e.g. `dashboard_service`, `ai_service`). The router itself contains no logic
3. **Model / ORM** — the service queries or writes to the database using SQLAlchemy async sessions and ORM models
4. **External APIs** — if the service needs live data (prices, AI analysis), it calls the appropriate external API (Yahoo Finance, CoinGecko, or Gemini)
5. **Response** — the result is serialized through a Pydantic schema and returned as JSON

### Key Data Flows

**Portfolio Dashboard**
```
GET /api/v1/dashboard/summary
  → dashboard_service.get_summary()
  → queries user_assets + asset_prices tables
  → calculator.py computes P&L and ROI per asset
  → returns aggregated totals
```

**AI Insights**
```
GET /api/v1/insights/ai
  → ai_service.get_gemini_insights()
  → checks insight_cache table (TTL: 6 hours)
  → if expired: builds portfolio context → calls Gemini 2.5 Flash API
  → parses JSON response → saves to cache → returns to client
  → if Gemini unavailable: falls back to rule-based insight_engine
```

**Stock Price Prediction**
```
GET /api/v1/predictions/{ticker}
  → prediction_service.predict_stock()
  → checks in-memory cache (TTL: 1 hour)
  → if miss: fetches 3 years of OHLCV data from Yahoo Finance
  → builds 40+ technical indicator features
  → trains LightGBM quantile models on-demand
  → returns lower/median/upper price for 1–7 business days
```

**Background Price Updates**
```
APScheduler (every 5 minutes)
  → price_updater_job()
  → fetches all distinct asset symbols from active user portfolios
  → calls price_service for each symbol (Yahoo Finance or CoinGecko)
  → upserts latest prices into asset_prices table
```

### Authentication Flow

```
Email/Password Login:
  POST /auth/login → verify password hash → issue JWT access token (15 min)
                   → issue refresh token (7 days, stored in DB)

Google OAuth:
  GET /auth/google → redirect to Google consent screen
  GET /auth/google/callback → exchange code for Google profile
                            → upsert user in DB → issue JWT + refresh token

Token Refresh:
  POST /auth/refresh → validate refresh token in DB
                     → rotate: revoke old token → issue new pair
```

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
