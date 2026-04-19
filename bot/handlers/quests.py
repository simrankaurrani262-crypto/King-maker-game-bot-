from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, UserQuest, Quest, Kingdom
from bot.services.game_data import GameData
from bot.utils.keyboards import quests_keyboard, back_dashboard_keyboard


async def show_quests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show quests menu"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom(user_id)
    user_quests = GameData.get_user_quests(user_id)
    
    text = "🎯 **QUESTS**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    
    # Daily quests
    text += "📅 **DAILY QUESTS**\n"
    daily_reset = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    reset_in = daily_reset - datetime.utcnow()
    reset_hours = int(reset_in.total_seconds() // 3600)
    reset_mins = int((reset_in.total_seconds() % 3600) // 60)
    text += f"(Reset: {reset_hours}h {reset_mins}m)\n\n"
    
    has_claimable = False
    
    for uq in user_quests:
        quest = uq.quest
        if quest.quest_type != "daily":
            continue
        
        status = "✅" if uq.completed else "⏳"
        progress = f"{uq.progress:,}/{quest.requirement_value:,}"
        if uq.completed:
            progress = "DONE!"
            has_claimable = True
        
        text += f"{status} {quest.name} — {progress}\n"
    
    # Milestone quests
    text += "\n🏆 **MILESTONES**\n"
    for uq in user_quests:
        quest = uq.quest
        if quest.quest_type != "milestone":
            continue
        
        status = "✅" if uq.completed else "🔒" if uq.progress == 0 else "⏳"
        progress = f"{uq.progress:,}/{quest.requirement_value:,}"
        if uq.completed:
            progress = "DONE!"
            has_claimable = True
        
        text += f"{status} {quest.name} — {progress}\n"
    
    text += "\n━━━━━━━━━━━━━━"
    
    await query.edit_message_text(text, reply_markup=quests_keyboard())


async def handle_quest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quest callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_quests":
        await show_quests_menu(update, context, user_id)
    
    elif data == "quests_claim":
        await claim_quest_rewards(update, context, user_id)


async def claim_quest_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Claim all completed quest rewards"""
    query = update.callback_query
    
    with get_db() as db:
        user_quests = db.query(UserQuest).filter(
            UserQuest.kingdom_id == user_id,
            UserQuest.completed == True,
            UserQuest.claimed == False
        ).all()
        
        if not user_quests:
            await query.answer("❌ Koi claim karne ke liye reward nahi hai!")
            await show_quests_menu(update, context, user_id)
            return
        
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        total_gold = 0
        total_food = 0
        total_gems = 0
        total_xp = 0
        
        for uq in user_quests:
            quest = uq.quest
            kingdom.gold += quest.reward_gold
            kingdom.food += quest.reward_food
            kingdom.gems += quest.reward_gems
            kingdom.xp += quest.reward_xp
            uq.claimed = True
            
            total_gold += quest.reward_gold
            total_food += quest.reward_food
            total_gems += quest.reward_gems
            total_xp += quest.reward_xp
            
            # Apply title reward
            if quest.reward_title:
                kingdom.current_title = quest.reward_title
        
        db.commit()
    
    rewards_text = "🎁 **Rewards Claimed!**\n━━━━━━━━━━━━━━\n"
    if total_gold > 0:
        rewards_text += f"💰 +{total_gold:,} Gold\n"
    if total_food > 0:
        rewards_text += f"🍖 +{total_food:,} Food\n"
    if total_gems > 0:
        rewards_text += f"💎 +{total_gems:,} Gems\n"
    if total_xp > 0:
        rewards_text += f"⭐ +{total_xp} XP\n"
    
    await query.edit_message_text(rewards_text, reply_markup=back_dashboard_keyboard())


async def update_quest_progress(user_id: int, quest_key: str, amount: int = 1):
    """Update quest progress (called from various game actions)"""
    with get_db() as db:
        quest = db.query(Quest).filter(Quest.quest_key == quest_key).first()
        if not quest:
            return
        
        user_quest = db.query(UserQuest).filter(
            UserQuest.kingdom_id == user_id,
            UserQuest.quest_id == quest.id
        ).first()
        
        if not user_quest or user_quest.completed:
            return
        
        user_quest.progress += amount
        
        if user_quest.progress >= quest.requirement_value:
            user_quest.progress = quest.requirement_value
            user_quest.completed = True
        
        db.commit()
