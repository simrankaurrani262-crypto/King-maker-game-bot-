"""
Bounty Handler - Bounty system for placing rewards on players
NEW FEATURE: Place bounties on other players, claim bounties by defeating them.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, Bounty
from bot.services.game_data import GameData
from bot.utils.keyboards import bounty_menu_keyboard, back_dashboard_keyboard


# Active bounties store
active_bounties = {}


async def show_bounty_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show bounty system menu"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query and not new_message:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    # Count active bounties
    with get_db() as db:
        total_bounties = db.query(Bounty).filter(Bounty.is_active == True).count()
        my_placed = db.query(Bounty).filter(Bounty.placed_by == user_id, Bounty.is_active == True).count()

    text = (
        "🎯 **BOUNTY BOARD**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n\n"
        f"📋 **Active Bounties:** {total_bounties}\n"
        f"🎯 **My Placed Bounties:** {my_placed}\n\n"
        "Place a bounty on a player to reward\n"
        "whoever defeats them in battle!"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=bounty_menu_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=bounty_menu_keyboard())


async def handle_bounty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bounty callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "menu_bounty":
        await show_bounty_menu(update, context, user_id)

    elif data == "bounty_view":
        await view_bounties(update, context, user_id)

    elif data == "bounty_place":
        await start_place_bounty(update, context, user_id)

    elif data == "bounty_my":
        await view_my_bounties(update, context, user_id)

    elif data.startswith("bounty_claim:"):
        bounty_id = int(data.split(":")[1])
        await claim_bounty(update, context, user_id, bounty_id)


async def view_bounties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """View all active bounties"""
    query = update.callback_query

    with get_db() as db:
        bounties = db.query(Bounty).filter(Bounty.is_active == True).all()

    if not bounties:
        await query.edit_message_text(
            (
                "🎯 **BOUNTY BOARD**\n"
                "━━━━━━━━━━━━━━\n\n"
                "📭 No active bounties!\n\n"
                "Be the first to place one!"
            ),
            reply_markup=bounty_menu_keyboard()
        )
        return

    text = (
        "🎯 **ACTIVE BOUNTIES**\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    buttons = []
    for b in bounties:
        target = db.query(Kingdom).filter(Kingdom.user_id == b.target_id).first()
        target_name = getattr(target, 'name', f"User {b.target_id}") if target else f"User {b.target_id}"
        text += (
            f"🎯 **{target_name}**\n"
            f"   💰 Reward: {b.reward_gold:,} Gold\n"
            f"   👤 Placed by: Anonymous\n"
            f"   ⏳ Expires: {b.expires_at.strftime('%Y-%m-%d')}\n\n"
        )
        buttons.append([InlineKeyboardButton(
            f"⚔️ Hunt {target_name}",
            callback_data=f"attack_player:{b.target_id}"
        )])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_bounty")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def start_place_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start placing a bounty"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)

    text = (
        "🎯 **PLACE BOUNTY**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"💰 Your Gold: {getattr(kingdom, 'gold', 0):,}\n\n"
        "Enter bounty details in this format:\n"
        "`bounty <username> <gold_amount>`\n\n"
        "Example: `bounty EnemyKing 1000`"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


async def view_my_bounties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """View bounties placed by user"""
    query = update.callback_query

    with get_db() as db:
        bounties = db.query(Bounty).filter(Bounty.placed_by == user_id).all()

    if not bounties:
        await query.edit_message_text(
            "🎯 **MY BOUNTIES**\n"
            "━━━━━━━━━━━━━━\n\n"
            "📭 You haven't placed any bounties!",
            reply_markup=bounty_menu_keyboard()
        )
        return

    text = (
        "🎯 **MY BOUNTIES**\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for b in bounties:
        target = db.query(Kingdom).filter(Kingdom.user_id == b.target_id).first()
        target_name = getattr(target, 'name', f"User {b.target_id}") if target else f"User {b.target_id}"
        status = "✅ Active" if b.is_active else "🏆 Claimed"
        text += f"{status} {target_name} — 💰 {b.reward_gold:,} Gold\n"

    await query.edit_message_text(text, reply_markup=bounty_menu_keyboard())


async def claim_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bounty_id: int):
    """Claim a bounty reward"""
    query = update.callback_query

    with get_db() as db:
        bounty = db.query(Bounty).filter(Bounty.id == bounty_id).first()
        if not bounty or not bounty.is_active:
            await query.answer("❌ Bounty not found or already claimed!")
            return

        # Mark as claimed
        bounty.is_active = False
        bounty.claimed_by = user_id

        # Give reward
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if kingdom:
            kingdom.gold += bounty.reward_gold

        db.commit()

    await query.edit_message_text(
        (
            "🏆 **BOUNTY CLAIMED!**\n"
            "━━━━━━━━━━━━━━\n\n"
            f"💰 +{bounty.reward_gold:,} Gold reward collected!\n\n"
            "Well done, bounty hunter!"
        ),
        reply_markup=back_dashboard_keyboard()
    )
