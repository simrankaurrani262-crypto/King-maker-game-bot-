#!/usr/bin/env python3
"""
Kingdom Conquest - Telegram Game Bot
Main entry point
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from bot.config import config
from bot.models import init_db
from bot.tasks.scheduler import setup_scheduler
from bot.handlers.start import (
    handler_start, handle_start_callback, handle_text_input
)
from bot.handlers.dashboard import (
    render_dashboard, handler_dashboard, handle_dashboard_callback
)
from bot.handlers.build import handle_build_callback
from bot.handlers.attack import handle_attack_callback
from bot.handlers.map_system import handle_map_callback
from bot.handlers.alliance import handle_alliance_callback
from bot.handlers.quests import handle_quest_callback
from bot.handlers.heroes import handle_heroes_callback
from bot.handlers.spy import handle_spy_callback
from bot.handlers.games import handle_games_callback
from bot.handlers.leaderboard import handle_leaderboard_callback
from bot.handlers.settings import handle_settings_callback
from bot.handlers.admin import handler_admin

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def handler_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """📖 **KINGDOM CONQUEST - HELP**
━━━━━━━━━━━━━━

**Commands:**
/start — Begin game / Dashboard
/dashboard — Main HUD
/attack — Quick attack menu
/build — Building management
/army — Army overview
/map — Show world map
/alliance — Alliance hub
/quests — Quest board
/hero — Hero management
/spy — Send spy mission
/raid — Quick raid
/leaderboard — Rankings
/settings — Preferences
/help — This guide

**Admin Commands:**
/admin stats
/admin broadcast <msg>
/admin warn @user <reason>
/admin ban @user <days> <reason>
/admin give @user <resource> <amount>

**Tips:**
🎯 Pehle buildings upgrade karo
🎯 Food maintain karo
🎯 Alliance join karo
🎯 Spy bhejo attack se pehle

Good luck, King! 👑"""
    
    await update.message.reply_text(help_text)


async def handler_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /attack command"""
    user_id = update.effective_user.id
    from bot.handlers.attack import show_attack_menu
    
    # Create a mock callback query
    await update.message.reply_text("⚔️ **ATTACK MODE**")
    from telegram import CallbackQuery, Message
    
    # Render dashboard with attack menu
    kingdom_data = render_dashboard_text(user_id)
    from bot.utils.keyboards import attack_menu_keyboard
    await update.message.reply_text(kingdom_data, reply_markup=attack_menu_keyboard())


async def handler_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /build command"""
    user_id = update.effective_user.id
    from bot.handlers.build import show_building_menu
    from telegram import CallbackQuery
    
    # Send building menu directly
    from bot.services.game_data import GameData
    from bot.utils.keyboards import building_menu_keyboard
    
    buildings = GameData.get_buildings(user_id)
    text = "🏗 **BUILDING MENU**\n━━━━━━━━━━━━━━\n\n"
    for b in buildings:
        status = "⬆️ Upgrading" if b.is_upgrading else f"Lv.{b.level}"
        text += f"{b.emoji} {b.display_name} — {status}\n"
    text += "\n━━━━━━━━━━━━━━\nSelect a building:"
    
    await update.message.reply_text(text, reply_markup=building_menu_keyboard(buildings))


async def handler_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /map command"""
    from bot.handlers.map_system import render_full_map_direct
    await render_full_map_direct(update, context, update.effective_user.id)


async def handler_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alliance command"""
    user_id = update.effective_user.id
    from bot.handlers.alliance import show_alliance_hub
    from telegram import CallbackQuery
    
    # Send alliance menu directly
    from bot.services.game_data import GameData
    from bot.utils.keyboards import alliance_hub_no_alliance_keyboard, alliance_hub_keyboard
    from bot.models import get_db, AllianceMember
    
    with get_db() as db:
        member = db.query(AllianceMember).filter(AllianceMember.kingdom_id == user_id).first()
    
    if not member:
        text = "🤝 **ALLIANCE HUB**\n\nAap kisi alliance mein nahi ho!\n\n[🏰 Create] or [🔍 Join]"
        await update.message.reply_text(text, reply_markup=alliance_hub_no_alliance_keyboard())
    else:
        alliance = member.alliance
        text = f"🤝 **{alliance.name}**\n👥 {len(alliance.members)}/20\n🏆 Power: {alliance.total_power:,}"
        await update.message.reply_text(text, reply_markup=alliance_hub_keyboard(alliance.id))


async def handler_army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /army command"""
    user_id = update.effective_user.id
    from bot.services.game_data import GameData
    from bot.utils.keyboards import army_menu_keyboard
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom or not kingdom.army:
        await update.message.reply_text("❌ Army not found!")
        return
    
    text = f"""⚔️ **ARMY MANAGEMENT**
━━━━━━━━━━━━━━

🗡 Infantry: {kingdom.army.infantry}
🏹 Archers: {kingdom.army.archers}
🐎 Cavalry: {kingdom.army.cavalry}
━━━━━━━━━━━━━━
⚠️ Food Consumption: {kingdom.army.food_consumption_per_hour}/hr

Select unit to train:"""
    
    await update.message.reply_text(text, reply_markup=army_menu_keyboard())


