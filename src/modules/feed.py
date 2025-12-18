from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, AuditLog, InventoryItem, InventoryLog
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard

router = Router()

class FeedStates(StatesGroup):
    select_item = State()
    amount = State()
    unit = State()

DEFAULT_BAG_WEIGHT = 70.0
DEFAULT_BAG_COST = 2500.0

@router.callback_query(F.data == "menu_feed")
async def start_feed(callback: types.CallbackQuery, state: FSMContext):
    db = next(get_db())
    feed_items = db.query(InventoryItem).filter(InventoryItem.type == "FEED", InventoryItem.quantity > 0).all()
    db.close()
    
    if not feed_items:
        # Fallback to simple mode if no inventory
        await callback.message.edit_text(
            text="🍽️ **Feed Usage**\n\nNo feed items in Inventory. Recording as generic usage.\n\nEnter amount used:",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard()
        )
        await state.set_state(FeedStates.amount)
        await state.update_data(item_id=None)
    else:
        keyboard = []
        for item in feed_items:
            keyboard.append([InlineKeyboardButton(text=f"{item.name} ({item.quantity} {item.unit})", callback_data=f"feed_item_{item.id}")])
        keyboard.append([InlineKeyboardButton(text="Skip / Generic", callback_data="feed_item_none")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")])
        
        await callback.message.edit_text(
            text="🍽️ **Select Feed Used**:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(FeedStates.select_item)
    
    await callback.answer()

@router.callback_query(FeedStates.select_item, F.data.startswith("feed_item_"))
async def receive_item(callback: types.CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("feed_item_", "")
    if item_id == "none": item_id = None
    else: item_id = int(item_id)
    
    await state.update_data(item_id=item_id)
    
    await callback.message.edit_text(
        text="🔢 **Amount Used**\n\nEnter quantity:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_feed')
    )
    await state.set_state(FeedStates.amount)
    await callback.answer()

@router.message(FeedStates.amount)
async def receive_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid positive number.")
        return
    
    await state.update_data(feed_amount=amount)
    
    keyboard = [
        [InlineKeyboardButton(text="⚖️ Kilograms (kg)", callback_data='unit_kg')],
        [InlineKeyboardButton(text="🎒 Bags", callback_data='unit_bag')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='menu_feed')]
    ]
    
    await message.answer(
        text=f"Select Unit for **{amount}**:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(FeedStates.unit)

@router.callback_query(FeedStates.unit, F.data.startswith("unit_"))
async def receive_unit(callback: types.CallbackQuery, state: FSMContext):
    unit = callback.data
    data = await state.get_data()
    amount = data.get('feed_amount')
    item_id = data.get('item_id')
    
    today = date.today()
    
    db = next(get_db())
    # Defaults
    weight_setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
    cost_setting = db.query(SystemSettings).filter_by(key="feed_bag_cost").first()
    bag_weight = float(weight_setting.value) if weight_setting else DEFAULT_BAG_WEIGHT
    bag_cost = float(cost_setting.value) if cost_setting else DEFAULT_BAG_COST
    
    item = None
    if item_id:
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    kg_used = 0.0
    cost = 0.0
    
    if unit == 'unit_kg':
        kg_used = amount
        if item and item.cost_per_unit > 0:
            # If item unit is KG, direct mult. If Bags, need conversion.
            # Simplified: Assuming InventoryItem stores cost PER UNIT.
            if item.unit.lower() in ['bag', 'bags']:
                # Item cost is per bag. We used KG.
                # Cost = (Amount KG / Bag Weight) * Cost per Bag
                cost = (amount / bag_weight) * item.cost_per_unit
            else:
                 # Assume Unit is KG or similar linear
                 cost = amount * item.cost_per_unit
        else:
             # Fallback to Settings
             cost = amount * (bag_cost / bag_weight)
             
    else: # Bags
        kg_used = amount * bag_weight
        if item and item.cost_per_unit > 0:
             if item.unit.lower() in ['bag', 'bags']:
                 cost = amount * item.cost_per_unit
             else:
                 # Item cost is per KG?
                 cost = (amount * bag_weight) * item.cost_per_unit
        else:
             cost = amount * bag_cost
        
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    
    if not entry:
        entry = DailyEntry(date=today)
        db.add(entry)
        
    entry.feed_used_kg += kg_used
    entry.feed_cost += cost
    
    # Deduct from inventory & Log
    inv_msg = ""
    item_name = "Generic Feed"
    
    if item_id:
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if item:
            item_name = item.name
            
            # Update cache quantity
            deduction = amount # Assume unit matches for now or we rely on logs?
            # Correct logic: We should standardize. But logic above did unit conversion.
            # Let's standardize on LOGGING KG if possible, or whatever unit user used?
            # Let's log 'Quantity Change' in ITEM UNITS (InventoryItem.unit).
            # If item.unit is 'bags', we deduct bags.
            
            change = 0.0
            if item.unit.lower() in ['kg', 'kgs']:
                 change = kg_used
            elif item.unit.lower() in ['bag', 'bags']:
                 # Convert if input was kg
                 if unit == 'unit_kg': change = amount / bag_weight
                 else: change = amount
            else:
                 change = amount # Fallback
            
            item.quantity -= change
            inv_msg = f" (Deducted {change:.2f} {item.unit} from {item.name})"
            if item.quantity < 10: 
                inv_msg += " ⚠️ Low Stock!"
            
            # Log to InventoryLog
            log = InventoryLog(
                item_name=item.name,
                quantity_change= -change, # Negative
                # flock_id? We don't have flock selection here yet (User plan said 'Select Flock'), 
                # but 'Digital Clipboard' flow often assumes active flock or 'All'.
                # For now leaving flock_id blank or 'General'.
            )
            db.add(log)

    # Audit log
    audit = AuditLog(
        user_id=callback.from_user.id,
        action="feed_recorded",
        details=f"Used: {kg_used:.2f} kg, Cost: {cost:.2f}{inv_msg}"
    )
    db.add(audit)
    db.commit()
    db.close()
    
    await state.clear()
    await callback.message.edit_text(
        text=f"✔️ **Feed Recorded!**\n\n"
             f"⚖️ Used: {kg_used:.2f} kg\n"
             f"💸 Cost: {cost:.2f}{inv_msg}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

