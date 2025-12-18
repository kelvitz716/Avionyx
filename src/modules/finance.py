from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, FinancialLedger, Contact, InventoryLog
from datetime import date
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
    inv_quantity = State()

EXPENSE_CATEGORIES = {
    'cat_feed': '🍽️ Feed',
    'cat_meds': '💊 Medication',
    'cat_labor': '👨‍🌾 Labor',
    'cat_other': '🛠️ Other'
}

@router.callback_query(F.data == "menu_finance")
async def start_finance(callback: types.CallbackQuery, state: FSMContext):
    keyboard = []
    row = []
    for key, label in EXPENSE_CATEGORIES.items():
        row.append(InlineKeyboardButton(text=label, callback_data=key))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Removed P&L from here (moved to Reports)
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")])

    await callback.message.edit_text(
        text="💰 **Finance Management**\n\nSelect an Expense Category:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
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
        db = next(get_db())
        items = db.query(FinancialLedger).session.query(InventoryItem).all() # Hacky access or just import InventoryItem?
        # Need to import InventoryItem in finance.py
        # Assuming import exists or will be added
        # items = db.query(InventoryItem).all()
        # To avoid import errors let's use the object from database.py if imported
        from database import InventoryItem
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
        db.close()
        
        await state.update_data(item_details=name, inv_item_unit=unit) # Auto-fill expense details with item name
        
        await callback.message.edit_text(
            text=f"🔢 **Quantity**\n\nHow many **{unit}** are you buying?",
            parse_mode="Markdown"
        )
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
        await finalize_expense(callback.message, state) # No code needed for Cash/Credit
    
    await callback.answer()

@router.message(ExpenseStates.transaction_ref)
async def receive_ref(message: types.Message, state: FSMContext):
    ref = message.text.upper()
    await state.update_data(transaction_ref=ref)
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
            item.quantity += qty
            
            # Log
            log = InventoryLog(
                item_name=item.name,
                quantity_change=qty,
                ledger_id=ledger.id
            )
            db.add(log)
            inv_msg = f"\n📦 Stock Updated: +{qty} {unit}"

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


