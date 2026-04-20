"""
Training Handler - Army training center
NEW FEATURE: Train infantry, archers, and cavalry with realistic costs and times.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, Army, Building
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.keyboards import training_menu_keyboard, train_amount_keyboard, back_dashboard_keyboard
from bot.utils.animations import BattleAnimator


async def show_training_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show training center menu"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    # Check barracks level for unit unlocks
    barracks = next((b for b in getattr(kingdom, 'buildings', []) if b.building_type == 'barracks'), None)
    barracks_level = getattr(barracks, 'level', 1) if barracks else 1

    army = getattr(kingdom, 'army', None)
    infantry = getattr(army, 'infantry', 0) if army else 0
    archers = getattr(army, 'archers', 0) if army else 0
    cavalry = getattr(army, 'cavalry', 0) if army else 0

    # Calculate max trainable
    max_inf = EconomyService.get_max_trainable(kingdom, "infantry")
    max_arc = EconomyService.get_max_trainable(kingdom, "archers") if barracks_level >= 2 else 0
    max_cav = EconomyService.get_max_trainable(kingdom, "cavalry") if barracks_level >= 4 else 0

    text = (
        "🏹 **TRAINING CENTER**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n"
        f"🍖 Food: {getattr(kingdom, 'food', 0):,}\n\n"
        f"⚔️ **Current Army:**\n"
        f"  🗡 Infantry: {infantry:,}\n"
        f"  🏹 Archers: {archers:,} (Unlock: Barracks Lv.2)\n"
        f"  🐎 Cavalry: {cavalry:,} (Unlock: Barracks Lv.4)\n\n"
        f"🏹 **Barracks Level:** {barracks_level}\n\n"
        "Select unit to train:"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=training_menu_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=training_menu_keyboard())


async def handle_training_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle training callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "menu_training":
        await show_training_menu(update, context, user_id)

    elif data == "train_infantry":
        await show_train_amount(update, context, user_id, "infantry")

    elif data == "train_archers":
        await show_train_amount(update, context, user_id, "archers")

    elif data == "train_cavalry":
        await show_train_amount(update, context, user_id, "cavalry")

    elif data.startswith("train_amount:"):
        parts = data.split(":")
        unit_type = parts[1]
        amount = int(parts[2])
        await execute_training(update, context, user_id, unit_type, amount)


async def show_train_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, unit_type: str):
    """Show amount selection for training"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    cost = EconomyService.calculate_training_cost(unit_type, 1)

    unit_names = {"infantry": "🗡 Infantry", "archers": "🏹 Archers", "cavalry": "🐎 Cavalry"}
    unit_name = unit_names.get(unit_type, unit_type)

    text = (
        f"{unit_name} **TRAINING**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"💰 Cost per unit: {cost['gold']} Gold, {cost['food']} Food\n"
        f"⏱ Time per unit: {cost['time']} min\n\n"
        f"💰 Your Gold: {getattr(kingdom, 'gold', 0):,}\n"
        f"🍖 Your Food: {getattr(kingdom, 'food', 0):,}\n\n"
        "Select amount:"
    )

    await query.edit_message_text(text, reply_markup=train_amount_keyboard(unit_type))


async def execute_training(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, unit_type: str, amount: int):
    """Execute army training"""
    query = update.callback_query

    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        army = db.query(Army).filter(Army.kingdom_id == user_id).first()

        if not kingdom or not army:
            await query.edit_message_text("❌ Error! Kingdom not found.", reply_markup=back_dashboard_keyboard())
            return

        # Check barracks level requirements
        barracks = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == "barracks"
        ).first()
        barracks_level = getattr(barracks, 'level', 1) if barracks else 1

        if unit_type == "archers" and barracks_level < 2:
            await query.answer("❌ Barracks Lv.2 required for Archers!")
            return

        if unit_type == "cavalry" and barracks_level < 4:
            await query.answer("❌ Barracks Lv.4 required for Cavalry!")
            return

        cost = EconomyService.calculate_training_cost(unit_type, amount)

        if kingdom.gold < cost['gold']:
            await query.answer(f"❌ {cost['gold'] - kingdom.gold:,} more Gold needed!")
            return

        if kingdom.food < cost['food']:
            await query.answer(f"❌ {cost['food'] - kingdom.food:,} more Food needed!")
            return

        # Deduct resources
        kingdom.gold -= cost['gold']
        kingdom.food -= cost['food']
        kingdom.soldiers_trained += amount

        # Add units
        if unit_type == "infantry":
            army.infantry += amount
        elif unit_type == "archers":
            army.archers += amount
        elif unit_type == "cavalry":
            army.cavalry += amount

        db.commit()

    unit_names = {"infantry": "🗡 Infantry", "archers": "🏹 Archers", "cavalry": "🐎 Cavalry"}
    unit_name = unit_names.get(unit_type, unit_type)

    text = (
        f"✅ **TRAINING COMPLETE!**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"{unit_name} x**{amount}** trained!\n\n"
        f"💰 Gold used: {cost['gold']:,}\n"
        f"🍖 Food used: {cost['food']:,}\n"
        f"⏱ Training time: {cost['time_minutes']} min\n\n"
        f"⚔️ New {unit_name} total: {getattr(army, unit_type, 0):,}"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
