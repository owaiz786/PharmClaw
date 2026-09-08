---
name: pharma-inventory
description: >
  AI-driven pharmacy inventory management assistant. Use this skill when the pharmacist asks about:
  stock levels, low stock alerts, expiring medicines, drug reorder recommendations, demand forecasts,
  or wants to record a stock transaction (stock in / dispensing / return). Also use for natural-language
  queries like "what should I order today?", "which drugs are expiring soon?", "how is my inventory?",
  "any low stock alerts?", "show demand forecast for [drug]", or any pharmacy inventory operation.
metadata:
  {
    "openclaw":
      {
        "emoji": "💊",
        "os": ["darwin", "linux", "win32"],
        "requires": { "bins": ["python3", "uvicorn"] },
        "install":
          [
            {
              "id": "pip",
              "kind": "shell",
              "command": "pip install fastapi uvicorn sqlalchemy groq httpx python-multipart python-dotenv --break-system-packages",
              "label": "Install Python dependencies",
            },
          ],
      },
  }
---

# PharmaClaw — Pharmacy Inventory Skill

AI-driven pharmacy inventory management system built on FastAPI + SQLite + Groq AI.

## Quick Start

```bash
# 1. Start the server (from the skill app directory)
cd {baseDir}/../../apps/pharma-inventory
uvicorn main:app --reload --port 8000

# 2. Open in browser
open http://localhost:8000
```

## Features

- **Dashboard** — live stats: total medicines, low-stock count, expiry alerts, top sellers
- **Medicines CRUD** — add/edit/delete medicines with full drug details
- **Stock Transactions** — record IN (purchase), OUT (sale/dispense), RETURN, ADJUST
- **Demand Forecasting** — 7-day ahead forecast using linear regression + moving average blend
- **Reorder Suggestions** — auto-generated replenishment list sorted by urgency
- **AI Assistant** — Groq-powered (llama-3.3-70b) natural-language pharmacy assistant

## Environment Variables

Set in `apps/pharma-inventory/.env` or `~/.openclaw/.env`:

```env
# Required for full AI responses:
GROQ_API_KEY=gsk_your_key_here

# Optional (rule-based fallback works without it)
```

Get a free Groq API key at https://console.groq.com

## Database

SQLite file at `apps/pharma-inventory/pharma_inventory.db` — auto-created on first run.
10 sample medicines with 30 days of sales history are seeded automatically.

## CLI Queries (via OpenClaw agent)

When the agent loads this skill, it can:

1. **Answer stock queries** — fetch from API and summarise
2. **Natural language forecasting** — call `/api/forecast/{id}` and interpret
3. **Trigger reorders** — read `/api/reorder-suggestions` and format for the pharmacist
4. **Expiry checks** — read `/api/dashboard` and highlight urgent items

### Example commands agent can run:

```bash
# Check dashboard
curl -s http://localhost:8000/api/dashboard | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Low stock: {d[\"low_stock_count\"]}, Expiring: {d[\"expiring_soon_count\"]}')"

# Get reorder suggestions
curl -s http://localhost:8000/api/reorder-suggestions | python3 -c "import sys,json; [print(f'{r[\"name\"]}: order {r[\"suggested_order_qty\"]}') for r in json.load(sys.stdin) if r['needs_reorder']]"

# Ask the AI assistant
curl -s -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{"message":"What should I order today?","history":[]}' | python3 -c "import sys,json; print(json.load(sys.stdin)['reply'])"
```

## Architecture

```
apps/pharma-inventory/
├── main.py              # FastAPI app entry point
├── db/
│   ├── models.py        # SQLAlchemy ORM (Medicine, Batch, StockTransaction, AIConversation)
│   └── seed.py          # Sample data seeder
├── api/
│   ├── routes.py        # All REST endpoints
│   └── assistant.py     # Groq AI chat + fallback logic
├── ml/
│   └── forecasting.py   # Linear regression + moving average demand forecast
└── static/
    └── index.html       # Single-page web UI
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Summary stats + alerts |
| GET | `/api/medicines` | List all medicines |
| POST | `/api/medicines` | Add medicine |
| PUT | `/api/medicines/{id}` | Update medicine |
| DELETE | `/api/medicines/{id}` | Delete medicine |
| POST | `/api/transactions` | Record stock movement |
| GET | `/api/forecast/{id}` | 7-day demand forecast |
| GET | `/api/reorder-suggestions` | All reorder recommendations |
| POST | `/api/chat` | AI assistant message |
