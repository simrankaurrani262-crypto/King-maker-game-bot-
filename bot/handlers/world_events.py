"""
World Events Handler - Display and interact with world events
NEW FEATURE: View active events, event history, and participate.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, WorldEvent
from bot.services.game_data import GameData
from bot.utils.keyboards import world_events_keyboard, back_dashboard_keyboard


async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show world events menu"""
    query = update.callback_query

    text = (
        "🌍 **WORLD EVENTS**\n"
        "━━━━━━━━━━━━━━\n\n"
        "Duniya bhar ke events yahan dikhaye jate hain!\n\n"
        "Events se fayda uthao ya challenges face karo!"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=world_events_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=world_events_keyboard())


async def handle_events_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle world events callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "events_active":
        await show_active_events(update, context, user_id)

    elif data == "events_history":
        await show_event_history(update, context, user_id)

    elif data == "menu_events":
        await show_events_menu(update, context, user_id)


async def show_active_events(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show currently active world events"""
    query = update.callback_query

    events = GameData.get_active_world_events()

    if not events:
        await query.edit_message_text(
            (
                "🌍 **ACTIVE EVENTS**\n"
                "━━━━━━━━━━━━━━\n\n"
                "🌙 Koi active event nahi hai abhi.\n\n"
                "Events har 15-30 min mein randomly spawn hote hain!"
            ),
            reply_markup=world_events_keyboard()
        )
        return

    text = (
        "🌍 **ACTIVE EVENTS**\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for event in events:
        remaining = event.ends_at - datetime.utcnow()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)

        event_emojis = {
            "treasure": "💎",
            "plague": "😷",
            "festival": "🎉",
            "invasion": "🐉",
        }
        emoji = event_emojis.get(event.event_type, "🌍")

        text += (
            f"{emoji} **{event.name}**\n"
            f"   {event.description}\n"
            f"   ⏳ {hours}h {minutes}m remaining\n\n"
        )

    await query.edit_message_text(text, reply_markup=world_events_keyboard())


async def show_event_history(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show past world events"""
    query = update.callback_query

    with get_db() as db:
        events = db.query(WorldEvent).filter(
            WorldEvent.ends_at <= datetime.utcnow()
        ).order_by(WorldEvent.created_at.desc()).limit(10).all()

    if not events:
        await query.edit_message_text(
            (
                "📜 **EVENT HISTORY**\n"
                "━━━━━━━━━━━━━━\n\n"
                "Koi past events nahi!"
            ),
            reply_markup=world_events_keyboard()
        )
        return

    text = (
        "📜 **EVENT HISTORY**\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    for event in events:
        event_emojis = {
            "treasure": "💎",
            "plague": "😷",
            "festival": "🎉",
            "invasion": "🐉",
        }
        emoji = event_emojis.get(event.event_type, "🌍")
        status = "✅ Ended" if datetime.utcnow() > event.ends_at else "⏳ Active"

        text += f"{emoji} {event.name} — {status}\n"

    await query.edit_message_text(text, reply_markup=world_events_keyboard())
