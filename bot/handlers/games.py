import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, Kingdom, WorldEvent
from bot.services.game_data import GameData
from bot.utils.keyboards import (
    games_menu_keyboard, dice_keyboard, spin_keyboard,
    black_market_keyboard, back_dashboard_keyboard, decision_keyboard
)
from bot.utils.constants import (
    DICE_COOLDOWN_HOURS, SPIN_COOLDOWN_HOURS, QUIZ_COOLDOWN_HOURS,
    BLACK_MARKET_ITEMS, BLACK_MARKET_REFRESH_HOURS,
    SPIN_WHEEL_ITEMS, QUIZ_QUESTIONS, DECISION_EVENTS,
    SURVIVAL_WAVES
)


async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show mini-games menu"""
    query = update.callback_query
    
    text = "🎲 **MINI-GAMES**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += "🎲 **Dice Game** — Test your luck!\n"
    text += "🎰 **Lucky Spin** — Free rewards!\n"
    text += "🧠 **Kingdom Quiz** — Test your knowledge!\n"
    text += "⚔️ **Survival Mode** — Co-op PvE!\n\n"
    text += "🏪 **Black Market** — Secret deals!"
    
    await query.edit_message_text(text, reply_markup=games_menu_keyboard())


async def handle_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle games menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_games":
        await show_games_menu(update, context, user_id)
    
    elif data == "game_dice":
        await show_dice_game(update, context, user_id)
    
    elif data.startswith("dice_bet:"):
        bet = int(data.split(":")[1])
        await roll_dice(update, context, user_id, bet)
    
    elif data == "game_spin":
        await show_spin_wheel(update, context, user_id)
    
    elif data == "spin_wheel":
        await spin_wheel(update, context, user_id)
    
    elif data == "game_quiz":
        await show_quiz(update, context, user_id)
    
    elif data.startswith("quiz_answer:"):
        parts = data.split(":")
        q_idx = int(parts[1])
        answer = int(parts[2])
        await check_quiz_answer(update, context, user_id, q_idx, answer)
    
    elif data == "game_survival":
        await show_survival_mode(update, context, user_id)
    
    elif data == "game_market":
        await show_black_market(update, context, user_id)
    
    elif data == "market_buy":
        await buy_market_item(update, context, user_id)
    
    elif data.startswith("decision:"):
        parts = data.split(":")
        event_id = parts[1]
        choice = parts[2]
        await resolve_decision(update, context, user_id, event_id, choice)


async def show_dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show dice game"""
    query = update.callback_query
    
    # Check cooldown
    cooldown = GameData.get_cooldown(user_id, "dice")
    cooldown_text = ""
    if cooldown and cooldown > datetime.utcnow():
        remaining = cooldown - datetime.utcnow()
        mins = int(remaining.total_seconds() // 60)
        cooldown_text = f"\n⏳ Cooldown: {mins}m\n"
    
    text = "🎲 **DICE GAME**\n"
    text += "━━━━━━━━━━━━━━\n"
    text += cooldown_text
    text += "\n🎲 Roll the dice!\n\n"
    text += "1-2: ❌ Lose your bet\n"
    text += "3-4: ➡️ Keep your bet\n"
    text += "5: 💰 Win 2x your bet\n"
    text += "6: 🔥 Win 5x your bet!\n"
    text += "\nCooldown: 4h per roll"
    
    await query.edit_message_text(text, reply_markup=dice_keyboard())


async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet: int):
    """Roll the dice"""
    query = update.callback_query
    
    # Check cooldown
    cooldown = GameData.get_cooldown(user_id, "dice")
    if cooldown and cooldown > datetime.utcnow():
        remaining = cooldown - datetime.utcnow()
        mins = int(remaining.total_seconds() // 60)
        await query.answer(f"⏳ {mins}m cooldown left!")
        return
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return
        
        if kingdom.gold < bet:
            await query.answer(f"❌ {bet} Gold chahiye!")
            return
        
        # Set cooldown
        GameData.set_cooldown(user_id, "dice", DICE_COOLDOWN_HOURS * 60)
        
        # Roll
        roll = random.randint(1, 6)
        
        if roll <= 2:
            kingdom.gold -= bet
            result = f"❌ **{roll}** — You lost {bet} Gold!"
        elif roll <= 4:
            result = f"➡️ **{roll}** — Bet returned!"
        elif roll == 5:
            winnings = bet * 2
            kingdom.gold += winnings
            result = f"💰 **{roll}** — You won {winnings} Gold!"
        else:
            winnings = bet * 5
            kingdom.gold += winnings
            result = f"🔥 **{roll}** — JACKPOT! You won {winnings} Gold!"
        
        db.commit()
    
    text = f"🎲 **DICE ROLLED: {roll}**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += f"{result}\n\n"
    text += f"💰 Gold: {kingdom.gold:,}"
    
    await query.edit_message_text(text, reply_markup=dice_keyboard())


async def show_spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show lucky spin"""
    query = update.callback_query
    
    cooldown = GameData.get_cooldown(user_id, "spin")
    cooldown_text = ""
    if cooldown and cooldown > datetime.utcnow():
        remaining = cooldown - datetime.utcnow()
        mins = int(remaining.total_seconds() // 60)
        cooldown_text = f"⏳ Cooldown: {mins}m\n"
    
    text = "🎰 **LUCKY SPIN**\n"
    text += "━━━━━━━━━━━━━━\n"
    text += cooldown_text
    text += "\n💎 50 Gems    | 💰 5000 Gold\n"
    text += "🍖 2000 Food  | ⚡ Full Energy\n"
    text += "🛡 12h Shield | 🎁 Mystery Box\n"
    text += "❌ Nothing\n"
    text += "\nFree every 8h!"
    
    await query.edit_message_text(text, reply_markup=spin_keyboard())


async def spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Spin the wheel"""
    query = update.callback_query
    
    cooldown = GameData.get_cooldown(user_id, "spin")
    if cooldown and cooldown > datetime.utcnow():
        remaining = cooldown - datetime.utcnow()
        mins = int(remaining.total_seconds() // 60)
        await query.answer(f"⏳ {mins}m cooldown left!")
        return
    
    # Weighted random selection
    roll = random.random()
    cumulative = 0
    selected = None
    
    for item in SPIN_WHEEL_ITEMS:
        cumulative += item["chance"]
        if roll <= cumulative:
            selected = item
            break
    
    if not selected:
        selected = SPIN_WHEEL_ITEMS[-1]
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return
        
        GameData.set_cooldown(user_id, "spin", SPIN_COOLDOWN_HOURS * 60)
        
        result_text = f"🎰 **Result: {selected['name']}**\n"
        
        if selected.get("gold"):
            kingdom.gold += selected["gold"]
            result_text += f"💰 +{selected['gold']:,} Gold!\n"
        elif selected.get("food"):
            kingdom.food += selected["food"]
            result_text += f"🍖 +{selected['food']:,} Food!\n"
        elif selected.get("gems"):
            kingdom.gems += selected["gems"]
            result_text += f"💎 +{selected['gems']} Gems!\n"
        elif selected.get("energy"):
            kingdom.energy = min(kingdom.max_energy, kingdom.energy + selected["energy"])
            result_text += f"⚡ Energy restored!\n"
        elif selected.get("shield_hours"):
            kingdom.shield_expires = datetime.utcnow() + timedelta(hours=selected["shield_hours"])
            result_text += f"🛡 +{selected['shield_hours']}h Shield!\n"
        elif selected.get("mystery"):
            mystery_gold = random.randint(100, 5000)
            kingdom.gold += mystery_gold
            result_text += f"🎁 Mystery Box: +{mystery_gold:,} Gold!\n"
        else:
            result_text += "Better luck next time!\n"
        
        db.commit()
    
    result_text += f"\n💰 Gold: {kingdom.gold:,}"
    
    await query.edit_message_text(result_text, reply_markup=spin_keyboard())


async def show_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show quiz question"""
    query = update.callback_query
    
    cooldown = GameData.get_cooldown(user_id, "quiz")
    if cooldown and cooldown > datetime.utcnow():
        remaining = cooldown - datetime.utcnow()
        mins = int(remaining.total_seconds() // 60)
        await query.answer(f"⏳ {mins}m cooldown left!")
        return
    
    # Pick random question
    question = random.choice(QUIZ_QUESTIONS)
    q_idx = QUIZ_QUESTIONS.index(question)
    
    from bot.utils.keyboards import quiz_keyboard
    
    text = "🧠 **KINGDOM QUIZ**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += f"❓ {question['question']}\n\n"
    text += "Sahi jawab = 💰 200 Gold + ⭐ 50 XP"
    
    await query.edit_message_text(
        text,
        reply_markup=quiz_keyboard(q_idx, question["options"])
    )


async def check_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, q_idx: int, answer: int):
    """Check quiz answer"""
    query = update.callback_query
    
    if q_idx < 0 or q_idx >= len(QUIZ_QUESTIONS):
        return
    
    question = QUIZ_QUESTIONS[q_idx]
    correct = answer == question["correct"]
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return
        
        GameData.set_cooldown(user_id, "quiz", QUIZ_COOLDOWN_HOURS * 60)
        
        if correct:
            kingdom.gold += 200
            kingdom.xp += 50
            result = "✅ **Sahi jawab!**\n💰 +200 Gold\n⭐ +50 XP"
        else:
            correct_answer = question["options"][question["correct"]]
            result = f"❌ **Galat jawab!**\nSahi answer tha: **{correct_answer}**\nKoi baat nahi, try again!"
        
        db.commit()
    
    text = f"🧠 **QUIZ RESULT**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += f"{result}\n\n"
    text += f"💰 Gold: {kingdom.gold:,}"
    
    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


async def show_survival_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show survival mode"""
    query = update.callback_query
    
    text = "⚔️ **SURVIVAL MODE**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += "Alliance members ke saath mil kar\n"
    text += "waves of enemies ko defeat karo!\n\n"
    
    for wave in SURVIVAL_WAVES:
        text += f"Wave {wave['wave']}: {wave['enemies']} {wave['type']} — 💰 {wave['reward_gold']:,}\n"
    
    text += "\n🚧 **Coming Soon!**\n"
    text += "Survival mode abhi development mein hai!"
    
    await query.edit_message_text(text, reply_markup=back_dashboard_keyboard())


async def show_black_market(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show black market"""
    query = update.callback_query
    
    # Generate items
    items = random.sample(BLACK_MARKET_ITEMS, k=min(4, len(BLACK_MARKET_ITEMS)))
    
    text = "🏪 **BLACK MARKET**\n"
    text += "━━━━━━━━━━━━━━\n"
    text += "🌙 Secret deals... shhh!\n\n"
    
    for i, item in enumerate(items):
        text += f"{i+1}. {item['name']} — 💎 {item['price_gems']} ({item['stock']} left)\n"
    
    text += f"\n⏳ Refresh: har {BLACK_MARKET_REFRESH_HOURS} hours"
    
    await query.edit_message_text(text, reply_markup=black_market_keyboard())


async def buy_market_item(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Buy from black market"""
    query = update.callback_query
    
    items = random.sample(BLACK_MARKET_ITEMS, k=4)
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return
        
        # Buy first available item (simplified)
        item = items[0]
        if kingdom.gems < item["price_gems"]:
            await query.answer(f"❌ {item['price_gems']} Gems chahiye!")
            return
        
        kingdom.gems -= item["price_gems"]
        
        # Apply effect
        if item["effect"] == "refill_energy":
            kingdom.energy = kingdom.max_energy
            result = "⚡ Energy refilled!"
        elif item["effect"] == "extend_shield":
            kingdom.shield_expires = datetime.utcnow() + timedelta(hours=24)
            result = "🛡 24h Shield activated!"
        elif item["effect"] == "add_gold":
            kingdom.gold += 10000
            result = "💰 +10,000 Gold!"
        else:
            result = f"{item['name']} khareeda!"
        
        db.commit()
    
    await query.answer("✅ Item khareeda!")
    await query.edit_message_text(
        f"🏪 **Purchase Successful!**\n\n{result}\n\n💎 Gems left: {kingdom.gems}",
        reply_markup=black_market_keyboard()
    )


async def resolve_decision(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, event_id: str, choice: str):
    """Resolve a decision event"""
    query = update.callback_query
    
    event = None
    for e in DECISION_EVENTS:
        if e["id"] == event_id:
            event = e
            break
    
    if not event:
        return
    
    outcome = event["outcomes"].get(choice, {"message": "Kuch nahi hua!"})
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        if not kingdom:
            return
        
        if "gold" in outcome:
            kingdom.gold += outcome["gold"]
        if "infantry" in outcome:
            if kingdom.army:
                kingdom.army.infantry += outcome["infantry"]
        
        db.commit()
    
    message = outcome.get("message", "Kuch nahi hua!")
    
    await query.edit_message_text(
        f"🎲 **Decision Result**\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{message}\n\n"
        f"💰 Gold: {kingdom.gold:,}",
        reply_markup=back_dashboard_keyboard()
    )
