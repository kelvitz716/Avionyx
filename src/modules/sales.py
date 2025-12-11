from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency

router = Router()

class SaleStates(StatesGroup):
    mode = State()
    quantity = State()

DEFAULT_PRICE_EGG = 15.0
DEFAULT_PRICE_CRATE = 450.0

@router.callback_query(F.data == "menu_sales")
async def start_sales(callback: types.CallbackQuery, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="🥚 Per Egg", callback_data='mode_egg'),
         InlineKeyboardButton(text="📦 Per Crate", callback_data='mode_crate')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text="💰 **Record Sales**\n\nHow are you selling?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(SaleStates.mode)
    await callback.answer()

@router.callback_query(SaleStates.mode, F.data.startswith("mode_"))
async def receive_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(sale_mode=callback.data)
    unit = "eggs" if callback.data == 'mode_egg' else "crates"
    
    await callback.message.edit_text(
        text=f"🔢 **Quantity**\n\nHow many {unit} sold?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_sales') 
    )
    await state.set_state(SaleStates.quantity)
    await callback.answer()

@router.message(SaleStates.quantity)
async def receive_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please enter a valid number.")
        return

    quantity = int(message.text)
    data = await state.get_data()
    mode = data.get('sale_mode')
    
    db = next(get_db())
    price_egg_setting = db.query(SystemSettings).filter_by(key="price_per_egg").first()
    price_crate_setting = db.query(SystemSettings).filter_by(key="price_per_crate").first()
    
    price_egg = float(price_egg_setting.value) if price_egg_setting else DEFAULT_PRICE_EGG
    price_crate = float(price_crate_setting.value) if price_crate_setting else DEFAULT_PRICE_CRATE
    
    revenue = 0.0
    eggs_sold = 0
    crates_sold = 0
    
    if mode == 'mode_egg':
        revenue = quantity * price_egg
        eggs_sold = quantity
    else:
        revenue = quantity * price_crate
        crates_sold = quantity
    
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    
    if not entry:
        entry = DailyEntry(date=today)
        db.add(entry)
    
    entry.eggs_sold += eggs_sold
    entry.crates_sold += crates_sold
    entry.income += revenue
    
    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        text=f"✔️ **Sale Recorded!**\n\n"
             f"💰 Revenue: {format_currency(revenue)}\n"
             f"📦 Quantity: {quantity} {'eggs' if mode == 'mode_egg' else 'crates'}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
