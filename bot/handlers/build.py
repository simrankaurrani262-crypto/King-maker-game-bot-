"""
King-Maker Bot — Elite Edition
Building / Construction / Resource Management Handlers
"""

import json
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.config import config
from bot.models import get_db, Kingdom, Building
from bot.services.economy import EconomyService


# ── Building configs ─────────────────────────────────────────────
BUILDING_CONFIGS = {
    "town_hall": {"base_cost": 200, "base_time": 300, "emoji": "🏛", "display": "Town Hall"},
    "barracks": {"base_cost": 100, "base_time": 180, "emoji": "⚔️", "display": "Barracks"},
    "farm": {"base_cost": 80, "base_time": 120, "emoji": "🌾", "display": "Farm"},
    "gold_mine": {"base_cost": 120, "base_time": 150, "emoji": "⛏️", "display": "Gold Mine"},
    "wall": {"base_cost": 150, "base_time": 200, "emoji": "🛡", "display": "Wall"},
    "market": {"base_cost": 100, "base_time": 140, "emoji": "🏪", "display": "Market"},
}


def render_bar(value: int, maximum: int, width: int = 12, fill: str = "█", empty: str = "░") -> str:
    """Render a horizontal progress bar."""
    if maximum <= 0:
        return empty * width
    ratio = min(value / maximum, 1.0)
    filled = int(round(ratio * width))
    return fill * filled + empty * (width - filled)


async def view_building_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, building_type: str):
    """Show detailed building info with visual upgrade progress."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type,
        ).first()

        if not building:
            return await query.edit_message_text("❌ Building nahi mili!")

        cfg = BUILDING_CONFIGS.get(building_type, {})
        upgrade_cost = cfg.get("base_cost", 100) * building.level
        upgrade_time = cfg.get("base_time", 120) * building.level

        # Production info
        gold_prod = EconomyService.calculate_gold_production(building.kingdom) if hasattr(building, 'kingdom') else 0
        food_prod = EconomyService.calculate_food_production(building.kingdom) if hasattr(building, 'kingdom') else 0

        # Upgrade progress
        if building.is_upgrading and building.upgrade_completes:
            remaining = (building.upgrade_completes - datetime.utcnow()).total_seconds()
            total = (building.upgrade_completes - building.upgrade_started).total_seconds() if building.upgrade_started else upgrade_time
            if total > 0:
                progress = 1 - (remaining / total)
                bar = render_bar(int(progress * 100), 100, 10)
                status = f"⏳ Upgrading...\n{bar} {int(progress * 100)}%\n{int(max(0, remaining) / 60)} min remaining"
            else:
                status = "⏳ Upgrading..."
        else:
            status = "✅ Ready"

        text = (
            f"{building.emoji} **{building.display_name}** — Level {building.level}\n\n"
            f"📊 Status: {status}\n\n"
            f"⬆️ **Upgrade Cost:**\n"
            f"   💰 {upgrade_cost} Gold\n"
            f"   ⏱ {upgrade_time // 60} min {upgrade_time % 60}s\n\n"
            f"📈 **Production:**\n"
            f"   💰 +{gold_prod}/hr\n"
            f"   🍖 +{food_prod}/hr\n\n"
            f"ℹ️ **Info:**\n"
            f"Har upgrade se production +10% badhti hai!"
        )

        if building.is_upgrading:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ Upgrading...", callback_data="noop")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_build")],
            ])
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬆️ Upgrade", callback_data=f"building_upgrade:{building_type}"),
                 InlineKeyboardButton("📥 Collect", callback_data=f"building_collect:{building_type}")],
                [InlineKeyboardButton("ℹ️ Info", callback_data=f"building_info:{building_type}")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_build")],
            ])

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def upgrade_building(update: Update, context: ContextTypes.DEFAULT_TYPE, building_type: str):
    """Start building upgrade with visual confirmation."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type,
        ).first()

        if not building:
            return await query.edit_message_text("❌ Building nahi mili!")

        if building.is_upgrading:
            return await query.edit_message_text(
                "⏳ Already upgrading!\nWait karo...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"building_select:{building_type}")],
                ]),
            )

        cfg = BUILDING_CONFIGS.get(building_type, {})
        upgrade_cost = cfg.get("base_cost", 100) * building.level

        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom or kingdom.gold < upgrade_cost:
            return await query.edit_message_text(
                f"💰 {upgrade_cost} Gold chahiye!\nAapke paas: {kingdom.gold if kingdom else 0}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"building_select:{building_type}")],
                ]),
            )

        # Deduct gold and start upgrade
        kingdom.gold -= upgrade_cost
        building.is_upgrading = True
        building.upgrade_started = datetime.utcnow()
        building.upgrade_completes = datetime.utcnow() + timedelta(seconds=cfg.get("base_time", 120) * building.level)

        db.commit()

        # Visual progress bar
        await query.edit_message_text(
            f"⬆️ **{building.display_name}** upgrading to Level {building.level + 1}!\n\n"
            f"💰 Gold spent: {upgrade_cost}\n"
            f"⏱ Time: {cfg.get('base_time', 120) * building.level // 60} min\n"
            f"{render_bar(0, 100, 10)} 0%\n\n"
            f"Upgrade complete hone pe notification aa jayegi!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Buildings", callback_data="menu_build")],
            ]),
        )


