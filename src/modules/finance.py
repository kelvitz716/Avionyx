from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, FinancialLedger, Contact, InventoryLog, SystemSettings, InventoryItem, DailyEntry, VaccinationRecord, Flock
from datetime import date, timedelta
from sqlalchemy import desc
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency
import json

router = Router()

class ExpenseStates(StatesGroup):
    category = State()
    supplier_id = State()
    item_details = State()  # specific brand/type
    amount = State()
    payment_method = State()
    transaction_ref = State()
    # Inventory Link States
    link_inventory = State()
    select_inv_item = State()
    new_inv_name = State()
    new_inv_unit = State()
    inv_quantity = State()
    
    # Multi-Feed Purchase States
    feed_mode = State()        # single/multiple
    feed_select = State()      # select existing feed or new
    feed_bag_count = State()   # number of bags
    feed_bag_weight = State()  # kg per bag
    feed_price_per_bag = State()
    feed_add_another = State() # prompt to add more feed types
    feed_expiry = State()      # for medications
    
    # Vaccination States
    vacc_flock = State()
    vacc_vaccine = State()
    vacc_count = State()
    vacc_next_due = State()
    vacc_notes = State()
    
    # Sales States
    sale_customer = State()
    new_cust_name = State() # NEW
    sale_mode = State()
    sale_flock = State()  # NEW: Select flock for bird sales
    sale_quantity = State()
    sale_price = State()
    
    # New Flock States
    new_flock_confirm = State()
    new_flock_name = State()
    new_flock_breakdown = State() # Ask for Hens/Roosters
    new_flock_age = State()
    
    # Existing Flock Add
    existing_flock_select = State()
    existing_flock_breakdown = State()

