"""
Dashboard Handler - Main HUD with real-time stats
Fixed version with error handling and visual improvements.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.formatters import format_number, get_defense_rating_label, format_time_remaining, calculate_xp_needed
from bot.utils.keyboards import dashboard_keyboard
from bot.utils.animations import DashboardAnimator

logger = logging.getLogger(__name__)


# ─── Main Dashboard Renderer ───

async def render_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message=False):
    """Render the main dashboard HUD with error handling"""
    try:
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            # Kingdom not found - user needs to start
            text = (
                "❌ **Kingdom not found!**\n"
                "━━━━━━━━━━━━━━\n"
                "Aapka kingdom exist nahi karta.\n\n"
                "🎮 Game shuru karne ke liye /start type karo!"
            )
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode="Markdown")
            elif update.message:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        # Calculate dashboard values
        energy = min(getattr(kingdom, 'energy', 0), getattr(kingdom, 'max_energy', 10))
        max_energy = getattr(kingdom, 'max_energy', 10)
        energy_display = f"{energy}/{max_energy}"
        if energy >= max_energy:
            energy_display += " ✅"
        elif energy <= 2:
            energy_display += " ⚠️"
        
        # Defense rating
        defense_power = EconomyService.calculate_defense_rating(kingdom)
        defense_label = get_defense_rating_label(defense_power)
        
        # Wall level
        wall_level = getattr(kingdom, 'wall_level', 1)
        
        # Army breakdown
        army = getattr(kingdom, 'army', None)
        infantry = getattr(army, 'infantry', 0) if army else 0
        archers = getattr(army, 'archers', 0) if army else 0
        cavalry = getattr(army, 'cavalry', 0) if army else 0
        total_army = infantry + archers + cavalry
        
        # XP for next level
        xp_needed = calculate_xp_needed(kingdom.level)
        current_xp = getattr(kingdom, 'xp', 0)
        xp_display = f"{current_xp:,} / {xp_needed:,}"
        xp_percent = min(100, int((current_xp / xp_needed) * 100)) if xp_needed > 0 else 0
        
        # Create XP bar
        xp_bar = _create_progress_bar(xp_percent, 10)
        
        # Shield status
        shield_display = _get_shield_display(kingdom)
        
        # Online status
        last_active = getattr(kingdom, 'last_active', datetime.utcnow())
        is_online = (datetime.utcnow() - last_active).total_seconds() < 300
        status = "🟢 Online" if is_online else "⚫ Offline"
        
        # Title display
        current_title = getattr(kingdom, 'current_title', None)
        title_display = f" [{current_title}]" if current_title else ""
        
        # Trait info
        from bot.utils.constants import KINGDOM_TRAITS
        trait_key = getattr(kingdom, 'trait', 'balanced')
        trait_info = KINGDOM_TRAITS.get(trait_key, KINGDOM_TRAITS['balanced'])
        
        # Power calculation
        total_power = EconomyService.calculate_kingdom_power(kingdom)
        
        dashboard_text = f"""👑 **{getattr(kingdom, 'name', 'Unknown')}**{title_display} {getattr(kingdom, 'flag', '')}
━━━━━━━━━━━━━━
🏆 Level: {getattr(kingdom, 'level', 1)} | ⭐ XP: {xp_display}
{xp_bar} {xp_percent}%

💰 Gold: {getattr(kingdom, 'gold', 0):,} | 🍖 Food: {getattr(kingdom, 'food', 0):,}
💎 Gems: {getattr(kingdom, 'gems', 0):,}
⚡ Energy: {energy_display}

⚔️ **Army:** {total_army:,}
   🗡 {infantry:,}  🏹 {archers:,}  🐎 {cavalry:,}
🛡 Defense: {defense_label} | Wall Lv.{wall_level}
⚡ Power: {total_power:,}

📍 Location: ({getattr(kingdom, 'map_x', 0)}, {getattr(kingdom, 'map_y', 0)})
🧬 Trait: {trait_info['name']}
{status} | 🛡 {shield_display}
━━━━━━━━━━━━━━"""
        
        keyboard = dashboard_keyboard()
        
        # Send or edit message
        if new_message:
            await context.bot.send_message(
                chat_id=user_id,
                text=dashboard_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        elif update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=dashboard_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except Exception as edit_error:
                # Message can't be edited (different content), send new
                logger.debug(f"Could not edit message: {edit_error}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=dashboard_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        elif update.message:
            await update.message.reply_text(
                dashboard_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error rendering dashboard for user {user_id}: {e}")
        error_text = (
            "⚠️ **Dashboard Error**\n"
            "━━━━━━━━━━━━━━\n"
            "Dashboard load nahi ho raha.\n"
            "Please try /dashboard again."
        )
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text, parse_mode="Markdown")
            elif update.message:
                await update.message.reply_text(error_text, parse_mode="Markdown")
        except Exception:
            pass


async def handler_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command"""
    await render_dashboard(update, context, update.effective_user.id, new_message=True)


# Alias for router compatibility
async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dashboard command entry point"""
    await handler_dashboard(update, context)


async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show dashboard wrapper for callback router"""
    await render_dashboard(update, context, user_id)


# ─── Dashboard Callback Router ───

async def handle_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dashboard button clicks with lazy imports to avoid circular dependencies"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    try:
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
        
        elif data.startswith("stats_"):
            from bot.handlers.stats import handle_stats_callback
            await handle_stats_callback(update, context)
        
        else:
            logger.warning(f"Unknown dashboard callback: {data}")
            await query.answer("❓ Unknown action", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in dashboard callback '{data}': {e}")
        await query.answer("❌ Error occurred!", show_alert=True)


# ─── Helper Functions ───

def _create_progress_bar(percent: int, length: int = 10) -> str:
    """Create a text-based progress bar"""
    filled = int(length * percent / 100)
    empty = length - filled
    return "█" * filled + "░" * empty


def _get_shield_display(kingdom) -> str:
    """Get formatted shield status"""
    shield_expires = getattr(kingdom, 'shield_expires', None)
    if shield_expires and datetime.utcnow() < shield_expires:
        remaining = shield_expires - datetime.utcnow()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"🛡 {hours}h {minutes}m"
        return f"🛡 {minutes}m"
    return "No Shield 🚫"
