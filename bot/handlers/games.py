"""
King-Maker Bot — Elite Edition
Mini-Games Handlers — Dice, Lucky Spin, Kingdom Quiz, Black Market
"""

import json, random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.config import config
from bot.models import get_db, Kingdom
from bot.services.economy import EconomyService
from bot.utils.keyboards import (
    games_menu_keyboard, dice_keyboard, spin_keyboard,
    quiz_keyboard, black_market_keyboard, back_dashboard_keyboard,
)


def render_bar(value: int, maximum: int, width: int = 12, fill: str = "█", empty: str = "░") -> str:
    """Render a horizontal progress bar."""
    if maximum <= 0:
        return empty * width
    ratio = min(value / maximum, 1.0)
    filled = int(round(ratio * width))
    return fill * filled + empty * (width - filled)


# ═══════════════════════════════════════════════════════════════════
#  DICE GAME
# ═══════════════════════════════════════════════════════════════════

DICE_FACES = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}


async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the games menu."""
    query = update.callback_query
    await query.edit_message_text(
        "🎮 **MINI-GAMES**\n\n"
        "Entertainment ke liye games khelo!\n"
        "Aur extra rewards jeeto!\n\n"
        "💰 Har game mein Gold jeet sakte ho!",
        parse_mode="Markdown",
        reply_markup=games_menu_keyboard(),
    )


async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dice game with betting options."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

    await query.edit_message_text(
        f"🎲 **DICE GAME**\n\n"
        f"💰 Balance: {k.gold}\n\n"
        f"Aapka dice vs Bot ka dice!\n"
        f"Jiska number zyada, woh jeeta!\n\n"
        f"Bet amount select karo:",
        parse_mode="Markdown",
        reply_markup=dice_keyboard(),
    )


async def handle_dice_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice roll with visual animation."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id

    bet = int(data.split(":")[1])

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

        if k.gold < bet:
            return await query.edit_message_text(
                f"💰 **Insufficient Gold!**\n\n"
                f"Bet: {bet}\n"
                f"Balance: {k.gold}\n\n"
                f"Kam bet karo ya gold collect karo!",
                parse_mode="Markdown",
                reply_markup=dice_keyboard(),
            )

        # Roll with "animation"
        player_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)

        if player_roll > bot_roll:
            winnings = bet
            k.gold += winnings
            result_emoji = "🎉"
            result_text = f"**YOU WIN!** +{winnings} Gold"
            result_color = "✅"
        elif player_roll < bot_roll:
            k.gold -= bet
            result_emoji = "😢"
            result_text = f"**You Lose!** -{bet} Gold"
            result_color = "❌"
        else:
            result_emoji = "🤝"
            result_text = "**DRAW!** Koi loss nahi!"
            result_color = "⚖️"

        db.commit()

        # Visual comparison bar
        bar = render_bar(player_roll, 6, 6)
        bot_bar = render_bar(bot_roll, 6, 6)

    await query.edit_message_text(
        f"🎲 **DICE ROLL**\n\n"
        f"```\n"
        f"You:   {DICE_FACES[player_roll]} ({player_roll})  {bar}\n"
        f"Bot:   {DICE_FACES[bot_roll]} ({bot_roll})  {bot_bar}\n"
        f"```\n"
        f"{result_emoji} {result_color} {result_text}\n\n"
        f"💰 Balance: **{k.gold}** Gold",
        parse_mode="Markdown",
        reply_markup=dice_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
#  LUCKY SPIN
# ═══════════════════════════════════════════════════════════════════

SPIN_PRIZES = [
    ("💰 100 Gold", 100, "gold_add", 20),
    ("💰 200 Gold", 200, "gold_add", 12),
    ("💰 500 Gold", 500, "gold_add", 5),
    ("🍖 50 Food", 50, "food_add", 15),
    ("🍖 150 Food", 150, "food_add", 10),
    ("⚡ 1 Energy", 1, "energy_add", 10),
    ("🏆 50 XP", 50, "xp_add", 15),
    ("❌ Nothing", 0, "none", 8),
    ("💎 1000 Gold", 1000, "gold_add", 3),
    ("🎁 Mystery Box", 0, "mystery", 2),
]


async def lucky_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show lucky spin wheel."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

    if k.gold < 50:
        return await query.edit_message_text(
            f"💰 **50 Gold** chahiye spin ke liye!\n"
            f"Balance: {k.gold}",
            reply_markup=games_menu_keyboard(),
        )

    await query.edit_message_text(
        f"🎰 **LUCKY SPIN**\n\n"
        f"Cost: 50 Gold/spin\n"
        f"💰 Balance: {k.gold}\n\n"
        f"🎁 Prizes: Gold, Food, Energy, XP\n"
        f"💎 Jackpot: 1000 Gold!\n\n"
        f"**SPIN** karo!",
        parse_mode="Markdown",
        reply_markup=spin_keyboard(),
    )


async def handle_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process lucky spin with visual wheel."""
    query = update.callback_query
    user_id = update.effective_user.id

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

        if k.gold < 50:
            return await query.edit_message_text(
                f"💰 50 Gold chahiye!\nBalance: {k.gold}",
                reply_markup=games_menu_keyboard(),
            )

        k.gold -= 50

        # Weighted random selection
        weights = [p[3] for p in SPIN_PRIZES]
        prize = random.choices(SPIN_PRIZES, weights=weights, k=1)[0]
        prize_name, amount, ptype, _ = prize

        bonus_text = ""
        if ptype == "gold_add":
            k.gold += amount
            bonus_text = f"💰 +{amount} Gold"
        elif ptype == "food_add":
            k.food += amount
            bonus_text = f"🍖 +{amount} Food"
        elif ptype == "energy_add":
            old_energy = k.energy
            k.energy = min(config.MAX_ENERGY, k.energy + amount)
            gained = k.energy - old_energy
            bonus_text = f"⚡ +{gained} Energy"
        elif ptype == "xp_add":
            k.xp += amount
            bonus_text = f"📈 +{amount} XP"
        elif ptype == "mystery":
            mystery_prizes = [
                ("💰 200 Gold", 200, "gold"), ("🍖 300 Food", 300, "food"),
                ("⚡ 2 Energy", 2, "energy"), ("📈 100 XP", 100, "xp"),
            ]
            m_prize = random.choice(mystery_prizes)
            m_name, m_val, m_type = m_prize
            if m_type == "gold":
                k.gold += m_val
            elif m_type == "food":
                k.food += m_val
            elif m_type == "energy":
                k.energy = min(config.MAX_ENERGY, k.energy + m_val)
            elif m_type == "xp":
                k.xp += m_val
            prize_name = f"🎁 Mystery: {m_name}"
            bonus_text = f"Surprise! {m_name}"

        db.commit()

    # Visual wheel representation
    wheel_visual = (
        "```\n"
        "    ╔═══════════╗\n"
        "    ║   🎰   ║\n"
        "    ║  SPIN  ║\n"
        "    ╚═══════════╝\n"
        "```"
    )

    await query.edit_message_text(
        f"{wheel_visual}\n"
        f"🎰 **LUCKY SPIN RESULT**\n\n"
        f"🎁 **{prize_name}**\n"
        f"{bonus_text}\n\n"
        f"📊 Updated Balance:\n"
        f"💰 Gold: {k.gold}\n"
        f"🍖 Food: {k.food}\n"
        f"⚡ Energy: {k.energy}/{config.MAX_ENERGY}",
        parse_mode="Markdown",
        reply_markup=spin_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
#  KINGDOM QUIZ
# ═══════════════════════════════════════════════════════════════════

QUIZ_QUESTIONS = [
    {
        "q": "Medieval warfare mein sabse powerful unit kaun thi?",
        "opts": ["Infantry (Foot soldiers)", "Cavalry (Horse riders)", "Archers", "Siege weapons"],
        "ans": 1,
        "fact": "Cavalry ne speed aur power se battles jeete!",
    },
    {
        "q": "Castle defense ke liye sabse important building kaunsa hai?",
        "opts": ["Farm", "Wall", "Market", "Barracks"],
        "ans": 1,
        "fact": "Wall se attackers ko roka ja sakta hai!",
    },
    {
        "q": "Resources collect karne ka sabse fast tareeka kya hai?",
        "opts": ["Enemy attack", "Building collect", "Market trade", "Dice game"],
        "ans": 1,
        "fact": "Buildings se regular production hoti hai!",
    },
    {
        "q": "Spy mission ka cooldown kitna hota hai?",
        "opts": ["1 minute", "5 minutes", "10 minutes", "30 minutes"],
        "ans": 1,
        "fact": "5 min cooldown — use wisely!",
    },
    {
        "q": "Level 10 Kingdom ke liye approximately kitni XP chahiye?",
        "opts": ["~500 XP", "~1500 XP", "~3000 XP", "~5000 XP"],
        "ans": 2,
        "fact": "XP requirement exponential hoti hai!",
    },
    {
        "q": "Food shortage pe kya hota hai?",
        "opts": ["Nothing", "Army desertion", "Gold loss", "Building damage"],
        "ans": 1,
        "fact": "Bhooki army bhaag jati hai! Food collect karo!",
    },
    {
        "q": "Alliance ka sabse bada benefit kya hai?",
        "opts": ["Free gold", "Team protection", "Extra energy", "No attacks"],
        "ans": 1,
        "fact": "Alliance se combined power aur protection milta hai!",
    },
]


async def kingdom_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the kingdom quiz."""
    query = update.callback_query
    context.user_data["quiz_idx"] = 0
    context.user_data["quiz_score"] = 0
    context.user_data["quiz_questions"] = random.sample(QUIZ_QUESTIONS, min(5, len(QUIZ_QUESTIONS)))

    await _show_quiz_question(update, context)


async def _show_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display current quiz question with progress."""
    query = update.callback_query
    idx = context.user_data.get("quiz_idx", 0)
    questions = context.user_data.get("quiz_questions", [])
    score = context.user_data.get("quiz_score", 0)

    if idx >= len(questions):
        return await _quiz_complete(update, context)

    q = questions[idx]
    progress_bar = render_bar(idx, len(questions), 8)

    await query.edit_message_text(
        f"🧠 **Kingdom Quiz**  {idx + 1}/{len(questions)}\n"
        f"{progress_bar}\n"
        f"Score: {score} ✅\n\n"
        f"**{idx + 1}. {q['q']}**",
        parse_mode="Markdown",
        reply_markup=quiz_keyboard(idx, q["opts"]),
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process quiz answer and show feedback."""
    query = update.callback_query
    data = query.data
    parts = data.split(":")
    q_idx = int(parts[1])
    ans = int(parts[2])

    questions = context.user_data.get("quiz_questions", [])
    if q_idx >= len(questions):
        return await query.answer("Quiz already completed!")

    q = questions[q_idx]
    correct = q["ans"]
    is_correct = (ans == correct)

    if is_correct:
        context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
        feedback = f"✅ **Correct!**\n\n💡 {q['fact']}"
    else:
        correct_answer = q["opts"][correct]
        feedback = f"❌ **Wrong!**\nCorrect: **{correct_answer}**\n\n💡 {q['fact']}"

    await query.answer(feedback, show_alert=True)

    # Move to next question
    context.user_data["quiz_idx"] = q_idx + 1
    await _show_quiz_question(update, context)


async def _quiz_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quiz completion with rewards."""
    query = update.callback_query
    score = context.user_data.get("quiz_score", 0)
    total = len(context.user_data.get("quiz_questions", []))
    bonus = score * 25
    xp_bonus = score * 10

    user_id = update.effective_user.id
    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if k:
            k.gold += bonus
            k.xp += xp_bonus
            db.commit()

    # Performance rating
    ratio = score / max(total, 1)
    if ratio == 1.0:
        rating = "🏆 PERFECT!"
    elif ratio >= 0.8:
        rating = "⭐ EXCELLENT!"
    elif ratio >= 0.6:
        rating = "👍 GOOD!"
    elif ratio >= 0.4:
        rating = "📚 NEEDS PRACTICE"
    else:
        rating = "📖 STUDY MORE!"

    bar = render_bar(score, total, 10)

    await query.edit_message_text(
        f"🧠 **QUIZ COMPLETE!**\n\n"
        f"{bar}\n"
        f"Score: **{score}/{total}**\n"
        f"Rating: {rating}\n\n"
        f"🎁 Rewards:\n"
        f"💰 +{bonus} Gold\n"
        f"📈 +{xp_bonus} XP\n\n"
        f"💰 Balance: {k.gold if k else 'N/A'}",
        parse_mode="Markdown",
        reply_markup=games_menu_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
#  BLACK MARKET
# ═══════════════════════════════════════════════════════════════════

MARKET_ITEMS = [
    {"id": "sword1", "name": "⚔️ Iron Sword", "cost": 100, "attack": 10, "desc": "+10 attack power"},
    {"id": "shield1", "name": "🛡 Wooden Shield", "cost": 80, "defense": 10, "desc": "+10 defense power"},
    {"id": "potion1", "name": "🧪 Health Potion", "cost": 50, "heal": 20, "desc": "Restore army units"},
    {"id": "scroll1", "name": "📜 XP Scroll", "cost": 150, "xp": 50, "desc": "+50 instant XP"},
    {"id": "ring1", "name": "💍 Gold Ring", "cost": 200, "gold_bonus": 0.1, "desc": "+10% gold production"},
    {"id": "armor1", "name": "🦺 Chain Armor", "cost": 120, "defense": 15, "desc": "+15 defense power"},
    {"id": "axe1", "name": "🪓 Battle Axe", "cost": 130, "attack": 15, "desc": "+15 attack power"},
    {"id": "boots1", "name": "👢 Swift Boots", "cost": 90, "speed": 10, "desc": "+10% attack speed"},
]


async def black_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show black market with proper item selection."""
    query = update.callback_query
    user_id = update.effective_user.id

    # Select 4 random items and store them for consistent purchase
    items = random.sample(MARKET_ITEMS, min(4, len(MARKET_ITEMS)))
    context.user_data["market_items"] = items

    lines = [
        "🖤 **BLACK MARKET**\n",
        "*Secret deals... Limited time!*\n",
        f"💰 Your Gold: Loading...\n",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    buttons = []
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {item['name']}")
        lines.append(f"   💰 {item['cost']} | {item['desc']}")
        buttons.append([InlineKeyboardButton(
            f"Buy {item['name']} — 💰{item['cost']}",
            callback_data=f"market_buy:{i - 1}",
        )])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="market_refresh")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_games")])

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle black market item purchase with stored items."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    item_idx = int(data.split(":")[1])

    # Get stored items
    items = context.user_data.get("market_items", [])
    if not items or item_idx >= len(items):
        return await query.edit_message_text(
            "❌ Items expired!\nMarket refresh karo.",
            reply_markup=black_market_keyboard(),
        )

    item = items[item_idx]

    with get_db() as db:
        k = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not k:
            return await query.edit_message_text("❌ Error!")

        if k.gold < item["cost"]:
            return await query.edit_message_text(
                f"💰 **{item['cost']} Gold** chahiye!\n"
                f"Balance: {k.gold}\n\n"
                f"Aur gold collect karo!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Market", callback_data="market_refresh")],
                ]),
            )

        # Process purchase
        k.gold -= item["cost"]
        effects = []

        if "attack" in item and k.army:
            k.army.infantry = max(0, k.army.infantry + 2)
            effects.append(f"⚔️ +{item['attack']} attack (infantry +2)")
        if "defense" in item:
            effects.append(f"🛡 +{item['defense']} defense")
        if "heal" in item and k.army:
            k.army.infantry = max(0, k.army.infantry + 5)
            effects.append(f"🧪 Army restored (+5 units)")
        if "xp" in item:
            k.xp += item["xp"]
            effects.append(f"📈 +{item['xp']} XP")
        if "gold_bonus" in item:
            k.gold += int(item["cost"] * 0.5)
            effects.append(f"💰 Bonus: +{int(item['cost'] * 0.5)} Gold")
        if "speed" in item:
            effects.append(f"👢 +{item['speed']}% speed boost")

        db.commit()

    effects_text = "\n".join(f"  {e}" for e in effects) if effects else "  Item added to inventory!"

    await query.edit_message_text(
        f"✅ **Purchase Successful!**\n\n"
        f"{item['name']}\n"
        f"💰 Spent: {item['cost']}\n\n"
        f"📊 Effects:\n{effects_text}\n\n"
        f"💰 Remaining: {k.gold} Gold",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖤 Back to Market", callback_data="market_refresh")],
            [InlineKeyboardButton("🔙 Games Menu", callback_data="menu_games")],
        ]),
    )


async def handle_market_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh black market items."""
    return await black_market(update, context)
