# 💊 PharmaClaw — Agentic AI Pharmacy Inventory Management

> Built on [OpenClaw](https://openclaw.ai) · FastAPI · SQLite · Groq (Llama-3.3-70B)

**PharmaClaw** is an intelligent pharmacy inventory management system powered by an **agentic AI assistant**. Unlike traditional systems with hardcoded logic or static prompts, PharmaClaw's agent autonomously decides which internal tools/API endpoints to invoke — checking live stock levels, batch expiry data, or demand forecasts — and grounds every answer in real-time database state. The system is accessible via a web dashboard **and Telegram**, enabling pharmacists to query inventory on the go.

---

## 🧠 Why "Agentic"?

Most "chat-over-your-data" tools simply stuff context into a prompt. PharmaClaw's assistant operates differently:

- **Plans and Calls Tools** — The agent decides at runtime whether it needs `/dashboard`, `/forecast/{id}`, `/reorder-suggestions`, or a direct DB query to answer a question, rather than following a fixed script.

- **Grounds Answers in Live Data** — Every response is backed by real-time queries against the SQLite inventory, not cached or stale context windows.

- **Acts Across Channels** — The same agent logic is exposed through both the web UI and **Telegram** (via OpenClaw's messaging integration), making the tool-calling behavior channel-agnostic.

- **Degrades Gracefully** — If no `GROQ_API_KEY` is set, a rule-based fallback still queries the same tools and returns structured answers, keeping the agent loop functional without an LLM.

---

## ✨ Core Features

- 📦 **Real-time Stock Tracking** — Medicines, batches, expiry dates
- 📊 **Demand Forecasting** — Linear Regression + Moving Average blend
- 🚨 **Stock-out Prevention** — Automatic reorder suggestions
- 💬 **Natural Language Queries** — Powered by Groq/Llama-3.3-70B
- ⏰ **Expiry Alerts** — Proactive notifications for expiring/expired stock
- 📱 **Multi-channel Access** — Web dashboard + Telegram

---

## 🚀 Quick Start (VS Code)

### 1. Install Dependencies

```bash
cd apps/pharma-inventory
pip install -r requirements.txt
```

### 2. Set Up Environment Variables (Optional but Recommended)

```bash
cp .env.example .env
# Edit .env and add:
#   - GROQ_API_KEY (get free at https://console.groq.com)
#   - TELEGRAM_BOT_TOKEN (to enable Telegram interface)
```

### 3. Run the Server

**Option A — VS Code Debugger (Recommended)**
- Press `F5` or go to **Run → Start Debugging**
- Select **"🚀 PharmaClaw — Start Server"**
- Server starts at `http://localhost:8000`

**Option B — Terminal**

```bash
cd apps/pharma-inventory
uvicorn main:app --reload --port 8000
```

> **Note:** The database is automatically created and seeded with 10 sample medicines + 30 days of sales history on first run.

### 4. Open the Web UI

Visit **http://localhost:8000** in your browser.

### 5. (Optional) Talk to It on Telegram

Once `TELEGRAM_BOT_TOKEN` is set and the OpenClaw agent is running, message your bot directly:

```
"Which antibiotics are running low this week?"
"What should I reorder today?"
```

The same agent powers both web and Telegram — no separate logic per channel.

---

## 🏗️ Architecture

```
openclaw-main/
├── apps/
│   └── pharma-inventory/         ← The app lives here
│       ├── main.py               ← FastAPI entry point (run this)
│       ├── requirements.txt      ← Python dependencies
│       ├── .env.example          ← Copy to .env for API keys
│       ├── pharma_inventory.db   ← SQLite DB (auto-created)
│       ├── db/
│       │   ├── models.py         ← SQLAlchemy ORM models
│       │   └── seed.py           ← Sample data seeder
│       ├── api/
│       │   ├── routes.py         ← All REST API endpoints (agent's "tools")
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

## 🗄️ Database Schema

**SQLite** (`pharma_inventory.db`) — zero configuration, runs everywhere.

| Table | Purpose |
|-------|---------|
| `medicines` | Drug catalogue (name, strength, stock, pricing, reorder levels) |
| `batches` | Individual stock batches with expiry dates |
| `stock_transactions` | Every stock movement (IN/OUT/RETURN/ADJUST) |
| `ai_conversations` | Chat history with the AI assistant |

---

## 📡 API Reference (Agent's Tool Surface)

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

📖 Interactive API docs: **http://localhost:8000/docs**

> Every endpoint is a callable "tool" the agent can invoke autonomously — not just for frontend use.

---

## 🤖 AI Assistant

### With Groq API Key (Full Agentic Mode)

Set `GROQ_API_KEY` in `.env`. The assistant uses `llama-3.3-70b-versatile` and, on each turn, decides which endpoints to call for fresh inventory context. It handles free-form questions like:

- *"Which antibiotics are running low this week?"*
- *"Show me items expiring in 15 days."*
- *"How is my inventory this month?"*
- *"What should I order today?"*

### Without API Key (Rule-Based Fallback)

The same tool-calling structure still runs — querying the database through the same endpoints and returning structured answers for common pharmacy questions. No AI key needed to get started.

---

## 📈 Forecasting Model

The demand forecast in `ml/forecasting.py` blends two approaches:

| Method | Weight | Best For |
|--------|--------|----------|
| Linear Regression | 60% | Trending demand (seasonal, growing) |
| Moving Average (7-day) | 40% | Stable, predictable demand |

**Inputs:** 30 days of `OUT` transactions per medicine  
**Output:** 7-day daily forecast + total + average daily demand

**Reorder Logic:**  
`days_of_cover = current_stock / avg_daily_demand`  
Medicines with `< 7` days cover or stock ≤ reorder level are flagged.

---

## 🔌 OpenClaw Integration (Web + Telegram)

This app is registered as an OpenClaw skill (`skills/pharma-inventory/SKILL.md`), enabling the same agent across multiple channels:

- 🌐 **Web** — Chat widget in dashboard
- 📱 **Telegram** — Message the bot directly
- 💬 **WhatsApp** — Supported via OpenClaw channel abstraction

**Example CLI Usage:**
```bash
openclaw agent --message "Which drugs are running low in the pharmacy?"
```

**Example Telegram Interaction:**
```
You:  What should I reorder today?
Bot:  3 items are below reorder level: 
      • Paracetamol 500mg (12 units left, reorder at 50)
      • Amoxicillin 250mg (8 units left, reorder at 30)
      • Ibuprofen 400mg (5 units left, reorder at 25)
```

The agent reasons over the same tool set regardless of channel. Adding a new interface (Slack, Discord, etc.) only requires a new OpenClaw channel adapter — no inventory logic rewrite.

---

## 💡 VS Code Tips

- **F5** — Start server with debugger attached (set breakpoints anywhere)
- **Thunder Client** — Test API endpoints directly in VS Code
- **SQLTools + SQLite driver** — Browse `pharma_inventory.db` visually
- The `.vscode/launch.json` includes two configs: server start + database seed

---

## 🔧 Extending the Project

| Feature | Where to Add |
|---------|-------------|
| SMS/WhatsApp alerts | `api/routes.py` — trigger on low stock POST |
| Supplier ordering emails | New `api/suppliers.py` route |
| Barcode scanning | Add `barcode` field to `Medicine` model |
| Multi-pharmacy support | Add `pharmacy_id` FK to all tables |
| Vector RAG over drug info | Add ChromaDB in `ml/`, embed drug leaflets |
| LSTM forecasting | Replace `ml/forecasting.py` with PyTorch model |
| More OpenClaw channels | Add new channel adapter under `skills/pharma-inventory/` |

---


---

**Built with ❤️ using OpenClaw**
