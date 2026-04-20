#!/usr/bin/env python3
"""
Kingdom Conquest - Advanced Telegram Game Bot v2.0
Main entry point with comprehensive error handling, logging,
and command routing.
"""

import os
import sys
import time
import asyncio
import logging
import functools
import traceback
from typing import Callable, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from bot.config import config
from bot.models import init_db, get_db, Kingdom, Army
from bot.tasks.scheduler import setup_scheduler
from bot.utils.animations import LoadingAnimation, BattleAnimator
from bot.utils.graphics import StatsChartGenerator

# ─── Logging Setup ───
logger = logging.getLogger(__name__)

# ─── Rate Limiting ───
class RateLimiter:
    """Simple in-memory rate limiter per user"""
    def __init__(self, calls_per_minute: int = 30, burst_size: int = 10):
        self.calls_per_minute = calls_per_minute
        self.burst_size = burst_size
        self.user_calls: dict[int, list[float]] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        calls = self.user_calls.get(user_id, [])
        
        # Remove calls older than 60 seconds
        calls = [c for c in calls if now - c < 60]
        
        if len(calls) >= self.calls_per_minute:
            self.user_calls[user_id] = calls
            return False
        
        calls.append(now)
        self.user_calls[user_id] = calls
        return True

rate_limiter = RateLimiter(
    calls_per_minute=config.RATE_LIMIT_PER_MINUTE,
    burst_size=config.RATE_LIMIT_BURST
)


# ─── Error Handling Decorator ───
def handle_errors(func: Callable) -> Callable:
    """Decorator to catch and log all errors in handlers"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            logger.error(f"Error in {func.__name__} for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
            error_message = (
                "⚠️ **System Error**\n"
                "━━━━━━━━━━━━━━\n"
                "Kuch galat ho gaya! Team fix kar rahi hai.\n"
                "Please try again later."
            )
            
            try:
                if update.callback_query:
                    await update.callback_query.answer("❌ Error occurred!", show_alert=True)
                    await update.callback_query.edit_message_text(
                        error_message,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")]
                        ])
                    )
                elif update.message:
                    await update.message.reply_text(error_message)
            except Exception:
                pass
    
    return wrapper


def rate_limited(func: Callable) -> Callable:
    """Decorator to apply rate limiting"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not rate_limiter.is_allowed(user_id):
            message = (
                "⏳ **Rate Limited!**\n"
                "━━━━━━━━━━━━━━\n"
                "Bahut tez requests bhej rahe ho!\n"
                "Thoda slow karo please."
            )
            
            if update.callback_query:
                await update.callback_query.answer("⏳ Slow down!", show_alert=True)
            elif update.message:
                await update.message.reply_text(message)
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


# ─── Lazy Imports to avoid circular imports ───
def _import_handler(module_name: str):
    """Lazy import handler modules"""
    try:
        module = __import__(f"bot.handlers.{module_name}", fromlist=[module_name])
        return module
    except ImportError as e:
        logger.error(f"Failed to import bot.handlers.{module_name}: {e}")
        return None


# ─── Command Handlers ───
@handle_errors
@rate_limited
async def handler_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - entry point"""
    start_module = _import_handler("start")
    if start_module:
        await start_module.handler_start(update, context)
    else:
        await update.message.reply_text("❌ Start module not available")


@handle_errors
@rate_limited
async def handler_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """📖 **KINGDOM CONQUEST - HELP GUIDE**
━━━━━━━━━━━━━━

**🎮 Core Commands:**
`/start` — Begin game / Dashboard
`/dashboard` — Main HUD
`/attack` — Quick attack menu
`/build` — Building management
`/army` — Army overview
`/map` — Show world map
`/alliance` — Alliance hub
`/quests` — Quest board
`/hero` — Hero management
`/spy` — Send spy mission
`/raid` — Quick raid
`/leaderboard` — Rankings
`/settings` — Preferences
`/stats` — Kingdom statistics
`/help` — This guide

**📊 Statistics & Charts:**
`/stats` — View kingdom growth charts
`/stats resources` — Resource history graph
`/stats battles` — Battle performance chart
`/stats army` — Army composition pie chart

