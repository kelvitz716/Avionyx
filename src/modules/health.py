from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import get_db, InventoryItem, Flock, VaccinationRecord, InventoryLog
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_back_home_keyboard, get_main_menu_keyboard
from datetime import date, timedelta
from sqlalchemy import desc

router = Router()

class HealthStates(StatesGroup):
    select_flock = State()
    select_vaccine = State()
    enter_birds_count = State()
    enter_stock_used = State()
    next_due = State()
    confirm = State()

@router.callback_query(F.data == "menu_health")
async def start_health_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="💉 Record Vaccination", callback_data="health_vacc")],
        # Future: [InlineKeyboardButton(text="📃 History", callback_data="health_history")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
    ]
    
    await callback.message.edit_text(
        text="❤️ **Health & Vaccination**\n\nManage flock health and vaccination schedules.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "health_vacc")
async def health_vacc_start(callback: types.CallbackQuery, state: FSMContext):
    # Select Flock
    db = next(get_db())
    flocks = db.query(Flock).all() # You might want to filter by active status if you have one
    db.close()
    
    if not flocks:
        await callback.answer("No flocks found! Create a flock first.", show_alert=True)
        return
        
    keyboard = []
    for flock in flocks:
        display = f"{flock.name}"
        if hasattr(flock, 'current_count'):
             display += f" ({flock.current_count} birds)"
        keyboard.append([InlineKeyboardButton(text=display, callback_data=f"h_flock_{flock.id}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Cancel", callback_data="menu_health")])
    
    await callback.message.edit_text(
        text="📍 **Select Flock**\n\nWhich flock are you vaccinating?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(HealthStates.select_flock)
    await callback.answer()

# Kenyan Poultry Vaccination Schedule (Day: Vaccine)
# From docs/kenyan_poultry_vaccination_guide.md
VACCINE_SCHEDULE = {
    7: "Newcastle (1st)",
    10: "Gumboro (1st)",
    14: "Newcastle Booster",
    18: "Gumboro (2nd)",
    21: "Newcastle (1st) - Kienyeji",  # Week 3
    28: "Newcastle + IB",
    42: "Fowl Pox",        # Week 6
    56: "Fowl Typhoid",    # Week 8
    112: "Deworming",      # Week 16
    126: "Newcastle + IB (Layer Boost)" # Week 18+
}

@router.callback_query(HealthStates.select_flock, F.data.startswith("h_flock_"))
async def receive_flock(callback: types.CallbackQuery, state: FSMContext):
    flock_id = int(callback.data.split("_")[2])
    
    # Store flock info & Calculate Age
    db = next(get_db())
    flock = db.query(Flock).filter_by(id=flock_id).first()
    flock_name = flock.name
    flock_count = getattr(flock, 'current_count', 0)
    
    age_days = (date.today() - flock.hatch_date).days
    db.close()
    
    await state.update_data(flock_id=flock_id, flock_name=flock_name, flock_count=flock_count, flock_age=age_days)
    
    # Determine Suggestion
    suggestion = ""
    for day, vac_name in VACCINE_SCHEDULE.items():
        # Fuzzy match age (+/- 3 days)
        if abs(age_days - day) <= 3:
            suggestion = f"\n💡 **Suggested for Age {age_days} days:** _{vac_name}_"
            break
            
    # Select Vaccine from Inventory
    db = next(get_db())
    vaccines = db.query(InventoryItem).filter(InventoryItem.type == "MEDICATION", InventoryItem.quantity > 0).all()
    db.close()
    
    if not vaccines:
         await callback.message.edit_text(
             text=f"⚠️ **No Medications/Vaccines in Stock**\n\nPlease purchase vaccines in the Finance module first.",
             parse_mode="Markdown",
             reply_markup=get_back_home_keyboard("menu_health")
         )
         return

    keyboard = []
    # Prioritize suggested vaccine if found in inventory
    # Simple logic: If suggestion matches name part
    
    for v in vaccines:
        entry = [InlineKeyboardButton(text=f"{v.name} ({v.quantity} {v.unit})", callback_data=f"h_vacc_{v.id}")]
        if suggestion and any(part in v.name.lower() for part in ["newcastle", "gumboro", "pox", "typhoid"]):
            # Very basic boost, better sorting could involve exact match
            pass
        keyboard.append(entry)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="health_vacc")])
    
    await callback.message.edit_text(
        text=f"💉 **Select Vaccine**\n\nFlock: {flock_name} (Age: {age_days} days){suggestion}\nChoose from inventory:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(HealthStates.select_vaccine)
    await callback.answer()

@router.callback_query(HealthStates.select_vaccine, F.data.startswith("h_vacc_"))
async def receive_vaccine(callback: types.CallbackQuery, state: FSMContext):
    vacc_id = int(callback.data.split("_")[2])
    
    db = next(get_db())
    item = db.query(InventoryItem).filter_by(id=vacc_id).first()
    
    await state.update_data(
        vaccine_id=item.id,
        vaccine_name=item.name,
        vaccine_stock=item.quantity,
        vaccine_unit=item.unit
    )
    db.close()
    
    data = await state.get_data()
    flock_count = data.get('flock_count', 0)
    
    await callback.message.edit_text(
        text=f"🔢 **Birds Vaccinated**\n\nFlock Size: {flock_count}\n\nHow many birds did you vaccinate?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("health_vacc")
    )
    await state.set_state(HealthStates.enter_birds_count)
    await callback.answer()

@router.message(HealthStates.enter_birds_count)
async def receive_birds_count(message: types.Message, state: FSMContext):
    try:
        count = int(message.text)
        if count <= 0: raise ValueError
    except:
        await message.answer("⚠️ Please enter a valid number of birds.")
        return
        
    await state.update_data(birds_vaccinated=count)
    
    # Check if we need to ask for stock usage
    data = await state.get_data()
    unit = data.get('vaccine_unit', 'units') # Need to ensure unit is stored
    stock = data.get('vaccine_stock', 0)
    
    # If unit suggests bulk, ask usage. If 'doses', assume 1:1?
    # Actually, safest is to ALWAYS ask "How much from stock?", pre-filling specific logic if needed.
    # But for user ease:
    if unit.lower() in ['doses', 'dose']:
        # Auto-assume 1 dose per bird
        if count > stock:
             await message.answer(f"⚠️ **Not enough stock!**\nYou vaccinated {count} birds but only have {stock} doses.\n\nEnter actual stock used (or buy more first):")
             await state.set_state(HealthStates.enter_stock_used)
        else:
             await state.update_data(stock_used=float(count))
             await ask_next_due(message, state) # Proceed
    else:
        # Bottles, vials, etc.
        await message.answer(
            text=f"📉 **Stock Usage**\n\nYou vaccinated {count} birds.\nInventory: {stock} {unit}\n\nHow many **{unit}** did you use?",
            reply_markup=get_back_home_keyboard("health_vacc")
        )
        await state.set_state(HealthStates.enter_stock_used)

@router.message(HealthStates.enter_stock_used)
async def receive_stock_usage(message: types.Message, state: FSMContext):
    try:
        usage = float(message.text)
        if usage <= 0: raise ValueError
    except:
        await message.answer("⚠️ Please enter a valid number.")
        return
        
    data = await state.get_data()
    stock = data.get('vaccine_stock', 0)
    
    if usage > stock:
        await message.answer(f"⛔ **Not enough stock!**\nYou have {stock}. Try a lower amount.")
        return

    await state.update_data(stock_used=usage)
    await ask_next_due(message, state)

async def ask_next_due(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name_lower = data.get('vaccine_name', '').lower()
    
    # Logic for Next Due Recommendation
    rec_days = None
    rec_label = ""
    
    if "newcastle" in name_lower:
        if "1st" in name_lower or "first" in name_lower:
            rec_days = 7
            rec_label = "Newcastle Booster (1 wk)"
        else:
            rec_days = 90
            rec_label = "Newcastle Routine (3 mo)"
    elif "gumboro" in name_lower and ("1st" in name_lower or "first" in name_lower):
        rec_days = 10
        rec_label = "Gumboro Booster (10 days)"
    elif "deworm" in name_lower:
        rec_days = 56
        rec_label = "Deworming (8 wks)"
    
    keyboard = []
    if rec_days:
        keyboard.append([InlineKeyboardButton(text=f"🌟 {rec_label}", callback_data=f"next_{rec_days}")])
        
    keyboard.extend([
        [InlineKeyboardButton(text="📅 3 Months", callback_data="next_90")],
        [InlineKeyboardButton(text="📅 1 Month", callback_data="next_30")],
        [InlineKeyboardButton(text="📅 1 Week", callback_data="next_7")],
        [InlineKeyboardButton(text="🚫 No Reminder", callback_data="next_none")]
    ])
    
    await message.answer(
        text="⏰ **Next Due Date**\n\nWhen is the next vaccination due?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(HealthStates.next_due)

@router.callback_query(HealthStates.next_due, F.data.startswith("next_"))
async def receive_next_due(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    next_date = None
    today = date.today()
    
    if choice != "none":
        days = int(choice)
        next_date = today + timedelta(days=days)
    
    await state.update_data(next_due_date=next_date.isoformat() if next_date else None)
    
    # Confirm
    data = await state.get_data()
    
    summary = (
        f"✅ **Confirm Vaccination**\n\n"
        f"🐔 Flock: {data['flock_name']}\n"
        f"💉 Vaccine: {data['vaccine_name']}\n"
        f"🔢 Birds: {data['birds_vaccinated']} ({data['stock_used']} {data.get('vaccine_unit')} used)\n"
        f"📅 Date: {today}\n"
        f"⏰ Next Due: {next_date if next_date else 'None'}"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Confirm & Save", callback_data="health_save")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_health")]
    ]
    
    await callback.message.edit_text(text=summary, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(HealthStates.confirm)
    await callback.answer()

@router.callback_query(HealthStates.confirm, F.data == "health_save")
async def save_health(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    
    # Update Inventory
    inv = db.query(InventoryItem).filter_by(id=data['vaccine_id']).first()
    if inv:
        inv.quantity -= data['stock_used']
        db.add(InventoryLog(item_name=inv.name, quantity_change=-data['stock_used'])) 
        
    # Create Record
    import datetime
    
    next_due = None
    if data.get('next_due_date'):
         next_due = datetime.date.fromisoformat(data['next_due_date'])
         
    rec = VaccinationRecord(
        flock_id=data['flock_id'],
        vaccine_name=data['vaccine_name'],
        doses_used=data['stock_used'],
        birds_vaccinated=data['birds_vaccinated'],
        date=date.today(),
        next_due_date=next_due
    )
    db.add(rec)
    db.commit()
    db.close()
    
    await callback.message.edit_text(
        "✅ **Vaccination Recorded!**\nInventory updated.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()
