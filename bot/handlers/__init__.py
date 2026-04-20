"""
Handlers Package - Register all Telegram bot handlers.
Version: 2.1.0 - All handlers fixed and registered.
"""

import logging

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from bot.config import config

logger = logging.getLogger(__name__)


def register_handlers(application: Application):
    """Register all bot handlers in correct order."""
    logger.info("Registering handlers...")

    # ─── Command Handlers ───
    application.add_handler(CommandHandler("start", _cmd_start))
    application.add_handler(CommandHandler("dashboard", _cmd_dashboard))
    application.add_handler(CommandHandler("help", _cmd_help))
    application.add_handler(CommandHandler("admin", _cmd_admin))

    # ─── Message Handler (for kingdom name input, etc.) ───
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        _handle_text_input
    ))

    # ─── Callback Query Router (single entry point for ALL callbacks) ───
    application.add_handler(CallbackQueryHandler(_callback_router))

    # ─── Error Handler ───
    application.add_error_handler(_error_handler)

    logger.info("All handlers registered successfully.")


# ═══════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════

async def _cmd_start(update, context):
    """/start command"""
    from bot.handlers.start import start_command
    await start_command(update, context)


async def _cmd_dashboard(update, context):
    """/dashboard command"""
    from bot.handlers.dashboard import dashboard_command
    await dashboard_command(update, context)


async def _cmd_help(update, context):
    """/help command"""
    from bot.handlers.start import help_command
    await help_command(update, context)


async def _cmd_admin(update, context):
    """/admin command"""
    from bot.handlers.admin import handler_admin
    await handler_admin(update, context)


# ═══════════════════════════════════════════════════════════
# CALLBACK ROUTER - Dispatches ALL callback queries
# ═══════════════════════════════════════════════════════════

