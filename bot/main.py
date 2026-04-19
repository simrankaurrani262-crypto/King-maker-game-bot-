"""
King-Maker Bot — Elite Edition
Main entry point with full callback routing, chart/graph support,
 and production-grade error handling.
"""

import logging, json, random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters,
)

from bot.config import config
from bot.models import (
    get_db, User, Kingdom, Army, Building, Battle,
    SpyReport, WorldEvent, Bounty, NotificationPref,
)
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.keyboards import (
    dashboard_keyboard, building_action_keyboard, building_menu_keyboard,
    attack_menu_keyboard, opponent_keyboard, army_menu_keyboard,
    back_dashboard_keyboard, start_menu_keyboard, hero_action_keyboard,
    games_menu_keyboard, dice_keyboard, spin_keyboard, alliance_hub_keyboard,
    alliance_hub_no_alliance_keyboard, map_menu_keyboard, map_tile_keyboard,
    quests_keyboard, spy_menu_keyboard, settings_keyboard,
    notification_settings_keyboard, leaderboard_keyboard,
    bounty_menu_keyboard, decision_keyboard, confirm_keyboard,
)
from bot.utils.validators import validate_kingdom_name, validate_positive_number

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("KingMakerBot")

# ── Conversation states ──────────────────────────────────────────
NAME, TRAIT = range(2)
INPUT_ACTION = "input_action"

# ═══════════════════════════════════════════════════════════════════
#  CHART / GRAPH HELPERS — Elite Visual System
# ═══════════════════════════════════════════════════════════════════


def render_bar(value: int, maximum: int, width: int = 12, fill: str = "█", empty: str = "░") -> str:
    """Render a single horizontal bar."""
    if maximum <= 0:
        return empty * width
    ratio = min(value / maximum, 1.0)
    filled = int(round(ratio * width))
    return fill * filled + empty * (width - filled)


def render_resource_gold(gold: int, max_g: int = 10000) -> str:
    return f"💰 Gold  {render_bar(gold, max_g)}  {gold:,} / {max_g:,}"


def render_resource_food(food: int, max_f: int = 10000) -> str:
    return f"🍖 Food  {render_bar(food, max_f)}  {food:,} / {max_f:,}"


def render_resource_energy(energy: int, max_e: int = 10) -> str:
    return f"⚡ Energy {render_bar(energy, max_e)}  {energy} / {max_e}"


