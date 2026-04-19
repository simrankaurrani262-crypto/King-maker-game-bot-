from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, Hero, Kingdom
from bot.services.game_data import GameData
from bot.utils.keyboards import heroes_keyboard, hero_action_keyboard, back_dashboard_keyboard
from bot.utils.constants import SKILL_TREE


async def show_heroes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show heroes management menu"""
    query = update.callback_query
    
    heroes = GameData.get_heroes(user_id)
    kingdom = GameData.get_kingdom(user_id)
    
    text = "🧙 **HERO ROSTER**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    
    for h in heroes:
        status = "✅" if h.unlocked else "🔒"
        text += f"{status} {h.display_name} — Lv.{h.level}\n"
        text += f"   {h.skill_description}\n"
        if not h.unlocked:
            text += f"   🔓 Unlock: {h.unlock_requirement}\n"
        text += "\n"
    
    text += f"⭐ Skill Points available: Check skill trees\n"
    text += "━━━━━━━━━━━━━━"
    
    await query.edit_message_text(text, reply_markup=heroes_keyboard(heroes))


async def handle_heroes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle hero callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_heroes":
        await show_heroes_menu(update, context, user_id)
    
    elif data.startswith("hero_select:"):
        hero_type = data.split(":")[1]
        await show_hero_detail(update, context, user_id, hero_type)
    
    elif data.startswith("hero_unlock:"):
        hero_type = data.split(":")[1]
        await unlock_hero(update, context, user_id, hero_type)
    
    elif data.startswith("hero_upgrade:"):
        hero_type = data.split(":")[1]
        await upgrade_hero(update, context, user_id, hero_type)
    
    elif data.startswith("skill_"):
        tree = data.split("_")[1]
        await show_skill_tree(update, context, user_id, tree)


async def show_hero_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, hero_type: str):
    """Show individual hero detail"""
    query = update.callback_query
    
    hero = GameData.get_hero(user_id, hero_type)
    if not hero:
        await query.edit_message_text("❌ Hero not found!", reply_markup=back_dashboard_keyboard())
        return
    
    kingdom = GameData.get_kingdom(user_id)
    
    text = f"{hero.display_name}\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"Level: {hero.level}\n"
    text += f"Status: {'✅ Unlocked' if hero.unlocked else '🔒 Locked'}\n"
    text += f"Skill: {hero.skill_description}\n"
    
    if not hero.unlocked:
        text += f"\n🔓 Unlock: {hero.unlock_requirement}\n"
        if hero.unlock_cost > 0:
            cost_type = "💎 Gems" if hero_type in ["morgana", "shadow"] else "💰 Gold"
            text += f"Cost: {cost_type} {hero.unlock_cost}\n"
    else:
        # Show upgrade cost
        upgrade_cost = 500 * (hero.level + 1)
        text += f"\n⬆️ Level Up: {upgrade_cost:,} Gold\n"
        text += f"Next: {hero.skill_description}\n"
    
    can_upgrade = hero.unlocked and kingdom.gold >= 500 * (hero.level + 1)
    
    keyboard = hero_action_keyboard(hero_type, hero.unlocked, hero.level, can_upgrade)
    await query.edit_message_text(text, reply_markup=keyboard)


async def unlock_hero(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, hero_type: str):
    """Unlock a hero"""
    query = update.callback_query
    
    with get_db() as db:
        hero = db.query(Hero).filter(
            Hero.kingdom_id == user_id,
            Hero.hero_type == hero_type
        ).first()
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        
        if not hero or not kingdom:
            return
        
        if hero.unlocked:
            await query.answer("✅ Pehle se unlocked hai!")
            return
        
        # Check unlock requirements
        cost = hero.unlock_cost
        if hero_type in ["morgana", "shadow"]:
            if kingdom.gems < cost:
                await query.answer(f"❌ {cost} Gems chahiye!")
                return
            kingdom.gems -= cost
        else:
            if kingdom.gold < cost:
                await query.answer(f"❌ {cost} Gold chahiye!")
                return
            kingdom.gold -= cost
        
        hero.unlocked = True
        hero.level = 1
        db.commit()
    
    await query.answer(f"🎉 {hero.display_name} unlocked!")
    await show_hero_detail(update, context, user_id, hero_type)


async def upgrade_hero(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, hero_type: str):
    """Upgrade a hero's level"""
    query = update.callback_query
    
    with get_db() as db:
        hero = db.query(Hero).filter(
            Hero.kingdom_id == user_id,
            Hero.hero_type == hero_type
        ).first()
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        
        if not hero or not kingdom or not hero.unlocked:
            return
        
        cost = 500 * (hero.level + 1)
        if kingdom.gold < cost:
            await query.answer(f"❌ {cost} Gold chahiye!")
            return
        
        kingdom.gold -= cost
        hero.level += 1
        db.commit()
    
    await query.answer(f"⬆️ {hero.display_name} Level {hero.level}!")
    await show_hero_detail(update, context, user_id, hero_type)


async def show_skill_tree(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, tree: str):
    """Show skill tree"""
    query = update.callback_query
    
    tree_data = SKILL_TREE.get(tree, {})
    tree_names = {"attack": "⚔️ Attack", "defense": "🛡 Defense", "economy": "💰 Economy"}
    
    text = f"{tree_names.get(tree, tree)} **SKILL TREE**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    
    for tier, skill in tree_data.items():
        text += f"**{skill['name']}** ({tier})\n"
        text += f"📊 {skill['desc']}\n"
        text += f"💎 Cost: {skill['cost']} points\n"
        if skill.get("requires"):
            text += f"🔒 Requires: {skill['requires']}\n"
        text += "\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="menu_heroes")],
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)
