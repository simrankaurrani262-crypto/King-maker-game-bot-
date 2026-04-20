"""
Trade Handler - Resource trading system
NEW FEATURE: Trade gold, food, and gems with dynamic rates.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.keyboards import trade_menu_keyboard, back_dashboard_keyboard


async def show_trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show trade menu"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query and not new_message:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    text = (
        "💱 **TRADING POST**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n"
        f"🍖 Food: {getattr(kingdom, 'food', 0):,}\n"
        f"💎 Gems: {getattr(kingdom, 'gems', 0):,}\n\n"
        "**Exchange Rates:**\n"
        "💰 1 Gold → 🍖 2 Food\n"
        "🍖 1 Food → 💰 0.35 Gold\n"
        "💎 1 Gem → 💰 500 Gold\n\n"
        "Select trade:"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=trade_menu_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=trade_menu_keyboard())


async def handle_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trade callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "menu_trade":
        await show_trade_menu(update, context, user_id)

    elif data == "trade_gold_food":
        await show_trade_amount(update, context, user_id, "gold", "food")

    elif data == "trade_food_gold":
        await show_trade_amount(update, context, user_id, "food", "gold")

    elif data == "trade_gems_gold":
        await show_trade_amount(update, context, user_id, "gems", "gold")

    elif data.startswith("trade_execute:"):
        parts = data.split(":")
        resource_from = parts[1]
        resource_to = parts[2]
        amount = int(parts[3])
        await execute_trade(update, context, user_id, resource_from, resource_to, amount)


async def show_trade_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, resource_from: str, resource_to: str):
    """Show trade amount options"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    rate = EconomyService.calculate_trade_rate(resource_from, resource_to)

    # Calculate available amounts
    if resource_from == "gold":
        available = getattr(kingdom, 'gold', 0)
        from_emoji, to_emoji = "💰", "🍖"
    elif resource_from == "food":
        available = getattr(kingdom, 'food', 0)
        from_emoji, to_emoji = "🍖", "💰"
    elif resource_from == "gems":
        available = getattr(kingdom, 'gems', 0)
        from_emoji, to_emoji = "💎", "💰"
    else:
        return

    # Predefined trade amounts
    amounts = []
    for base in [100, 500, 1000, 5000]:
        if available >= base:
            amounts.append({
                'from': base,
                'to': int(base * rate),
                'from_emoji': from_emoji,
                'to_emoji': to_emoji,
            })

    if not amounts:
        await query.edit_message_text(
            f"❌ Not enough {resource_from} to trade!",
            reply_markup=back_dashboard_keyboard()
        )
        return

    text = (
        f"💱 **TRADE: {from_emoji} {resource_from.upper()} → {to_emoji} {resource_to.upper()}**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"Rate: 1 {resource_from} = {rate} {resource_to}\n"
        f"Available: {available:,} {resource_from}\n\n"
        "Select amount:"
    )

    from bot.utils.keyboards import trade_amount_keyboard
    await query.edit_message_text(text, reply_markup=trade_amount_keyboard(resource_from, resource_to, amounts))


async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, resource_from: str, resource_to: str, amount: int):
    """Execute trade"""
    query = update.callback_query

    rate = EconomyService.calculate_trade_rate(resource_from, resource_to)
    amount_to = int(amount * rate)

    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return

        # Check and deduct
        if resource_from == "gold":
            if kingdom.gold < amount:
                await query.answer("❌ Not enough Gold!")
                return
            kingdom.gold -= amount
            if resource_to == "food":
                kingdom.food += amount_to
        elif resource_from == "food":
            if kingdom.food < amount:
                await query.answer("❌ Not enough Food!")
                return
            kingdom.food -= amount
            if resource_to == "gold":
                kingdom.gold += amount_to
        elif resource_from == "gems":
            if kingdom.gems < amount:
                await query.answer("❌ Not enough Gems!")
                return
            kingdom.gems -= amount
            if resource_to == "gold":
                kingdom.gold += amount_to

        db.commit()

    from_emojis = {"gold": "💰", "food": "🍖", "gems": "💎"}
    to_emojis = {"gold": "💰", "food": "🍖", "gems": "💎"}

    text = (
        "✅ **TRADE SUCCESSFUL!**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"{from_emojis.get(resource_from, '')} -{amount:,} {resource_from.title()}\n"
        f"{to_emojis.get(resource_to, '')} +{amount_to:,} {resource_to.title()}\n\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n"
        f"🍖 Food: {getattr(kingdom, 'food', 0):,}\n"
        f"💎 Gems: {getattr(kingdom, 'gems', 0):,}"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