def render_xp_bar(xp: int, xp_needed: int, width: int = 16) -> str:
    """Render XP progress with percentage."""
    ratio = min(xp / max(xp_needed, 1), 1.0)
    filled = int(round(ratio * width))
    pct = int(ratio * 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"📈 XP {bar} {pct}% ({xp:,}/{xp_needed:,})"


def render_power_comparison(my_power: int, opp_power: int, width: int = 14) -> str:
    """Side-by-side power bar for battle preview."""
    total = max(my_power + opp_power, 1)
    my_w = int(round(my_power / total * width))
    opp_w = width - my_w
    return f"⚔️  {'█' * my_w}{'░' * opp_w}  🛡"


def render_radar_chart(kingdom) -> str:
    """ASCII radar chart showing kingdom stats."""
    categories = ["Attack", "Defend", "Economy", "Growth", "Intel"]
    if not kingdom.army:
        return "📊 No army data for radar chart."
    atk = min(kingdom.army.attack_power / 500, 10)
    dfn = min(kingdom.army.defense_power / 500, 10)
    eco = min(kingdom.gold / 5000, 10)
    grw = min(kingdom.level, 10)
    intel = kingdom.spy_level if hasattr(kingdom, "spy_level") else 0
    intel = min(intel / 5, 10)
    values = [atk, dfn, eco, grw, intel]

    def bar(v: float) -> str:
        filled = int(round(v))
        return "█" * filled + "░" * (10 - filled)

    lines = ["📊 **KINGDOM RADAR CHART**", "```"]
    for cat, val in zip(categories, values):
        lines.append(f"{cat:8s} {bar(val)} {val:.1f}/10")
    lines.append("```")
    return "\n".join(lines)


def render_line_chart(data_points: list, label: str = "Trend", width: int = 20) -> str:
    """Simple ASCII line chart for history data."""
    if not data_points or len(data_points) < 2:
        return ""
    mn, mx = min(data_points), max(data_points)
    if mx == mn:
        return f"📈 {label}: {'─' * width} (flat)"
    lines = [f"📈 **{label}**", "```"]
    for val in data_points:
        pos = int(round((val - mn) / (mx - mn) * width))
        bar = " " * pos + "●"
        lines.append(bar)
    lines.append("```")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  CORE COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point — show start menu (both CommandHandler & CallbackQuery)."""
    from bot.handlers.start import start_menu_handler, tutorial_handler

    query = update.callback_query
    if query:
        data = query.data
        if data == "start_game":
            return await start_menu_handler(update, context)
        elif data == "how_to_play":
            return await tutorial_handler(update, context)
        return await query.answer()

    user = update.effective_user
    with get_db() as db:
        existing = db.query(User).filter(User.telegram_id == user.id).first()
        if existing:
            # Registered user → show dashboard
            await show_dashboard(update, context)
            return

    # New user → start menu
    welcome = (
        "👑 **Welcome to King-Maker!**\n\n"
        "Ek anokha **Kingdom Strategy Game**!\n\n"
        "Apna khud ka Kingdom banao, Army train karo,\n"
        "Dushmano pe attack karo, aur **Supreme King** bano!"
    )
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=start_menu_keyboard(),
    )


async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Render the main game dashboard with ELITE visual charts."""
    user_id = update.effective_user.id
    with get_db() as db:
        user = db.query(User).join(Kingdom).filter(User.telegram_id == user_id).first()
        if not user or not user.kingdom:
            await update.effective_message.reply_text(
                "❌ Kingdom nahi mila! /start se start karo.",
            )
            return

        k = user.kingdom
        k.last_active = datetime.utcnow()
        db.commit()

        power = EconomyService.calculate_kingdom_power(k)
        gold_prod = EconomyService.calculate_gold_production(k)
        food_prod = EconomyService.calculate_food_production(k)
        xp_needed = EconomyService.calculate_xp_needed(k.level)

        # Radar chart
        radar = render_radar_chart(k)

        # Production mini chart
        prod_history = getattr(k, "gold_history", [gold_prod * 0.8, gold_prod * 0.9, gold_prod])
        if len(prod_history) < 3:
            prod_history = [gold_prod * 0.7, gold_prod * 0.85, gold_prod]
        gold_chart = render_line_chart(prod_history[-7:], "Gold Production", 16)

        text = (
            f"🏰 **{k.name}**  |  {k.flag}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎖 Level: **{k.level}**\n"
            f"⚔ Power: **{power:,}**\n\n"
            f"{render_resource_gold(k.gold)}\n"
            f"{render_resource_food(k.food)}\n"
            f"{render_resource_energy(k.energy, config.MAX_ENERGY)}\n"
            f"{render_xp_bar(k.xp, xp_needed)}\n\n"
            f"💰 +{gold_prod}/hr  |  🍖 +{food_prod}/hr\n\n"
            f"{radar}\n\n"
            f"{gold_chart}\n\n"
            f"🪖 Army: 🗡 {k.army.infantry if k.army else 0}  "
            f"🏹 {k.army.archers if k.army else 0}  "
            f"🐎 {k.army.cavalry if k.army else 0}\n\n"
            f"🛡 Shield: {'Active' if k.has_shield else 'Inactive'}\n"
            f"👥 Alliance: {k.alliance.name if k.alliance else 'None'}\n\n"
            f"📍 Position: ({k.map_x}, {k.map_y})"
        )

        msg = update.effective_message
        # Try to edit existing message, fallback to new message
        try:
            await msg.edit_text(text, parse_mode="Markdown", reply_markup=dashboard_keyboard())
        except Exception:
            await msg.reply_text(text, parse_mode="Markdown", reply_markup=dashboard_keyboard())


# ═══════════════════════════════════════════════════════════════════
#  CALLBACK ROUTER — All callback_data routes
# ═══════════════════════════════════════════════════════════════════


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central callback router with full feature coverage."""
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        # ── Navigation ──────────────────────────────────────────
        if data == "back_dashboard":
            return await show_dashboard(update, context)
        elif data == "cancel_action":
            return await query.edit_message_text("❌ Action cancelled.", reply_markup=back_dashboard_keyboard())
        elif data == "noop":
            return await query.answer("Please wait...", show_alert=True)

        # ── Main Menu Categories ────────────────────────────────
        elif data == "menu_attack":
            return await route_attack(update, context)
        elif data == "menu_build":
            return await route_build(update, context)
        elif data == "menu_map":
            return await route_map(update, context)
        elif data == "menu_alliance":
            return await route_alliance(update, context)
        elif data == "menu_heroes":
            return await route_heroes(update, context)
        elif data == "menu_spy":
            return await route_spy(update, context)
        elif data == "menu_quests":
            return await route_quests(update, context)
        elif data == "menu_leaderboard":
            return await route_leaderboard(update, context)
        elif data == "menu_games":
            return await route_games(update, context)
        elif data == "menu_settings":
            return await route_settings(update, context)
        elif data == "menu_bounty":
            return await route_bounty(update, context)

        # ── Start / Tutorial ────────────────────────────────────
        elif data in ("start_game", "how_to_play"):
            return await start_command(update, context)

        # ── Settings ────────────────────────────────────────────
        elif data.startswith("settings_"):
            return await route_settings_detail(update, context)
        elif data.startswith("toggle_"):
            return await route_toggle_setting(update, context)

        # ── Attack System ───────────────────────────────────────
        elif data.startswith("attack_"):
            return await route_attack_action(update, context)
        elif data.startswith("battle_"):
            return await route_battle(update, context)

        # ── Spy System ──────────────────────────────────────────
        elif data.startswith("spy_"):
            return await route_spy(update, context)

        # ── Alliance ────────────────────────────────────────────
        elif data.startswith("alliance_"):
            return await route_alliance(update, context)

        # ── Building ────────────────────────────────────────────
        elif data.startswith("building_"):
            return await route_building(update, context)

        # ── Heroes ──────────────────────────────────────────────
        elif data.startswith("hero_") or data.startswith("skill_"):
            return await route_heroes(update, context)

        # ── Quests ──────────────────────────────────────────────
        elif data.startswith("quests_"):
            return await route_quests(update, context)

        # ── Games ───────────────────────────────────────────────
        elif data.startswith("game_"):
            return await route_games(update, context)
        elif data.startswith("dice_"):
            return await route_dice(update, context)
        elif data.startswith("spin_"):
            return await route_spin(update, context)
        elif data.startswith("quiz_"):
            return await route_quiz(update, context)
        elif data.startswith("survival_"):
            return await route_survival(update, context)
        elif data.startswith("market_"):
            return await route_market(update, context)

        # ── Leaderboard ─────────────────────────────────────────
        elif data.startswith("lb_"):
            return await route_leaderboard(update, context)

        # ── Bounty ──────────────────────────────────────────────
        elif data.startswith("bounty_"):
            return await route_bounty(update, context)

        # ── Map ─────────────────────────────────────────────────
        elif data.startswith("map_"):
            return await route_map(update, context)

        # ── Decision Events ─────────────────────────────────────
        elif data.startswith("decision:"):
            return await route_decision(update, context)

        # ── Trait Selection ─────────────────────────────────────
        elif data.startswith("trait:"):
            return await route_trait(update, context)

        else:
            logger.warning(f"Unknown callback: {data}")
            await query.edit_message_text("⚠️ Feature jald aa raha hai!", reply_markup=back_dashboard_keyboard())

    except Exception as e:
        logger.error(f"Callback error [{data}]: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ **Error!**\nKuch galat ho gaya.\nDashboard pe wapas ja rahe hain...",
            parse_mode="Markdown",
            reply_markup=back_dashboard_keyboard(),
        )


# ═══════════════════════════════════════════════════════════════════
#  ROUTE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════


async def route_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show attack menu with power preview."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        user = db.query(User).join(Kingdom).filter(User.telegram_id == user_id).first()
        if not user or not user.kingdom:
            return await query.edit_message_text("❌ Kingdom nahi mila!", reply_markup=back_dashboard_keyboard())
        k = user.kingdom
        power = EconomyService.calculate_kingdom_power(k) if k.army else 0
        await query.edit_message_text(
            f"⚔️ **ATTACK MENU**\n\n"
            f"Your Power: **{power:,}**\n"
            f"Energy: {k.energy}/{config.MAX_ENERGY}\n\n"
            f"Choose your strategy:",
            parse_mode="Markdown",
            reply_markup=attack_menu_keyboard(),
        )


async def route_attack_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all attack sub-actions."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).join(Kingdom).filter(User.telegram_id == user_id).first()
        if not user or not user.kingdom:
            return await query.edit_message_text("❌ Kingdom nahi mila!", reply_markup=back_dashboard_keyboard())
        k = user.kingdom

        if data == "attack_find":
            # Find opponent with power comparison
            candidates = GameDataService.find_opponents(k, db)
            if not candidates:
                return await query.edit_message_text(
                    "🔍 No suitable opponents found!\nBaad mein try karo.",
                    reply_markup=back_dashboard_keyboard(),
                )
            # Store candidates in user_data for pagination
            candidate_ids = [c.user_id for c in candidates]
            context.user_data["candidates"] = candidate_ids
            context.user_data["candidate_idx"] = 0
            return await _show_opponent(update, context, candidates[0])

        elif data == "attack_next":
            candidates_ids = context.user_data.get("candidates", [])
            idx = context.user_data.get("candidate_idx", 0) + 1
            if idx >= len(candidates_ids):
                idx = 0
            context.user_data["candidate_idx"] = idx
            opp = db.query(Kingdom).options(
                db.selectinload(Kingdom.army)
            ).filter(Kingdom.user_id == candidates_ids[idx]).first()
            if not opp:
                return await query.edit_message_text("Opponent not found!", reply_markup=attack_menu_keyboard())
            return await _show_opponent(update, context, opp)

        elif data == "attack_revenge":
            # Check battle history for revenge targets
            recent_battles = db.query(Battle).filter(
                Battle.defender_id == user_id,
                Battle.winner_id != user_id,
            ).order_by(Battle.timestamp.desc()).limit(5).all()
            if not recent_battles:
                return await query.edit_message_text(
                    "🔥 No one has defeated you recently!\nAap top pe hain!",
                    reply_markup=attack_menu_keyboard(),
                )
            # Show first revenge target
            battle = recent_battles[0]
            opp = db.query(Kingdom).options(
                db.selectinload(Kingdom.army)
            ).filter(Kingdom.user_id == battle.attacker_id).first()
            if not opp:
                return await query.edit_message_text("Opponent not found!", reply_markup=attack_menu_keyboard())
            context.user_data["revenge_targets"] = [b.attacker_id for b in recent_battles]
            return await _show_opponent(update, context, opp, revenge=True)

        elif data == "attack_map":
            return await route_map(update, context)

        elif data == "attack_raid":
            return await _quick_raid(update, context, k, db)

        elif data.startswith("attack_player:"):
            target_id = int(data.split(":")[1])
            return await _execute_attack(update, context, k, target_id, db)

        else:
            await query.edit_message_text("⚔️ Attack menu:", reply_markup=attack_menu_keyboard())


async def _show_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent, revenge: bool = False):
    """Display opponent info with visual power comparison."""
    query = update.callback_query
    my_id = update.effective_user.id
    with get_db() as db:
        me = db.query(Kingdom).options(db.selectinload(Kingdom.army)).filter(Kingdom.user_id == my_id).first()
        if not me:
            return await query.edit_message_text("❌ Error loading your kingdom!", reply_markup=back_dashboard_keyboard())
        my_power = EconomyService.calculate_kingdom_power(me) if me.army else 0
        opp_power = EconomyService.calculate_kingdom_power(opponent) if opponent.army else 0
        comparison = render_power_comparison(my_power, opp_power)
        label = "🔥 REVENGE TARGET" if revenge else "🎯 OPPONENT FOUND"
        text = (
            f"{label}\n\n"
            f"🏰 **{opponent.name}** {opponent.flag}\n"
            f"🎖 Level: {opponent.level}\n"
            f"⚔ Power: **{opp_power:,}**\n\n"
            f"{comparison}\n"
            f"You: {my_power:,}  vs  Them: {opp_power:,}\n\n"
            f"🪖 Army: 🗡 {opponent.army.infantry if opponent.army else 0}  "
            f"🏹 {opponent.army.archers if opponent.army else 0}  "
            f"🐎 {opponent.army.cavalry if opponent.army else 0}\n"
            f"🛡 Shield: {'Yes' if opponent.has_shield else 'No'}"
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=opponent_keyboard(opponent.user_id),
        )


async def _quick_raid(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom, db):
    """Quick raid on a random weak NPC target."""
    query = update.callback_query
    if kingdom.energy < 1:
        return await query.edit_message_text(
            "⚡ Energy kam hai!\n30 min mein regenerate hogi.",
            reply_markup=back_dashboard_keyboard(),
        )
    # Find a weak target (NPC style - just random low power)
    all_kingdoms = db.query(Kingdom).options(db.selectinload(Kingdom.army)).all()
    my_power = EconomyService.calculate_kingdom_power(kingdom) if kingdom.army else 0
    weak_targets = [k for k in all_kingdoms
                    if k.user_id != kingdom.user_id
                    and EconomyService.calculate_kingdom_power(k) < my_power * 0.5]
    if not weak_targets:
        return await query.edit_message_text(
            "🔍 No easy raid targets available!",
            reply_markup=attack_menu_keyboard(),
        )
    target = random.choice(weak_targets)
    return await _execute_attack(update, context, kingdom, target.user_id, db, raid=True)


async def _execute_attack(update: Update, context: ContextTypes.DEFAULT_TYPE, attacker_kingdom, target_id: int, db, raid: bool = False):
    """Execute a full attack with combat engine and visual results."""
    query = update.callback_query
    from bot.services.combat_engine import CombatEngine

    if attacker_kingdom.energy < 1:
        return await query.edit_message_text(
            "⚡ Energy kam hai!\n30 min mein regenerate hogi.",
            reply_markup=back_dashboard_keyboard(),
        )
    target = db.query(Kingdom).options(db.selectinload(Kingdom.army)).filter(Kingdom.user_id == target_id).first()
    if not target:
        return await query.edit_message_text("❌ Target not found!", reply_markup=attack_menu_keyboard())
    if target.has_shield:
        return await query.edit_message_text(
            "🛡 Target ke paas **Shield** hai!\nAttack nahi kar sakte.",
            parse_mode="Markdown",
            reply_markup=attack_menu_keyboard(),
        )

    # Consume energy
    attacker_kingdom.energy -= 1
    db.commit()

    # Run combat
    engine = CombatEngine(attacker_kingdom, target)
    result = engine.simulate_battle()

    # Apply losses
    if attacker_kingdom.army:
        attacker_kingdom.army.infantry = max(0, attacker_kingdom.army.infantry - result["attacker_losses"]["infantry"])
        attacker_kingdom.army.archers = max(0, attacker_kingdom.army.archers - result["attacker_losses"]["archers"])
        attacker_kingdom.army.cavalry = max(0, attacker_kingdom.army.cavalry - result["attacker_losses"]["cavalry"])
    if target.army:
        target.army.infantry = max(0, target.army.infantry - result["defender_losses"]["infantry"])
        target.army.archers = max(0, target.army.archers - result["defender_losses"]["archers"])
        target.army.cavalry = max(0, target.army.cavalry - result["defender_losses"]["cavalry"])

    # Loot
    gold_loot = result["gold_looted"]
    attacker_kingdom.gold += gold_loot
    attacker_kingdom.total_gold_earned = getattr(attacker_kingdom, "total_gold_earned", 0) + gold_loot
    target.gold = max(0, target.gold - gold_loot)

    # XP
    attacker_kingdom.xp += result["xp_gained"]
    xp_needed = EconomyService.calculate_xp_needed(attacker_kingdom.level)
    leveled_up = False
    while attacker_kingdom.xp >= xp_needed:
        attacker_kingdom.xp -= xp_needed
        attacker_kingdom.level += 1
        leveled_up = True
        xp_needed = EconomyService.calculate_xp_needed(attacker_kingdom.level)

    # Winner tracking
    winner_id = attacker_kingdom.user_id if result["winner"] == "attacker" else target_id
    if result["winner"] == "attacker":
        attacker_kingdom.battles_won = getattr(attacker_kingdom, "battles_won", 0) + 1

    # Save battle
    battle = Battle(
        attacker_id=attacker_kingdom.user_id,
        defender_id=target_id,
        winner_id=winner_id,
        battle_log=json.dumps(result["rounds"]),
        gold_looted=gold_loot,
        xp_gained=result["xp_gained"],
    )
    db.add(battle)
    db.commit()

    # Visual battle result
    outcome = "🏆 **VICTORY!**" if result["winner"] == "attacker" else "💀 **DEFEAT!**"
    level_msg = "\n🎉 **LEVEL UP!** 🎉" if leveled_up else ""
    attack_type = "⚡ Quick Raid" if raid else "⚔️ Battle"

    text = (
        f"{attack_type} Report\n\n"
        f"{outcome}{level_msg}\n\n"
        f"🏰 {attacker_kingdom.name}  vs  {target.name}\n\n"
        f"📊 **RESULTS:**\n"
        f"💰 Gold Looted: +{gold_loot}\n"
        f"📈 XP Gained: +{result['xp_gained']}\n\n"
        f"💀 **Your Losses:**\n"
        f"🗡 -{result['attacker_losses']['infantry']}  "
        f"🏹 -{result['attacker_losses']['archers']}  "
        f"🐎 -{result['attacker_losses']['cavalry']}\n\n"
        f"💀 **Enemy Losses:**\n"
        f"🗡 -{result['defender_losses']['infantry']}  "
        f"🏹 -{result['defender_losses']['archers']}  "
        f"🐎 -{result['defender_losses']['cavalry']}\n\n"
        f"⚡ Energy: {attacker_kingdom.energy}/{config.MAX_ENERGY}"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_dashboard_keyboard())


async def route_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle battle accept/decline."""
    query = update.callback_query
    data = query.data
    if data.startswith("battle_accept:"):
        # Manual battle request acceptance
        request_id = data.split(":")[1]
        await query.edit_message_text(f"✅ Battle request #{request_id} accepted! Feature expanding...")
    elif data.startswith("battle_decline:"):
        await query.edit_message_text("❌ Battle declined.", reply_markup=back_dashboard_keyboard())


async def route_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show building menu with visual upgrade progress."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        user = db.query(User).join(Kingdom).filter(User.telegram_id == user_id).first()
        if not user or not user.kingdom:
            return await query.edit_message_text("❌ Error!", reply_markup=back_dashboard_keyboard())
        buildings = db.query(Building).filter(Building.kingdom_id == user.kingdom.user_id).all()
        await query.edit_message_text(
            "🏗 **BUILDINGS**\n\nSelect building to manage:",
            parse_mode="Markdown",
            reply_markup=building_menu_keyboard(buildings),
        )


async def route_building(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle building actions: select, upgrade, collect, info."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    from bot.handlers.build import (
        view_building_detail, upgrade_building, collect_resources, building_info,
    )
    try:
        if data.startswith("building_select:"):
            building_type = data.split(":")[1]
            return await view_building_detail(update, context, building_type)
        elif data.startswith("building_upgrade:"):
            building_type = data.split(":")[1]
            return await upgrade_building(update, context, building_type)
        elif data.startswith("building_collect:"):
            building_type = data.split(":")[1]
            return await collect_resources(update, context, building_type)
        elif data.startswith("building_info:"):
            building_type = data.split(":")[1]
            return await building_info(update, context, building_type)
    except Exception as e:
        logger.error(f"Building error: {e}", exc_info=True)
        await query.edit_message_text("❌ Building action failed!", reply_markup=back_dashboard_keyboard())


async def route_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle map viewing and tile interactions."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    from bot.handlers.map_system import generate_map_view, handle_tile_click

    if data == "menu_map" or data == "map_view":
        # Generate visual map
        map_text = generate_map_view(user_id)
        await query.edit_message_text(map_text, parse_mode="Markdown", reply_markup=map_menu_keyboard())
    elif data.startswith("map_tile:"):
        _, x, y = data.split(":")
        return await handle_tile_click(update, context, int(x), int(y))
    elif data == "attack_map":
        # Redirect to attack menu from map
        return await route_attack(update, context)


async def route_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle alliance hub and actions."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    from bot.handlers.alliance import show_alliance_hub, create_alliance, join_alliance, leave_alliance

    try:
        if data == "menu_alliance":
            return await show_alliance_hub(update, context)
        elif data == "alliance_create":
            # Enter conversation flow for name input
            await query.edit_message_text(
                "🏰 **Create Alliance**\n\nAlliance ka naam batao (3-20 characters):",
                parse_mode="Markdown",
            )
            context.user_data[INPUT_ACTION] = "alliance_create_name"
            return
        elif data == "alliance_join":
            return await join_alliance(update, context)
        elif data.startswith("alliance_leave:"):
            alliance_id = int(data.split(":")[1])
            return await leave_alliance(update, context, alliance_id)
        elif data.startswith("alliance_members:"):
            alliance_id = int(data.split(":")[1])
            return await _show_alliance_members(update, context, alliance_id)
        elif data.startswith("alliance_donate:"):
            alliance_id = int(data.split(":")[1])
            return await _alliance_donate(update, context, alliance_id)
        elif data.startswith("alliance_invite:"):
            # Invite from map tile click
            target_id = int(data.split(":")[1])
            return await _alliance_invite_player(update, context, target_id)
        else:
            await query.edit_message_text("🤝 **Alliance Hub**:", reply_markup=alliance_hub_no_alliance_keyboard())
    except Exception as e:
        logger.error(f"Alliance error: {e}", exc_info=True)
        await query.edit_message_text("❌ Alliance action failed!", reply_markup=back_dashboard_keyboard())


async def _show_alliance_members(update: Update, context: ContextTypes.DEFAULT_TYPE, alliance_id: int):
    """Display alliance members with power chart."""
    query = update.callback_query
    with get_db() as db:
        from bot.models import Alliance
        alliance = db.query(Alliance).filter(Alliance.id == alliance_id).first()
        if not alliance:
            return await query.edit_message_text("Alliance not found!", reply_markup=back_dashboard_keyboard())
        members = db.query(Kingdom).filter(Kingdom.alliance_id == alliance_id).all()
        lines = [f"👥 **{alliance.name}** — Members\n"]
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        total_power = 0
        for i, m in enumerate(members, 1):
            power = EconomyService.calculate_kingdom_power(m) if m.army else 0
            total_power += power
            crown = "👑" if m.user_id == alliance.leader_id else "  "
            lines.append(f"{crown}{i}. {m.name} {m.flag} — ⚔ {power:,}")
        lines.append(f"\n📊 Total Power: **{total_power:,}**")
        lines.append(f"👥 Members: {len(members)}")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_alliance")],
        ])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)


