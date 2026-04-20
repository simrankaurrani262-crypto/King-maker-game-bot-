"""
Buildings Handler - Building management, upgrades, and collection.
Fixed version with all callback handlers and show_building_menu function.
"""

from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, Building
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.keyboards import (
    building_menu_keyboard,
    building_action_keyboard,
    back_dashboard_keyboard,
)
from bot.utils.constants import BUILDING_CONFIG
from bot.utils.formatters import format_time_remaining, format_duration


# ═══════════════════════════════════════════
# BUILDING MENU
# ═══════════════════════════════════════════

async def show_building_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show building menu - FIXED: renamed from show_building_list"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query and not new_message:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    buildings = getattr(kingdom, 'buildings', []) or []

    text = (
        "🏗 **BUILDINGS**\n"
        "━━━━━━━━━━━━━━\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n"
        f"🍖 Food: {getattr(kingdom, 'food', 0):,}\n\n"
        "Apne buildings manage karo:\n"
    )

    # Count completed upgrades for display
    total_level = sum(getattr(b, 'level', 1) for b in buildings)

    text += f"📊 Total Building Levels: {total_level}\n"

    if not buildings:
        text += "\n❌ No buildings yet!"
        keyboard = back_dashboard_keyboard()
    else:
        keyboard = building_menu_keyboard(buildings)

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)


# Alias for backward compatibility
show_building_list = show_building_menu


# ═══════════════════════════════════════════
# BUILDING DETAIL
# ═══════════════════════════════════════════

async def show_building_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Show details and actions for a specific building"""
    query = update.callback_query

    with get_db() as db:
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()

        if not building:
            await query.answer("❌ Building not found!", show_alert=True)
            return

        config = BUILDING_CONFIG.get(building_type, {})
        level = getattr(building, 'level', 1)
        is_upgrading = getattr(building, 'is_upgrading', False)

        # Calculate upgrade cost and time
        cost = EconomyService.calculate_upgrade_cost(building_type, level)
        time_minutes = EconomyService.calculate_upgrade_time(building_type, level)

        text = (
            f"{config.get('emoji', '🏗')} **{config.get('name', building_type.title())}**\n"
            "━━━━━━━━━━━━━━\n"
            f"📊 Level: {level}\n"
            f"📖 {config.get('description', '')}\n"
        )

        if is_upgrading:
            remaining = format_time_remaining(getattr(building, 'upgrade_completes', None))
            text += f"\n⏳ Upgrading... {remaining}"
        else:
            text += (
                f"\n\n"
                f"⬆️ **Upgrade Cost:**\n"
                f"💰 {cost['gold']:,} Gold\n"
                f"🍖 {cost['food']:,} Food\n"
                f"⏱ Time: {format_duration(time_minutes)}\n"
            )

        # Show current production if applicable
        if building_type == "gold_mine":
            rate = getattr(config, 'GOLD_MINE_BASE_RATE', 100) * level
            text += f"\n📈 Production: {rate} Gold/hour"
        elif building_type == "farm":
            rate = getattr(config, 'FARM_BASE_RATE', 50) * level
            text += f"\n📈 Production: {rate} Food/hour"
        elif building_type == "barracks":
            rate = getattr(config, 'BARRACKS_TRAIN_RATE', 10) * level
            text += f"\n📈 Training: {rate} soldiers/hour"
        elif building_type == "wall":
            from bot.config import config as app_config
            reduction = getattr(app_config, 'WALL_DEFENSE_REDUCTION_PER_LEVEL', 0.03) * level * 100
            text += f"\n🛡 Defense: -{reduction:.0f}% damage"

    keyboard = building_action_keyboard(building_type, level, is_upgrading)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ═══════════════════════════════════════════
# UPGRADE BUILDING
# ═══════════════════════════════════════════

async def upgrade_building(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Start building upgrade"""
    query = update.callback_query

    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()

        if not kingdom or not building:
            await query.answer("❌ Error!", show_alert=True)
            return

        if getattr(building, 'is_upgrading', False):
            await query.answer("⏳ Already upgrading!", show_alert=True)
            return

        from bot.config import config as app_config
        if getattr(building, 'level', 1) >= getattr(app_config, 'BUILDING_MAX_LEVEL', 25):
            await query.answer("❌ Max level reached!", show_alert=True)
            return

        # Check town hall requirement
        town_hall = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == "town_hall"
        ).first()
        town_hall_level = getattr(town_hall, 'level', 1) if town_hall else 1

        if building_type != "town_hall" and getattr(building, 'level', 1) >= town_hall_level:
            await query.answer(f"❌ Town Hall Lv.{getattr(building, 'level', 1) + 1} required!", show_alert=True)
            return

        # Check cost
        cost = EconomyService.calculate_upgrade_cost(building_type, getattr(building, 'level', 1))

        if getattr(kingdom, 'gold', 0) < cost['gold']:
            await query.answer("❌ Not enough Gold!", show_alert=True)
            return

        if getattr(kingdom, 'food', 0) < cost['food']:
            await query.answer("❌ Not enough Food!", show_alert=True)
            return

        # Deduct resources
        kingdom.gold -= cost['gold']
        kingdom.food -= cost['food']

        # Start upgrade
        time_minutes = EconomyService.calculate_upgrade_time(building_type, getattr(building, 'level', 1))
        building.is_upgrading = True
        building.upgrade_started = datetime.utcnow()
        building.upgrade_completes = datetime.utcnow() + timedelta(minutes=time_minutes)

        db.commit()

    config = BUILDING_CONFIG.get(building_type, {})
    text = (
        f"⬆️ **UPGRADE STARTED!**\n"
        "━━━━━━━━━━━━━━\n"
        f"{config.get('emoji', '🏗')} {config.get('name', building_type.title())}\n"
        f"Level {getattr(building, 'level', 1)} → {getattr(building, 'level', 1) + 1}\n"
        f"\n"
        f"⏳ Time: {format_duration(time_minutes)}\n"
        f"💰 Gold: -{cost['gold']:,}\n"
        f"🍖 Food: -{cost['food']:,}\n"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard(), parse_mode="Markdown")


