from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.services.game_data import GameData
from bot.utils.keyboards import (
    settings_keyboard, notification_settings_keyboard,
    back_dashboard_keyboard
)


async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show settings menu"""
    query = update.callback_query
    
    text = "⚙️ **SETTINGS**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += "Apni preferences customize karo!"
    
    await query.edit_message_text(text, reply_markup=settings_keyboard())


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_settings":
        await show_settings_menu(update, context, user_id)
    
    elif data == "settings_notif":
        await show_notification_settings(update, context, user_id)
    
    elif data.startswith("toggle_"):
        toggle = data.replace("toggle_", "")
        await toggle_notification(update, context, user_id, toggle)
    
    elif data == "settings_title":
        await show_title_settings(update, context, user_id)
    
    elif data == "settings_lang":
        await show_language_settings(update, context, user_id)
    
    elif data == "settings_help":
        await show_help(update, context, user_id)


async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show notification settings"""
    query = update.callback_query
    
    prefs = GameData.get_notification_prefs(user_id)
    
    text = "🔔 **NOTIFICATION SETTINGS**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += "Toggle karne ke liye button dabao:"
    
    await query.edit_message_text(
        text,
        reply_markup=notification_settings_keyboard(prefs)
    )


async def toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, toggle: str):
    """Toggle a notification preference"""
    query = update.callback_query
    
    with get_db() as db:
        prefs = db.query(NotificationPref).filter(NotificationPref.user_id == user_id).first()
        if not prefs:
            prefs = NotificationPref(user_id=user_id)
            db.add(prefs)
        
        toggle_map = {
            "battle": "battle_alerts",
            "energy": "energy_full",
            "resource": "resource_full",
            "building": "building_complete",
            "alliance": "alliance_events",
            "bounty": "bounty_alerts",
            "promo": "promotions",
        }
        
        field = toggle_map.get(toggle)
        if field:
            current = getattr(prefs, field)
            setattr(prefs, field, not current)
            db.commit()
    
    await query.answer("✅ Toggled!")
    await show_notification_settings(update, context, user_id)


async def show_title_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show title settings"""
    query = update.callback_query
    
    with get_db() as db:
        from bot.models import UserAchievement, Achievement
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()
    
    titles = []
    for ua in user_achievements:
        if ua.achievement and ua.achievement.title_reward:
            titles.append(ua.achievement.title_reward)
    
    if not titles:
        await query.edit_message_text(
            "🏷 **Titles**\n"
            "━━━━━━━━━━━━━━\n\n"
            "❌ Abhi tak koi title nahi!\n"
            "Achievements unlock karo titles paane ke liye!",
            reply_markup=back_dashboard_keyboard()
        )
        return
    
    text = "🏷 **SELECT TITLE**\n━━━━━━━━━━━━━━\n\n"
    buttons = []
    for t in titles:
        buttons.append([InlineKeyboardButton(t, callback_data=f"set_title:{t}")])
    buttons.append([InlineKeyboardButton("❌ No Title", callback_data="set_title:none")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_settings")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def show_language_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show language settings"""
    query = update.callback_query
    
    text = "🌐 **LANGUAGE**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += "Abhi sirf **Hinglish** (Hindi + English) supported hai!\n\n"
    text += "Aur languages jald aayengi! 🌍"
    
    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show help / how to play"""
    query = update.callback_query
    
    help_text = """📖 **HOW TO PLAY**
━━━━━━━━━━━━━━

**Core Loop:**
1️⃣ Collect resources from Gold Mine & Farm
2️⃣ Upgrade buildings for more production
3️⃣ Train army in Barracks
4️⃣ Attack other players for loot!

**Commands:**
/start — Dashboard
/attack — Attack menu
/build — Buildings
/army — Army view
/map — World map
/help — This guide

**Energy System:**
⚡ 10 Energy max, 1 per attack
⏳ Regenerates every 30 min

**Shield System:**
🛡 24h newbie shield
🛡 Shield breaks on attack

**Tips:**
🎯 Pehle buildings upgrade karo
🎯 Food maintain karo warna army bhaag jayegi
🎯 Alliance join karo protection ke liye
🎯 Spy bhejo pehle attack ke liye

Good luck, King! 👑"""
    
    await query.edit_message_text(help_text, reply_markup=back_dashboard_keyboard())


# Need get_db import
from bot.models import get_db
