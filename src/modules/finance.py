from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, FinancialLedger, Contact, InventoryLog, SystemSettings, InventoryItem, DailyEntry
from datetime import date
from sqlalchemy import desc
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency

router = Router()

class ExpenseStates(StatesGroup):
    category = State()
    supplier_id = State()
    item_details = State() # specific brand/type
    amount = State()
    payment_method = State()
    transaction_ref = State()
    # Inventory Link States
    link_inventory = State()
    select_inv_item = State()
    new_inv_name = State()
    new_inv_unit = State()
    new_inv_unit = State()
    inv_quantity = State()
    
    # Sales States
    sale_customer = State()
    sale_mode = State()
    sale_quantity = State()
    sale_price = State()

EXPENSE_CATEGORIES = {
    'cat_feed': '🍽️ Feed',
    'cat_meds': '💊 Medication',
    'cat_labor': '👨‍🌾 Labor',
    'cat_other': '🛠️ Other'
}

@router.callback_query(F.data == "menu_finance")
async def start_finance(callback: types.CallbackQuery, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="📉 Record Expense", callback_data="fin_expense_start")],
        [InlineKeyboardButton(text="📈 Record Income (Sales)", callback_data="fin_income_start")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
    ]

    await callback.message.edit_text(
        text="💰 **Finance Management**\n\nChoose functionality:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "fin_expense_start")
async def start_expense(callback: types.CallbackQuery, state: FSMContext):
    keyboard = []
    row = []
    for key, label in EXPENSE_CATEGORIES.items():
        row.append(InlineKeyboardButton(text=label, callback_data=key))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_finance")])

    await callback.message.edit_text(
        text="📉 **Record Expense**\n\nSelect Category:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "fin_income_start")
async def start_income(callback: types.CallbackQuery, state: FSMContext):
    # Select Customer
    db = next(get_db())
    customers = db.query(Contact).filter_by(role="CUSTOMER").all()
    db.close()
    
    keyboard = []
    for c in customers:
        keyboard.append([InlineKeyboardButton(text=f"👤 {c.name}", callback_data=f"cust_{c.id}")])
    
    keyboard.append([InlineKeyboardButton(text="🚶 Walk-in / Generic", callback_data="cust_generic")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_finance")])
    
    await callback.message.edit_text(
        text="📈 **Record Income**\n\nSelect Customer:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.sale_customer)
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"))
async def expense_category(callback: types.CallbackQuery, state: FSMContext):
    category_key = callback.data
    category_name = EXPENSE_CATEGORIES.get(category_key, "Unknown")
    await state.update_data(cat_key=category_key, cat_name=category_name)
    
    # Step 2: Select Supplier
    db = next(get_db())
    suppliers = db.query(Contact).filter_by(role="SUPPLIER").all()
    db.close()
    
    keyboard = []
    for s in suppliers:
        keyboard.append([InlineKeyboardButton(text=f"🏢 {s.name}", callback_data=f"supp_{s.id}")])
    
    keyboard.append([InlineKeyboardButton(text="🚶 Generic / Unknown", callback_data="supp_generic")])
    keyboard.append([InlineKeyboardButton(text="➕ Add New Supplier", callback_data="menu_add_contact_redirect")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_finance")])
    
    await callback.message.edit_text(
        text=f"🏢 **Select Supplier**\n\nWho are you paying for {category_name}?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.supplier_id)
    await callback.answer()

@router.callback_query(ExpenseStates.supplier_id, F.data.startswith("supp_"))
async def select_supplier(callback: types.CallbackQuery, state: FSMContext):
    supp_id = callback.data.split("_")[1]
    if supp_id == "generic":
        supp_id = None
        supp_name = "Generic Supplier"
    else:
        db = next(get_db())
        supp = db.query(Contact).filter_by(id=supp_id).first()
        supp_name = supp.name if supp else "Unknown"
        db.close()
        
    await state.update_data(supplier_id=supp_id, supplier_name=supp_name)
    
    # Check Category for Inventory Link
    data = await state.get_data()
    cat_key = data.get('cat_key')
    
    # Categories that might be inventory: Feed, Meds, Other
    if cat_key in ['cat_feed', 'cat_meds', 'cat_other']:
        keyboard = [
            [InlineKeyboardButton(text="✅ Yes, Add to Stock", callback_data="inv_yes")],
            [InlineKeyboardButton(text="❌ No, Expense Only", callback_data="inv_no")]
        ]
        await callback.message.edit_text(
            text="📦 **Inventory Check**\n\nIs this a physical item you want to add to stock?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.link_inventory)
    else:
        # Labor, etc -> Skip
        await ask_item_details(callback.message, state) # Helper or direct

@router.callback_query(ExpenseStates.link_inventory, F.data.startswith("inv_"))
async def receive_inv_link(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    await state.update_data(link_inventory=(choice == "yes"))
    
    if choice == "yes":
         # Select Item from Inventory
        # Select Item from Inventory
        db = next(get_db())
        items = db.query(InventoryItem).all()
        db.close()
        
        keyboard = []
        for item in items:
            keyboard.append([InlineKeyboardButton(text=f"{item.name}", callback_data=f"invitem_{item.id}")])
        keyboard.append([InlineKeyboardButton(text="➕ New Item", callback_data="invitem_new")])
        
        await callback.message.edit_text(
            text="📦 **Select Item** to add stock to:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.select_inv_item)
    else:
        # Just ask details manually
        await callback.message.edit_text(
            text="📝 **Expense Details**\n\nWhat are you paying for?",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("menu_finance")
        )
        await state.set_state(ExpenseStates.item_details)
    await callback.answer()

@router.callback_query(ExpenseStates.select_inv_item, F.data.startswith("invitem_"))
async def receive_inv_item(callback: types.CallbackQuery, state: FSMContext):
    item_id = callback.data.split("_")[1]
    
    if item_id == "new":
        await callback.message.edit_text("📝 **New Item Name**\n\nWhat is it called?", parse_mode="Markdown")
        await state.set_state(ExpenseStates.new_inv_name)
    else:
        await state.update_data(inv_item_id=int(item_id))
        # Get item name for details
        db = next(get_db())
        from database import InventoryItem
        item = db.query(InventoryItem).filter_by(id=int(item_id)).first()
        name = item.name if item else "Unknown"
        unit = item.unit if item else "units"
        inv_type = item.type if item else "SUPPLY"
        db.close()
        
        await state.update_data(item_details=name, inv_item_unit=unit, inv_item_type=inv_type) 
        
        # If FEED and unit is KG, ask if buying in Bags
        keyboard = []
        if inv_type == "FEED" and unit == "kg":
             keyboard = [
                [InlineKeyboardButton(text="🎒 Bags (70kg)", callback_data="uom_bags")],
                [InlineKeyboardButton(text="⚖️ KGs", callback_data="uom_kgs")]
             ]
             await callback.message.edit_text(
                text=f"🔢 **Unit of Measure**\n\nAre you buying in Bags or KGs?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
             await state.set_state(ExpenseStates.new_inv_unit) # Use this state temp or new one? Reuse or skip to quantity logic
        else:
             await callback.message.edit_text(
                text=f"🔢 **Quantity**\n\nHow many **{unit}** are you buying?",
                parse_mode="Markdown"
            )
             await state.set_state(ExpenseStates.inv_quantity)
    await callback.answer()

@router.callback_query(ExpenseStates.new_inv_unit, F.data.startswith("uom_"))
async def receive_feed_uom(callback: types.CallbackQuery, state: FSMContext):
    uom = callback.data.split("_")[1]
    await state.update_data(feed_input_uom=uom)
    
    unit_label = "Bags" if uom == "bags" else "KGs"
    await callback.message.edit_text(f"🔢 **Quantity**\n\nHow many **{unit_label}**?")
    await state.set_state(ExpenseStates.inv_quantity)
    await callback.answer()

@router.message(ExpenseStates.new_inv_name)
async def receive_new_inv_name(message: types.Message, state: FSMContext):
    await state.update_data(item_details=message.text, is_new_item=True)
    await message.answer("📏 **Unit** (e.g. kg, bags, pcs):")
    await state.set_state(ExpenseStates.new_inv_unit)

@router.message(ExpenseStates.new_inv_unit)
async def receive_new_inv_unit(message: types.Message, state: FSMContext):
    await state.update_data(inv_item_unit=message.text)
    await message.answer("🔢 **Quantity**\n\nHow much?")
    await state.set_state(ExpenseStates.inv_quantity)

@router.message(ExpenseStates.inv_quantity)
async def receive_inv_quantity(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
    except:
        await message.answer("⚠️ Invalid number.")
        return
    
    await state.update_data(inv_quantity=qty)
    
    # Now ask Cost
    await message.answer(
        text="💰 **Total Cost**\n\nTotal amount to pay:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_finance")
    )
    await state.set_state(ExpenseStates.amount)


async def ask_item_details(message: types.Message, state: FSMContext):
    await message.edit_text(
        text="📝 **Expense Details**\n\nWhat are you paying for?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_finance")
    ) if isinstance(message, types.Message) else await message.answer("📝 **Expense Details**\n\nWhat are you paying for?")
    await state.set_state(ExpenseStates.item_details)

@router.message(ExpenseStates.item_details)
async def receive_details(message: types.Message, state: FSMContext):
    await state.update_data(item_details=message.text)
    
    await message.answer(
        text="💰 **Cost**\n\nTotal amount to pay:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_finance")
    )
    await state.set_state(ExpenseStates.amount)

@router.message(ExpenseStates.amount)
async def receive_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid positive number.")
        return
        
    await state.update_data(amount=amount)
    
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
    await state.set_state(ExpenseStates.payment_method)

@router.callback_query(ExpenseStates.payment_method, F.data.startswith("pay_"))
async def receive_payment_method(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    await state.update_data(payment_method=method)
    
    if method == "MPESA":
        await callback.message.edit_text(
            text="📲 **M-Pesa Reference**\n\nEnter the MPESA Transaction Code:",
            parse_mode="Markdown"
        )
        await state.set_state(ExpenseStates.transaction_ref)
    else:
        data = await state.get_data()
        if data.get('sale_mode'):
            await finalize_sale(callback.message, state)
        else:
            await finalize_expense(callback.message, state)
    
    await callback.answer()

@router.message(ExpenseStates.transaction_ref)
async def receive_ref(message: types.Message, state: FSMContext):
    ref = message.text.upper()
    await state.update_data(transaction_ref=ref)
    
    data = await state.get_data()
    if data.get('sale_mode'):
         await finalize_sale(message, state)
    else:
         await finalize_expense(message, state)

async def finalize_expense(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    from database import InventoryItem # Ensure import
    
    cat_name = data.get('cat_name')
    supp_id = data.get('supplier_id')
    supp_name = data.get('supplier_name')
    item_desc = data.get('item_details')
    amount = data.get('amount')
    method = data.get('payment_method')
    ref = data.get('transaction_ref', None) # None if Cash
    
    link_inv = data.get('link_inventory', False)
    
    # 1. Create Ledger Entry
    ledger = FinancialLedger(
        amount=amount,
        direction="OUT",
        payment_method=method,
        transaction_ref=ref,
        category=cat_name,
        description=f"Bought {item_desc}" + (f" ({data.get('inv_quantity')} {data.get('inv_item_unit')})" if link_inv else ""),
        contact_id=supp_id
    )
    db.add(ledger)
    db.flush()
    
    # 2. Inventory Link
    inv_msg = ""
    if link_inv:
        qty = data.get('inv_quantity')
        unit = data.get('inv_item_unit', 'units')
        item_id = data.get('inv_item_id')
        is_new = data.get('is_new_item', False)
        
        # Calculate Unit Cost for cache
        unit_cost = amount / qty if qty > 0 else 0
        
        item = None
        if is_new:
            item = InventoryItem(
                name=item_desc,
                type="SUPPLY", # Default type or ask? Assuming SUPPLY/FEED based on Cat?
                # Simplify: just use SUPPLY or Generic. Or check Cat Key?
                # If cat_feed -> FEED. If cat_meds -> MEDICATION.
                quantity=0,
                unit=unit,
                cost_per_unit=unit_cost
            )
            cat_key = data.get('cat_key')
            if cat_key == 'cat_feed': item.type = "FEED"
            elif cat_key == 'cat_meds': item.type = "MEDICATION"
            else: item.type = "EQUIPMENT"
            
            db.add(item)
            db.flush()
        else:
            item = db.query(InventoryItem).filter_by(id=item_id).first()
            if item:
                # Update Cost averaging? Or just overwrite?
                # User preference: "Ask if I need to change... use default".
                # For this flow, we just update Last Known Cost.
                item.cost_per_unit = unit_cost
        
        if item:
            final_qty = qty
            
            # Feed Conversion: If bought in Bags but stored in KG
            if data.get('feed_input_uom') == 'bags' and item.unit == 'kg':
                 # Get Dynamic Weight
                 setting = db.query(SystemSettings).filter_by(key="feed_bag_weight").first()
                 bag_weight = float(setting.value) if setting else 70.0
                 
                 final_qty = qty * bag_weight 
                 # Recalculate cost per unit (per KG)
                 # Total Amount / Total KG
                 unit_cost = amount / final_qty
                 item.cost_per_unit = unit_cost
                 
            item.quantity += final_qty
            
            # Log
            log = InventoryLog(
                item_name=item.name,
                quantity_change=final_qty,
                ledger_id=ledger.id
            )
            db.add(log)
            inv_msg = f"\n📦 Stock Updated: +{final_qty} {item.unit}"
            if data.get('feed_input_uom') == 'bags':
                inv_msg += f" ({qty} bags)"

    db.commit()
    db.close()
    
    await state.clear()
    
    ref_text = f"(Ref: {ref})" if ref else ""
    await message.answer(
        text=f"✅ **Expense Recorded!**\n\n"
             f"🛒 Bought: {item_desc}\n"
             f"🏢 From: {supp_name}\n"
             f"💰 {format_currency(amount)} via {method} {ref_text}"
             f"{inv_msg}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )



# --- SALES / INCOME HANDLERS ---

@router.callback_query(ExpenseStates.sale_customer, F.data.startswith("cust_"))
async def select_sale_customer(callback: types.CallbackQuery, state: FSMContext):
    cust_id = callback.data.split("_")[1]
    if cust_id == "generic":
        cust_id = None
        cust_name = "Walk-in Info"
    else:
        db = next(get_db())
        cust = db.query(Contact).filter_by(id=cust_id).first()
        cust_name = cust.name if cust else "Unknown"
        db.close()

    await state.update_data(customer_id=cust_id, customer_name=cust_name)
    
    keyboard = [
        [InlineKeyboardButton(text="🥚 Per Egg", callback_data='mode_egg'),
         InlineKeyboardButton(text="📦 Per Crate", callback_data='mode_crate')],
        [InlineKeyboardButton(text="🐥 Birds (Culls/Stock)", callback_data='mode_bird')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='fin_income_start')]
    ]
    
    await callback.message.edit_text(
        text=f"🛒 **Selling to: {cust_name}**\n\nWhat are they buying?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.sale_mode)
    await callback.answer()

@router.callback_query(ExpenseStates.sale_mode, F.data.startswith("mode_"))
async def receive_sale_mode(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data
    await state.update_data(sale_mode=mode)
    
    unit = "eggs"
    if mode == 'mode_crate': unit = "crates"
    elif mode == 'mode_bird': unit = "birds"
    
    await callback.message.edit_text(
        text=f"🔢 **Quantity**\n\nHow many {unit}?",
        parse_mode="Markdown"
    )
    await state.set_state(ExpenseStates.sale_quantity)
    await callback.answer()

@router.message(ExpenseStates.sale_quantity)
async def receive_sale_qty(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    qty = int(message.text)
    
    data = await state.get_data()
    mode = data.get('sale_mode')
    
    # Check Stock
    # Check Stock
    db = next(get_db())
    today = date.today()
    
    if mode in ['mode_egg', 'mode_crate']:
        # Check Eggs
        egg_item = db.query(InventoryItem).filter_by(name="Eggs").first()
        current_stock = egg_item.quantity if egg_item else 0
        
        if current_stock < qty:
             await message.answer(
                 f"⛔ **Not enough eggs!**\n\nStock: {current_stock} eggs\nTrying to sell: {qty} eggs\n\nTry a lower amount:",
                 reply_markup=get_back_home_keyboard('menu_finance')
             )
             db.close()
             return

    elif mode == 'mode_crate':
        eggs_needed = qty * 30
        entry = db.query(DailyEntry).filter_by(date=today).first()
        current_stock = entry.eggs_good if entry else 0
        
        if current_stock < eggs_needed:
             await message.answer(
                 f"⛔ **Not enough eggs for crates!**\n\nStock: {current_stock} eggs\nNeeded: {eggs_needed} eggs\n\nTry fewer crates:",
                 reply_markup=get_back_home_keyboard('menu_finance')
             )
             db.close()
             return

    elif mode == 'mode_bird':
        entry = db.query(DailyEntry).filter_by(date=today).first()
        last = db.query(DailyEntry).filter(DailyEntry.date < today).order_by(desc(DailyEntry.date)).first()
        current_flock = entry.flock_total if entry else (last.flock_total if last else 0)
        
        if current_flock < qty:
            await message.answer(
                f"⛔ **Not enough birds!**\n\nFlock Count: {current_flock}\nTrying to sell: {qty}\n\nTry a lower amount:",
                reply_markup=get_back_home_keyboard('menu_finance')
            )
            db.close()
            return
            
    db.close()
    await state.update_data(sale_qty=qty)
    
    # Calculate or Ask Price
    price = 0.0
    
    if mode == 'mode_bird':
        await message.answer("💸 **Total Price** for these birds:")
        await state.set_state(ExpenseStates.sale_price)
    else:
        db = next(get_db())
        # defaults
        p_egg = 15.0
        p_crate = 450.0
        
        s_egg = db.query(SystemSettings).filter_by(key="price_per_egg").first()
        s_crate = db.query(SystemSettings).filter_by(key="price_per_crate").first()
        if s_egg: p_egg = float(s_egg.value)
        if s_crate: p_crate = float(s_crate.value)
        db.close()
        
        if mode == 'mode_egg': price = qty * p_egg
        else: price = qty * p_crate
        
        await state.update_data(amount=price)
        await ask_payment_input(message, state, price)

@router.message(ExpenseStates.sale_price)
async def receive_sale_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(amount=price)
        await ask_payment_input(message, state, price)
    except:
        await message.answer("Invalid price.")

async def ask_payment_input(message, state, amount):
    keyboard = [
        [InlineKeyboardButton(text="💵 Cash", callback_data='pay_CASH')],
        [InlineKeyboardButton(text="📱 M-Pesa", callback_data='pay_MPESA')],
        [InlineKeyboardButton(text="💳 Credit / Later", callback_data='pay_CREDIT')]
    ]
    await message.answer(
        text=f"�� **Payment**\n\nTotal: {format_currency(amount)}\nMethod?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.payment_method)

async def finalize_sale(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db = next(get_db())
    
    mode = data.get('sale_mode')
    qty = data.get('sale_qty')
    total = data.get('amount')
    method = data.get('payment_method')
    ref = data.get('transaction_ref', None)
    cust_id = data.get('customer_id')
    
    item_name = "Eggs"
    if mode == 'mode_crate': item_name = "Egg Crates"
    elif mode == 'mode_bird': item_name = "Birds/Meat"
    
    # 1. Financial Ledger - IN
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
    db.flush()
    
    # 2. Daily Entry
    today = date.today()
    entry = db.query(DailyEntry).filter(DailyEntry.date == today).first()
    if not entry:
        entry = DailyEntry(date=today)
        db.add(entry)
    
    entry.income += total
    if mode == 'mode_egg': entry.eggs_sold += qty
    elif mode == 'mode_crate': entry.crates_sold += qty
    elif mode == 'mode_bird':
        if entry.flock_removed is None: entry.flock_removed = 0
        entry.flock_removed += qty
        
    # 3. Inventory Deduction
    # Sales decrement inventory as INCOME -> Item leaves farm
    inv_msg = ""
    # Simple logic
    inv_log = InventoryLog(item_name=item_name, quantity_change=-qty, ledger_id=ledger.id)
    db.add(inv_log)
    
    db.commit()
    cust_name = data.get('customer_name')
    db.close()
    
    await state.clear()
    await message.answer(
        text=f"✅ **Sale Recorded!**\n\n👤 {cust_name}\n📦 {qty} {item_name}\n💰 {format_currency(total)}",
        reply_markup=get_main_menu_keyboard()
    )
