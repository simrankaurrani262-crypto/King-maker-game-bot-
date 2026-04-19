import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, Kingdom, Army, Battle, Cooldown
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.services.combat_engine import CombatEngine
from bot.utils.formatters import format_number, get_defense_rating_label
from bot.utils.keyboards import (
    attack_menu_keyboard, opponent_keyboard, battle_response_keyboard,
    back_dashboard_keyboard, raid_menu_keyboard
)
from bot.utils.constants import ENERGY_COST_ATTACK, RAID_ENERGY_COST

# Store active battle requests
battle_requests = {}
revenge_opportunities = {}


async def show_attack_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show attack mode menu"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        await query.edit_message_text("❌ Kingdom not found!", reply_markup=back_dashboard_keyboard())
        return
    
    text = "⚔️ **ATTACK MODE**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"⚡ Energy: {kingdom.energy}/10\n"
    text += f"⚔️ Army: {kingdom.army.total if kingdom.army else 0}\n\n"
    text += "Choose option:"
    
    await query.edit_message_text(text, reply_markup=attack_menu_keyboard())


async def handle_attack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle attack menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_attack":
        await show_attack_menu(update, context, user_id)
    
    elif data == "attack_find":
        await find_opponent(update, context, user_id)
    
    elif data == "attack_next":
        await find_opponent(update, context, user_id, skip=1)
    
    elif data.startswith("attack_player:"):
        target_id = int(data.split(":")[1])
        await initiate_attack(update, context, user_id, target_id)
    
    elif data.startswith("battle_accept:"):
        request_id = data.split(":")[1]
        await accept_battle(update, context, request_id)
    
    elif data.startswith("battle_decline:"):
        request_id = data.split(":")[1]
        await decline_battle(update, context, request_id)
    
    elif data == "attack_revenge":
        await show_revenge(update, context, user_id)
    
    elif data.startswith("revenge_attack:"):
        target_id = int(data.split(":")[1])
        await execute_revenge(update, context, user_id, target_id)
    
    elif data == "attack_raid":
        await show_raid_menu(update, context, user_id)
    
    elif data == "raid_find":
        await find_raid_target(update, context, user_id)
    
    elif data.startswith("raid_player:"):
        target_id = int(data.split(":")[1])
        await execute_raid(update, context, user_id, target_id)
    
    elif data == "attack_map":
        from bot.handlers.map_system import show_map_menu
        await show_map_menu(update, context, user_id)


async def find_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, skip=0):
    """Find a suitable opponent"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return
    
    if kingdom.energy < ENERGY_COST_ATTACK:
        await query.answer("❌ Energy kam hai!")
        await query.edit_message_text(
            "❌ **Energy kam hai!**\n"
            f"⚡ {kingdom.energy}/10 — Attack ke liye 1 Energy chahiye!\n"
            "⏳ Energy har 30 min mein regenerate hoti hai!",
            reply_markup=attack_menu_keyboard()
        )
        return
    
    # Find opponents
    candidates = GameData.find_opponents(user_id, limit=5)
    
    if not candidates:
        await query.edit_message_text(
            "❌ **No opponents found!**\n\n"
            "Koi suitable opponent nahi mila.\n"
            "Thodi der baad try karo!",
            reply_markup=attack_menu_keyboard()
        )
        return
    
    # Store candidates in user context
    context.user_data["opponents"] = [c[0].user_id for c in candidates]
    context.user_data["current_opponent_idx"] = skip % len(candidates)
    
    candidate, power, distance = candidates[skip % len(candidates)]
    
    defense_power = EconomyService.calculate_defense_rating(candidate)
    defense_label = get_defense_rating_label(defense_power)
    
    # Estimate army (obfuscated)
    estimated_army = candidate.army.total if candidate.army else 0
    obfuscated = max(10, estimated_army + random.randint(-10, 10))
    
    text = f"""⚔️ **OPPONENT FOUND**
