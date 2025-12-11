from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, SystemSettings
from utils import get_back_home_keyboard

router = Router()

class SettingsStates(StatesGroup):
    edit_value = State()

@router.callback_query(F.data == "menu_settings")
async def menu_settings(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🥚 Egg Price", callback_data='set_price_per_egg'),
         InlineKeyboardButton(text="📦 Crate Price", callback_data='set_price_per_crate')],
        [InlineKeyboardButton(text="⚖️ Feed Bag Weight", callback_data='set_feed_bag_weight'),
         InlineKeyboardButton(text="💸 Feed Bag Cost", callback_data='set_feed_bag_cost')],
        [InlineKeyboardButton(text="🐥 Reset Flock Count", callback_data='set_starting_flock_count')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text="⚙️ **Settings**\n\nSelect a parameter to change:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_"))
async def start_edit_setting(callback: types.CallbackQuery, state: FSMContext):
    key = callback.data.replace("set_", "")
    await state.update_data(setting_key=key)
    
    # Get current value
    db = next(get_db())
    setting = db.query(SystemSettings).filter_by(key=key).first()
    current_val = setting.value if setting else "Not Set"
    db.close()
    
    readable_key = key.replace("_", " ").title()
    
    await callback.message.edit_text(
        text=f"✏️ **Edit {readable_key}**\n\nCurrent Value: `{current_val}`\n\nEnter new value:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_settings')
    )
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
