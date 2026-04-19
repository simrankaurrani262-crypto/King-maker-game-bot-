from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.formatters import format_number, get_defense_rating_label, format_time_remaining
from bot.utils.keyboards import dashboard_keyboard


async def render_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message=False):
    """Render the main dashboard HUD"""
    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return
    
    # Calculate energy
    energy = min(kingdom.energy, kingdom.max_energy)
    energy_display = f"{energy}/{kingdom.max_energy}"
    if energy >= kingdom.max_energy:
        energy_display += " ✅ Full"
    
    # Calculate defense rating
    defense_power = EconomyService.calculate_defense_rating(kingdom)
    defense_label = get_defense_rating_label(defense_power)
    
    # Get wall level
    wall_level = kingdom.wall_level
    
    # Army breakdown
    army = kingdom.army
    infantry = army.infantry if army else 0
    archers = army.archers if army else 0
    cavalry = army.cavalry if army else 0
    total_army = infantry + archers + cavalry
    
    # XP for next level
    from bot.utils.formatters import calculate_xp_needed
    xp_needed = calculate_xp_needed(kingdom.level)
    current_level_xp = kingdom.xp
    
    # Shield status
    shield_display = kingdom.shield_time_remaining if kingdom.has_shield else "No Shield 🚫"
    
    # Online status
    status = "🟢 Online" if kingdom.is_online else "⚫ Offline"
    
    # Title
    title_display = f" [{kingdom.current_title}]" if kingdom.current_title else ""
    
    dashboard_text = f"""👑 Kingdom: {kingdom.name}{title_display} {kingdom.flag}
━━━━━━━━━━━━━━
🏆 Level: {kingdom.level}  |  ⭐ XP: {current_level_xp:,}
💰 Gold: {kingdom.gold:,}  |  🍖 Food: {kingdom.food:,}
⚡ Energy: {energy_display}

⚔️ Army: {total_army}
   🗡 {infantry}  🏹 {archers}  🐎 {cavalry}
🛡 Defense: {defense_label}  |  Wall Lv.{wall_level}

📍 Location: ({kingdom.map_x},{kingdom.map_y})
🟢 Status: {status}
🛡 Shield: {shield_display}
━━━━━━━━━━━━━━"""
    
    keyboard = dashboard_keyboard()
    
    if new_message:
        await context.bot.send_message(
            chat_id=user_id,
            text=dashboard_text,
            reply_markup=keyboard
        )
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=dashboard_text,
                reply_markup=keyboard
            )
        except Exception:
            # Message can't be edited, send new
            await context.bot.send_message(
                chat_id=user_id,
                text=dashboard_text,
                reply_markup=keyboard
            )
    elif update.message:
        await update.message.reply_text(
            dashboard_text,
            reply_markup=keyboard
        )


async def handler_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command"""
    await render_dashboard(update, context, update.effective_user.id, new_message=True)


async def handle_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dashboard button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "back_dashboard":
        await render_dashboard(update, context, user_id)
    
    elif data == "menu_attack":
        from bot.handlers.attack import show_attack_menu
        await show_attack_menu(update, context, user_id)
    
    elif data == "menu_build":
        from bot.handlers.build import show_building_menu
        await show_building_menu(update, context, user_id)
    
    elif data == "menu_map":
        from bot.handlers.map_system import show_map_menu
        await show_map_menu(update, context, user_id)
    
    elif data == "menu_alliance":
        from bot.handlers.alliance import show_alliance_hub
        await show_alliance_hub(update, context, user_id)
    
    elif data == "menu_heroes":
        from bot.handlers.heroes import show_heroes_menu
        await show_heroes_menu(update, context, user_id)
    
    elif data == "menu_spy":
        from bot.handlers.spy import show_spy_menu
        await show_spy_menu(update, context, user_id)
    
    elif data == "menu_quests":
        from bot.handlers.quests import show_quests_menu
        await show_quests_menu(update, context, user_id)
    
    elif data == "menu_leaderboard":
        from bot.handlers.leaderboard import show_leaderboard
        await show_leaderboard(update, context, user_id)
    
    elif data == "menu_games":
        from bot.handlers.games import show_games_menu
        await show_games_menu(update, context, user_id)
    
    elif data == "menu_settings":
        from bot.handlers.settings import show_settings_menu
        await show_settings_menu(update, context, user_id)
    
    elif data.startswith("tutorial_"):
        from bot.handlers.start import handle_tutorial_callback
        await handle_tutorial_callback(update, context)
    
    elif data.startswith("decision:"):
        from bot.handlers.games import handle_decision
        await handle_decision(update, context)
