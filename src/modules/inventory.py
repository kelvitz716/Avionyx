from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import get_db, InventoryItem
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_back_home_keyboard, get_main_menu_keyboard

router = Router()

class InventoryStates(StatesGroup):
    add_name = State()
    add_type = State()
    add_quantity = State()
    add_unit = State()
    add_cost = State()

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
    await state.update_data(item_name=message.text)
    await message.answer(text="🔢 **Quantity**\n\nEnter current stock level:", reply_markup=get_back_home_keyboard('menu_inventory'))
    await state.set_state(InventoryStates.add_quantity)

@router.message(InventoryStates.add_quantity)
async def receive_quantity(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
    except ValueError:
        await message.answer("⚠️ Invalid number.")
        return
    await state.update_data(item_qty=qty)
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
        
    data = await state.get_data()
    
    db = next(get_db())
    item = InventoryItem(
        name=data['item_name'],
        type=data['item_type'],
        quantity=data['item_qty'],
        unit=data['item_unit'],
        cost_per_unit=cost
    )
    db.add(item)
    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        text="✔️ **Item Added!**",
        reply_markup=get_main_menu_keyboard()
    )
