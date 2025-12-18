from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, InventoryItem, InventoryLog, AuditLog, DailyFeedUsage
from datetime import date, datetime
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency
from sqlalchemy import desc

router = Router()

class DailyWizardStates(StatesGroup):
    eggs_collected = State()
    eggs_broken = State()
    feed_mode = State()       # single/multiple
    feed_select = State()
    feed_amount = State()
    feed_unit = State()
    multi_feed_select = State()   # for adding multiple feeds
    multi_feed_amount = State()
    multi_feed_add_more = State() # prompt to add another feed
    mortality_check = State()
    mortality_count = State()
    mortality_reason = State()
    confirm = State()

@router.callback_query(F.data == "menu_daily_wizard")
async def start_wizard(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="📝 **Daily Update**\n\nUpdate your farm records. You can skip any section.\n\n"
             "Step 1/3: **Eggs** 🥚\n"
             "How many eggs were collected?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Skip Eggs", callback_data="skip_eggs")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
        ])
    )
    await state.set_state(DailyWizardStates.eggs_collected)
    await callback.answer()

@router.callback_query(DailyWizardStates.eggs_collected, F.data == "skip_eggs")
async def skip_eggs(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(eggs_skipped=True)
    await show_feed_select_menu(callback.message, state) # Move to Step 2
    await callback.answer()

@router.message(DailyWizardStates.eggs_collected)
async def receive_eggs(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please enter a number.")
        return
        
    await state.update_data(eggs_collected=int(message.text), eggs_skipped=False)
    
    keyboard = get_back_home_keyboard("menu_daily_wizard")
    await message.answer(
        text="🥚 **Broken Eggs**\n\nHow many were broken/bad?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(DailyWizardStates.eggs_broken)

@router.message(DailyWizardStates.eggs_broken)
async def receive_broken(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please enter a number.")
        return
        
    await state.update_data(eggs_broken=int(message.text))
    await show_feed_mode_menu(message, state)




@router.callback_query(F.data == "back_to_feed_select")
async def back_to_feed_select(callback: types.CallbackQuery, state: FSMContext):
     await show_feed_mode_menu(callback.message, state)
     await callback.answer()


async def show_feed_mode_menu(message_or_callback, state: FSMContext):
    """Ask if using single or multiple feeds today."""
    keyboard = [
        [InlineKeyboardButton(text="🍽️ Single Feed Type", callback_data="dailyfeed_single")],
        [InlineKeyboardButton(text="🍽️🍽️ Multiple Feed Types", callback_data="dailyfeed_multi")],
        [InlineKeyboardButton(text="⏩ Skip Feed", callback_data="dailyfeed_skip")],
        [InlineKeyboardButton(text="⬅️ Back (Eggs)", callback_data="wizard_edit_eggs")],
        [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
    ]
    
    text = "Step 2/3: **Feed** 🍽️\n\nAre you using one type of feed or multiple types today?"
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        await message_or_callback.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await state.set_state(DailyWizardStates.feed_mode)


@router.callback_query(DailyWizardStates.feed_mode, F.data.startswith("dailyfeed_"))
async def receive_feed_mode(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]
    
    if mode == "skip":
        await state.update_data(feed_skipped=True, daily_feeds=[])
        await start_mortality_step(callback.message, state)
    else:
        await state.update_data(
            feed_mode=mode,
            daily_feeds=[],  # List to accumulate feed usages
            feed_skipped=False
        )
        await show_feed_select_menu(callback.message, state)
    
    await callback.answer()


async def show_feed_select_menu(message_or_callback, state: FSMContext):
    """Show available feeds to select from."""
    db = next(get_db())
    feed_items = db.query(InventoryItem).filter(InventoryItem.type == "FEED", InventoryItem.quantity > 0).all()
    db.close()
    
    keyboard = []
    if feed_items:
        for item in feed_items:
            # Show available quantity
            display = f"{item.name} ({item.quantity:.1f} {item.unit})"
            keyboard.append([InlineKeyboardButton(text=display, callback_data=f"feedwizard_{item.id}")])
    else:
        keyboard.append([InlineKeyboardButton(text="⚠️ No feed in stock", callback_data="feedwizard_none")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_feed_mode")])
    keyboard.append([InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")])
    
    text = "🍽️ **Select Feed**\n\nWhich feed did you use?"
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        await message_or_callback.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await state.set_state(DailyWizardStates.feed_select)


@router.callback_query(F.data == "back_to_feed_mode")
async def back_to_feed_mode(callback: types.CallbackQuery, state: FSMContext):
    await show_feed_mode_menu(callback.message, state)
    await callback.answer()


@router.callback_query(DailyWizardStates.feed_select, F.data.startswith("feedwizard_"))
async def receive_feed_select(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    if choice == "none":
        await state.update_data(feed_skipped=True)
        await start_mortality_step(callback.message, state)
    else:
        item_id = int(choice)
        db = next(get_db())
        item = db.query(InventoryItem).filter_by(id=item_id).first()
        
        if item:
            await state.update_data(
                current_feed_id=item.id,
                current_feed_name=item.name,
                current_feed_unit=item.unit,
                current_feed_stock=item.quantity
            )
        db.close()
        
        await callback.message.edit_text(
            text=f"🍽️ **{item.name}**\n\nStock: {item.quantity:.1f} {item.unit}\n\nHow much did you use (in kg)?",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("back_to_feed_select")
        )
        await state.set_state(DailyWizardStates.feed_amount)
    
    await callback.answer()



@router.message(DailyWizardStates.feed_amount)
async def receive_feed_amount(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
        if qty <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Please enter a valid positive number.")
        return
    
    data = await state.get_data()
    current_stock = data.get('current_feed_stock', 0)
    feed_name = data.get('current_feed_name', 'Feed')
    
    # Check stock availability
    if qty > current_stock:
        await message.answer(
            f"⛔ **Not Enough {feed_name}!**\n\n"
            f"Stock: {current_stock:.1f} kg\n"
            f"Trying to use: {qty} kg\n\n"
            f"Please enter a lower amount:",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("back_to_feed_select")
        )
        return
    
    # Add this feed to the daily_feeds list
    feed_id = data.get('current_feed_id')
    daily_feeds = data.get('daily_feeds', [])
    
    daily_feeds.append({
        'id': feed_id,
        'name': feed_name,
        'quantity_kg': qty
    })
    
    await state.update_data(
        daily_feeds=daily_feeds,
        current_feed_id=None,
        current_feed_name=None,
        current_feed_stock=None
    )
    
    # Check if multi-feed mode
    feed_mode = data.get('feed_mode', 'single')
    
    if feed_mode == 'multi':
        # Ask if they want to add another feed
        keyboard = [
            [InlineKeyboardButton(text="➕ Add Another Feed", callback_data="multifeed_add")],
            [InlineKeyboardButton(text="✅ Done with Feed", callback_data="multifeed_done")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_feed_select")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        
        # Show summary so far
        summary_lines = ["🍽️ **Feed Usage Today**\n"]
        total_kg = 0
        for f in daily_feeds:
            summary_lines.append(f"• {f['name']}: {f['quantity_kg']}kg")
            total_kg += f['quantity_kg']
        summary_lines.append(f"\n**Total: {total_kg}kg**")
        
        await message.answer(
            text="\n".join(summary_lines) + "\n\nAdd more feed types?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(DailyWizardStates.multi_feed_add_more)
    else:
        # Single feed mode - proceed to mortality
        await start_mortality_step(message, state)


@router.callback_query(DailyWizardStates.multi_feed_add_more, F.data.startswith("multifeed_"))
async def receive_multi_feed_choice(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    if choice == "add":
        # Show feed selection again
        await show_feed_select_menu(callback.message, state)
    else:
        # Done - proceed to mortality
        await start_mortality_step(callback.message, state)
    
    await callback.answer()



async def start_mortality_step(message: types.Message, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="✅ All Good (0 Deaths)", callback_data="mort_zero")],
        [InlineKeyboardButton(text="⚰️ Record Mortality", callback_data="mort_record")],
        [InlineKeyboardButton(text="⬅️ Back (Feed)", callback_data="back_to_feed_select")]
    ]
    msg_text = "Step 3/3: **Mortality** 🐣\n\nAny losses today?"
    
    if isinstance(message, types.CallbackQuery): # Edge case handling if passed callback object
        await message.message.edit_text(text=msg_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    else:
        await message.answer(text=msg_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
        
    await state.set_state(DailyWizardStates.mortality_check)

@router.callback_query(DailyWizardStates.mortality_check, F.data.startswith("mort_"))
async def receive_mortality_check(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    if choice == "zero":
        await state.update_data(mortality_count=0)
        await show_summary(callback.message, state)
    else:
        # Add Back Button support
        keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_mortality_start")]]
        await callback.message.edit_text("⚰️ **Mortality Count**\n\nHow many died?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await state.set_state(DailyWizardStates.mortality_count)
    await callback.answer()
    
# Backward navigation for mortality
@router.callback_query(F.data == "back_to_mortality_start")
async def back_to_mortality_start(callback: types.CallbackQuery, state: FSMContext):
    await start_mortality_step(callback.message, state)
    await callback.answer()

@router.message(DailyWizardStates.mortality_count)
async def receive_mortality_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    count = int(message.text)
    await state.update_data(mortality_count=count)
    
    if count > 0:
        keyboard = [
            [InlineKeyboardButton(text="🦠 Sickness", callback_data='reason_sickness')],
            [InlineKeyboardButton(text="❓ Unknown", callback_data='reason_unknown')],
            [InlineKeyboardButton(text="⬅️ Back", callback_data='back_to_mortality_start')]
        ]
        await message.answer("Reason?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await state.set_state(DailyWizardStates.mortality_reason)
    else:
        await show_summary(message, state)

@router.callback_query(DailyWizardStates.mortality_reason, F.data.startswith("reason_"))
async def receive_reason(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(mortality_reason=callback.data.split("_")[1])
    await show_summary(callback.message, state)
    await callback.answer()

# Summary & Edit Handlers
@router.callback_query(F.data == "wizard_edit_eggs")
async def wizard_edit_eggs(callback: types.CallbackQuery, state: FSMContext):
    await start_wizard(callback, state) # Restart from step 1
    
@router.callback_query(F.data == "wizard_edit_feed")
async def wizard_edit_feed(callback: types.CallbackQuery, state: FSMContext):
    await show_feed_select_menu(callback, state)

@router.callback_query(F.data == "wizard_edit_mortality")
async def wizard_edit_mortality(callback: types.CallbackQuery, state: FSMContext):
    await start_mortality_step(callback.message, state)

async def show_summary(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Feed Details Str - now supports multi-feed
    feed_str = "Skipped"
    if not data.get('feed_skipped'):
        daily_feeds = data.get('daily_feeds', [])
        if daily_feeds:
            feed_parts = []
            total_kg = 0
            for f in daily_feeds:
                feed_parts.append(f"{f['name']}: {f['quantity_kg']}kg")
                total_kg += f['quantity_kg']
            feed_str = ", ".join(feed_parts) if len(feed_parts) <= 2 else f"{len(feed_parts)} types, {total_kg}kg total"
        elif data.get('feed_amount'):
            # Legacy fallback
            unit = data.get('feed_unit', 'kg')
            if unit:
                unit = unit.replace('unit_', '')
            feed_str = f"{data.get('feed_amount')} {unit}"
        
    text = (
        "📊 **Daily Summary**\n\n"
        f"🥚 Eggs: {data.get('eggs_collected', 0)} (Broken: {data.get('eggs_broken', 0)})\n"
        f"🍽️ Feed: {feed_str}\n"
        f"⚰️ Mortality: {data.get('mortality_count', 0)}\n\n"
        "Save this record?"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="💾 Save Record", callback_data="wizard_save")],
        [InlineKeyboardButton(text="✏️ Edit Eggs", callback_data="wizard_edit_eggs"),
         InlineKeyboardButton(text="✏️ Edit Feed", callback_data="wizard_edit_feed")],
        [InlineKeyboardButton(text="✏️ Edit Mortality", callback_data="wizard_edit_mortality")]
    ]
    
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    else:
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
        
    await state.set_state(DailyWizardStates.confirm)

@router.callback_query(DailyWizardStates.confirm, F.data == "wizard_save")
async def save_wizard(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    today = date.today()
    
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    if not entry:
        entry = DailyEntry(date=today)
        last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(desc(DailyEntry.date)).first()
        entry.flock_total = last.flock_total if last else 0
        db.add(entry)
        
    # Initialization Fixes (Handle None)
    if entry.eggs_collected is None: entry.eggs_collected = 0
    if entry.eggs_broken is None: entry.eggs_broken = 0
    if entry.eggs_good is None: entry.eggs_good = 0
    if entry.mortality_count is None: entry.mortality_count = 0
    if entry.flock_total is None: entry.flock_total = 0
    if entry.feed_used_kg is None: entry.feed_used_kg = 0.0
    if entry.feed_cost is None: entry.feed_cost = 0.0
    if entry.flock_added is None: entry.flock_added = 0
    if entry.flock_removed is None: entry.flock_removed = 0
    if entry.eggs_sold is None: entry.eggs_sold = 0
    if entry.crates_sold is None: entry.crates_sold = 0
    if entry.income is None: entry.income = 0.0
        
    # Eggs
    if not data.get('eggs_skipped'):
        collected = data.get('eggs_collected', 0)
        broken = data.get('eggs_broken', 0)
        good = collected - broken
        
        entry.eggs_collected += collected
        entry.eggs_broken += broken
        entry.eggs_good = entry.eggs_collected - entry.eggs_broken
        
        # SYNC TO INVENTORY (The "Repository")
        # Find or Create 'Eggs' item
        egg_item = db.query(InventoryItem).filter_by(name="Eggs").first()
        if not egg_item:
            egg_item = InventoryItem(name="Eggs", type="PRODUCE", quantity=0, unit="eggs", cost_per_unit=15.0) # Default cost
            db.add(egg_item)
            db.flush()
        
        if good > 0:
            egg_item.quantity += good
            db.add(InventoryLog(item_name="Eggs", quantity_change=good))
    
    # Mortality
    m_count = data.get('mortality_count', 0)
    # Only update if user actually visited mortality step and set a count?
    # Logic in checks: if m_count > 0 it updates.
    # What if they entered 0? It does nothing.
    # We should arguably have a 'mortality_skipped' flag too if we add a skip button there.
    # For now, 0 implies no change or no mortality.
    
    if m_count > 0:
        entry.mortality_count += m_count
        entry.flock_total = max(0, entry.flock_total - m_count)
        reason = data.get('mortality_reason', 'unknown')
        entry.mortality_reasons = f"{entry.mortality_reasons}, {reason} ({m_count})" if entry.mortality_reasons else f"{reason} ({m_count})"
        
    # Feed - Now supports multiple feeds
    daily_feeds = data.get('daily_feeds', [])
    if not data.get('feed_skipped') and daily_feeds:
        total_kg = 0.0
        total_cost = 0.0
        
        # Ensure entry is flushed to get ID for foreign key
        db.flush()
        
        for feed_data in daily_feeds:
            feed_id = feed_data.get('id')
            qty_kg = feed_data.get('quantity_kg', 0)
            feed_name = feed_data.get('name', 'Unknown Feed')
            
            # Get the inventory item
            item = None
            if feed_id:
                item = db.query(InventoryItem).filter_by(id=feed_id).first()
            
            # Calculate cost
            cost = 0.0
            if item and item.cost_per_unit:
                cost = qty_kg * item.cost_per_unit
            
            total_kg += qty_kg
            total_cost += cost
            
            # Deduct from inventory
            if item:
                item.quantity -= qty_kg
                db.add(InventoryLog(item_name=item.name, quantity_change=-qty_kg))
            
            # Create DailyFeedUsage record
            if feed_id:
                usage = DailyFeedUsage(
                    daily_entry_id=entry.id,
                    feed_item_id=feed_id,
                    quantity_kg=qty_kg
                )
                db.add(usage)
        
        entry.feed_used_kg += total_kg
        entry.feed_cost += total_cost
    
    # Legacy support for single feed flow (if daily_feeds is empty but old data exists)
    elif not data.get('feed_skipped') and data.get('feed_amount'):
        amount = data.get('feed_amount', 0.0)
        item_id = data.get('current_feed_id')
        
        if item_id:
            item = db.query(InventoryItem).filter_by(id=item_id).first()
            if item:
                cost = amount * (item.cost_per_unit or 0)
                entry.feed_used_kg += amount
                entry.feed_cost += cost
                item.quantity -= amount
                db.add(InventoryLog(item_name=item.name, quantity_change=-amount))
    
    # Audit
    db.add(AuditLog(user_id=callback.from_user.id, action="daily_wizard", details="Completed Daily Update"))
    
    db.commit()
    db.close()
    
    await state.clear()
    await callback.message.edit_text("✅ **Records Updated!**", reply_markup=get_main_menu_keyboard())
    await callback.answer()
