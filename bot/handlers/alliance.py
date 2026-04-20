from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, Alliance, AllianceMember, Kingdom
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.formatters import format_number
from bot.utils.keyboards import (
    alliance_hub_no_alliance_keyboard, alliance_hub_keyboard,
    back_dashboard_keyboard
)
from bot.utils.constants import ALLIANCE_CREATION_COST, ALLIANCE_MAX_MEMBERS


async def show_alliance_hub(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show alliance hub"""
    query = update.callback_query
    
    with get_db() as db:
        member = db.query(AllianceMember).filter(AllianceMember.kingdom_id == user_id).first()
    
    if not member:
        kingdom = GameData.get_kingdom(user_id)
        text = "🤝 **ALLIANCE HUB**\n"
        text += f"━━━━━━━━━━━━━━\n\n"
        text += f"💰 Your Gold: {kingdom.gold:,}\n\n"
        text = f"🤝 **ALLIANCE HUB**\n"
        text += f"━━━━━━━━━━━━━━\n\n"
        text += f"Aap kisi alliance mein nahi ho!\n\n"
        text += f"[🏰 Create Alliance] — {ALLIANCE_CREATION_COST:,} Gold\n"
        text += f"[🔍 Join Alliance] — Open alliances browse karo\n\n"
        text += f"Alliance benefits:\n"
        text += f"🟦 Blue color on map\n"
        text += f"⚔️ Team Wars\n"
        text += f"💰 Shared resources\n"
        
        await query.edit_message_text(text, reply_markup=alliance_hub_no_alliance_keyboard())
        return
    
    # User is in an alliance
    alliance = member.alliance
    members_count = len(alliance.members)
    
    text = f"🤝 **{alliance.name}**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"👑 Leader: {alliance.leader_id}\n"
    text += f"👥 Members: {members_count}/{ALLIANCE_MAX_MEMBERS}\n"
    text += f"🏆 Alliance Power: {format_number(alliance.total_power)}\n"
    text += f"💰 Treasury: {format_number(alliance.gold_treasury)}\n"
    text += f"━━━━━━━━━━━━━━"
    
    await query.edit_message_text(text, reply_markup=alliance_hub_keyboard(alliance.id))


async def handle_alliance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle alliance callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_alliance":
        await show_alliance_hub(update, context, user_id)
    
    elif data == "alliance_create":
        await start_alliance_creation(update, context, user_id)
    
    elif data == "alliance_join":
        await show_open_alliances(update, context, user_id)
    
    elif data.startswith("alliance_join_id:"):
        alliance_id = int(data.split(":")[1])
        await join_alliance(update, context, user_id, alliance_id)
    
    elif data.startswith("alliance_members:"):
        alliance_id = int(data.split(":")[1])
        await show_alliance_members(update, context, user_id, alliance_id)
    
    elif data.startswith("alliance_donate:"):
        alliance_id = int(data.split(":")[1])
        await donate_to_alliance(update, context, user_id, alliance_id)
    
    elif data.startswith("alliance_leave:"):
        alliance_id = int(data.split(":")[1])
        await leave_alliance(update, context, user_id, alliance_id)


async def start_alliance_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start alliance creation flow"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom(user_id)
    if kingdom.gold < ALLIANCE_CREATION_COST:
        await query.answer(f"❌ {ALLIANCE_CREATION_COST:,} Gold chahiye!")
        return
    
    await query.edit_message_text(
        "🏰 **Create Alliance**\n"
        "━━━━━━━━━━━━━━\n\n"
        "Alliance ka naam batao:\n"
        "(3-20 characters)\n\n"
        "Type naam message mein bhejo:",
        reply_markup=back_dashboard_keyboard()
    )
    
    # Store state
    from bot.handlers.start import user_states
    user_states[user_id] = {"step": "alliance_name"}


async def create_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, name: str):
    """Create a new alliance"""
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        
        if kingdom.gold < ALLIANCE_CREATION_COST:
            await update.message.reply_text("❌ Gold kam hai!")
            return
        
        # Check name uniqueness
        existing = db.query(Alliance).filter(Alliance.name == name).first()
        if existing:
            await update.message.reply_text("❌ Ye naam pehle se hai! Dusra chuno:")
            return
        
        kingdom.gold -= ALLIANCE_CREATION_COST
        
        alliance = Alliance(
            name=name,
            leader_id=user_id,
            total_power=EconomyService.calculate_kingdom_power(kingdom),
        )
        db.add(alliance)
        db.commit()
        db.refresh(alliance)
        
        # Add creator as leader
        member = AllianceMember(
            alliance_id=alliance.id,
            kingdom_id=user_id,
            role="leader",
        )
        db.add(member)
        db.commit()
    
    await update.message.reply_text(
        f"🎉 **Alliance Created!**\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"🏰 {name}\n"
        f"👑 Leader: {kingdom.name}\n\n"
        f"Ab dusre players ko invite karo!",
        reply_markup=back_dashboard_keyboard()
    )


async def show_open_alliances(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show open alliances to join"""
    query = update.callback_query
    
    with get_db() as db:
        alliances = db.query(Alliance).all()
    
    if not alliances:
        await query.edit_message_text(
            "❌ Koi alliance available nahi hai!\n"
            "Aap pehla alliance bana sakte ho!",
            reply_markup=alliance_hub_no_alliance_keyboard()
        )
        return
    
    text = "🔍 **OPEN ALLIANCES**\n━━━━━━━━━━━━━━\n\n"
    buttons = []
    for a in alliances:
        member_count = len(a.members)
        if member_count < ALLIANCE_MAX_MEMBERS:
            text += f"🏰 {a.name} ({member_count}/{ALLIANCE_MAX_MEMBERS})\n"
            buttons.append([InlineKeyboardButton(
                f"🤝 Join {a.name}",
                callback_data=f"alliance_join_id:{a.id}"
            )])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_alliance")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def join_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Join an alliance"""
    query = update.callback_query
    
    with get_db() as db:
        existing = db.query(AllianceMember).filter(AllianceMember.kingdom_id == user_id).first()
        if existing:
            await query.answer("❌ Pehle se ek alliance mein ho!")
            return
        
        alliance = db.query(Alliance).filter(Alliance.id == alliance_id).first()
        if not alliance:
            await query.answer("❌ Alliance nahi mila!")
            return
        
        if len(alliance.members) >= ALLIANCE_MAX_MEMBERS:
            await query.answer("❌ Alliance full hai!")
            return
        
        member = AllianceMember(
            alliance_id=alliance_id,
            kingdom_id=user_id,
            role="member",
        )
        db.add(member)
        db.commit()
    
    await query.answer(f"✅ {alliance.name} mein shamil ho gaye!")
    await show_alliance_hub(update, context, user_id)


async def show_alliance_members(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Show alliance members"""
    query = update.callback_query
    
    with get_db() as db:
        alliance = db.query(Alliance).filter(Alliance.id == alliance_id).first()
        if not alliance:
            return
    
    text = f"👥 **{alliance.name} Members**\n━━━━━━━━━━━━━━\n\n"
    for m in alliance.members:
        role_emoji = "👑" if m.role == "leader" else "⚔️" if m.role == "officer" else "👤"
        text += f"{role_emoji} {m.kingdom.name} — {m.role}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data=f"alliance_hub:{alliance_id}")],
        ])
    )


async def donate_to_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Donate gold to alliance treasury"""
    query = update.callback_query
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        alliance = db.query(Alliance).filter(Alliance.id == alliance_id).first()
        
        if not kingdom or not alliance:
            return
        
        donate_amount = min(1000, kingdom.gold)
        if donate_amount < 100:
            await query.answer("❌ Minimum 100 Gold chahiye!")
            return
        
        kingdom.gold -= donate_amount
        alliance.gold_treasury += donate_amount
        db.commit()
    
    await query.answer(f"💰 +{donate_amount:,} Gold donated!")
    await show_alliance_hub(update, context, user_id)


async def leave_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Leave an alliance"""
    query = update.callback_query
    
    with get_db() as db:
        member = db.query(AllianceMember).filter(
            AllianceMember.kingdom_id == user_id,
            AllianceMember.alliance_id == alliance_id
        ).first()
        
        if member:
            if member.role == "leader":
                # Delete alliance if leader leaves
                db.query(AllianceMember).filter(AllianceMember.alliance_id == alliance_id).delete()
                db.query(Alliance).filter(Alliance.id == alliance_id).delete()
            else:
                db.delete(member)
            db.commit()
    
    await query.answer("🚪 Alliance chhod diya!")
    await show_alliance_hub(update, context, user_id)


# ═══════════════════════════════════════════
# ROUTER COMPATIBILITY WRAPPERS
# ═══════════════════════════════════════════

async def show_alliance_create(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for alliance creation flow"""
    await start_alliance_creation(update, context, user_id)


async def show_alliance_list(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for showing open alliances"""
    await show_open_alliances(update, context, user_id)


async def show_donate_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Wrapper for alliance donation"""
    await donate_to_alliance(update, context, user_id, alliance_id)


async def handle_alliance_leave(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Wrapper for leaving alliance"""
    await leave_alliance(update, context, user_id, alliance_id)


async def handle_join_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, alliance_id: int):
    """Wrapper for joining alliance"""
    await join_alliance(update, context, user_id, alliance_id)
