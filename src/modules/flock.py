from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, AuditLog
from datetime import date
from sqlalchemy import desc
from utils import get_back_home_keyboard, get_main_menu_keyboard

router = Router()

class FlockStates(StatesGroup):
    action = State()
    count = State()
    reason = State()

def get_current_flock_count(db):
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    if entry and entry.flock_total > 0:
        return entry.flock_total
    
    last_entry = db.query(DailyEntry).order_by(desc(DailyEntry.date)).first()
    if last_entry:
        return last_entry.flock_total
        
    setting = db.query(SystemSettings).filter_by(key="starting_flock_count").first()
    return int(setting.value) if setting else 0

@router.callback_query(F.data.in_({"menu_flock", "menu_mortality"}))
async def start_flock(callback: types.CallbackQuery, state: FSMContext):
    db = next(get_db())
    current = get_current_flock_count(db)
    db.close()
    
    keyboard = [
        [InlineKeyboardButton(text="➕ Add Birds", callback_data='action_add'),
         InlineKeyboardButton(text="➖ Remove Birds", callback_data='action_remove')],
        [InlineKeyboardButton(text="⚰️ Record Mortality", callback_data='action_mortality')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text=f"🐥 **Flock Management**\nCurrent Flock: **{current}**\n\nChoose action:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(FlockStates.action)
    await callback.answer()

@router.callback_query(FlockStates.action, F.data.startswith("action_"))
async def receive_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    await state.update_data(flock_action=action)
    
    prompt = "How many birds to **ADD**?"
    if action == 'action_remove':
        prompt = "How many birds to **REMOVE**?"
    elif action == 'action_mortality':
        prompt = "How many birds **DIED**?"
        
    await callback.message.edit_text(
        text=f"{prompt}\n\nEnter number:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('menu_flock')
    )
    await state.set_state(FlockStates.count)
    await callback.answer()

@router.message(FlockStates.count)
async def receive_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please enter a valid number.")
        return
        
    count = int(message.text)
    await state.update_data(flock_count=count)
    data = await state.get_data()
    action = data.get('flock_action')
    
    if action == 'action_mortality':
        keyboard = [
            [InlineKeyboardButton(text="🦠 Sickness", callback_data='reason_sickness'),
             InlineKeyboardButton(text="🦊 Predator", callback_data='reason_predator')],
            [InlineKeyboardButton(text="❓ Unknown", callback_data='reason_unknown'),
             InlineKeyboardButton(text="Other", callback_data='reason_other')],
             [InlineKeyboardButton(text="⬅️ Back", callback_data='menu_flock')]
        ]
        await message.answer(
            text="Checking... What was the cause?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(FlockStates.reason)
        return
    
    await process_flock_update(message, state, message.from_user.id)

@router.callback_query(FlockStates.reason, F.data.startswith("reason_"))
async def receive_reason(callback: types.CallbackQuery, state: FSMContext):
    reason = callback.data.replace('reason_', '')
    await state.update_data(flock_reason=reason)
    await process_flock_update(callback.message, state, callback.from_user.id) # reuse msg object
    await callback.answer()

async def process_flock_update(message: types.Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    action = data.get('flock_action')
    count = data.get('flock_count')
    reason = data.get('flock_reason', "")
    
    db = next(get_db())
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    
    if not entry:
        entry = DailyEntry(date=today)
        last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(desc(DailyEntry.date)).first()
        entry.flock_total = last.flock_total if last else 0
        db.add(entry)
    elif entry.flock_total == 0:
         last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(desc(DailyEntry.date)).first()
         if last: entry.flock_total = last.flock_total

    if action == 'action_add':
        if entry.flock_added is None: entry.flock_added = 0
        if entry.flock_total is None: entry.flock_total = 0
        entry.flock_added += count
        entry.flock_total += count
    elif action == 'action_remove':
        if entry.flock_removed is None: entry.flock_removed = 0
        if entry.flock_total is None: entry.flock_total = 0
        entry.flock_removed += count
        entry.flock_total -= count
    elif action == 'action_mortality':
        if entry.mortality_count is None: entry.mortality_count = 0
        if entry.flock_total is None: entry.flock_total = 0
        entry.mortality_count += count
        entry.flock_total -= count
        entry.mortality_reasons = f"{entry.mortality_reasons}, {reason} ({count})" if entry.mortality_reasons else f"{reason} ({count})"

    # Audit log
    log = AuditLog(
        user_id=user_id,
        action=f"flock_{action.replace('action_', '')}",
        details=f"Count: {count}, Reason: {reason}, Total: {entry.flock_total}"
    )
    db.add(log)
    db.commit()
    new_total = entry.flock_total
    db.close()
    
    msg = ""
    if action == 'action_add': msg = f"➕ Added {count} birds."
    elif action == 'action_remove': msg = f"➖ Removed {count} birds."
    elif action == 'action_mortality': msg = f"⚰️ Recorded {count} deaths ({reason})."
    
    await state.clear()
    await message.answer(
        text=f"✔️ **Updated!**\n\n{msg}\nTotal Flock: **{new_total}**",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