# ═══════════════════════════════════════════
# COLLECT BUILDING
# ═══════════════════════════════════════════

async def collect_building(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Collect resources from a building"""
    query = update.callback_query

    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()

        if not kingdom or not building:
            await query.answer("❌ Error!", show_alert=True)
            return

        config = BUILDING_CONFIG.get(building_type, {})
        level = getattr(building, 'level', 1)

        # Calculate collection based on building type
        if building_type == "gold_mine":
            from bot.config import config as app_config
            rate = getattr(app_config, 'GOLD_MINE_BASE_RATE', 100)
            amount = rate * level
            kingdom.gold += amount
            db.commit()

            text = (
                f"⛏ **{config.get('name', 'Gold Mine')}**\n"
                "━━━━━━━━━━━━━━\n"
                f"💰 +{amount:,} Gold collected!\n"
                f"📊 Level: {level}\n"
                f"📈 Rate: {rate * level} Gold/hour"
            )

        elif building_type == "farm":
            from bot.config import config as app_config
            rate = getattr(app_config, 'FARM_BASE_RATE', 50)
            amount = rate * level
            kingdom.food += amount
            db.commit()

            text = (
                f"🌾 **{config.get('name', 'Farm')}**\n"
                "━━━━━━━━━━━━━━\n"
                f"🍖 +{amount:,} Food collected!\n"
                f"📊 Level: {level}\n"
                f"📈 Rate: {rate * level} Food/hour"
            )

        elif building_type == "barracks":
            from bot.config import config as app_config
            rate = getattr(app_config, 'BARRACKS_TRAIN_RATE', 10)
            amount = rate * level

            # Add soldiers
            from bot.models import Army
            army = db.query(Army).filter(Army.kingdom_id == user_id).first()
            if army:
                army.infantry += amount
                db.commit()

            text = (
                f"🏹 **{config.get('name', 'Barracks')}**\n"
                "━━━━━━━━━━━━━━\n"
                f"⚔️ +{amount} Infantry trained!\n"
                f"📊 Level: {level}\n"
                f"📈 Rate: {rate * level} soldiers/hour"
            )

        else:
            text = (
                f"{config.get('emoji', '🏗')} **{config.get('name', building_type.title())}**\n"
                "━━━━━━━━━━━━━━\n"
                "📖 This building produces no collectable resources.\n"
                f"📊 Level: {level}"
            )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard(), parse_mode="Markdown")


# ═══════════════════════════════════════════
# BUILDING INFO
# ═══════════════════════════════════════════

async def show_building_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Show detailed building information"""
    query = update.callback_query

    config = BUILDING_CONFIG.get(building_type, {})

    text = (
        f"{config.get('emoji', '🏗')} **{config.get('name', building_type.title())} INFO**\n"
        "━━━━━━━━━━━━━━\n"
        f"📖 {config.get('description', 'No description')}\n"
        "\n"
    )

    # Show upgrade costs for next 5 levels
    with get_db() as db:
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()
        current_level = getattr(building, 'level', 1) if building else 1

    text += "**Upgrade Costs:**\n"
    for lvl in range(current_level, min(current_level + 5, 25)):
        cost = EconomyService.calculate_upgrade_cost(building_type, lvl)
        time_min = EconomyService.calculate_upgrade_time(building_type, lvl)
        text += f"Lv.{lvl+1}: 💰{cost['gold']:,} 🍖{cost['food']:,} ⏱{format_duration(time_min)}\n"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"building_select:{building_type}")]
    ]), parse_mode="Markdown")
