import database
from database import get_db, User
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Role-based permissions
ROLE_PERMISSIONS = {
    "ADMIN": ["daily_wizard", "finance", "inventory", "health", "reports", "settings", "demo", "contacts"],
    "MANAGER": ["daily_wizard", "finance", "inventory", "health", "reports", "contacts"],
    "STAFF": ["daily_wizard", "health"]  # Basic access only
}

def get_user_role(telegram_id: int) -> str:
    """Get user role from database, default to ADMIN for ADMIN_IDS, STAFF otherwise."""
    from config import cfg
    try:
        db = next(get_db())
        user = db.query(User).filter_by(telegram_id=telegram_id, is_active=True).first()
        db.close()
        if user:
            return user.role
    except Exception:
        pass  # Table doesn't exist yet or other DB error
    
    # Fallback: ADMIN_IDS get ADMIN role, others get STAFF
    return "ADMIN" if telegram_id in cfg.ADMIN_IDS else "STAFF"

def get_main_menu_keyboard(role: str = "ADMIN"):
    """Generate role-filtered main menu keyboard."""
    demo_label = "🔴 Demo Mode Active" if database.IS_DEMO_MODE else "🎮 Demo Mode"
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["STAFF"])
    
    keyboard = []
    
    # Row 1: Daily Update (everyone)
    if "daily_wizard" in perms:
        keyboard.append([InlineKeyboardButton(text="📝 Daily Update", callback_data='menu_daily_wizard')])
    
    # Row 2: Finance & Inventory
    row2 = []
    if "finance" in perms:
        row2.append(InlineKeyboardButton(text="💵 Finance", callback_data='menu_finance'))
    if "inventory" in perms:
        row2.append(InlineKeyboardButton(text="📦 Inventory", callback_data='menu_inventory'))
    if row2:
        keyboard.append(row2)
    
    # Row 3: Health & Contacts
    row3 = []
    if "health" in perms:
        row3.append(InlineKeyboardButton(text="❤️ Health", callback_data='menu_health'))
    if "contacts" in perms:
        row3.append(InlineKeyboardButton(text="📇 Contacts", callback_data='menu_contacts'))
    if row3:
        keyboard.append(row3)
    
    # Row 4: Reports & Settings
    row4 = []
    if "reports" in perms:
        row4.append(InlineKeyboardButton(text="📊 Reports", callback_data='menu_reports'))
    if "settings" in perms:
        row4.append(InlineKeyboardButton(text="⚙️ Settings", callback_data='menu_settings'))
    if row4:
        keyboard.append(row4)
    
    # Demo button (admin only)
    if "demo" in perms:
        keyboard.append([InlineKeyboardButton(text=demo_label, callback_data='menu_demo_info')])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_home_keyboard(back_callback: str = 'main_menu'):
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback),
         InlineKeyboardButton(text="🏠 Home", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_currency(amount: float) -> str:
    return f"Ksh {amount:,.0f}"
 # Adjustable currency
