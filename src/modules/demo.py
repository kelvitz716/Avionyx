from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup
import database
from utils import get_main_menu_keyboard

router = Router()

@router.callback_query(F.data == "menu_demo_info")
async def cb_demo_info(callback: types.CallbackQuery):
    state_status = "🔴 ACTIVE" if database.IS_DEMO_MODE else "⚪ INACTIVE"
    await callback.message.edit_text(
        f"🎮 **Demo Mode**\n\nCurrent Status: {state_status}\n\n"
        "Use `/demo start` to enter Demo Mode (Sandbox).\n"
        "Use `/demo stop` to exit and WIPE data.",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard() # Keep them in menu flow
    )
    await callback.answer()

@router.message(Command("demo"))
async def cmd_demo(message: types.Message, command: CommandObject):
    arg = command.args
    
    if not arg or arg not in ["start", "stop"]:
        state_status = "🔴 ACTIVE" if database.IS_DEMO_MODE else "⚪ INACTIVE"
        await message.answer(
            f"🎮 **Demo Mode**\n\nCurrent Status: {state_status}\n\n"
            "Use `/demo start` to enter Demo Mode (Sandbox).\n"
            "Use `/demo stop` to exit and WIPE data.",
            parse_mode="Markdown"
        )
        return

    if arg == "start":
        if database.IS_DEMO_MODE:
            await message.answer("⚠️ Demo mode is already active.", reply_markup=get_main_menu_keyboard())
            return
            
        database.IS_DEMO_MODE = True
        database.init_demo_db()
        
        await message.answer(
            "🔴 **DEMO MODE ACTIVATED** 🔴\n\n"
            "You are now in a sandbox environment. \n"
            "✅ All actions are temporary.\n"
            "❌ Data will be DELETED when you exit.",
            reply_markup=get_main_menu_keyboard()
        )
        
    elif arg == "stop":
        if not database.IS_DEMO_MODE:
            await message.answer("⚠️ You are not in Demo Mode.", reply_markup=get_main_menu_keyboard())
            return
            
        database.wipe_demo_db() # Also sets IS_DEMO_MODE = False
        
        await message.answer(
            "⚪ **Demo Mode Deactivated**\n\n"
            "Sandbox data has been wiped.\n"
            "You are back to Production.",
            reply_markup=get_main_menu_keyboard()
        )