━━━━━━━━━━━━━━
👑 Kingdom: {candidate.name} {candidate.flag}
🏆 Level: {candidate.level}
⚔️ Army: ~{obfuscated} (estimated)
🛡 Defense: {defense_label}
📍 Distance: {distance} tiles
━━━━━━━━━━━━━━"""
    
    keyboard = opponent_keyboard(candidate.user_id)
    await query.edit_message_text(text, reply_markup=keyboard)


async def initiate_attack(update: Update, context: ContextTypes.DEFAULT_TYPE, attacker_id: int, defender_id: int):
    """Send battle request to defender"""
    query = update.callback_query
    
    attacker = GameData.get_kingdom_with_relations(attacker_id)
    defender = GameData.get_kingdom_with_relations(defender_id)
    
    if not attacker or not defender:
        await query.answer("❌ Error!")
        return
    
    if attacker.energy < ENERGY_COST_ATTACK:
        await query.answer("❌ Energy kam hai!")
        return
    
    if defender.has_shield:
        await query.answer("🛡 Defender ke paas shield hai!")
        return
    
    # Create battle request
    import uuid
    request_id = str(uuid.uuid4())
    battle_requests[request_id] = {
        "attacker_id": attacker_id,
        "defender_id": defender_id,
        "timestamp": datetime.utcnow(),
        "status": "pending"
    }
    
    # Send to attacker
    await query.edit_message_text(
        f"⚔️ **Battle Request Sent!**\n\n"
        f"👑 {defender.name} ko challenge bheja gaya!\n"
        f"⏳ 30 seconds mein accept/decline karega...",
        reply_markup=back_dashboard_keyboard()
    )
    
    # Send to defender
    try:
        await context.bot.send_message(
            chat_id=defender_id,
            text=f"""⚔️ **WAR DECLARATION!**
━━━━━━━━━━━━━━
@{attacker.name} wants to attack your kingdom!
⚔️ Their Army: ~{attacker.army.total if attacker.army else 0}
🛡 Your Defense: {get_defense_rating_label(EconomyService.calculate_defense_rating(defender))}
━━━━━━━━━━━━━━
⏳ Auto-defend in 30 seconds!""",
            reply_markup=battle_response_keyboard(request_id)
        )
    except Exception:
        # Defender can't be reached, auto-win for attacker
        battle_requests[request_id]["status"] = "auto"
        await execute_battle(context, request_id)
        return
    
    # Schedule auto-defend
    context.job_queue.run_once(
        auto_defend_battle,
        when=30,
        data={'request_id': request_id},
        name=f"battle_{request_id}"
    )


async def accept_battle(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: str):
    """Defender accepts the battle"""
    query = update.callback_query
    
    request = battle_requests.get(request_id)
    if not request or request["status"] != "pending":
        await query.answer("❌ Battle expired!")
        return
    
    request["status"] = "accepted"
    await query.answer("✅ Battle accepted!")
    await query.edit_message_text("⚔️ **BATTLE STARTING...**")
    
    await execute_battle(context, request_id)


async def decline_battle(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: str):
    """Defender declines the battle"""
    query = update.callback_query
    
    request = battle_requests.get(request_id)
    if not request or request["status"] != "pending":
        await query.answer("❌ Battle expired!")
        return
    
    request["status"] = "declined"
    await query.answer("❌ Battle declined")
    
    attacker_id = request["attacker_id"]
    defender_id = request["defender_id"]
    
    # Notify attacker
    try:
        await context.bot.send_message(
            chat_id=attacker_id,
            text=f"❌ **@{defender_id} declined the battle!**\nNo energy lost."
        )
    except Exception:
        pass
    
    await query.edit_message_text("❌ You declined the battle. Minor reputation penalty applied.")


async def auto_defend_battle(context: ContextTypes.DEFAULT_TYPE):
    """Auto-defend if defender didn't respond"""
    job_data = context.job.data
    request_id = job_data['request_id']
    
    request = battle_requests.get(request_id)
    if not request or request["status"] != "pending":
        return
    
    request["status"] = "auto"
    await execute_battle(context, request_id)


