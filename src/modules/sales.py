from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, BirdSale, Transaction
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency

router = Router()

class SaleStates(StatesGroup):
    mode = State()
    quantity = State()
    price = State() # For manual price input (Birds)

DEFAULT_PRICE_EGG = 15.0
DEFAULT_PRICE_CRATE = 450.0

@router.callback_query(F.data == "menu_sales")
async def start_sales(callback: types.CallbackQuery, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="🥚 Per Egg", callback_data='mode_egg'),
         InlineKeyboardButton(text="📦 Per Crate", callback_data='mode_crate')],
        [InlineKeyboardButton(text="🐥 Sell Birds (Culls)", callback_data='mode_bird')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')]
    ]
    
    await callback.message.edit_text(
        text="💰 **Record Sales**\n\nSelect category:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(SaleStates.mode)
    await callback.answer()

@router.callback_query(SaleStates.mode, F.data.startswith("mode_"))
async def receive_mode(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data
    await state.update_data(sale_mode=mode)
    
    unit = "eggs"
    if mode == 'mode_crate': unit = "crates"
    elif mode == 'mode_bird': unit = "birds"
    
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
    await state.update_data(quantity=quantity)
    data = await state.get_data()
    mode = data.get('sale_mode')
    
    if mode == 'mode_bird':
        # Ask for price for birds
        await message.answer(
            text=f"💸 **Price**\n\nEnter price PER BIRD:",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard('menu_sales')
        )
        await state.set_state(SaleStates.price)
        return

    # Process Eggs/Crates immediately
    await process_sale(message, state, quantity, None)

@router.message(SaleStates.price)
async def receive_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        if price < 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid price.")
        return
        
    data = await state.get_data()
    quantity = data.get('quantity')
    
    await process_sale(message, state, quantity, price)

async def process_sale(message: types.Message, state: FSMContext, quantity: int, manual_price: float):
    data = await state.get_data()
    mode = data.get('sale_mode')
    
    db = next(get_db())
    
    revenue = 0.0
    details = ""
    
    if mode in ['mode_egg', 'mode_crate']:
        price_egg_setting = db.query(SystemSettings).filter_by(key="price_per_egg").first()
        price_crate_setting = db.query(SystemSettings).filter_by(key="price_per_crate").first()
        
        price_egg = float(price_egg_setting.value) if price_egg_setting else DEFAULT_PRICE_EGG
        price_crate = float(price_crate_setting.value) if price_crate_setting else DEFAULT_PRICE_CRATE
        
        today = date.today()
        entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
        if not entry:
            entry = DailyEntry(date=today)
            db.add(entry)
            
        if mode == 'mode_egg':
            revenue = quantity * price_egg
            entry.eggs_sold += quantity
            details = f"{quantity} Eggs"
        else:
            revenue = quantity * price_crate
            entry.crates_sold += quantity
            details = f"{quantity} Crates"
            
        entry.income += revenue
        
        # Log Transaction for Egg Sales (Aggregated or Individual?)
        # Let's log individual transaction for visibility in P&L
        txn = Transaction(
            type="INCOME",
            category="Egg Sales",
            amount=revenue,
            description=f"Sold {details}",
            related_table="daily_entries", # rough link
            related_id=entry.id 
        )
        db.add(txn)
        
    elif mode == 'mode_bird':
        revenue = quantity * manual_price
        
        bird_sale = BirdSale(
            quantity=quantity,
            price_per_bird=manual_price,
            total_amount=revenue
        )
        db.add(bird_sale)
        db.flush()
        
        txn = Transaction(
            type="INCOME",
            category="Bird Sales",
            amount=revenue,
            description=f"Sold {quantity} birds @ {manual_price}",
            related_id=bird_sale.id,
            related_table="bird_sales"
        )
        db.add(txn)
        details = f"{quantity} Birds"
        
        # Should we remove from Flock count?
        # Yes!
        today = date.today()
        entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
        if not entry:
            entry = DailyEntry(date=today)
            last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(DailyEntry.date.desc()).first()
            entry.flock_total = last.flock_total if last else 0
            db.add(entry)
            
        if entry.flock_removed is None: entry.flock_removed = 0
        entry.flock_removed += quantity
        entry.flock_total -= quantity

    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        text=f"✔️ **Sale Recorded!**\n\n"
        f"💰 Revenue: {format_currency(revenue)}\n"
        f"📦 Sold: {details}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
