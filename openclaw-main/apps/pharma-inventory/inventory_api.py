"""
FastAPI bridge to serve pharmacy inventory data from SQLite database.
This allows OpenClaw to access your database via REST API.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Dict, Any

# Import your database models
from db.models import SessionLocal, Medicine, Batch, StockTransaction

app = FastAPI(title="Pharmacy Inventory API")

# Enable CORS for OpenClaw
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/inventory/status")
def get_inventory_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get overall inventory health summary"""
    medicines = db.query(Medicine).all()
    today = date.today()
    
    low_stock = [m for m in medicines if m.current_stock <= m.reorder_level]
    
    # Check expiring batches
    expiring_soon = db.query(Batch).filter(
        Batch.expiry_date <= today + timedelta(days=30),
        Batch.expiry_date >= today,
        Batch.quantity > 0
    ).count()
    
    expired = db.query(Batch).filter(
        Batch.expiry_date < today,
        Batch.quantity > 0
    ).count()
    
    return {
        "total_medicines": len(medicines),
        "low_stock_count": len(low_stock),
        "expiring_soon_count": expiring_soon,
        "expired_count": expired,
        "low_stock_items": [{"name": m.name, "stock": m.current_stock, "reorder_level": m.reorder_level} for m in low_stock[:10]]
    }

@app.get("/api/medicines")
def get_medicines(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get all medicines with current stock"""
    medicines = db.query(Medicine).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "current_stock": m.current_stock,
            "reorder_level": m.reorder_level,
            "unit": m.unit,
            "unit_price": m.unit_price,
            "category": m.category
        }
        for m in medicines
    ]

@app.get("/api/medicines/{medicine_id}")
def get_medicine(medicine_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get specific medicine details including batches"""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        return {"error": "Medicine not found"}
    
    batches = db.query(Batch).filter(Batch.medicine_id == medicine_id).all()
    
    return {
        "id": medicine.id,
        "name": medicine.name,
        "current_stock": medicine.current_stock,
        "reorder_level": medicine.reorder_level,
        "unit": medicine.unit,
        "unit_price": medicine.unit_price,
        "batches": [
            {
                "batch_number": b.batch_number,
                "quantity": b.quantity,
                "expiry_date": b.expiry_date.isoformat()
            }
            for b in batches
        ]
    }

@app.get("/api/expiring")
def get_expiring_medicines(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get medicines expiring within 30 days"""
    today = date.today()
    expiring_batches = db.query(Batch).filter(
        Batch.expiry_date <= today + timedelta(days=30),
        Batch.expiry_date >= today,
        Batch.quantity > 0
    ).all()
    
    return [
        {
            "medicine_name": b.medicine.name,
            "batch_number": b.batch_number,
            "quantity": b.quantity,
            "expiry_date": b.expiry_date.isoformat()
        }
        for b in expiring_batches
    ]

@app.get("/api/low-stock")
def get_low_stock(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get all medicines below reorder level"""
    medicines = db.query(Medicine).filter(
        Medicine.current_stock <= Medicine.reorder_level
    ).all()
    
    return [
        {
            "name": m.name,
            "current_stock": m.current_stock,
            "reorder_level": m.reorder_level,
            "unit": m.unit
        }
        for m in medicines
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)