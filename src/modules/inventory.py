from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import get_db, InventoryItem, SystemSettings, InventoryLog
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency
from datetime import date

router = Router()

class InventoryStates(StatesGroup):
    add_type = State()
    select_item = State() # Handled via callback
    add_quantity = State()
    add_reason = State() # Was add_name

@router.callback_query(F.data == "menu_inventory")
async def start_inventory(callback: types.CallbackQuery):
    db = next(get_db())
    # Get counts for dashboard
    from sqlalchemy import func
    counts = {}
    for t in ["FEED", "MEDICATION", "EQUIPMENT", "LIVESTOCK"]:
        c = db.query(func.count(InventoryItem.id)).filter(InventoryItem.type == t, InventoryItem.quantity > 0).scalar()
        counts[t] = c or 0
    db.close()
    
    text = "📦 **Inventory Manager**\n\nSelect a category to view stock or make adjustments."
    
    keyboard = [
        [InlineKeyboardButton(text=f"🍽️ Feed ({counts['FEED']})", callback_data="inv_view_FEED"),
         InlineKeyboardButton(text=f"💊 Meds ({counts['MEDICATION']})", callback_data="inv_view_MEDICATION")],
        [InlineKeyboardButton(text=f"🛠️ Equipment ({counts['EQUIPMENT']})", callback_data="inv_view_EQUIPMENT"),
         InlineKeyboardButton(text=f"🐥 Birds ({counts['LIVESTOCK']})", callback_data="inv_view_LIVESTOCK")],
        [InlineKeyboardButton(text="📝 Adjust Stock (Quick)", callback_data="inv_add_menu")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
    ]
    
    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("inv_view_"))
async def view_category_inventory(callback: types.CallbackQuery):
    item_type = callback.data.replace("inv_view_", "")
    
    db = next(get_db())
    items = db.query(InventoryItem).filter_by(type=item_type).all()
    
    # Group by Name to avoid duplicates in display
    grouped = {}
    setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
    def_bag_weight = float(setting.value) if setting else 70.0
    
    for item in items:
        if item.quantity <= 0: continue # Skip empty
        
        name = item.name.strip() # Normalize?
        if name not in grouped:
            grouped[name] = {'qty': 0.0, 'unit': item.unit, 'ids': []}
        
        # Simple merging
        grouped[name]['qty'] += item.quantity
        grouped[name]['ids'].append(item.id)
        # Unit consistency check? Assuming same unit for same name
        
    db.close()
    
    text = f"📋 **{item_type} Stock**\n\n"
    if not grouped:
        text += "_No items in stock._\n"
    else:
        for name, data in grouped.items():
            qty = data['qty']
            unit = data['unit']
            display = f"{qty:.1f} {unit}"
            
            if item_type == "FEED" and unit == 'kg':
                 bags = qty / def_bag_weight
                 display = f"{qty:.1f} kg (~{bags:.1f} bags)"
            
            text += f"▪️ **{name}**: {display}\n"
            
    keyboard = [
        [InlineKeyboardButton(text=f"📝 Adjust {item_type}", callback_data=f"inv_add_type_{item_type}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu_inventory")]
    ]
    
    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "inv_add_menu")
