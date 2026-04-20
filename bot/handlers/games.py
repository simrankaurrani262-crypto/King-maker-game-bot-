"""
Mini-Games Handler - Dice, Spin Wheel, Quiz, Survival, Black Market.
Fixed version with all game logic complete.
"""

import random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.models import get_db, Kingdom, Army
from bot.services.game_data import GameData
from bot.utils.keyboards import (
    games_menu_keyboard,
    dice_keyboard,
    spin_keyboard,
    quiz_keyboard,
    black_market_keyboard,
    back_dashboard_keyboard,
)
from bot.utils.constants import (
    DICE_COOLDOWN_HOURS,
    SPIN_COOLDOWN_HOURS,
    QUIZ_COOLDOWN_HOURS,
    QUIZ_QUESTIONS,
    BLACK_MARKET_ITEMS,
    SPIN_WHEEL_ITEMS,
    SURVIVAL_WAVES,
)


# ─── Quiz Session Tracking ───
class QuizSession:
    """Track a user's quiz session"""
    def __init__(self, question_index, answer_index):
        self.question_index = question_index
        self.answer_index = answer_index
        self.asked_at = datetime.utcnow()


# Module-level storage for active quiz sessions
quiz_sessions = {}


# ═══════════════════════════════════════════
# GAMES MENU
# ═══════════════════════════════════════════

async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, new_message: bool = False):
    """Show mini-games menu"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        text = "❌ Kingdom not found!"
        if query and not new_message:
            await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_dashboard_keyboard())
        return

    text = (
        "🎮 **MINI-GAMES**\n"
        "━━━━━━━━━━━━━━\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n"
        f"💎 Gems: {getattr(kingdom, 'gems', 0):,}\n\n"
        "Games khelo aur rewards jeeto!\n\n"
        "🎲 **Dice Game** - Lucky roll se jeeto\n"
        "🎰 **Lucky Spin** - Daily free spin\n"
        "🧠 **Kingdom Quiz** - Knowledge test\n"
        "⚔️ **Survival Mode** - Wave defense\n"
        "🏪 **Black Market** - Special items"
    )

    if query and not new_message:
        await query.edit_message_text(text, reply_markup=games_menu_keyboard())
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=games_menu_keyboard())


# ═══════════════════════════════════════════
# DICE GAME
# ═══════════════════════════════════════════

async def show_dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show dice game menu"""
    query = update.callback_query

    # Check cooldown
    last_played = GameData.get_cooldown(user_id, "dice")
    if last_played:
        elapsed = datetime.utcnow() - last_played
        if elapsed < timedelta(hours=DICE_COOLDOWN_HOURS):
            remaining = timedelta(hours=DICE_COOLDOWN_HOURS) - elapsed
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await query.answer(f"⏳ {hours}h {minutes}m cooldown remaining!", show_alert=True)
            return

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    text = (
        "🎲 **DICE GAME**\n"
        "━━━━━━━━━━━━━━\n"
        f"💰 Gold: {getattr(kingdom, 'gold', 0):,}\n\n"
        "Apna bet choose karo:\n"
        "🎲 Roll karo, 4-6 = Double Gold return!\n"
        "1-3 = Gold lost...\n\n"
        f"⏳ Cooldown: {DICE_COOLDOWN_HOURS} hours"
    )

    await query.edit_message_text(text, reply_markup=dice_keyboard())


