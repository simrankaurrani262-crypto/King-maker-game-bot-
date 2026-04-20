"""
Main Entry Point - Telegram Bot Setup and Handler Registration
Fixed version with all correct imports and comprehensive handler setup.
"""

import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from bot.config import config

# ─── Logging ───

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─── Command Handlers ───

async def handler_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    from bot.handlers.start import handler_start as start_handler
    await start_handler(update, context)


async def handler_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command"""
    from bot.handlers.dashboard import handler_dashboard as dashboard_handler
    await dashboard_handler(update, context)


async def handler_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /attack command"""
    from bot.handlers.attack import show_attack_menu
    query = None
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    await show_attack_menu(update, context, update.effective_user.id)


async def handler_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /build command"""
    from bot.handlers.build import show_building_menu
    from telegram import InlineKeyboardMarkup
    query = update.callback_query
    if query:
        await query.answer()
    await show_building_menu(update, context, update.effective_user.id)


async def handler_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /map command"""
    from bot.handlers.map_system import render_full_map_direct
    await render_full_map_direct(update, context, update.effective_user.id)


async def handler_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **COMMAND GUIDE**\n"
        "━━━━━━━━━━━━━━\n\n"
        "**Main Commands:**\n"
        "/start — Start the game / Dashboard\n"
        "/dashboard — Open main dashboard\n"
        "/attack — Attack menu\n"
        "/build — Building management\n"
        "/map — World map\n"
        "/stats — Kingdom statistics\n"
        "/train — Training center\n"
        "/trade — Trade resources\n"
        "/bounty — Bounty board\n"
        "/achievements — View achievements\n"
        "/events — World events\n"
        "/heroes — Hero management\n"
        "/spy — Spy missions\n"
        "/quests — Quest board\n"
        "/leaderboard — Rankings\n"
        "/games — Mini-games\n"
        "/settings — Preferences\n"
        "/help — This guide\n\n"
        "**Admin Commands:**\n"
        "/admin <command> — Admin tools\n\n"
        "━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handler_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    from bot.handlers.admin import handler_admin as admin_handler
    await admin_handler(update, context)


async def handler_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /train command"""
    from bot.handlers.training import show_training_menu
    await show_training_menu(update, context, update.effective_user.id, new_message=True)


async def handler_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trade command"""
    from bot.handlers.trade import show_trade_menu
    await show_trade_menu(update, context, update.effective_user.id, new_message=True)


async def handler_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bounty command"""
    from bot.handlers.bounty import show_bounty_menu
    await show_bounty_menu(update, context, update.effective_user.id, new_message=True)


async def handler_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /achievements command"""
    from bot.handlers.achievements import show_achievements_menu
    await show_achievements_menu(update, context, update.effective_user.id, new_message=True)


async def handler_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /events command"""
    from bot.handlers.world_events import show_events_menu
    await show_events_menu(update, context, update.effective_user.id, new_message=True)


async def handler_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    from bot.handlers.stats import show_stats_menu
    await show_stats_menu(update, context, update.effective_user.id)


async def handler_heroes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /heroes command"""
    from bot.handlers.heroes import show_heroes_menu
    query = update.callback_query
    if query:
        await query.answer()
    await show_heroes_menu(update, context, update.effective_user.id)


async def handler_spy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /spy command"""
    from bot.handlers.spy import show_spy_menu
    query = update.callback_query
    if query:
        await query.answer()
    await show_spy_menu(update, context, update.effective_user.id)


async def handler_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quests command"""
    from bot.handlers.quests import show_quests_menu
    query = update.callback_query
    if query:
        await query.answer()
    await show_quests_menu(update, context, update.effective_user.id)


async def handler_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    from bot.handlers.leaderboard import show_leaderboard
    query = update.callback_query
    if query:
        await query.answer()
    await show_leaderboard(update, context, update.effective_user.id)


