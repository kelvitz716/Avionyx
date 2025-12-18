from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import csv
import io
from database import get_db, DailyEntry
from datetime import date, timedelta, datetime
from utils import get_back_home_keyboard, format_currency

router = Router()

class ReportStates(StatesGroup):
    export_range = State()

@router.callback_query(F.data == "menu_reports")
async def menu_reports(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="💰 Financial Report (P&L)", callback_data='report_pnl')],
        [InlineKeyboardButton(text="🥚 Production & Performance", callback_data='report_prod')],
        [InlineKeyboardButton(text="🏥 Health & Inventory Status", callback_data='report_status')],
        [InlineKeyboardButton(text="📥 Export All Data (CSV)", callback_data='report_export')],
        [InlineKeyboardButton(text="⬅️ Main Menu", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text="📊 **Business Intelligence**\n\nSelect a comprehensive report to view:",
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

@router.callback_query(F.data == "report_export")
async def show_export_options(callback: types.CallbackQuery, state: FSMContext):
    """Show date range options for export."""
    keyboard = [
        [InlineKeyboardButton(text="📌 This Week", callback_data="export_week")],
        [InlineKeyboardButton(text="📅 This Month", callback_data="export_month")],
        [InlineKeyboardButton(text="📆 Last 30 Days", callback_data="export_30days")],
        [InlineKeyboardButton(text="♾️ All Time", callback_data="export_all")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu_reports")]
    ]
    await callback.message.edit_text(
        "📥 **Export Data**\n\nSelect date range:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ReportStates.export_range)
    await callback.answer()

@router.callback_query(ReportStates.export_range, F.data.startswith("export_"))
async def export_data(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Generate and send CSV export with selected date range."""
    range_type = callback.data.split("_")[1]
    await callback.answer("⏳ Generating export...", show_alert=False)
    
    # Calculate date range
    today = date.today()
    start_date = None
    range_label = "All Time"
    
    if range_type == "week":
        start_date = today - timedelta(days=7)
        range_label = "Last 7 Days"
    elif range_type == "month":
        start_date = date(today.year, today.month, 1)
        range_label = f"{today.strftime('%B %Y')}"
    elif range_type == "30days":
        start_date = today - timedelta(days=30)
        range_label = "Last 30 Days"
    # else: all time - no filter
    
    db = next(get_db())
    query = db.query(DailyEntry).order_by(DailyEntry.date.desc())
    if start_date:
        query = query.filter(DailyEntry.date >= start_date)
    entries = query.all()
    db.close()
    
    if not entries:
        await callback.message.edit_text(
            f"⚠️ No data found for **{range_label}**.",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard('menu_reports')
        )
        await state.clear()
        return

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Eggs Collected', 'Eggs Broken', 'Feed Used (kg)', 'Feed Cost', 'Income', 'Mortality', 'Flock Total', 'Notes'])
    
    for e in entries:
        writer.writerow([
            e.date, e.eggs_collected, e.eggs_broken, e.feed_used_kg,
            e.feed_cost, e.income, e.mortality_count, e.flock_total, e.notes or ""
        ])
        
    output.seek(0)
    csv_bytes = output.getvalue().encode('utf-8')
    
    file = BufferedInputFile(csv_bytes, filename=f"avionyx_export_{range_type}_{date.today()}.csv")
    
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=file,
        caption=f"📊 **Avionyx Data Export**\n📅 Range: {range_label}\n🗓️ Entries: {len(entries)}",
        parse_mode="Markdown"
    )
    await state.clear()

@router.callback_query(F.data == "report_pnl")
async def show_pnl(callback: types.CallbackQuery):
    from database import FinancialLedger
    import sqlalchemy
    db = next(get_db())
    
    # Get range: Defaulting to Current Month for start, with toggle for All Time?
    # For "Comprehensive", let's show separate columns or just comprehensive totals.
    # Let's show "Current Month" vs "All Time"
    
    today = date.today()
    start_month = date(today.year, today.month, 1)
    
    ledgers = db.query(FinancialLedger).all()
    db.close()
    
    # Aggregation
    data = {
        'in_month': {'in': 0, 'out': 0, 'cats': {}},
        'all_time': {'in': 0, 'out': 0, 'cats': {}}
    }
    
    for l in ledgers:
        amt = l.amount
        cat = l.category or "Other"
        
        # All Time
        if l.direction == "IN":
            data['all_time']['in'] += amt
        else:
            data['all_time']['out'] += amt
            data['all_time']['cats'][cat] = data['all_time']['cats'].get(cat, 0) + amt
            
        # Month
        l_date = l.date.date() if isinstance(l.date, datetime) else l.date
        if l_date >= start_month:
            if l.direction == "IN":
                data['in_month']['in'] += amt
            else:
                data['in_month']['out'] += amt
                data['in_month']['cats'][cat] = data['in_month']['cats'].get(cat, 0) + amt
                
    # Build Text
    def build_cat_list(cats):
        if not cats: return "_No expenses_"
        sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"  • {c}: {format_currency(v)}" for c, v in sorted_cats])

    text = f"📉 **Financial Performance**\n\n"
    
    # Month Section
    m_income = data['in_month']['in']
    m_expense = data['in_month']['out']
    m_net = m_income - m_expense
    m_margin = (m_net / m_income * 100) if m_income > 0 else 0
    status_icon = "🟢" if m_net >= 0 else "🔴"
    
    text += f"📅 **Current Month ({today.strftime('%B')})**\n"
    text += f"  💵 **Revenue:** `{format_currency(m_income)}`\n"
    text += f"  💸 **Expenses:** `{format_currency(m_expense)}`\n"
    text += f"  _Breakdown:_\n{build_cat_list(data['in_month']['cats'])}\n"
    text += f"  ▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
    text += f"  {status_icon} **Net Profit: {format_currency(m_net)}**\n"
    text += f"  📊 **Net Margin:** `{m_margin:.1f}%`\n\n"
    
    # All Time Section
    a_income = data['all_time']['in']
    a_net = a_income - data['all_time']['out']
    a_margin = (a_net / a_income * 100) if a_income > 0 else 0
    
    text += f"♾️ **All Time Performance**\n"
    text += f"  💵 Revenue: `{format_currency(a_income)}`\n"
    text += f"  💰 Net Profit: `{format_currency(a_net)}` ({a_margin:.1f}%)"
    
    keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="menu_reports")]]
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@router.callback_query(F.data == "report_prod")
async def show_production(callback: types.CallbackQuery):
    db = next(get_db())
    # Last 30 days
    today = date.today()
    start = today - timedelta(days=30)
    
    entries = db.query(DailyEntry).filter(DailyEntry.date >= start).order_by(DailyEntry.date).all()
    
    total_eggs = sum(e.eggs_collected for e in entries)
    total_broken = sum(e.eggs_broken for e in entries)
    total_feed = sum(e.feed_used_kg for e in entries)
    
    # Calculate Laying Rate (Avg Eggs / Avg Flock Size)
    avg_flock = sum(e.flock_total for e in entries) / len(entries) if entries else 0
    laying_rate = 0
    if avg_flock > 0 and entries:
        laying_rate = (total_eggs / len(entries)) / avg_flock * 100
        
    mortality = sum(e.mortality_count for e in entries)
    
    from database import Flock
    flocks = db.query(Flock).filter_by(status='ACTIVE').all()
    flock_text = "\n".join([f"• {f.name}: {f.current_count} birds" for f in flocks])
    
    db.close()
    
    # Feed Efficiency (Grams per Egg)
    feed_per_egg = (total_feed * 1000) / total_eggs if total_eggs else 0
    eff_icon = "🟢" if feed_per_egg < 160 else "🟠" # 140-160g is decent for layers
    if feed_per_egg > 200: eff_icon = "🔴"
    
    text = f"🥚 **Production Insights (Last 30 Days)**\n\n"
    text += f"📊 **Efficiency Metrics**\n"
    text += f"  • Laying Rate: `{laying_rate:.1f}%`\n"
    text += f"  • Feed Efficiency: `{feed_per_egg:.0f}g / egg` {eff_icon}\n"
    text += f"  • Broken Eggs: `{((total_broken/total_eggs)*100 if total_eggs else 0):.1f}%`\n\n"
    text += f"📉 **Resource Usage**\n"
    text += f"  • Total Feed: `{total_feed:.1f} kg`\n"
    text += f"  • Mortality: `{mortality} birds`\n\n"
    
    text += f"🐣 **Active Flocks**\n{flock_text}" if flock_text else "🐣 **Active Flocks**\n_No active flocks_"
    
    keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="menu_reports")]]
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@router.callback_query(F.data == "report_status")
async def show_status(callback: types.CallbackQuery):
    db = next(get_db())
    from database import InventoryItem, VaccinationRecord
    
    # Stock
    feed = db.query(InventoryItem).filter(InventoryItem.type == "FEED", InventoryItem.quantity > 0).all()
    meds = db.query(InventoryItem).filter(InventoryItem.type == "MEDICATION", InventoryItem.quantity > 0).all()
    
    # Calculate Burn Rate (Last 7 Days)
    today = date.today()
    start_7 = today - timedelta(days=7)
    entries_7 = db.query(DailyEntry).filter(DailyEntry.date >= start_7).all()
    avg_daily_feed = sum(e.feed_used_kg for e in entries_7) / 7 if entries_7 else 0
    
    # Health
    # Get last vaccination per flock?
    # Just list recent vaccinations
    recent_vacs = db.query(VaccinationRecord).order_by(VaccinationRecord.date.desc()).limit(5).all()
    
    db.close()
    
    text = "🏥 **Health & Inventory Status**\n\n"
    
    text += f"🍽️ **Feed Stock** (Avg usage: {avg_daily_feed:.1f} kg/day)\n"
    if not feed: text += "  _Low stock_\n"
    for f in feed:
         est_days = f.quantity / avg_daily_feed if avg_daily_feed > 0 else 99
         alert = "⚠️" if est_days < 3 else ""
         text += f"  • {f.name}: `{f.quantity} {f.unit}` (~{est_days:.1f} days) {alert}\n"
         
    text += "\n💊 **Medication Stock**\n"
    if not meds: text += "_None_\n"
    for m in meds:
         text += f"• {m.name}: {m.quantity} {m.unit}\n"
         
    text += "\n💉 **Recent Vaccinations**\n"
    if not recent_vacs: text += "_No records_\n"
    for v in recent_vacs:
         text += f"• {v.date}: {v.vaccine_name} ({v.birds_vaccinated} birds)\n"
    
    keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="menu_reports")]]
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()
