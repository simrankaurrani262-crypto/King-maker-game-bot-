import random
from telegram import Update
from telegram.ext import ContextTypes
from bot.models import get_db, User, Kingdom
from bot.services.game_data import GameData
from bot.utils.keyboards import start_menu_keyboard, trait_selection_keyboard
from bot.utils.validators import validate_kingdom_name
from bot.utils.constants import FLAGS, KINGDOM_TRAITS


# User state tracking for multi-step flows
user_states = {}


async def handler_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - entry point"""
    user = update.effective_user
    
    # Create or get user
    db_user = GameData.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )
    
    # Check if banned
    if db_user.is_banned:
        await update.message.reply_text(
            "⛔ Aapko ban kar diya gaya hai.\nContact admin for help."
        )
        return
    
    # Check if kingdom exists
    kingdom = GameData.get_kingdom(user.id)
    
    if kingdom:
        # Existing player - show dashboard
        from bot.handlers.dashboard import render_dashboard
        await render_dashboard(update, context, user.id)
        return
    
    # New player - welcome
    welcome_text = """⚔️ WELCOME TO KINGDOM CONQUEST ⚔️

👑 बनो एक महान राजा!
🏰 अपना Kingdom बनाओ
⚔️ दुश्मनों पर हमला करो
🏆 सबसे शक्तिशाली बनो!"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=start_menu_keyboard()
    )


async def handle_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "start_game":
        # Start kingdom creation wizard
        user_states[user_id] = {"step": "kingdom_name"}
        await query.edit_message_text(
            "🏰 **Kingdom Creation**\n\n"
            "Apne Kingdom ka naam batao:\n"
            "(3-20 characters, letters/numbers only)\n\n"
            "Type naam message mein bhejo:",
            reply_markup=None
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

Good luck, King! 👑"""
        await query.edit_message_text(
            help_text,
            reply_markup=start_menu_keyboard()
        )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input during multi-step flows"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if user is in a flow
    state = user_states.get(user_id)
    if not state:
        # Not in a flow, ignore or show dashboard
        kingdom = GameData.get_kingdom(user_id)
        if kingdom:
            from bot.handlers.dashboard import render_dashboard
            await render_dashboard(update, context, user_id, new_message=True)
        return
    
    step = state.get("step")
    
    if step == "kingdom_name":
        # Validate name
        valid, error = validate_kingdom_name(text)
        if not valid:
            await update.message.reply_text(f"❌ {error}\n\nDobara try karo:")
            return
        
        # Check uniqueness
        with get_db() as db:
            existing = db.query(Kingdom).filter(Kingdom.name == text).first()
            if existing:
                await update.message.reply_text(
                    "❌ Ye naam pehle se liya gaya hai!\n\nDusra naam try karo:"
                )
                return
        
        # Save name, move to flag selection
        state["kingdom_name"] = text
        state["step"] = "select_flag"
        
        # Show flag grid
        flag_buttons = []
        row = []
        for i, flag in enumerate(FLAGS):
            row.append(f"{flag}")
            if (i + 1) % 4 == 0:
                flag_buttons.append(" ".join(row))
                row = []
        if row:
            flag_buttons.append(" ".join(row))
        
        flag_text = f"🏰 **{text}** — naam approved! ✅\n\n🎌 Ab apna Flag chuno:\n\n"
        flag_text += "\n".join(flag_buttons)
        flag_text += "\n\nFlag ke liye number type karo (1-24):"
        
        state["flags_displayed"] = FLAGS
        await update.message.reply_text(flag_text)
    
    elif step == "select_flag":
        try:
            flag_idx = int(text) - 1
            flags = state.get("flags_displayed", FLAGS)
            if flag_idx < 0 or flag_idx >= len(flags):
                await update.message.reply_text(
                    f"❌ 1 se {len(flags)} ke beech number chuno!"
                )
                return
            
            selected_flag = flags[flag_idx]
            state["flag"] = selected_flag
            state["step"] = "select_trait"
            
            # Show trait selection
            trait_text = f"🏰 **{state['kingdom_name']}** {selected_flag}\n\n"
            trait_text += "⚡ Apna Kingdom Trait chuno:\n\n"
            
            for key, trait in KINGDOM_TRAITS.items():
                trait_text += f"**{trait['name']}**\n{trait['description']}\n\n"
            
            trait_text += "Trait ke liye type karo: aggressive / defensive / rich / balanced"
            
            await update.message.reply_text(trait_text)
        
        except ValueError:
            await update.message.reply_text("❌ Valid number enter karo!")
    
    elif step == "select_trait":
        trait = text.lower().strip()
        if trait not in KINGDOM_TRAITS:
            await update.message.reply_text(
                "❌ Valid trait chuno: aggressive / defensive / rich / balanced"
            )
            return
        
        # Create kingdom!
        kingdom = GameData.create_kingdom(
            user_id=user_id,
            name=state["kingdom_name"],
            flag=state["flag"],
            trait=trait,
        )
        
        # Clear state
        del user_states[user_id]
        
        # Update user tutorial
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.tutorial_step = 1
                db.commit()
        
        # Show created message
        created_text = f"""🎉 **Kingdom Created!**
━━━━━━━━━━━━━━

👑 Kingdom: {kingdom.name} {kingdom.flag}
📍 Location: ({kingdom.map_x}, {kingdom.map_y})
⚡ Trait: {KINGDOM_TRAITS[trait]['name']}

🎁 **Starter Resources:**
💰 {kingdom.gold:,} Gold
🍖 {kingdom.food:,} Food
⚡ {kingdom.energy}/10 Energy
🗡 {50} Infantry

🛡 **24h Newbie Shield active!**

Tutorial shuru ho raha hai..."""
        
        await update.message.reply_text(created_text)
        
        # Start tutorial
        await start_tutorial(update, context, user_id)


async def start_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start the 3-step interactive tutorial"""
    tutorial_text = """📚 **TUTORIAL** (Step 1/3)
━━━━━━━━━━━━━━

💰 **Collect Resources**
Gold Mine se gold ikattha karo!

👉 [🏗 Build] button → Gold Mine → [📥 Collect]

Try karo!"""
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏗 Build", callback_data="tutorial_build")],
    ])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=tutorial_text,
        reply_markup=keyboard
    )
    
    # Mark tutorial step
    user_states[user_id] = {"step": "tutorial_1"}