async def handler_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /games command"""
    from bot.handlers.games import show_games_menu
    query = update.callback_query
    if query:
        await query.answer()
    await show_games_menu(update, context, update.effective_user.id)


async def handler_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    from bot.handlers.settings import show_settings_menu
    query = update.callback_query
    if query:
        await query.answer()
    await show_settings_menu(update, context, update.effective_user.id)


# ─── Callback Router ───

async def route_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central callback query router"""
    query = update.callback_query
    await query.answer()

    data = query.data

    try:
        # Dashboard navigation
        if data == "back_dashboard":
            await handler_dashboard(update, context)

        # Start menu
        elif data in ("start_game", "how_to_play", "cancel_creation"):
            from bot.handlers.start import handle_start_callback
            await handle_start_callback(update, context)

        # Tutorial
        elif data.startswith("tutorial_"):
            from bot.handlers.start import handle_tutorial_callback
            await handle_tutorial_callback(update, context)

        # Dashboard menu items
        elif data == "menu_attack":
            await handler_attack(update, context)
        elif data == "menu_build":
            await handler_build(update, context)
        elif data == "menu_map":
            await handler_map(update, context)
        elif data == "menu_alliance":
            from bot.handlers.alliance import show_alliance_hub
            await show_alliance_hub(update, context, update.effective_user.id)
        elif data == "menu_heroes":
            await handler_heroes(update, context)
        elif data == "menu_spy":
            await handler_spy(update, context)
        elif data == "menu_quests":
            await handler_quests(update, context)
        elif data == "menu_leaderboard":
            await handler_leaderboard(update, context)
        elif data == "menu_games":
            await handler_games(update, context)
        elif data == "menu_settings":
            await handler_settings(update, context)
        elif data == "menu_stats":
            await handler_stats(update, context)

        # Attack callbacks
        elif data.startswith(("attack_", "battle_", "revenge_", "raid_")):
            from bot.handlers.attack import handle_attack_callback
            await handle_attack_callback(update, context)

        # Building callbacks
        elif data.startswith(("building_", "menu_build")):
            from bot.handlers.build import handle_build_callback
            await handle_build_callback(update, context)

        # Map callbacks
        elif data.startswith(("map_", "menu_map")):
            from bot.handlers.map_system import handle_map_callback
            await handle_map_callback(update, context)

        # Alliance callbacks
        elif data.startswith(("alliance_", "menu_alliance")):
            from bot.handlers.alliance import handle_alliance_callback
            await handle_alliance_callback(update, context)

        # Hero callbacks
        elif data.startswith(("hero_", "skill_", "menu_heroes")):
            from bot.handlers.heroes import handle_heroes_callback
            await handle_heroes_callback(update, context)

        # Spy callbacks
        elif data.startswith(("spy_", "menu_spy")):
            from bot.handlers.spy import handle_spy_callback
            await handle_spy_callback(update, context)

        # Quest callbacks
        elif data.startswith(("quests_", "menu_quests")):
            from bot.handlers.quests import handle_quest_callback
            await handle_quest_callback(update, context)

        # Leaderboard callbacks
        elif data.startswith(("lb_", "menu_leaderboard")):
            from bot.handlers.leaderboard import handle_leaderboard_callback
            await handle_leaderboard_callback(update, context)

        # Games callbacks
        elif data.startswith(("game_", "dice_", "spin_", "quiz_", "market_", "decision:")):
            from bot.handlers.games import handle_games_callback
            await handle_games_callback(update, context)

        # Settings callbacks
        elif data.startswith(("settings_", "toggle_", "menu_settings")):
            from bot.handlers.settings import handle_settings_callback
            await handle_settings_callback(update, context)

        # Stats callbacks
        elif data.startswith(("stats_", "menu_stats")):
            from bot.handlers.stats import handle_stats_callback
            await handle_stats_callback(update, context)

        # Training callbacks
        elif data.startswith(("train_", "menu_training")):
            from bot.handlers.training import handle_training_callback
            await handle_training_callback(update, context)

        # Trade callbacks
        elif data.startswith(("trade_", "menu_trade")):
            from bot.handlers.trade import handle_trade_callback
            await handle_trade_callback(update, context)

        # Bounty callbacks
        elif data.startswith(("bounty_", "menu_bounty")):
            from bot.handlers.bounty import handle_bounty_callback
            await handle_bounty_callback(update, context)

        # Achievements callbacks
        elif data.startswith(("achievements_", "menu_achievements")):
            from bot.handlers.achievements import handle_achievements_callback
            await handle_achievements_callback(update, context)

        # World events callbacks
        elif data.startswith(("events_", "menu_events")):
            from bot.handlers.world_events import handle_events_callback
            await handle_events_callback(update, context)

        # Admin callbacks
        elif data.startswith("admin_"):
            from bot.handlers.admin import handle_admin_callback
            await handle_admin_callback(update, context)

        else:
            logger.warning(f"Unknown callback: {data}")
            await query.answer("Unknown action", show_alert=True)

    except Exception as e:
        logger.error(f"Callback error ({data}): {e}")
        try:
            await query.edit_message_text(
                f"❌ Error processing request.\nPlease try again with /start",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")]
                ])
            )
        except Exception:
            pass