async def handler_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quests command"""
    user_id = update.effective_user.id
    from bot.handlers.quests import show_quests_menu
    from telegram import CallbackQuery
    
    # Send quest menu directly
    from bot.services.game_data import GameData
    from bot.utils.keyboards import quests_keyboard
    from bot.models import UserQuest
    
    kingdom = GameData.get_kingdom(user_id)
    user_quests = GameData.get_user_quests(user_id)
    
    text = "🎯 **QUESTS**\n━━━━━━━━━━━━━━\n\n"
    text += "📅 **DAILY QUESTS**\n"
    for uq in user_quests:
        quest = uq.quest
        if quest.quest_type == "daily":
            status = "✅" if uq.completed else "⏳"
            progress = f"{uq.progress:,}/{quest.requirement_value:,}" if not uq.completed else "DONE!"
            text += f"{status} {quest.name} — {progress}\n"
    
    text += "\n🏆 **MILESTONES**\n"
    for uq in user_quests:
        quest = uq.quest
        if quest.quest_type == "milestone":
            status = "✅" if uq.completed else "🔒" if uq.progress == 0 else "⏳"
            progress = f"{uq.progress:,}/{quest.requirement_value:,}" if not uq.completed else "DONE!"
            text += f"{status} {quest.name} — {progress}\n"
    
    await update.message.reply_text(text, reply_markup=quests_keyboard())


async def handler_hero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hero command"""
    user_id = update.effective_user.id
    from bot.services.game_data import GameData
    from bot.utils.keyboards import heroes_keyboard
    
    heroes = GameData.get_heroes(user_id)
    text = "🧙 **HERO ROSTER**\n━━━━━━━━━━━━━━\n\n"
    for h in heroes:
        status = "✅" if h.unlocked else "🔒"
        text += f"{status} {h.display_name} — Lv.{h.level}\n"
        text += f"   {h.skill_description}\n\n"
    
    await update.message.reply_text(text, reply_markup=heroes_keyboard(heroes))


async def handler_spy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /spy command"""
    user_id = update.effective_user.id
    from bot.services.game_data import GameData
    from bot.utils.keyboards import spy_menu_keyboard
    
    kingdom = GameData.get_kingdom(user_id)
    text = "🕵️ **SPY MENU**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"💰 Cost: 300 Gold\n"
    text += f"🕵️ Dusre kingdoms par spy bhejo!"
    
    await update.message.reply_text(text, reply_markup=spy_menu_keyboard())


async def handler_raid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /raid command"""
    user_id = update.effective_user.id
    from bot.handlers.attack import show_raid_menu
    from telegram import CallbackQuery
    
    from bot.services.game_data import GameData
    from bot.utils.keyboards import raid_menu_keyboard
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    text = "🏃 **QUICK RAID**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"⚡ Energy: {kingdom.energy}/10\n"
    text += f"Quick raid mein 15% resources steal!"
    
    await update.message.reply_text(text, reply_markup=raid_menu_keyboard())


async def handler_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    user_id = update.effective_user.id
    from bot.handlers.leaderboard import show_leaderboard
    from telegram import CallbackQuery
    
    from bot.services.game_data import GameData
    from bot.services.economy import EconomyService
    from bot.utils.formatters import format_number
    from bot.utils.keyboards import leaderboard_keyboard
    
    ranked = GameData.get_leaderboard(limit=10)
    
    text = "🏆 **LEADERBOARD**\n━━━━━━━━━━━━━━\n\n"
    for i, (kingdom, power) in enumerate(ranked, 1):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medals.get(i, f"#{i}")
        text += f"{medal} {kingdom.name} {kingdom.flag}\n"
        text += f"   ⚡ {format_number(power)} Power | Lv.{kingdom.level}\n\n"
    
    await update.message.reply_text(text, reply_markup=leaderboard_keyboard())


