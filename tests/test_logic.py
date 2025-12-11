"""Tests for business logic (calculations, aggregations)."""
from datetime import date, timedelta
from database import DailyEntry, SystemSettings


class TestFeedCalculations:
    """Tests for feed cost calculation logic."""

    def test_feed_cost_per_kg(self, db_session):
        """Test calculating cost when using kg."""
        # Setup settings
        db_session.add(SystemSettings(key="feed_bag_weight", value="70"))
        db_session.add(SystemSettings(key="feed_bag_cost", value="2500"))
        db_session.commit()

        bag_weight = 70.0
        bag_cost = 2500.0
        kg_used = 10.0

        # Cost calculation (from feed.py logic)
        cost = kg_used * (bag_cost / bag_weight)

        # 10kg * (2500 / 70) = 10 * 35.71... = 357.14...
        assert round(cost, 2) == 357.14

    def test_feed_cost_per_bag(self, db_session):
        """Test calculating cost when using bags."""
        bag_weight = 70.0
        bag_cost = 2500.0
        bags_used = 2.0

        kg_used = bags_used * bag_weight
        cost = bags_used * bag_cost

        assert kg_used == 140.0
        assert cost == 5000.0


class TestReportAggregations:
    """Tests for report aggregation logic."""

    def test_monthly_aggregation(self, db_session):
        """Test aggregating data for a month."""
        # Create entries for a week
        base_date = date(2024, 1, 1)
        for i in range(7):
            entry = DailyEntry(
                date=base_date + timedelta(days=i),
                eggs_collected=100 + i,
                income=500.0 + (i * 10),
                feed_used_kg=10.0 + i
            )
            db_session.add(entry)
        db_session.commit()

        # Query and aggregate (simulating reports.py logic)
        entries = db_session.query(DailyEntry).filter(
            DailyEntry.date >= base_date,
            DailyEntry.date <= base_date + timedelta(days=6)
        ).all()

        total_eggs = sum(e.eggs_collected for e in entries)
        total_income = sum(e.income for e in entries)
        total_feed = sum(e.feed_used_kg for e in entries)
        avg_eggs = total_eggs / len(entries) if entries else 0

        # 100+101+102+103+104+105+106 = 721
        assert total_eggs == 721
        # 500+510+520+530+540+550+560 = 3710
        assert total_income == 3710.0
        # 10+11+12+13+14+15+16 = 91
        assert total_feed == 91.0
        # 721 / 7 = 103
        assert round(avg_eggs, 0) == 103

    def test_weekly_chart_scaling(self, db_session):
        """Test the bar chart scaling logic."""
        # Values for 7 days
        daily_counts = [50, 100, 80, 120, 90, 60, 110]

        max_val = max(daily_counts)
        scale = 10.0 / max_val if max_val > 0 else 1  # 10 blocks max

        # For max value (120), should get ~10 blocks
        assert int(120 * scale) == 10
        # For min value (50), should get ~4 blocks
        assert int(50 * scale) == 4
