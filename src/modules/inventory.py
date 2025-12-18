from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import get_db, InventoryItem, SystemSettings
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency
from datetime import date

router = Router()

class InventoryStates(StatesGroup):
    add_name = State()
    add_type = State()
    add_quantity = State()
    add_unit = State()
    add_cost = State()
    smart_confirm = State()

@router.callback_query(F.data == "menu_inventory")
async def start_inventory(callback: types.CallbackQuery):
    db = next(get_db())
    items = db.query(InventoryItem).all()
    db.close()
    
    text = "📦 **Inventory Status**\n\n"
    if not items:
        text += "_No items in stock._"
    else:
        # Get weight setting
        setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
        bag_weight = float(setting.value) if setting else 70.0
        
        for item in items:
            display_qty = f"{item.quantity} {item.unit}"
            if item.type == "FEED" and item.unit == 'kg':
                 # Dynamic Weight Per Item
                 w_setting = db.query(SystemSettings).filter_by(key=f"weight_{item.id}").first()
                 item_weight = float(w_setting.value) if w_setting else bag_weight
                 
                 bags = item.quantity / item_weight
                 display_qty = f"{item.quantity} kg (~{bags:.1f} bags)"
                 
            text += f"▪️ **{item.name}**: {display_qty}\n"
    
    keyboard = [
        [InlineKeyboardButton(text="📝 Adjust Stock (Correction)", callback_data="inv_add")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
    ]
    
    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "inv_add")
async def start_add_item(callback: types.CallbackQuery, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="🍽️ Feed", callback_data="type_FEED"),
         InlineKeyboardButton(text="💊 Medication", callback_data="type_MEDICATION")],
        [InlineKeyboardButton(text="🛠️ Equipment", callback_data="type_EQUIPMENT"),
         InlineKeyboardButton(text="🐥 Livestock (Birds)", callback_data="type_LIVESTOCK")],
        [InlineKeyboardButton(text="⬅️ Cancel", callback_data="menu_inventory")]
    ]
    await callback.message.edit_text(
        text="➕ **Add Item**\n\nSelect type:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(InventoryStates.add_type)
    await callback.answer()

@router.callback_query(InventoryStates.add_type, F.data.startswith("type_"))
async def receive_type(callback: types.CallbackQuery, state: FSMContext):
    item_type = callback.data.replace("type_", "")
    await state.update_data(item_type=item_type)
    
    # Query existing items of this type
    db = next(get_db())
    items = db.query(InventoryItem).filter_by(type=item_type).all()
    db.close()
    
    if items:
        keyboard = []
        for item in items:
            keyboard.append([InlineKeyboardButton(text=f"{item.name} ({item.quantity} {item.unit})", callback_data=f"inv_select_{item.id}")])
        
        keyboard.append([InlineKeyboardButton(text="➕ New Item", callback_data="inv_new_item")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="inv_add")])
        
        await callback.message.edit_text(
            text=f"📋 **Select {item_type}**\n\nChoose an existing item to adjust or create new:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        # We stay in add_type state or move to a selection state? 
        # Let's keep it flexible. Handlers for inv_select_ will pick it up.
    else:
        # No items, go straight to name
        await ask_new_item_name(callback, state, item_type)

@router.callback_query(F.data == "inv_new_item")
async def inv_new_item_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_type = data.get('item_type', 'ITEM')
    await ask_new_item_name(callback, state, item_type)

async def ask_new_item_name(callback, state, item_type):
    await callback.message.edit_text(
        text=f"📝 **Name**\n\nEnter the name of the {item_type.lower()}:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_inventory')
    )
    await state.set_state(InventoryStates.add_name)
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
        item_name=item.name,
        smart_unit=item.unit,
        smart_cost=item.cost_per_unit,
        using_smart=True
    )
    db.close()
    
    # Jump to Quantity
    await callback.message.edit_text(
        text=f"🔢 **Adjust Stock: {item.name}**\n\nCurrent: {item.quantity} {item.unit}\n\nHow much are you adding/removing? (Use - for removal)",
        parse_mode="Markdown"
    )
    await state.set_state(InventoryStates.add_quantity)
    await callback.answer()

