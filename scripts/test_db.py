import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from database import init_db, DailyEntry, SystemSettings
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_logic():
    print("Initializing Database...")
    # Use memory DB for test
    engine = create_engine("sqlite:///:memory:", echo=False)
    from database import Base
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    print("Testing DailyEntry creation...")
    today = date.today()
    entry = DailyEntry(date=today, eggs_collected=30, eggs_broken=2)
    entry.eggs_good = entry.eggs_collected - entry.eggs_broken
    entry.income = 500.0
    entry.flock_total = 100
    
    db.add(entry)
    db.commit()
    
    retrieved = db.query(DailyEntry).first()
    assert retrieved.eggs_collected == 30
    assert retrieved.eggs_good == 28
    assert retrieved.income == 500.0
    print("✅ DailyEntry OK")
    
    print("Testing Settings...")
    setting = SystemSettings(key="price_per_egg", value="15.0")
    db.add(setting)
    db.commit()
    
    val = db.query(SystemSettings).filter_by(key="price_per_egg").first()
    assert float(val.value) == 15.0
    print("✅ Settings OK")

    db.close()
    print("🎉 All Tests Passed!")

if __name__ == "__main__":
    test_logic()
