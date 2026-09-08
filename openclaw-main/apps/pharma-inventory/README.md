# 💊 PharmaClaw — AI-Driven Pharmacy Inventory Management

Built on [OpenClaw](https://openclaw.ai) · FastAPI · SQLite · Groq AI

---

## What It Does

PharmaClaw is a pharmacy inventory management system with an AI assistant that helps pharmacists:

- **Track stock** in real time (medicines, batches, expiry dates)
- **Forecast demand** using linear regression + moving average blending
- **Avoid stock-outs** with automatic reorder suggestions
- **Get AI-powered answers** via natural language (Groq / llama-3.3-70b)
- **Alert on expiring / expired** stock

---

## Quick Start (VS Code)

### 1. Install dependencies

```bash
cd apps/pharma-inventory
pip install -r requirements.txt
```

### 2. Set up environment (optional but recommended for AI)

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free at https://console.groq.com)
```

### 3. Run the server

**Option A — VS Code debugger (recommended)**
- Press `F5` or go to Run → Start Debugging
- Select **"🚀 PharmaClaw — Start Server"**
- Server starts at http://localhost:8000

**Option B — Terminal**
```bash
cd apps/pharma-inventory
uvicorn main:app --reload --port 8000
```

### 4. Open the web UI

Visit **http://localhost:8000** in your browser.

The database is automatically created and seeded with 10 sample medicines + 30 days of sales history on first run.

---

## Architecture

```
openclaw-main/
├── apps/
│   └── pharma-inventory/         ← The app lives here
│       ├── main.py               ← FastAPI entry point (run this)
│       ├── requirements.txt      ← Python dependencies
│       ├── .env.example          ← Copy to .env, add GROQ_API_KEY
│       ├── pharma_inventory.db   ← SQLite DB (auto-created)
│       ├── db/
│       │   ├── models.py         ← SQLAlchemy ORM models
│       │   └── seed.py           ← Sample data seeder
│       ├── api/
│       │   ├── routes.py         ← All REST API endpoints
│       │   └── assistant.py      ← Groq AI chat + rule-based fallback
│       ├── ml/
│       │   └── forecasting.py    ← Demand forecasting (LR + MA)
│       └── static/
│           └── index.html        ← Single-page web UI
│
└── skills/
    └── pharma-inventory/
        └── SKILL.md              ← OpenClaw skill definition
```

---

## Database Schema

**SQLite** (`pharma_inventory.db`) — zero config, runs everywhere.

| Table | Purpose |
|-------|---------|
| `medicines` | Drug catalogue (name, strength, stock, pricing, reorder levels) |
| `batches` | Individual stock batches with expiry dates |
| `stock_transactions` | Every stock movement (IN/OUT/RETURN/ADJUST) |
| `ai_conversations` | Chat history with the AI assistant |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Stats + alerts (low stock, expiry, top sellers) |
| GET | `/api/medicines` | List medicines (filter by name/category) |
| POST | `/api/medicines` | Add a new medicine |
| PUT | `/api/medicines/{id}` | Update medicine details |
| DELETE | `/api/medicines/{id}` | Remove medicine |
| POST | `/api/transactions` | Record IN/OUT/RETURN/ADJUST |
| GET | `/api/transactions/{id}` | Transaction history for a medicine |
| POST | `/api/batches` | Add a stock batch |
| GET | `/api/forecast/{id}` | 7-day demand forecast |
| GET | `/api/reorder-suggestions` | All reorder recommendations |
| POST | `/api/chat` | Send message to AI assistant |
| GET | `/api/chat/history` | Chat history |

Interactive API docs: **http://localhost:8000/docs**

---

## AI Assistant

### With Groq API key (full AI)

Set `GROQ_API_KEY` in `.env`. The assistant uses `llama-3.3-70b-versatile` with live inventory context injected into every prompt. It can answer free-form questions like:

- *"Which antibiotics are running low this week?"*
- *"Show me items expiring in 15 days."*
- *"How is my inventory this month?"*
- *"What should I order today?"*

### Without API key (rule-based fallback)

The assistant still works using built-in rules — it queries the database directly and returns structured answers for common pharmacy questions. No AI key needed to get started.

---

## Forecasting Model

The demand forecast in `ml/forecasting.py` blends two approaches:

| Method | Weight | Best For |
|--------|--------|----------|
| Linear Regression | 60% | Trending demand (seasonal, growing) |
| Moving Average (7-day) | 40% | Stable, predictable demand |

**Inputs:** 30 days of `OUT` transactions per medicine  
**Output:** 7-day daily forecast + total + average daily demand

Reorder suggestions use `days_of_cover = current_stock / avg_daily_demand` — medicines with < 7 days cover or stock ≤ reorder level are flagged.

---

## OpenClaw Integration

This app is also registered as an OpenClaw skill (`skills/pharma-inventory/SKILL.md`).

When OpenClaw is running, the agent can answer pharmacy inventory questions by:
1. Calling the local API endpoints
2. Formatting responses for WhatsApp / Telegram / any connected channel

Example agent usage:
```bash
openclaw agent --message "Which drugs are running low in the pharmacy?"
```

---

## VS Code Tips

- **F5** → starts the server with the debugger attached (set breakpoints anywhere)
- **Thunder Client** extension → test API endpoints directly in VS Code
- **SQLTools + SQLite driver** → browse `pharma_inventory.db` visually in VS Code
- The `.vscode/launch.json` has two configs: server start + database seed

---

## Extending the Project

| Feature | Where to add |
|---------|-------------|
| SMS/WhatsApp alerts | `api/routes.py` → trigger on low stock POST |
| Supplier ordering emails | New `api/suppliers.py` route |
| Barcode scanning | Add barcode field to `Medicine` model |
| Multi-pharmacy support | Add `pharmacy_id` FK to all tables |
| Vector RAG over drug info | Add ChromaDB in `ml/`, embed drug leaflets |
| LSTM forecasting | Replace `ml/forecasting.py` with PyTorch model |
