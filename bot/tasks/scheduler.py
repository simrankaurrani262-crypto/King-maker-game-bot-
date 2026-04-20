from datetime import datetime, timedelta
from telegram.ext import Application, ContextTypes
import random


def setup_scheduler(application: Application):
    """Setup all background scheduled tasks"""
    job_queue = application.job_queue
    
    # Energy regeneration - every 30 minutes
    job_queue.run_repeating(
        energy_regen_task,
        interval=timedelta(minutes=30),
        first=timedelta(minutes=30),
        name="energy_regen"
    )
    
    # Food consumption - every hour
    job_queue.run_repeating(
        food_consumption_task,
        interval=timedelta(hours=1),
        first=timedelta(hours=1),
        name="food_consumption"
    )
    
    # Daily quest reset - at midnight UTC
    now = datetime.utcnow()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    seconds_until_midnight = (midnight - now).total_seconds()
    
    job_queue.run_repeating(
        daily_quest_reset_task,
        interval=timedelta(days=1),
        first=timedelta(seconds=seconds_until_midnight),
        name="daily_quest_reset"
    )
    
    # Building upgrade completion check - every minute
    job_queue.run_repeating(
        building_upgrade_task,
        interval=timedelta(minutes=1),
        first=timedelta(minutes=1),
        name="building_upgrades"
    )
    
    # Random world event - every 15 minutes
    job_queue.run_repeating(
        world_event_task,
        interval=timedelta(minutes=15),
        first=timedelta(minutes=15),
        name="world_events"
    )
    
    # NPC attack - every 20 minutes
    job_queue.run_repeating(
        npc_attack_task,
        interval=timedelta(minutes=20),
        first=timedelta(minutes=20),
        name="npc_attacks"
    )
    
    # Leaderboard snapshot - daily at 23:55
    leaderboard_time = now.replace(hour=23, minute=55, second=0, microsecond=0)
    if leaderboard_time <= now:
        leaderboard_time += timedelta(days=1)
    lb_seconds = (leaderboard_time - now).total_seconds()
    
    job_queue.run_repeating(
        leaderboard_snapshot_task,
        interval=timedelta(days=1),
        first=timedelta(seconds=lb_seconds),
        name="leaderboard_snapshot"
    )
    
    # Black market refresh - every 6 hours
    job_queue.run_repeating(
        black_market_refresh_task,
        interval=timedelta(hours=6),
        first=timedelta(hours=6),
        name="black_market_refresh"
    )
    
    # Inactive player cleanup - daily at 3 AM
    cleanup_time = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if cleanup_time <= now:
        cleanup_time += timedelta(days=1)
    cleanup_seconds = (cleanup_time - now).total_seconds()
    
    job_queue.run_repeating(
        inactive_cleanup_task,
        interval=timedelta(days=1),
        first=timedelta(seconds=cleanup_seconds),
        name="inactive_cleanup"
    )
    
    # Decision event trigger - every 6 hours (10% chance)
    job_queue.run_repeating(
        decision_event_task,
        interval=timedelta(hours=6),
        first=timedelta(hours=6),
        name="decision_events"
    )


async def energy_regen_task(context: ContextTypes.DEFAULT_TYPE):
    """Regenerate energy for all players"""
    from bot.models import get_db, Kingdom
    from bot.config import config
    
    with get_db() as db:
        kingdoms = db.query(Kingdom).filter(Kingdom.energy < config.MAX_ENERGY).all()
        
        for k in kingdoms:
            k.energy = min(config.MAX_ENERGY, k.energy + 1)
        
        db.commit()
    
    print(f"[TASK] Energy regen: {len(kingdoms)} kingdoms")


async def food_consumption_task(context: ContextTypes.DEFAULT_TYPE):
    """Process food consumption and starvation"""
    from bot.models import get_db, Kingdom
    from bot.services.economy import EconomyService
    
    with get_db() as db:
        kingdoms = db.query(Kingdom).all()
        starved = 0
        
        for k in kingdoms:
            if k.army and k.army.total > 0:
                consumption = EconomyService.calculate_food_consumption(k.army)
                if k.food >= consumption:
                    k.food -= consumption
                else:
                    # Starvation
                    desertion_rate = 0.10
                    k.army.infantry = int(k.army.infantry * (1 - desertion_rate))
                    k.army.archers = int(k.army.archers * (1 - desertion_rate))
                    k.army.cavalry = int(k.army.cavalry * (1 - desertion_rate))
                    k.food = 0
                    starved += 1
                    
                    # Notify
                    try:
                        await context.bot.send_message(
                            chat_id=k.user_id,
                            text="⚠️ **FOOD SHORTAGE!**\n"
                                 "Bhukh ke kaaran se bhaag gayi!\n"
                                 "🍖 Food collect karo!"
                        )
                    except Exception:
                        pass
        
        db.commit()
    
    print(f"[TASK] Food consumption: {starved} kingdoms starved")


