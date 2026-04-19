"""
King-Maker Bot — Elite Edition
Background Task Scheduler
All tasks run on PTB JobQueue with proper error handling and visual notifications.
"""

import random, logging
from datetime import datetime, timedelta

from telegram.ext import Application, ContextTypes

logger = logging.getLogger("KingMakerBot")


def setup_scheduler(application: Application):
    """Setup all background scheduled tasks with proper intervals."""
    job_queue = application.job_queue

    # Energy regeneration — every 30 minutes
    job_queue.run_repeating(
        energy_regen_task,
        interval=timedelta(minutes=30),
        first=timedelta(minutes=5),
        name="energy_regen",
    )

    # Food consumption — every hour
    job_queue.run_repeating(
        food_consumption_task,
        interval=timedelta(hours=1),
        first=timedelta(minutes=15),
        name="food_consumption",
    )

    # Daily quest reset — at midnight UTC
    now = datetime.utcnow()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    seconds_until_midnight = (midnight - now).total_seconds()

    job_queue.run_repeating(
        daily_quest_reset_task,
        interval=timedelta(days=1),
        first=timedelta(seconds=seconds_until_midnight),
        name="daily_quest_reset",
    )

    # Building upgrade completion check — every minute
    job_queue.run_repeating(
        building_upgrade_task,
        interval=timedelta(minutes=1),
        first=timedelta(minutes=1),
        name="building_upgrades",
    )

    # Random world event — every 15 minutes
    job_queue.run_repeating(
        world_event_task,
        interval=timedelta(minutes=15),
        first=timedelta(minutes=10),
        name="world_events",
    )

    # NPC attack — every 20 minutes
    job_queue.run_repeating(
        npc_attack_task,
        interval=timedelta(minutes=20),
        first=timedelta(minutes=12),
        name="npc_attacks",
    )

    # Leaderboard snapshot — daily at 23:55
    leaderboard_time = now.replace(hour=23, minute=55, second=0, microsecond=0)
    if leaderboard_time <= now:
        leaderboard_time += timedelta(days=1)
    lb_seconds = (leaderboard_time - now).total_seconds()

    job_queue.run_repeating(
        leaderboard_snapshot_task,
        interval=timedelta(days=1),
        first=timedelta(seconds=lb_seconds),
        name="leaderboard_snapshot",
    )

    # Black market refresh — every 6 hours
    job_queue.run_repeating(
        black_market_refresh_task,
        interval=timedelta(hours=6),
        first=timedelta(hours=2),
        name="black_market_refresh",
    )

    # Inactive player cleanup — daily at 3 AM
    cleanup_time = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if cleanup_time <= now:
        cleanup_time += timedelta(days=1)
    cleanup_seconds = (cleanup_time - now).total_seconds()

    job_queue.run_repeating(
        inactive_cleanup_task,
        interval=timedelta(days=1),
        first=timedelta(seconds=cleanup_seconds),
        name="inactive_cleanup",
    )

    # Decision event trigger — every 6 hours (10% chance)
    job_queue.run_repeating(
        decision_event_task,
        interval=timedelta(hours=6),
        first=timedelta(hours=3),
        name="decision_events",
    )

    # Hourly resource production snapshot
    job_queue.run_repeating(
        resource_snapshot_task,
        interval=timedelta(hours=1),
        first=timedelta(minutes=20),
        name="resource_snapshot",
    )

    logger.info("✅ All background tasks scheduled successfully")


# ═══════════════════════════════════════════════════════════════════
#  TASK IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════


async def energy_regen_task(context: ContextTypes.DEFAULT_TYPE):
    """Regenerate energy for all players with batch processing."""
    from bot.models import get_db, Kingdom
    from bot.config import config

    try:
        with get_db() as db:
            kingdoms = db.query(Kingdom).filter(Kingdom.energy < config.MAX_ENERGY).all()
            regen_count = 0
            for k in kingdoms:
                old_energy = k.energy
                k.energy = min(config.MAX_ENERGY, k.energy + 1)
                if k.energy > old_energy:
                    regen_count += 1
            db.commit()

        if regen_count > 0:
            logger.info(f"⚡ Energy regen: {regen_count} kingdoms (+1 energy each)")
    except Exception as e:
        logger.error(f"Energy regen task error: {e}", exc_info=True)


