from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, InventoryItem, InventoryLog, AuditLog
from datetime import date, datetime
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency
from sqlalchemy import desc

router = Router()

class DailyWizardStates(StatesGroup):
    eggs_collected = State()
    eggs_broken = State()
    feed_select = State()
    feed_amount = State()
    feed_unit = State()
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
    await show_feed_select_menu(message, state) # Move to Feed
    
    # Get weight setting
    db = next(get_db())
    setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
    bag_weight = float(setting.value) if setting else 70.0
    db.close()
    
    keyboard = []
    if feed_items:
        for item in feed_items:
            # Dual Unit Display
            display_text = f"{item.name} ({item.quantity} {item.unit})"
            if item.type == 'FEED':
                # Get specific weight
                db = next(get_db()) # Re-open db session for this query
                w_setting = db.query(SystemSettings).filter_by(key=f"weight_{item.id}").first()
                db.close() # Close db session
                i_weight = float(w_setting.value) if w_setting else bag_weight
                
                if item.unit == 'kg':
                    bags = item.quantity / i_weight
                    display_text = f"{item.name} ({item.quantity} kg / ~{bags:.1f} bags)"
            
            keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"feedwizard_{item.id}")])
    
    keyboard.append([InlineKeyboardButton(text="Skip Feed / Generic", callback_data="feedwizard_none")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back (Eggs)", callback_data="menu_daily_wizard")])

    await message.answer(
        text="Step 2/3: **Feed** 🍽️\n\nWhat feed did you use today?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(DailyWizardStates.feed_select)

@router.callback_query(DailyWizardStates.feed_select, F.data.startswith("feedwizard_"))
async def receive_feed_select(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    if choice == "skip":
        await state.update_data(feed_skipped=True)
        await start_mortality_step(callback.message, state) # Helper
    else:
        item_id = int(choice) if choice != "none" else None
        await state.update_data(feed_item_id=item_id, feed_skipped=False)
        
        # Add Back Button
        keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_feed_select")]]
        
        await callback.message.edit_text(
            text="🍽️ **Feed Amount**\n\nHow much (kg/bags)?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(DailyWizardStates.feed_amount)
    await callback.answer()

# Also need to handle "back_to_feed_select" - implemented below or relies on state transition?
# Best to redirect to receive_broken (which shows feed select)? No, that's not easily callable as handler.
# I will create a dedicated `show_feed_select(message, state)` function to be reusable.

@router.callback_query(F.data == "back_to_feed_select")
async def back_to_feed_select(callback: types.CallbackQuery, state: FSMContext):
     # Re-trigger logic from receive_broken
     # Copy-paste logic or refactor? Refactor is cleaner.
     await show_feed_select_menu(callback.message, state)
     await callback.answer()

async def show_feed_select_menu(message_or_callback, state):
    db = next(get_db())
    feed_items = db.query(InventoryItem).filter(InventoryItem.type == "FEED", InventoryItem.quantity > 0).all()
    db.close()
    
    keyboard = []
    if feed_items:
        for item in feed_items:
            keyboard.append([InlineKeyboardButton(text=f"{item.name} ({item.quantity} {item.unit})", callback_data=f"feedwizard_{item.id}")])
    
    keyboard.append([InlineKeyboardButton(text="Skip Feed / Generic", callback_data="feedwizard_none")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back (Eggs)", callback_data="wizard_edit_eggs")]) # Or menu_daily_wizard...
    # Wait, back from Feed Select goes to... Eggs Broken? Or just restart wizard if linear?
    # User can go back to Eggs Broken... but `receive_broken` needs input.
    # Simpler: Back goes to "menu_daily_wizard" (Restart) or I implement full step back.
    # Let's say Back goes to Edit Eggs step (which is basically restart for Step 1).
    
    text = "Step 2/3: **Feed** 🍽️\n\nWhat feed did you use today?"
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        await message_or_callback.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await state.set_state(DailyWizardStates.feed_select)

@router.message(DailyWizardStates.feed_amount)
async def receive_feed_amount(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
    except:
        await message.answer("⚠️ Invalid number.")
        return
        
    await state.update_data(feed_amount=qty)
    
    # Unit
    keyboard = [
        [InlineKeyboardButton(text="⚖️ Kilograms (kg)", callback_data='unit_kg')],
        [InlineKeyboardButton(text="🎒 Bags", callback_data='unit_bag')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='back_to_feed_select')]
    ]
    await message.answer("Unit?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(DailyWizardStates.feed_unit)

@router.callback_query(DailyWizardStates.feed_unit, F.data.startswith("unit_"))
async def receive_feed_unit(callback: types.CallbackQuery, state: FSMContext):
    unit = callback.data
    await state.update_data(feed_unit=unit)
    
    # Check Stock Availability
    data = await state.get_data()
    item_id = data.get('feed_item_id')
    amount = data.get('feed_amount')
    
    if item_id:
        db = next(get_db())
        item = db.query(InventoryItem).filter_by(id=item_id).first()
        
        # Get weight
        w_setting = db.query(SystemSettings).filter_by(key=f"weight_{item_id}").first()
        g_setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
        bag_weight = float(w_setting.value) if w_setting else (float(g_setting.value) if g_setting else 70.0)
        
        db.close()
        
        if item:
            qty_needed_kg = amount
            if unit == 'unit_bag':
                qty_needed_kg = amount * bag_weight
            elif item.unit == 'bags': # Inventory is bags, user entered KG? Complexity. 
                # Assumption: Inventory is usually KG for feed.
                pass
                
            # Compare in KG (assuming item.unit is kg for FEED)
            current_kg = item.quantity
            
            if qty_needed_kg > current_kg:
                 msg = f"⚠️ **Low Stock Warning**\n\nYou have {current_kg} kg.\nYou are trying to use {qty_needed_kg} kg."
                 # For wizard, we might not want to BLOCK, but warn?
                 # User 'Module Refinement' objective said "prevent negative physical inventory".
                 # So we MUST BLOCK.
                 
                 await callback.message.edit_text(
                     f"⛔ **Not Enough Feed!**\n\nStock: {current_kg} kg\nTrying to use: {qty_needed_kg} kg\n\nPlease enter a lower amount:",
                     reply_markup=get_back_home_keyboard("wizard_edit_feed") # Back goes to feed select to retry
                 )
                 # We need to set state back to feed_amount to retry? 
                 # Or back to feed select?
                 # Let's send them to feed_amount to retry number
                 await state.set_state(DailyWizardStates.feed_amount)
                 await callback.answer()
                 return

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
    
    # Feed Details Str
    feed_str = "Skipped"
    if not data.get('feed_skipped'):
        feed_str = f"{data.get('feed_amount')} {data.get('feed_unit').replace('unit_', '')}"
        
    text = (
        "📊 **Daily Summary**\n\n"
        f"🥚 Eggs: {data.get('eggs_collected')} (Broken: {data.get('eggs_broken')})\n"
        f"🍽️ Feed: {feed_str}\n"
        f"⚰️ Mortality: {data.get('mortality_count')}\n\n"
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
            db.add(InventoryLog(item_name="Eggs", quantity_change=good, notes="Daily Collection"))
    
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
        
    # Feed
    if not data.get('feed_skipped'):
        amount = data.get('feed_amount', 0.0)
        unit = data.get('feed_unit')
        item_id = data.get('feed_item_id')
        
        # Calculate Cost & KG
        setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
        bag_weight = float(setting.value) if setting else 70.0
        
        DEFAULT_BAG_WEIGHT = bag_weight
        DEFAULT_BAG_COST = 2500.0 # Could make this config too, but cost is usually per purchase/item
        
        kg_used = amount
        cost = 0.0
        
        item = None
        if item_id:
            item = db.query(InventoryItem).filter_by(id=item_id).first()
            
        if unit == 'unit_kg':
            kg_used = amount
            if item and item.cost_per_unit:
                cost = amount * item.cost_per_unit 
        else: # Bags
            kg_used = amount * DEFAULT_BAG_WEIGHT 
            if item:
                cost = amount * item.cost_per_unit
            else:
                cost = amount * DEFAULT_BAG_COST
                
        entry.feed_used_kg += kg_used
        entry.feed_cost += cost
        
        # Deduct Inventory
        if item:
             item.quantity -= amount 
             db.add(InventoryLog(item_name=item.name, quantity_change=-amount, notes="Daily Feeding"))
    
    # Audit
    db.add(AuditLog(user_id=callback.from_user.id, action="daily_wizard", details="Completed Daily Update"))
    
    db.commit()
    db.close()
    
    await state.clear()
    await callback.message.edit_text("✅ **Records Updated!**", reply_markup=get_main_menu_keyboard())
    await callback.answer()