async def _alliance_donate(update: Update, context: ContextTypes.DEFAULT_TYPE, alliance_id: int):
    """Donate gold to alliance with visual confirmation."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!", reply_markup=back_dashboard_keyboard())
        if k.gold < 100:
            return await query.edit_message_text(
                "💰 Minimum 100 gold chahiye donate karne ke liye!",
                reply_markup=back_dashboard_keyboard(),
            )
        donate_amount = min(500, k.gold)
        k.gold -= donate_amount
        db.commit()
        await query.edit_message_text(
            f"💰 **{donate_amount} Gold** donated to alliance!\n\n"
            f"Remaining: {k.gold} gold",
            parse_mode="Markdown",
            reply_markup=back_dashboard_keyboard(),
        )


async def _alliance_invite_player(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: int):
    """Send alliance invite to a player from map."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k or not k.alliance_id:
            return await query.edit_message_text(
                "❌ Aap kisi alliance mein nahi hain!",
                reply_markup=back_dashboard_keyboard(),
            )
        from bot.models import Alliance
        alliance = db.query(Alliance).filter(Alliance.id == k.alliance_id).first()
        target = db.query(Kingdom).filter(Kingdom.user_id == target_id).first()
        if not target:
            return await query.edit_message_text("❌ Player not found!")
        # Send invite notification
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🤝 **Alliance Invite!**\n\n{k.name} ne aapko **{alliance.name}** mein invite kiya!\n\n"
                     f"Alliance accept karne ke liye /start karo aur Alliance hub mein Join karo.",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"✅ Invite sent to **{target.name}**!",
            parse_mode="Markdown",
            reply_markup=back_dashboard_keyboard(),
        )