**👑 Admin Commands:**
`/admin stats` — Bot statistics
`/admin broadcast <msg>` — Send global message
`/admin warn @user <reason>` — Warn user
`/admin ban @user <days> <reason>` — Ban user
`/admin give @user <resource> <amount>` — Give resources
`/admin maintenance <on/off>` — Toggle maintenance
`/admin reload` — Reload config

**💡 Pro Tips:**
🎯 Pehle buildings upgrade karo
🎯 Food maintain karo warna army bhaagegi
🎯 Alliance join karo for protection
🎯 Spy bhejo attack se pehle
🎯 Daily quests complete karo
🎯 World events ka fayda uthao

Good luck, King! 👑"""
    
    await update.message.reply_text(help_text)


@handle_errors
@rate_limited
async def handler_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command"""
    dashboard_module = _import_handler("dashboard")
    if dashboard_module:
        await dashboard_module.render_dashboard(update, context, update.effective_user.id, new_message=True)
    else:
        await update.message.reply_text("❌ Dashboard module not available")


@handle_errors
@rate_limited
async def handler_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /attack command"""
    attack_module = _import_handler("attack")
    if attack_module and hasattr(attack_module, 'show_attack_menu'):
        await attack_module.show_attack_menu(update, context, update.effective_user.id)
    else:
        await update.message.reply_text(
            "⚔️ **ATTACK MODE**\n━━━━━━━━━━━━━━\nAttack module loading...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Dashboard", callback_data="back_dashboard")]
            ])
        )


@handle_errors
@rate_limited
async def handler_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /build command"""
    build_module = _import_handler("build")
    if build_module and hasattr(build_module, 'show_building_menu'):
        await build_module.show_building_menu(update, context, update.effective_user.id)
    else:
        from bot.services.game_data import GameData
        from bot.utils.keyboards import building_menu_keyboard
        
        buildings = GameData.get_buildings(update.effective_user.id)
        if buildings:
            text = "🏗 **BUILDING MENU**\n━━━━━━━━━━━━━━\n\n"
            for b in buildings:
                status = "⬆️ Upgrading" if getattr(b, 'is_upgrading', False) else f"Lv.{b.level}"
                emoji = getattr(b, 'emoji', '🏗')
                name = getattr(b, 'display_name', b.building_type)
                text += f"{emoji} {name} — {status}\n"
            text += "\n━━━━━━━━━━━━━━\nSelect a building:"
            await update.message.reply_text(text, reply_markup=building_menu_keyboard(buildings))
        else:
            await update.message.reply_text("❌ No buildings found! Use /start first.")


@handle_errors
@rate_limited
async def handler_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /map command"""
    map_module = _import_handler("map_system")
    if map_module and hasattr(map_module, 'render_full_map_direct'):
        await map_module.render_full_map_direct(update, context, update.effective_user.id)
    else:
        await update.message.reply_text(
            "🗺 **WORLD MAP**\n━━━━━━━━━━━━━━\nMap system loading...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Dashboard", callback_data="back_dashboard")]
            ])
        )


@handle_errors
@rate_limited
async def handler_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alliance command"""
    alliance_module = _import_handler("alliance")
    if alliance_module and hasattr(alliance_module, 'show_alliance_hub'):
        await alliance_module.show_alliance_hub(update, context, update.effective_user.id)
    else:
        await update.message.reply_text(
            "🤝 **ALLIANCE HUB**\n━━━━━━━━━━━━━━\nAlliance system loading...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Dashboard", callback_data="back_dashboard")]
            ])
        )


@handle_errors
@rate_limited
async def handler_army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /army command"""
    from bot.services.game_data import GameData
    from bot.utils.keyboards import army_menu_keyboard
    
    user_id = update.effective_user.id
    kingdom = GameData.get_kingdom_with_relations(user_id)
    
    if not kingdom:
        await update.message.reply_text("❌ Kingdom not found! Use /start to begin.")
        return
    
    army = getattr(kingdom, 'army', None)
    infantry = getattr(army, 'infantry', 0) if army else 0
    archers = getattr(army, 'archers', 0) if army else 0
    cavalry = getattr(army, 'cavalry', 0) if army else 0
    total = infantry + archers + cavalry
    
    from bot.services.economy import EconomyService
    food_consumption = EconomyService.calculate_food_consumption(army) if army else 0
    
    text = f"""⚔️ **ARMY MANAGEMENT**