async def execute_battle(context: ContextTypes.DEFAULT_TYPE, request_id: str):
    """Execute the battle"""
    request = battle_requests.get(request_id)
    if not request:
        return
    
    attacker_id = request["attacker_id"]
    defender_id = request["defender_id"]
    is_revenge = request.get("is_revenge", False)
    
    with get_db() as db:
        attacker = db.query(Kingdom).filter(Kingdom.user_id == attacker_id).first()
        defender = db.query(Kingdom).filter(Kingdom.user_id == defender_id).first()
        
        if not attacker or not defender:
            return
        
        # Load relationships
        attacker.army = db.query(Army).filter(Army.kingdom_id == attacker_id).first()
        defender.army = db.query(Army).filter(Army.kingdom_id == defender_id).first()
        
        # Run combat engine
        engine = CombatEngine(attacker, defender, is_revenge=is_revenge)
        result = engine.simulate_battle()
        
        # Apply results
        if result["winner"] == "attacker":
            attacker.gold += result["gold_loot"]
            attacker.xp += result["xp_gain"]
            attacker.battles_won += 1
            attacker.total_gold_looted += result["gold_loot"]
            defender.gold = max(0, defender.gold - result["gold_loot"])
            defender.battles_lost += 1
            
            # Remove defender shield on loss
            defender.shield_expires = datetime.utcnow()
            
            # Check for building damage (30% chance)
            if random.random() < 0.3:
                damage_building = random.choice(["gold_mine", "farm", "barracks"])
                building = db.query(Building).filter(
                    Building.kingdom_id == defender_id,
                    Building.building_type == damage_building
                ).first()
                if building and building.level > 1:
                    building.level -= 1
                    try:
                        await context.bot.send_message(
                            chat_id=defender_id,
                            text=f"💥 **Building Damaged!**\nYour {building.display_name} was damaged! Level -1!"
                        )
                    except Exception:
                        pass
        else:
            defender.xp += result["xp_gain"]
            defender.battles_won += 1
            attacker.battles_lost += 1
            attacker.xp += 25  # Participation XP
        
        # Deduct losses
        if attacker.army:
            attacker.army.infantry = max(0, attacker.army.infantry - result["attacker_losses"]["infantry"])
            attacker.army.archers = max(0, attacker.army.archers - result["attacker_losses"]["archers"])
            attacker.army.cavalry = max(0, attacker.army.cavalry - result["attacker_losses"]["cavalry"])
        
        if defender.army:
            defender.army.infantry = max(0, defender.army.infantry - result["defender_losses"]["infantry"])
            defender.army.archers = max(0, defender.army.archers - result["defender_losses"]["archers"])
            defender.army.cavalry = max(0, defender.army.cavalry - result["defender_losses"]["cavalry"])
        
        # Deduct energy from attacker
        attacker.energy = max(0, attacker.energy - ENERGY_COST_ATTACK)
        
        # Save battle
        import json
        battle = Battle(
            attacker_id=attacker_id,
            defender_id=defender_id,
            winner_id=attacker_id if result["winner"] == "attacker" else defender_id,
            battle_log=json.dumps(result["rounds"]),
            gold_looted=result["gold_loot"],
            xp_gained=result["xp_gain"],
            attacker_infantry_lost=result["attacker_losses"]["infantry"],
            attacker_archers_lost=result["attacker_losses"]["archers"],
            attacker_cavalry_lost=result["attacker_losses"]["cavalry"],
            defender_infantry_lost=result["defender_losses"]["infantry"],
            defender_archers_lost=result["defender_losses"]["archers"],
            defender_cavalry_lost=result["defender_losses"]["cavalry"],
            is_revenge=1 if is_revenge else 0,
        )
        db.add(battle)
        
        # Check level up
        from bot.utils.formatters import calculate_xp_needed, get_level_from_xp
        xp_needed = calculate_xp_needed(attacker.level)
        while attacker.xp >= xp_needed:
            attacker.xp -= xp_needed
            attacker.level += 1
            xp_needed = calculate_xp_needed(attacker.level)
            try:
                await context.bot.send_message(
                    chat_id=attacker_id,
                    text=f"🎉 **LEVEL UP!**\n🏆 You are now Level {attacker.level}!"
                )
            except Exception:
                pass
        
        db.commit()
    
    # Send results
    try:
        await context.bot.send_message(chat_id=attacker_id, text=result["message"])
    except Exception:
        pass
    
    try:
        await context.bot.send_message(chat_id=defender_id, text=result["message"])
    except Exception:
        pass
    
    # Create revenge opportunity for defender
    if result["winner"] == "attacker":
        revenge_key = f"{defender_id}:{attacker_id}"
        revenge_opportunities[revenge_key] = {
            "attacker_id": defender_id,
            "target_id": attacker_id,
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "used": False,
        }
        
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔥 Revenge!", callback_data=f"revenge_attack:{attacker_id}")],
            ])
            await context.bot.send_message(
                chat_id=defender_id,
                text=f"🔥 **REVENGE AVAILABLE!**\n@{attacker.name} ne aap par hamla kiya!\n1 ghante mein badla lo!",
                reply_markup=keyboard
            )
        except Exception:
            pass