async def route_heroes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle hero menu and actions."""
    query = update.callback_query
    data = query.data
    from bot.handlers.heroes import show_heroes_hub, handle_hero_action

    if data == "menu_heroes":
        return await show_heroes_hub(update, context)
    elif data.startswith("hero_select:"):
        hero_type = data.split(":")[1]
        return await handle_hero_action(update, context, hero_type)
    elif data.startswith("hero_unlock:"):
        hero_type = data.split(":")[1]
        return await handle_hero_action(update, context, hero_type, action="unlock")
    elif data.startswith("hero_upgrade:"):
        hero_type = data.split(":")[1]
        return await handle_hero_action(update, context, hero_type, action="upgrade")
    elif data.startswith("skill_"):
        return await _show_skill_tree(update, context, data.replace("skill_", ""))


async def _show_skill_tree(update: Update, context: ContextTypes.DEFAULT_TYPE, tree_type: str):
    """Show skill tree with visual progress."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!", reply_markup=back_dashboard_keyboard())
        from bot.models import Hero
        hero = db.query(Hero).filter(Hero.kingdom_id == k.user_id, Hero.hero_type == "commander").first()
        if not hero:
            return await query.edit_message_text("❌ No hero found!", reply_markup=back_dashboard_keyboard())
        # Visual skill tree representation
        atk = hero.attack_bonus
        dfn = hero.defense_bonus
        eco = hero.economy_bonus
        skill_points = hero.skill_points
        skill_data = json.loads(hero.skill_tree) if hero.skill_tree else {}
        trees = {
            "attack": {"icon": "⚔️", "bonus": atk, "skills": ["Sword Mastery", "Charge", "Berserker", "War Cry"]},
            "defense": {"icon": "🛡", "bonus": dfn, "skills": ["Shield Wall", "Fortify", "Regen", "Last Stand"]},
            "economy": {"icon": "💰", "bonus": eco, "skills": ["Trade", "Harvest", "Tax", "Treasury"]},
        }
        info = trees.get(tree_type, trees["attack"])
        lines = [f"{info['icon']} **{tree_type.upper()} SKILL TREE**\n"]
        for skill in info["skills"]:
            unlocked = skill_data.get(skill, False)
            bar = render_bar(1 if unlocked else 0, 1, 6, "✦", "✧")
            lines.append(f"{bar} {skill} {'✅' if unlocked else '🔒'}")
        lines.append(f"\n📊 Bonus: +{info['bonus']:.1f}")
        lines.append(f"🎆 Skill Points: {skill_points}")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Heroes", callback_data="menu_heroes")],
        ])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)