━━━━━━━━━━━━━━

🗡 Infantry: {infantry:,}
🏹 Archers: {archers:,}
🐎 Cavalry: {cavalry:,}
━━━━━━━━━━━━━━
👥 Total: {total:,}
⚠️ Food Consumption: {food_consumption}/hr

Select unit to train:"""
    
    await update.message.reply_text(text, reply_markup=army_menu_keyboard())


@handle_errors
@rate_limited
async def handler_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quests command"""
    quests_module = _import_handler("quests")
    if quests_module and hasattr(quests_module, 'show_quests_menu'):
        await quests_module.show_quests_menu(update, context, update.effective_user.id)
    else:
        await update.message.reply_text(
            "🎯 **QUESTS**\n━━━━━━━━━━━━━━\nQuest system loading...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Dashboard", callback_data="back_dashboard")]
            ])
        )


@handle_errors
@rate_limited
async def handler_hero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hero command"""
    from bot.services.game_data import GameData
    from bot.utils.keyboards import heroes_keyboard
    
    user_id = update.effective_user.id
    heroes = GameData.get_heroes(user_id)
    
    text = "🧙 **HERO ROSTER**\n━━━━━━━━━━━━━━\n\n"
    for h in heroes:
        status = "✅" if getattr(h, 'unlocked', False) else "🔒"
        name = getattr(h, 'display_name', h.hero_type)
        level = getattr(h, 'level', 0)
        desc = getattr(h, 'skill_description', '')
        text += f"{status} {name} — Lv.{level}\n"
        if desc:
            text += f"   {desc}\n"
        text += "\n"
    
    await update.message.reply_text(text, reply_markup=heroes_keyboard(heroes))


@handle_errors
@rate_limited
async def handler_spy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /spy command"""
    spy_module = _import_handler("spy")
    if spy_module and hasattr(spy_module, 'show_spy_menu'):
        await spy_module.show_spy_menu(update, context, update.effective_user.id)
    else:
        from bot.utils.keyboards import spy_menu_keyboard
        
        text = (
            "🕵️ **SPY MENU**\n"
            "━━━━━━━━━━━━━━\n"
            f"💰 Cost: {config.SPY_COST_GOLD:,} Gold\n"
            "🕵️ Dusre kingdoms par spy bhejo!"
        )
        await update.message.reply_text(text, reply_markup=spy_menu_keyboard())


