from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.formatters import format_number
from bot.utils.keyboards import leaderboard_keyboard, back_dashboard_keyboard


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show leaderboard"""
    query = update.callback_query
    
    ranked = GameData.get_leaderboard(limit=50)
    
    text = "🏆 **LEADERBOARD**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    
    viewer_kingdom = GameData.get_kingdom(user_id)
    viewer_power = EconomyService.calculate_kingdom_power(viewer_kingdom) if viewer_kingdom else 0
    viewer_rank = None
    
    for i, (kingdom, power) in enumerate(ranked[:10], 1):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medals.get(i, f"#{i}")
        
        title = kingdom.current_title or ""
        text += f"{medal} {kingdom.name} {kingdom.flag} {title}\n"
        text += f"   ⚡ {format_number(power)} Power | Lv.{kingdom.level}\n\n"
        
        if kingdom.user_id == user_id:
            viewer_rank = i
    
    if viewer_rank:
        text += f"\n📊 Your Rank: **#{viewer_rank}**\n"
    else:
        text += f"\n📊 Your Power: {format_number(viewer_power)}\n"
    
    text += "━━━━━━━━━━━━━━"
    
    await query.edit_message_text(text, reply_markup=leaderboard_keyboard())


async def handle_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaderboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_leaderboard":
        await show_leaderboard(update, context, user_id)
    
    elif data == "lb_players":
        await show_leaderboard(update, context, user_id)
    
    elif data == "lb_alliances":
        await show_alliance_leaderboard(update, context, user_id)


async def show_alliance_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show alliance leaderboard"""
    query = update.callback_query
    
    from bot.models import get_db, Alliance
    
    with get_db() as db:
        alliances = db.query(Alliance).order_by(Alliance.total_power.desc()).limit(10).all()
    
    text = "🏆 **ALLIANCE LEADERBOARD**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    
    if not alliances:
        text += "❌ Koi alliance abhi tak nahi bana!\n"
    else:
        for i, a in enumerate(alliances, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            medal = medals.get(i, f"#{i}")
            text += f"{medal} {a.name}\n"
            text += f"   ⚡ {format_number(a.total_power)} | 👥 {len(a.members)}/{20}\n\n"
    
    text += "━━━━━━━━━━━━━━"
    
    await query.edit_message_text(text, reply_markup=leaderboard_keyboard())
