"""
Start Handler - Kingdom Creation Wizard & Tutorial
Fixed version with proper imports, error handling, and visual effects.
"""

import random
import json
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes

from bot.models import get_db, User, Kingdom, Building, Army
from bot.services.game_data import GameData
from bot.services.combat_engine import CombatEngine
from bot.utils.keyboards import start_menu_keyboard, trait_selection_keyboard
from bot.utils.validators import validate_kingdom_name
from bot.utils.constants import FLAGS, KINGDOM_TRAITS
from bot.utils.animations import LoadingAnimation, KingdomCreationAnimator

logger = logging.getLogger(__name__)

# User state tracking for multi-step flows
user_states = {}


def get_user_state(user_id: int) -> dict:
    """Get user state safely"""
    return user_states.get(user_id, {})


def set_user_state(user_id: int, state: dict):
    """Set user state"""
    user_states[user_id] = state


def clear_user_state(user_id: int):
    """Clear user state"""
    user_states.pop(user_id, None)


# ═══════════════════════════════════════════
# COMMAND HANDLERS ( Aliases for main router )
# ═══════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /start command"""
    await handler_start(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help text"""
    help_text = """📖 **HOW TO PLAY**
━━━━━━━━━━━━━━

**Core Loop:**
1️⃣ Collect resources from Gold Mine & Farm
2️⃣ Upgrade buildings for more production
3️⃣ Train army in Barracks
4️⃣ Attack other players for loot!

**Commands:**
/start — Start the game
/dashboard — Open dashboard
/help — Show this help

**Army Types:**
🗡 Infantry — Balanced (Unlock: Starter)
🏹 Archers — Ranged damage (Unlock: Barracks Lv.2)
🐎 Cavalry — Fast & strong (Unlock: Barracks Lv.4)

**Buildings:**
🏰 Town Hall — Unlocks buildings
⛏ Gold Mine — Produces Gold
🌾 Farm — Produces Food
🏹 Barracks — Trains Army
🛡 Wall — Reduces damage

**Energy System:**
⚡ 10 Energy max, 1 per attack
⏳ Regenerates every 30 minutes

**Shield System:**
🛡 New players get 24h shield
🛡 Shield breaks when you attack

**Alliance:**
🤝 Team up with other players
⚔️ Fight team wars together

**Pro Tips:**
🎯 Daily quests complete karo
🎯 Spy bhejo attack se pehle
🎯 World events ka fayda uthao
🎯 Alliance mein rehno for protection

Good luck, King! 👑"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Handle text messages from users during multi-step flows"""
    # Check if user is in a flow
    state = get_user_state(user_id)
    if not state:
        # Not in a flow, show dashboard if kingdom exists
        kingdom = GameData.get_kingdom(user_id)
        if kingdom:
            from bot.handlers.dashboard import render_dashboard
            await render_dashboard(update, context, user_id, new_message=True)
        else:
            await update.message.reply_text(
                "🎮 /start type karo game shuru karne ke liye!"
            )
        return

    step = state.get("step")

    if step == "kingdom_name":
        await _handle_kingdom_name_step(update, user_id, text)
    elif step == "select_flag":
        await _handle_flag_selection_step(update, user_id, text, state)
    elif step == "select_trait":
        await _handle_trait_selection_step(update, user_id, text, state)
    elif step == "alliance_name":
        from bot.handlers.alliance import handle_alliance_name_input
        await handle_alliance_name_input(update, user_id, text)
    elif step == "bounty_target":
        await update.message.reply_text("Bounty system processing...")
    else:
        clear_user_state(user_id)
        await update.message.reply_text(
            "❌ Invalid state. /start se dobara shuru karo."
        )


# ─── Main Start Handler ───

async def handler_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - entry point with error handling"""
    try:
        user = update.effective_user

        # Create or get user
        db_user = GameData.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

        # Check if banned
        if getattr(db_user, 'is_banned', False):
            await update.message.reply_text(
                "⛔ **BANNED**\n"
                "━━━━━━━━━━━━━━\n"
                "Aapko ban kar diya gaya hai.\n"
                "Contact admin for help.",
                parse_mode="Markdown"
            )
            return

        # Check if kingdom exists
        kingdom = GameData.get_kingdom(user.id)

        if kingdom:
            # Existing player - show dashboard
            from bot.handlers.dashboard import render_dashboard
            await render_dashboard(update, context, user.id)
            return

        # New player - show welcome with animation
        welcome_text = """⚔️ **WELCOME TO KINGDOM CONQUEST** ⚔️
━━━━━━━━━━━━━━

👑 बनो एक महान राजा!
🏰 अपना Kingdom बनाओ
⚔️ दुश्मनों पर हमला करो
🏆 सबसे शक्तिशाली बनो!

🎮 **Features:**
📊 Real-time statistics & charts
🎬 Animated battle sequences
🌍 Dynamic world events
🤝 Alliance wars
🎯 Daily quests & achievements

**Ready to begin your journey?**"""

        await update.message.reply_text(
            welcome_text,
            reply_markup=start_menu_keyboard(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in handler_start: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try /start again."
        )


# ─── Callback Handlers ───

async def handle_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start menu button clicks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "start_game":
        # Start kingdom creation wizard
        set_user_state(user_id, {"step": "kingdom_name"})

        creation_text = """🏰 **KINGDOM CREATION**
━━━━━━━━━━━━━━

Step 1 of 4: **Kingdom Name**

Apne Kingdom ka naam batao:
• 3-20 characters
• Letters, numbers, spaces only
• Unique naam hona chahiye

Type naam message mein bhejo:"""

        await query.edit_message_text(
            creation_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ]),
            parse_mode="Markdown"
        )

    elif data == "how_to_play":
        help_text = """📖 **HOW TO PLAY**
━━━━━━━━━━━━━━

**Core Loop:**
1️⃣ Collect resources from Gold Mine & Farm
2️⃣ Upgrade buildings for more production
3️⃣ Train army in Barracks
4️⃣ Attack other players for loot!

**Army Types:**
🗡 Infantry — Balanced (Unlock: Starter)
🏹 Archers — Ranged damage (Unlock: Barracks Lv.2)
🐎 Cavalry — Fast & strong (Unlock: Barracks Lv.4)

**Buildings:**
🏰 Town Hall — Unlocks buildings
⛏ Gold Mine — Produces Gold
🌾 Farm — Produces Food
🏹 Barracks — Trains Army
🛡 Wall — Reduces damage

**Energy System:**
⚡ 10 Energy max, 1 per attack
⏳ Regenerates every 30 minutes

**Shield System:**
🛡 New players get 24h shield
🛡 Shield breaks when you attack

**Alliance:**
🤝 Team up with other players
⚔️ Fight team wars together

**💡 Pro Tips:**
🎯 Daily quests complete karo
🎯 Spy bhejo attack se pehle
🎯 World events ka fayda uthao
🎯 Alliance mein rehno for protection

Good luck, King! 👑"""

        await query.edit_message_text(
            help_text,
            reply_markup=start_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "cancel_creation":
        clear_user_state(user_id)
        await query.edit_message_text(
            "❌ Creation cancelled.\n\nDobara shuru karne ke liye /start type karo.",
            reply_markup=start_menu_keyboard()
        )


# ─── Text Input Handler ───

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input during multi-step flows with validation"""
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        await handle_text_message(update, context, user_id, text)

    except Exception as e:
        logger.error(f"Error in handle_text_input: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again with /start"
        )


async def _handle_kingdom_name_step(update: Update, user_id: int, text: str):
    """Handle kingdom name selection step"""
    # Validate name
    valid, error = validate_kingdom_name(text)
    if not valid:
        await update.message.reply_text(
            f"❌ **{error}**\n\nDobara try karo:",
            parse_mode="Markdown"
        )
        return

    # Check uniqueness
    with get_db() as db:
        existing = db.query(Kingdom).filter(Kingdom.name == text).first()
        if existing:
            await update.message.reply_text(
                "❌ **Ye naam pehle se liya gaya hai!**\n\nDusra naam try karo:",
                parse_mode="Markdown"
            )
            return

    # Save name, move to flag selection
    state = get_user_state(user_id)
    state["kingdom_name"] = text
    state["step"] = "select_flag"
    set_user_state(user_id, state)

    # Show flag grid with numbers
    flag_text = f"🏰 **{text}** — naam approved! ✅\n\n"
    flag_text += "🎌 **Step 2 of 4: Select Flag**\n\n"

    for i in range(0, len(FLAGS), 4):
        row = FLAGS[i:i+4]
        flag_text += " ".join([f"`{i+j+1}`.{f}" for j, f in enumerate(row)])
        flag_text += "\n"

    flag_text += "\nFlag ke liye number type karo (1-24):"

    await update.message.reply_text(
        flag_text,
        parse_mode="Markdown"
    )


async def _handle_flag_selection_step(update: Update, user_id: int, text: str, state: dict):
    """Handle flag selection step"""
    try:
        flag_idx = int(text) - 1
        if flag_idx < 0 or flag_idx >= len(FLAGS):
            await update.message.reply_text(
                f"❌ **1 se {len(FLAGS)} ke beech number chuno!**\n\nDobara try karo:",
                parse_mode="Markdown"
            )
            return

        selected_flag = FLAGS[flag_idx]
        state["flag"] = selected_flag
        state["step"] = "select_trait"
        set_user_state(user_id, state)

        # Show trait selection
        trait_text = f"🏰 **{state['kingdom_name']}** {selected_flag}\n\n"
        trait_text += "⚡ **Step 3 of 4: Select Kingdom Trait**\n\n"

        for key, trait in KINGDOM_TRAITS.items():
            trait_text += f"**{trait['name']}**\n"
            trait_text += f"_{trait['description']}_\n\n"

        trait_text += "Trait ke liye type karo:\n"
        trait_text += "`aggressive` / `defensive` / `rich` / `balanced`"

        await update.message.reply_text(
            trait_text,
            parse_mode="Markdown"
        )

    except ValueError:
        await update.message.reply_text(
            "❌ **Valid number enter karo!**\n\nDobara try karo:",
            parse_mode="Markdown"
        )


async def _handle_trait_selection_step(update: Update, user_id: int, text: str, state: dict):
    """Handle trait selection and create kingdom"""
    trait = text.lower().strip()
    if trait not in KINGDOM_TRAITS:
        await update.message.reply_text(
            "❌ **Valid trait chuno:**\n"
            "`aggressive` / `defensive` / `rich` / `balanced`\n\n"
            "Dobara try karo:",
            parse_mode="Markdown"
        )
        return

    # Show loading animation
    loading_msg = await update.message.reply_text(
        "🏰 **Creating your Kingdom...**\n"
        "━━━━━━━━━━━━━━\n"
        "⚡ Generating map position...\n"
        "🏗 Constructing buildings...\n"
        "🗡 Training starter army...\n"
        "🧙 Summoning heroes..."
    )

    try:
        # Create kingdom!
        kingdom = GameData.create_kingdom(
            user_id=user_id,
            name=state["kingdom_name"],
            flag=state["flag"],
            trait=trait,
        )

        # Clear state
        clear_user_state(user_id)

        # Update user tutorial step
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.tutorial_step = 1
                db.commit()

        # Update loading message
        trait_info = KINGDOM_TRAITS[trait]

        created_text = f"""🎉 **KINGDOM CREATED SUCCESSFULLY!**
━━━━━━━━━━━━━━

👑 Kingdom: **{kingdom.name}** {kingdom.flag}
📍 Location: ({kingdom.map_x}, {kingdom.map_y})
⚡ Trait: {trait_info['name']}

🎁 **Starter Resources:**
💰 {kingdom.gold:,} Gold
🍖 {kingdom.food:,} Food
⚡ {kingdom.energy}/10 Energy
🗡 50 Infantry

🛡 **24h Newbie Shield active!**

Tutorial shuru ho raha hai..."""

        await loading_msg.edit_text(
            created_text,
            parse_mode="Markdown"
        )

        # Start tutorial after a brief delay
        await asyncio.sleep(2)
        await start_tutorial(update, context, user_id)

    except Exception as e:
        logger.error(f"Error creating kingdom: {e}")
        await loading_msg.edit_text(
            "❌ **Error creating kingdom!**\n"
            "Please try again with /start",
            parse_mode="Markdown"
        )
        clear_user_state(user_id)


# ─── Tutorial System ───

async def start_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start the interactive tutorial"""
    try:
        tutorial_text = """📚 **TUTORIAL** (Step 1/3)
━━━━━━━━━━━━━━

💰 **Resource Collection**
Gold Mine se gold ikattha karo!
Yeh aapki kingdom ki growth ka base hai.

👉 **Gold Mine** par click karo → **📥 Collect** dabao

Try karo!"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⛏ Gold Mine — 📥 Collect", callback_data="tutorial_collect")],
        ])

        await context.bot.send_message(
            chat_id=user_id,
            text=tutorial_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        # Mark tutorial step
        state = get_user_state(user_id)
        if not state:
            state = {}
        state["step"] = "tutorial_1"
        set_user_state(user_id, state)

    except Exception as e:
        logger.error(f"Error starting tutorial: {e}")


async def handle_tutorial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tutorial-specific callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    state = get_user_state(user_id) or {}
    tutorial_step = state.get("step", "")

    if data == "tutorial_collect":
        await _handle_tutorial_collect(query, user_id, state)

    elif data == "tutorial_upgrade":
        await _handle_tutorial_upgrade(query, user_id, state)

    elif data == "tutorial_attack":
        await _handle_tutorial_attack(query, user_id, state, context)

    else:
        await query.answer("Tutorial step not recognized")


async def _handle_tutorial_collect(query, user_id: int, state: dict):
    """Handle tutorial collect step"""
    try:
        # Give starter gold bonus
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                kingdom.gold += 100
                db.commit()

        # Move to step 2
        state["step"] = "tutorial_2"
        set_user_state(user_id, state)

        await query.edit_message_text(
            "🎉 **Step 1 Complete!** ✅\n"
            "💰 +100 Gold collected!\n\n"
            "📚 **TUTORIAL** (Step 2/3)\n"
            "━━━━━━━━━━━━━━\n\n"
            "⬆️ **Building Upgrade**\n"
            "Town Hall upgrade karo apni kingdom ka level badhane ke liye!\n\n"
            "Higher level = More features unlocked!\n\n"
            "👉 **Town Hall** → **⬆️ Upgrade** par click karo",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏰 Town Hall — ⬆️ Upgrade", callback_data="tutorial_upgrade")],
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Tutorial collect error: {e}")
        await query.edit_message_text("❌ Error in tutorial. Please /start again.")


async def _handle_tutorial_upgrade(query, user_id: int, state: dict):
    """Handle tutorial upgrade step"""
    try:
        # Simulate instant upgrade
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            building = db.query(Building).filter(
                Building.kingdom_id == user_id,
                Building.building_type == "town_hall"
            ).first()
            if building and kingdom:
                building.level = 2
                kingdom.level = 2
                kingdom.buildings_upgraded = getattr(kingdom, 'buildings_upgraded', 0) + 1
                db.commit()

        state["step"] = "tutorial_3"
        set_user_state(user_id, state)

        await query.edit_message_text(
            "🎉 **Step 2 Complete!** ✅\n"
            "🏰 Town Hall upgraded to Lv.2!\n\n"
            "📚 **TUTORIAL** (Step 3/3)\n"
            "━━━━━━━━━━━━━━\n\n"
            "⚔️ **First Battle**\n"
            "Ek weak AI player par attack karo!\n"
            "Combat system kaise kaam karta hai seekho.\n\n"
            "👉 **Tutorial Battle** par click karo",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Tutorial Battle", callback_data="tutorial_attack")],
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Tutorial upgrade error: {e}")
        await query.edit_message_text("❌ Error in tutorial. Please /start again.")


async def _handle_tutorial_attack(query, user_id: int, state: dict, context: ContextTypes.DEFAULT_TYPE):
    """Handle tutorial battle step"""
    try:
        # Simulate tutorial battle against AI
        with get_db() as db:
            attacker = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if not attacker:
                await query.edit_message_text("❌ Kingdom not found! /start again.")
                return

            # Create a dummy defender (training dummy)
            defender = Kingdom(
                user_id=0,
                name="Training Dummy",
                flag="🎯",
                level=1,
                gold=500,
                food=200,
                energy=0,
                map_x=attacker.map_x,
                map_y=attacker.map_y + 1,
                shield_expires=datetime.utcnow(),
                trait="balanced",
            )
            db.add(defender)
            db.commit()
            db.refresh(defender)

            # Create dummy army
            defender_army = Army(kingdom_id=0, infantry=10, archers=0, cavalry=0)
            db.add(defender_army)
            db.commit()

            # Load attacker army
            attacker_army = db.query(Army).filter(Army.kingdom_id == user_id).first()
            attacker.army = attacker_army
            defender.army = defender_army

            # Load buildings for attacker
            attacker.buildings = db.query(Building).filter(Building.kingdom_id == user_id).all()

            # Simulate battle
            engine = CombatEngine(attacker, defender, is_tutorial=True)
            result = engine.simulate_battle()

            # Process results
            if result["winner"] == "attacker":
                attacker.gold += result["gold_loot"]
                attacker.xp += result["xp_gain"]
                attacker.battles_won = getattr(attacker, 'battles_won', 0) + 1

            # Deduct attacker losses
            if attacker_army:
                attacker_army.infantry = max(0, attacker_army.infantry - result["attacker_losses"]["infantry"])
                attacker_army.archers = max(0, attacker_army.archers - result["attacker_losses"]["archers"])
                attacker_army.cavalry = max(0, attacker_army.cavalry - result["attacker_losses"]["cavalry"])

            # Save battle log
            from bot.models import Battle
            battle = Battle(
                attacker_id=user_id,
                defender_id=0,
                winner_id=user_id if result["winner"] == "attacker" else None,
                battle_log=json.dumps(result.get("rounds", [])),
                gold_looted=result["gold_loot"],
                xp_gained=result["xp_gain"],
                is_tutorial=1,
            )
            db.add(battle)

            # Remove dummy
            db.query(Army).filter(Army.kingdom_id == 0).delete()
            db.query(Kingdom).filter(Kingdom.user_id == 0).delete()
            db.commit()

        # Tutorial complete
        clear_user_state(user_id)

        # Update user
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.tutorial_step = 3
                db.commit()

        # Give tutorial rewards
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                kingdom.gold += 500
                kingdom.food += 200
                kingdom.gems = getattr(kingdom, 'gems', 0) + 1
                db.commit()

        # Show battle result + completion
        battle_summary = (
            f"{result['message']}\n\n"
            f"🎉 **TUTORIAL COMPLETE!**\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"🎁 **Completion Rewards:**\n"
            f"💰 +500 Gold\n"
            f"🍖 +200 Food\n"
            f"💎 +1 Gem\n\n"
            f"✅ Aap taiyaar hain! 👑\n"
            f"Dashboard khul raha hai..."
        )

        await query.edit_message_text(
            battle_summary,
            parse_mode="Markdown"
        )

        # Show dashboard after delay
        await asyncio.sleep(3)
        from bot.handlers.dashboard import render_dashboard
        await render_dashboard(update, context, user_id, new_message=True)

    except Exception as e:
        logger.error(f"Tutorial battle error: {e}")
        await query.edit_message_text(
            "❌ Battle simulation error.\n"
            "Aapka kingdom create ho gaya hai! /dashboard se continue karo.",
            parse_mode="Markdown"
        )
        clear_user_state(user_id)


# ─── Utility Functions ───

async def cancel_user_flow(update: Update, user_id: int):
    """Cancel any active user flow"""
    clear_user_state(user_id)
    await update.message.reply_text(
        "❌ Cancelled.\n\nDashboard ke liye /dashboard type karo.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")]
        ])
    )


# Callback handlers for trait and flag selection (used by router)
async def handle_trait_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, trait: str):
    """Handle trait selection via inline button"""
    # This is used if trait selection is done via buttons instead of text
    pass


async def handle_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, flag: str):
    """Handle flag selection via inline button"""
    pass
