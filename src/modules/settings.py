from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, SystemSettings, Flock, DailyEntry, AuditLog, InventoryItem
from utils import get_back_home_keyboard, get_main_menu_keyboard
from datetime import date, datetime
from sqlalchemy import desc

router = Router()

class SettingsStates(StatesGroup):
    edit_value = State()
    select_feed_weight = State() # Select feed for weight
    edit_feed_weight = State()   # Enter weight
    select_feed_cost = State()   # Select feed for cost
    edit_feed_cost = State()     # Enter cost
    
    # New Flock
    new_name = State()
    new_breed = State()
    new_hatch_date = State()
    new_initial_count = State()
    new_confirm = State()

@router.callback_query(F.data == "menu_settings")
async def menu_settings(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🥚 Egg Price", callback_data='set_price_per_egg'),
         InlineKeyboardButton(text="📦 Crate Price", callback_data='set_price_per_crate')],
        [InlineKeyboardButton(text="⚖️ Feed Bag Weight", callback_data='set_feed_bag_weight'),
         InlineKeyboardButton(text="💸 Feed Bag Cost", callback_data='set_feed_bag_cost')],
        [InlineKeyboardButton(text="➕ Create New Flock", callback_data='set_new_flock')],
        [InlineKeyboardButton(text="🐥 Reset Flock Count", callback_data='set_starting_flock_count')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text="⚙️ **Settings**\n\nSelect a parameter to change:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.in_({'set_feed_bag_weight', 'set_feed_bag_cost'}))
async def start_feed_setting_select(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    
    # Get Feeds
    db = next(get_db())
    feeds = db.query(InventoryItem).filter_by(type="FEED").all()
    db.close()
    
    if not feeds:
        await callback.answer("No feeds found in inventory.", show_alert=True)
        return

    await state.update_data(setting_action=action)
    
    keyboard = []
    for feed in feeds:
        keyboard.append([InlineKeyboardButton(text=feed.name, callback_data=f"feedset_{feed.id}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_settings")])
    
    title = "Select Feed to Configure"
    await callback.message.edit_text(
        f"⚙️ **{title}**\n\nChoose a feed:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    # Set state based on action
    if action == 'set_feed_bag_weight':
        await state.set_state(SettingsStates.select_feed_weight)
    else:
        await state.set_state(SettingsStates.select_feed_cost)
    await callback.answer()

@router.callback_query(SettingsStates.select_feed_weight, F.data.startswith("feedset_"))
async def receive_feed_for_weight(callback: types.CallbackQuery, state: FSMContext):
    feed_id = int(callback.data.split("_")[1])
    await state.update_data(target_feed_id=feed_id)
    
    db = next(get_db())
    feed = db.query(InventoryItem).filter_by(id=feed_id).first()
    
    # Check existing setting
    key = f"weight_{feed_id}"
    setting = db.query(SystemSettings).filter_by(key=key).first()
    val = setting.value if setting else "Not Set (Using Global 70.0)"
    db.close()
    
    await callback.message.edit_text(
        f"⚖️ **Edit Bag Weight: {feed.name}**\n\nCurrent: {val}\nEnter new weight (kg):",
        reply_markup=get_back_home_keyboard('menu_settings')
    )
    await state.set_state(SettingsStates.edit_feed_weight)
    await callback.answer()

@router.message(SettingsStates.edit_feed_weight)
async def save_feed_weight(message: types.Message, state: FSMContext):
    try:
        val = float(message.text)
        data = await state.get_data()
        feed_id = data['target_feed_id']
        key = f"weight_{feed_id}"
        
        db = next(get_db())
        setting = db.query(SystemSettings).filter_by(key=key).first()
        if not setting:
            setting = SystemSettings(key=key, value=str(val))
            db.add(setting)
        else:
            setting.value = str(val)
        
        # Log
        db.add(AuditLog(user_id=message.from_user.id, action="update_setting", details=f"Set {key} to {val}"))
        db.commit()
        db.close()
        
        await state.clear()
        await message.answer("✅ **Weight Updated!**", reply_markup=get_main_menu_keyboard())
    except ValueError:
        await message.answer("Invalid number.")

@router.callback_query(SettingsStates.select_feed_cost, F.data.startswith("feedset_"))
async def receive_feed_for_cost(callback: types.CallbackQuery, state: FSMContext):
    feed_id = int(callback.data.split("_")[1])
    await state.update_data(target_feed_id=feed_id)
    
    db = next(get_db())
    feed = db.query(InventoryItem).filter_by(id=feed_id).first()
    
    # Check existing setting
    key = f"cost_bag_{feed_id}"
    setting = db.query(SystemSettings).filter_by(key=key).first()
    val = setting.value if setting else "Not Set"
    db.close()
    
    await callback.message.edit_text(
        f"💸 **Edit Bag Cost: {feed.name}**\n\nCurrent: {val}\nEnter new cost per bag:",
        reply_markup=get_back_home_keyboard('menu_settings')
    )
    await state.set_state(SettingsStates.edit_feed_cost)
    await callback.answer()

@router.message(SettingsStates.edit_feed_cost)
async def save_feed_cost(message: types.Message, state: FSMContext):
    try:
        cost = float(message.text)
        data = await state.get_data()
        feed_id = data['target_feed_id']
        key_cost = f"cost_bag_{feed_id}"
        key_weight = f"weight_{feed_id}"
        
        db = next(get_db())
        
        # Save Bag Cost Setting
        s_cost = db.query(SystemSettings).filter_by(key=key_cost).first()
        if not s_cost:
            s_cost = SystemSettings(key=key_cost, value=str(cost))
            db.add(s_cost)
        else:
            s_cost.value = str(cost)
            
        # Get Weight to Calc Per KG
        s_weight = db.query(SystemSettings).filter_by(key=key_weight).first()
        if s_weight:
            weight = float(s_weight.value)
        else:
            # Fallback global
            g_weight = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
            weight = float(g_weight.value) if g_weight else 70.0
            
        # Update Inventory Item
        feed = db.query(InventoryItem).filter_by(id=feed_id).first()
        if feed:
            cost_kg = cost / weight if weight > 0 else 0
            feed.cost_per_unit = cost_kg
        
        # Log
        db.add(AuditLog(user_id=message.from_user.id, action="update_setting", details=f"Set {key_cost} to {cost} (Updated Item Cost/KG to {feed.cost_per_unit:.2f})"))
        db.commit()
        db.close()
        
        await state.clear()
        await message.answer("✅ **Cost Updated!**\nInventory unit cost recalculated.", reply_markup=get_main_menu_keyboard())
    except ValueError:
        await message.answer("Invalid number.")

@router.callback_query(F.data.startswith("set_"))
async def start_edit_setting(callback: types.CallbackQuery, state: FSMContext):
    # This handles generic/global settings (Price per Egg, etc)
    # Exclude the feed ones we handled above
    key_map = {
        'set_price_per_egg': ('price_per_egg', 'Price per Egg'),
        'set_price_per_crate': ('price_per_crate', 'Price per Crate'),
        'set_starting_flock_count': ('starting_flock_count', 'Starting Flock Count')
    }
    
    if callback.data not in key_map: return # Should be covered above
    
    db_key, label = key_map[callback.data]
    
    db = next(get_db())
    setting = db.query(SystemSettings).filter_by(key=db_key).first()
    current_value = setting.value if setting else "Not Set"
    db.close()
    
    await callback.message.edit_text(
        f"✏️ **Edit {label}**\n\nCurrent Value: {current_value}\n\nEnter new value:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_settings')
    )
    await state.update_data(setting_key=db_key)
    await state.set_state(SettingsStates.edit_value)
    await callback.answer()

@router.message(SettingsStates.edit_value)
async def save_setting(message: types.Message, state: FSMContext):
    data = await state.get_data()
    key = data.get('setting_key')
    new_value = message.text
    
    # Simple validation (all our settings are numbers for now)
    try:
        float(new_value)
    except ValueError:
        await message.answer("⚠️ Please enter a valid number.")
        return
        
    db = next(get_db())
    setting = db.query(SystemSettings).filter_by(key=key).first()
    if not setting:
        setting = SystemSettings(key=key, value=new_value)
        db.add(setting)
    else:
        setting.value = new_value
        
    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        text=f"✔️ **Saved!**\n\n{key.replace('_', ' ').title()} set to `{new_value}`.",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_settings') # Go back to settings menu
    )

# --- NEW FLOCK CREATION ---

@router.callback_query(F.data == "set_new_flock")
async def start_new_flock(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🆕 **New Flock Onboarding**\n\nEnter a unique name (e.g. 'Flock B - Jan 2026'):",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_settings')
    )
    await state.set_state(SettingsStates.new_name)
    await callback.answer()

@router.message(SettingsStates.new_name)
async def receive_new_name(message: types.Message, state: FSMContext):
    await state.update_data(new_name=message.text)
    
    keyboard = [
        [InlineKeyboardButton(text="Gen. Kuroiler", callback_data='breed_Kuroiler')],
        [InlineKeyboardButton(text="Gen. Broiler", callback_data='breed_Broiler')],
        [InlineKeyboardButton(text="Kenbro", callback_data='breed_Kenbro')],
        [InlineKeyboardButton(text="Layers", callback_data='breed_Layers')],
        [InlineKeyboardButton(text="Other", callback_data='breed_Other')]
    ]
    await message.answer(
        "🐥 **Breed**\n\nSelect or type breed:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(SettingsStates.new_breed)

@router.callback_query(SettingsStates.new_breed, F.data.startswith("breed_"))
async def receive_new_breed_cb(callback: types.CallbackQuery, state: FSMContext):
    breed = callback.data.split("_")[1]
    await state.update_data(new_breed=breed)
    await callback.message.edit_text(
        "📅 **Hatch Date**\n\nEnter date (YYYY-MM-DD):",
        parse_mode="Markdown"
    )
    await state.set_state(SettingsStates.new_hatch_date)
    await callback.answer()

@router.message(SettingsStates.new_hatch_date)
async def receive_hatch_date(message: types.Message, state: FSMContext):
    try:
        current_date_text = message.text
        # Basic validation attempt
        datetime.strptime(current_date_text, "%Y-%m-%d")
    except ValueError:
        await message.answer("⚠️ Invalid format. Use YYYY-MM-DD.")
        return
        
    await state.update_data(new_hatch_date=current_date_text)
    await message.answer("🔢 **Initial Count**\n\nHow many chicks?")
    await state.set_state(SettingsStates.new_initial_count)

@router.message(SettingsStates.new_initial_count)
async def receive_new_initial_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    count = int(message.text)
    await state.update_data(new_initial_count=count)
    
    data = await state.get_data()
    text = (f"Confirm New Flock:\n\n"
            f"🏷️ Name: {data.get('new_name')}\n"
            f"🐥 Breed: {data.get('new_breed')}\n"
            f"📅 Hatched: {data.get('new_hatch_date')}\n"
            f"🔢 Count: {count}")
    
    keyboard = [[InlineKeyboardButton(text="✅ Create Flock", callback_data="confirm_new_flock")]]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(SettingsStates.new_confirm)

@router.callback_query(SettingsStates.new_confirm, F.data == "confirm_new_flock")
async def confirm_new_flock(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    
    flock = Flock(
        name=data.get('new_name'),
        breed=data.get('new_breed'),
        hatch_date=datetime.strptime(data.get('new_hatch_date'), "%Y-%m-%d").date(),
        initial_count=data.get('new_initial_count'),
        status="ACTIVE"
    )
    db.add(flock)
    
    # Update Daily Entry
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    if not entry:
        entry = DailyEntry(date=today)
        last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(desc(DailyEntry.date)).first()
        entry.flock_total = last.flock_total if last else 0
        db.add(entry)
    
    if entry.flock_added is None: entry.flock_added = 0
    if entry.flock_total is None: entry.flock_total = 0
    
    entry.flock_added += flock.initial_count
    entry.flock_total += flock.initial_count

    db.add(AuditLog(user_id=callback.from_user.id, action="new_flock", details=f"Created {flock.name}"))
    db.commit()
    db.close()
    
    await state.clear()
    await callback.message.edit_text("✅ **Flock Created!**", reply_markup=get_main_menu_keyboard())
    await callback.answer()
