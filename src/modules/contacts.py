from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, Contact
from utils import get_main_menu_keyboard, get_back_home_keyboard

router = Router()

class ContactStates(StatesGroup):
    name = State()
    role = State()
    phone = State()

@router.message(Command("newcontact"))
async def cmd_new_contact(message: types.Message, state: FSMContext):
    await start_new_contact_flow(message, state)

@router.callback_query(F.data == "menu_add_contact_redirect")
async def cb_new_contact_redirect(callback: types.CallbackQuery, state: FSMContext):
    await start_new_contact_flow(callback.message, state)
    await callback.answer()

async def start_new_contact_flow(message: types.Message, state: FSMContext):
    await message.edit_text(
        "📇 **New Contact**\n\nWhat is the name of the person or business?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('main_menu')
    ) if isinstance(message, types.Message) and message.from_user.is_bot else \
    await message.answer(
        "📇 **New Contact**\n\nWhat is the name of the person or business?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('main_menu')
    )
    await state.set_state(ContactStates.name)

@router.message(ContactStates.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    # Role Selection Keyboard
    roles = ["SUPPLIER", "CUSTOMER", "VET", "STAFF"]
    keyboard = []
    for role in roles:
        keyboard.append([InlineKeyboardButton(text=role, callback_data=f"role_{role}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")])
    
    await message.answer(
        f"👤 **Role**\n\nWhat is the role of {message.text}?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ContactStates.role)

@router.callback_query(ContactStates.role, F.data.startswith("role_"))
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    await state.update_data(role=role)
    
    await callback.message.edit_text(
        f"📱 **Phone**\n\nEnter the phone number for this {role}:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('main_menu')
    )
    await state.set_state(ContactStates.phone)
    await callback.answer()

@router.message(ContactStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    data = await state.get_data()
    
    db = next(get_db())
    new_contact = Contact(
        name=data['name'],
        role=data['role'],
        phone=phone
    )
    db.add(new_contact)
    db.commit()
    db.close()
    
    await state.clear()
    await message.answer(
        f"✅ **Contact Saved!**\n\n"
        f"Name: {data['name']}\n"
        f"Role: {data['role']}\n"
        f"Phone: {phone}",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("listcontacts"))
async def cmd_list_contacts(message: types.Message):
    db = next(get_db())
    contacts = db.query(Contact).all()
    db.close()
    
    if not contacts:
        await message.answer("📭 No contacts found.", reply_markup=get_main_menu_keyboard())
        return

    text = "📋 **Contact List**\n\n"
    for c in contacts:
        text += f"🔹 **{c.name}** ({c.role})\n   📞 {c.phone}\n\n"
        
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
