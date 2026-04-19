"""
King-Maker Bot — Elite Edition
Spy / Espionage Handlers — Fixed cooldown system
"""

from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, SpyReport, Cooldown
from bot.services.economy import EconomyService
from bot.utils.keyboards import spy_menu_keyboard, back_dashboard_keyboard


SPY_COOLDOWN_MINUTES = 5
SPY_COST_GOLD = 50


async def show_spy_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show spy menu with cooldown status."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

        # Check cooldown
        cd = db.query(Cooldown).filter(
            Cooldown.user_id == user_id,
            Cooldown.action_type == "spy",
        ).first()

        cooldown_text = ""
        if cd and cd.expires_at and cd.expires_at > datetime.utcnow():
            mins = int((cd.expires_at - datetime.utcnow()).total_seconds() / 60)
            secs = int((cd.expires_at - datetime.utcnow()).total_seconds() % 60)
            cooldown_text = f"\n⏳ Cooldown: {mins}m {secs}s"

        await query.edit_message_text(
            f"🕵️ **SPY AGENCY**\n\n"
            f"Dushman ki secret info collect karo!\n\n"
            f"💰 Cost: {SPY_COST_GOLD} Gold/spy\n"
            f"⏳ Cooldown: {SPY_COOLDOWN_MINUTES} minutes\n"
            f"📊 Reports: Last 5 saved\n"
            f"{cooldown_text}",
            parse_mode="Markdown",
            reply_markup=spy_menu_keyboard(),
        )


async def send_spy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send spy to a target — FIXED unified cooldown system."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

        # Check gold
        if k.gold < SPY_COST_GOLD:
            return await query.edit_message_text(
                f"💰 **{SPY_COST_GOLD} Gold** chahiye!\n"
                f"Balance: {k.gold}",
                parse_mode="Markdown",
                reply_markup=spy_menu_keyboard(),
            )

        # FIXED: Unified cooldown check using expires_at only
        cd = db.query(Cooldown).filter(
            Cooldown.user_id == user_id,
            Cooldown.action_type == "spy",
        ).first()

        if cd and cd.expires_at and cd.expires_at > datetime.utcnow():
            mins = int((cd.expires_at - datetime.utcnow()).total_seconds() / 60)
            secs = int((cd.expires_at - datetime.utcnow()).total_seconds() % 60)
            return await query.edit_message_text(
                f"⏳ **Spy on Cooldown!**\n\n"
                f"{mins}m {secs}s remaining\n\n"
                f"Baad mein try karo!",
                parse_mode="Markdown",
                reply_markup=spy_menu_keyboard(),
            )

        # Get random target (similar level, different player)
        target = _find_spy_target(db, k, user_id)
        if not target:
            return await query.edit_message_text(
                "🔍 No suitable spy targets found!\n"
                "Aur players join hone do!",
                reply_markup=spy_menu_keyboard(),
            )

        # Deduct gold
        k.gold -= SPY_COST_GOLD

        # Set cooldown — FIXED: Consistent interface
        if not cd:
            cd = Cooldown(
                user_id=user_id,
                action_type="spy",
                duration_minutes=SPY_COOLDOWN_MINUTES,
                expires_at=datetime.utcnow() + timedelta(minutes=SPY_COOLDOWN_MINUTES),
            )
            db.add(cd)
        else:
            cd.expires_at = datetime.utcnow() + timedelta(minutes=SPY_COOLDOWN_MINUTES)
            cd.duration_minutes = SPY_COOLDOWN_MINUTES

        # Calculate accuracy based on kingdom level
        accuracy = min(0.95, 0.50 + (k.level * 0.05))

        # Generate spy report
        report = SpyReport(
            spy_id=user_id,
            target_id=target.user_id,
            target_name=target.name,
            army_total=target.army.total if target.army else 0,
            infantry=target.army.infantry if target.army else 0,
            archers=target.army.archers if target.army else 0,
            cavalry=target.army.cavalry if target.army else 0,
            attack_power=int((target.army.attack_power if target.army else 0) * accuracy),
            defense_power=int((target.army.defense_power if target.army else 0) * accuracy),
            gold=int(target.gold * accuracy),
            food=int(target.food * accuracy),
            accuracy=accuracy,
        )
        db.add(report)
        db.commit()

    # Visual spy report with accuracy bar
    acc_bar = _render_bar(int(accuracy * 100), 100, 10)

    await query.edit_message_text(
        f"🕵️ **SPY REPORT**\n"
        f"Target: **{target.name}** {target.flag}\n\n"
        f"📊 Accuracy: {int(accuracy * 100)}%\n"
        f"{acc_bar}\n\n"
        f"🪖 **Army Intelligence:**\n"
        f"   Total: ~{report.army_total} units\n"
        f"   🗡 Infantry: ~{report.infantry}\n"
        f"   🏹 Archers: ~{report.archers}\n"
        f"   🐎 Cavalry: ~{report.cavalry}\n\n"
        f"⚔ Attack: ~{report.attack_power}\n"
        f"🛡 Defense: ~{report.defense_power}\n\n"
        f"💰 Gold: ~{report.gold}\n"
        f"🍖 Food: ~{report.food}\n"
        f"🛡 Shield: {'Yes ⚠️' if target.has_shield else 'No ✅'}\n\n"
        f"⏳ Next spy: {SPY_COOLDOWN_MINUTES} min",
        parse_mode="Markdown",
        reply_markup=spy_menu_keyboard(),
    )


def _find_spy_target(db, kingdom, user_id):
    """Find a suitable spy target."""
    candidates = db.query(Kingdom).filter(
        Kingdom.user_id != user_id,
        Kingdom.level.between(max(1, kingdom.level - 5), kingdom.level + 5),
    ).all()

    valid = [c for c in candidates if not c.has_shield]
    if valid:
        import random
        return random.choice(valid)
    return None


def _render_bar(value: int, maximum: int, width: int = 12, fill: str = "█", empty: str = "░") -> str:
    """Render a horizontal bar."""
    if maximum <= 0:
        return empty * width
    ratio = min(value / maximum, 1.0)
    filled = int(round(ratio * width))
    return fill * filled + empty * (width - filled)


async def show_spy_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show spy history with visual timeline."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        reports = db.query(SpyReport).filter(
            SpyReport.spy_id == user_id,
        ).order_by(SpyReport.timestamp.desc()).limit(10).all()

        if not reports:
            return await query.edit_message_text(
                "📭 No spy reports yet!\n\n"
                "🕵️ Spy bhejo pehle!",
                reply_markup=spy_menu_keyboard(),
            )

        lines = ["🕵️ **SPY HISTORY**\n"]
        for r in reports:
            time_ago = _time_ago(r.timestamp)
            acc = int(r.accuracy * 100)
            lines.append(
                f"• {r.target_name}\n"
                f"  ⚔~{r.attack_power} 💰~{r.gold} 🛡{'Yes' if r.shield else 'No'}\n"
                f"  📊 {acc}% accuracy | {time_ago}"
            )

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="menu_spy")],
            ]),
        )


def _time_ago(timestamp) -> str:
    """Human readable time ago."""
    if not timestamp:
        return "unknown"
    delta = datetime.utcnow() - timestamp
    if delta.days > 0:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    mins = delta.seconds // 60
    return f"{mins}m ago"