async def route_spy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle spy menu and actions including spy from opponent screen."""
    query = update.callback_query
    data = query.data
    from bot.handlers.spy import show_spy_hub, send_spy

    if data == "menu_spy":
        return await show_spy_hub(update, context)
    elif data == "spy_send":
        return await send_spy(update, context)
    elif data == "spy_history":
        return await _show_spy_history(update, context)
    elif data.startswith("spy_player:"):
        target_id = int(data.split(":")[1])
        return await _spy_specific_target(update, context, target_id)


async def _spy_specific_target(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: int):
    """Spy on a specific target (from map or opponent screen)."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!", reply_markup=back_dashboard_keyboard())
        target = db.query(Kingdom).options(db.selectinload(Kingdom.army)).filter(Kingdom.user_id == target_id).first()
        if not target:
            return await query.edit_message_text("❌ Target not found!")
        # Spy logic
        gold_cost = 50
        if k.gold < gold_cost:
            return await query.edit_message_text(
                f"💰 {gold_cost} Gold chahiye spying ke liye!",
                reply_markup=back_dashboard_keyboard(),
            )
        # Check cooldown
        from bot.models import Cooldown
        cd = db.query(Cooldown).filter(Cooldown.user_id == user_id, Cooldown.action_type == "spy").first()
        if cd and cd.expires_at and cd.expires_at > datetime.utcnow():
            mins = int((cd.expires_at - datetime.utcnow()).total_seconds() / 60)
            return await query.edit_message_text(
                f"⏳ Spy cooldown! {mins} minutes wait karo.",
                reply_markup=back_dashboard_keyboard(),
            )
        k.gold -= gold_cost
        # Set cooldown
        if not cd:
            cd = Cooldown(user_id=user_id, action_type="spy", duration_minutes=5, expires_at=datetime.utcnow() + timedelta(minutes=5))
            db.add(cd)
        else:
            cd.expires_at = datetime.utcnow() + timedelta(minutes=5)
        # Generate spy report
        accuracy = min(0.95, 0.5 + (k.level * 0.05))
        report = SpyReport(
            spy_id=user_id,
            target_id=target_id,
            target_name=target.name,
            army_total=target.army.total if target.army else 0,
            infantry=target.army.infantry if target.army else 0,
            archers=target.army.archers if target.army else 0,
            cavalry=target.army.cavalry if target.army else 0,
            attack_power=int(target.army.attack_power * accuracy) if target.army else 0,
            defense_power=int(target.army.defense_power * accuracy) if target.army else 0,
            gold=int(target.gold * accuracy),
            food=int(target.food * accuracy),
            accuracy=accuracy,
        )
        db.add(report)
        db.commit()
        await query.edit_message_text(
            f"🕵️ **SPY REPORT on {target.name}**\n\n"
            f"📊 Accuracy: {int(accuracy * 100)}%\n\n"
            f"🪖 Army: ~{report.army_total} units\n"
            f"⚔ Attack: ~{report.attack_power}\n"
            f"🛡 Defense: ~{report.defense_power}\n"
            f"💰 Gold: ~{report.gold}\n"
            f"🍖 Food: ~{report.food}\n"
            f"🛡 Shield: {'Yes' if target.has_shield else 'No'}\n\n"
            f"⏳ Next spy in 5 min",
            parse_mode="Markdown",
            reply_markup=back_dashboard_keyboard(),
        )


async def _show_spy_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show spy history with visual timeline."""
    query = update.callback_query
    user_id = update.effective_user.id
    with get_db() as db:
        reports = db.query(SpyReport).filter(SpyReport.spy_id == user_id).order_by(SpyReport.timestamp.desc()).limit(5).all()
        if not reports:
            return await query.edit_message_text("📭 No spy reports yet!", reply_markup=back_dashboard_keyboard())
        lines = ["🕵️ **SPY HISTORY**\n"]
        for r in reports:
            time_ago = _time_ago(r.timestamp)
            lines.append(f"• {r.target_name} — ⚔~{r.attack_power} 💰~{r.gold} ({time_ago})")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_spy")],
        ])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)


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


async def route_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quest menu with visual progress bars."""
    query = update.callback_query
    data = query.data
    from bot.handlers.quests import show_quests, claim_quest_rewards

    if data == "menu_quests":
        return await show_quests(update, context)
    elif data == "quests_claim":
        return await claim_quest_rewards(update, context)


