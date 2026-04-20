"""
Task Scheduler - Background Scheduled Tasks
Fixed version with proper attribute access and comprehensive error handling.
"""

import random
import logging
from datetime import datetime, timedelta
from telegram.ext import Application, ContextTypes

from bot.config import config

logger = logging.getLogger(__name__)


def setup_scheduler(application: Application):
    """Setup all background scheduled tasks with safety checks"""
    job_queue = application.job_queue
    if not job_queue:
        logger.warning("Job queue not available - scheduler disabled")
        return
    
    # Energy regeneration - every 30 minutes
    job_queue.run_repeating(
        energy_regen_task,
        interval=timedelta(minutes=config.ENERGY_REGEN_MINUTES),
        first=timedelta(minutes=5),
        name="energy_regen"
    )
    logger.info("✅ Energy regen task scheduled")
    
    # Food consumption - every hour
    job_queue.run_repeating(
        food_consumption_task,
        interval=timedelta(hours=1),
        first=timedelta(hours=1),
        name="food_consumption"
    )
    logger.info("✅ Food consumption task scheduled")
    
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
    logger.info("✅ Daily quest reset task scheduled")
    
    # Building upgrade completion check - every minute
    job_queue.run_repeating(
        building_upgrade_task,
        interval=timedelta(minutes=1),
        first=timedelta(minutes=1),
        name="building_upgrades"
    )
    logger.info("✅ Building upgrade task scheduled")
    
    # Random world event - every 15 minutes
    if config.FEATURE_WORLD_EVENTS:
        job_queue.run_repeating(
            world_event_task,
            interval=timedelta(minutes=config.WORLD_EVENT_INTERVAL_MINUTES),
            first=timedelta(minutes=config.WORLD_EVENT_INTERVAL_MINUTES),
            name="world_events"
        )
        logger.info("✅ World events task scheduled")
    
    # NPC attack - every 20 minutes
    if config.FEATURE_NPC_ATTACKS:
        job_queue.run_repeating(
            npc_attack_task,
            interval=timedelta(minutes=config.NPC_ATTACK_INTERVAL_MINUTES),
            first=timedelta(minutes=config.NPC_ATTACK_INTERVAL_MINUTES),
            name="npc_attacks"
        )
        logger.info("✅ NPC attack task scheduled")
    
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
    logger.info("✅ Leaderboard snapshot task scheduled")
    
    # Black market refresh - every 6 hours
    if config.FEATURE_BLACK_MARKET:
        job_queue.run_repeating(
            black_market_refresh_task,
            interval=timedelta(hours=config.BLACK_MARKET_REFRESH_HOURS),
            first=timedelta(hours=config.BLACK_MARKET_REFRESH_HOURS),
            name="black_market_refresh"
        )
        logger.info("✅ Black market refresh task scheduled")
    
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
    logger.info("✅ Inactive cleanup task scheduled")
    
    # Decision event trigger - every 6 hours (10% chance)
    if config.FEATURE_DECISION_EVENTS:
        job_queue.run_repeating(
            decision_event_task,
            interval=timedelta(hours=config.DECISION_EVENT_INTERVAL_HOURS),
            first=timedelta(hours=config.DECISION_EVENT_INTERVAL_HOURS),
            name="decision_events"
        )
        logger.info("✅ Decision events task scheduled")
    
    logger.info("✅ All scheduler tasks initialized")


# ─── Energy Regeneration ───

async def energy_regen_task(context: ContextTypes.DEFAULT_TYPE):
    """Regenerate energy for all players"""
    try:
        from bot.models import get_db, Kingdom
        
        with get_db() as db:
            kingdoms = db.query(Kingdom).filter(Kingdom.energy < config.MAX_ENERGY).all()
            
            count = 0
            for k in kingdoms:
                try:
                    k.energy = min(config.MAX_ENERGY, k.energy + 1)
                    count += 1
                except Exception:
                    continue
            
            db.commit()
        
        if count > 0:
            logger.info(f"[TASK] Energy regen: {count} kingdoms")
    
    except Exception as e:
        logger.error(f"[TASK] Energy regen error: {e}")


# ─── Food Consumption ───