@handle_errors
@rate_limited
async def handler_raid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /raid command"""
    from bot.services.game_data import GameData
    from bot.utils.keyboards import raid_menu_keyboard
    
    user_id = update.effective_user.id
    kingdom = GameData.get_kingdom_with_relations(user_id)
    
    if not kingdom:
        await update.message.reply_text("❌ Kingdom not found! Use /start to begin.")
        return
    
    energy = getattr(kingdom, 'energy', 0)
    max_energy = getattr(kingdom, 'max_energy', config.MAX_ENERGY)
    
    text = (
        "🏃 **QUICK RAID**\n"
        "━━━━━━━━━━━━━━\n"
        f"⚡ Energy: {energy}/{max_energy}\n"
        "Quick raid mein 15% resources steal!"
    )
    await update.message.reply_text(text, reply_markup=raid_menu_keyboard())


@handle_errors
@rate_limited
async def handler_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    leaderboard_module = _import_handler("leaderboard")
    if leaderboard_module and hasattr(leaderboard_module, 'show_leaderboard'):
        await leaderboard_module.show_leaderboard(update, context, update.effective_user.id)
    else:
        from bot.services.game_data import GameData
        from bot.services.economy import EconomyService
        from bot.utils.formatters import format_number
        from bot.utils.keyboards import leaderboard_keyboard
        
        ranked = GameData.get_leaderboard(limit=10)
        
        text = "🏆 **LEADERBOARD**\n━━━━━━━━━━━━━━\n\n"
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        
        for i, (kingdom, power) in enumerate(ranked, 1):
            medal = medals.get(i, f"#{i}")
            name = getattr(kingdom, 'name', 'Unknown')
            flag = getattr(kingdom, 'flag', '')
            level = getattr(kingdom, 'level', 1)
            text += f"{medal} {name} {flag}\n"
            text += f"   ⚡ {format_number(power)} Power | Lv.{level}\n\n"
        
        await update.message.reply_text(text, reply_markup=leaderboard_keyboard())


@handle_errors
@rate_limited
async def handler_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    from bot.utils.keyboards import settings_keyboard
    
    text = "⚙️ **SETTINGS**\nApni preferences customize karo!"
    await update.message.reply_text(text, reply_markup=settings_keyboard())


@handle_errors
@rate_limited
async def handler_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - NEW: Shows kingdom statistics with charts"""
    stats_module = _import_handler("stats")
    if stats_module and hasattr(stats_module, 'show_stats_menu'):
        await stats_module.show_stats_menu(update, context, update.effective_user.id)
    else:
        from bot.services.game_data import GameData
        from bot.services.economy import EconomyService
        
        user_id = update.effective_user.id
        kingdom = GameData.get_kingdom_with_relations(user_id)
        
        if not kingdom:
            await update.message.reply_text("❌ Kingdom not found! Use /start to begin.")
            return
        
        # Generate stats text
        defense_power = EconomyService.calculate_defense_rating(kingdom)
        total_power = EconomyService.calculate_kingdom_power(kingdom)
        
        army = getattr(kingdom, 'army', None)
        infantry = getattr(army, 'infantry', 0) if army else 0
        archers = getattr(army, 'archers', 0) if army else 0
        cavalry = getattr(army, 'cavalry', 0) if army else 0
        total_army = infantry + archers + cavalry
        
        battles_won = getattr(kingdom, 'battles_won', 0)
        battles_lost = getattr(kingdom, 'battles_lost', 0)
        total_battles = battles_won + battles_lost
        win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0
        
        text = f"""📊 **KINGDOM STATISTICS**
━━━━━━━━━━━━━━

👑 {getattr(kingdom, 'name', 'Unknown')} {getattr(kingdom, 'flag', '')}
🏆 Level: {getattr(kingdom, 'level', 1)}
⚡ Total Power: {total_power:,}
🛡 Defense Rating: {defense_power:,}

⚔️ **Army Composition:**
🗡 Infantry: {infantry} ({infantry/total_army*100:.1f}% if total_army else 0)
🏹 Archers: {archers} ({archers/total_army*100:.1f}% if total_army else 0)
🐎 Cavalry: {cavalry} ({cavalry/total_army*100:.1f}% if total_army else 0)

📈 **Battle Record:**
✅ Wins: {battles_won}
❌ Losses: {battles_lost}
📊 Win Rate: {win_rate:.1f}%

💰 Gold Earned: {getattr(kingdom, 'total_gold_earned', 0):,}
🏗 Buildings Upgraded: {getattr(kingdom, 'buildings_upgraded', 0)}
🕵️ Spy Missions: {getattr(kingdom, 'spy_missions', 0)}
"""
        
        # Try to generate chart
        try:
            chart_gen = StatsChartGenerator()
            chart_path = chart_gen.create_kingdom_summary(kingdom)
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📊 Resources Chart", callback_data="stats_resources")],
                            [InlineKeyboardButton("⚔️ Battle Stats", callback_data="stats_battles")],
                            [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")]
                        ])
                    )
                return
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")]
            ])
        )


@handle_errors
@rate_limited
async def handler_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    admin_module = _import_handler("admin")
    if admin_module and hasattr(admin_module, 'handler_admin'):
        await admin_module.handler_admin(update, context)
    else:
        user_id = update.effective_user.id
        if user_id != config.ADMIN_TELEGRAM_ID:
            await update.message.reply_text("⛔ Admin access only!")
            return
        await update.message.reply_text("👑 Admin panel loaded.")