# ─── Text Message Handler ───

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from users"""
    from bot.handlers.start import handle_text_input
    await handle_text_input(update, context)


# ─── Error Handler ───

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    logger.error(f"Update {update} caused error: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred.\nPlease try /start to continue."
            )
        elif update and update.callback_query:
            await update.callback_query.answer("❌ Error occurred!", show_alert=True)
    except Exception:
        pass


# ─── Main Setup ───

def main():
    """Initialize and start the bot"""
    logger.info("🚀 Starting Kingdom Conquest Bot v2.0...")

    # Validate config
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        logger.error("❌ TELEGRAM_BOT_TOKEN not configured! Check your .env file.")
        sys.exit(1)

    # Initialize database
    try:
        from bot.models import init_db
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

    # Build application
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # ─── Register Command Handlers ───
    application.add_handler(CommandHandler("start", handler_start))
    application.add_handler(CommandHandler("dashboard", handler_dashboard))
    application.add_handler(CommandHandler("attack", handler_attack))
    application.add_handler(CommandHandler("build", handler_build))
    application.add_handler(CommandHandler("map", handler_map))
    application.add_handler(CommandHandler("help", handler_help))
    application.add_handler(CommandHandler("admin", handler_admin))
    application.add_handler(CommandHandler("train", handler_training))
    application.add_handler(CommandHandler("trade", handler_trade))
    application.add_handler(CommandHandler("bounty", handler_bounty))
    application.add_handler(CommandHandler("achievements", handler_achievements))
    application.add_handler(CommandHandler("events", handler_events))
    application.add_handler(CommandHandler("stats", handler_stats))
    application.add_handler(CommandHandler("heroes", handler_heroes))
    application.add_handler(CommandHandler("spy", handler_spy))
    application.add_handler(CommandHandler("quests", handler_quests))
    application.add_handler(CommandHandler("leaderboard", handler_leaderboard))
    application.add_handler(CommandHandler("games", handler_games))
    application.add_handler(CommandHandler("settings", handler_settings))

    # ─── Register Callback Handler ───
    application.add_handler(CallbackQueryHandler(route_callbacks))

    # ─── Register Text Message Handler ───
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    # ─── Register Error Handler ───
    application.add_error_handler(error_handler)

    # ─── Setup Background Tasks ───
    try:
        from bot.tasks.scheduler import setup_scheduler
        setup_scheduler(application)
        logger.info("✅ Scheduler tasks setup")
    except Exception as e:
        logger.warning(f"⚠️ Scheduler setup failed: {e}")

    logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def on_startup(application: Application):
    """Post-initialization tasks"""
    logger.info("🎉 Kingdom Conquest Bot started successfully!")
    logger.info(f"📊 Admin ID: {config.ADMIN_TELEGRAM_ID}")


if __name__ == "__main__":
    main()
