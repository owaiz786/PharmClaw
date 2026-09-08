"""
Simple bridge to let OpenClaw access inventory data via file system
"""

import json
import os
from db.models import SessionLocal, Medicine, Batch
from datetime import date, timedelta

INVENTORY_FILE = "/tmp/inventory_status.json"

def update_inventory_file():
    """Write current inventory status to a JSON file that OpenClaw can read"""
    db = SessionLocal()
    medicines = db.query(Medicine).all()
    
    inventory_data = {
        "total_medicines": len(medicines),
        "items": []
    }
    
    for m in medicines:
        inventory_data["items"].append({
            "name": m.name,
            "stock": m.current_stock,
            "reorder_level": m.reorder_level,
            "unit": m.unit,
            "status": "LOW" if m.current_stock <= m.reorder_level else "OK"
        })
    
    with open(INVENTORY_FILE, 'w') as f:
        json.dump(inventory_data, f, indent=2)
    
    db.close()
    print(f"✅ Inventory updated: {len(medicines)} medicines")

if __name__ == "__main__":
    update_inventory_file()