async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet: int):
    """Roll the dice"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom or getattr(kingdom, 'gold', 0) < bet:
        await query.answer("❌ Not enough Gold!", show_alert=True)
        return

    # Deduct bet
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k or k.gold < bet:
            await query.answer("❌ Not enough Gold!", show_alert=True)
            return
        k.gold -= bet
        db.commit()

    # Roll animation
    await query.edit_message_text("🎲 Rolling dice... 🎲")
    import asyncio
    await asyncio.sleep(1)

    roll = random.randint(1, 6)

    if roll >= 4:
        winnings = bet * 2
        with get_db() as db:
            k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            k.gold += winnings
            db.commit()

        text = (
            f"🎲 **DICE ROLLED: {roll}**\n"
            "━━━━━━━━━━━━━━\n"
            "🎉 **YOU WIN!**\n"
            f"💰 +{winnings:,} Gold!"
        )
    else:
        text = (
            f"🎲 **DICE ROLLED: {roll}**\n"
            "━━━━━━━━━━━━━━\n"
            "😢 **You lose...**\n"
            f"💰 -{bet:,} Gold"
        )

    # Set cooldown
    GameData.set_cooldown(user_id, "dice")

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


# ═══════════════════════════════════════════
# SPIN WHEEL
# ═══════════════════════════════════════════

async def show_spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show lucky spin wheel"""
    query = update.callback_query

    # Check cooldown
    last_played = GameData.get_cooldown(user_id, "spin")
    if last_played:
        elapsed = datetime.utcnow() - last_played
        if elapsed < timedelta(hours=SPIN_COOLDOWN_HOURS):
            remaining = timedelta(hours=SPIN_COOLDOWN_HOURS) - elapsed
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await query.answer(f"⏳ {hours}h {minutes}m remaining!", show_alert=True)
            return

    text = (
        "🎰 **LUCKY SPIN**\n"
        "━━━━━━━━━━━━━━\n\n"
        "SPIN karo aur jeeto:\n"
        "• 💎 50 Gems (5%)\n"
        "• 💰 5000 Gold (15%)\n"
        "• 🍖 2000 Food (20%)\n"
        "• ⚡ Full Energy (20%)\n"
        "• 🛡 12h Shield (15%)\n"
        "• 🎁 Mystery Box (10%)\n"
        "• ❌ Nothing (15%)\n\n"
        f"⏳ Next free spin: {SPIN_COOLDOWN_HOURS}h"
    )

    await query.edit_message_text(text, reply_markup=spin_keyboard())