async def _callback_router(update, context):
    """Main callback query router - handles ALL inline button clicks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    logger.debug(f"Callback: {data} from user {user_id}")

    try:
        # ─── Maintenance check ───
        if config.MAINTENANCE_MODE and user_id != config.ADMIN_TELEGRAM_ID:
            await query.edit_message_text(
                "🔧 **Maintenance Mode**\n\nBot temporarily under maintenance. Please try again later.",
                parse_mode="Markdown"
            )
            return

        # ═══════════════════════════════════════════
        # START / HOW TO PLAY
        # ═══════════════════════════════════════════
        if data == "start_game":
            from bot.handlers.start import start_game
            await start_game(update, context)
        elif data == "how_to_play":
            from bot.handlers.start import how_to_play
            await how_to_play(update, context)

        # ═══════════════════════════════════════════
        # KINGDOM CREATION
        # ═══════════════════════════════════════════
        elif data.startswith("trait_"):
            trait = data.replace("trait_", "")
            from bot.handlers.start import handle_trait_selection
            await handle_trait_selection(update, context, user_id, trait)
        elif data.startswith("flag_"):
            flag = data.replace("flag_", "")
            from bot.handlers.start import handle_flag_selection
            await handle_flag_selection(update, context, user_id, flag)

        # ═══════════════════════════════════════════
        # DASHBOARD / MAIN MENU
        # ═══════════════════════════════════════════
        elif data == "back_dashboard":
            from bot.handlers.dashboard import show_dashboard
            await show_dashboard(update, context, user_id)
        elif data == "menu_dashboard":
            from bot.handlers.dashboard import show_dashboard
            await show_dashboard(update, context, user_id)

        # ═══════════════════════════════════════════
        # ATTACK MENU
        # ═══════════════════════════════════════════
        elif data == "menu_attack":
            from bot.handlers.attack import show_attack_menu
            await show_attack_menu(update, context, user_id)
        elif data == "attack_find":
            from bot.handlers.attack import find_opponent
            await find_opponent(update, context, user_id)
        elif data == "attack_next":
            from bot.handlers.attack import find_opponent
            await find_opponent(update, context, user_id)
        elif data == "attack_revenge":
            from bot.handlers.attack import show_revenge_menu
            await show_revenge_menu(update, context, user_id)
        elif data == "attack_raid":
            from bot.handlers.attack import show_raid_menu
            await show_raid_menu(update, context, user_id)
        elif data == "raid_find":
            from bot.handlers.attack import find_raid_target
            await find_raid_target(update, context, user_id)
        elif data == "attack_map":
            from bot.handlers.map_system import render_full_map
            await render_full_map(update, context, user_id)
        elif data.startswith("attack_player:"):
            target_id = int(data.split(":")[1])
            from bot.handlers.attack import show_battle_response
            await show_battle_response(update, context, user_id, target_id)
        elif data.startswith("spy_opponent:"):
            target_id = int(data.split(":")[1])
            from bot.handlers.spy import show_spy_menu
            await show_spy_menu(update, context, user_id, target_id)
        elif data.startswith("battle_accept:"):
            request_id = data.split(":")[1]
            from bot.handlers.attack import handle_battle_callback
            await handle_battle_callback(update, context, user_id)
        elif data.startswith("battle_decline:"):
            request_id = data.split(":")[1]
            from bot.handlers.attack import handle_battle_callback
            await handle_battle_callback(update, context, user_id)

        # ═══════════════════════════════════════════
        # BUILDINGS MENU
        # ═══════════════════════════════════════════
        elif data == "menu_build":
            from bot.handlers.build import show_building_menu
            await show_building_menu(update, context, user_id)
        elif data.startswith("building_select:"):
            btype = data.split(":")[1]
            from bot.handlers.build import show_building_detail
            await show_building_detail(update, context, user_id, btype)
        elif data.startswith("building_upgrade:"):
            btype = data.split(":")[1]
            from bot.handlers.build import upgrade_building
            await upgrade_building(update, context, user_id, btype)
        elif data.startswith("building_collect:"):
            btype = data.split(":")[1]
            from bot.handlers.build import collect_building
            await collect_building(update, context, user_id, btype)
        elif data.startswith("building_info:"):
            btype = data.split(":")[1]
            from bot.handlers.build import show_building_info
            await show_building_info(update, context, user_id, btype)

        # ═══════════════════════════════════════════
        # MAP SYSTEM
        # ═══════════════════════════════════════════
        elif data == "menu_map":
            from bot.handlers.map_system import show_map_menu
            await show_map_menu(update, context, user_id)
        elif data == "map_view":
            from bot.handlers.map_system import render_full_map
            await render_full_map(update, context, user_id)
        elif data.startswith("map_tile:"):
            parts = data.split(":")
            x, y = int(parts[1]), int(parts[2])
            from bot.handlers.map_system import show_tile_detail
            await show_tile_detail(update, context, user_id, x, y)
        elif data.startswith("spy_target:"):
            target_id = int(data.split(":")[1])
            from bot.handlers.spy import show_spy_menu
            await show_spy_menu(update, context, user_id, target_id)

        # ═══════════════════════════════════════════
        # ALLIANCE MENU
        # ═══════════════════════════════════════════
        elif data == "menu_alliance":
            from bot.handlers.alliance import show_alliance_hub
            await show_alliance_hub(update, context, user_id)
        elif data == "alliance_create":
            from bot.handlers.alliance import show_alliance_create
            await show_alliance_create(update, context, user_id)
        elif data == "alliance_join":
            from bot.handlers.alliance import show_alliance_list
            await show_alliance_list(update, context, user_id)
        elif data.startswith("alliance_members:"):
            aid = int(data.split(":")[1])
            from bot.handlers.alliance import show_alliance_members
            await show_alliance_members(update, context, user_id, aid)
        elif data.startswith("alliance_donate:"):
            aid = int(data.split(":")[1])
            from bot.handlers.alliance import show_donate_menu
            await show_donate_menu(update, context, user_id, aid)
        elif data.startswith("alliance_leave:"):
            aid = int(data.split(":")[1])
            from bot.handlers.alliance import handle_alliance_leave
            await handle_alliance_leave(update, context, user_id, aid)
        elif data.startswith("join_alliance:"):
            aid = int(data.split(":")[1])
            from bot.handlers.alliance import handle_join_alliance
            await handle_join_alliance(update, context, user_id, aid)

        # ═══════════════════════════════════════════
        # HEROES MENU
        # ═══════════════════════════════════════════
        elif data == "menu_heroes":
            from bot.handlers.heroes import show_heroes_menu
            await show_heroes_menu(update, context, user_id)
        elif data.startswith("hero_select:"):
            htype = data.split(":")[1]
            from bot.handlers.heroes import show_hero_detail
            await show_hero_detail(update, context, user_id, htype)
        elif data.startswith("hero_unlock:"):
            htype = data.split(":")[1]
            from bot.handlers.heroes import unlock_hero
            await unlock_hero(update, context, user_id, htype)
        elif data.startswith("hero_upgrade:"):
            htype = data.split(":")[1]
            from bot.handlers.heroes import upgrade_hero
            await upgrade_hero(update, context, user_id, htype)
        elif data == "skill_attack" or data == "skill_defense" or data == "skill_economy":
            skill_type = data.replace("skill_", "")
            from bot.handlers.heroes import show_skill_tree
            await show_skill_tree(update, context, user_id, skill_type)
        elif data.startswith("skill_unlock:"):
            parts = data.split(":")
            skill_type = parts[1]
            tier = parts[2]
            from bot.handlers.heroes import unlock_skill
            await unlock_skill(update, context, user_id, skill_type, tier)

        # ═══════════════════════════════════════════
        # SPY MENU
        # ═══════════════════════════════════════════
        elif data == "menu_spy":
            from bot.handlers.spy import show_spy_hub
            await show_spy_hub(update, context, user_id)
        elif data == "spy_send":
            from bot.handlers.spy import find_spy_target
            await find_spy_target(update, context, user_id)
        elif data == "spy_history":
            from bot.handlers.spy import show_spy_history
            await show_spy_history(update, context, user_id)

        # ═══════════════════════════════════════════
        # QUESTS MENU
        # ═══════════════════════════════════════════
        elif data == "menu_quests":
            from bot.handlers.quests import show_quests_menu
            await show_quests_menu(update, context, user_id)
        elif data == "quests_claim":
            from bot.handlers.quests import claim_quest_rewards
            await claim_quest_rewards(update, context, user_id)

        # ═══════════════════════════════════════════
        # LEADERBOARD MENU
        # ═══════════════════════════════════════════
        elif data == "menu_leaderboard":
            from bot.handlers.leaderboard import show_leaderboard_menu
            await show_leaderboard_menu(update, context, user_id)
        elif data == "lb_players":
            from bot.handlers.leaderboard import show_player_leaderboard
            await show_player_leaderboard(update, context, user_id)
        elif data == "lb_alliances":
            from bot.handlers.leaderboard import show_alliance_leaderboard
            await show_alliance_leaderboard(update, context, user_id)

        # ═══════════════════════════════════════════
        # MINI-GAMES MENU
        # ═══════════════════════════════════════════
        elif data == "menu_games":
            from bot.handlers.games import show_games_menu
            await show_games_menu(update, context, user_id)
        elif data == "game_dice":
            from bot.handlers.games import show_dice_game
            await show_dice_game(update, context, user_id)
        elif data == "game_spin":
            from bot.handlers.games import show_spin_wheel
            await show_spin_wheel(update, context, user_id)
        elif data == "game_quiz":
            from bot.handlers.games import show_quiz_game
            await show_quiz_game(update, context, user_id)
        elif data == "game_survival":
            from bot.handlers.games import show_survival_menu
            await show_survival_menu(update, context, user_id)
        elif data == "game_market":
            from bot.handlers.games import show_black_market
            await show_black_market(update, context, user_id)

        # ─── Dice game ───
        elif data.startswith("dice_bet:"):
            amount = int(data.split(":")[1])
            from bot.handlers.games import roll_dice
            await roll_dice(update, context, user_id, amount)

        # ─── Spin wheel ───
        elif data == "spin_wheel":
            from bot.handlers.games import spin_wheel
            await spin_wheel(update, context, user_id)

        # ─── Quiz game ───
        elif data.startswith("quiz_answer:"):
            parts = data.split(":")
            q_idx = int(parts[1])
            answer = int(parts[2])
            from bot.handlers.games import handle_quiz_answer
            await handle_quiz_answer(update, context, user_id, q_idx, answer)

        # ─── Survival mode ───
        elif data == "survival_start":
            from bot.handlers.games import start_survival
            await start_survival(update, context, user_id)
        elif data == "survival_next":
            from bot.handlers.games import next_survival_wave
            await next_survival_wave(update, context, user_id)

        # ─── Black market ───
        elif data == "market_buy":
            from bot.handlers.games import show_market_items
            await show_market_items(update, context, user_id)
        elif data.startswith("market_buy:"):
            item_idx = int(data.split(":")[1])
            from bot.handlers.games import buy_market_item
            await buy_market_item(update, context, user_id, item_idx)

        # ─── Decision events ───
        elif data.startswith("decision:"):
            parts = data.split(":")
            event_id = parts[1]
            choice = parts[2]
            from bot.handlers.games import handle_decision_event
            await handle_decision_event(update, context, user_id, event_id, choice)

        # ═══════════════════════════════════════════
        # STATS MENU
        # ═══════════════════════════════════════════
        elif data == "menu_stats":
            from bot.handlers.stats import show_stats_menu
            await show_stats_menu(update, context, user_id)
        elif data == "stats_summary":
            from bot.handlers.stats import show_full_summary
            await show_full_summary(update, context, user_id)
        elif data == "stats_army":
            from bot.handlers.stats import show_army_chart
            await show_army_chart(update, context, user_id)
        elif data == "stats_battles":
            from bot.handlers.stats import show_battle_history
            await show_battle_history(update, context, user_id)
        elif data == "stats_buildings":
            from bot.handlers.stats import show_building_stats
            await show_building_stats(update, context, user_id)
        elif data == "stats_resources":
            from bot.handlers.stats import show_resource_stats
            await show_resource_stats(update, context, user_id)

        # ═══════════════════════════════════════════
        # SETTINGS MENU
        # ═══════════════════════════════════════════
        elif data == "menu_settings":
            from bot.handlers.settings import show_settings_menu
            await show_settings_menu(update, context, user_id)
        elif data == "settings_notif":
            from bot.handlers.settings import show_notification_settings
            await show_notification_settings(update, context, user_id)
        elif data == "settings_title":
            from bot.handlers.settings import show_title_menu
            await show_title_menu(update, context, user_id)
        elif data == "settings_lang":
            from bot.handlers.settings import show_language_menu
            await show_language_menu(update, context, user_id)
        elif data == "settings_help":
            from bot.handlers.settings import show_help_menu
            await show_help_menu(update, context, user_id)
        elif data.startswith("toggle_"):
            toggle_type = data.replace("toggle_", "")
            from bot.handlers.settings import toggle_setting
            await toggle_setting(update, context, user_id, toggle_type)

        # ═══════════════════════════════════════════
        # TRAINING MENU
        # ═══════════════════════════════════════════
        elif data == "menu_training":
            from bot.handlers.training import show_training_menu
            await show_training_menu(update, context, user_id)
        elif data == "train_infantry":
            from bot.handlers.training import show_train_amount
            await show_train_amount(update, context, user_id, "infantry")
        elif data == "train_archers":
            from bot.handlers.training import show_train_amount
            await show_train_amount(update, context, user_id, "archers")
        elif data == "train_cavalry":
            from bot.handlers.training import show_train_amount
            await show_train_amount(update, context, user_id, "cavalry")
        elif data.startswith("train_amount:"):
            parts = data.split(":")
            unit_type = parts[1]
            amount = int(parts[2])
            from bot.handlers.training import execute_training
            await execute_training(update, context, user_id, unit_type, amount)

        # ═══════════════════════════════════════════
        # TRADE MENU
        # ═══════════════════════════════════════════
        elif data == "menu_trade":
            from bot.handlers.trade import show_trade_menu
            await show_trade_menu(update, context, user_id)
        elif data == "trade_gold_food":
            from bot.handlers.trade import show_trade_amount
            await show_trade_amount(update, context, user_id, "gold", "food")
        elif data == "trade_food_gold":
            from bot.handlers.trade import show_trade_amount
            await show_trade_amount(update, context, user_id, "food", "gold")
        elif data == "trade_gems_gold":
            from bot.handlers.trade import show_trade_amount
            await show_trade_amount(update, context, user_id, "gems", "gold")
        elif data.startswith("trade_execute:"):
            parts = data.split(":")
            r_from = parts[1]
            r_to = parts[2]
            amount = int(parts[3])
            from bot.handlers.trade import execute_trade
            await execute_trade(update, context, user_id, r_from, r_to, amount)

        # ═══════════════════════════════════════════
        # BOUNTY MENU
        # ═══════════════════════════════════════════
        elif data == "menu_bounty":
            from bot.handlers.bounty import show_bounty_menu
            await show_bounty_menu(update, context, user_id)
        elif data == "bounty_view":
            from bot.handlers.bounty import show_active_bounties
            await show_active_bounties(update, context, user_id)
        elif data == "bounty_place":
            from bot.handlers.bounty import show_place_bounty
            await show_place_bounty(update, context, user_id)
        elif data == "bounty_my":
            from bot.handlers.bounty import show_my_bounties
            await show_my_bounties(update, context, user_id)

        # ═══════════════════════════════════════════
        # ACHIEVEMENTS MENU
        # ═══════════════════════════════════════════
        elif data == "menu_achievements":
            from bot.handlers.achievements import show_achievements_menu
            await show_achievements_menu(update, context, user_id)
        elif data == "achievements_view":
            from bot.handlers.achievements import view_achievements
            await view_achievements(update, context, user_id)
        elif data == "achievements_claim":
            from bot.handlers.achievements import claim_achievement_rewards
            await claim_achievement_rewards(update, context, user_id)

        # ═══════════════════════════════════════════
        # WORLD EVENTS MENU
        # ═══════════════════════════════════════════
        elif data == "menu_events":
            from bot.handlers.world_events import show_events_menu
            await show_events_menu(update, context, user_id)
        elif data == "events_active":
            from bot.handlers.world_events import show_active_events
            await show_active_events(update, context, user_id)
        elif data == "events_history":
            from bot.handlers.world_events import show_event_history
            await show_event_history(update, context, user_id)

        # ═══════════════════════════════════════════
        # ADMIN CALLBACKS
        # ═══════════════════════════════════════════
        elif data == "admin_stats":
            from bot.handlers.admin import handle_admin_callback
            await handle_admin_callback(update, context)
        elif data == "admin_broadcast":
            from bot.handlers.admin import handle_admin_callback
            await handle_admin_callback(update, context)
        elif data == "admin_maintenance":
            from bot.handlers.admin import handle_admin_callback
            await handle_admin_callback(update, context)

        # ═══════════════════════════════════════════
        # FALLBACK
        # ═══════════════════════════════════════════
        elif data == "noop":
            await query.answer("⏳ Please wait...")
        else:
            logger.warning(f"Unhandled callback: {data}")
            await query.answer("Feature coming soon!", show_alert=True)

    except Exception as e:
        logger.error(f"Error in callback '{data}': {e}", exc_info=True)
        try:
            await query.edit_message_text(
                f"❌ **Error**\n\nSomething went wrong. Please return to the dashboard.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")
                ]]),
                parse_mode="Markdown"
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# TEXT INPUT HANDLER
# ═══════════════════════════════════════════════════════════

async def _handle_text_input(update, context):
    """Handle text messages (kingdom name, alliance name, etc.)"""
    user_id = update.effective_user.id
    text = update.message.text

    # Check for ongoing registration
    from bot.handlers.start import handle_text_message
    await handle_text_message(update, context, user_id, text)


# ═══════════════════════════════════════════════════════════
# ERROR HANDLER
# ═══════════════════════════════════════════════════════════

async def _error_handler(update, context):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try /start to restart."
            )
        except Exception:
            pass


__all__ = ["register_handlers"]
