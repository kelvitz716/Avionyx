import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import cfg

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=cfg.TELEGRAM_TOKEN)
dp = Dispatcher()

# Middlewares/Checks could go here, but we'll check manually for now

async def main():
    # Import routers here to avoid circular deps if any, 
    # but strictly speaking we should import them at top.
    # We will need to create routers in modules first.
    from modules.eggs import router as eggs_router
    from modules.sales import router as sales_router
    from modules.feed import router as feed_router
    from modules.flock import router as flock_router
    from modules.reports import router as reports_router
    from modules.settings import router as settings_router
    from modules.alerts import router as alerts_router
    
    dp.include_router(eggs_router)
    dp.include_router(sales_router)
    dp.include_router(feed_router)
    dp.include_router(flock_router)
    dp.include_router(reports_router)
    dp.include_router(settings_router)
    dp.include_router(alerts_router)

    # Main Menu Handler (attached to dp directly for now or a common router)
    from utils import get_main_menu_keyboard
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        if message.from_user.id not in cfg.ADMIN_IDS:
             await message.answer("⛔ Access Denied.")
             return
             
        await message.answer(
            "🐔 **Avionyx Manager**\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        
    @dp.callback_query(F.data == "main_menu")
    async def cb_main_menu(callback: types.CallbackQuery):
        await callback.message.edit_text(
            "🐔 **Avionyx Manager**\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()

    print(f"Avionyx Bot Started (Aiogram)! Authorized UIDs: {cfg.ADMIN_IDS}")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