async def daily_quest_reset_task(context: ContextTypes.DEFAULT_TYPE):
    """Reset daily quests"""
    from bot.models import get_db, UserQuest, Quest
    from datetime import datetime, timedelta
    
    with get_db() as db:
        daily_quests = db.query(Quest).filter(Quest.quest_type == "daily").all()
        
        for quest in daily_quests:
            user_quests = db.query(UserQuest).filter(UserQuest.quest_id == quest.id).all()
            for uq in user_quests:
                uq.progress = 0
                uq.completed = False
                uq.claimed = False
                uq.reset_at = datetime.utcnow() + timedelta(days=1)
        
        db.commit()
    
    print("[TASK] Daily quests reset")


async def building_upgrade_task(context: ContextTypes.DEFAULT_TYPE):
    """Complete building upgrades"""
    from bot.models import get_db, Building
    from datetime import datetime
    
    with get_db() as db:
        upgrading = db.query(Building).filter(
            Building.is_upgrading == True,
            Building.upgrade_completes <= datetime.utcnow()
        ).all()
        
        for building in upgrading:
            building.level += 1
            building.is_upgrading = False
            building.upgrade_started = None
            building.upgrade_completes = None
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=building.kingdom_id,
                    text=f"✅ **{building.display_name}** is now **Level {building.level}**!"
                )
            except Exception:
                pass
        
        db.commit()
    
    if upgrading:
        print(f"[TASK] Building upgrades completed: {len(upgrading)}")


async def world_event_task(context: ContextTypes.DEFAULT_TYPE):
    """Spawn random world events"""
    from bot.models import get_db, WorldEvent
    from datetime import datetime, timedelta
    
    events = [
        {"type": "treasure", "name": "💎 Hidden Treasure", "desc": "Sab players ko +500 Gold mila!"},
        {"type": "plague", "name": "😷 Plague", "desc": "Food production -50% for 6 hours!"},
        {"type": "festival", "name": "🎉 Mahotsav", "desc": "Training speed 2x for 12 hours!"},
        {"type": "invasion", "name": "🐉 Dragon Invasion", "desc": "Survival event active!"},
    ]
    
    event_data = random.choice(events)
    
    with get_db() as db:
        event = WorldEvent(
            event_type=event_data["type"],
            name=event_data["name"],
            description=event_data["desc"],
            ends_at=datetime.utcnow() + timedelta(hours=6),
        )
        db.add(event)
        db.commit()
    
    # Broadcast to all
    if event_data["type"] == "treasure":
        from bot.models import Kingdom
        with get_db() as db:
            kingdoms = db.query(Kingdom).all()
            for k in kingdoms:
                k.gold += 500
            db.commit()
    
    from bot.models import User
    with get_db() as db:
        users = db.query(User).filter(User.is_banned == False).all()
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"🌍 **WORLD EVENT!**\n\n{event_data['name']}\n{event_data['desc']}"
                )
            except Exception:
                pass
    
    print(f"[TASK] World event: {event_data['name']}")


