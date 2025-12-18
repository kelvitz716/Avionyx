from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_db, DailyEntry, AuditLog, InventoryLog
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard

router = Router()

class EggStates(StatesGroup):
    count = State()
    broken = State()

@router.callback_query(F.data == "menu_eggs")
async def start_egg_collection(callback: types.CallbackQuery, state: FSMContext):
    db = next(get_db())
    today = date.today()
    # Find last entry with eggs data
    last_entry = db.query(DailyEntry).filter(DailyEntry.date < today, DailyEntry.eggs_collected > 0).order_by(DailyEntry.date.desc()).first()
    db.close()
    
    suggestion = ""
    if last_entry:
        suggestion = f"_(Yesterday: {last_entry.eggs_collected})_"

    await callback.message.edit_text(
        text=f"🥚 **Egg Collection**\n{suggestion}\n\nHow many eggs were collected today?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard()
    )
    await state.set_state(EggStates.count)
    await callback.answer()

@router.message(EggStates.count)
async def receive_egg_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please enter a valid number.")
        return
    
    await state.update_data(eggs_total=int(message.text))
    await message.answer(
        text="❌ **Broken Eggs**\n\nHow many eggs were broken? (Enter 0 if none)",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard()
    )
    await state.set_state(EggStates.broken)

@router.message(EggStates.broken)
async def receive_broken_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please enter a valid number.")
        return
    
    data = await state.get_data()
    eggs_total = data['eggs_total']
    eggs_broken = int(message.text)
    
    if eggs_broken > eggs_total:
         await message.answer("⚠️ Broken eggs cannot exceed total collected. Try again.")
         return

    eggs_good = eggs_total - eggs_broken
    today = date.today()
    
    db = next(get_db())
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    if not entry:
        entry = DailyEntry(date=today)
        db.add(entry)
    
    entry.eggs_collected = eggs_total
    entry.eggs_broken = eggs_broken
    entry.eggs_good = eggs_good
    
    # Log Inventory Production (Good Eggs)
    inv_log = InventoryLog(
        item_name="Eggs",
        quantity_change=eggs_good,
        flock_id="General" # Placeholder
    )
    db.add(inv_log)
    
    # Update Stock Cache
    from database import InventoryItem
    egg_item = db.query(InventoryItem).filter_by(name="Eggs").first()
    if not egg_item:
        egg_item = InventoryItem(
            name="Eggs",
            type="PRODUCE",
            quantity=0,
            unit="eggs",
            cost_per_unit=0 # Product, not expense
        )
        db.add(egg_item)
        db.flush()
        
    egg_item.quantity += eggs_good
    new_quantity = egg_item.quantity
    
    # Audit log
    log = AuditLog(
        user_id=message.from_user.id,
        action="eggs_collected",
        details=f"Total: {eggs_total}, Broken: {eggs_broken}, Good: {eggs_good}"
    )
    db.add(log)
    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        text=f"✔️ **Saved!**\n\n"
             f"🥚 Total: {eggs_total}\n"
             f"❌ Broken: {eggs_broken}\n"
             f"✅ Good: {eggs_good} (Added to Stock: {new_quantity})",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

