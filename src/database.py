from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, date
import os

# Database path - configurable via environment variable for Docker
DB_PATH = os.getenv("DB_PATH", "sqlite:///avionyx.db")

Base = declarative_base()

class DailyEntry(Base):
    __tablename__ = 'daily_entries'

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    
    # Eggs
    eggs_collected = Column(Integer, default=0)
    eggs_broken = Column(Integer, default=0)
    eggs_good = Column(Integer, default=0) # Computed/Stored for ease
    
    # Sales
    eggs_sold = Column(Integer, default=0)
    crates_sold = Column(Integer, default=0)
    income = Column(Float, default=0.0)
    
    # Feed
    feed_used_kg = Column(Float, default=0.0)
    feed_cost = Column(Float, default=0.0)
    
    # Mortality & Flock
    mortality_count = Column(Integer, default=0)
    mortality_reasons = Column(String, default="") # JSON or comma-separated if multiple reasons in a day
    flock_added = Column(Integer, default=0)
    flock_removed = Column(Integer, default=0)
    flock_total = Column(Integer, default=0)
    
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class SystemSettings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False) # Store everything as string, cast on use

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    user_id = Column(Integer, nullable=False)  # Telegram user ID
    action = Column(String, nullable=False)  # e.g., "eggs_added", "feed_recorded", "flock_mortality"
    details = Column(String, default="")  # JSON or human-readable details

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # FEED, MEDICATION, EQUIPMENT
    quantity = Column(Float, default=0.0)
    unit = Column(String, default="units")
    cost_per_unit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Expense(Base):
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today)
    category = Column(String, nullable=False) # FEED, MEDS, LABOR, OTHER
    amount = Column(Float, nullable=False)
    description = Column(String)
    user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

class BirdSale(Base):
    __tablename__ = 'bird_sales'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today)
    quantity = Column(Integer, nullable=False)
    price_per_bird = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    buyer_name = Column(String)
    created_at = Column(DateTime, default=datetime.now)

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today)
    type = Column(String, nullable=False) # INCOME, EXPENSE
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    related_id = Column(Integer) # ID of Expense or BirdSale or DailyEntry
    related_table = Column(String) # 'expenses', 'bird_sales', 'daily_entries'
    created_at = Column(DateTime, default=datetime.now)

def init_db():
    engine = create_engine(DB_PATH, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

# Global session factory (to be used by usage code)
engine = create_engine(DB_PATH, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base.metadata.create_all(engine) - Managed by Alembic now


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