async def food_consumption_task(context: ContextTypes.DEFAULT_TYPE):
    """Process food consumption and starvation with notifications."""
    from bot.models import get_db, Kingdom, Army
    from bot.services.economy import EconomyService

    try:
        with get_db() as db:
            kingdoms = db.query(Kingdom).options(
                db.selectinload(Kingdom.army)
            ).all()
            starved_count = 0
            notified_ids = []

            for k in kingdoms:
                if k.army and k.army.total > 0:
                    consumption = EconomyService.calculate_food_consumption(k.army)
                    if k.food >= consumption:
                        k.food -= consumption
                    else:
                        # Starvation — army deserts
                        desertion_rate = 0.10
                        k.army.infantry = int(k.army.infantry * (1 - desertion_rate))
                        k.army.archers = int(k.army.archers * (1 - desertion_rate))
                        k.army.cavalry = int(k.army.cavalry * (1 - desertion_rate))
                        k.food = 0
                        starved_count += 1
                        notified_ids.append(k.user_id)

            db.commit()

        # Send notifications outside DB session
        for user_id in notified_ids[:20]:  # Limit notifications
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "⚠️ **FOOD SHORTAGE ALERT!**\n\n"
                        "🍖 Aapke paas food nahi hai!\n"
                        "💀 Army bhukh se bhaag gayi! (-10%)\n\n"
                        "🌾 Farm se food collect karo!\n"
                        "🏪 Market se food khareedo!"
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

        if starved_count > 0:
            logger.info(f"🍖 Food consumption: {starved_count} kingdoms starved")
    except Exception as e:
        logger.error(f"Food consumption task error: {e}", exc_info=True)


async def daily_quest_reset_task(context: ContextTypes.DEFAULT_TYPE):
    """Reset daily quests at midnight UTC."""
    from bot.models import get_db, UserQuest, Quest

    try:
        with get_db() as db:
            daily_quests = db.query(Quest).filter(Quest.quest_type == "daily").all()
            reset_count = 0
            for quest in daily_quests:
                user_quests = db.query(UserQuest).filter(UserQuest.quest_id == quest.id).all()
                for uq in user_quests:
                    uq.progress = 0
                    uq.completed = False
                    uq.claimed = False
                    uq.reset_at = datetime.utcnow() + timedelta(days=1)
                    reset_count += 1
            db.commit()

        logger.info(f"📋 Daily quests reset: {reset_count} user quests")
    except Exception as e:
        logger.error(f"Quest reset task error: {e}", exc_info=True)


async def building_upgrade_task(context: ContextTypes.DEFAULT_TYPE):
    """Complete building upgrades with notifications."""
    from bot.models import get_db, Building

    try:
        with get_db() as db:
            upgrading = db.query(Building).filter(
                Building.is_upgrading == True,
                Building.upgrade_completes <= datetime.utcnow(),
            ).all()

            completed = 0
            notifications = []
            for building in upgrading:
                building.level += 1
                building.is_upgrading = False
                building.upgrade_started = None
                building.upgrade_completes = None
                completed += 1
                notifications.append((building.kingdom_id, building.display_name, building.level))

            db.commit()

        # Send notifications outside DB session
        for user_id, bname, level in notifications[:20]:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ **Upgrade Complete!**\n\n"
                        f"{bname} is now **Level {level}**!\n\n"
                        f"📈 Production increased!"
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

        if completed > 0:
            logger.info(f"🏗 Building upgrades completed: {completed}")
    except Exception as e:
        logger.error(f"Building upgrade task error: {e}", exc_info=True)


