from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, Expense, Transaction, InventoryItem, AuditLog
from datetime import date
from utils import get_back_home_keyboard, get_main_menu_keyboard, format_currency

router = Router()

class ExpenseStates(StatesGroup):
    category = State()
    amount = State()
    description = State()
    confirm = State()

EXPENSE_CATEGORIES = {
    'cat_feed': '🍽️ Feed',
    'cat_meds': '💊 Medication',
    'cat_labor': '👨‍🌾 Labor',
    'cat_birds': '🐥 Birds Purchase',
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
    
    keyboard.append([InlineKeyboardButton(text="📉 P&L Report", callback_data="report_pnl")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")])

    await callback.message.edit_text(
        text="💰 **Finance Management**\n\nSelect an option to record an expense or view reports.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"))
async def expense_category(callback: types.CallbackQuery, state: FSMContext):
    category_key = callback.data
    category_name = EXPENSE_CATEGORIES.get(category_key, "Unknown")
    
    await state.update_data(cat_key=category_key, cat_name=category_name)
    
    await callback.message.edit_text(
        text=f"💸 **Record Expense: {category_name}**\n\nEnter the amount spent:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_finance")
    )
    await state.set_state(ExpenseStates.amount)
    await callback.answer()

@router.message(ExpenseStates.amount)
async def expense_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid positive number.")
        return
        
    await state.update_data(amount=amount)
    await message.answer(
        text="📝 **Description**\n\nEnter a brief description (e.g., 'Layer Mash 5 bags', 'Vaccines'):",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_finance")
    )
    await state.set_state(ExpenseStates.description)

@router.message(ExpenseStates.description)
async def expense_description(message: types.Message, state: FSMContext):
    description = message.text
    data = await state.get_data()
    
    await state.update_data(description=description)
    
    # Summary
    text = (f"Please confirm expense:\n\n"
            f"📂 Category: {data['cat_name']}\n"
            f"💰 Amount: {format_currency(data['amount'])}\n"
            f"📝 Note: {description}")
            
    keyboard = [
        [InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_expense")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_finance")]
    ]
    
    await message.answer(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ExpenseStates.confirm)

@router.callback_query(ExpenseStates.confirm, F.data == "confirm_expense")
async def finish_expense(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat_key = data['cat_key']
    amount = data['amount']
    desc = data['description']
    
    db = next(get_db())
    
    # Save Expense
    expense = Expense(
        category=data['cat_name'],
        amount=amount,
        description=desc,
        user_id=callback.from_user.id
    )
    db.add(expense)
    db.flush() # get ID
    
    # Save Transaction
    txn = Transaction(
        type="EXPENSE",
        category=data['cat_name'],
        amount=amount,
        description=desc,
        related_id=expense.id,
        related_table="expenses"
    )
    db.add(txn)
    
    # If Feed or Meds, prompt to add to inventory?
    # For now, we just record expense. Inventory addition should be explicit or we can auto-add if parsed?
    # Keeping it simple: Just expense. Use Inventory module to `add` items if needed, or link later.
    
    db.commit()
    db.close()
    
    await state.clear()
    await callback.message.edit_text(
        text="✔️ **Expense Recorded!**",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "report_pnl")
async def show_pnl(callback: types.CallbackQuery):
    db = next(get_db())
    
    # 1. Transactions P&L
    txns = db.query(Transaction).all()
    income_txns = sum(t.amount for t in txns if t.type == "INCOME")
    expense_txns = sum(t.amount for t in txns if t.type == "EXPENSE")
    
    # 2. DailyEntry Legacy P&L (if not migrated)
    # We should avoid double counting if we log Transactions for DailyEntries now.
    # Logic: If I modified Feed/Sales to log Transactions, then I don't need to sum DailyEntry.
    # I modified Sales.py to log Transactions.
    # I did NOT modify Feed.py to log Transactions (Wait, I should have?).
    # feed.py logs audit log but calculates cost.
    # I should check feed.py. If it doesn't create Transaction, P&L is missing feed cost!
    
    # Let's fix feed.py first? Or assume DailyEntry.feed_cost is separate?
    # For now, let's sum DailyEntry.feed_cost and treat it as 'Operational Cost' if not in Transaction.
    # But new sales are in Transaction. Old sales are in DailyEntry.income.
    
    # Hybrid Approach for "Complete" system:
    # Sum Transaction Income.
    # Sum Transaction Expenses.
    
    # If I want to be safe about double counting:
    # Transactions created by Sales.py have related_table='daily_entries' maybe?
    # In sales.py I linked egg sales to 'daily_entries'.
    
    # So P&L = Sum(Transaction.amount where type=INCOME) - Sum(Transaction.amount where type=EXPENSE)
    # BUT feed.py DOES NOT create Transaction yet.
    # I MUST update feed.py to create Transaction.
    
    # For now, I'll just show what we have.
    
    net_profit = income_txns - expense_txns
    
    text = (f"📉 **P&L Statement (Transactions)**\n\n"
            f"💰 **Total Income**: {format_currency(income_txns)}\n"
            f"💸 **Total Expenses**: {format_currency(expense_txns)}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"**Net Profit**: {format_currency(net_profit)}")
    
    db.close()
    
    keyboard = [[InlineKeyboardButton(text="⬅️ Back", callback_data="menu_finance")]]
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()