async def route_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show games menu."""
    query = update.callback_query
    await query.edit_message_text(
        "🎮 **MINI-GAMES**\n\nEntertainment ke liye games khelo!\nAur rewards jeeto!",
        parse_mode="Markdown",
        reply_markup=games_menu_keyboard(),
    )


async def route_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dice game with visual rolling animation."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")
        if data == "dice_bet":
            return await query.edit_message_text(
                "🎲 **DICE GAME**\n\nBet amount select karo:",
                parse_mode="Markdown",
                reply_markup=dice_keyboard(),
            )
        elif data.startswith("dice_bet:"):
            bet = int(data.split(":")[1])
            if k.gold < bet:
                return await query.edit_message_text(
                    f"💰 {bet} Gold nahi hai!\nAapke paas: {k.gold}",
                    reply_markup=games_menu_keyboard(),
                )
            # Roll dice
            player_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            if player_roll > bot_roll:
                winnings = bet
                k.gold += winnings
                result = f"🎉 **YOU WIN!**\n💰 +{winnings} Gold"
            elif player_roll < bot_roll:
                k.gold -= bet
                result = f"😢 **You Lose!**\n💰 -{bet} Gold"
            else:
                result = "🤝 **DRAW!**\nKoi loss nahi!"
            db.commit()
            # Visual dice representation
            dice_faces = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
            await query.edit_message_text(
                f"🎲 **DICE ROLL**\n\n"
                f"You:   {dice_faces.get(player_roll, player_roll)} ({player_roll})\n"
                f"Bot:   {dice_faces.get(bot_roll, bot_roll)} ({bot_roll})\n\n"
                f"{result}\n\n"
                f"💰 Balance: {k.gold}",
                parse_mode="Markdown",
                reply_markup=dice_keyboard(),
            )


async def route_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lucky spin with visual wheel."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data == "game_spin":
        return await query.edit_message_text(
            "🎰 **LUCKY SPIN**\n\nSpin karke prizes jeeto!\nCost: 50 Gold per spin",
            parse_mode="Markdown",
            reply_markup=spin_keyboard(),
        )
    elif data == "spin_wheel":
        with get_db() as db:
            k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if not k:
                return await query.edit_message_text("❌ Error!")
            if k.gold < 50:
                return await query.edit_message_text(
                    "💰 50 Gold chahiye spin ke liye!",
                    reply_markup=games_menu_keyboard(),
                )
            k.gold -= 50
            prizes = [
                ("💰 100 Gold", 100, "gold_add"), ("💰 200 Gold", 200, "gold_add"),
                ("🍖 50 Food", 50, "food_add"), ("🍖 150 Food", 150, "food_add"),
                ("⚡ 1 Energy", 1, "energy_add"), ("🏆 50 XP", 50, "xp_add"),
                ("💎 500 Gold", 500, "gold_add"), ("❌ Nothing", 0, "none"),
            ]
            weights = [20, 15, 15, 10, 10, 15, 5, 10]
            prize_name, amount, ptype = random.choices(prizes, weights=weights, k=1)[0]
            if ptype == "gold_add":
                k.gold += amount
            elif ptype == "food_add":
                k.food += amount
            elif ptype == "energy_add":
                k.energy = min(config.MAX_ENERGY, k.energy + amount)
            elif ptype == "xp_add":
                k.xp += amount
            db.commit()
            # Visual wheel
            wheel = "🎰\n ╔═══╗\n ║ {0} ║\n ╚═══╝".format(prize_name.split()[1] if len(prize_name.split()) > 1 else "🎁")
            await query.edit_message_text(
                f"{wheel}\n\n🎁 **Result: {prize_name}**!\n\n💰 Gold: {k.gold}\n🍖 Food: {k.food}",
                parse_mode="Markdown",
                reply_markup=spin_keyboard(),
            )


async def route_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kingdom quiz with questions and visual progress."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    questions = [
        {
            "q": "Medieval mein sabse powerful unit kaun thi?",
            "opts": ["Infantry", "Cavalry", "Archers", "Siege"],
            "ans": 1,
        },
        {
            "q": "Castle defense ke liye best building kaunsa hai?",
            "opts": ["Farm", "Wall", "Market", "Barracks"],
            "ans": 1,
        },
        {
            "q": "Gold collect karne ka sabse fast tareeka?",
            "opts": ["Attack", "Market", "Farm", "Casino"],
            "ans": 1,
        },
        {
            "q": "Spy mission ka cooldown kitna hai?",
            "opts": ["1 min", "5 min", "10 min", "30 min"],
            "ans": 1,
        },
        {
            "q": "Level 5 pe XP requirement kitni hai?",
            "opts": ["~400 XP", "~500 XP", "~600 XP", "~700 XP"],
            "ans": 1,
        },
    ]
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")
        if data == "game_quiz":
            context.user_data["quiz_idx"] = 0
            context.user_data["quiz_score"] = 0
            return await _show_quiz_question(update, context, questions[0], 0)
        elif data.startswith("quiz_answer:"):
            _, q_idx, ans = data.split(":")
            q_idx = int(q_idx)
            ans = int(ans)
            correct = questions[q_idx]["ans"]
            if ans == correct:
                context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
                result = "✅ Correct! +10 XP"
                k.xp += 10
            else:
                result = f"❌ Wrong! Answer: {questions[q_idx]['opts'][correct]}"
            db.commit()
            next_idx = q_idx + 1
            if next_idx >= len(questions):
                score = context.user_data.get("quiz_score", 0)
                bonus = score * 20
                k.gold += bonus
                db.commit()
                await query.edit_message_text(
                    f"🧠 **QUIZ COMPLETE!**\n\n"
                    f"Score: {score}/{len(questions)}\n"
                    f"🎁 Bonus: +{bonus} Gold!\n\n"
                    f"{render_xp_bar(k.xp, EconomyService.calculate_xp_needed(k.level))}\n\n"
                    f"💰 Gold: {k.gold}",
                    parse_mode="Markdown",
                    reply_markup=games_menu_keyboard(),
                )
                return
            await query.answer(result, show_alert=True)
            return await _show_quiz_question(update, context, questions[next_idx], next_idx)


async def _show_quiz_question(update, context, question, idx):
    """Display a quiz question."""
    query = update.callback_query
    score = context.user_data.get("quiz_score", 0)
    total = idx
    from bot.utils.keyboards import quiz_keyboard
    await query.edit_message_text(
        f"🧠 **Kingdom Quiz** ({total}/5)\n"
        f"Score: {score} ✅\n\n"
        f"{idx + 1}. {question['q']}",
        parse_mode="Markdown",
        reply_markup=quiz_keyboard(idx, question["opts"]),
    )


async def route_survival(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Survival mode - wave-based defense game."""
    query = update.callback_query
    user_id = update.effective_user.id
    if data := query.data:
        if data == "game_survival":
            with get_db() as db:
                k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
                if not k:
                    return await query.edit_message_text("❌ Error!")
                army_total = k.army.total if k.army else 0
                if army_total < 10:
                    return await query.edit_message_text(
                        "🛡 Survival mode ke liye minimum 10 units chahiye!\n"
                        "Barracks se train karo!",
                        reply_markup=games_menu_keyboard(),
                    )
                # Initialize survival mode
                wave = 1
                enemy_count = 5
                result_lines = ["⚔️ **SURVIVAL MODE**\n"]
                my_power = k.army.attack_power if k.army else 0
                my_def = k.army.defense_power if k.army else 0
                while wave <= 5:
                    enemy_power = int(50 * wave * 1.5)
                    enemy_def = int(30 * wave)
                    # Simple combat calc
                    my_dmg = max(0, my_power - enemy_def)
                    enemy_dmg = max(0, enemy_power - my_def)
                    won = my_dmg > enemy_dmg
                    icon = "🏆" if won else "💀"
                    result_lines.append(f"Wave {wave}: {icon} Enemy Power {enemy_power}")
                    if not won:
                        # Losses
                        if k.army:
                            loss = int(k.army.total * 0.1)
                            k.army.infantry = max(0, k.army.infantry - loss)
                        break
                    wave += 1
                reward_gold = (wave - 1) * 100
                k.gold += reward_gold
                db.commit()
                result_lines.append(f"\n💰 Reward: +{reward_gold} Gold\n")
                result_lines.append(f"Survived: {wave - 1}/5 waves")
                await query.edit_message_text(
                    "\n".join(result_lines),
                    parse_mode="Markdown",
                    reply_markup=games_menu_keyboard(),
                )


async def route_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Black market with proper item selection."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")
        if data == "market_buy":
            items = [
                {"name": "⚔️ Sword of Power", "cost": 300, "boost": {"attack": 50}},
                {"name": "🛡 Shield of Kings", "cost": 250, "boost": {"defense": 40}},
                {"name": "🍖 Feast Basket", "cost": 100, "boost": {"food": 200}},
                {"name": "📜 XP Scroll", "cost": 200, "boost": {"xp": 100}},
                {"name": "⚡ Energy Potion", "cost": 150, "boost": {"energy": 2}},
            ]
            # Store in user_data for consistent selection
            context.user_data["market_items"] = {str(i): item for i, item in enumerate(items)}
            lines = ["🖤 **BLACK MARKET**\n\nSelect item to buy:\n"]
            buttons = []
            for i, item in items:
                lines.append(f"{i + 1}. {item['name']} — 💰 {item['cost']}")
                buttons.append([InlineKeyboardButton(f"Buy {item['name']}", callback_data=f"market_item:{i}")])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_games")])
            await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("market_item:"):
            item_idx = data.split(":")[1]
            items = context.user_data.get("market_items", {})
            item = items.get(item_idx)
            if not item:
                return await query.edit_message_text("❌ Item not found!", reply_markup=back_dashboard_keyboard())
            if k.gold < item["cost"]:
                return await query.edit_message_text(
                    f"💰 {item['cost']} Gold chahiye!",
                    reply_markup=back_dashboard_keyboard(),
                )
            k.gold -= item["cost"]
            boost = item["boost"]
            for key, val in boost.items():
                if key == "attack" and k.army:
                    k.army.infantry += 5
                elif key == "defense" and k.army:
                    pass  # Defense is calculated
                elif key == "food":
                    k.food += val
                elif key == "xp":
                    k.xp += val
                elif key == "energy":
                    k.energy = min(config.MAX_ENERGY, k.energy + val)
            db.commit()
            await query.edit_message_text(
                f"✅ **{item['name']}** khareeda!\n\n💰 Remaining: {k.gold}",
                parse_mode="Markdown",
                reply_markup=games_menu_keyboard(),
            )