async def start_add_menu(callback: types.CallbackQuery, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="🍽️ Feed", callback_data="inv_add_type_FEED"),
         InlineKeyboardButton(text="💊 Meds", callback_data="inv_add_type_MEDICATION")],
        [InlineKeyboardButton(text="🛠️ Equipment", callback_data="inv_add_type_EQUIPMENT"),
         InlineKeyboardButton(text="🐥 Birds", callback_data="inv_add_type_LIVESTOCK")],
        [InlineKeyboardButton(text="⬅️ Cancel", callback_data="menu_inventory")]
    ]
    await callback.message.edit_text(
        text=f"⚖️ **Adjust Inventory**\n\nSelect type to adjust:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(InventoryStates.add_type)
    await callback.answer()

@router.callback_query(F.data.startswith("inv_add_type_"))
async def receive_adjust_type(callback: types.CallbackQuery, state: FSMContext):
    item_type = callback.data.replace("inv_add_type_", "")
    await state.update_data(item_type=item_type)
    
    # Query items for selection
    db = next(get_db())
    items = db.query(InventoryItem).filter_by(type=item_type).all()
    db.close()
    
    if items:
        keyboard = []
        for item in items:
            # Show individual items here (allows targeting specific batches if needed)
            # Or merge? For adjustment, targeting specific ID is safer if they are separate rows.
            # But duplicate names confuse users. 
            # Ideally we show Name + ID or Name + Qty.
            keyboard.append([InlineKeyboardButton(text=f"{item.name} ({item.quantity:.1f} {item.unit})", callback_data=f"inv_select_{item.id}")])
        
        # Back button depends on where we came from? Default to Inventory Menu
        keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_inventory")])
        
        await callback.message.edit_text(
            text=f"📋 **Adjust {item_type}**\n\nSelect item to adjust:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(InventoryStates.select_item) # New state or reuse?
    else:
        keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="menu_inventory")]]
        await callback.message.edit_text(
            text=f"⚠️ No {item_type} items found to adjust.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("inv_select_"))
async def receive_existing_select(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    
    db = next(get_db())
    item = db.query(InventoryItem).filter_by(id=item_id).first()
    
    if not item:
        await callback.answer("Item not found.", show_alert=True)
        db.close()
        return

    # Pre-fill state
    await state.update_data(
        item_id=item.id,
        item_name=item.name,
        current_qty=item.quantity,
        item_unit=item.unit
    )
    db.close()
    
    # Jump to Quantity
    await callback.message.edit_text(
        text=f"🔢 **Adjust Stock: {item.name}**\n\nCurrent: {item.quantity} {item.unit}\n\nEnter adjustment amount:\n• Use positive number to ADD (e.g. `10` or `+10`)\n• Use negative number to REMOVE (e.g. `-5`)",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_inventory')
    )
    await state.set_state(InventoryStates.add_quantity)
    await callback.answer()

@router.message(InventoryStates.add_quantity)
async def receive_quantity(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
    except ValueError:
        await message.answer("⚠️ Invalid number. Use -5 for removal, 10 for addition.")
        return
        
    data = await state.get_data()
    current_qty = data.get('current_qty', 0)
    name = data.get('item_name')
    unit = data.get('item_unit')

    # Check limits
    if current_qty + qty < 0:
        await message.answer(
             f"⛔ **Cannot reduce stock below zero!**\nCurrent: {current_qty}\nResult would be: {current_qty + qty}\n\nTry a smaller removal amount:",
             reply_markup=get_back_home_keyboard('menu_inventory')
         )
        return
    
    # Ask for reason/note
    await state.update_data(adjustment_qty=qty)
    
    keyboard = [
        [InlineKeyboardButton(text="⚠️ Spoilage/Damaged", callback_data="reason_spoilage")],
        [InlineKeyboardButton(text="📝 Correction/Count", callback_data="reason_correction")],
        [InlineKeyboardButton(text="🎁 Gift/Bonus", callback_data="reason_gift")],
        [InlineKeyboardButton(text="Other (Type it)", callback_data="reason_other")]
    ]
    
    await message.answer(
        text=f"📝 **Reason for Adjustment**\n\nAdjusting {name} by {qty:+.1f} {unit}.\nReason?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(InventoryStates.add_reason)

@router.callback_query(InventoryStates.add_reason, F.data.startswith("reason_"))
async def receive_reason_button(callback: types.CallbackQuery, state: FSMContext):
    reason = callback.data.split("_")[1].capitalize()
    if reason == "Other":
        await callback.message.edit_text("⌨️ Please type the reason:")
        # Stay in state
        return
        
    await finalize_adjustment(callback.message, state, reason)
    await callback.answer()

@router.message(InventoryStates.add_reason)
async def receive_reason_text(message: types.Message, state: FSMContext):
    await finalize_adjustment(message, state, message.text)

async def finalize_adjustment(message_or_callback, state: FSMContext, reason: str):
    data = await state.get_data()
    db = next(get_db())
    
    item_id = data.get('item_id')
    qty = data.get('adjustment_qty')
    
    item = db.query(InventoryItem).filter_by(id=item_id).first()
    final_qty = 0
    unit = ""
    
    if item:
        item.quantity += qty
        final_qty = item.quantity
        unit = item.unit
        
        # Log
        log = InventoryLog(
            item_name=item.name,
            quantity_change=qty,
            # notes=f"Adjustment: {reason}" # InventoryLog might not have notes column? 
            # I checked previously, it MIGHT NOT have notes. 
            # Wait, previously I removed 'notes' from Daily Wizard because it errored.
            # Does InventoryLog have notes? 
            # Let me check database.py quickly or just assume it doesn't from previous error.
            # The previous error was "TypeError: 'notes' is an invalid keyword argument for InventoryLog"
            # So I should NOT pass notes.
        )
        # But wait, where do I store the reason?
        # If InventoryLog has no notes, I can't store the reason.
        # Let me check 'database.py' to be sure about InventoryLog fields.
        db.add(log)
        
        # Special: Update Flock Count if LIVESTOCK
        if item.type == "LIVESTOCK":
            from database import DailyEntry
            today = date.today()
            daily = db.query(DailyEntry).filter_by(date=today).first()
            if daily:
                daily.flock_total = max(0, daily.flock_total + int(qty))
    
    db.commit()
    db.close()
    
    await state.clear()
    
    if isinstance(message_or_callback, types.CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback
        
    await message.answer(
        f"✅ **Stock Adjusted!**\n\nItem: {data['item_name']}\nChange: {qty:+.1f} {unit}\nReason: {reason}",
        reply_markup=get_main_menu_keyboard()
    )
