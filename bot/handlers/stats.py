"""
Stats Handler - Kingdom Statistics with Charts & Graphs
NEW FEATURE: Advanced analytics and visual data representation
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.formatters import format_number
from bot.utils.graphics import StatsChartGenerator, ImageEffects
from bot.utils.animations import ProgressBar

logger = logging.getLogger(__name__)


# ─── Main Stats Menu ───

async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show main statistics menu"""
    try:
        query = update.callback_query
        if query:
            await query.answer()
        
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            text = (
                "❌ **Kingdom not found!**\n"
                "━━━━━━━━━━━━━━\n"
                "Aapka kingdom exist nahi karta.\n"
                "/start se game shuru karo!"
            )
            if query:
                await query.edit_message_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        # Generate quick stats
        total_power = EconomyService.calculate_kingdom_power(kingdom)
        defense = EconomyService.calculate_defense_rating(kingdom)
        
        army = getattr(kingdom, 'army', None)
        infantry = getattr(army, 'infantry', 0) if army else 0
        archers = getattr(army, 'archers', 0) if army else 0
        cavalry = getattr(army, 'cavalry', 0) if army else 0
        total_army = infantry + archers + cavalry
        
        battles_won = getattr(kingdom, 'battles_won', 0)
        battles_lost = getattr(kingdom, 'battles_lost', 0)
        total_battles = battles_won + battles_lost
        win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0
        
        # Create XP progress bar
        from bot.utils.formatters import calculate_xp_needed
        xp_needed = calculate_xp_needed(kingdom.level)
        current_xp = getattr(kingdom, 'xp', 0)
        xp_percent = min(100, int((current_xp / xp_needed) * 100)) if xp_needed > 0 else 0
        xp_bar = ProgressBar.create(xp_percent, 15)
        
        text = f"""📊 **KINGDOM STATISTICS**
━━━━━━━━━━━━━━

👑 **{getattr(kingdom, 'name', 'Unknown')}** {getattr(kingdom, 'flag', '')}
🏆 Level: {getattr(kingdom, 'level', 1)}
{xp_bar}

⚡ **Total Power:** {format_number(total_power)}
🛡 **Defense Rating:** {format_number(defense)}

⚔️ **Army Composition:**
🗡 Infantry: {infantry:,} ({infantry/total_army*100:.1f}%)
🏹 Archers: {archers:,} ({archers/total_army*100:.1f}%)
🐎 Cavalry: {cavalry:,} ({cavalry/total_army*100:.1f}%)

📈 **Battle Record:**
✅ Wins: {battles_won}
❌ Losses: {battles_lost}
📊 Win Rate: {win_rate:.1f}%

💰 Gold Earned: {getattr(kingdom, 'total_gold_earned', 0):,}
🏗 Buildings: {len(getattr(kingdom, 'buildings', []))}
🕵️ Spy Missions: {getattr(kingdom, 'spy_missions', 0)}
━━━━━━━━━━━━━━

📊 Select chart type below:"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Full Summary", callback_data="stats_summary")],
            [InlineKeyboardButton("⚔️ Army Chart", callback_data="stats_army"),
             InlineKeyboardButton("📈 Battles", callback_data="stats_battles")],
            [InlineKeyboardButton("🏰 Buildings", callback_data="stats_buildings"),
             InlineKeyboardButton("💰 Resources", callback_data="stats_resources")],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")],
        ])
        
        if query:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error showing stats menu: {e}")
        await _send_error_message(update, "Stats menu load nahi ho raha!")


# ─── Stats Callback Handler ───

async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats-related callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    try:
        if data == "stats_summary":
            await _show_full_summary(query, user_id)
        elif data == "stats_army":
            await _show_army_chart(query, user_id)
        elif data == "stats_battles":
            await _show_battle_stats(query, user_id)
        elif data == "stats_buildings":
            await _show_building_stats(query, user_id)
        elif data == "stats_resources":
            await _show_resource_stats(query, user_id)
        elif data == "stats_menu":
            await show_stats_menu(update, context, user_id)
        else:
            await query.answer("Unknown stats action", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in stats callback '{data}': {e}")
        await query.answer("❌ Error loading stats!", show_alert=True)


# ─── Detailed Stat Views ───

async def _show_full_summary(query, user_id: int):
    """Show full kingdom summary with chart"""
    try:
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            await query.edit_message_text("❌ Kingdom not found!")
            return
        
        # Generate chart
        chart_gen = StatsChartGenerator()
        chart_path = chart_gen.create_kingdom_summary(kingdom)
        
        # Build text
        from bot.utils.constants import KINGDOM_TRAITS
        trait_key = getattr(kingdom, 'trait', 'balanced')
        trait_info = KINGDOM_TRAITS.get(trait_key, KINGDOM_TRAITS['balanced'])
        
        text = f"""📊 **FULL KINGDOM REPORT**