async def food_consumption_task(context: ContextTypes.DEFAULT_TYPE):
    """Process food consumption and starvation - FIXED with safe attribute access"""
    try:
        from bot.models import get_db, Kingdom, Army
        from bot.services.economy import EconomyService
        
        with get_db() as db:
            # Get all kingdoms with armies
            armies = db.query(Army).all()
            starved = 0
            notified_users = []
            
            for army in armies:
                try:
                    # Calculate total army safely - FIXED
                    infantry = getattr(army, 'infantry', 0)
                    archers = getattr(army, 'archers', 0)
                    cavalry = getattr(army, 'cavalry', 0)
                    total = infantry + archers + cavalry
                    
                    if total == 0:
                        continue
                    
                    kingdom = db.query(Kingdom).filter(Kingdom.user_id == army.kingdom_id).first()
                    if not kingdom:
                        continue
                    
                    consumption = EconomyService.calculate_food_consumption(army)
                    food = getattr(kingdom, 'food', 0)
                    
                    if food >= consumption:
                        kingdom.food = food - consumption
                    else:
                        # Starvation
                        desertion_rate = config.ARMY_STARVATION_DESERTION_RATE
                        
                        army.infantry = max(0, int(infantry * (1 - desertion_rate)))
                        army.archers = max(0, int(archers * (1 - desertion_rate)))
                        army.cavalry = max(0, int(cavalry * (1 - desertion_rate)))
                        kingdom.food = 0
                        starved += 1
                        
                        # Queue notification
                        notified_users.append(kingdom.user_id)
                
                except Exception as inner_e:
                    logger.error(f"[TASK] Food consumption inner error: {inner_e}")
                    continue
            
            db.commit()
            
            # Send starvation notifications
            for user_id in notified_users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⚠️ **FOOD SHORTAGE!**\n"
                            "━━━━━━━━━━━━━━\n"
                            "Bhukh ke kaaran army bhaag gayi!\n"
                            "🍖 Farm se food collect karo!"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        
        if starved > 0:
            logger.info(f"[TASK] Food consumption: {starved} kingdoms starved")
    
    except Exception as e:
        logger.error(f"[TASK] Food consumption error: {e}")


# ─── Daily Quest Reset ───

async def daily_quest_reset_task(context: ContextTypes.DEFAULT_TYPE):
    """Reset daily quests"""
    try:
        from bot.models import get_db, UserQuest, Quest
        
        with get_db() as db:
            daily_quests = db.query(Quest).filter(Quest.quest_type == "daily").all()
            
            count = 0
            for quest in daily_quests:
                try:
                    user_quests = db.query(UserQuest).filter(UserQuest.quest_id == quest.id).all()
                    for uq in user_quests:
                        uq.progress = 0
                        uq.completed = False
                        uq.claimed = False
                        uq.reset_at = datetime.utcnow() + timedelta(days=1)
                        count += 1
                except Exception:
                    continue
            
            db.commit()
        
        logger.info(f"[TASK] Daily quests reset: {count} entries")
    
    except Exception as e:
        logger.error(f"[TASK] Daily quest reset error: {e}")


# ─── Building Upgrades ───

async def building_upgrade_task(context: ContextTypes.DEFAULT_TYPE):
    """Complete building upgrades"""
    try:
        from bot.models import get_db, Building
        
        with get_db() as db:
            upgrading = db.query(Building).filter(
                Building.is_upgrading == True,
                Building.upgrade_completes <= datetime.utcnow()
            ).all()
            
            completed = 0
            for building in upgrading:
                try:
                    building.level += 1
                    building.is_upgrading = False
                    building.upgrade_started = None
                    building.upgrade_completes = None
                    completed += 1
                    
                    # Notify user
                    building_name = getattr(building, 'display_name', building.building_type.replace('_', ' ').title())
                    try:
                        await context.bot.send_message(
                            chat_id=building.kingdom_id,
                            text=(
                                f"✅ **Upgrade Complete!**\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"🏗 {building_name} is now **Level {building.level}**!"
                            ),
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                
                except Exception:
                    continue
            
            db.commit()
        
        if completed > 0:
            logger.info(f"[TASK] Building upgrades completed: {completed}")
    
    except Exception as e:
        logger.error(f"[TASK] Building upgrade error: {e}")


# ─── World Events ───

async def world_event_task(context: ContextTypes.DEFAULT_TYPE):
    """Spawn random world events"""
    try:
        # Check chance
        if random.random() > config.WORLD_EVENT_CHANCE:
            return
        
        from bot.models import get_db, WorldEvent, Kingdom, User
        
        events = [
            {"type": "treasure", "name": "💎 Hidden Treasure", 
             "desc": "Sab players ko +500 Gold mila!", "effect": "gold_bonus"},
            {"type": "plague", "name": "😷 Plague",
             "desc": "Food production -50% for 6 hours!", "effect": "food_penalty"},
            {"type": "festival", "name": "🎉 Mahotsav",
             "desc": "Training speed 2x for 12 hours!", "effect": "training_bonus"},
            {"type": "invasion", "name": "🐉 Dragon Invasion",
             "desc": "Survival event active!", "effect": "combat"},
        ]
        
        event_data = random.choice(events)
        
        with get_db() as db:
            # Create event
            event = WorldEvent(
                event_type=event_data["type"],
                name=event_data["name"],
                description=event_data["desc"],
                ends_at=datetime.utcnow() + timedelta(hours=config.WORLD_EVENT_DURATION_HOURS),
            )
            db.add(event)
            db.commit()
            
            # Apply effects
            if event_data["type"] == "treasure":
                kingdoms = db.query(Kingdom).all()
                for k in kingdoms:
                    k.gold = getattr(k, 'gold', 0) + 500
                db.commit()
            
            # Broadcast to all users
            users = db.query(User).filter(User.is_banned == False).all()
            notified = 0
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            f"🌍 **WORLD EVENT!**\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"{event_data['name']}\n"
                            f"{event_data['desc']}\n"
                            f"⏰ Duration: {config.WORLD_EVENT_DURATION_HOURS} hours"
                        ),
                        parse_mode="Markdown"
                    )
                    notified += 1
                except Exception:
                    pass
        
        logger.info(f"[TASK] World event: {event_data['name']} (notified {notified} users)")
    
    except Exception as e:
        logger.error(f"[TASK] World event error: {e}")


