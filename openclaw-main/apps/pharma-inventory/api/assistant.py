"""
AI assistant using Google Gemini API (gemini-2.5-flash).
Falls back to rule-based responses if GEMINI_API_KEY is not set.
"""

import os
import json
import httpx
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional

# ── FIX 1: os.getenv() takes the VARIABLE NAME, not the value ─────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

SYSTEM_PROMPT = """You are PharmAssist, an expert AI assistant for a pharmacy inventory management system.
You help pharmacists with:
- Stock status and inventory queries
- Demand analysis and reorder recommendations
- Expiry date alerts
- Sales trend analysis
- General pharmaceutical inventory advice

Keep answers concise, practical, and pharmacy-focused.
When you mention specific medicines or numbers, be precise.
Always prioritize patient safety (no recommendations for expired drugs, flag critically low stock)."""


def get_db_session():
    """Create a standalone DB session (used by Telegram bot, not FastAPI)."""
    from db.models import SessionLocal
    return SessionLocal()


def build_inventory_context(db=None) -> str:
    """Build a rich text summary of current inventory state to inject as context."""
    from db.models import Medicine, Batch

    # ── FIX 2: Create our own session if none is provided (Telegram path) ────
    own_session = False
    if db is None:
        db = get_db_session()
        own_session = True

    try:
        medicines = db.query(Medicine).all()
        today = date.today()

        low_stock = [m for m in medicines if m.current_stock <= m.reorder_level]
        expiring_soon = (
            db.query(Batch)
            .filter(Batch.expiry_date <= today + timedelta(days=30))
            .filter(Batch.expiry_date >= today)
            .filter(Batch.quantity > 0)
            .all()
        )
        expired = (
            db.query(Batch)
            .filter(Batch.expiry_date < today)
            .filter(Batch.quantity > 0)
            .all()
        )

        lines = ["=== CURRENT PHARMACY INVENTORY SNAPSHOT ==="]
        lines.append(f"Date: {today}")
        lines.append(f"Total medicines in catalogue: {len(medicines)}")
        lines.append(f"Low stock alerts: {len(low_stock)}")
        lines.append(f"Batches expiring within 30 days: {len(expiring_soon)}")
        lines.append(f"Expired batches still in stock: {len(expired)}")
        lines.append("")

        lines.append("--- STOCK LEVELS ---")
        for m in medicines:
            status = "LOW" if m.current_stock <= m.reorder_level else "OK"
            lines.append(f"{m.name}: {m.current_stock} {m.unit}s [{status}] | Reorder at: {m.reorder_level}")

        if expiring_soon:
            lines.append("\n--- EXPIRING SOON (<=30 days) ---")
            for b in expiring_soon:
                lines.append(f"{b.medicine.name} | Batch {b.batch_number} | {b.quantity} units | Expires: {b.expiry_date}")

        if expired:
            lines.append("\n--- EXPIRED STOCK ---")
            for b in expired:
                lines.append(f"{b.medicine.name} | Batch {b.batch_number} | {b.quantity} units | Expired: {b.expiry_date}")

        return "\n".join(lines)

    finally:
        if own_session:
            db.close()


async def chat_with_gemini(
    user_message: str,
    history: List[Dict],
    db=None,
) -> str:
    """Send message to Gemini and return assistant reply."""

    if not GEMINI_API_KEY:
        return fallback_response(user_message, db)

    # Build context -- creates its own DB session if db is None (Telegram path)
    inventory_context = build_inventory_context(db)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{inventory_context}\n\n"

    for h in history[-10:]:
        full_prompt += f"{h['role']}: {h['content']}\n"

    full_prompt += f"user: {user_message}\nassistant:"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }],
                    "generationConfig": {
                        "maxOutputTokens": 600,
                        "temperature": 0.3,
                    }
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Gemini API error: {e}\n\n{fallback_response(user_message, db)}"


# Keep the original function name for compatibility
chat_with_groq = chat_with_gemini


def fallback_response(user_message: str, db=None) -> str:
    """Rule-based fallback when Gemini API key is absent."""
    from db.models import Medicine, Batch
    from ml.forecasting import get_reorder_suggestions

    own_session = False
    if db is None:
        db = get_db_session()
        own_session = True

    try:
        msg = user_message.lower()
        today = date.today()

        if any(k in msg for k in ["low", "reorder", "order", "stock out", "shortage"]):
            suggestions = get_reorder_suggestions(db)
            urgent = [s for s in suggestions if s["needs_reorder"]]
            if not urgent:
                return "All medicines are above their reorder levels. Stock looks healthy!"
            lines = [f"{len(urgent)} medicines need reordering:\n"]
            for s in urgent[:8]:
                lines.append(f"- {s['name']}: {s['current_stock']} left, {s['days_of_cover']}d cover. Order: {s['suggested_order_qty']} {s['unit']}s")
            return "\n".join(lines)

        if any(k in msg for k in ["expir", "expire", "expiry"]):
            expiring = (
                db.query(Batch)
                .filter(Batch.expiry_date <= today + timedelta(days=30))
                .filter(Batch.expiry_date >= today)
                .all()
            )
            expired = db.query(Batch).filter(Batch.expiry_date < today).all()
            lines = []
            if expired:
                lines.append(f"{len(expired)} expired batches (must be quarantined!):")
                for b in expired[:5]:
                    lines.append(f"  - {b.medicine.name}: {b.quantity} units expired {b.expiry_date}")
            if expiring:
                lines.append(f"\n{len(expiring)} batches expiring within 30 days:")
                for b in expiring[:8]:
                    lines.append(f"  - {b.medicine.name}: {b.quantity} units, expires {b.expiry_date}")
            return "\n".join(lines) if lines else "No expiry issues detected."

        if any(k in msg for k in ["how many", "count", "total", "inventory", "medicine"]):
            medicines = db.query(Medicine).all()
            low = [m for m in medicines if m.current_stock <= m.reorder_level]
            return (
                f"Inventory Summary:\n"
                f"- Total medicines: {len(medicines)}\n"
                f"- Healthy stock: {len(medicines) - len(low)}\n"
                f"- Low stock / reorder needed: {len(low)}\n"
                f"Low stock: {', '.join(m.name for m in low[:5]) or 'None'}"
            )

        if any(k in msg for k in ["stock", "status", "health"]):
            medicines = db.query(Medicine).all()
            low = [m for m in medicines if m.current_stock <= m.reorder_level]
            return (
                f"Inventory Summary:\n"
                f"- Total medicines: {len(medicines)}\n"
                f"- Healthy stock: {len(medicines) - len(low)}\n"
                f"- Low stock / reorder needed: {len(low)}\n"
                f"Low stock: {', '.join(m.name for m in low[:5]) or 'None'}"
            )

        return (
            "I'm PharmAssist. Ask me about:\n"
            "- How many medicines are in inventory\n"
            "- Stock levels and low stock alerts\n"
            "- Expiring medicines\n"
            "- Reorder recommendations\n\n"
            "(Set GEMINI_API_KEY in .env for full AI responses)"
        )
    finally:
        if own_session:
            db.close()