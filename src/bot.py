import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramNetworkError
from config import cfg
from tenacity import retry, stop_never, wait_exponential, retry_if_exception_type, before_sleep_log

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=cfg.TELEGRAM_TOKEN)
dp = Dispatcher()

VERSION = "3.0.0"

@retry(
    stop=stop_never,
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((TelegramNetworkError, ConnectionError, OSError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def resilient_polling():
    """Start polling with automatic retry on network errors."""
    logger.info("Starting polling...")
    await dp.start_polling(bot)

async def main():
    # Import routers
    from modules.reports import router as reports_router
    from modules.settings import router as settings_router
    from modules.alerts import router as alerts_router
    from modules.finance import router as finance_router
    from modules.inventory import router as inventory_router
    from modules.contacts import router as contacts_router
    from modules.demo import router as demo_router
    from modules.health import router as health_router
    from modules.daily_wizard import router as wizard_router
    
    # Register routers
    for r in [reports_router, settings_router, alerts_router, finance_router, 
              inventory_router, contacts_router, demo_router, health_router, wizard_router]:
        dp.include_router(r)

    # Main Menu Handler
    from utils import get_main_menu_keyboard, get_user_role
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        if message.from_user.id not in cfg.ADMIN_IDS:
             await message.answer("⛔ Access Denied.")
             return
        
        role = get_user_role(message.from_user.id)
        await message.answer(
            "🐔 **Avionyx Manager**\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(role),
            parse_mode="Markdown"
        )
        
    @dp.callback_query(F.data == "main_menu")
    async def cb_main_menu(callback: types.CallbackQuery):
        role = get_user_role(callback.from_user.id)
        await callback.message.edit_text(
            "🐔 **Avionyx Manager**\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(role),
            parse_mode="Markdown"
        )
        await callback.answer()

    print(f"Avionyx Bot Started (v{VERSION})! Authorized UIDs: {cfg.ADMIN_IDS}")
    await resilient_polling()

if __name__ == '__main__':
    asyncio.run(main())