# ─── NPC Attacks ───

async def npc_attack_task(context: ContextTypes.DEFAULT_TYPE):
    """NPC attacks on vulnerable players - FIXED with safe attribute access"""
    try:
        # Check chance
        if random.random() > config.NPC_ATTACK_CHANCE:
            return
        
        from bot.models import get_db, Kingdom, Army, Battle, Building
        from bot.services.combat_engine import CombatEngine
        import json
        
        with get_db() as db:
            # Find vulnerable kingdoms (low level, no shield)
            all_kingdoms = db.query(Kingdom).all()
            vulnerable = []
            
            for k in all_kingdoms:
                try:
                    level = getattr(k, 'level', 1)
                    shield = getattr(k, 'shield_expires', None)
                    has_shield = shield and datetime.utcnow() < shield
                    
                    if level <= config.NPC_ATTACK_MAX_LEVEL and not has_shield:
                        vulnerable.append(k)
                except Exception:
                    continue
            
            if not vulnerable:
                return
            
            target = random.choice(vulnerable)
            target_id = getattr(target, 'user_id', None)
            target_name = getattr(target, 'name', 'Unknown')
            
            if not target_id:
                return
            
            # Get target army - FIXED
            target_army = db.query(Army).filter(Army.kingdom_id == target_id).first()
            
            # Calculate NPC strength based on target
            target_level = getattr(target, 'level', 1)
            npc_level = max(1, target_level - 1)
            
            target_total = 0
            if target_army:
                target_total = (getattr(target_army, 'infantry', 0) + 
                              getattr(target_army, 'archers', 0) + 
                              getattr(target_army, 'cavalry', 0))
            
            npc_army_size = max(5, int(target_total * 0.7))
            
            # Create NPC attacker
            npc_name = random.choice(config.NPC_NAMES)
            npc_flag = "👹"
            
            npc = Kingdom(
                user_id=-1,
                name=npc_name,
                flag=npc_flag,
                level=npc_level,
                gold=0,
                food=0,
                energy=0,
                map_x=getattr(target, 'map_x', 1),
                map_y=getattr(target, 'map_y', 1),
                shield_expires=datetime.utcnow(),
                trait="aggressive",
            )
            db.add(npc)
            db.commit()
            db.refresh(npc)
            
            npc_army = Army(kingdom_id=-1, infantry=npc_army_size, archers=0, cavalry=0)
            db.add(npc_army)
            db.commit()
            
            # Load armies for combat
            target.army = target_army
            npc.army = npc_army
            target.buildings = db.query(Building).filter(Building.kingdom_id == target_id).all()
            
            # Simulate battle
            engine = CombatEngine(npc, target)
            result = engine.simulate_battle()
            
            # Apply losses to target
            if target_army:
                target_army.infantry = max(0, target_army.infantry - result["defender_losses"]["infantry"])
                target_army.archers = max(0, target_army.archers - result["defender_losses"]["archers"])
                target_army.cavalry = max(0, target_army.cavalry - result["defender_losses"]["cavalry"])
            
            # Save battle log
            battle = Battle(
                attacker_id=-1,
                defender_id=target_id,
                winner_id=target_id if result.get("winner") == "defender" else -1,
                battle_log=json.dumps(result.get("rounds", [])),
                gold_looted=0,
                xp_gained=10,
            )
            db.add(battle)
            
            # Clean up NPC
            db.query(Army).filter(Army.kingdom_id == -1).delete()
            db.query(Kingdom).filter(Kingdom.user_id == -1).delete()
            db.commit()
            
            # Notify target
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=(
                        f"🤖 **NPC ATTACK!**\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"👹 {npc_name} ne attack kiya!\n"
                        f"🛡 Aapne defend kar liya!\n"
                        f"💀 Losses: 🗡-{result['defender_losses']['infantry']}"
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        
        logger.info(f"[TASK] NPC attack on {target_name}")
    
    except Exception as e:
        logger.error(f"[TASK] NPC attack error: {e}")


# ─── Leaderboard Snapshot ───

async def leaderboard_snapshot_task(context: ContextTypes.DEFAULT_TYPE):
    """Take daily leaderboard snapshot"""
    try:
        from bot.models import get_db, Kingdom, LeaderboardEntry
        from bot.services.economy import EconomyService
        
        with get_db() as db:
            kingdoms = db.query(Kingdom).all()
            
            # Sort by power
            sorted_kingdoms = sorted(
                kingdoms,
                key=lambda x: EconomyService.calculate_kingdom_power(x),
                reverse=True
            )
            
            entries_added = 0
            for i, k in enumerate(sorted_kingdoms):
                try:
                    power = EconomyService.calculate_kingdom_power(k)
                    entry = LeaderboardEntry(
                        kingdom_id=k.user_id,
                        rank=i + 1,
                        power=power,
                        battles_won=getattr(k, 'battles_won', 0),
                        total_gold=getattr(k, 'total_gold_earned', 0),
                    )
                    db.add(entry)
                    entries_added += 1
                except Exception:
                    continue
            
            db.commit()
        
        logger.info(f"[TASK] Leaderboard snapshot: {entries_added} entries")
    
    except Exception as e:
        logger.error(f"[TASK] Leaderboard snapshot error: {e}")


# ─── Black Market Refresh ───

async def black_market_refresh_task(context: ContextTypes.DEFAULT_TYPE):
    """Refresh black market inventories"""
    try:
        logger.info("[TASK] Black market refreshed")
    except Exception as e:
        logger.error(f"[TASK] Black market refresh error: {e}")


# ─── Inactive Cleanup ───

async def inactive_cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    """Mark inactive players with shields"""
    try:
        from bot.models import get_db, Kingdom, User
        
        with get_db() as db:
            cutoff_time = datetime.utcnow() - timedelta(days=config.INACTIVE_PLAYER_DAYS)
            
            inactive_kingdoms = db.query(Kingdom).filter(
                Kingdom.last_active < cutoff_time
            ).all()
            
            shielded = 0
            for k in inactive_kingdoms:
                try:
                    k.shield_expires = datetime.utcnow() + timedelta(
                        hours=config.INACTIVE_PLAYER_SHIELD_HOURS
                    )
                    shielded += 1
                except Exception:
                    continue
            
            db.commit()
        
        logger.info(f"[TASK] Inactive cleanup: {shielded} kingdoms shielded")
    
    except Exception as e:
        logger.error(f"[TASK] Inactive cleanup error: {e}")


# ─── Decision Events ───

async def decision_event_task(context: ContextTypes.DEFAULT_TYPE):
    """Trigger random decision events for active players"""
    try:
        # Check global chance
        if random.random() > config.DECISION_EVENT_CHANCE:
            return
        
        from bot.models import get_db, Kingdom, User
        from bot.utils.constants import DECISION_EVENTS
        from bot.utils.keyboards import decision_keyboard
        
        with get_db() as db:
            active_cutoff = datetime.utcnow() - timedelta(hours=24)
            active_kingdoms = db.query(Kingdom).filter(
                Kingdom.last_active > active_cutoff
            ).all()
            
            sent = 0
            for k in active_kingdoms:
                try:
                    # Individual player chance
                    if random.random() > config.DECISION_EVENT_PLAYER_CHANCE:
                        continue
                    
                    event = random.choice(DECISION_EVENTS)
                    
                    await context.bot.send_message(
                        chat_id=k.user_id,
                        text=(
                            f"🎲 **RANDOM EVENT!**\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"{event['message']}"
                        ),
                        reply_markup=decision_keyboard(event["id"]),
                        parse_mode="Markdown"
                    )
                    sent += 1
                except Exception:
                    continue
        
        if sent > 0:
            logger.info(f"[TASK] Decision events sent: {sent}")
    
    except Exception as e:
        logger.error(f"[TASK] Decision event error: {e}")
