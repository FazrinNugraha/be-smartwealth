# SmartWealth Backend - Test Files

> Collection of test scripts untuk manual testing dan development

---

## 📋 Test Files

### **Core Tests**

#### `test_db.py`
Test database connection ke Neon PostgreSQL.

**Run:**
```bash
python tests/test_db.py
```

**Expected Output:**
```
[OK] Connected! Result: 1
```

---

#### `test_auth_flow.py`
Test complete authentication flow (register → login → protected route).

**Run:**
```bash
python tests/test_auth_flow.py
```

**Tests:**
- Register user
- Login user
- Access protected route dengan token
- Refresh token

---

#### `test_google_oauth.py`
Test Google OAuth login flow.

**Run:**
```bash
python tests/test_google_oauth.py
```

**Flow:**
1. Generate Google OAuth URL
2. Manual login via browser
3. Copy authorization code
4. Exchange code → tokens

---

### **Feature Tests**

#### `test_assets.py`
Test asset CRUD operations.

**Tests:**
- Create asset
- Get user assets
- Update asset
- Delete asset (soft delete)

---

#### `test_transactions.py`
Test transaction system (buy/sell).

**Tests:**
- Create buy transaction
- Create sell transaction
- Validate oversell
- Calculate avg_buy_price

---

#### `test_prices_simple.py` & `test_prices.py`
Test price service (yfinance + CoinGecko).

**Tests:**
- Fetch stock price
- Fetch crypto price
- Fetch gold price
- Caching mechanism

---

#### `test_dashboard.py`
Test dashboard metrics.

**Tests:**
- Net worth calculation
- Allocation breakdown
- Performance metrics (ROI, P&L)
- Summary endpoint

---

#### `test_background_jobs.py`
Test background jobs (APScheduler).

**Tests:**
- Wealth snapshot job
- Price updater job
- Wealth history endpoint

---

#### `test_insights.py`
Test rule-based insights.

**Tests:**
- Concentration risk check
- Risk profile mismatch
- Emergency fund check
- Loss alert
- Diversification check

---

#### `test_ai_insights.py`
Test Gemini AI insights.

**Tests:**
- Get AI insights (cached)
- Refresh AI insights (force)
- Verify response format

---

### **Unit Tests**

#### `test_models.py`
Test SQLAlchemy models.

#### `test_schemas.py`
Test Pydantic schemas.

#### `test_tables.py`
Test database tables.

#### `test_jwt_simple.py`
Test JWT token generation/verification.

#### `test_register.py`
Test user registration.

---

### **API Tests**

#### `api-test.http`
HTTP requests untuk test API via REST Client (VS Code extension).

**Usage:**
1. Install REST Client extension di VS Code
2. Buka `api-test.http`
3. Klik "Send Request" di atas setiap request

---

## 🚀 Running Tests

### **Prerequisites:**
```bash
# Pastikan server running
python -m uvicorn app.main:app --reload
```

### **Run Individual Test:**
```bash
# Dari root folder be/
python tests/test_db.py
python tests/test_auth_flow.py
python tests/test_dashboard.py
```

### **Run All Tests (Future):**
```bash
# Dengan pytest (belum implemented)
pytest tests/
```

---

## 📝 Notes

- Test files ini untuk **manual testing** dan **development**
- Bukan automated tests (pytest)
- Perlu server running untuk test API endpoints
- Beberapa test perlu user/asset data di database

---

## 🎯 Test Coverage

**Tested Features:**
- ✅ Database connection
- ✅ Authentication (Email/Password + Google OAuth)
- ✅ Asset CRUD
- ✅ Transaction system
- ✅ Price service (caching)
- ✅ Dashboard metrics
- ✅ Background jobs
- ✅ Rule-based insights
- ✅ AI insights (Gemini)

**Not Tested:**
- ❌ Edge cases (oversell, negative values, dll)
- ❌ Error handling
- ❌ Performance/load testing
- ❌ Security testing

---

## 🔧 Maintenance

**Keep:**
- `test_db.py` - Quick database check
- `test_auth_flow.py` - Auth verification
- `test_google_oauth.py` - OAuth testing
- `test_dashboard.py` - Dashboard verification
- `test_ai_insights.py` - AI testing

**Can Archive:**
- `test_jwt_simple.py` - Covered by test_auth_flow
- `test_register.py` - Covered by test_auth_flow
- `test_models.py` - Basic model tests
- `test_schemas.py` - Basic schema tests
- `test_tables.py` - Basic table tests

---

## 📚 Documentation

For API documentation, see:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

For development guide, see:
- `docs/BACKEND_STEPS.md`
- `docs/SMARTWEALTH_SPEC.md`

