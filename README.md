# Tenda BI — Retail Intelligence Platform

Full-stack Django + React BI platform for Shopify stores.

## Architecture (data pipeline)

```
Shopify API
    ↓
ingestion/          ← Celery tasks pull raw data every 15 min
    ↓
raw_data/           ← Verbatim Shopify JSON storage (RawOrder, RawProduct, etc.)
    ↓
warehouse/          ← ETL transforms raw → clean analytics tables
    ↓
analytics/          ← Metrics engine: DailyRevenue, RFMScore, KPISnapshot, etc.
    ↓
insights/           ← Alert + insight generation from computed metrics
    ↓
api/                ← DRF endpoints (never touch raw_data or run queries)
    ↓
frontend/           ← React dashboard
```

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5 + Django REST Framework |
| Database | PostgreSQL |
| Task queue | Celery + Redis |
| Caching | Redis (django-redis) |
| Auth | JWT (SimpleJWT) |
| Shopify | OAuth 2.0 + REST Admin API |
| Frontend | React 18 + Vite + Recharts |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env     # edit with your credentials
createdb tenda_bi
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev              # http://localhost:3000
```

### 3. Celery worker

```bash
cd backend
celery -A core worker --loglevel=info --pool=solo
```

### 4. Celery Beat scheduler

```bash
cd backend
celery -A core beat --loglevel=info
```

## Django Apps

| App | Responsibility |
|-----|---------------|
| `core/` | Settings, URLs, WSGI, Celery config |
| `users/` | Custom User model (email auth), roles |
| `stores/` | Store model, Shopify connection record |
| `ingestion/` | Shopify API client + sync Celery tasks |
| `raw_data/` | Verbatim Shopify JSON models + SyncLog |
| `warehouse/` | Clean ETL models: Product, Order, Customer, Inventory |
| `analytics/` | Precomputed metrics: KPISnapshot, DailyRevenue, RFMScore, InventoryMetric |
| `insights/` | Alert and Insight generation service |
| `api/` | DRF views, serializers, URL routing |
| `workers/` | Celery Beat schedule + maintenance tasks |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/register/ | Create account |
| POST | /api/auth/login/ | Get JWT tokens |
| GET | /api/auth/me/ | Current user |
| GET | /api/shopify/connect/?shop=... | Start OAuth |
| GET | /api/shopify/callback/ | OAuth callback |
| GET | /api/shopify/stores/ | List stores |
| POST | /api/shopify/stores/{id}/sync/ | Manual sync |
| GET | /api/dashboard/{id}/kpis/ | KPI snapshot |
| GET | /api/dashboard/{id}/revenue-trend/ | Daily revenue |
| GET | /api/dashboard/{id}/top-products/ | Top products |
| GET | /api/dashboard/{id}/category-revenue/ | By category |
| GET | /api/dashboard/{id}/location-revenue/ | By location |
| GET | /api/dashboard/{id}/insights/ | AI insights |
| GET | /api/inventory/{id}/ | Inventory health |
| GET | /api/customers/{id}/analytics/ | RFM analytics |
| GET | /api/customers/{id}/list/ | Customer list |
| GET | /api/alerts/{id}/ | Active alerts |
| POST | /api/alerts/{id}/{alert_id}/resolve/ | Resolve alert |
| POST | /api/webhooks/{event}/ | Shopify webhooks |

## Key Principles

- **Views never calculate metrics** — all metrics come from precomputed tables
- **Views never call Shopify** — only `ingestion/services/shopify_client.py` does
- **Raw data is never modified** — it is the source of truth for reprocessing
- **Every layer has one job** — ingestion → raw → warehouse → analytics → insights → api

## Shopify App Setup

1. Go to https://partners.shopify.com → Create app
2. Set redirect URI: `http://localhost:8000/api/shopify/callback/`
3. Required scopes: `read_orders,read_products,read_customers,read_inventory,read_locations`
4. Add API Key and Secret to `.env`