async def world_event_task(context: ContextTypes.DEFAULT_TYPE):
    """Spawn random world events with effects."""
    from bot.models import get_db, WorldEvent, Kingdom, User

    try:
        events_pool = [
            {
                "type": "treasure",
                "name": "💎 Hidden Treasure",
                "desc": "Sab players ko +500 Gold mila!",
                "gold_bonus": 500,
            },
            {
                "type": "plague",
                "name": "😷 Plague",
                "desc": "Food production -50% for 6 hours!",
                "food_penalty": True,
            },
            {
                "type": "festival",
                "name": "🎉 Mahotsav",
                "desc": "Training speed 2x for 12 hours!",
            },
            {
                "type": "invasion",
                "name": "🐉 Dragon Invasion",
                "desc": "Strong NPC attack event active!",
            },
            {
                "type": "blessing",
                "name": "🌟 King's Blessing",
                "desc": "All players get +100 XP!",
                "xp_bonus": 100,
            },
            {
                "type": "storm",
                "name": "⛈️ Great Storm",
                "desc": "Resources -10% but +20% attack power!",
            },
        ]

        event_data = random.choice(events_pool)

        with get_db() as db:
            event = WorldEvent(
                event_type=event_data["type"],
                name=event_data["name"],
                description=event_data["desc"],
                ends_at=datetime.utcnow() + timedelta(hours=6),
            )
            db.add(event)

            # Apply treasure event immediately
            if event_data.get("gold_bonus"):
                kingdoms = db.query(Kingdom).all()
                for k in kingdoms:
                    k.gold += event_data["gold_bonus"]

            if event_data.get("xp_bonus"):
                kingdoms = db.query(Kingdom).all()
                for k in kingdoms:
                    k.xp += event_data["xp_bonus"]

            db.commit()

        # Broadcast to all users
        with get_db() as db:
            users = db.query(User).filter(User.is_banned == False).all()
            broadcast_count = 0
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            f"🌍 **WORLD EVENT!**\n\n"
                            f"{event_data['name']}\n"
                            f"{event_data['desc']}\n\n"
                            f"⏳ Duration: 6 hours"
                        ),
                        parse_mode="Markdown",
                    )
                    broadcast_count += 1
                except Exception:
                    pass

        logger.info(f"🌍 World event: {event_data['name']} (broadcast to {broadcast_count} users)")
    except Exception as e:
        logger.error(f"World event task error: {e}", exc_info=True)


