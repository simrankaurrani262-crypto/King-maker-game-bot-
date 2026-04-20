"""
Settings Handler - User preferences and configuration
Fixed version with proper imports and complete functionality.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, NotificationPref, UserAchievement, Achievement
from bot.services.game_data import GameData
from bot.utils.keyboards import (
    settings_keyboard, notification_settings_keyboard,
    back_dashboard_keyboard
)


async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show settings menu"""
    query = update.callback_query

    text = (
        "⚙️ **SETTINGS**\n"
        "━━━━━━━━━━━━━━\n\n"
        "Apni preferences customize karo!"
    )

    if query:
        await query.edit_message_text(text, reply_markup=settings_keyboard())
    else:
        await context.bot.send_message(
            chat_id=user_id, text=text, reply_markup=settings_keyboard()
        )


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

    text = (
        "🔔 **NOTIFICATION SETTINGS**\n"
        "━━━━━━━━━━━━━━\n\n"
        "Toggle karne ke liye button dabao:"
    )

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
            current = getattr(prefs, field, True)
            setattr(prefs, field, not current)
            db.commit()

    await query.answer("✅ Toggled!")
    await show_notification_settings(update, context, user_id)


async def show_title_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show title settings"""
    query = update.callback_query

    with get_db() as db:
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()

    titles = []
    for ua in user_achievements:
        if ua.achievement and ua.achievement.title_reward:
            titles.append(ua.achievement.title_reward)

    if not titles:
        await query.edit_message_text(
            (
                "🏷 **Titles**\n"
                "━━━━━━━━━━━━━━\n\n"
                "❌ Abhi tak koi title nahi!\n"
                "Achievements unlock karo titles paane ke liye!"
            ),
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

    text = (
        "🌐 **LANGUAGE**\n"
        "━━━━━━━━━━━━━━\n\n"
        "Abhi sirf **Hinglish** (Hindi + English) supported hai!\n\n"
        "Aur languages jald aayengi! 🌍"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show help / how to play"""
    query = update.callback_query

    help_text = (
        "📖 **HOW TO PLAY**\n"
        "━━━━━━━━━━━━━━\n\n"
        "**Core Loop:**\n"
        "1️⃣ Collect resources from Gold Mine & Farm\n"
        "2️⃣ Upgrade buildings for more production\n"
        "3️⃣ Train army in Training Center\n"
        "4️⃣ Attack other players for loot!\n\n"
        "**Commands:**\n"
        "/start — Dashboard\n"
        "/attack — Attack menu\n"
        "/build — Buildings\n"
        "/train — Training center\n"
        "/trade — Trade resources\n"
        "/map — World map\n"
        "/stats — Statistics & charts\n"
        "/help — This guide\n\n"
        "**Energy System:**\n"
        "⚡ 10 Energy max, 1 per attack\n"
        "⏳ Regenerates every 30 min\n\n"
        "**Shield System:**\n"
        "🛡 24h newbie shield\n"
        "🛡 Shield breaks on attack\n\n"
        "**Tips:**\n"
        "🎯 Pehle buildings upgrade karo\n"
        "🎯 Food maintain karo warna army bhaag jayegi\n"
        "🎯 Alliance join karo protection ke liye\n"
        "🎯 Spy bhejo pehle attack ke liye\n\n"
        "Good luck, King! 👑"
    )

    await query.edit_message_text(help_text, reply_markup=back_dashboard_keyboard())


# ═══════════════════════════════════════════
# ROUTER COMPATIBILITY WRAPPERS
# ═══════════════════════════════════════════

async def show_title_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for title settings"""
    await show_title_settings(update, context, user_id)


async def show_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for language settings"""
    await show_language_settings(update, context, user_id)


async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for help display"""
    await show_help(update, context, user_id)


async def toggle_setting(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, toggle_type: str):
    """Wrapper for toggling notification settings"""
    await toggle_notification(update, context, user_id, toggle_type)
