"""
King-Maker Bot — Elite Edition
Start / Tutorial / Kingdom Creation Handlers
"""

import json
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.config import config
from bot.models import (
    get_db, User, Kingdom, Army, Building, Hero, Quest, UserQuest, Battle,
)
from bot.services.economy import EconomyService
from bot.utils.keyboards import start_menu_keyboard, trait_selection_keyboard
from bot.utils.validators import validate_kingdom_name

# ── Conversation states ──────────────────────────────────────────
NAME, TRAIT, CONFIRM = range(3)

# Kingdom emojis pool
FLAG_EMOJIS = [
    "🏴", "🏳️", "🚩", "🏁", "🎌", "🏴‍☠️", "🏳️‍🌈", "🇦🇷", "🇦🇺", "🇧🇷",
    "🇨🇦", "🇩🇪", "🇪🇸", "🇫🇷", "🇬🇧", "🇮🇳", "🇮🇹", "🇯🇵", "🇰🇷", "🇲🇽",
    "🇳🇱", "🇷🇺", "🇺🇸", "🇿🇦", "🇨🇳", "🇸🇦", "🇹🇷", "🇵🇰", "🇧🇩", "🇳🇵",
    "🦁", "🐯", "🦅", "🐉", "🦈", "🐺", "🦉", "🐻", "🦌", "🦊",
]


def get_random_flag() -> str:
    """Return a random flag emoji."""
    import random
    return random.choice(FLAG_EMOJIS)


async def start_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show start menu to new or returning users."""
    user = update.effective_user
    query = update.callback_query

    with get_db() as db:
        existing = db.query(User).filter(User.telegram_id == user.id).first()

    if existing:
        # Returning user
        if query:
            await query.edit_message_text(
                "🎮 **Welcome back!**\n\nKingdom mein waapas swagat hai!\n\n"
                "Dashboard open karne ke liye niche click karo:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏰 Open Dashboard", callback_data="back_dashboard")],
                    [InlineKeyboardButton("📖 How to Play", callback_data="how_to_play")],
                ]),
            )
        else:
            await update.message.reply_text(
                "🎮 **Welcome back!**\n\nKingdom mein waapas swagat hai!\n\n"
                "Dashboard open karne ke liye niche click karo:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏰 Open Dashboard", callback_data="back_dashboard")],
                    [InlineKeyboardButton("📖 How to Play", callback_data="how_to_play")],
                ]),
            )
        return ConversationHandler.END

    # New user — begin kingdom creation
    welcome_text = (
        f"👑 **Welcome to King-Maker, {user.first_name}!**\n\n"
        "Ek **strategy game** jismein aap apna Kingdom banate ho,\n"
        "Army train karte ho, aur dushmano ko haraate ho!\n\n"
        "🎯 **Goal**: Supreme King bano!\n\n"
        "Shuru karne ke liye **Start Game** dabao:"
    )

    if query:
        await query.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=start_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=start_menu_keyboard(),
        )
    return ConversationHandler.END


async def start_game_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for new kingdom creation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏰 **Kingdom Creation**\n\n"
        "Apne Kingdom ka naam batao!\n"
        "(3 se 20 characters, letters/numbers only)\n\n"
        "Example: *Shadow Empire*, *Dragonia*",
        parse_mode="Markdown",
    )
    return NAME


async def receive_kingdom_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process kingdom name input."""
    name = update.message.text.strip()
    valid, error = validate_kingdom_name(name)
    if not valid:
        await update.message.reply_text(
            f"❌ **{error}**\n\nDobara try karo:",
            parse_mode="Markdown",
        )
        return NAME

    context.user_data["kingdom_name"] = name
    flag = get_random_flag()
    context.user_data["kingdom_flag"] = flag

    await update.message.reply_text(
        f"✅ **{name}** — mast naam hai!\n\n"
        f"Aapka flag: {flag}\n\n"
        "Ab apna **Kingdom Trait** select karo:\n\n"
        "⚔️ **Aggressive** — +20% Attack, +10 Infantry\n"
        "🛡 **Defensive** — +20% Defense, +Wall boost\n"
        "💰 **Rich** — +300 Starting Gold\n"
        "⚖️ **Balanced** — +100 Gold, +5 Infantry, +100 Food",
        parse_mode="Markdown",
        reply_markup=trait_selection_keyboard(),
    )
    return TRAIT