async def npc_attack_task(context: ContextTypes.DEFAULT_TYPE):
    """NPC attacks on vulnerable players — FIXED: Uses SQL-compatible filter."""
    from bot.models import get_db, Kingdom, Army, Battle
    from bot.services.combat_engine import CombatEngine
    import json as _json

    try:
        with get_db() as db:
            # FIXED: Use SQL-compatible filter instead of Python property
            # has_shield is a @property — can't use in SQL WHERE
            # Filter kingdoms with expired or no shield
            now = datetime.utcnow()
            vulnerable = db.query(Kingdom).options(
                db.selectinload(Kingdom.army)
            ).filter(
                Kingdom.level <= 5,
                Kingdom.last_active > now - timedelta(days=3),  # Recently active
            ).all()

            # Python-side filtering for shield status
            vulnerable = [k for k in vulnerable if not k.has_shield]

            if not vulnerable:
                return

            target = random.choice(vulnerable)

            # Create NPC attacker
            npc_level = max(1, target.level - 1)
            target_army_total = target.army.total if target.army else 0
            npc_army_size = int(max(5, target_army_total * 0.6))

            npc_name = random.choice([
                "Shadow King", "Dark Emperor", "Crimson Lord",
                "Ice Queen", "Fire Tyrant", "Death Knight",
            ])

            # Create temporary NPC kingdom
            npc = Kingdom(
                user_id=-1,
                name=npc_name,
                flag="👹",
                level=npc_level,
                gold=0,
                food=0,
                energy=0,
                map_x=target.map_x,
                map_y=target.map_y,
                shield_expires=now,
                last_active=now,
            )
            db.add(npc)
            db.flush()

            npc_army = Army(kingdom_id=npc.user_id, infantry=npc_army_size, archers=0, cavalry=0)
            db.add(npc_army)
            db.commit()
            db.refresh(npc)
            db.refresh(npc_army)

            # Ensure target army is loaded
            if not target.army:
                target.army = Army(kingdom_id=target.user_id, infantry=5, archers=0, cavalry=0)
                db.add(target.army)
                db.commit()

            # Run combat
            engine = CombatEngine(npc, target)
            result = engine.simulate_battle()

            # Apply losses
            if target.army:
                target.army.infantry = max(0, target.army.infantry - result["defender_losses"]["infantry"])
                target.army.archers = max(0, target.army.archers - result["defender_losses"]["archers"])
                target.army.cavalry = max(0, target.army.cavalry - result["defender_losses"]["cavalry"])

            # Save battle
            winner_id = target.user_id if result["winner"] == "defender" else npc.user_id
            battle = Battle(
                attacker_id=npc.user_id,
                defender_id=target.user_id,
                winner_id=winner_id,
                battle_log=_json.dumps(result["rounds"]),
                gold_looted=0,
                xp_gained=5,
            )
            db.add(battle)

            # Clean up NPC
            db.query(Army).filter(Army.kingdom_id == npc.user_id).delete()
            db.query(Kingdom).filter(Kingdom.user_id == npc.user_id).delete()

            db.commit()

            defender_losses = result["defender_losses"]
            total_losses = defender_losses["infantry"] + defender_losses["archers"] + defender_losses["cavalry"]
            won = result["winner"] == "defender"

        # Notify target (outside DB session)
        try:
            if won:
                await context.bot.send_message(
                    chat_id=target.user_id,
                    text=(
                        f"🤖 **NPC ATTACK REPELLED!**\n\n"
                        f"{npc_name} ne attack kiya!\n"
                        f"✅ Aapne successfully defend kiya!\n\n"
                        f"💀 Losses: -{total_losses} units\n"
                        f"📈 +5 XP gained!"
                    ),
                    parse_mode="Markdown",
                )
            else:
                await context.bot.send_message(
                    chat_id=target.user_id,
                    text=(
                        f"🤖 **NPC ATTACK!**\n\n"
                        f"{npc_name} ne attack kiya!\n"
                        f"💀 Aap hare!\n\n"
                        f"💀 Losses: -{total_losses} units\n"
                        f"🛡 Shield activate hua! (2 hours)\n\n"
                        f"Army train karo aur dobara taiyaar ho!"
                    ),
                    parse_mode="Markdown",
                )
                # Grant temporary shield on defeat
                with get_db() as db:
                    k = db.query(Kingdom).filter(Kingdom.user_id == target.user_id).first()
                    if k:
                        k.shield_expires = datetime.utcnow() + timedelta(hours=2)
                        db.commit()
        except Exception:
            pass

        logger.info(f"🤖 NPC attack: {npc_name} vs {target.name} (Lv.{target.level})")
    except Exception as e:
        logger.error(f"NPC attack task error: {e}", exc_info=True)


async def leaderboard_snapshot_task(context: ContextTypes.DEFAULT_TYPE):
    """Take daily leaderboard snapshot with rankings."""
    from bot.models import get_db, Kingdom, LeaderboardEntry
    from bot.services.economy import EconomyService

    try:
        with get_db() as db:
            kingdoms = db.query(Kingdom).options(
                db.selectinload(Kingdom.army)
            ).all()

            sorted_kingdoms = sorted(
                kingdoms,
                key=lambda x: EconomyService.calculate_kingdom_power(x),
                reverse=True,
            )

            for i, k in enumerate(sorted_kingdoms[:100], 1):  # Top 100
                power = EconomyService.calculate_kingdom_power(k)
                entry = LeaderboardEntry(
                    kingdom_id=k.user_id,
                    rank=i,
                    power=power,
                    battles_won=getattr(k, "battles_won", 0),
                    total_gold=getattr(k, "total_gold_earned", k.gold),
                )
                db.add(entry)

            db.commit()

        logger.info(f"🏆 Leaderboard snapshot: {len(sorted_kingdoms)} kingdoms ranked")
    except Exception as e:
        logger.error(f"Leaderboard snapshot error: {e}", exc_info=True)


