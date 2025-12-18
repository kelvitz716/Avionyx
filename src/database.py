from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, date
import os
import shutil

# Database paths
PROD_DB_PATH = os.getenv("DB_PATH", "sqlite:///avionyx.db")
DEMO_DB_PATH = "sqlite:///avionyx_demo.db"
DEMO_FILE = "avionyx_demo.db"

Base = declarative_base()

# Global State
IS_DEMO_MODE = False

class Contact(Base):
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False) # SUPPLIER, CUSTOMER, VET, STAFF
    phone = Column(String)
    trust_score = Column(Integer, default=50) # AI metric (0-100)
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)

class FinancialLedger(Base):
    __tablename__ = 'financial_ledger'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today)
    description = Column(String)
    amount = Column(Float, nullable=False)
    direction = Column(String, nullable=False) # IN, OUT
    payment_method = Column(String, default="CASH") # CASH, MPESA, CREDIT
    transaction_ref = Column(String) # M-Pesa Code
    category = Column(String, nullable=False) # Feed, Meds, Bird Sales, Egg Sales, Labor, Consultation
    
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True) # Optional (e.g. misc expense)
    contact = relationship("Contact")
    
    created_at = Column(DateTime, default=datetime.now)

class InventoryLog(Base):
    __tablename__ = 'inventory_logs'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today)
    item_name = Column(String, nullable=False) # 'Growers Mash', 'Kenbro Chick'
    quantity_change = Column(Float, nullable=False) # +50 or -10
    
    flock_id = Column(String, nullable=True) # Optional link to flock ID string
    
    ledger_id = Column(Integer, ForeignKey('financial_ledger.id'), nullable=True)
    ledger = relationship("FinancialLedger")
    
    created_at = Column(DateTime, default=datetime.now)

class DailyEntry(Base):
    __tablename__ = 'daily_entries'

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    
    # Eggs
    eggs_collected = Column(Integer, default=0)
    eggs_broken = Column(Integer, default=0)
    eggs_good = Column(Integer, default=0) # Computed/Stored for ease
    
    # Sales (Metrics only - financial detail in Ledger)
    eggs_sold = Column(Integer, default=0)
    crates_sold = Column(Integer, default=0)
    income = Column(Float, default=0.0)
    
    # Feed (Metrics only)
    feed_used_kg = Column(Float, default=0.0)
    feed_cost = Column(Float, default=0.0)
    
    # Mortality & Flock
    mortality_count = Column(Integer, default=0)
    mortality_reasons = Column(String, default="") 
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

class User(Base):
    """Bot users with role-based access control."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="STAFF")  # ADMIN, MANAGER, STAFF
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class InventoryItem(Base):
    """
    Kept for 'Current Stock' definition and pricing cache.
    Real-time stock could be calculated from logs, but this is faster for 'Select Item' menus.
    """
    __tablename__ = 'inventory_items'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # FEED, MEDICATION, EQUIPMENT, LIVESTOCK
    quantity = Column(Float, default=0.0)
    unit = Column(String, default="units")
    cost_per_unit = Column(Float, default=0.0)
    # New fields for enhanced tracking
    expiry_date = Column(Date, nullable=True)  # For medications/vaccines
    bag_weight = Column(Float, nullable=True)  # Weight per bag in kg (for FEED type)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Flock(Base):
    __tablename__ = 'flocks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g. "Flock A - Dec 2025"
    breed = Column(String, nullable=False)  # Kuroiler, Broiler, etc
    hatch_date = Column(Date, nullable=False)
    initial_count = Column(Integer, default=0)
    current_count = Column(Integer, default=0)  # Track current live count
    hens_count = Column(Integer, default=0)     # Number of females (for egg production stats)
    roosters_count = Column(Integer, default=0) # Number of males
    status = Column(String, default="ACTIVE")  # ACTIVE, SOLD, ARCHIVED
    created_at = Column(DateTime, default=datetime.now)


class VaccinationRecord(Base):
    """Track vaccination events per flock with scheduling for next dose."""
    __tablename__ = 'vaccination_records'
    
    id = Column(Integer, primary_key=True)
    flock_id = Column(Integer, ForeignKey('flocks.id'), nullable=False)
    flock = relationship("Flock")
    vaccine_name = Column(String, nullable=False)
    doses_used = Column(Integer, nullable=False)
    birds_vaccinated = Column(Integer, nullable=False)
    date = Column(Date, default=date.today)
    next_due_date = Column(Date, nullable=True)  # Scheduled reminder
    vaccinator = Column(String, default="Self")  # Who administered
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)


class DailyFeedUsage(Base):
    """Track multiple feed types used per day (linked to DailyEntry)."""
    __tablename__ = 'daily_feed_usage'
    
    id = Column(Integer, primary_key=True)
    daily_entry_id = Column(Integer, ForeignKey('daily_entries.id'), nullable=False)
    daily_entry = relationship("DailyEntry", backref="feed_usages")
    feed_item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    feed_item = relationship("InventoryItem")
    quantity_kg = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


# Engine Instances
prod_engine = create_engine(PROD_DB_PATH, echo=False, connect_args={"check_same_thread": False})
ProdSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prod_engine)

# Placeholder for Demo Engine (Lazy load)
demo_engine = None
DemoSessionLocal = None

def init_db():
    # Mainly for manual init, ALembic handles migration usually
    Base.metadata.create_all(prod_engine)
    return sessionmaker(bind=prod_engine)()

def init_demo_db():
    global demo_engine, DemoSessionLocal
    demo_engine = create_engine(DEMO_DB_PATH, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(demo_engine)
    DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=demo_engine)

def wipe_demo_db():
    global demo_engine, DemoSessionLocal, IS_DEMO_MODE
    if demo_engine:
        demo_engine.dispose()
    demo_engine = None
    DemoSessionLocal = None
    IS_DEMO_MODE = False
    
    if os.path.exists(DEMO_FILE):
        os.remove(DEMO_FILE)

def get_db():
    if IS_DEMO_MODE:
        if not DemoSessionLocal:
            init_demo_db()
        db = DemoSessionLocal()
    else:
        db = ProdSessionLocal()
        
    try:
        yield db
    finally:
        db.close()
