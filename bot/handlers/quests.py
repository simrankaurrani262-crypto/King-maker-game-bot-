"""
Quests Handler - Quest and reward system.
Fixed version with all callbacks implemented.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, UserQuest, Quest
from bot.services.game_data import GameData
from bot.utils.keyboards import quests_keyboard, back_dashboard_keyboard


async def show_quests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show quests menu with active quests"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query and not new_message:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    # Ensure quests exist for user
    _ensure_quests_exist(user_id)

    with get_db() as db:
        user_quests = db.query(UserQuest).filter(
            UserQuest.user_id == user_id
        ).all()

    total = len(user_quests)
    completed = sum(1 for uq in user_quests if getattr(uq, 'completed', False))
    claimable = sum(1 for uq in user_quests
                    if getattr(uq, 'completed', False) and not getattr(uq, 'claimed', False))

    text = (
        "🎯 **QUESTS**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"📊 Total: {total}\n"
        f"✅ Completed: {completed}\n"
        f"🎁 Claimable: {claimable}\n\n"
    )

    if claimable > 0:
        text += f"🎁 **{claimable} rewards ready to claim!**\n"
    else:
        text += "Complete quests to earn rewards!\n"

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=quests_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=quests_keyboard())


async def claim_quest_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Claim all completed quest rewards"""
    query = update.callback_query

    with get_db() as db:
        user_quests = db.query(UserQuest).filter(
            UserQuest.user_id == user_id,
            UserQuest.completed == True,
            UserQuest.claimed == False
        ).all()

        if not user_quests:
            await query.answer("❌ No rewards to claim!", show_alert=True)
            return

        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()

        total_gold = 0
        total_xp = 0
        claimed_count = 0

        for uq in user_quests:
            quest = uq.quest
            if quest:
                reward_gold = getattr(quest, 'reward_gold', 0)
                reward_xp = getattr(quest, 'reward_xp', 0)

                if kingdom:
                    kingdom.gold += reward_gold
                    kingdom.xp += reward_xp
                total_gold += reward_gold
                total_xp += reward_xp
            uq.claimed = True
            claimed_count += 1

        db.commit()

    text = (
        f"🎁 **REWARDS CLAIMED!**\n"
        "━━━━━━━━━━━━━━\n"
        f"✅ {claimed_count} quests claimed!\n"
    )
    if total_gold > 0:
        text += f"💰 +{total_gold:,} Gold\n"
    if total_xp > 0:
        text += f"⭐ +{total_xp} XP\n"

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


# ═══════════════════════════════════════════
# QUEST DATA MANAGEMENT
# ═══════════════════════════════════════════

# Default quest definitions
DEFAULT_QUESTS = [
    {"quest_key": "daily_login", "name": "Daily Login", "description": "Login today", "requirement": 1, "reward_gold": 100, "reward_xp": 10, "quest_type": "daily"},
    {"quest_key": "attack_1", "name": "First Blood", "description": "Win 1 battle", "requirement": 1, "reward_gold": 500, "reward_xp": 50, "quest_type": "daily"},
    {"quest_key": "attack_3", "name": "Warmonger", "description": "Win 3 battles", "requirement": 3, "reward_gold": 1500, "reward_xp": 100, "quest_type": "daily"},
    {"quest_key": "train_10", "name": "Recruiter", "description": "Train 10 soldiers", "requirement": 10, "reward_gold": 300, "reward_xp": 30, "quest_type": "daily"},
    {"quest_key": "collect_gold", "name": "Gold Collector", "description": "Collect from Gold Mine", "requirement": 1, "reward_gold": 200, "reward_xp": 20, "quest_type": "daily"},
    {"quest_key": "upgrade_building", "name": "Builder", "description": "Upgrade any building", "requirement": 1, "reward_gold": 1000, "reward_xp": 100, "quest_type": "daily"},
    {"quest_key": "spy_1", "name": "Spy Master", "description": "Send 1 spy mission", "requirement": 1, "reward_gold": 400, "reward_xp": 40, "quest_type": "daily"},
    {"quest_key": "spin_wheel", "name": "Lucky Spin", "description": "Spin the wheel once", "requirement": 1, "reward_gold": 200, "reward_xp": 20, "quest_type": "daily"},
]


def _ensure_quests_exist(user_id: int):
    """Ensure user has all default quests"""
    with get_db() as db:
        # Create global quests if not exist
        for qd in DEFAULT_QUESTS:
            existing = db.query(Quest).filter(Quest.quest_key == qd["quest_key"]).first()
            if not existing:
                quest = Quest(
                    quest_key=qd["quest_key"],
                    name=qd["name"],
                    description=qd["description"],
                    requirement_value=qd["requirement"],
                    reward_gold=qd["reward_gold"],
                    reward_xp=qd["reward_xp"],
                    quest_type=qd["quest_type"],
                )
                db.add(quest)
                db.commit()
                db.refresh(quest)
            else:
                quest = existing

            # Create user quest if not exists
            uq = db.query(UserQuest).filter(
                UserQuest.user_id == user_id,
                UserQuest.quest_id == quest.id
            ).first()

            if not uq:
                uq = UserQuest(
                    user_id=user_id,
                    quest_id=quest.id,
                    progress=0,
                    completed=False,
                    claimed=False
                )
                db.add(uq)

        db.commit()


def update_quest_progress(user_id: int, quest_key: str, increment: int = 1):
    """Update quest progress for a user"""
    with get_db() as db:
        quest = db.query(Quest).filter(Quest.quest_key == quest_key).first()
        if not quest:
            return

        uq = db.query(UserQuest).filter(
            UserQuest.user_id == user_id,
            UserQuest.quest_id == quest.id
        ).first()

        if not uq:
            return

        if uq.completed and uq.claimed:
            return

        uq.progress += increment

        if uq.progress >= quest.requirement_value:
            uq.progress = quest.requirement_value
            uq.completed = True

        db.commit()