async def route_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leaderboard with visual ranking chart."""
    query = update.callback_query
    data = query.data
    with get_db() as db:
        if data == "menu_leaderboard":
            await query.edit_message_text(
                "🏆 **LEADERBOARD**\n\nTop players dekhne ke liye select karo:",
                parse_mode="Markdown",
                reply_markup=leaderboard_keyboard(),
            )
        elif data == "lb_players":
            kingdoms = db.query(Kingdom).options(db.selectinload(Kingdom.army)).all()
            sorted_k = sorted(kingdoms, key=lambda x: EconomyService.calculate_kingdom_power(x), reverse=True)[:10]
            lines = ["🏆 **TOP PLAYERS**\n"]
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for i, k in enumerate(sorted_k):
                power = EconomyService.calculate_kingdom_power(k)
                medal = medals[i] if i < len(medals) else f"{i + 1}."
                bar = render_bar(power, sorted_k[0] and EconomyService.calculate_kingdom_power(sorted_k[0]) or 1, 10)
                lines.append(f"{medal} {k.name} {k.flag} — ⚔ {power:,}\n    {bar}")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="menu_leaderboard")],
            ])
            await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)
        elif data == "lb_alliances":
            from bot.models import Alliance
            alliances = db.query(Alliance).all()
            lines = ["🏆 **TOP ALLIANCES**\n"]
            for i, a in enumerate(alliances[:10], 1):
                members = db.query(Kingdom).filter(Kingdom.alliance_id == a.id).count()
                lines.append(f"{i}. {a.name} — 👥 {members} members")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="menu_leaderboard")],
            ])
            await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)


async def route_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    query = update.callback_query
    await query.edit_message_text(
        "⚙️ **SETTINGS**\n\nCustomize your experience:",
        parse_mode="Markdown",
        reply_markup=settings_keyboard(),
    )


async def route_settings_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings detail views."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    with get_db() as db:
        prefs = db.query(NotificationPref).filter(NotificationPref.user_id == user_id).first()
        if data == "settings_notif":
            if not prefs:
                prefs = NotificationPref(user_id=user_id)
                db.add(prefs)
                db.commit()
            await query.edit_message_text(
                "🔔 **Notification Settings**\n\nToggle notifications:",
                parse_mode="Markdown",
                reply_markup=notification_settings_keyboard(prefs),
            )
        elif data == "settings_title":
            await query.edit_message_text(
                "🏷 **Change Title**\n\nNaya title batao:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu_settings")]]),
            )
            context.user_data[INPUT_ACTION] = "change_title"
        elif data == "settings_lang":
            await query.edit_message_text(
                "🌐 **Language**\n\nCurrently: English\n\nAur languages jald aa rahi hain!",
                reply_markup=back_dashboard_keyboard(),
            )
        elif data == "settings_help":
            return await _show_help(update, context)


async def route_toggle_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle notification settings."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    toggle_map = {
        "toggle_battle": "battle_alerts",
        "toggle_energy": "energy_full",
        "toggle_resource": "resource_full",
        "toggle_building": "building_complete",
        "toggle_alliance": "alliance_events",
        "toggle_bounty": "bounty_alerts",
        "toggle_promo": "promotions",
    }
    field = toggle_map.get(data)
    if not field:
        return await query.answer("Unknown toggle!")
    with get_db() as db:
        prefs = db.query(NotificationPref).filter(NotificationPref.user_id == user_id).first()
        if not prefs:
            prefs = NotificationPref(user_id=user_id)
            db.add(prefs)
        current = getattr(prefs, field, False)
        setattr(prefs, field, not current)
        db.commit()
        await query.edit_message_text(
            "🔔 **Notification Settings**\n\nToggle notifications:",
            parse_mode="Markdown",
            reply_markup=notification_settings_keyboard(prefs),
        )


async def _show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive help guide."""
    query = update.callback_query
    help_text = (
        "📖 **HOW TO PLAY — King-Maker**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 **GOAL**: Apna Kingdom build karo, dushmano ko harao,\n"
        "    aur **#1 King** bano!\n\n"
        "⚔️ **ATTACK**:\n"
        "  • Find Opponent — Similar power wale opponents\n"
        "  • Quick Raid — Fast attack kamzor target pe\n"
        "  • Revenge — Jo aapko haraaye, unse badla lo!\n\n"
        "🏗 **BUILDINGS**:\n"
        "  • Town Hall — Level up se aur features unlock\n"
        "  • Barracks — Army train karo\n"
        "  • Farm — Food production\n"
        "  • Gold Mine — Gold production\n"
        "  • Wall — Defense boost\n"
        "  • Market — Resource trading\n\n"
        "🪖 **ARMY**: 🗡 Infantry, 🏹 Archers, 🐎 Cavalry\n"
        "   Barracks se train karo, attack mein use karo!\n\n"
        "🤝 **ALLIANCE**:\n"
        "   Doston ke saath alliance banao,\n"
        "   milkar dushmano se lado!\n\n"
        "🕵️ **SPY**:\n"
        "   Dushman ki info collect karo —\n"
        "   army size, resources, shield status!\n\n"
        "🎮 **MINI-GAMES**: Dice, Spin, Quiz, Survival\n"
        "   Games khelo, rewards jeeto!\n\n"
        "📊 **TIPS**:\n"
        "  • Food collect karo — army bhooki maregi!\n"
        "  • Shield active rakho — protection from attacks\n"
        "  • Daily quests complete karo — free rewards\n"
        "  • Alliance donate karo — teamwork matters!\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Commands: /start /help /dashboard"
    )
    await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=back_dashboard_keyboard())


async def route_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bounty system."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    with get_db() as db:
        if data == "menu_bounty":
            # Show active bounties
            active = db.query(Bounty).filter(Bounty.is_active == True).order_by(Bounty.reward.desc()).limit(5).all()
            lines = ["🎯 **BOUNTY BOARD**\n"]
            if not active:
                lines.append("📭 No active bounties!\n")
            else:
                for b in active:
                    lines.append(f"💰 {b.reward} Gold — Target: {b.target_name}\n   Placed by: Unknown")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Place Bounty", callback_data="bounty_place")],
                [InlineKeyboardButton("⚔️ Accept Bounty", callback_data="bounty_accept")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
            ])
            await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)
        elif data == "bounty_place":
            await query.edit_message_text(
                "🎯 **Place Bounty**\n\n"
                "Target ka Telegram ID ya Kingdom name batao:\n"
                "(Feature expanding...)",
                reply_markup=back_dashboard_keyboard(),
            )
        elif data == "bounty_accept":
            await query.edit_message_text(
                "⚔️ **Accept Bounty**\n\n"
                "Bounty target ko defeat karo aur reward paao!\n"
                "(Feature expanding...)",
                reply_markup=back_dashboard_keyboard(),
            )


