import database
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    demo_label = "🔴 Demo Mode Active" if database.IS_DEMO_MODE else "🎮 Demo Mode"
    
    keyboard = [
        [InlineKeyboardButton(text="📝 Daily Update", callback_data='menu_daily_wizard')],
        [InlineKeyboardButton(text="💵 Finance", callback_data='menu_finance'),
         InlineKeyboardButton(text="📦 Inventory", callback_data='menu_inventory')],
        [InlineKeyboardButton(text="📊 Reports", callback_data='menu_reports'),
         InlineKeyboardButton(text="⚙️ Settings", callback_data='menu_settings')],
         [InlineKeyboardButton(text=demo_label, callback_data='menu_demo_info')] # Added Demo Button for visibility
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_home_keyboard(back_callback: str = 'main_menu'):
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback),
         InlineKeyboardButton(text="🏠 Home", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_currency(amount: float) -> str:
    return f"Ksh {amount:,.0f}" # Adjustable currency