async def spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Spin the wheel"""
    query = update.callback_query

    # Spin animation
    await query.edit_message_text("🎰 Spinning... 🎰")
    import asyncio
    await asyncio.sleep(2)

    # Weighted random selection
    items = SPIN_WHEEL_ITEMS
    r = random.random()
    cumulative = 0
    selected = items[-1]  # default to last

    for item in items:
        cumulative += item.get("chance", 0)
        if r <= cumulative:
            selected = item
            break

    # Apply reward
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return

        reward_text = ""

        if selected.get("gems"):
            kingdom.gems += selected["gems"]
            reward_text = f"💎 +{selected['gems']} Gems!"
        elif selected.get("gold"):
            kingdom.gold += selected["gold"]
            reward_text = f"💰 +{selected['gold']:,} Gold!"
        elif selected.get("food"):
            kingdom.food += selected["food"]
            reward_text = f"🍖 +{selected['food']:,} Food!"
        elif selected.get("energy"):
            kingdom.energy = min(10, getattr(kingdom, 'energy', 0) + selected["energy"])
            reward_text = "⚡ Full Energy Refill!"
        elif selected.get("shield_hours"):
            kingdom.shield_expires = datetime.utcnow() + timedelta(hours=selected["shield_hours"])
            reward_text = f"🛡 +{selected['shield_hours']}h Shield!"
        elif selected.get("mystery"):
            mystery_reward = random.choice([
                ("gold", 1000, "💰"),
                ("gems", 10, "💎"),
                ("food", 500, "🍖"),
            ])
            attr, amount, emoji = mystery_reward
            setattr(kingdom, attr, getattr(kingdom, attr, 0) + amount)
            reward_text = f"{emoji} Mystery Reward: +{amount:,} {attr.title()}!"
        elif selected.get("nothing"):
            reward_text = "Kuch nahi mila... Better luck next time!"

        db.commit()

    # Set cooldown
    GameData.set_cooldown(user_id, "spin")

    text = (
        f"🎰 **SPIN RESULT**\n"
        "━━━━━━━━━━━━━━\n"
        f"🎁 {selected['name']}\n"
        f"{reward_text}"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


# ═══════════════════════════════════════════
# QUIZ GAME
# ═══════════════════════════════════════════

async def show_quiz_game(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show quiz game"""
    query = update.callback_query

    # Check cooldown
    last_played = GameData.get_cooldown(user_id, "quiz")
    if last_played:
        elapsed = datetime.utcnow() - last_played
        if elapsed < timedelta(hours=QUIZ_COOLDOWN_HOURS):
            remaining = timedelta(hours=QUIZ_COOLDOWN_HOURS) - elapsed
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await query.answer(f"⏳ {hours}h {minutes}m remaining!", show_alert=True)
            return

    # Select random question
    q_idx = random.randint(0, len(QUIZ_QUESTIONS) - 1)
    question = QUIZ_QUESTIONS[q_idx]

    # Store session
    quiz_sessions[user_id] = QuizSession(q_idx, question["correct"])

    text = (
        "🧠 **KINGDOM QUIZ**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"❓ {question['question']}\n\n"
        "Sahi answer choose karo!"
    )

    await query.edit_message_text(
        text,
        reply_markup=quiz_keyboard(q_idx, question["options"])
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, q_idx: int, answer: int):
    """Handle quiz answer"""
    query = update.callback_query

    # Validate session
    session = quiz_sessions.get(user_id)
    if not session or session.question_index != q_idx:
        await query.answer("❌ Session expired!", show_alert=True)
        return

    question = QUIZ_QUESTIONS[q_idx]
    is_correct = (answer == question["correct"])

    # Clear session
    quiz_sessions.pop(user_id, None)

    # Set cooldown regardless of result
    GameData.set_cooldown(user_id, "quiz")

    if is_correct:
        reward = random.choice([
            ("gold", 500, "💰"),
            ("gems", 5, "💎"),
            ("food", 300, "🍖"),
        ])

        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                attr, amount, emoji = reward
                setattr(kingdom, attr, getattr(kingdom, attr, 0) + amount)
                db.commit()

        text = (
            "✅ **CORRECT!**\n"
            "━━━━━━━━━━━━━━\n"
            f"{emoji} +{amount:,} {attr.title()}!\n"
            "🧠 Smart player!"
        )
    else:
        correct_option = question["options"][question["correct"]]
        text = (
            "❌ **Wrong Answer!**\n"
            "━━━━━━━━━━━━━━\n"
            f"Correct answer: **{correct_option}**\n"
            "🧠 Try again next time!"
        )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


# ═══════════════════════════════════════════
# SURVIVAL MODE
# ═══════════════════════════════════════════

async def show_survival_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show survival mode menu"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    army = getattr(kingdom, 'army', None)
    total_army = (getattr(army, 'infantry', 0) +
                  getattr(army, 'archers', 0) +
                  getattr(army, 'cavalry', 0))

    text = (
        "⚔️ **SURVIVAL MODE**\n"
        "━━━━━━━━━━━━━━\n"
        f"⚔️ Your Army: {total_army:,}\n"
        f"⚡ Energy: {getattr(kingdom, 'energy', 0)}/10\n\n"
        "5 waves of enemies face karo!\n"
        "Har wave ke baad reward milta hai.\n\n"
        "**Rewards:**\n"
    )
    for wave in SURVIVAL_WAVES:
        text += f"  Wave {wave['wave']}: {wave['reward_gold']:,} Gold\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ START!", callback_data="survival_start")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])

    await query.edit_message_text(text, reply_markup=keyboard)