# ─── Callback Router ───
@handle_errors
async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all callback queries to appropriate handlers with safety"""
    query = update.callback_query
    data = query.data
    
    # Rate limit callbacks
    user_id = query.from_user.id
    if not rate_limiter.is_allowed(user_id):
        await query.answer("⏳ Slow down!", show_alert=True)
        return
    
    # Route based on callback prefix
    router_map = {
        # Start handlers
        ("start_game", "how_to_play"): "start",
        
        # Dashboard handlers
        ("back_dashboard", "menu_", "tutorial_", "decision:"): "dashboard",
        
        # Building handlers
        ("building_", "menu_build"): "build",
        
        # Attack handlers
        ("attack_", "battle_", "revenge_", "raid_"): "attack",
        
        # Map handlers
        ("map_", "menu_map"): "map_system",
        
        # Alliance handlers
        ("alliance_", "menu_alliance"): "alliance",
        
        # Quest handlers
        ("quests_", "menu_quests"): "quests",
        
        # Hero handlers
        ("hero_", "skill_", "menu_heroes"): "heroes",
        
        # Spy handlers
        ("spy_", "menu_spy"): "spy",
        
        # Game handlers
        ("game_", "dice_", "spin_", "quiz_", "market_", "survival_"): "games",
        
        # Leaderboard handlers
        ("lb_", "menu_leaderboard"): "leaderboard",
        
        # Settings handlers
        ("settings_", "toggle_", "menu_settings"): "settings",
        
        # Stats handlers (NEW)
        ("stats_", "chart_"): "stats",
        
        # Admin handlers
        ("admin_",): "admin",
        
        # Training handlers
        ("train_",): None,  # Handled inline
        
        # Bounty handlers
        ("bounty_",): None,  # Handled inline
    }
    
    # Find matching handler
    handler_name = None
    for prefixes, module in router_map.items():
        if any(data.startswith(p) or data == p for p in prefixes):
            handler_name = module
            break
    
    if handler_name:
        handler_module = _import_handler(handler_name)
        if handler_module:
            # Try to find appropriate handler function
            handler_funcs = [
                f"handle_{handler_name}_callback",
                f"handler_{handler_name}_callback",
                f"handle_{handler_name}",
            ]
            
            for func_name in handler_funcs:
                if hasattr(handler_module, func_name):
                    await getattr(handler_module, func_name)(update, context)
                    return
    
    # Handle training callbacks inline
    if data.startswith("train_"):
        await handle_train_callback(update, context)
        return
    
    # Handle title setting inline
    if data.startswith("set_title:"):
        await handle_set_title(update, context)
        return
    
    # Unknown callback
    logger.warning(f"Unknown callback data: {data} from user {user_id}")
    await query.answer("❓ Unknown action", show_alert=True)


# ─── Message Handler ───
@handle_errors
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input during multi-step flows"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Route to start handler for wizard flows
    start_module = _import_handler("start")
    if start_module and hasattr(start_module, 'handle_text_input'):
        await start_module.handle_text_input(update, context)
    else:
        # Default: show dashboard if kingdom exists
        from bot.services.game_data import GameData
        kingdom = GameData.get_kingdom(user_id)
        if kingdom:
            dashboard_module = _import_handler("dashboard")
            if dashboard_module and hasattr(dashboard_module, 'render_dashboard'):
                await dashboard_module.render_dashboard(update, context, user_id, new_message=True)


# ─── Inline Handlers ───
@handle_errors
async def handle_train_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle army training callbacks with full validation"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    unit_type = data.replace("train_", "")
    
    from bot.services.game_data import GameData
    from bot.services.economy import EconomyService
    
    # Training costs
    costs = {
        "infantry": {"gold": 50, "food": 20, "amount": 5},
        "archers": {"gold": 80, "food": 30, "amount": 5},
        "cavalry": {"gold": 150, "food": 50, "amount": 5},
    }
    
    cost = costs.get(unit_type)
    if not cost:
        await query.answer("❌ Invalid unit type!")
        return
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        army = db.query(Army).filter(Army.kingdom_id == user_id).first()
        
        if not kingdom or not army:
            await query.answer("❌ Kingdom not found!")
            return
        
        # Resource checks
        if kingdom.gold < cost["gold"]:
            await query.answer(f"❌ {cost['gold']:,} Gold chahiye!")
            return
        
        if kingdom.food < cost["food"]:
            await query.answer(f"❌ {cost['food']:,} Food chahiye!")
            return
        
        # Unlock checks
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
        
        # Deduct resources
        kingdom.gold -= cost["gold"]
        kingdom.food -= cost["food"]
        
        # Add units
        if unit_type == "infantry":
            army.infantry += cost["amount"]
        elif unit_type == "archers":
            army.archers += cost["amount"]
        elif unit_type == "cavalry":
            army.cavalry += cost["amount"]
        
        kingdom.soldiers_trained = getattr(kingdom, 'soldiers_trained', 0) + cost["amount"]
        db.commit()
        
        # Refresh army data
        infantry = army.infantry
        archers = army.archers
        cavalry = army.cavalry
        food_consumption = EconomyService.calculate_food_consumption(army)
    
    unit_emojis = {"infantry": "🗡", "archers": "🏹", "cavalry": "🐎"}
    await query.answer(f"{unit_emojis.get(unit_type, '⚔️')} +{cost['amount']} trained!")
    
    # Show updated army
    from bot.utils.keyboards import army_menu_keyboard
    
    text = f"""⚔️ **ARMY MANAGEMENT**
