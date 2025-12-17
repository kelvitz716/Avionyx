from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🥚 Eggs", callback_data='menu_eggs'),
         InlineKeyboardButton(text="🍽️ Feed", callback_data='menu_feed')],
        [InlineKeyboardButton(text="🐥 Flock", callback_data='menu_flock'),
         InlineKeyboardButton(text="💰 Sales", callback_data='menu_sales')],
        [InlineKeyboardButton(text="💵 Finance", callback_data='menu_finance'),
         InlineKeyboardButton(text="📦 Inventory", callback_data='menu_inventory')],
        [InlineKeyboardButton(text="📊 Reports", callback_data='menu_reports'),
         InlineKeyboardButton(text="⚙️ Settings", callback_data='menu_settings')]
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
