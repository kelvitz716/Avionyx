from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🥚 Collect Eggs", callback_data='menu_eggs')],
        [InlineKeyboardButton(text="💰 Record Sales", callback_data='menu_sales')],
        [InlineKeyboardButton(text="🍽️ Feed Usage", callback_data='menu_feed')],
        [InlineKeyboardButton(text="⚰️ Mortality", callback_data='menu_mortality')],
        [InlineKeyboardButton(text="🐥 Flock Count", callback_data='menu_flock')],
        [InlineKeyboardButton(text="📊 Reports", callback_data='menu_reports')],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data='menu_settings')]
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
