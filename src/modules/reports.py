from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry
from datetime import date, timedelta
from utils import get_back_home_keyboard, format_currency

router = Router()

@router.callback_query(F.data == "menu_reports")
async def menu_reports(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="📅 Today's Summary", callback_data='report_daily')],
        [InlineKeyboardButton(text="🗓️ Last 7 Days", callback_data='report_weekly')],
        [InlineKeyboardButton(text="📆 Monthly Report", callback_data='report_month')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text="📊 **Reports & Insights**\n\nChoose a report:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "report_daily")
async def show_daily_report(callback: types.CallbackQuery):
    db = next(get_db())
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    db.close()
    
    report = f"🐓 **Daily Farm Summary — {today.strftime('%b %d')}**\n"
    report += "————————————————\n"
    
    if entry:
        report += f"🥚 **Eggs Collected:** {entry.eggs_collected} "
        if entry.eggs_broken > 0:
            report += f"(_Broken: {entry.eggs_broken}_)\n"
        else:
            report += "\n"
            
        report += f"💰 **Sales:** {format_currency(entry.income)}\n"
        report += f"🍽️ **Feed:** {entry.feed_used_kg:.1f} kg ({format_currency(entry.feed_cost)})\n"
        report += f"⚰️ **Deaths:** {entry.mortality_count}\n"
        report += f"🐥 **Flock Count:** {entry.flock_total} birds\n"
    else:
        report += "⚠️ *No data recorded for today yet.*\n"

    await callback.message.edit_text(
        text=report,
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_reports')
    )
    await callback.answer()

@router.callback_query(F.data == "report_weekly")
async def show_weekly_report(callback: types.CallbackQuery):
    db = next(get_db())
    today = date.today()
    start_date = today - timedelta(days=6)
    
    entries = db.query(DailyEntry).filter(DailyEntry.date >= start_date).order_by(DailyEntry.date).all()
    db.close()
    
    data = { (start_date + timedelta(days=i)): 0 for i in range(7) }
    for e in entries:
        data[e.date] = e.eggs_collected
        
    chart = "📈 **Eggs (Last 7 Days)**\n\n"
    max_val = max(data.values()) if any(data.values()) else 1
    scale = 10.0 / max_val if max_val > 0 else 1
    
    for day_date, count in data.items():
        day_name = day_date.strftime("%a")
        # Use full block character for better visuals
        num_blocks = int(count * scale)
        bars = "▇" * num_blocks
        if count == 0: bars = " "
        
        # Format: Mon: ▇▇▇▇ 4
        chart += f"`{day_name}: {bars:<10} {count}`\n"
        
    await callback.message.edit_text(
        text=chart,
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_reports')
    )
    await callback.answer()

@router.callback_query(F.data.startswith("report_month"))
async def show_monthly_report(callback: types.CallbackQuery):
    # Format: report_month or report_month_2023_11
    data = callback.data.split('_')
    
    today = date.today()
    target_year = today.year
    target_month = today.month
    
    if len(data) == 4:
        target_year = int(data[2])
        target_month = int(data[3])
        
    # Calculate start and end of month
    import calendar
    import sqlalchemy
    
    num_days = calendar.monthrange(target_year, target_month)[1]
    start_date = date(target_year, target_month, 1)
    end_date = date(target_year, target_month, num_days)
    
    db = next(get_db())
    entries = db.query(DailyEntry).filter(
        DailyEntry.date >= start_date,
        DailyEntry.date <= end_date
    ).all()
    db.close()
    
    # Aggregate
    total_eggs = sum(e.eggs_collected for e in entries)
    total_income = sum(e.income for e in entries)
    total_feed = sum(e.feed_used_kg for e in entries)
    avg_eggs = total_eggs / len(entries) if entries else 0
    
    month_name = start_date.strftime("%B %Y")
    
    report = f"🗓️ **Monthly Report — {month_name}**\n"
    report += "————————————————\n"
    report += f"🥚 **Total Eggs:** {total_eggs} _(Avg: {avg_eggs:.0f}/day)_\n"
    report += f"💰 **Total Income:** {format_currency(total_income)}\n"
    report += f"🍽️ **Feed Used:** {total_feed:.1f} kg\n"
    
    # Pagination Logic
    prev_month_date = start_date - timedelta(days=1)
    next_month_date = end_date + timedelta(days=1)
    
    # Don't show next button if it's future
    show_next = next_month_date <= date.today()
    
    keyboard = []
    nav_row = []
    nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"report_month_{prev_month_date.year}_{prev_month_date.month}"))
    if show_next:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"report_month_{next_month_date.year}_{next_month_date.month}"))
    
    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data='menu_reports')])
    
    await callback.message.edit_text(
        text=report,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()
