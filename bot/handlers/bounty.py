"""
Bounty Handler - Place bounties and claim rewards
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Bounty, Kingdom, Army
from bot.services.game_data import GameData
from bot.services.combat_engine import CombatEngine
from bot.utils.keyboards import (
    bounty_menu_keyboard,
    bounty_place_keyboard,
    back_dashboard_keyboard,
    back_dashboard_keyboard,
)


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
        f"🎯 Active Bounties: {total_bounties}\n"
        f"📌 Your Bounties: {my_placed}\n\n"
        "Dusre players par bounty lagao!\n"
        "Jo bounty complete karega usse reward milega!"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=bounty_menu_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=bounty_menu_keyboard())


async def view_bounties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show active bounties"""
    query = update.callback_query

    with get_db() as db:
        bounties = db.query(Bounty).filter(Bounty.is_active == True).order_by(Bounty.reward_gold.desc()).limit(10).all()

    if not bounties:
        await query.edit_message_text(
            "🎯 **BOUNTY BOARD**\n"
            "━━━━━━━━━━━━━━\n\n"
            "❌ Koi active bounty nahi hai!\n\n"
            "Pehli bounty lagao!",
            reply_markup=bounty_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    text = "🎯 **ACTIVE BOUNTIES**\n━━━━━━━━━━━━━━\n\n"
    for i, bounty in enumerate(bounties[:5]):
        target = db.query(Kingdom).filter(Kingdom.user_id == bounty.target_id).first()
        target_name = target.name if target else "Unknown"

        text += (
            f"{i+1}. 👑 **{target_name}**\n"
            f"   💰 Reward: {bounty.reward_gold:,} Gold\n"
            f"   🎯 Condition: {bounty.condition}\n\n"
        )

    await query.edit_message_text(text, reply_markup=bounty_menu_keyboard(), parse_mode="Markdown")


async def start_place_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start placing a bounty"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    text = (
        "🎯 **PLACE BOUNTY**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"💰 Your Gold: {getattr(kingdom, 'gold', 0):,}\n\n"
        "Select bounty type:\n"
        "💰 1000 Gold\n"
        "💰 5000 Gold\n"
        "💰 10000 Gold\n"
        "💰 50000 Gold"
    )

    await query.edit_message_text(text, reply_markup=bounty_place_keyboard())


async def view_my_bounties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show my active bounties"""
    query = update.callback_query

    with get_db() as db:
        bounties = db.query(Bounty).filter(
            Bounty.placed_by == user_id,
            Bounty.is_active == True
        ).all()

    if not bounties:
        await query.edit_message_text(
            "📌 **MY BOUNTIES**\n"
            "━━━━━━━━━━━━━━\n\n"
            "❌ Aapne koi bounty nahi lagayi!",
            reply_markup=bounty_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    text = "📌 **MY BOUNTIES**\n━━━━━━━━━━━━━━\n\n"
    for bounty in bounties:
        target = db.query(Kingdom).filter(Kingdom.user_id == bounty.target_id).first()
        target_name = target.name if target else "Unknown"

        text += (
            f"🎯 **{target_name}**\n"
            f"💰 Reward: {bounty.reward_gold:,} Gold\n"
            f"📅 Placed: {bounty.created_at.strftime('%Y-%m-%d') if bounty.created_at else 'N/A'}\n\n"
        )

    await query.edit_message_text(text, reply_markup=bounty_menu_keyboard(), parse_mode="Markdown")


# ═══════════════════════════════════════════
# ROUTER COMPATIBILITY WRAPPERS
# ═══════════════════════════════════════════

async def show_active_bounties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for viewing active bounties"""
    await view_bounties(update, context, user_id)


async def show_place_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for starting bounty placement"""
    await start_place_bounty(update, context, user_id)


async def show_my_bounties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for viewing my bounties"""
    await view_my_bounties(update, context, user_id)
