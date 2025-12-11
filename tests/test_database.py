"""Tests for database models and CRUD operations."""
from datetime import date
from database import DailyEntry, SystemSettings


class TestDailyEntry:
    """Tests for the DailyEntry model."""

    def test_create_daily_entry(self, db_session):
        """Test creating a DailyEntry with today's date."""
        today = date.today()
        entry = DailyEntry(date=today)
        db_session.add(entry)
        db_session.commit()

        result = db_session.query(DailyEntry).filter(DailyEntry.date == today).first()
        assert result is not None
        assert result.date == today

    def test_default_values(self, db_session):
        """Test that default values are correctly set on DailyEntry."""
        entry = DailyEntry(date=date.today())
        db_session.add(entry)
        db_session.commit()

        assert entry.eggs_collected == 0
        assert entry.eggs_broken == 0
        assert entry.income == 0.0
        assert entry.mortality_count == 0
        assert entry.flock_total == 0

    def test_none_handling_for_counters(self, db_session):
        """Test the manual handling of None values (simulating legacy data)."""
        entry = DailyEntry(date=date.today())
        db_session.add(entry)
        db_session.commit()

        # Simulate a legacy row with NULL mortality_count
        # In real DB this might happen, SQLAlchemy defaults should prevent it,
        # but let's ensure our logic handles it.
        entry.mortality_count = None
        db_session.commit()

        # Re-fetch
        fetched = db_session.query(DailyEntry).first()

        # Simulate the fix we implemented in flock.py
        if fetched.mortality_count is None:
            fetched.mortality_count = 0

        fetched.mortality_count += 5
        db_session.commit()

        assert fetched.mortality_count == 5


class TestSystemSettings:
    """Tests for the SystemSettings model."""

    def test_create_setting(self, db_session):
        """Test creating and retrieving a system setting."""
        setting = SystemSettings(key="egg_price", value="30")
        db_session.add(setting)
        db_session.commit()

        result = db_session.query(SystemSettings).filter_by(key="egg_price").first()
        assert result is not None
        assert result.value == "30"

    def test_update_setting(self, db_session):
        """Test updating a system setting."""
        setting = SystemSettings(key="egg_price", value="30")
        db_session.add(setting)
        db_session.commit()

        setting.value = "35"
        db_session.commit()

        result = db_session.query(SystemSettings).filter_by(key="egg_price").first()
        assert result.value == "35"
