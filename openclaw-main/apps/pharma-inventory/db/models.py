"""
SQLAlchemy models for Pharmacy Inventory Management.
Database: SQLite (pharma_inventory.db) — zero-config, VS Code friendly.
"""

from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, Text, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pharma_inventory.db")
DATABASE_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Medicine(Base):
    """Core medicine/drug catalogue."""
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    generic_name = Column(String(200))
    strength = Column(String(50))          # e.g. "500mg", "10mg/5ml"
    dosage_form = Column(String(50))       # tablet, syrup, injection, etc.
    manufacturer = Column(String(200))
    supplier = Column(String(200))
    category = Column(String(100))        # analgesic, antibiotic, etc.
    unit = Column(String(30), default="strip")   # strip, bottle, vial
    unit_price = Column(Float, default=0.0)
    reorder_level = Column(Integer, default=20)  # trigger alert below this
    reorder_qty = Column(Integer, default=100)   # suggested order qty
    current_stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batches = relationship("Batch", back_populates="medicine", cascade="all, delete")
    transactions = relationship("StockTransaction", back_populates="medicine", cascade="all, delete")


class Batch(Base):
    """Individual stock batch with expiry tracking."""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    batch_number = Column(String(100), nullable=False)
    quantity = Column(Integer, default=0)
    expiry_date = Column(Date, nullable=False)
    purchase_price = Column(Float, default=0.0)
    received_date = Column(Date, default=date.today)

    medicine = relationship("Medicine", back_populates="batches")


class StockTransaction(Base):
    """Every stock movement — in (purchase) or out (sale/dispense/return)."""
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # IN / OUT / RETURN / ADJUST
    quantity = Column(Integer, nullable=False)
    notes = Column(Text)
    transacted_at = Column(DateTime, default=datetime.utcnow)
    transacted_by = Column(String(100), default="pharmacist")

    medicine = relationship("Medicine", back_populates="transactions")


class AIConversation(Base):
    """Stores Groq/AI chat history for the assistant tab."""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)   # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