━━━━━━━━━━━━━━

👑 {getattr(kingdom, 'name', 'Unknown')} {getattr(kingdom, 'flag', '')}
🧬 Trait: {trait_info['name']}
📍 Position: ({getattr(kingdom, 'map_x', 0)}, {getattr(kingdom, 'map_y', 0)})

📈 Charts generated! 👆"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="stats_menu")],
        ])
        
        if chart_path and os.path.exists(chart_path):
            # Delete old message and send photo
            await query.message.delete()
            await query.message.chat.send_photo(
                photo=open(chart_path, 'rb'),
                caption=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                text + "\n\n⚠️ Chart generation failed (library missing)",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error showing full summary: {e}")
        await query.edit_message_text("❌ Error generating summary!")


async def _show_army_chart(query, user_id: int):
    """Show army composition pie chart"""
    try:
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            await query.edit_message_text("❌ Kingdom not found!")
            return
        
        army = getattr(kingdom, 'army', None)
        infantry = getattr(army, 'infantry', 0) if army else 0
        archers = getattr(army, 'archers', 0) if army else 0
        cavalry = getattr(army, 'cavalry', 0) if army else 0
        total = infantry + archers + cavalry
        
        text = f"""⚔️ **ARMY COMPOSITION**
━━━━━━━━━━━━━━

👥 **Total Units:** {total:,}

🗡 Infantry: {infantry:,} ({infantry/total*100:.1f}%)
🏹 Archers: {archers:,} ({archers/total*100:.1f}%)
🐎 Cavalry: {cavalry:,} ({cavalry/total*100:.1f}%)

{text_bar(infantry/total if total else 0, '🗡')}
{text_bar(archers/total if total else 0, '🏹')}
{text_bar(cavalry/total if total else 0, '🐎')}
━━━━━━━━━━━━━━"""
        
        # Try to generate pie chart
        chart_gen = StatsChartGenerator()
        chart_path = chart_gen.create_army_pie(kingdom)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="stats_menu")],
        ])
        
        if chart_path and os.path.exists(chart_path):
            await query.message.delete()
            await query.message.chat.send_photo(
                photo=open(chart_path, 'rb'),
                caption=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                text, reply_markup=keyboard, parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error showing army chart: {e}")
        await query.edit_message_text("❌ Error loading army stats!")


async def _show_battle_stats(query, user_id: int):
    """Show battle statistics"""
    try:
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            await query.edit_message_text("❌ Kingdom not found!")
            return
        
        battles_won = getattr(kingdom, 'battles_won', 0)
        battles_lost = getattr(kingdom, 'battles_lost', 0)
        total_battles = battles_won + battles_lost
        win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0
        
        # Win rate bar
        win_bar = ProgressBar.create_colored(int(win_rate), 20)
        
        text = f"""📈 **BATTLE STATISTICS**
━━━━━━━━━━━━━━

⚔️ **Total Battles:** {total_battles}

✅ **Wins:** {battles_won}
❌ **Losses:** {battles_lost}

📊 **Win Rate:**
{win_bar}

🏆 **Rank:** {_get_battle_rank(win_rate)}

💰 **Total Gold Looted:** {getattr(kingdom, 'total_gold_looted', 0):,}
━━━━━━━━━━━━━━"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="stats_menu")],
        ])
        
        await query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error showing battle stats: {e}")
        await query.edit_message_text("❌ Error loading battle stats!")


async def _show_building_stats(query, user_id: int):
    """Show building statistics"""
    try:
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            await query.edit_message_text("❌ Kingdom not found!")
            return
        
        buildings = getattr(kingdom, 'buildings', [])
        
        text = "🏰 **BUILDING STATISTICS**\n━━━━━━━━━━━━━━\n\n"
        
        building_emojis = {
            'town_hall': '🏰',
            'gold_mine': '⛏',
            'farm': '🌾',
            'barracks': '🏹',
            'wall': '🛡'
        }
        
        total_level = 0
        for b in buildings:
            btype = getattr(b, 'building_type', 'unknown')
            blevel = getattr(b, 'level', 1)
            total_level += blevel
            
            emoji = building_emojis.get(btype, '🏗')
            name = btype.replace('_', ' ').title()
            
            # Progress bar for each building (max level 25)
            progress = int((blevel / 25) * 100)
            bar = ProgressBar.create(progress, 10)
            
            text += f"{emoji} **{name}**\nLv.{blevel}/25 {bar}\n\n"
        
        avg_level = total_level / len(buildings) if buildings else 0
        text += f"━━━━━━━━━━━━━━\n📊 Average Level: {avg_level:.1f}\n"
        text += f"🏗 Total Buildings: {len(buildings)}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="stats_menu")],
        ])
        
        await query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error showing building stats: {e}")
        await query.edit_message_text("❌ Error loading building stats!")


async def _show_resource_stats(query, user_id: int):
    """Show resource statistics"""
    try:
        kingdom = GameData.get_kingdom_with_relations(user_id)
        if not kingdom:
            await query.edit_message_text("❌ Kingdom not found!")
            return
        
        gold = getattr(kingdom, 'gold', 0)
        food = getattr(kingdom, 'food', 0)
        gems = getattr(kingdom, 'gems', 0)
        total_gold_earned = getattr(kingdom, 'total_gold_earned', 0)
        
        # Production rates
        from bot.services.economy import EconomyService
        from bot.utils.constants import KINGDOM_TRAITS
        
        gold_mine = next((b for b in getattr(kingdom, 'buildings', []) if b.building_type == 'gold_mine'), None)
        farm = next((b for b in getattr(kingdom, 'buildings', []) if b.building_type == 'farm'), None)
        
        trait = KINGDOM_TRAITS.get(getattr(kingdom, 'trait', 'balanced'), {})
        
        gold_rate = EconomyService.calculate_production_rate('gold_mine', gold_mine.level if gold_mine else 1, kingdom.trait) if gold_mine else 0
        food_rate = EconomyService.calculate_production_rate('farm', farm.level if farm else 1, kingdom.trait) if farm else 0
        
        text = f"""💰 **RESOURCE STATISTICS**
━━━━━━━━━━━━━━

📊 **Current Resources:**
💰 Gold: {gold:,}
🍖 Food: {food:,}
💎 Gems: {gems:,}

📈 **Production Rates:**
⛏ Gold Mine: {gold_rate:,}/hr
🌾 Farm: {food_rate:,}/hr

💰 **Total Gold Earned:** {total_gold_earned:,}
🏦 **Net Worth:** {gold + (gems * 1000):,} equivalent
━━━━━━━━━━━━━━"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="stats_menu")],
        ])
        
        await query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error showing resource stats: {e}")
        await query.edit_message_text("❌ Error loading resource stats!")


# ─── Helper Functions ───

def text_bar(ratio: float, emoji: str, length: int = 15) -> str:
    """Create a simple text bar"""
    percent = min(100, max(0, int(ratio * 100)))
    filled = int(length * percent / 100)
    empty = length - filled
    return f"{emoji} `{'█' * filled}{'░' * empty}` {percent}%"


def _get_battle_rank(win_rate: float) -> str:
    """Get battle rank based on win rate"""
    if win_rate >= 80:
        return "👑 Legendary"
    elif win_rate >= 60:
        return "⭐ Master"
    elif win_rate >= 40:
        return "🎖️ Veteran"
    elif win_rate >= 20:
        return "⚔️ Fighter"
    else:
        return "🌱 Novice"


async def _send_error_message(update, message: str):
    """Send error message safely"""
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"❌ **Error**\n━━━━━━━━━━━━━━\n{message}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")]
                ]),
                parse_mode="Markdown"
            )
        elif update.message:
            await update.message.reply_text(f"❌ {message}")
    except Exception:
        pass