async def npc_attack_task(context: ContextTypes.DEFAULT_TYPE):
    """NPC attacks on vulnerable players"""
    from bot.models import get_db, Kingdom, Army, Battle
    from bot.services.combat_engine import CombatEngine
    import json
    
    with get_db() as db:
        # Find low-level, inactive kingdoms
        vulnerable = db.query(Kingdom).filter(
            Kingdom.level <= 5,
            Kingdom.has_shield == False,
        ).all()
        
        if not vulnerable:
            return
        
        target = random.choice(vulnerable)
        
        # Create NPC attacker
        npc_level = max(1, target.level - 1)
        npc_army_size = int((target.army.total if target.army else 0) * 0.7)
        npc_army_size = max(5, npc_army_size)
        
        # Run quick battle
        npc = Kingdom(
            user_id=-1,
            name=random.choice(["Shadow King", "Dark Emperor", "Crimson Lord", "Ice Queen", "Fire Tyrant"]),
            flag="👹",
            level=npc_level,
            gold=0,
            food=0,
            energy=0,
            map_x=target.map_x,
            map_y=target.map_y,
            shield_expires=datetime.utcnow(),
        )
        db.add(npc)
        db.commit()
        db.refresh(npc)
        
        npc_army = Army(kingdom_id=-1, infantry=npc_army_size)
        db.add(npc_army)
        db.commit()
        
        # Load target army
        target.army = db.query(Army).filter(Army.kingdom_id == target.user_id).first()
        npc.army = npc_army
        
        engine = CombatEngine(npc, target)
        result = engine.simulate_battle()
        
        # Apply minimal losses (NPC attacks are weak)
        if target.army:
            target.army.infantry = max(0, target.army.infantry - result["defender_losses"]["infantry"])
            target.army.archers = max(0, target.army.archers - result["defender_losses"]["archers"])
            target.army.cavalry = max(0, target.army.cavalry - result["defender_losses"]["cavalry"])
        
        # Save battle
        battle = Battle(
            attacker_id=-1,
            defender_id=target.user_id,
            winner_id=target.user_id,
            battle_log=json.dumps(result["rounds"]),
            gold_looted=0,
            xp_gained=10,
        )
        db.add(battle)
        
        # Clean up NPC
        db.query(Army).filter(Army.kingdom_id == -1).delete()
        db.query(Kingdom).filter(Kingdom.user_id == -1).delete()
        
        db.commit()
        
        # Notify
        try:
            await context.bot.send_message(
                chat_id=target.user_id,
                text=f"🤖 **NPC ATTACK!**\n\n"
                     f"{npc.name} ne attack kiya!\n"
                     f"Aapne defend kar liya!\n"
                     f"💀 Losses: 🗡-{result['defender_losses']['infantry']}"
            )
        except Exception:
            pass
    
    print(f"[TASK] NPC attack on {target.name}")


async def leaderboard_snapshot_task(context: ContextTypes.DEFAULT_TYPE):
    """Take daily leaderboard snapshot"""
    from bot.models import get_db, Kingdom, LeaderboardEntry
    from bot.services.economy import EconomyService
    from datetime import datetime
    
    with get_db() as db:
        kingdoms = db.query(Kingdom).all()
        
        for i, k in enumerate(sorted(kingdoms, key=lambda x: EconomyService.calculate_kingdom_power(x), reverse=True)):
            power = EconomyService.calculate_kingdom_power(k)
            entry = LeaderboardEntry(
                kingdom_id=k.user_id,
                rank=i + 1,
                power=power,
                battles_won=k.battles_won,
                total_gold=k.total_gold_earned,
            )
            db.add(entry)
        
        db.commit()
    
    print("[TASK] Leaderboard snapshot taken")


async def black_market_refresh_task(context: ContextTypes.DEFAULT_TYPE):
    """Refresh black market inventories"""
    # Markets are generated on-demand, so this is a no-op
    # But we can notify users
    print("[TASK] Black market refreshed")


async def inactive_cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    """Mark inactive players"""
    from bot.models import get_db, Kingdom, User
    from datetime import datetime, timedelta
    
    with get_db() as db:
        inactive_kingdoms = db.query(Kingdom).filter(
            Kingdom.last_active < datetime.utcnow() - timedelta(days=7)
        ).all()
        
        for k in inactive_kingdoms:
            # Send shield to protect inactive players
            k.shield_expires = datetime.utcnow() + timedelta(hours=48)
        
        db.commit()
    
    print(f"[TASK] Inactive cleanup: {len(inactive_kingdoms)} kingdoms shielded")


async def decision_event_task(context: ContextTypes.DEFAULT_TYPE):
    """Trigger random decision events for active players"""
    from bot.models import get_db, Kingdom
    from bot.utils.constants import DECISION_EVENTS
    from bot.utils.keyboards import decision_keyboard
    import random
    
    # 10% chance to trigger
    if random.random() > 0.10:
        return
    
    with get_db() as db:
        active_kingdoms = db.query(Kingdom).filter(
            Kingdom.last_active > datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        for k in active_kingdoms:
            if random.random() > 0.05:  # Only 5% of active players
                continue
            
            event = random.choice(DECISION_EVENTS)
            
            try:
                await context.bot.send_message(
                    chat_id=k.user_id,
                    text=f"🎲 **RANDOM EVENT!**\n\n{event['message']}",
                    reply_markup=decision_keyboard(event["id"])
                )
            except Exception:
                pass
    
    print("[TASK] Decision events sent")


# datetime import needed for some tasks
from datetime import datetime