async def show_revenge(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show available revenge targets"""
    query = update.callback_query
    
    available = []
    now = datetime.utcnow()
    for key, rev in list(revenge_opportunities.items()):
        if rev["attacker_id"] == user_id and not rev["used"] and rev["expires_at"] > now:
            target = GameData.get_kingdom(rev["target_id"])
            if target:
                remaining = rev["expires_at"] - now
                minutes = int(remaining.total_seconds() / 60)
                available.append((target, minutes))
    
    if not available:
        await query.edit_message_text(
            "🔥 **No Revenge Available**\n\n"
            "Koi active revenge opportunity nahi hai!\n"
            "Attack hone par yahan dikhayi dega.",
            reply_markup=attack_menu_keyboard()
        )
        return
    
    text = "🔥 **REVENGE LIST**\n━━━━━━━━━━━━━━\n\n"
    buttons = []
    for target, minutes in available:
        text += f"👑 {target.name} {target.flag} — {minutes}m left\n"
        buttons.append([InlineKeyboardButton(f"🔥 Attack {target.name}", callback_data=f"revenge_attack:{target.user_id}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_attack")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def execute_revenge(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, target_id: int):
    """Execute revenge attack"""
    query = update.callback_query
    
    revenge_key = f"{user_id}:{target_id}"
    revenge = revenge_opportunities.get(revenge_key)
    
    if not revenge or revenge["used"] or revenge["expires_at"] < datetime.utcnow():
        await query.answer("❌ Revenge samay samapt ho gaya!")
        return
    
    revenge["used"] = True
    
    # Set as revenge in battle request
    import uuid
    request_id = str(uuid.uuid4())
    battle_requests[request_id] = {
        "attacker_id": user_id,
        "defender_id": target_id,
        "timestamp": datetime.utcnow(),
        "status": "accepted",
        "is_revenge": True,
    }
    
    await query.answer("⚔️ Revenge battle starting!")
    await query.edit_message_text("🔥 **REVENGE BATTLE!**\n⚔️ Battle starting...")
    
    await execute_battle(context, request_id)


async def show_raid_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show raid menu"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    
    text = "🏃 **QUICK RAID**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"⚡ Energy: {kingdom.energy}/10\n"
    text += f"⚔️ Army: {kingdom.army.total if kingdom.army else 0}\n\n"
    text += "Quick raid mein kam reward, kam risk!\n"
    text += "15% resources steal ho sakte hain!"
    
    await query.edit_message_text(text, reply_markup=raid_menu_keyboard())


async def find_raid_target(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Find raid target"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom or kingdom.energy < RAID_ENERGY_COST:
        await query.answer("❌ Energy kam hai!")
        return
    
    candidates = GameData.find_opponents(user_id, limit=3)
    if not candidates:
        await query.edit_message_text(
            "❌ **No raid targets found!**",
            reply_markup=attack_menu_keyboard()
        )
        return
    
    text = "🏃 **SELECT RAID TARGET**\n━━━━━━━━━━━━━━\n\n"
    buttons = []
    for candidate, power, distance in candidates:
        text += f"👑 {candidate.name} {candidate.flag} — Lv.{candidate.level}\n"
        buttons.append([InlineKeyboardButton(
            f"🏃 Raid {candidate.name}",
            callback_data=f"raid_player:{candidate.user_id}"
        )])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="attack_raid")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def execute_raid(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, target_id: int):
    """Execute a quick raid"""
    query = update.callback_query
    
    attacker = GameData.get_kingdom_with_relations(user_id)
    defender = GameData.get_kingdom_with_relations(target_id)
    
    if not attacker or not defender:
        await query.answer("❌ Error!")
        return
    
    if attacker.energy < RAID_ENERGY_COST:
        await query.answer("❌ Energy kam hai!")
        return
    
    # Run raid simulation
    engine = CombatEngine(attacker, defender, is_raid=True)
    result = engine.simulate_raid()
    
    with get_db() as db:
        attacker = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        defender = db.query(Kingdom).filter(Kingdom.user_id == target_id).first()
        
        if result["success"]:
            attacker.gold += result["gold_stolen"]
            attacker.food += result["food_stolen"]
            attacker.total_gold_looted += result["gold_stolen"]
            defender.gold = max(0, defender.gold - result["gold_stolen"])
            defender.food = max(0, defender.food - result["food_stolen"])
        
        # Deduct army loss
        if attacker.army and result["army_loss"] > 0:
            attacker.army.infantry = max(0, attacker.army.infantry - result["army_loss"])
        
        # Deduct energy
        attacker.energy = max(0, attacker.energy - RAID_ENERGY_COST)
        
        # Save as battle
        battle = Battle(
            attacker_id=user_id,
            defender_id=target_id,
            winner_id=user_id if result["success"] else target_id,
            gold_looted=result["gold_stolen"],
            is_raid=1,
        )
        db.add(battle)
        db.commit()
    
    await query.edit_message_text(result["message"], reply_markup=back_dashboard_keyboard())
    
    # Notify defender
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🚨 **RAID ALERT!**\n🏃 @{attacker.name} ne raid kiya!\n💰 -{result['gold_stolen']:,} Gold stolen!\n🍖 -{result['food_stolen']:,} Food stolen!"
        )
    except Exception:
        pass