async def receive_trait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process trait selection and create the full kingdom."""
    query = update.callback_query
    await query.answer()

    trait = query.data.split(":")[1]
    name = context.user_data.get("kingdom_name", "Unknown Kingdom")
    flag = context.user_data.get("kingdom_flag", "🏴")
    user = update.effective_user

    # Trait definitions
    traits = {
        "aggressive": {"gold": 100, "food": 50, "infantry": 10, "archers": 0, "cavalry": 0, "energy": 5},
        "defensive": {"gold": 100, "food": 100, "infantry": 5, "archers": 5, "cavalry": 0, "energy": 5},
        "rich": {"gold": 400, "food": 100, "infantry": 5, "archers": 0, "cavalry": 0, "energy": 5},
        "balanced": {"gold": 200, "food": 150, "infantry": 5, "archers": 2, "cavalry": 1, "energy": 5},
    }

    t = traits.get(trait, traits["balanced"])

    with get_db() as db:
        # Create user record
        user_record = User(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
        db.add(user_record)
        db.flush()

        # Create kingdom
        kingdom = Kingdom(
            user_id=user.id,
            name=name,
            flag=flag,
            level=1,
            gold=t["gold"],
            food=t["food"],
            energy=t["energy"],
            xp=0,
            map_x=__import__('random').randint(0, 49),
            map_y=__import__('random').randint(0, 49),
            shield_expires=datetime.utcnow() + timedelta(hours=24),
            last_active=datetime.utcnow(),
            battles_won=0,
            total_gold_earned=0,
            gold_history=json.dumps([t["gold"] * 0.8, t["gold"] * 0.9, t["gold"]]),
        )
        db.add(kingdom)
        db.flush()

        # Create army
        army = Army(
            kingdom_id=user.id,
            infantry=t["infantry"],
            archers=t["archers"],
            cavalry=t["cavalry"],
        )
        db.add(army)

        # Create buildings
        building_configs = [
            ("town_hall", "🏛", "Town Hall"),
            ("barracks", "⚔️", "Barracks"),
            ("farm", "🌾", "Farm"),
            ("gold_mine", "⛏️", "Gold Mine"),
            ("wall", "🛡", "Wall"),
            ("market", "🏪", "Market"),
        ]
        for btype, emoji, display in building_configs:
            building = Building(
                kingdom_id=user.id,
                building_type=btype,
                emoji=emoji,
                display_name=display,
                level=1,
                is_upgrading=False,
            )
            db.add(building)

        # Create default hero
        hero = Hero(
            kingdom_id=user.id,
            hero_type="commander",
            display_name="Sir Lancelot",
            unlocked=True,
            level=1,
            skill_points=0,
            skill_tree="{}",
        )
        db.add(hero)

        # Create default quests
        __create_default_quests(db, user.id)

        db.commit()

    trait_display = {"aggressive": "⚔️ Aggressive", "defensive": "🛡 Defensive",
                     "rich": "💰 Rich", "balanced": "⚖️ Balanced"}

    summary = (
        f"🎉 **Kingdom Created!**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏰 **{name}**  {flag}\n"
        f"🎖 Level: **1**\n"
        f"🧬 Trait: **{trait_display.get(trait, trait)}**\n\n"
        f"💰 Gold: **{t['gold']}**\n"
        f"🍖 Food: **{t['food']}**\n"
        f"⚡ Energy: **{t['energy']}/{config.MAX_ENERGY}**\n\n"
        f"🪖 **Starting Army:**\n"
        f"   🗡 Infantry: {t['infantry']}\n"
        f"   🏹 Archers: {t['archers']}\n"
        f"   🐎 Cavalry: {t['cavalry']}\n\n"
        f"🏗 **Buildings Ready:**\n"
        f"   🏛 Town Hall, ⚔️ Barracks, 🌾 Farm\n"
        f"   ⛏️ Gold Mine, 🛡 Wall, 🏪 Market\n\n"
        f"🛡 Shield: **24 hours protection**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Dashboard open ho raha hai..."
    )

    await query.edit_message_text(
        summary,
        parse_mode="Markdown",
    )

    # Show dashboard
    from bot.main import show_dashboard
    await show_dashboard(update, context)
    return ConversationHandler.END


def __create_default_quests(db, user_id):
    """Create default quests for a new user."""
    quests = [
        Quest(quest_type="daily", name="Gold Collector", description="50 Gold collect karo",
              target_amount=50, reward_gold=25, reward_xp=10),
        Quest(quest_type="daily", name="Army Builder", description="5 units train karo",
              target_amount=5, reward_gold=30, reward_xp=15),
        Quest(quest_type="daily", name="First Blood", description="1 battle win karo",
              target_amount=1, reward_gold=50, reward_xp=20),
        Quest(quest_type="weekly", name="Conqueror", description="10 battles jeeto",
              target_amount=10, reward_gold=200, reward_xp=100),
        Quest(quest_type="weekly", name="Rich King", description="1000 Gold earn karo",
              target_amount=1000, reward_gold=100, reward_xp=50),
    ]
    for quest in quests:
        db.add(quest)
        db.flush()
        user_quest = UserQuest(user_id=user_id, quest_id=quest.id, progress=0, completed=False, claimed=False)
        db.add(user_quest)


async def tutorial_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show interactive tutorial with visual guide."""
    query = update.callback_query

    tutorial_pages = [
        (
            "📖 **TUTORIAL — Page 1/5**\n\n"
            "👑 **King-Maker Kya Hai?**\n\n"
            "Ye ek **real-time strategy game** hai Telegram pe!\n\n"
            "• Apna Kingdom banao\n"
            "• Resources collect karo\n"
            "• Army train karo\n"
            "• Dushmano pe attack karo\n"
            "• Supreme King bano!",
            "tutorial_2",
        ),
        (
            "📖 **TUTORIAL — Page 2/5**\n\n"
            "🏗 **BUILDINGS**\n\n"
            "Har building ka alag kaam hai:\n\n"
            "🏛 **Town Hall** — Kingdom level up\n"
            "⚔️ **Barracks** — Army training\n"
            "🌾 **Farm** — Food production\n"
            "⛏️ **Gold Mine** — Gold production\n"
            "🛡 **Wall** — Defense boost\n"
            "🏪 **Market** — Resource trading",
            "tutorial_3",
        ),
        (
            "📖 **TUTORIAL — Page 3/5**\n\n"
            "⚔️ **COMBAT SYSTEM**\n\n"
            "Attack karne ke liye:\n"
            "1. Attack menu se opponent dhoondo\n"
            "2. Power comparison dekho\n"
            "3. Attack ya Spy karo\n\n"
            "💀 **Army Types:**\n"
            "🗡 Infantry — Balanced\n"
            "🏹 Archers — High attack\n"
            "🐎 Cavalry — Fast, strong\n\n"
            "⚡ Energy har attack mein lagti hai!",
            "tutorial_4",
        ),
        (
            "📖 **TUTORIAL — Page 4/5**\n\n"
            "🤝 **ALLIANCE SYSTEM**\n\n"
            "• Alliance create karo ya join karo\n"
            "• Members ko donate karo\n"
            "• Saath milkar attack karo\n"
            "• Alliance leaderboard pe top aao!\n\n"
            "🕵️ **SPY SYSTEM**\n\n"
            "• Dushman ki info collect karo\n"
            "• Army size, resources dekho\n"
            "• 5 minute cooldown",
            "tutorial_5",
        ),
        (
            "📖 **TUTORIAL — Page 5/5**\n\n"
            "💡 **PRO TIPS**\n\n"
            "• Daily quests karo — free rewards!\n"
            "• Food collect karo — army bhooki maregi\n"
            "• Shield active rakho — 24h protection\n"
            "• Mini-games khelo — extra gold\n"
            "• Alliance join karo — teamwork OP\n\n"
            "🎮 **Ready ho?**\n"
            "Neeche Start Game dabao!",
            "start_game",
        ),
    ]

    # Show first page
    text, next_btn = tutorial_pages[0]
    context.user_data["tutorial_pages"] = tutorial_pages
    context.user_data["tutorial_idx"] = 0

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Next", callback_data=f"tutorial_next:{next_btn}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def tutorial_next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tutorial pagination."""
    query = update.callback_query
    await query.answer()

    pages = context.user_data.get("tutorial_pages", [])
    idx = context.user_data.get("tutorial_idx", 0) + 1

    if idx >= len(pages):
        return await start_menu_handler(update, context)

    context.user_data["tutorial_idx"] = idx
    text, next_btn = pages[idx]

    buttons = []
    if idx < len(pages) - 1:
        buttons.append([InlineKeyboardButton("➡️ Next", callback_data=f"tutorial_next:{next_btn}")])
    else:
        buttons.append([InlineKeyboardButton("🎮 Start Game", callback_data="start_game")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