async def handle_tutorial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tutorial-specific callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    state = user_states.get(user_id, {})
    tutorial_step = state.get("step", "")
    
    if data == "tutorial_build":
        # Show building menu
        await query.edit_message_text(
            "🏗 **Buildings**\n\n"
            "⛏ Gold Mine — Lv.1\n"
            "📥 Collect karne ke liye Gold Mine par click karo!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⛏ Gold Mine — 📥 Collect", callback_data="tutorial_collect")],
            ])
        )
    
    elif data == "tutorial_collect":
        # Give starter gold bonus
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                kingdom.gold += 100
                db.commit()
        
        # Move to step 2
        state["step"] = "tutorial_2"
        
        await query.edit_message_text(
            "🎉 **Step 1 Complete!**\n💰 +100 Gold!\n\n"
            "📚 **TUTORIAL** (Step 2/3)\n━━━━━━━━━━━━━━\n\n"
            "⬆️ **Upgrade Building**\n"
            "Town Hall upgrade karo apni kingdom ka level badhane ke liye!\n\n"
            "👉 [🏰 Town Hall] → [⬆️ Upgrade]",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏰 Town Hall — ⬆️ Upgrade", callback_data="tutorial_upgrade")],
            ])
        )
    
    elif data == "tutorial_upgrade":
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
                db.commit()
        
        state["step"] = "tutorial_3"
        
        await query.edit_message_text(
            "🎉 **Step 2 Complete!**\n🏰 Town Hall Lv.2!\n\n"
            "📚 **TUTORIAL** (Step 3/3)\n━━━━━━━━━━━━━━\n\n"
            "⚔️ **First Attack**\n"
            "Ek weak AI player par attack karo!\n\n"
            "👉 [⚔️ Attack] button → [🎯 Tutorial Battle]",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Tutorial Battle", callback_data="tutorial_attack")],
            ])
        )
    
    elif data == "tutorial_attack":
        # Simulate tutorial battle against AI
        from bot.services.combat_engine import CombatEngine
        from bot.services.game_data import GameData
        
        with get_db() as db:
            attacker = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            
            # Create a dummy defender
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
            )
            db.add(defender)
            db.commit()
            db.refresh(defender)
            
            defender_army = Army(kingdom_id=0, infantry=10)
            db.add(defender_army)
            db.commit()
            
            engine = CombatEngine(attacker, defender, is_tutorial=True)
            result = engine.simulate_battle()
            
            # Process results
            if result["winner"] == "attacker":
                attacker.gold += result["gold_loot"]
                attacker.xp += result["xp_gain"]
                attacker.battles_won += 1
            
            # Deduct attacker losses
            if attacker.army:
                attacker.army.infantry = max(0, attacker.army.infantry - result["attacker_losses"]["infantry"])
                attacker.army.archers = max(0, attacker.army.archers - result["attacker_losses"]["archers"])
                attacker.army.cavalry = max(0, attacker.army.cavalry - result["attacker_losses"]["cavalry"])
            
            # Save battle
            battle = Battle(
                attacker_id=user_id,
                defender_id=0,
                winner_id=user_id if result["winner"] == "attacker" else None,
                battle_log=json.dumps(result["rounds"]),
                gold_looted=result["gold_loot"],
                xp_gained=result["xp_gain"],
                is_tutorial=1,
            )
            db.add(battle)
            db.commit()
            
            # Remove dummy
            db.query(Army).filter(Army.kingdom_id == 0).delete()
            db.query(Kingdom).filter(Kingdom.user_id == 0).delete()
            db.commit()
        
        # Tutorial complete
        del user_states[user_id]
        
        # Update user
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.tutorial_step = 3
                db.commit()
        
        await query.edit_message_text(
            f"{result['message']}\n\n"
            "🎉 **TUTORIAL COMPLETE!**\n"
            "━━━━━━━━━━━━━━\n\n"
            "🎁 **Bonus Rewards:**\n"
            "💰 +500 Gold\n"
            "🍖 +200 Food\n"
            "💎 +1 Gem\n\n"
            "Aap taiyaar hain! 👑\n"
            "Dashboard khul raha hai..."
        )
        
        # Give tutorial rewards
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                kingdom.gold += 500
                kingdom.food += 200
                kingdom.gems += 1
                db.commit()
        
        # Show dashboard
        from bot.handlers.dashboard import render_dashboard
        await render_dashboard(update, context, user_id, new_message=True)