EXPENSE_CATEGORIES = {
    'cat_feed': '🍽️ Feed',
    'cat_meds': '💊 Medication',
    'cat_birds': '🐥 Birds',
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
    keyboard.append([InlineKeyboardButton(text="➕ Add New Customer", callback_data="cust_new")])
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
    
    # Check Category for special handling
    data = await state.get_data()
    cat_key = data.get('cat_key')
    
    # Feed gets special multi-feed flow
    if cat_key == 'cat_feed':
        keyboard = [
            [InlineKeyboardButton(text="📦 Single Feed Type", callback_data="feedmode_single")],
            [InlineKeyboardButton(text="📦📦 Multiple Feed Types", callback_data="feedmode_multi")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        await callback.message.edit_text(
            text="🍽️ **Feed Purchase**\n\nAre you buying one type of feed or multiple types?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.update_data(feed_items=[], link_inventory=True)
        await state.set_state(ExpenseStates.feed_mode)
    
    # Medication gets expiry date tracking
    elif cat_key == 'cat_meds':
        keyboard = [
            [InlineKeyboardButton(text="✅ Yes, Add to Stock", callback_data="inv_yes")],
            [InlineKeyboardButton(text="❌ No, Expense Only", callback_data="inv_no")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        await callback.message.edit_text(
            text="📦 **Inventory Check**\n\nAdd this medication to inventory with expiry tracking?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.link_inventory)
    
    # Birds / Livestock
    elif cat_key == 'cat_birds':
        keyboard = [
            [InlineKeyboardButton(text="✅ Yes, Add to Stock", callback_data="inv_yes")],
            [InlineKeyboardButton(text="❌ No, Expense Only", callback_data="inv_no")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        await callback.message.edit_text(
            text="🐣 **Bird Purchase**\n\nAre you adding these birds to your inventory count?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.link_inventory)
    
    # Other categories
    elif cat_key in ['cat_other']:
        keyboard = [
            [InlineKeyboardButton(text="✅ Yes, Add to Stock", callback_data="inv_yes")],
            [InlineKeyboardButton(text="❌ No, Expense Only", callback_data="inv_no")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        await callback.message.edit_text(
            text="📦 **Inventory Check**\n\nIs this a physical item you want to add to stock?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.link_inventory)
    else:
        # Labor, etc -> Skip inventory
        await ask_item_details(callback.message, state)
    
    await callback.answer()

@router.callback_query(ExpenseStates.link_inventory, F.data.startswith("inv_"))
async def receive_inv_link(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    await state.update_data(link_inventory=(choice == "yes"))
    data = await state.get_data()
    cat_key = data.get('cat_key')
    
    if choice == "yes":
        db = next(get_db())
        if cat_key == 'cat_meds':
            items = db.query(InventoryItem).filter_by(type="MEDICATION").all()
        elif cat_key == 'cat_birds':
            items = db.query(InventoryItem).filter_by(type="LIVESTOCK").all()
        else:
            items = db.query(InventoryItem).all()
        db.close()
        
        # Auto-Select Logic for Birds
        if cat_key == 'cat_birds':
            # Group by Name
            unique_names = list(set([i.name for i in items]))
            should_auto = False
            target_item = None
            
            if len(unique_names) <= 1:
                # If 0, create default "Chickens"
                if len(unique_names) == 0:
                    target_item = InventoryItem(name="Chickens", type="LIVESTOCK", unit="birds", quantity=0)
                    db.add(target_item)
                    db.flush() # Get ID
                else:
                    target_item = items[0] # Pick the first one (others are duplicates by name if any)
                should_auto = True
            
            if should_auto:
                await state.update_data(
                    inv_item_id=target_item.id,
                    item_details=target_item.name,
                    inv_item_unit=target_item.unit,
                    inv_item_type="LIVESTOCK"
                )
                db.close()
                await callback.message.edit_text(
                    text=f"🔢 **Quantity**\n\nHow many **{target_item.unit}** are you buying?",
                    parse_mode="Markdown",
                    reply_markup=get_back_home_keyboard("fin_expense_start")
                )
                await state.set_state(ExpenseStates.inv_quantity)
                return

        # Group by Name for Menu
        grouped = {}
        for item in items:
            name = item.name.strip()
            if name not in grouped:
                grouped[name] = {'item': item, 'total_qty': 0.0}
            grouped[name]['total_qty'] += item.quantity
        
        keyboard = []
        for name, data in grouped.items():
            item = data['item']
            qty = data['total_qty']
            display = f"{name} ({qty} {item.unit})"
            keyboard.append([InlineKeyboardButton(text=display, callback_data=f"invitem_{item.id}")])
            
        keyboard.append([InlineKeyboardButton(text="➕ New Item", callback_data="invitem_new")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")])
        keyboard.append([InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")])
        
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


# ========================================
# MULTI-FEED PURCHASE FLOW
# ========================================

@router.callback_query(ExpenseStates.feed_mode, F.data.startswith("feedmode_"))
async def receive_feed_mode(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]
    await state.update_data(
        feed_purchase_mode=mode,
        feed_items=[],  # List to collect multiple feed items
        total_expense=0.0
    )
    
    # Show feed selection
    await show_feed_selection(callback.message, state)
    await callback.answer()


async def show_feed_selection(message: types.Message, state: FSMContext):
    """Show list of existing feeds or option to add new."""
    db = next(get_db())
    feeds = db.query(InventoryItem).filter_by(type="FEED").all()
    db.close()
    
    # Group by Name
    grouped = {}
    for feed in feeds:
        name = feed.name.strip()
        if name not in grouped:
            grouped[name] = {'item': feed, 'total_qty': 0.0}
        grouped[name]['total_qty'] += feed.quantity
    
    keyboard = []
    for name, data in grouped.items():
        feed = data['item']
        qty = data['total_qty'] # Usually Kg
        display = f"{name}"
        if feed.bag_weight:
             display += f" (Stock: ~{qty/feed.bag_weight:.1f} bags)"
        else:
             display += f" (Stock: {qty} {feed.unit})"
             
        keyboard.append([InlineKeyboardButton(text=display, callback_data=f"feedsel_{feed.id}")])
    
    keyboard.append([InlineKeyboardButton(text="➕ New Feed Type", callback_data="feedsel_new")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")])
    keyboard.append([InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")])
    
    await message.edit_text(
        text="🍽️ **Select Feed**\n\nWhich feed are you buying?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.feed_select)


@router.callback_query(ExpenseStates.feed_select, F.data.startswith("feedsel_"))
async def receive_feed_selection(callback: types.CallbackQuery, state: FSMContext):
    selection = callback.data.split("_")[1]
    
    if selection == "new":
        await callback.message.edit_text(
            text="📝 **New Feed Name**\n\nEnter the name (e.g., 'Growers Mash', 'Layers Mash'):",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("fin_expense_start")
        )
        await state.update_data(is_new_feed=True)
        await state.set_state(ExpenseStates.new_inv_name)
    else:
        # Existing feed selected
        db = next(get_db())
        feed = db.query(InventoryItem).filter_by(id=int(selection)).first()
        
        if feed:
            await state.update_data(
                current_feed_id=feed.id,
                current_feed_name=feed.name,
                current_feed_unit=feed.unit,
                current_bag_weight=feed.bag_weight or 70.0,
                is_new_feed=False
            )
        db.close()
        
        # Ask for number of bags
        await callback.message.edit_text(
            text=f"🎒 **Number of Bags**\n\nHow many bags of **{feed.name}**?",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("fin_expense_start")
        )
        await state.set_state(ExpenseStates.feed_bag_count)
    
    await callback.answer()


@router.message(ExpenseStates.new_inv_name, F.text)
async def receive_new_feed_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Check if we're in multi-feed flow
    if data.get('feed_purchase_mode'):
        await state.update_data(
            current_feed_name=message.text,
            is_new_feed=True
        )
        await message.answer(
            text="⚖️ **Bag Weight**\n\nHow many kg per bag?",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("fin_expense_start")
        )
        await state.set_state(ExpenseStates.feed_bag_weight)
    else:
        # Non-feed items - show pre-populated UoM dropdown
        await state.update_data(item_details=message.text, is_new_item=True)
        keyboard = [
            [InlineKeyboardButton(text="📦 pcs (pieces)", callback_data="newuom_pcs")],
            [InlineKeyboardButton(text="⚖️ kgs (kilograms)", callback_data="newuom_kgs")],
            [InlineKeyboardButton(text="🎒 bags", callback_data="newuom_bags")],
            [InlineKeyboardButton(text="🧴 ltrs (litres)", callback_data="newuom_ltrs")],
            [InlineKeyboardButton(text="💊 doses", callback_data="newuom_doses")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        await message.answer(
            text="📏 **Unit of Measure**\n\nSelect the unit for this item:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.new_inv_unit)


@router.callback_query(ExpenseStates.new_inv_unit, F.data.startswith("newuom_"))
async def receive_new_uom_selection(callback: types.CallbackQuery, state: FSMContext):
    unit = callback.data.split("_")[1]
    await state.update_data(inv_item_unit=unit)
    
    await callback.message.edit_text(
        text="🔢 **Quantity**\n\nHow many are you buying?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("fin_expense_start")
    )
    await state.set_state(ExpenseStates.inv_quantity)
    await callback.answer()


@router.message(ExpenseStates.feed_bag_weight, F.text)
async def receive_feed_bag_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid positive number.")
        return
    
    await state.update_data(current_bag_weight=weight)
    
    await message.answer(
        text=f"🎒 **Number of Bags**\n\nHow many bags (at {weight}kg each)?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("fin_expense_start")
    )
    await state.set_state(ExpenseStates.feed_bag_count)


@router.message(ExpenseStates.feed_bag_count, F.text)
async def receive_feed_bag_count(message: types.Message, state: FSMContext):
    try:
        bags = int(message.text)
        if bags <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid number of bags.")
        return
    
    await state.update_data(current_bag_count=bags)
    
    data = await state.get_data()
    bag_weight = data.get('current_bag_weight', 70.0)
    total_kg = bags * bag_weight
    
    await message.answer(
        text=f"💰 **Price per Bag**\n\n{bags} bags × {bag_weight}kg = **{total_kg}kg**\n\nPrice per bag (KSh)?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("fin_expense_start")
    )
    await state.set_state(ExpenseStates.feed_price_per_bag)


@router.message(ExpenseStates.feed_price_per_bag, F.text)
async def receive_feed_price_per_bag(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid price.")
        return
    
    data = await state.get_data()
    bags = data.get('current_bag_count', 1)
    bag_weight = data.get('current_bag_weight', 70.0)
    feed_name = data.get('current_feed_name', 'Unknown Feed')
    feed_id = data.get('current_feed_id')
    is_new = data.get('is_new_feed', False)
    
    total_kg = bags * bag_weight
    total_cost = bags * price
    cost_per_kg = price / bag_weight
    
    # Add to feed items list
    feed_items = data.get('feed_items', [])
    feed_items.append({
        'id': feed_id,
        'name': feed_name,
        'bags': bags,
        'bag_weight': bag_weight,
        'total_kg': total_kg,
        'price_per_bag': price,
        'total_cost': total_cost,
        'cost_per_kg': cost_per_kg,
        'is_new': is_new
    })
    
    current_total = data.get('total_expense', 0.0) + total_cost
    await state.update_data(
        feed_items=feed_items,
        total_expense=current_total,
        current_feed_id=None,
        current_feed_name=None,
        is_new_feed=False
    )
    
    # Check if multi mode
    mode = data.get('feed_purchase_mode')
    
    if mode == 'multi':
        # Ask if they want to add another
        keyboard = [
            [InlineKeyboardButton(text="➕ Add Another Feed Type", callback_data="feedadd_yes")],
            [InlineKeyboardButton(text="✅ Done - Finalize Purchase", callback_data="feedadd_done")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]
        
        # Show summary so far
        summary_lines = ["📋 **Feed Purchase Summary**\n"]
        for item in feed_items:
            summary_lines.append(f"• {item['name']}: {item['bags']} bags ({item['total_kg']}kg) @ {format_currency(item['price_per_bag'])}/bag = {format_currency(item['total_cost'])}")
        summary_lines.append(f"\n**Running Total: {format_currency(current_total)}**")
        
        await message.answer(
            text="\n".join(summary_lines) + "\n\nAdd more feed types?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.feed_add_another)
    else:
        # Single feed - go to payment
        await ask_feed_payment(message, state)


@router.callback_query(ExpenseStates.feed_add_another, F.data.startswith("feedadd_"))
async def receive_feed_add_another(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    
    if choice == "yes":
        # Show feed selection again
        await show_feed_selection(callback.message, state)
    else:
        # Done - go to payment
        await ask_feed_payment(callback.message, state)
    
    await callback.answer()


async def ask_feed_payment(message: types.Message, state: FSMContext):
    """Ask for payment method for feed purchase."""
    data = await state.get_data()
    total = data.get('total_expense', 0.0)
    
    keyboard = [
        [InlineKeyboardButton(text="💵 Cash", callback_data='feedpay_CASH')],
        [InlineKeyboardButton(text="📱 M-Pesa", callback_data='feedpay_MPESA')],
        [InlineKeyboardButton(text="💳 Credit / Later", callback_data='feedpay_CREDIT')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="fin_expense_start")],
        [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
    ]
    
    await message.answer(
        text=f"💳 **Payment Method**\n\nTotal: **{format_currency(total)}**\n\nHow are you paying?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.payment_method)


@router.callback_query(ExpenseStates.payment_method, F.data.startswith("feedpay_"))
async def receive_feed_payment(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    await state.update_data(payment_method=method)
    
    if method == "MPESA":
        await callback.message.edit_text(
            text="📲 **M-Pesa Reference**\n\nEnter the transaction code:",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("fin_expense_start")
        )
        await state.set_state(ExpenseStates.transaction_ref)
    else:
        await finalize_feed_purchase(callback.message, state)
    
    await callback.answer()


async def finalize_feed_purchase(message: types.Message, state: FSMContext):
    """Save feed purchase to database with inventory updates."""
    data = await state.get_data()
    db = next(get_db())
    
    feed_items = data.get('feed_items', [])
    total = data.get('total_expense', 0.0)
    method = data.get('payment_method', 'CASH')
    ref = data.get('transaction_ref')
    supp_id = data.get('supplier_id')
    supp_name = data.get('supplier_name', 'Unknown')
    
    # Build description
    desc_parts = []
    for item in feed_items:
        desc_parts.append(f"{item['bags']}×{item['name']} ({item['total_kg']}kg)")
    description = ", ".join(desc_parts)
    
    # 1. Create Financial Ledger Entry
    ledger = FinancialLedger(
        amount=total,
        direction="OUT",
        payment_method=method,
        transaction_ref=ref,
        category="Feed",
        description=f"Feed Purchase: {description}",
        contact_id=supp_id
    )
    db.add(ledger)
    db.flush()
    
    # 2. Update Inventory for each feed item
    inv_updates = []
    for item in feed_items:
        if item.get('is_new'):
            # Create new inventory item
            inv_item = InventoryItem(
                name=item['name'],
                type="FEED",
                quantity=item['total_kg'],
                unit="kg",
                bag_weight=item['bag_weight'],
                cost_per_unit=item['cost_per_kg']
            )
            db.add(inv_item)
            db.flush()
            inv_updates.append(f"+{item['total_kg']}kg {item['name']} (NEW)")
        else:
            # Update existing
            inv_item = db.query(InventoryItem).filter_by(id=item['id']).first()
            if inv_item:
                inv_item.quantity += item['total_kg']
                inv_item.cost_per_unit = item['cost_per_kg']  # Update to latest cost
                if item['bag_weight']:
                    inv_item.bag_weight = item['bag_weight']
                inv_updates.append(f"+{item['total_kg']}kg {item['name']}")
        
        # Create inventory log
        log = InventoryLog(
            item_name=item['name'],
            quantity_change=item['total_kg'],
            ledger_id=ledger.id
        )
        db.add(log)
    
    db.commit()
    db.close()
    
    await state.clear()
    
    # Success message
    inv_msg = "\n".join([f"📦 {u}" for u in inv_updates])
    ref_text = f" (Ref: {ref})" if ref else ""
    
    await message.answer(
        text=f"✅ **Feed Purchase Recorded!**\n\n"
             f"🏢 From: {supp_name}\n"
             f"💰 Total: {format_currency(total)} via {method}{ref_text}\n\n"
             f"**Inventory Updated:**\n{inv_msg}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )



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
        if qty <= 0: raise ValueError
    except:
        await message.answer("⚠️ Please enter a valid positive number.")
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
    from database import InventoryItem, Flock
    
    cat_name = data.get('cat_name')
    cat_key = data.get('cat_key')
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
    created_item_quantity = 0
    if link_inv:
        qty = data.get('inv_quantity')
        unit = data.get('inv_item_unit', 'units')
        item_id = data.get('inv_item_id')
        is_new = data.get('is_new_item', False)
        created_item_quantity = qty
        
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
            if cat_key == 'cat_feed': item.type = "FEED"
            elif cat_key == 'cat_meds': item.type = "MEDICATION"
            elif cat_key == 'cat_birds': item.type = "LIVESTOCK"
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
                 # Product of amount / final_qty
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

    # Check if Bird Purchase -> Trigger New Flock Flow
    if cat_key == 'cat_birds' and created_item_quantity > 0:
        keyboard = [
            [InlineKeyboardButton(text="🐣 Yes, Create NEW Flock", callback_data="nwflock_yes")],
            [InlineKeyboardButton(text="➕ Yes, Add to EXISTING Flock", callback_data="nwflock_existing")],
            [InlineKeyboardButton(text="❌ No (Just Inventory)", callback_data="nwflock_no")]
        ]
        await message.answer(
            text="🐣 **Manage Flock**\n\nYou bought birds. Do you want to track them?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.update_data(flock_size_total=created_item_quantity)
        await state.set_state(ExpenseStates.new_flock_confirm)
    else:
        await state.clear()



# --- SALES / INCOME HANDLERS ---

@router.callback_query(ExpenseStates.sale_customer, F.data.startswith("cust_"))
async def receive_customer_select(callback: types.CallbackQuery, state: FSMContext):
    cust_id = callback.data.split("_")[1]
    
    if cust_id == "new":
        await callback.message.edit_text("👤 **New Customer Name**\n\nEnter the customer's name:", parse_mode="Markdown")
        await state.set_state(ExpenseStates.new_cust_name)
        await callback.answer()
        return

    if cust_id == "generic":
        cust_id = None
        cust_name = "Walk-in / Generic"
    else:
        db = next(get_db())
        from database import Contact
        c = db.query(Contact).filter_by(id=int(cust_id)).first()
        cust_name = c.name if c else "Unknown"
        db.close()
        
    await state.update_data(customer_id=cust_id, customer_name=cust_name)
    
    # Proceed to sale type
    keyboard = [
        [InlineKeyboardButton(text="🥚 Eggs (Trays/Pcs)", callback_data="sale_eggs")],
        [InlineKeyboardButton(text="🐤 Chicks / Birds / Meat", callback_data="sale_birds")]
    ]
    await callback.message.edit_text(
        text=f"🛒 **Customer: {cust_name}**\n\nWhat are you selling?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.sale_mode)
    await callback.answer()

@router.message(ExpenseStates.new_cust_name)
async def receive_new_customer_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name: return
    
    db = next(get_db())
    from database import Contact
    contact = Contact(name=name, role="CUSTOMER")
    db.add(contact)
    db.commit()
    cid = contact.id
    db.close()
    
    await state.update_data(customer_id=cid, customer_name=name)

    keyboard = [
        [InlineKeyboardButton(text="🥚 Eggs (Trays/Pcs)", callback_data="sale_eggs")],
        [InlineKeyboardButton(text="🐤 Chicks / Birds / Meat", callback_data="sale_birds")]
    ]
    await message.answer(
        text=f"✅ **Customer Added: {name}**\n\nWhat are you selling?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.sale_mode)

@router.callback_query(ExpenseStates.sale_mode, F.data == "sale_eggs")
async def receive_sale_eggs(callback: types.CallbackQuery, state: FSMContext):
    """Handle egg sale - show egg/crate mode selection."""
    keyboard = [
        [InlineKeyboardButton(text="🥚 Per Egg", callback_data="mode_egg")],
        [InlineKeyboardButton(text="📦 Per Crate (30)", callback_data="mode_crate")]
    ]
    await callback.message.edit_text(
        "🥚 **Egg Sale Mode**\n\nSell by:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(ExpenseStates.sale_mode, F.data == "sale_birds")
async def receive_sale_birds(callback: types.CallbackQuery, state: FSMContext):
    """Handle bird sale - show active flocks to select from."""
    db = next(get_db())
    flocks = db.query(Flock).filter_by(status="ACTIVE").filter(Flock.current_count > 0).all()
    db.close()
    
    if not flocks:
        await callback.message.edit_text(
            "⚠️ **No Birds Available**\n\nNo active flocks with birds to sell.",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard('menu_finance')
        )
        await callback.answer()
        return
    
    keyboard = []
    for f in flocks:
        label = f"{f.name} ({f.current_count} birds)"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"sellf_{f.id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_finance")])
    
    await callback.message.edit_text(
        "🐔 **Select Flock**\n\nWhich flock are you selling from?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.sale_flock)
    await callback.answer()

@router.callback_query(ExpenseStates.sale_flock, F.data.startswith("sellf_"))
async def receive_flock_for_sale(callback: types.CallbackQuery, state: FSMContext):
    """Receive flock selection for bird sale."""
    flock_id = int(callback.data.split("_")[1])
    db = next(get_db())
    flock = db.query(Flock).filter_by(id=flock_id).first()
    
    if not flock:
        await callback.answer("Flock not found", show_alert=True)
        db.close()
        return
    
    await state.update_data(sale_mode="mode_bird", sale_flock_id=flock_id, sale_flock_name=flock.name, sale_flock_count=flock.current_count)
    db.close()
    
    await callback.message.edit_text(
        f"🔢 **Quantity**\n\nFlock: **{flock.name}** ({flock.current_count} available)\n\nHow many birds to sell?",
        parse_mode="Markdown"
    )
    await state.set_state(ExpenseStates.sale_quantity)
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
        # Check against selected flock
        flock_count = data.get('sale_flock_count', 0)
        if flock_count < qty:
            await message.answer(
                f"⛔ **Not enough birds!**\n\nFlock: {data.get('sale_flock_name')}\nAvailable: {flock_count}\nTrying to sell: {qty}\n\nTry a lower amount:",
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
        # Deduct from specific flock
        flock_id = data.get('sale_flock_id')
        if flock_id:
            flock = db.query(Flock).filter_by(id=flock_id).first()
            if flock:
                flock.current_count -= qty
        
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

# --- NEW FLOCK HANDLERS ---
@router.callback_query(ExpenseStates.new_flock_confirm, F.data.startswith("nwflock_"))
async def new_flock_decision(callback: types.CallbackQuery, state: FSMContext):
    decision = callback.data.split("_")[1]
    
    if decision == "no":
        await callback.message.edit_text("👍 Okay, kept as inventory only.")
        await state.clear()
        return

    if decision == "existing":
        # logic for existing flock
        db = next(get_db())
        from database import Flock
        flocks = db.query(Flock).filter(Flock.status == 'ACTIVE').all()
        db.close()
        
        if not flocks:
            await callback.answer("⚠️ No active flocks found! Please create a new one.", show_alert=True)
            return

        keyboard = []
        for f in flocks:
            # Breakdown display
            hc = f.hens_count or 0
            rc = f.roosters_count or 0
            label = f"{f.name} ({f.current_count}: {hc}H/{rc}R)"
            keyboard.append([InlineKeyboardButton(text=label, callback_data=f"exflock_{f.id}")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Cancel", callback_data="nwflock_no")])
        
        await callback.message.edit_text(
            text="Select which flock to add birds to:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.set_state(ExpenseStates.existing_flock_select)
        await callback.answer()
        return

    await callback.message.edit_text(
        text="📝 **Flock Name**\n\nGive this flock a name (e.g. 'Batch A Dec 2025'):",
        parse_mode="Markdown"
    )
    await state.set_state(ExpenseStates.new_flock_name)
    await callback.answer()

@router.message(ExpenseStates.new_flock_name)
async def receive_flock_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    
    # Check Uniqueness
    db = next(get_db())
    from database import Flock
    exists = db.query(Flock).filter(Flock.name.ilike(name)).first()
    db.close()
    
    if exists:
        await message.answer(f"⚠️ **Name Taken**\n\nA flock named '{name}' already exists.\n\nPlease enter a different name (e.g., '{name} B'):")
        return

    await state.update_data(new_flock_name=name)
    
    data = await state.get_data()
    total = int(data.get('flock_size_total', 0))
    
    await message.answer(
        text=f"🚻 **Flock Breakdown**\n\nTotal Birds: {total}\n\nHow many are **HENS** (Females)?\nOf the remaining, they will be counted as Roosters.",
        parse_mode="Markdown"
    )
    await state.set_state(ExpenseStates.new_flock_breakdown)

@router.message(ExpenseStates.new_flock_breakdown)
async def receive_hens_count(message: types.Message, state: FSMContext):
    try:
        hens = int(message.text)
        if hens < 0: raise ValueError
    except:
        await message.answer("⚠️ Invalid number.")
        return
        
    data = await state.get_data()
    total = int(data.get('flock_size_total', 0))
    
    if hens > total:
        await message.answer(f"⛔ Cannot have more hens ({hens}) than total birds ({total})!")
        return
        
    roosters = total - hens
    await state.update_data(flock_hens=hens, flock_roosters=roosters)
    
    await message.answer(
        text=f"🔢 Breakdown: **{hens} Hens**, **{roosters} Roosters**.\n\n📅 **Age**\n\nHow old are they in **WEEKS**? (Enter 0 for day-old)",
        parse_mode="Markdown"
    )
    await state.set_state(ExpenseStates.new_flock_age)

@router.message(ExpenseStates.new_flock_age)
async def receive_flock_age(message: types.Message, state: FSMContext):
    try:
        weeks = float(message.text)
        if weeks < 0: raise ValueError
    except:
        await message.answer("⚠️ Invalid number.")
        return
        
    # Calculate Hatch Date
    days_old = int(weeks * 7)
    today = date.today()
    hatch_date = today - timedelta(days=days_old)
    
    # Save Flock
    data = await state.get_data()
    db = next(get_db())
    from database import Flock
    
    flock = Flock(
        name=data['new_flock_name'],
        breed=data.get('item_details', 'Unknown'), # From inventory name
        hatch_date=hatch_date,
        initial_count=data['flock_size_total'],
        current_count=data['flock_size_total'],
        hens_count=data['flock_hens'],
        roosters_count=data['flock_roosters'],
        status="ACTIVE"
    )
    db.add(flock)
    db.commit()
    
    msg_text = (
        f"✅ **Flock Created!**\n\n"
        f"🐔 Name: {flock.name}\n"
        f"🎂 Hatch Date: {hatch_date} ({weeks} wks old)\n"
        f"🚻 {data['flock_hens']} Hens, {data['flock_roosters']} Roosters"
    )
    
    db.close()
    
    await message.answer(
        text=msg_text,
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()

@router.callback_query(ExpenseStates.existing_flock_select, F.data.startswith("exflock_"))
async def receive_existing_flock_select(callback: types.CallbackQuery, state: FSMContext):
    f_id = int(callback.data.split("_")[1])
    await state.update_data(target_flock_id=f_id)
    
    data = await state.get_data()
    total = int(data.get('flock_size_total', 0))
    
    await callback.message.edit_text(
        text=f"🚻 **Added Birds Breakdown**\n\nYou are adding {total} birds.\n\nHow many are **HENS** (Females)?\nRest will be Roosters.",
        parse_mode="Markdown"
    )
    await state.set_state(ExpenseStates.existing_flock_breakdown)
    await callback.answer()

@router.message(ExpenseStates.existing_flock_breakdown)
async def receive_existing_flock_breakdown_count(message: types.Message, state: FSMContext):
    try:
        hens = int(message.text)
        if hens < 0: raise ValueError
    except:
        await message.answer("⚠️ Invalid number.")
        return
        
    data = await state.get_data()
    total = int(data.get('flock_size_total', 0))
    f_id = data.get('target_flock_id')
    
    if hens > total:
        await message.answer(f"⛔ Cannot have more hens ({hens}) than added birds ({total})!")
        return
        
    roosters = total - hens
    
    # Update DB
    db = next(get_db())
    from database import Flock
    flock = db.query(Flock).filter_by(id=f_id).first()
    
    if flock:
        old_count = flock.current_count
        flock.current_count += total
        # Ensure default values if None
        if flock.hens_count is None: flock.hens_count = 0
        if flock.roosters_count is None: flock.roosters_count = 0
        
        flock.hens_count += hens
        flock.roosters_count += roosters
        
        db.commit()
        
        await message.answer(
            text=f"✅ **Flock Updated!**\n\n"
                 f"🐔 Flock: {flock.name}\n"
                 f"📈 Count: {old_count} ➡️ {flock.current_count}\n"
                 f"➕ Added: {hens} Hens, {roosters} Roosters",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer("⚠️ Error finding flock.")
        
    db.close()
    await state.clear()
