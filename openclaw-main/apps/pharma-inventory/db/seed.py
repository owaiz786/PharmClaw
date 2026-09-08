"""Seed the database with realistic pharmacy sample data."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, datetime, timedelta
import random
from db.models import init_db, SessionLocal, Medicine, Batch, StockTransaction

MEDICINES = [
    {"name": "Paracetamol 500mg", "generic_name": "Paracetamol", "strength": "500mg",
     "dosage_form": "Tablet", "manufacturer": "Cipla", "supplier": "MedDistrib India",
     "category": "Analgesic", "unit": "strip", "unit_price": 12.0, "reorder_level": 50, "reorder_qty": 200},
    {"name": "Amoxicillin 500mg", "generic_name": "Amoxicillin", "strength": "500mg",
     "dosage_form": "Capsule", "manufacturer": "Sun Pharma", "supplier": "MedDistrib India",
     "category": "Antibiotic", "unit": "strip", "unit_price": 85.0, "reorder_level": 30, "reorder_qty": 100},
    {"name": "Metformin 500mg", "generic_name": "Metformin HCl", "strength": "500mg",
     "dosage_form": "Tablet", "manufacturer": "Lupin", "supplier": "HealthPlus",
     "category": "Antidiabetic", "unit": "strip", "unit_price": 35.0, "reorder_level": 40, "reorder_qty": 150},
    {"name": "Omeprazole 20mg", "generic_name": "Omeprazole", "strength": "20mg",
     "dosage_form": "Capsule", "manufacturer": "Dr. Reddy's", "supplier": "HealthPlus",
     "category": "Antacid", "unit": "strip", "unit_price": 55.0, "reorder_level": 25, "reorder_qty": 100},
    {"name": "Atorvastatin 10mg", "generic_name": "Atorvastatin", "strength": "10mg",
     "dosage_form": "Tablet", "manufacturer": "Cipla", "supplier": "MedDistrib India",
     "category": "Antilipidemic", "unit": "strip", "unit_price": 90.0, "reorder_level": 20, "reorder_qty": 80},
    {"name": "Cetirizine 10mg", "generic_name": "Cetirizine HCl", "strength": "10mg",
     "dosage_form": "Tablet", "manufacturer": "Sun Pharma", "supplier": "QuickMed",
     "category": "Antihistamine", "unit": "strip", "unit_price": 28.0, "reorder_level": 30, "reorder_qty": 120},
    {"name": "Azithromycin 500mg", "generic_name": "Azithromycin", "strength": "500mg",
     "dosage_form": "Tablet", "manufacturer": "Alkem", "supplier": "QuickMed",
     "category": "Antibiotic", "unit": "strip", "unit_price": 120.0, "reorder_level": 15, "reorder_qty": 60},
    {"name": "Pantoprazole 40mg", "generic_name": "Pantoprazole", "strength": "40mg",
     "dosage_form": "Tablet", "manufacturer": "Zydus", "supplier": "HealthPlus",
     "category": "Antacid", "unit": "strip", "unit_price": 62.0, "reorder_level": 20, "reorder_qty": 80},
    {"name": "Amlodipine 5mg", "generic_name": "Amlodipine", "strength": "5mg",
     "dosage_form": "Tablet", "manufacturer": "Lupin", "supplier": "MedDistrib India",
     "category": "Antihypertensive", "unit": "strip", "unit_price": 40.0, "reorder_level": 25, "reorder_qty": 100},
    {"name": "Ibuprofen 400mg", "generic_name": "Ibuprofen", "strength": "400mg",
     "dosage_form": "Tablet", "manufacturer": "Cipla", "supplier": "QuickMed",
     "category": "NSAID", "unit": "strip", "unit_price": 22.0, "reorder_level": 40, "reorder_qty": 160},
]

def seed():
    init_db()
    db = SessionLocal()
    if db.query(Medicine).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    today = date.today()
    random.seed(42)

    for med_data in MEDICINES:
        stock = random.randint(10, 150)
        med = Medicine(**med_data, current_stock=stock)
        db.add(med)
        db.flush()

        # Add 1-2 batches
        for b in range(random.randint(1, 2)):
            expiry = today + timedelta(days=random.choice([20, 45, 90, 180, 365]))
            batch = Batch(
                medicine_id=med.id,
                batch_number=f"BT{med.id:03d}{b+1:02d}",
                quantity=stock // (b + 1),
                expiry_date=expiry,
                purchase_price=med_data["unit_price"] * 0.7,
                received_date=today - timedelta(days=random.randint(0, 60))
            )
            db.add(batch)

        # Add 30 days of historical sales transactions
        for day_offset in range(30, 0, -1):
            tx_date = datetime.utcnow() - timedelta(days=day_offset)
            sale_qty = random.randint(1, 8)
            db.add(StockTransaction(
                medicine_id=med.id,
                transaction_type="OUT",
                quantity=sale_qty,
                notes="Daily sale",
                transacted_at=tx_date,
            ))

        # Initial stock-in
        db.add(StockTransaction(
            medicine_id=med.id,
            transaction_type="IN",
            quantity=stock,
            notes="Opening stock",
            transacted_at=datetime.utcnow() - timedelta(days=31),
        ))

    db.commit()
    db.close()
    print(f"✅ Seeded {len(MEDICINES)} medicines with batches + 30 days of transactions.")

if __name__ == "__main__":
    seed()