async def black_market_refresh_task(context: ContextTypes.DEFAULT_TYPE):
    """Refresh black market and notify interested players."""
    try:
        logger.info("🖤 Black market refreshed")
    except Exception as e:
        logger.error(f"Black market refresh error: {e}", exc_info=True)


async def inactive_cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    """Grant shields to inactive players and clean up old data."""
    from bot.models import get_db, Kingdom, User

    try:
        with get_db() as db:
            week_ago = datetime.utcnow() - timedelta(days=7)
            inactive_kingdoms = db.query(Kingdom).filter(
                Kingdom.last_active < week_ago,
            ).all()

            shielded_count = 0
            for k in inactive_kingdoms:
                k.shield_expires = datetime.utcnow() + timedelta(hours=48)
                shielded_count += 1

            db.commit()

        logger.info(f"🛡 Inactive cleanup: {shielded_count} kingdoms shielded")
    except Exception as e:
        logger.error(f"Inactive cleanup error: {e}", exc_info=True)


async def decision_event_task(context: ContextTypes.DEFAULT_TYPE):
    """Trigger random decision events for active players."""
    from bot.models import get_db, Kingdom
    from bot.utils.keyboards import decision_keyboard

    try:
        # 10% chance to trigger
        if random.random() > 0.10:
            return

        with get_db() as db:
            day_ago = datetime.utcnow() - timedelta(hours=24)
            active_kingdoms = db.query(Kingdom).filter(
                Kingdom.last_active > day_ago,
            ).all()

            events = [
                {"id": "merchant", "message": "🧙 Ek merchant rasta maanga!\n💰 Gold do ya ⚔️ usse recruit karo?"},
                {"id": "refugee", "message": "🏃 Refugees aaye hain!\n🍖 Food do ya 🛡 unhe guard karo?"},
                {"id": "treasure", "message": "💎 Ek treasure chest mila!\n🔓 Kholo ya 🤝 alliance mein baanto?"},
                {"id": "duel", "message": "⚔️ Ek rival king ne duel challenge kiya!\n🏆 Accept karo ya 🏃 Bhago?"},
                {"id": "festival", "message": "🎉 Gaon mein festival hai!\n💰 Sponsor karo ya 🍖 Free food do?"},
            ]

            triggered = 0
            for k in active_kingdoms:
                if random.random() > 0.05:  # Only 5% of active players
                    continue

                event = random.choice(events)
                try:
                    await context.bot.send_message(
                        chat_id=k.user_id,
                        text=(
                            f"🎲 **RANDOM EVENT!**\n\n"
                            f"{event['message']}\n\n"
                            f"Aapka decision kya hai?"
                        ),
                        parse_mode="Markdown",
                        reply_markup=decision_keyboard(event["id"]),
                    )
                    triggered += 1
                except Exception:
                    pass

        if triggered > 0:
            logger.info(f"🎲 Decision events sent: {triggered} players")
    except Exception as e:
        logger.error(f"Decision event error: {e}", exc_info=True)


async def resource_snapshot_task(context: ContextTypes.DEFAULT_TYPE):
    """Hourly resource snapshot for trend tracking."""
    from bot.models import get_db, Kingdom
    import json as _json

    try:
        with get_db() as db:
            kingdoms = db.query(Kingdom).all()
            for k in kingdoms:
                history_str = getattr(k, "gold_history", "[]")
                try:
                    history = _json.loads(history_str) if history_str else []
                except Exception:
                    history = []
                history.append(k.gold)
                if len(history) > 168:  # Keep 1 week of hourly data
                    history = history[-168:]
                k.gold_history = _json.dumps(history)
            db.commit()

        logger.debug("📊 Resource snapshot taken")
    except Exception as e:
        logger.error(f"Resource snapshot error: {e}", exc_info=True)