async def handler_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    from bot.utils.keyboards import settings_keyboard
    
    text = "⚙️ **SETTINGS**\nApni preferences customize karo!"
    await update.message.reply_text(text, reply_markup=settings_keyboard())


def render_dashboard_text(user_id):
    """Helper to render dashboard text for command handlers"""
    from bot.services.game_data import GameData
    from bot.services.economy import EconomyService
    from bot.utils.formatters import get_defense_rating_label, calculate_xp_needed
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return "❌ Kingdom not found! Use /start to begin."
    
    defense_power = EconomyService.calculate_defense_rating(kingdom)
    defense_label = get_defense_rating_label(defense_power)
    wall_level = kingdom.wall_level
    
    army = kingdom.army
    infantry = army.infantry if army else 0
    archers = army.archers if army else 0
    cavalry = army.cavalry if army else 0
    total_army = infantry + archers + cavalry
    
    energy_display = f"{kingdom.energy}/{kingdom.max_energy}"
    if kingdom.energy >= kingdom.max_energy:
        energy_display += " ✅ Full"
    
    text = f"""👑 Kingdom: {kingdom.name} {kingdom.flag}
━━━━━━━━━━━━━━
🏆 Level: {kingdom.level}  |  ⭐ XP: {kingdom.xp:,}
💰 Gold: {kingdom.gold:,}  |  🍖 Food: {kingdom.food:,}
⚡ Energy: {energy_display}

⚔️ Army: {total_army}
   🗡 {infantry}  🏹 {archers}  🐎 {cavalry}
🛡 Defense: {defense_label}  |  Wall Lv.{wall_level}

📍 Location: ({kingdom.map_x},{kingdom.map_y})
🛡 Shield: {kingdom.shield_time_remaining if kingdom.has_shield else 'No Shield 🚫'}
━━━━━━━━━━━━━━"""
    
    return text


