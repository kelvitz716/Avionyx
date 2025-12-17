from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, AuditLog, InventoryItem
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
    
    db = next(get_db())
    weight_setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
    cost_setting = db.query(SystemSettings).filter_by(key="feed_bag_cost").first()
    
    bag_weight = float(weight_setting.value) if weight_setting else DEFAULT_BAG_WEIGHT
    bag_cost = float(cost_setting.value) if cost_setting else DEFAULT_BAG_COST
    
    kg_used = 0.0
    cost = 0.0
    
    if unit == 'unit_kg':
        kg_used = amount
        cost = amount * (bag_cost / bag_weight)
    else:
        kg_used = amount * bag_weight
        cost = amount * bag_cost
        
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    
    if not entry:
        entry = DailyEntry(date=today)
        db.add(entry)
        
    entry.feed_used_kg += kg_used
    entry.feed_cost += cost
    
    # Deduct from inventory
    inv_msg = ""
    if item_id:
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if item:
            # Simple conversion if units mismatch? 
            # Assuming user inputs consistent units or we handle it later.
            # Ideally Inventory should store consistently (e.g., kg).
            # If item.unit != 'kg', we might have issue.
            # For simplicity, we deduct 'amount' if unit matches, or just log note?
            # Let's deduct from 'quantity' blindly for now, assuming user knows?
            # Or better, deduct converted KG if item unit is KG?
            if item.unit.lower() in ['kg', 'kgs']:
                 item.quantity -= kg_used
            elif item.unit.lower() in ['bag', 'bags']:
                 # Convert to bags
                 bags = kg_used / bag_weight
                 item.quantity -= bags
            else:
                 # Just deduct the raw number entered? risky.
                 # Let's rely on kg_used if we can.
                 item.quantity -= amount # Fallback to raw input
            
            inv_msg = f" (Deducted from {item.name})"
            if item.quantity < 10: # Low stock warning logic could go here
                inv_msg += " ⚠️ Low Stock!"

    # Audit log
    log = AuditLog(
        user_id=callback.from_user.id,
        action="feed_recorded",
        details=f"Used: {kg_used:.2f} kg, Cost: {cost:.2f}{inv_msg}"
    )
    db.add(log)
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