@router.message(InventoryStates.add_name)
async def receive_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(item_name=name)
    
    # Smart Check
    db = next(get_db())
    existing = db.query(InventoryItem).filter(InventoryItem.name.ilike(name)).first()
    db.close()
    
    if existing:
        await state.update_data(
            smart_unit=existing.unit,
            smart_cost=existing.cost_per_unit,
            using_smart=True
        )
        keyboard = [
            [InlineKeyboardButton(text="✅ Yes, use saved details", callback_data="smart_yes")],
            [InlineKeyboardButton(text="✏️ No, enter new details", callback_data="smart_no")]
        ]
        await message.answer(
            f"🔍 **Found existing item!**\n\n"
            f"Name: {existing.name}\n"
            f"Unit: {existing.unit}\n"
            f"Cost: {format_currency(existing.cost_per_unit)}\n\n"
            f"Reuse these settings?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        # We need a new state for this confirmation, let's add it dynamically or handle here?
        # Better to add to StatesGroup, but I can't easily modify the class definition from here without replacing the whole file.
        # I'll rely on a temporary state handling or just replace the StatesGroup too.
        # Actually I'll replace the whole file content for cleanliness in this tool call logic since I'm refactoring the flow.
        await state.set_state(InventoryStates.smart_confirm)
    else:
        await state.update_data(using_smart=False)
        await message.answer(text="🔢 **Quantity**\n\nEnter current stock level:", reply_markup=get_back_home_keyboard('menu_inventory'))
        await state.set_state(InventoryStates.add_quantity)

@router.callback_query(InventoryStates.smart_confirm, F.data.startswith("smart_"))
async def receive_smart_confirm(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    if choice == "yes":
        await callback.message.edit_text(
            text="🔢 **Quantity**\n\nHow much are you adding?",
            parse_mode="Markdown"
        )
        await state.set_state(InventoryStates.add_quantity)
    else:
        await state.update_data(using_smart=False)
        await callback.message.edit_text(
            text="🔢 **Quantity**\n\nEnter current stock level:",
            parse_mode="Markdown"
        )
        await state.set_state(InventoryStates.add_quantity)
    await callback.answer()

@router.message(InventoryStates.add_quantity)
async def receive_quantity(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
    except ValueError:
        await message.answer("⚠️ Invalid number.")
        return
        
    await state.update_data(item_qty=qty)

    # Check for negative stock limit
    if qty < 0:
        db = next(get_db())
        data = await state.get_data()
        name = data.get('item_name')
        existing = db.query(InventoryItem).filter(InventoryItem.name.ilike(name)).first()
        current = existing.quantity if existing else 0
        db.close()
        
        if current + qty < 0:
             await message.answer(
                 f"⛔ **Cannot reduce stock below zero!**\nCurrent: {current}\n\nTry a smaller removal amount:",
                 reply_markup=get_back_home_keyboard('menu_inventory')
             )
             return
    
    data = await state.get_data()
    if data.get('using_smart'):
        # Skip to Finish
        await finalize_inventory_add(message, state)
    elif data.get('item_type') == "LIVESTOCK":
        # Auto-set unit to 'birds' and skip
        await state.update_data(item_unit="birds")
        await message.answer(text="💰 **Cost per Bird** (Optional, enter 0 if unknown):", reply_markup=get_back_home_keyboard('menu_inventory'))
        await state.set_state(InventoryStates.add_cost)
    else:
        await message.answer(text="📏 **Unit**\n\nEnter unit (e.g., kg, liters, pcs):", reply_markup=get_back_home_keyboard('menu_inventory'))
        await state.set_state(InventoryStates.add_unit)

@router.message(InventoryStates.add_unit)
async def receive_unit(message: types.Message, state: FSMContext):
    await state.update_data(item_unit=message.text)
    await message.answer(text="💰 **Cost per Unit** (Optional, enter 0 if unknown):", reply_markup=get_back_home_keyboard('menu_inventory'))
    await state.set_state(InventoryStates.add_cost)

@router.message(InventoryStates.add_cost)
async def receive_cost(message: types.Message, state: FSMContext):
    try:
        cost = float(message.text)
    except ValueError:
        cost = 0.0
    
    await state.update_data(item_cost=cost)
    await finalize_inventory_add(message, state)

async def finalize_inventory_add(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    
    name = data['item_name']
    
    if data.get('using_smart'):
        unit = data['smart_unit']
        cost = data['smart_cost']
        # Update quantity of existing item
        existing = db.query(InventoryItem).filter(InventoryItem.name.ilike(name)).first()
        if existing:
            existing.quantity += data['item_qty']
    else:
        unit = data['item_unit']
        cost = data.get('item_cost', 0.0)
        
        existing = db.query(InventoryItem).filter(InventoryItem.name.ilike(name)).first()
        if existing:
            existing.unit = unit
            existing.cost_per_unit = cost
            existing.quantity += data['item_qty']
        else:
            item = InventoryItem(
                name=name,
                type=data['item_type'],
                quantity=data['item_qty'],
                unit=unit,
                cost_per_unit=cost
            )
            db.add(item)
            
    # Special Logic for Livestock: Update DailyEntry Flock Count
    # This should run regardless of whether it was existing or new, as long as we added stock.
    if data.get('item_type') == "LIVESTOCK":
        today = date.today()
        from database import DailyEntry
        from sqlalchemy import desc
        entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
        if not entry:
            entry = DailyEntry(date=today)
            last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(desc(DailyEntry.date)).first()
            entry.flock_total = last.flock_total if last else 0
            db.add(entry)
        
        if entry.flock_added is None: entry.flock_added = 0
        entry.flock_added += data['item_qty']
        entry.flock_total += data['item_qty']
            
    db.commit()
    
    # Capture new values for recap
    final_qty = existing.quantity if existing else item.quantity
    final_unit = existing.unit if existing else item.unit
    
    db.close()
    
    change_qty = data['item_qty']
    change_str = f"+{change_qty}" if change_qty > 0 else f"{change_qty}"
    
    await state.clear()
    
    recap = (f"✔️ **Inventory Updated!**\n\n"
             f"📦 **{name}**\n"
             f"🔄 Change: {change_str} {final_unit}\n"
             f"📊 **New Balance: {final_qty} {final_unit}**")
             
    await message.answer(
        text=recap,
        reply_markup=get_main_menu_keyboard()
    ) if isinstance(message, types.Message) else await message.message.edit_text(text=recap, reply_markup=get_main_menu_keyboard())
