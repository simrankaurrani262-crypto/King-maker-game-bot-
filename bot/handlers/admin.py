from telegram import Update
from telegram.ext import ContextTypes
from bot.models import get_db, User, Kingdom
from bot.services.game_data import GameData


async def handler_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin commands"""
    user_id = update.effective_user.id
    
    # Check admin status
    from bot.config import config
    if user_id != config.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Admin access only!")
        return
    
    if not context.args:
        await show_admin_help(update, context)
        return
    
    command = context.args[0].lower()
    
    if command == "stats":
        await admin_stats(update, context)
    elif command == "broadcast":
        await admin_broadcast(update, context)
    elif command == "warn":
        await admin_warn(update, context)
    elif command == "ban":
        await admin_ban(update, context)
    elif command == "unban":
        await admin_unban(update, context)
    elif command == "give":
        await admin_give(update, context)
    elif command == "maintenance":
        await admin_maintenance(update, context)
    else:
        await show_admin_help(update, context)


async def show_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin command help"""
    text = """🔧 **ADMIN COMMANDS**
━━━━━━━━━━━━━━

`/admin stats` — Bot statistics
`/admin broadcast <message>` — Global announcement
`/admin warn @user <reason>` — Warn user
`/admin ban @user <days> <reason>` — Ban user
`/admin unban @user` — Unban user
`/admin give @user <gold|gems|food> <amount>` — Give resources
`/admin maintenance <on|off>` — Toggle maintenance"""
    
    await update.message.reply_text(text)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    with get_db() as db:
        total_users = db.query(User).count()
        total_kingdoms = db.query(Kingdom).count()
        banned_users = db.query(User).filter(User.is_banned == True).count()
        active_today = db.query(User).filter(
            User.last_active > __import__('datetime').datetime.utcnow() - __import__('datetime').timedelta(days=1)
        ).count()
    
    text = f"""📊 **BOT STATISTICS**
━━━━━━━━━━━━━━

👥 Total Users: {total_users}
🏰 Total Kingdoms: {total_kingdoms}
🟢 Active Today: {active_today}
⛔ Banned: {banned_users}"""
    
    await update.message.reply_text(text)


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/admin broadcast <message>`")
        return
    
    message = " ".join(context.args[1:])
    
    with get_db() as db:
        users = db.query(User).filter(User.is_banned == False).all()
    
    sent = 0
    failed = 0
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 **ANNOUNCEMENT**\n\n{message}"
            )
            sent += 1
        except Exception:
            failed += 1
    
    await update.message.reply_text(f"✅ Sent: {sent}\n❌ Failed: {failed}")


async def admin_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user"""
    if len(context.args) < 3:
        await update.message.reply_text("❌ Usage: `/admin warn @user <reason>`")
        return
    
    username = context.args[1].replace("@", "")
    reason = " ".join(context.args[2:])
    
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await update.message.reply_text("❌ User nahi mila!")
            return
        
        user.warning_count += 1
        db.commit()
    
    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=f"⚠️ **WARNING #{user.warning_count}**\nReason: {reason}\n\n3 warnings = temporary ban!"
        )
    except Exception:
        pass
    
    await update.message.reply_text(f"⚠️ {username} ko warning #{user.warning_count} di gayi!")


async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user"""
    if len(context.args) < 4:
        await update.message.reply_text("❌ Usage: `/admin ban @user <days> <reason>`")
        return
    
    username = context.args[1].replace("@", "")
    try:
        days = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Valid days enter karo!")
        return
    
    reason = " ".join(context.args[3:])
    
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await update.message.reply_text("❌ User nahi mila!")
            return
        
        user.is_banned = True
        user.ban_reason = reason
        user.ban_expires = __import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(days=days)
        db.commit()
    
    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=f"⛔ **BANNED**\nReason: {reason}\nDuration: {days} days"
        )
    except Exception:
        pass
    
    await update.message.reply_text(f"⛔ {username} {days} din ke liye banned!")


async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/admin unban @user`")
        return
    
    username = context.args[1].replace("@", "")
    
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await update.message.reply_text("❌ User nahi mila!")
            return
        
        user.is_banned = False
        user.ban_reason = None
        user.ban_expires = None
        user.warning_count = 0
        db.commit()
    
    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text="✅ **UNBANNED**\nAapka ban khatam ho gaya hai!"
        )
    except Exception:
        pass
    
    await update.message.reply_text(f"✅ {username} unbanned!")


async def admin_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give resources to a user"""
    if len(context.args) < 4:
        await update.message.reply_text("❌ Usage: `/admin give @user <gold|gems|food> <amount>`")
        return
    
    username = context.args[1].replace("@", "")
    resource = context.args[2].lower()
    try:
        amount = int(context.args[3])
    except ValueError:
        await update.message.reply_text("❌ Valid amount enter karo!")
        return
    
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await update.message.reply_text("❌ User nahi mila!")
            return
        
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user.telegram_id).first()
        if not kingdom:
            await update.message.reply_text("❌ User ka kingdom nahi mila!")
            return
        
        if resource == "gold":
            kingdom.gold += amount
        elif resource == "gems":
            kingdom.gems += amount
        elif resource == "food":
            kingdom.food += amount
        else:
            await update.message.reply_text("❌ Resource: gold/gems/food")
            return
        
        db.commit()
    
    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=f"🎁 **Admin Gift!**\n💰 +{amount:,} {resource.title()}!"
        )
    except Exception:
        pass
    
    await update.message.reply_text(f"✅ {username} ko {amount:,} {resource} diya!")


async def admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle maintenance mode"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/admin maintenance <on|off>`")
        return

    state = context.args[1].lower()
    from bot.config import config

    if state == "on":
        config.MAINTENANCE_MODE = True
        await update.message.reply_text("🔧 Maintenance mode **ON**")
    else:
        config.MAINTENANCE_MODE = False
        await update.message.reply_text("✅ Maintenance mode **OFF**")


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    from bot.config import config

    if user_id != config.ADMIN_TELEGRAM_ID:
        await query.edit_message_text("⛔ Admin access only!")
        return

    data = query.data

    if data == "admin_stats":
        await _admin_stats_callback(query)

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 Send broadcast message using:\n`/admin broadcast <message>`",
            reply_markup=back_dashboard_keyboard()
        )

    elif data == "admin_maintenance":
        await query.edit_message_text(
            "🔧 Toggle maintenance:\n`/admin maintenance <on|off>`",
            reply_markup=back_dashboard_keyboard()
        )


async def _admin_stats_callback(query):
    """Show admin stats in callback"""
    with get_db() as db:
        total_users = db.query(User).count()
        total_kingdoms = db.query(Kingdom).count()
        banned_users = db.query(User).filter(User.is_banned == True).count()
        active_today = db.query(User).filter(
            User.last_active > datetime.utcnow() - timedelta(days=1)
        ).count()

    text = (
        f"📊 **BOT STATISTICS**\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🏰 Total Kingdoms: {total_kingdoms}\n"
        f"🟢 Active Today: {active_today}\n"
        f"⛔ Banned: {banned_users}"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


# Import at bottom to avoid circular issues
from bot.utils.keyboards import back_dashboard_keyboard
from bot.models import get_db, User, Kingdom
