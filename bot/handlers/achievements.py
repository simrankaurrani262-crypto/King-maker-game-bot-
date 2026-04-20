"""
Achievements Handler - Achievement and reward system
NEW FEATURE: Complete achievements to earn titles and rewards.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, Achievement, UserAchievement
from bot.services.game_data import GameData
from bot.utils.keyboards import achievements_keyboard, back_dashboard_keyboard


# Default achievements
DEFAULT_ACHIEVEMENTS = [
    {"key": "first_attack", "name": "First Blood", "description": "Win your first battle", "requirement": 1, "reward_title": "Warrior", "reward_gold": 500, "reward_xp": 100},
    {"key": "wins_10", "name": "Veteran Fighter", "description": "Win 10 battles", "requirement": 10, "reward_title": "Veteran", "reward_gold": 2000, "reward_xp": 300},
    {"key": "wins_50", "name": "Warlord", "description": "Win 50 battles", "requirement": 50, "reward_title": "Warlord", "reward_gold": 10000, "reward_xp": 1000},
    {"key": "gold_10k", "name": "Wealthy King", "description": "Earn 10,000 gold total", "requirement": 10000, "reward_title": "Wealthy", "reward_gold": 0, "reward_xp": 200},
    {"key": "gold_100k", "name": "Millionaire", "description": "Earn 100,000 gold total", "requirement": 100000, "reward_title": "Millionaire", "reward_gold": 0, "reward_xp": 500},
    {"key": "buildings_10", "name": "Builder", "description": "Upgrade buildings 10 times", "requirement": 10, "reward_title": "Builder", "reward_gold": 1000, "reward_xp": 150},
    {"key": "spy_5", "name": "Master Spy", "description": "Complete 5 successful spy missions", "requirement": 5, "reward_title": "Spymaster", "reward_gold": 1500, "reward_xp": 200},
    {"key": "level_5", "name": "Rising Star", "description": "Reach level 5", "requirement": 5, "reward_title": "Rising Star", "reward_gold": 2000, "reward_xp": 300},
    {"key": "level_10", "name": "Legendary King", "description": "Reach level 10", "requirement": 10, "reward_title": "Legendary", "reward_gold": 10000, "reward_xp": 1000},
    {"key": "train_100", "name": "Commander", "description": "Train 100 soldiers", "requirement": 100, "reward_title": "Commander", "reward_gold": 1500, "reward_xp": 250},
]


async def show_achievements_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show achievements menu"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query and not new_message:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    # Initialize achievements if needed
    _init_achievements(user_id)

    # Get user achievements
    with get_db() as db:
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()

    total = len(DEFAULT_ACHIEVEMENTS)
    completed = sum(1 for ua in user_achievements if ua.completed)

    text = (
        "🏅 **ACHIEVEMENTS**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"📊 Progress: {completed}/{total}\n"
        f"🏆 Completion: {int(completed/total*100)}%\n\n"
        "Complete achievements to earn\n"
        "titles and rewards!"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=achievements_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=achievements_keyboard())


async def handle_achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle achievements callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "achievements_view":
        await view_achievements(update, context, user_id)

    elif data == "achievements_claim":
        await claim_achievement_rewards(update, context, user_id)


async def view_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """View all achievements with progress"""
    query = update.callback_query

    _init_achievements(user_id)

    with get_db() as db:
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()

    text = (
        "🏅 **ACHIEVEMENT LIST**\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for ua in user_achievements:
        ach = ua.achievement
        status = "✅" if ua.completed else "⏳"
        progress = f"({ua.progress}/{ach.requirement_value})"
        title_reward = f" 🏷 {ach.title_reward}" if ach.title_reward else ""

        text += f"{status} **{ach.name}**{title_reward}\n"
        text += f"   {ach.description} {progress}\n"
        if ach.reward_gold > 0:
            text += f"   💰 {ach.reward_gold:,} Gold"
        if ach.reward_xp > 0:
            text += f" ⭐ {ach.reward_xp} XP"
        text += "\n\n"

    await query.edit_message_text(text, reply_markup=achievements_keyboard())


async def claim_achievement_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Claim all completed achievement rewards"""
    query = update.callback_query

    with get_db() as db:
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.completed == True,
            UserAchievement.claimed == False
        ).all()

        if not user_achievements:
            await query.answer("❌ No rewards to claim!")
            return

        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        total_gold = 0
        total_xp = 0
        titles = []

        for ua in user_achievements:
            ach = ua.achievement
            if kingdom:
                kingdom.gold += ach.reward_gold
                kingdom.xp += ach.reward_xp
            total_gold += ach.reward_gold
            total_xp += ach.reward_xp
            if ach.title_reward:
                titles.append(ach.title_reward)
                if kingdom:
                    kingdom.current_title = ach.title_reward
            ua.claimed = True

        db.commit()

    text = (
        "🎁 **REWARDS CLAIMED!**\n"
        "━━━━━━━━━━━━━━\n"
    )
    if total_gold > 0:
        text += f"💰 +{total_gold:,} Gold\n"
    if total_xp > 0:
        text += f"⭐ +{total_xp} XP\n"
    for t in titles:
        text += f"🏷 New Title: {t}\n"

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


def _init_achievements(user_id: int):
    """Initialize achievements for a user"""
    with get_db() as db:
        # Create default achievements if not exists
        for ach_data in DEFAULT_ACHIEVEMENTS:
            existing = db.query(Achievement).filter(Achievement.achievement_key == ach_data["key"]).first()
            if not existing:
                ach = Achievement(
                    achievement_key=ach_data["key"],
                    name=ach_data["name"],
                    description=ach_data["description"],
                    requirement_value=ach_data["requirement"],
                    reward_title=ach_data["reward_title"],
                    reward_gold=ach_data["reward_gold"],
                    reward_xp=ach_data["reward_xp"],
                )
                db.add(ach)
                db.commit()
                db.refresh(ach)
            else:
                ach = existing

            # Create user achievement if not exists
            ua = db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == ach.id
            ).first()

            if not ua:
                ua = UserAchievement(user_id=user_id, achievement_id=ach.id, progress=0, completed=False, claimed=False)
                db.add(ua)

        db.commit()


def check_achievement_progress(user_id: int, key: str, value: int):
    """Check and update achievement progress"""
    with get_db() as db:
        achievement = db.query(Achievement).filter(Achievement.achievement_key == key).first()
        if not achievement:
            return

        ua = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()

        if not ua or ua.completed:
            return

        ua.progress = value
        if ua.progress >= achievement.requirement_value:
            ua.progress = achievement.requirement_value
            ua.completed = True

        db.commit()
