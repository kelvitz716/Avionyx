from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import get_db, InventoryItem
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency

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
        for item in items:
            text += f"▪️ **{item.name}**: {item.quantity} {item.unit}\n"
    
    keyboard = [
        [InlineKeyboardButton(text="➕ Add Item", callback_data="inv_add")],
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
        [InlineKeyboardButton(text="🛠️ Equipment", callback_data="type_EQUIPMENT")],
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
    
    await callback.message.edit_text(
        text=f"📝 **Name**\n\nEnter the name of the {item_type.lower()}:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_inventory')
    )
    await state.set_state(InventoryStates.add_name)
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
    
    data = await state.get_data()
    if data.get('using_smart'):
        # Skip to Finish
        await finalize_inventory_add(message, state)
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
            # Optionally update cost if we wanted to average, but we are keeping old cost for now
    else:
        unit = data['item_unit']
        cost = data.get('item_cost', 0.0)
        
        # New Item (or overwritten if name matched but chose No? Logic check: name matched -> existing item. 'No' means we might create duplicate or update?)
        # If 'No', we probably want to create a NEW entry or UPDATE existing?
        # Standard: Update existing details.
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
            
    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        text="✔️ **Inventory Updated!**",
        reply_markup=get_main_menu_keyboard()
    ) if isinstance(message, types.Message) else await message.message.edit_text("✔️ **Inventory Updated!**", reply_markup=get_main_menu_keyboard())