async def collect_resources(update: Update, context: ContextTypes.DEFAULT_TYPE, building_type: str):
    """Collect resources from building with visual output."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type,
        ).first()

        if not building:
            return await query.edit_message_text("❌ Building nahi mili!")

        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return await query.edit_message_text("❌ Kingdom nahi mila!")

        # Calculate production based on building type and level
        gold_gain = 0
        food_gain = 0

        if building_type == "gold_mine":
            gold_gain = 10 * building.level
        elif building_type == "farm":
            food_gain = 15 * building.level
        elif building_type == "market":
            gold_gain = 5 * building.level
            food_gain = 5 * building.level
        elif building_type == "town_hall":
            gold_gain = 20 * building.level
            food_gain = 10 * building.level
        else:
            gold_gain = 3 * building.level

        # Apply limits
        max_cap = 10000
        actual_gold = min(gold_gain, max_cap - kingdom.gold) if kingdom.gold < max_cap else 0
        actual_food = min(food_gain, max_cap - kingdom.food) if kingdom.food < max_cap else 0

        kingdom.gold += actual_gold
        kingdom.food += actual_food

        db.commit()

        # Visual resource bars
        gold_bar = render_bar(kingdom.gold, max_cap, 10)
        food_bar = render_bar(kingdom.food, max_cap, 10)

        lines = [f"📥 **Resources Collected from {building.display_name}!**\n"]
        if actual_gold > 0:
            lines.append(f"💰 +{actual_gold} Gold")
        if actual_food > 0:
            lines.append(f"🍖 +{actual_food} Food")
        if actual_gold == 0 and actual_food == 0:
            lines.append("📭 Storage full! Upgrade karo!")

        lines.append(f"\n💰 {gold_bar} {kingdom.gold}/{max_cap}")
        lines.append(f"🍖 {food_bar} {kingdom.food}/{max_cap}")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Buildings", callback_data="menu_build")],
            ]),
        )


async def building_info(update: Update, context: ContextTypes.DEFAULT_TYPE, building_type: str):
    """Show detailed building information with upgrade chart."""
    query = update.callback_query

    info_data = {
        "town_hall": {
            "name": "🏛 Town Hall",
            "desc": "Kingdom ka main building. Har level pe naye features unlock hote hain.",
            "benefits": ["Level 2: Alliance unlock", "Level 3: Heroes unlock", "Level 5: Spy agency unlock"],
        },
        "barracks": {
            "name": "⚔️ Barracks",
            "desc": "Army training ka center. Har level pe training speed badhti hai.",
            "benefits": ["+Training speed per level", "+Army capacity at Lv.5", "Elite units at Lv.10"],
        },
        "farm": {
            "name": "🌾 Farm",
            "desc": "Food production. Army ko food chahiye warna bhaag jayegi!",
            "benefits": ["+15 Food/level per collect", "Storage +100 per level", "Auto-collect at Lv.10"],
        },
        "gold_mine": {
            "name": "⛏️ Gold Mine",
            "desc": "Gold production. Sabse important resource hai!",
            "benefits": ["+10 Gold/level per collect", "Storage +100 per level", "Gem mining at Lv.10"],
        },
        "wall": {
            "name": "🛡 Wall",
            "desc": "Kingdom ki defense. Attack se protection deta hai.",
            "benefits": ["+10% Defense/level", "Trap damage at Lv.5", "Moat at Lv.10"],
        },
        "market": {
            "name": "🏪 Market",
            "desc": "Trade center. Resources exchange kar sakte ho.",
            "benefits": ["Resource trading", "Better exchange rates/level", "Black market at Lv.8"],
        },
    }

    info = info_data.get(building_type, {"name": building_type, "desc": "No info", "benefits": []})

    text = (
        f"{info['name']}\n\n"
        f"{info['desc']}\n\n"
        f"📈 **Upgrade Benefits:**\n"
    )
    for benefit in info["benefits"]:
        text += f"  • {benefit}\n"

    text += "\n💡 Tip: Har upgrade se production +10% badhti hai!"

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data=f"building_select:{building_type}")],
        ]),
    )
