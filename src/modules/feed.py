from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, AuditLog
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard

router = Router()

class FeedStates(StatesGroup):
    amount = State()
    unit = State()

DEFAULT_BAG_WEIGHT = 70.0
DEFAULT_BAG_COST = 2500.0

@router.callback_query(F.data == "menu_feed")
async def start_feed(callback: types.CallbackQuery, state: FSMContext):
    db = next(get_db())
    today = date.today()
    # Find last entry with feed data
    last_entry = db.query(DailyEntry).filter(DailyEntry.date < today, DailyEntry.feed_used_kg > 0).order_by(DailyEntry.date.desc()).first()
    db.close()

    suggestion = ""
    if last_entry:
        suggestion = f"_(Last: {last_entry.feed_used_kg:.1f} kg)_"

    await callback.message.edit_text(
        text=f"🍽️ **Feed Usage**\n{suggestion}\n\nEnter amount used:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard()
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
    
    # Audit log
    log = AuditLog(
        user_id=callback.from_user.id,
        action="feed_recorded",
        details=f"Used: {kg_used:.2f} kg, Cost: {cost:.2f}"
    )
    db.add(log)
    db.commit()
    db.close()
    
    await state.clear()
    await callback.message.edit_text(
        text=f"✔️ **Feed Recorded!**\n\n"
             f"⚖️ Used: {kg_used:.2f} kg\n"
             f"💸 Cost: {cost:.2f}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
