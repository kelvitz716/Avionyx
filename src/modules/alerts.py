"""Alerts & Notifications module for proactive monitoring."""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, AuditLog
from datetime import date, timedelta
from sqlalchemy import desc
from utils import get_back_home_keyboard

router = Router()

# Default thresholds
DEFAULT_FEED_LOW_THRESHOLD = 50.0  # kg
DEFAULT_EGG_DROP_THRESHOLD = 20  # percentage

def get_setting_value(db, key: str, default: float) -> float:
    """Get a setting value or return default."""
    setting = db.query(SystemSettings).filter_by(key=key).first()
    return float(setting.value) if setting else default


def check_low_feed_stock(db) -> str | None:
    """Check if feed usage indicates low stock. Returns alert message or None."""
    # This is a simplified check - in a real system, you'd track inventory
    # For now, we check if today's cumulative feed is high
    threshold = get_setting_value(db, "feed_low_threshold", DEFAULT_FEED_LOW_THRESHOLD)
    
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    
    if entry and entry.feed_used_kg >= threshold:
        return f"⚠️ **Feed Alert!**\nToday's usage ({entry.feed_used_kg:.1f} kg) has reached high threshold ({threshold:.0f} kg). Consider restocking."
    
    return None


def check_egg_production_anomaly(db) -> str | None:
    """Check for significant drop in egg production. Returns alert message or None."""
    threshold_pct = get_setting_value(db, "egg_drop_threshold", DEFAULT_EGG_DROP_THRESHOLD)
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    today_entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    yesterday_entry = db.query(DailyEntry).filter(DailyEntry.date == yesterday).first()
    
    if not today_entry or not yesterday_entry:
        return None
    
    if yesterday_entry.eggs_collected == 0:
        return None  # Avoid division by zero
    
    drop_pct = ((yesterday_entry.eggs_collected - today_entry.eggs_collected) / yesterday_entry.eggs_collected) * 100
    
    if drop_pct >= threshold_pct:
        return (
            f"🚨 **Production Alert!**\n"
            f"Egg production dropped by **{drop_pct:.0f}%**!\n"
            f"Yesterday: {yesterday_entry.eggs_collected} → Today: {today_entry.eggs_collected}\n\n"
            f"_Consider checking flock health._"
        )
    
    return None


def run_all_checks(db) -> list[str]:
    """Run all alert checks and return list of alert messages."""
    alerts = []
    
    feed_alert = check_low_feed_stock(db)
    if feed_alert:
        alerts.append(feed_alert)
    
    egg_alert = check_egg_production_anomaly(db)
    if egg_alert:
        alerts.append(egg_alert)
    
    return alerts


@router.callback_query(F.data == "menu_alerts")
async def show_alerts(callback: types.CallbackQuery):
    """Show current alerts status."""
    db = next(get_db())
    alerts = run_all_checks(db)
    db.close()
    
    if alerts:
        text = "\n\n".join(alerts)
    else:
        text = "✅ **All Clear!**\n\nNo alerts at this time. Your farm is running smoothly."
    
    keyboard = [
        [InlineKeyboardButton(text="🔄 Refresh", callback_data='menu_alerts')],
        [InlineKeyboardButton(text="📜 View Logs", callback_data='view_logs')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "view_logs")
async def view_audit_logs(callback: types.CallbackQuery):
    """Show recent audit logs."""
    db = next(get_db())
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(10).all()
    db.close()
    
    if logs:
        text = "📜 **Recent Activity Log**\n————————————————\n"
        for log in logs:
            ts = log.timestamp.strftime("%b %d, %H:%M")
            text += f"`{ts}` — **{log.action}**\n_{log.details}_\n\n"
    else:
        text = "📜 **Activity Log**\n\n_No activity recorded yet._"
    
    keyboard = [
        [InlineKeyboardButton(text="🔔 Back to Alerts", callback_data='menu_alerts')],
        [InlineKeyboardButton(text="🏠 Home", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()