━━━━━━━━━━━━━━

🗡 Infantry: {infantry:,}
🏹 Archers: {archers:,}
🐎 Cavalry: {cavalry:,}
━━━━━━━━━━━━━━
⚠️ Food Consumption: {food_consumption}/hr

Select unit to train:"""
    
    await query.edit_message_text(text, reply_markup=army_menu_keyboard())


@handle_errors
async def handle_set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle title selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    title = query.data.replace("set_title:", "")
    
    with get_db() as db:
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


# ─── Main Entry Point ───
def main():
    """Main entry point with full initialization"""
    logger.info("=" * 50)
    logger.info("Kingdom Conquest Bot v2.0 Starting...")
    logger.info("=" * 50)
    
    # Validate configuration
    validation_errors = config.validate()
    if validation_errors:
        logger.error("Configuration errors:")
        for key, error in validation_errors.items():
            logger.error(f"  {key}: {error}")
        sys.exit(1)
    
    logger.info("✅ Configuration validated")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)
    
    # Check token
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
        logger.error("Set it via: export TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)
    
    # Build application
    try:
        application = Application.builder().token(token).build()
        logger.info("✅ Application built")
    except Exception as e:
        logger.error(f"❌ Failed to build application: {e}")
        sys.exit(1)
    
    # Setup scheduled tasks
    try:
        setup_scheduler(application)
        logger.info("✅ Scheduler initialized")
    except Exception as e:
        logger.error(f"⚠️ Scheduler initialization failed: {e}")
        logger.info("Continuing without scheduler...")
    
    # ─── Register Command Handlers ───
    commands = [
        ("start", handler_start),
        ("dashboard", handler_dashboard),
        ("attack", handler_attack),
        ("build", handler_build),
        ("army", handler_army),
        ("map", handler_map),
        ("alliance", handler_alliance),
        ("quests", handler_quests),
        ("hero", handler_hero),
        ("spy", handler_spy),
        ("raid", handler_raid),
        ("leaderboard", handler_leaderboard),
        ("settings", handler_settings),
        ("stats", handler_stats),
        ("help", handler_help),
        ("admin", handler_admin),
    ]
    
    for command, handler in commands:
        application.add_handler(CommandHandler(command, handler))
        logger.info(f"  ✅ /{command} registered")
    
    # Callback query handler (single dispatcher for all callbacks)
    application.add_handler(CallbackQueryHandler(route_callback))
    logger.info("  ✅ Callback router registered")
    
    # Message handler (for text input during flows)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    logger.info("  ✅ Message handler registered")
    
    logger.info("=" * 50)
    logger.info("🤖 Bot is running! Press Ctrl+C to stop.")
    logger.info("=" * 50)
    
    # Run the bot
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
