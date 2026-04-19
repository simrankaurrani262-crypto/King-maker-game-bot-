"""
King-Maker Bot — Elite Edition
Alliance / Guild System Handlers
"""

from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, Alliance
from bot.services.economy import EconomyService


def render_bar(value: int, maximum: int, width: int = 12, fill: str = "█", empty: str = "░") -> str:
    """Render a horizontal progress bar."""
    if maximum <= 0:
        return empty * width
    ratio = min(value / maximum, 1.0)
    filled = int(round(ratio * width))
    return fill * filled + empty * (width - filled)


async def show_alliance_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show alliance hub — member view or join/create options."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

        if k.alliance_id:
            # Show current alliance
            alliance = db.query(Alliance).filter(Alliance.id == k.alliance_id).first()
            if not alliance:
                k.alliance_id = None
                db.commit()
                return await _show_no_alliance(query)

            members = db.query(Kingdom).filter(Kingdom.alliance_id == alliance.id).all()
            total_power = sum(
                EconomyService.calculate_kingdom_power(m) if m.army else 0
                for m in members
            )
            is_leader = alliance.leader_id == user_id

            # Member list (top 5)
            member_lines = []
            for i, m in enumerate(sorted(members, key=lambda x: EconomyService.calculate_kingdom_power(x) if x.army else 0, reverse=True)[:5], 1):
                power = EconomyService.calculate_kingdom_power(m) if m.army else 0
                crown = "👑" if m.user_id == alliance.leader_id else "  "
                member_lines.append(f"{crown}{i}. {m.name} {m.flag} — ⚔ {power:,}")

            # Power bar
            power_bar = render_bar(total_power, max(total_power * 2, 10000), 14)

            text = (
                f"🤝 **{alliance.name}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 Members: {len(members)}\n"
                f"⚔ Total Power: **{total_power:,}**\n"
                f"{power_bar}\n"
                f"👑 Leader: {alliance.leader_id == user_id and 'You' or 'Other'}\n\n"
                f"**Top Members:**\n"
                f"{chr(10).join(member_lines)}\n\n"
                f"💰 Alliance Gold: {getattr(alliance, 'gold', 0)}"
            )

            buttons = [
                [InlineKeyboardButton("👥 All Members", callback_data=f"alliance_members:{alliance.id}")],
                [InlineKeyboardButton("💰 Donate", callback_data=f"alliance_donate:{alliance.id}")],
            ]
            if is_leader:
                buttons.append([InlineKeyboardButton("⚙️ Manage", callback_data=f"alliance_manage:{alliance.id}")])
            buttons.append([InlineKeyboardButton("🚪 Leave Alliance", callback_data=f"alliance_leave:{alliance.id}")])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")])

            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        else:
            await _show_no_alliance(query)


async def _show_no_alliance(query):
    """Show options for players without alliance."""
    await query.edit_message_text(
        "🤝 **ALLIANCE HUB**\n\n"
        "Aap kisi alliance mein nahi hain!\n\n"
        "Alliance se benefits:\n"
        "• 👥 Team protection\n"
        "• 💰 Shared resources\n"
        "• ⚔️ Coordinated attacks\n"
        "• 🏆 Alliance leaderboard\n\n"
        "Create ya join karo!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏰 Create Alliance", callback_data="alliance_create")],
            [InlineKeyboardButton("🔍 Join Alliance", callback_data="alliance_join")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
        ]),
    )


async def create_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start alliance creation flow."""
    query = update.callback_query
    await query.edit_message_text(
        "🏰 **Create Alliance**\n\n"
        "Alliance ka naam batao!\n"
        "(3-20 characters)\n\n"
        "Cost: 500 Gold",
        parse_mode="Markdown",
    )
    context.user_data["input_action"] = "alliance_create_name"


async def join_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available alliances to join."""
    query = update.callback_query

    with get_db() as db:
        alliances = db.query(Alliance).all()
        if not alliances:
            return await query.edit_message_text(
                "📭 Koi alliance available nahi!\n\n"
                "🏰 Apna alliance create karo!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏰 Create Alliance", callback_data="alliance_create")],
                    [InlineKeyboardButton("🔙 Back", callback_data="menu_alliance")],
                ]),
            )

        lines = ["🔍 **AVAILABLE ALLIANCES**\n"]
        buttons = []
        for a in alliances:
            members = db.query(Kingdom).filter(Kingdom.alliance_id == a.id).count()
            lines.append(f"• {a.name} — 👥 {members} members")
            buttons.append([InlineKeyboardButton(f"Join {a.name}", callback_data=f"alliance_join_id:{a.id}")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_alliance")])

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def leave_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE, alliance_id: int):
    """Leave current alliance."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k or k.alliance_id != alliance_id:
            return await query.edit_message_text("❌ Alliance error!")

        alliance = db.query(Alliance).filter(Alliance.id == alliance_id).first()
        if not alliance:
            return await query.edit_message_text("❌ Alliance not found!")

        # If leader, disband or transfer
        if alliance.leader_id == user_id:
            members = db.query(Kingdom).filter(Kingdom.alliance_id == alliance_id).all()
            if len(members) > 1:
                # Transfer leadership
                for m in members:
                    if m.user_id != user_id:
                        alliance.leader_id = m.user_id
                        break
            else:
                # Disband
                db.delete(alliance)

        k.alliance_id = None
        db.commit()

    await query.edit_message_text(
        "🚪 **Alliance chhod diya!**\n\n"
        "Naya alliance join kar sakte ho!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Alliance Hub", callback_data="menu_alliance")],
            [InlineKeyboardButton("🔙 Dashboard", callback_data="back_dashboard")],
        ]),
    )
