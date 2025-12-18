from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, DailyEntry, SystemSettings, FinancialLedger, InventoryLog, Contact
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency

router = Router()

class SaleStates(StatesGroup):
    customer_id = State()
    mode = State()
    quantity = State()
    price = State() # For manual price input (Birds) or override
    payment_method = State()
    transaction_ref = State()

DEFAULT_PRICE_EGG = 15.0
DEFAULT_PRICE_CRATE = 450.0

@router.callback_query(F.data == "menu_sales")
async def start_sales(callback: types.CallbackQuery, state: FSMContext):
    # Step 1: Select Customer
    db = next(get_db())
    customers = db.query(Contact).filter_by(role="CUSTOMER").all()
    db.close()
    
    keyboard = []
    for c in customers:
        keyboard.append([InlineKeyboardButton(text=f"👤 {c.name}", callback_data=f"cust_{c.id}")])
    
    # Add generic/walk-in option if needed, but we want to encourage entities
    keyboard.append([InlineKeyboardButton(text="🚶 Walk-in / Generic", callback_data="cust_generic")])
    keyboard.append([InlineKeyboardButton(text="➕ Add New Customer", callback_data="menu_add_contact_redirect")]) # Placeholder
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data='main_menu')])
    
    await callback.message.edit_text(
        text="💰 **New Sale**\n\nSelect the Customer:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(SaleStates.customer_id)
    await callback.answer()

@router.callback_query(SaleStates.customer_id, F.data.startswith("cust_"))
async def select_customer(callback: types.CallbackQuery, state: FSMContext):
    cust_id = callback.data.split("_")[1]
    if cust_id == "generic":
        cust_id = None
        cust_name = "Walk-in Information"
    else:
        db = next(get_db())
        cust = db.query(Contact).filter_by(id=cust_id).first()
        cust_name = cust.name if cust else "Unknown"
        db.close()

    await state.update_data(customer_id=cust_id, customer_name=cust_name)
    
    # Step 2: Select Item Mode
    keyboard = [
        [InlineKeyboardButton(text="🥚 Per Egg", callback_data='mode_egg'),
         InlineKeyboardButton(text="📦 Per Crate", callback_data='mode_crate')],
        [InlineKeyboardButton(text="🐥 Sell Birds (Culls/Stock)", callback_data='mode_bird')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='menu_sales')]
    ]
    
    await callback.message.edit_text(
        text=f"🛒 **Selling to: {cust_name}**\n\nWhat are they buying?",
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
        text=f"🔢 **Quantity**\n\nHow many {unit}?",
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
    
    # Calculate price or ask for it
    if mode == 'mode_bird':
        await message.answer(
            text=f"💸 **Price**\n\nEnter TOTAL price for {quantity} birds (or price per bird if you prefer, but I need final total):", # Simplification: Ask for Total or Per unit? 
            # User prompt said: "/sell Broilers 50 25000" (Total 25000)
            # Let's ask for Total Price to be flexible
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard('menu_sales')
        )
        await state.set_state(SaleStates.price)
    else:
        # Auto-calc for eggs
        db = next(get_db())
        price_egg = float(db.query(SystemSettings).filter_by(key="price_per_egg").first().value) if db.query(SystemSettings).filter_by(key="price_per_egg").first() else DEFAULT_PRICE_EGG
        price_crate = float(db.query(SystemSettings).filter_by(key="price_per_crate").first().value) if db.query(SystemSettings).filter_by(key="price_per_crate").first() else DEFAULT_PRICE_CRATE
        db.close()
        
        total_price = quantity * price_egg if mode == 'mode_egg' else quantity * price_crate
        await state.update_data(total_price=total_price)
        
        # Confirm price or allow override?
        # Let's just go to payment
        await ask_payment_method(message, state, total_price)

@router.message(SaleStates.price)
async def receive_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        if price < 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid price.")
        return
        
    await state.update_data(total_price=price)
    await ask_payment_method(message, state, price)

async def ask_payment_method(message: types.Message, state: FSMContext, amount: float):
    keyboard = [
        [InlineKeyboardButton(text="💵 Cash", callback_data='pay_CASH')],
        [InlineKeyboardButton(text="📱 M-Pesa", callback_data='pay_MPESA')],
        [InlineKeyboardButton(text="💳 Credit / Later", callback_data='pay_CREDIT')]
    ]
    
    await message.answer(
        text=f"💳 **Payment**\n\nTotal: {format_currency(amount)}\nMethod?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(SaleStates.payment_method)

@router.callback_query(SaleStates.payment_method, F.data.startswith("pay_"))
async def receive_payment_method(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    await state.update_data(payment_method=method)
    
    if method == "MPESA":
        await callback.message.edit_text(
            text="📲 **M-Pesa Reference**\n\nEnter the MPESA Transaction Code (e.g. QKD...):",
            parse_mode="Markdown"
        )
        await state.set_state(SaleStates.transaction_ref)
    else:
        await finalize_sale(callback.message, state) # No code needed for Cash/Credit
    
    await callback.answer()

@router.message(SaleStates.transaction_ref)
async def receive_ref(message: types.Message, state: FSMContext):
    ref = message.text.upper()
    await state.update_data(transaction_ref=ref)
    await finalize_sale(message, state)

async def finalize_sale(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    
    mode = data.get('sale_mode')
    qty = data.get('quantity')
    total = data.get('total_price')
    method = data.get('payment_method')
    ref = data.get('transaction_ref', None) # None if Cash
    cust_id = data.get('customer_id') # Can be None (Walk-in)
    
    item_name = "Eggs"
    if mode == 'mode_crate': item_name = "Egg Crates"
    elif mode == 'mode_bird': item_name = "Birds/Meat"
    
    # 1. Create Financial Ledger Entry
    ledger = FinancialLedger(
        amount=total,
        direction="IN",
        payment_method=method,
        transaction_ref=ref,
        category="Sales",
        description=f"Sold {qty} {item_name}",
        contact_id=cust_id
    )
    db.add(ledger)
    db.flush() # Get ID
    
    # 2. Update Inventory Log
    inv = InventoryLog(
        item_name=item_name,
        quantity_change=-qty, # Negative for sale
        ledger_id=ledger.id
    )
    db.add(inv)
    
    # 3. Update Daily Entry (For stats)
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    if not entry:
        entry = DailyEntry(date=today)
        # Carry over flock total if needed
        last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(DailyEntry.date.desc()).first()
        entry.flock_total = last.flock_total if last else 0
        db.add(entry)
    
    entry.income += total
    if mode == 'mode_egg': entry.eggs_sold += qty
    elif mode == 'mode_crate': entry.crates_sold += qty
    elif mode == 'mode_bird':
        if entry.flock_removed is None: entry.flock_removed = 0
        entry.flock_removed += qty
        entry.flock_total -= qty

    db.commit()
    cust_name = data.get('customer_name')
    
    # 4. Update InventoryItem Stock (Harmonization)
    from database import InventoryItem
    
    # helper to find and deduct
    def deduct_stock(name_query, amount):
        # sensitive case match first, then ilike
        item = db.query(InventoryItem).filter(InventoryItem.name == name_query).first()
        if not item:
            item = db.query(InventoryItem).filter(InventoryItem.name.ilike(name_query)).first()
        
        if item:
            item.quantity -= amount
            return f"\n📦 Stock Updated: -{amount} {item.unit}"
        return ""

    inv_msg = ""
    if mode == 'mode_egg':
        inv_msg = deduct_stock("Eggs", qty)
    elif mode == 'mode_crate':
        # Assuming 1 Crate = 30 Eggs. Check if "Eggs" exists, else try "Egg Crates"
        # Prioritize converting to Eggs if 'Eggs' inventory exists
        egg_item = db.query(InventoryItem).filter(InventoryItem.name == "Eggs").first()
        if egg_item:
            deduction = qty * 30
            egg_item.quantity -= deduction
            inv_msg = f"\n📦 Stock Updated: -{deduction} Eggs (30/crate)"
        else:
            inv_msg = deduct_stock("Egg Crates", qty)
    elif mode == 'mode_bird':
        # Harder to guess. Try "Broilers" or "Birds" or "Chickens"
        # Use a generic approach: Decrement matching name if exists, else skip
        # Users often name it "Broilers" or "Culls"
        # We will try to find a best guess or just leave it to DailyEntry flock total
        # (DailyEntry flock total is already updated above)
        pass 
        
    db.commit()
    db.close()
    
    await state.clear()
    
    ref_text = f"(Ref: {ref})" if ref else ""
    await message.answer(
        text=f"✅ **Sale Complete!**\n\n"
             f"👤 {cust_name}\n"
             f"📦 {qty} {item_name}\n"
             f"💰 {format_currency(total)} via {method} {ref_text}"
             f"{inv_msg}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

