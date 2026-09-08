"""
FastAPI routes for Pharmacy Inventory Management System.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import get_db, Medicine, Batch, StockTransaction, AIConversation
from ml.forecasting import forecast_medicine, get_reorder_suggestions
from api.assistant import chat_with_groq

router = APIRouter()


# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class MedicineCreate(BaseModel):
    name: str
    generic_name: Optional[str] = ""
    strength: Optional[str] = ""
    dosage_form: Optional[str] = "Tablet"
    manufacturer: Optional[str] = ""
    supplier: Optional[str] = ""
    category: Optional[str] = ""
    unit: Optional[str] = "strip"
    unit_price: Optional[float] = 0.0
    reorder_level: Optional[int] = 20
    reorder_qty: Optional[int] = 100
    current_stock: Optional[int] = 0


class MedicineUpdate(BaseModel):
    name: Optional[str] = None
    strength: Optional[str] = None
    unit_price: Optional[float] = None
    reorder_level: Optional[int] = None
    reorder_qty: Optional[int] = None
    current_stock: Optional[int] = None
    supplier: Optional[str] = None
    category: Optional[str] = None


class BatchCreate(BaseModel):
    medicine_id: int
    batch_number: str
    quantity: int
    expiry_date: date
    purchase_price: Optional[float] = 0.0


class TransactionCreate(BaseModel):
    medicine_id: int
    transaction_type: str   # IN / OUT / RETURN / ADJUST
    quantity: int
    notes: Optional[str] = ""
    transacted_by: Optional[str] = "pharmacist"


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    medicines = db.query(Medicine).all()

    low_stock = [m for m in medicines if m.current_stock <= m.reorder_level]
    expiring_30 = (
        db.query(Batch)
        .filter(Batch.expiry_date <= today + timedelta(days=30))
        .filter(Batch.expiry_date >= today)
        .filter(Batch.quantity > 0)
        .all()
    )
    expired = db.query(Batch).filter(Batch.expiry_date < today).filter(Batch.quantity > 0).all()

    # Top 5 selling in last 7 days
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    top_sellers = (
        db.query(
            StockTransaction.medicine_id,
            func.sum(StockTransaction.quantity).label("total"),
        )
        .filter(StockTransaction.transaction_type == "OUT")
        .filter(StockTransaction.transacted_at >= cutoff_7d)
        .group_by(StockTransaction.medicine_id)
        .order_by(func.sum(StockTransaction.quantity).desc())
        .limit(5)
        .all()
    )
    top_sellers_out = []
    for row in top_sellers:
        med = db.query(Medicine).get(row.medicine_id)
        if med:
            top_sellers_out.append({"name": med.name, "sold_7d": row.total, "unit": med.unit})

    return {
        "total_medicines": len(medicines),
        "low_stock_count": len(low_stock),
        "expiring_soon_count": len(expiring_30),
        "expired_count": len(expired),
        "low_stock_items": [{"id": m.id, "name": m.name, "stock": m.current_stock, "reorder_level": m.reorder_level} for m in low_stock[:10]],
        "expiring_soon": [{"name": b.medicine.name, "batch": b.batch_number, "qty": b.quantity, "expiry": str(b.expiry_date)} for b in expiring_30[:10]],
        "expired_batches": [{"name": b.medicine.name, "batch": b.batch_number, "qty": b.quantity, "expiry": str(b.expiry_date)} for b in expired[:10]],
        "top_sellers_7d": top_sellers_out,
    }


# ─── Medicines CRUD ───────────────────────────────────────────────────────────

@router.get("/medicines")
def list_medicines(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Medicine)
    if search:
        q = q.filter(Medicine.name.ilike(f"%{search}%"))
    if category:
        q = q.filter(Medicine.category == category)
    return q.order_by(Medicine.name).all()


@router.get("/medicines/{med_id}")
def get_medicine(med_id: int, db: Session = Depends(get_db)):
    med = db.query(Medicine).get(med_id)
    if not med:
        raise HTTPException(404, "Medicine not found")
    return med


@router.post("/medicines", status_code=201)
def create_medicine(payload: MedicineCreate, db: Session = Depends(get_db)):
    med = Medicine(**payload.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


@router.put("/medicines/{med_id}")
def update_medicine(med_id: int, payload: MedicineUpdate, db: Session = Depends(get_db)):
    med = db.query(Medicine).get(med_id)
    if not med:
        raise HTTPException(404, "Medicine not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(med, k, v)
    med.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(med)
    return med


@router.delete("/medicines/{med_id}")
def delete_medicine(med_id: int, db: Session = Depends(get_db)):
    med = db.query(Medicine).get(med_id)
    if not med:
        raise HTTPException(404, "Medicine not found")
    db.delete(med)
    db.commit()
    return {"detail": "deleted"}


# ─── Stock Transactions ────────────────────────────────────────────────────────

@router.post("/transactions", status_code=201)
def record_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    med = db.query(Medicine).get(payload.medicine_id)
    if not med:
        raise HTTPException(404, "Medicine not found")

    if payload.transaction_type in ("OUT", "RETURN") and payload.transaction_type == "OUT":
        if med.current_stock < payload.quantity:
            raise HTTPException(400, f"Insufficient stock: {med.current_stock} available")

    tx = StockTransaction(**payload.model_dump())
    db.add(tx)

    if payload.transaction_type == "IN":
        med.current_stock += payload.quantity
    elif payload.transaction_type == "OUT":
        med.current_stock -= payload.quantity
    elif payload.transaction_type == "RETURN":
        med.current_stock += payload.quantity
    elif payload.transaction_type == "ADJUST":
        med.current_stock = payload.quantity

    db.commit()
    return {"detail": "recorded", "new_stock": med.current_stock}


@router.get("/transactions/{med_id}")
def get_transactions(med_id: int, limit: int = 30, db: Session = Depends(get_db)):
    return (
        db.query(StockTransaction)
        .filter(StockTransaction.medicine_id == med_id)
        .order_by(StockTransaction.transacted_at.desc())
        .limit(limit)
        .all()
    )


# ─── Batches ──────────────────────────────────────────────────────────────────

@router.get("/batches/{med_id}")
def get_batches(med_id: int, db: Session = Depends(get_db)):
    return db.query(Batch).filter(Batch.medicine_id == med_id).all()


@router.post("/batches", status_code=201)
def add_batch(payload: BatchCreate, db: Session = Depends(get_db)):
    batch = Batch(**payload.model_dump())
    db.add(batch)
    med = db.query(Medicine).get(payload.medicine_id)
    if med:
        med.current_stock += payload.quantity
    db.commit()
    return batch


# ─── Forecasting ──────────────────────────────────────────────────────────────

@router.get("/forecast/{med_id}")
def get_forecast(med_id: int, db: Session = Depends(get_db)):
    med = db.query(Medicine).get(med_id)
    if not med:
        raise HTTPException(404, "Medicine not found")
    fc = forecast_medicine(db, med_id)
    fc["medicine_name"] = med.name
    fc["current_stock"] = med.current_stock
    fc["unit"] = med.unit
    return fc


@router.get("/reorder-suggestions")
def reorder_suggestions(db: Session = Depends(get_db)):
    return get_reorder_suggestions(db)


# ─── AI Chat ──────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    reply = await chat_with_groq(payload.message, payload.history, db)
    # Persist to DB
    db.add(AIConversation(role="user", content=payload.message))
    db.add(AIConversation(role="assistant", content=reply))
    db.commit()
    return {"reply": reply}


@router.get("/chat/history")
def chat_history(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(AIConversation).order_by(AIConversation.created_at.desc()).limit(limit).all()
    return list(reversed(rows))


# ─── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    rows = db.query(Medicine.category).distinct().all()
    return sorted([r.category for r in rows if r.category])