async def start_survival(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start survival mode"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    if getattr(kingdom, 'energy', 0) < 1:
        await query.answer("❌ Not enough Energy!", show_alert=True)
        return

    # Store survival state in user_data
    context.user_data["survival_wave"] = 1
    context.user_data["survival_reward"] = 0

    await _run_survival_wave(update, context, user_id)


async def next_survival_wave(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Continue to next wave"""
    wave = context.user_data.get("survival_wave", 1)
    if wave <= 5:
        await _run_survival_wave(update, context, user_id)
    else:
        # All waves complete - claim reward
        total_reward = context.user_data.get("survival_reward", 0)

        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                kingdom.gold += total_reward
                db.commit()

        text = (
            "🏆 **SURVIVAL COMPLETE!**\n"
            "━━━━━━━━━━━━━━\n"
            f"💰 Total Reward: {total_reward:,} Gold!\n"
            "🎉 All 5 waves defeated!"
        )

        # Clear survival data
        context.user_data.pop("survival_wave", None)
        context.user_data.pop("survival_reward", None)

        query = update.callback_query
        await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


async def _run_survival_wave(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Run a single survival wave"""
    query = update.callback_query

    wave_num = context.user_data.get("survival_wave", 1)
    wave_data = SURVIVAL_WAVES[wave_num - 1]

    kingdom = GameData.get_kingdom_with_relations(user_id)
    army = getattr(kingdom, 'army', None)
    total_army = (getattr(army, 'infantry', 0) +
                  getattr(army, 'archers', 0) +
                  getattr(army, 'cavalry', 0))

    # Simple combat calculation
    enemy_count = wave_data["enemies"]
    player_power = total_army * 10
    enemy_power = enemy_count * 5

    # Random factor
    player_power = int(player_power * random.uniform(0.9, 1.1))

    if player_power >= enemy_power:
        # Victory
        reward = wave_data["reward_gold"]
        context.user_data["survival_reward"] = context.user_data.get("survival_reward", 0) + reward

        # Small army losses
        losses = max(0, int(total_army * 0.05 * wave_num))
        if losses > 0 and army:
            with get_db() as db:
                db_army = db.query(Army).filter(Army.kingdom_id == user_id).first()
                if db_army:
                    db_army.infantry = max(0, getattr(db_army, 'infantry', 0) - losses)
                    db.commit()

        text = (
            f"⚔️ **WAVE {wave_num} CLEARED!**\n"
            "━━━━━━━━━━━━━━\n"
            f"👹 Enemies: {wave_data['type']} x{enemy_count}\n"
            f"💰 Reward: {reward:,} Gold\n"
            f"💀 Losses: {losses} soldiers\n\n"
        )

        context.user_data["survival_wave"] = wave_num + 1

        if wave_num < 5:
            text += "Next wave start karo?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Next Wave", callback_data="survival_next")],
                [InlineKeyboardButton("🏃 Retreat", callback_data="menu_games")],
            ])
        else:
            text += "🎉 All waves complete! Reward claim karo!"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Claim Reward", callback_data="survival_next")],
            ])
    else:
        # Defeat
        text = (
            f"💀 **WAVE {wave_num} FAILED!**\n"
            "━━━━━━━━━━━━━━\n"
            f"👹 Enemies: {wave_data['type']} x{enemy_count}\n"
            "😢 Army too weak!\n\n"
            "💪 Train more soldiers!"
        )

        # Clear survival data
        context.user_data.pop("survival_wave", None)
        context.user_data.pop("survival_reward", None)
        keyboard = back_dashboard_keyboard()

    await query.edit_message_text(text, reply_markup=keyboard)


# ═══════════════════════════════════════════
# BLACK MARKET
# ═══════════════════════════════════════════

async def show_black_market(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show black market"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    text = (
        "🏪 **BLACK MARKET**\n"
        "━━━━━━━━━━━━━━\n"
        f"💎 Gems: {getattr(kingdom, 'gems', 0):,}\n\n"
        "Special items gems se kharido!\n\n"
    )

    for i, item in enumerate(BLACK_MARKET_ITEMS):
        text += f"{i+1}. {item['name']} - 💎 {item['price_gems']} Gems\n"

    await query.edit_message_text(text, reply_markup=black_market_keyboard())