async def route_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle decision event choices."""
    query = update.callback_query
    data = query.data
    parts = data.split(":")
    if len(parts) < 3:
        return await query.answer("Invalid decision!")
    event_id, choice = parts[1], parts[2]
    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")
        # Process choice effects
        outcomes = {
            "A": {"gold": 100, "msg": "💰 Aapne gold invest kiya! +100 Gold"},
            "B": {"attack": True, "msg": "⚔️ Aapne attack kiya! Victory mila!"},
            "C": {"shield": True, "msg": "🛡 Aapne defense choose kiya! Safe rahe!"},
        }
        outcome = outcomes.get(choice, outcomes["C"])
        if "gold" in outcome:
            k.gold += outcome["gold"]
        if "shield" in outcome:
            k.shield_expires = datetime.utcnow() + timedelta(hours=2)
        db.commit()
        await query.edit_message_text(
            f"🎲 **Decision Made!**\n\n{outcome['msg']}\n\n"
            f"💰 Gold: {k.gold}",
            parse_mode="Markdown",
            reply_markup=back_dashboard_keyboard(),
        )


async def route_trait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trait selection during kingdom creation."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    trait = data.split(":")[1]
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Kingdom not found!")
        # Apply trait bonuses
        traits = {
            "aggressive": {"attack": 20, "infantry": 10},
            "defensive": {"defense": 20, "wall": True},
            "rich": {"gold": 300},
            "balanced": {"gold": 100, "infantry": 5, "food": 100},
        }
        t = traits.get(trait, traits["balanced"])
        if "gold" in t:
            k.gold += t["gold"]
        if "infantry" in t and k.army:
            k.army.infantry += t["infantry"]
        if "food" in t:
            k.food += t["food"]
        db.commit()
        trait_names = {"aggressive": "⚔️ Aggressive", "defensive": "🛡 Defensive", "rich": "💰 Rich", "balanced": "⚖️ Balanced"}
        await query.edit_message_text(
            f"✅ **Trait Selected: {trait_names.get(trait, trait)}**!\n\n"
            f"Kingdom ban gaya hai!\n\n"
            f"🏰 {k.name} {k.flag}\n"
            f"🎖 Level: {k.level}\n"
            f"💰 Gold: {k.gold}\n"
            f"🍖 Food: {k.food}\n\n"
            f"Dashboard khul raha hai...",
            parse_mode="Markdown",
        )
        # Show dashboard after a moment
        await show_dashboard(update, context)


# ═══════════════════════════════════════════════════════════════════
#  TEXT INPUT HANDLER
# ═══════════════════════════════════════════════════════════════════


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text inputs — title change, alliance creation, search, etc."""
    user_id = update.effective_user.id
    action = context.user_data.get(INPUT_ACTION)
    text = update.message.text.strip()

    if action == "change_title":
        # Validate and update title
        valid, error = validate_kingdom_name(text)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        with get_db() as db:
            k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if k:
                k.name = text
                db.commit()
                await update.message.reply_text(
                    f"✅ Kingdom name changed to **{text}**!",
                    parse_mode="Markdown",
                    reply_markup=back_dashboard_keyboard(),
                )
        context.user_data.pop(INPUT_ACTION, None)

    elif action == "alliance_create_name":
        from bot.utils.validators import validate_alliance_name
        valid, error = validate_alliance_name(text)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        with get_db() as db:
            k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if not k:
                await update.message.reply_text("❌ Kingdom nahi mila!")
                return
            if k.alliance_id:
                await update.message.reply_text("❌ Aap pehle se alliance mein hain!")
                return
            from bot.models import Alliance
            alliance = Alliance(name=text, leader_id=user_id, total_power=0)
            db.add(alliance)
            db.commit()
            db.refresh(alliance)
            k.alliance_id = alliance.id
            db.commit()
            await update.message.reply_text(
                f"🏰 **Alliance '{text}'** successfully create ho gaya!\n\n"
                f"Ab doston ko invite karo!",
                parse_mode="Markdown",
                reply_markup=back_dashboard_keyboard(),
            )
        context.user_data.pop(INPUT_ACTION, None)

    elif action == "spy_target_search":
        # Search for kingdom by name
        with get_db() as db:
            target = db.query(Kingdom).filter(Kingdom.name.ilike(f"%{text}%")).first()
            if not target:
                await update.message.reply_text(
                    f"🔍 '{text}' naam ka koi kingdom nahi mila!",
                    reply_markup=back_dashboard_keyboard(),
                )
                return
            return await _spy_specific_target(update, context, target.user_id)

    else:
        await update.message.reply_text(
            "❓ Main menu se option select karo.",
            reply_markup=back_dashboard_keyboard(),
        )


# ═══════════════════════════════════════════════════════════════════
#  ARMY TRAIN CALLBACK (Direct, not via router)
# ═══════════════════════════════════════════════════════════════════


async def handle_train_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle army training with visual confirmation."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    unit_map = {
        "train_infantry": ("infantry", 5, 10, 5),
        "train_archers": ("archers", 5, 15, 5),
        "train_cavalry": ("cavalry", 5, 25, 10),
    }
    unit_info = unit_map.get(data)
    if not unit_info:
        return await query.answer("Unknown unit!")

    unit_type, qty, food_cost, gold_cost = unit_info
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")
        if k.food < food_cost:
            return await query.edit_message_text(
                f"🍖 {food_cost} Food chahiye!\nAapke paas: {k.food}",
                reply_markup=army_menu_keyboard(),
            )
        if k.gold < gold_cost:
            return await query.edit_message_text(
                f"💰 {gold_cost} Gold chahiye!\nAapke paas: {k.gold}",
                reply_markup=army_menu_keyboard(),
            )
        # Train army
        if not k.army:
            k.army = Army(kingdom_id=user_id, infantry=0, archers=0, cavalry=0)
            db.add(k.army)
            db.flush()
        if unit_type == "infantry":
            k.army.infantry += qty
        elif unit_type == "archers":
            k.army.archers += qty
        elif unit_type == "cavalry":
            k.army.cavalry += qty
        k.food -= food_cost
        k.gold -= gold_cost
        k.xp += 2
        db.commit()
        # Visual progress
        total = k.army.total if k.army else 0
        bar = render_bar(total, 200, 12)
        await query.edit_message_text(
            f"✅ **+{qty} {unit_type.capitalize()}** trained!\n\n"
            f"🪖 Total Army: {total}\n"
            f"{bar}\n\n"
            f"🍖 Food: {k.food}  |  💰 Gold: {k.gold}",
            parse_mode="Markdown",
            reply_markup=army_menu_keyboard(),
        )


# ═══════════════════════════════════════════════════════════════════
#  CONVERSATION HANDLER — Kingdom Creation
# ═══════════════════════════════════════════════════════════════════


async def conv_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conversation: get kingdom name."""
    name = update.message.text.strip()
    valid, error = validate_kingdom_name(name)
    if not valid:
        await update.message.reply_text(f"❌ {error}\n\nDobara try karo:")
        return NAME
    context.user_data["kingdom_name"] = name
    await update.message.reply_text(
        f"✅ **{name}** — mast naam hai!\n\n"
        "Ab apna **Trait** select karo:\n\n"
        "⚔️ **Aggressive** — +Attack bonus\n"
        "🛡 **Defensive** — +Defense bonus\n"
        "💰 **Rich** — +Starting Gold\n"
        "⚖️ **Balanced** — Small bonus to all",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Aggressive", callback_data="trait:aggressive")],
            [InlineKeyboardButton("🛡 Defensive", callback_data="trait:defensive")],
            [InlineKeyboardButton("💰 Rich", callback_data="trait:rich")],
            [InlineKeyboardButton("⚖️ Balanced", callback_data="trait:balanced")],
        ]),
    )
    return TRAIT


async def conv_trait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conversation: trait selected, finalize kingdom."""
    query = update.callback_query
    await query.answer()
    # Handled by route_trait now
    return ConversationHandler.END


async def conv_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation."""
    await update.message.reply_text("❌ Setup cancelled. /start se dobara shuru karo.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════
#  ERROR HANDLER
# ═══════════════════════════════════════════════════════════════════


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler with graceful recovery."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ **Oops! Kuch galat ho gaya.**\n\n"
                "Developers ne error log kar liya hai.\n"
                "Please /start se dobara try karo.",
                parse_mode="Markdown",
            )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ═══════════════════════════════════════════════════════════════════


def main():
    """Build and run the bot."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # ── Conversation: Kingdom Creation ────────────────────────
    create_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_command, pattern="^start_game$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, conv_name)],
            TRAIT: [CallbackQueryHandler(conv_trait, pattern="^trait:")],
        },
        fallbacks=[CommandHandler("cancel", conv_cancel)],
    )

    # ── Handlers ──────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("dashboard", show_dashboard))
    app.add_handler(create_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # ── Army training callbacks ───────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_train_callback, pattern="^train_"))

    # ── Error handling ────────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Background tasks ──────────────────────────────────────
    from bot.tasks.scheduler import setup_scheduler
    setup_scheduler(app)

    logger.info("🤴 King-Maker Bot (Elite Edition) started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
