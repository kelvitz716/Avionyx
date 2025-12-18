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
    adjust_trust_amount = State()
    adjust_trust_reason = State()

def get_trust_emoji(score: int) -> str:
    """Return emoji based on trust score tier."""
    if score >= 90: return "🟢"
    elif score >= 70: return "🟡"
    elif score >= 50: return "🟠"
    elif score >= 30: return "🔴"
    else: return "⚫"

def get_trust_label(score: int) -> str:
    """Return label based on trust score tier."""
    if score >= 90: return "Excellent"
    elif score >= 70: return "Good"
    elif score >= 50: return "Fair"
    elif score >= 30: return "Poor"
    else: return "Critical"

@router.callback_query(F.data == "menu_contacts")
async def menu_contacts(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="📋 View Contacts", callback_data="contacts_list")],
        [InlineKeyboardButton(text="➕ Add Contact", callback_data="menu_add_contact_redirect")],
        [InlineKeyboardButton(text="📊 Trust Report", callback_data="contacts_trust_report")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
    ]
    await callback.message.edit_text(
        "📇 **Contact Management**\n\nManage suppliers, customers, and staff:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "contacts_list")
async def list_contacts(callback: types.CallbackQuery):
    db = next(get_db())
    contacts = db.query(Contact).order_by(Contact.name).all()
    db.close()
    
    if not contacts:
        await callback.message.edit_text(
            "📭 No contacts found.\n\nAdd your first contact to get started.",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("menu_contacts")
        )
        await callback.answer()
        return

    keyboard = []
    for c in contacts:
        emoji = get_trust_emoji(c.trust_score)
        keyboard.append([InlineKeyboardButton(
            text=f"{emoji} {c.name} ({c.role})",
            callback_data=f"contact_view_{c.id}"
        )])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu_contacts")])
    
    await callback.message.edit_text(
        "📋 **Contact List**\n\nSelect a contact to view details:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("contact_view_"))
async def view_contact(callback: types.CallbackQuery):
    contact_id = int(callback.data.split("_")[2])
    db = next(get_db())
    c = db.query(Contact).filter_by(id=contact_id).first()
    db.close()
    
    if not c:
        await callback.answer("Contact not found", show_alert=True)
        return

    emoji = get_trust_emoji(c.trust_score)
    label = get_trust_label(c.trust_score)
    
    text = f"📇 **{c.name}**\n\n"
    text += f"👤 **Role:** {c.role}\n"
    text += f"📞 **Phone:** {c.phone or 'Not set'}\n"
    text += f"📝 **Notes:** {c.notes or 'None'}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"{emoji} **Trust Score:** `{c.trust_score}/100` ({label})\n"
    
    keyboard = [
        [InlineKeyboardButton(text="📈 Adjust Trust", callback_data=f"trust_adjust_{c.id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="contacts_list")]
    ]
    
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("trust_adjust_"))
async def start_trust_adjust(callback: types.CallbackQuery, state: FSMContext):
    contact_id = int(callback.data.split("_")[2])
    db = next(get_db())
    c = db.query(Contact).filter_by(id=contact_id).first()
    db.close()
    
    await state.update_data(contact_id=contact_id, contact_name=c.name, current_score=c.trust_score)
    
    keyboard = [
        [InlineKeyboardButton(text="➕ +5 (Good)", callback_data="trust_change_+5")],
        [InlineKeyboardButton(text="➕ +10 (Great)", callback_data="trust_change_+10")],
        [InlineKeyboardButton(text="➖ -5 (Issue)", callback_data="trust_change_-5")],
        [InlineKeyboardButton(text="➖ -10 (Problem)", callback_data="trust_change_-10")],
        [InlineKeyboardButton(text="⬅️ Cancel", callback_data=f"contact_view_{contact_id}")]
    ]
    
    await callback.message.edit_text(
        f"📈 **Adjust Trust Score**\n\n"
        f"Contact: **{c.name}**\n"
        f"Current: `{c.trust_score}/100`\n\n"
        f"Select adjustment:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("trust_change_"))
async def receive_trust_change(callback: types.CallbackQuery, state: FSMContext):
    change = int(callback.data.split("_")[2])
    await state.update_data(trust_change=change)
    
    await callback.message.edit_text(
        f"📝 **Reason Required**\n\n"
        f"Adjustment: `{'+' if change > 0 else ''}{change}` points\n\n"
        f"Please enter a reason for this change:",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_contacts")
    )
    await state.set_state(ContactStates.adjust_trust_reason)
    await callback.answer()

@router.message(ContactStates.adjust_trust_reason)
async def save_trust_adjustment(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    if not reason:
        await message.answer("⚠️ Reason is required. Please enter a reason:")
        return
    
    data = await state.get_data()
    contact_id = data['contact_id']
    change = data['trust_change']
    
    db = next(get_db())
    c = db.query(Contact).filter_by(id=contact_id).first()
    
    old_score = c.trust_score
    new_score = max(0, min(100, old_score + change))
    c.trust_score = new_score
    
    # Append to notes
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d")
    note = f"[{timestamp}] Trust {'+' if change > 0 else ''}{change}: {reason}"
    c.notes = (c.notes + "\n" + note) if c.notes else note
    
    db.commit()
    db.close()
    
    await state.clear()
    
    emoji = get_trust_emoji(new_score)
    await message.answer(
        f"✅ **Trust Score Updated**\n\n"
        f"Contact: **{data['contact_name']}**\n"
        f"Change: `{'+' if change > 0 else ''}{change}`\n"
        f"New Score: {emoji} `{new_score}/100`\n"
        f"Reason: _{reason}_",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "contacts_trust_report")
async def trust_report(callback: types.CallbackQuery):
    db = next(get_db())
    contacts = db.query(Contact).all()
    db.close()
    
    if not contacts:
        await callback.message.edit_text(
            "📊 **Trust Report**\n\nNo contacts to analyze.",
            parse_mode="Markdown",
            reply_markup=get_back_home_keyboard("menu_contacts")
        )
        await callback.answer()
        return

    # Group by tier
    tiers = {"🟢 Excellent": [], "🟡 Good": [], "🟠 Fair": [], "🔴 Poor": [], "⚫ Critical": []}
    for c in contacts:
        emoji = get_trust_emoji(c.trust_score)
        label = get_trust_label(c.trust_score)
        tiers[f"{emoji} {label}"].append(c.name)
    
    text = "📊 **Trust Report**\n\n"
    for tier, names in tiers.items():
        if names:
            text += f"**{tier}** ({len(names)})\n"
            text += ", ".join(names[:3])
            if len(names) > 3:
                text += f" +{len(names)-3} more"
            text += "\n\n"
    
    # Low trust warnings
    low_trust = [c for c in contacts if c.trust_score < 50]
    if low_trust:
        text += "⚠️ **Action Recommended:**\n"
        for c in low_trust[:3]:
            text += f"• {c.name} ({c.trust_score}) - Review history\n"
    
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=get_back_home_keyboard("menu_contacts")
    )
    await callback.answer()

# --- Original flows preserved below ---

@router.message(Command("newcontact"))
async def cmd_new_contact(message: types.Message, state: FSMContext):
    await start_new_contact_flow(message, state)

@router.callback_query(F.data == "menu_add_contact_redirect")
async def cb_new_contact_redirect(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📇 **New Contact**\n\nWhat is the name of the person or business?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('main_menu')
    )
    await state.set_state(ContactStates.name)
    await callback.answer()

async def start_new_contact_flow(message: types.Message, state: FSMContext):
    await message.answer(
        "📇 **New Contact**\n\nWhat is the name of the person or business?",
        parse_mode="Markdown",
        reply_markup=get_back_home_keyboard('main_menu')
    )
    await state.set_state(ContactStates.name)

@router.message(ContactStates.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    roles = ["SUPPLIER", "CUSTOMER", "VET", "STAFF"]
    keyboard = [[InlineKeyboardButton(text=r, callback_data=f"role_{r}")] for r in roles]
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
    new_contact = Contact(name=data['name'], role=data['role'], phone=phone)
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