async def show_market_items(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show detailed market items for purchase"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    buttons = []
    for i, item in enumerate(BLACK_MARKET_ITEMS):
        buttons.append([InlineKeyboardButton(
            f"{item['name']} - 💎 {item['price_gems']}",
            callback_data=f"market_buy:{i}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_games")])

    text = (
        "🛒 **SELECT ITEM**\n"
        "━━━━━━━━━━━━━━\n"
        f"💎 Your Gems: {getattr(kingdom, 'gems', 0):,}\n"
    )

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def buy_market_item(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, item_idx: int):
    """Buy a black market item"""
    query = update.callback_query

    if item_idx < 0 or item_idx >= len(BLACK_MARKET_ITEMS):
        await query.answer("❌ Invalid item!", show_alert=True)
        return

    item = BLACK_MARKET_ITEMS[item_idx]

    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return

        if getattr(kingdom, 'gems', 0) < item["price_gems"]:
            await query.answer("❌ Not enough Gems!", show_alert=True)
            return

        # Deduct gems
        kingdom.gems -= item["price_gems"]

        # Apply effect
        effect_msg = ""
        effect = item["effect"]

        if effect == "skip_build_time":
            # Complete all current upgrades
            from bot.models import Building
            upgrading = db.query(Building).filter(
                Building.kingdom_id == user_id,
                Building.is_upgrading == True
            ).all()
            for b in upgrading:
                b.level += 1
                b.is_upgrading = False
                b.upgrade_started = None
                b.upgrade_completes = None
            effect_msg = f"⏩ {len(upgrading)} upgrades instantly completed!"

        elif effect == "refill_energy":
            kingdom.energy = 10
            effect_msg = "⚡ Energy fully refilled!"

        elif effect == "extend_shield":
            current = getattr(kingdom, 'shield_expires', None)
            base = current if current and current > datetime.utcnow() else datetime.utcnow()
            kingdom.shield_expires = base + timedelta(hours=24)
            effect_msg = "🛡 +24h Shield added!"

        elif effect == "full_spy_report":
            effect_msg = "📜 Next spy will reveal full details!"
            context.user_data["full_spy"] = True

        elif effect == "add_gold":
            kingdom.gold += 10000
            effect_msg = "💰 +10,000 Gold added!"

        elif effect == "extra_dice_roll":
            effect_msg = "🎲 Extra dice roll granted!"
            # Clear cooldown
            GameData.clear_cooldown(user_id, "dice")

        db.commit()

    text = (
        f"✅ **PURCHASED: {item['name']}**\n"
        "━━━━━━━━━━━━━━\n"
        f"💎 -{item['price_gems']} Gems\n"
        f"{effect_msg}"
    )

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


# ═══════════════════════════════════════════
# DECISION EVENTS
# ═══════════════════════════════════════════

async def handle_decision_event(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, event_id: str, choice: str):
    """Handle random decision event choice"""
    query = update.callback_query

    from bot.utils.constants import DECISION_EVENTS

    event = None
    for e in DECISION_EVENTS:
        if e["id"] == event_id:
            event = e
            break

    if not event:
        await query.answer("❌ Event expired!", show_alert=True)
        return

    outcomes = event.get("outcomes", {})
    outcome = outcomes.get(choice.upper(), {"message": "Kuch nahi hua..."})

    # Apply rewards
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if kingdom:
            if "gold" in outcome:
                kingdom.gold += outcome["gold"]
            if "food" in outcome:
                kingdom.food += outcome["food"]
            if "infantry" in outcome:
                army = db.query(Army).filter(Army.kingdom_id == user_id).first()
                if army:
                    army.infantry += outcome["infantry"]
            db.commit()

    text = (
        "🎲 **EVENT RESULT**\n"
        "━━━━━━━━━━━━━━\n"
        f"{outcome['message']}\n"
    )

    if "gold" in outcome:
        text += f"\n💰 +{outcome['gold']:,} Gold"
    if "food" in outcome:
        text += f"\n🍖 +{outcome['food']:,} Food"
    if "infantry" in outcome:
        text += f"\n⚔️ +{outcome['infantry']} Infantry"

    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())