def main():
    """Main entry point"""
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Check token
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        print("Set it via environment variable: export TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)
    
    # Build application
    application = Application.builder().token(token).build()
    
    # Setup scheduled tasks
    setup_scheduler(application)
    print("✅ Scheduler initialized")
    
    # Command handlers
    application.add_handler(CommandHandler("start", handler_start))
    application.add_handler(CommandHandler("dashboard", handler_dashboard))
    application.add_handler(CommandHandler("attack", handler_attack))
    application.add_handler(CommandHandler("build", handler_build))
    application.add_handler(CommandHandler("army", handler_army))
    application.add_handler(CommandHandler("map", handler_map))
    application.add_handler(CommandHandler("alliance", handler_alliance))
    application.add_handler(CommandHandler("quests", handler_quests))
    application.add_handler(CommandHandler("hero", handler_hero))
    application.add_handler(CommandHandler("spy", handler_spy))
    application.add_handler(CommandHandler("raid", handler_raid))
    application.add_handler(CommandHandler("leaderboard", handler_leaderboard))
    application.add_handler(CommandHandler("settings", handler_settings))
    application.add_handler(CommandHandler("help", handler_help))
    application.add_handler(CommandHandler("admin", handler_admin))
    
    # Callback query handler (single dispatcher for all callbacks)
    application.add_handler(CallbackQueryHandler(route_callback))
    
    # Message handler (for text input during flows)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    print("✅ Bot started! Press Ctrl+C to stop.")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all callback queries to appropriate handlers"""
    query = update.callback_query
    data = query.data
    
    # Route based on callback prefix
    if data in ["start_game", "how_to_play"]:
        await handle_start_callback(update, context)
    
    elif data == "back_dashboard" or data.startswith("menu_") or data.startswith("tutorial_") or data.startswith("decision:"):
        await handle_dashboard_callback(update, context)
    
    elif data.startswith("building_") or data == "menu_build":
        await handle_build_callback(update, context)
    
    elif data.startswith("attack_") or data.startswith("battle_") or data.startswith("revenge_") or data.startswith("raid_"):
        await handle_attack_callback(update, context)
    
    elif data.startswith("map_") or data == "menu_map":
        await handle_map_callback(update, context)
    
    elif data.startswith("alliance_") or data == "menu_alliance":
        await handle_alliance_callback(update, context)
    
    elif data.startswith("quests_") or data == "menu_quests":
        await handle_quest_callback(update, context)
    
    elif data.startswith("hero_") or data.startswith("skill_") or data == "menu_heroes":
        await handle_heroes_callback(update, context)
    
    elif data.startswith("spy_") or data == "menu_spy":
        await handle_spy_callback(update, context)
    
    elif data.startswith("game_") or data.startswith("dice_") or data.startswith("spin_") or data.startswith("quiz_") or data.startswith("market_"):
        await handle_games_callback(update, context)
    
    elif data.startswith("lb_") or data == "menu_leaderboard":
        await handle_leaderboard_callback(update, context)
    
    elif data.startswith("settings_") or data.startswith("toggle_") or data == "menu_settings":
        await handle_settings_callback(update, context)
    
    elif data.startswith("train_"):
        await handle_train_callback(update, context)
    
    elif data.startswith("set_title:"):
        await handle_set_title(update, context)
    
    else:
        await query.answer("❓ Unknown action")


async def handle_train_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle army training callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    unit_type = data.replace("train_", "")
    
    from bot.models import get_db, Kingdom, Army
    from bot.services.game_data import GameData
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        army = db.query(Army).filter(Army.kingdom_id == user_id).first()
        
        if not kingdom or not army:
            return
        
        # Training costs
        costs = {
            "infantry": {"gold": 50, "food": 20, "amount": 5},
            "archers": {"gold": 80, "food": 30, "amount": 5},
            "cavalry": {"gold": 150, "food": 50, "amount": 5},
        }
        
        cost = costs.get(unit_type, costs["infantry"])
        
        if kingdom.gold < cost["gold"]:
            await query.answer(f"❌ {cost['gold']} Gold chahiye!")
            return
        
        if kingdom.food < cost["food"]:
            await query.answer(f"❌ {cost['food']} Food chahiye!")
            return
        
        # Check unlock requirements
        if unit_type == "archers":
            barracks = next((b for b in kingdom.buildings if b.building_type == "barracks"), None)
            if not barracks or barracks.level < 2:
                await query.answer("🔒 Barracks Lv.2 chahiye!")
                return
        
        if unit_type == "cavalry":
            barracks = next((b for b in kingdom.buildings if b.building_type == "barracks"), None)
            if not barracks or barracks.level < 4:
                await query.answer("🔒 Barracks Lv.4 chahiye!")
                return
        
        kingdom.gold -= cost["gold"]
        kingdom.food -= cost["food"]
        
        if unit_type == "infantry":
            army.infantry += cost["amount"]
        elif unit_type == "archers":
            army.archers += cost["amount"]
        elif unit_type == "cavalry":
            army.cavalry += cost["amount"]
        
        kingdom.soldiers_trained += cost["amount"]
        db.commit()
    
    unit_emojis = {"infantry": "🗡", "archers": "🏹", "cavalry": "🐎"}
    await query.answer(f"{unit_emojis.get(unit_type, '⚔️')} +{cost['amount']} trained!")
    
    # Show updated army
    from bot.utils.keyboards import army_menu_keyboard
    
    text = f"""⚔️ **ARMY MANAGEMENT**
━━━━━━━━━━━━━━

🗡 Infantry: {army.infantry}
🏹 Archers: {army.archers}
🐎 Cavalry: {army.cavalry}
━━━━━━━━━━━━━━
⚠️ Food Consumption: {army.food_consumption_per_hour}/hr

Select unit to train:"""
    
    await query.edit_message_text(text, reply_markup=army_menu_keyboard())


async def handle_set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle title selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    title = query.data.replace("set_title:", "")
    
    with get_db() as db:
        from bot.models import Kingdom
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if kingdom:
            kingdom.current_title = None if title == "none" else title
            db.commit()
    
    await query.edit_message_text(
        f"✅ Title updated: {title if title != 'none' else 'None'}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")],
        ])
    )


# Import needed for map handler
from bot.handlers.map_system import render_full_map_direct

if __name__ == "__main__":
    main()
