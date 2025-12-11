from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
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

def init_db():
    engine = create_engine(DB_PATH, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

# Global session factory (to be used by usage code)
engine = create_engine(DB_PATH, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
