"""
Game Data Service - Database operations with lazy loading
Fixed version with all missing methods implemented.
"""

import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

from bot.models import get_db, User, Kingdom, Army, Building, Cooldown, Quest, UserQuest, Hero, NotificationPref

logger = logging.getLogger(__name__)


class GameData:
    """Central game data service with proper lazy loading"""

    # ─── User Management ───

    @staticmethod
    def get_or_create_user(telegram_id: int, **kwargs) -> User:
        """Get existing user or create new one"""
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                # Update last active
                user.last_active = datetime.utcnow()
                db.commit()
                return user

            user = User(telegram_id=telegram_id, **kwargs)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    @staticmethod
    def get_user(telegram_id: int) -> User:
        """Get user by telegram ID"""
        with get_db() as db:
            return db.query(User).filter(User.telegram_id == telegram_id).first()

    @staticmethod
    def get_all_users():
        """Get all users"""
        with get_db() as db:
            return db.query(User).all()

    # ─── Kingdom Management ───

    @staticmethod
    def get_kingdom(user_id: int) -> Kingdom:
        """Get kingdom by user ID (basic, no relations)"""
        with get_db() as db:
            return db.query(Kingdom).filter(Kingdom.user_id == user_id).first()

    @staticmethod
    def get_kingdom_with_relations(user_id: int) -> Kingdom:
        """Get kingdom with all relationships eagerly loaded"""
        with get_db() as db:
            kingdom = db.query(Kingdom).options(
                joinedload(Kingdom.army),
                joinedload(Kingdom.buildings),
                joinedload(Kingdom.alliance_member),
                joinedload(Kingdom.heroes),
                joinedload(Kingdom.user_quests),
            ).filter(Kingdom.user_id == user_id).first()

            # Attach db session for lazy loading
            if kingdom:
                kingdom._db = db

            return kingdom

    @staticmethod
    def get_all_kingdoms():
        """Get all kingdoms with army loaded"""
        with get_db() as db:
            return db.query(Kingdom).options(
                joinedload(Kingdom.army)
            ).all()

    @staticmethod
    def create_kingdom(user_id: int, name: str, flag: str, trait: str) -> Kingdom:
        """Create a new kingdom with starter setup"""
        with get_db() as db:
            # Random map position (1-10)
            map_x = random.randint(1, 10)
            map_y = random.randint(1, 10)

            # Create kingdom
            kingdom = Kingdom(
                user_id=user_id,
                name=name,
                flag=flag,
                level=1,
                gold=500,
                food=300,
                gems=0,
                energy=10,
                max_energy=10,
                map_x=map_x,
                map_y=map_y,
                shield_expires=datetime.utcnow() + timedelta(hours=24),
                trait=trait,
                xp=0,
                battles_won=0,
                battles_lost=0,
                total_gold_earned=0,
                total_gold_looted=0,
                soldiers_trained=0,
                buildings_upgraded=0,
                spy_missions=0,
                successful_spies=0,
                wall_level=1,
            )
            db.add(kingdom)
            db.commit()
            db.refresh(kingdom)

            # Create starter army (50 infantry)
            army = Army(
                kingdom_id=user_id,
                infantry=50,
                archers=0,
                cavalry=0,
            )
            db.add(army)

            # Create default buildings
            default_buildings = [
                Building(kingdom_id=user_id, building_type="town_hall", level=1, emoji="🏰", display_name="Town Hall"),
                Building(kingdom_id=user_id, building_type="gold_mine", level=1, emoji="⛏", display_name="Gold Mine"),
                Building(kingdom_id=user_id, building_type="farm", level=1, emoji="🌾", display_name="Farm"),
                Building(kingdom_id=user_id, building_type="barracks", level=1, emoji="🏹", display_name="Barracks"),
                Building(kingdom_id=user_id, building_type="wall", level=1, emoji="🛡", display_name="Wall"),
            ]
            for b in default_buildings:
                db.add(b)

            # Create default heroes
            from bot.utils.constants import HERO_CONFIG
            for hero_type, config in HERO_CONFIG.items():
                hero = Hero(
                    kingdom_id=user_id,
                    hero_type=hero_type,
                    level=0,
                    unlocked=False,
                    unlock_cost=config.get("unlock_cost", 1000),
                )
                db.add(hero)

            # Create quests
            GameData._initialize_quests(db, user_id)

            # Create notification preferences
            GameData._initialize_notification_prefs(db, user_id)

            db.commit()
            logger.info(f"Kingdom created: {name} (user_id: {user_id})")
            return kingdom

    @staticmethod
    def _initialize_quests(db, user_id: int):
        """Initialize default quests for a user"""
        existing_quests = db.query(Quest).all()
        if not existing_quests:
            # Create default quests
            default_quests = [
                Quest(name="Daily Attacker", quest_key="daily_attacks", quest_type="daily",
                      requirement_value=3, reward_gold=500, reward_xp=100),
                Quest(name="Resource Collector", quest_key="daily_collects", quest_type="daily",
                      requirement_value=5, reward_gold=300, reward_xp=50),
                Quest(name="Daily Upgrader", quest_key="daily_upgrades", quest_type="daily",
                      requirement_value=2, reward_gold=400, reward_xp=75),
                Quest(name="First Victory", quest_key="first_win", quest_type="milestone",
                      requirement_value=1, reward_gold=1000, reward_xp=200, reward_title="Conqueror"),
                Quest(name="Seasoned Warrior", quest_key="wins_10", quest_type="milestone",
                      requirement_value=10, reward_gold=5000, reward_xp=500, reward_title="Veteran"),
                Quest(name="Wealthy King", quest_key="gold_100k", quest_type="milestone",
                      requirement_value=100000, reward_gold=0, reward_xp=300, reward_title="Wealthy"),
            ]
            for q in default_quests:
                db.add(q)
            db.commit()
            existing_quests = default_quests

        # Create user quest entries
        for quest in existing_quests:
            uq = db.query(UserQuest).filter(
                UserQuest.kingdom_id == user_id,
                UserQuest.quest_id == quest.id
            ).first()
            if not uq:
                uq = UserQuest(kingdom_id=user_id, quest_id=quest.id, progress=0, completed=False, claimed=False)
                db.add(uq)

    @staticmethod
    def _initialize_notification_prefs(db, user_id: int):
        """Initialize notification preferences"""
        existing = db.query(NotificationPref).filter(NotificationPref.user_id == user_id).first()
        if not existing:
            prefs = NotificationPref(user_id=user_id)
            db.add(prefs)

    # ─── Building Management ───

    @staticmethod
    def get_buildings(user_id: int):
        """Get all buildings for a user"""
        with get_db() as db:
            return db.query(Building).filter(Building.kingdom_id == user_id).all()

    @staticmethod
    def get_building(user_id: int, building_type: str) -> Building:
        """Get specific building for a user"""
        with get_db() as db:
            return db.query(Building).filter(
                Building.kingdom_id == user_id,
                Building.building_type == building_type
            ).first()

    # ─── Hero Management ───

    @staticmethod
    def get_heroes(user_id: int):
        """Get all heroes for a user"""
        with get_db() as db:
            return db.query(Hero).filter(Hero.kingdom_id == user_id).all()

    @staticmethod
    def get_hero(user_id: int, hero_type: str) -> Hero:
        """Get specific hero for a user"""
        with get_db() as db:
            return db.query(Hero).filter(
                Hero.kingdom_id == user_id,
                Hero.hero_type == hero_type
            ).first()

    # ─── Quest Management ───

    @staticmethod
    def get_user_quests(user_id: int):
        """Get all user quests with quest data"""
        with get_db() as db:
            return db.query(UserQuest).options(
                joinedload(UserQuest.quest)
            ).filter(UserQuest.kingdom_id == user_id).all()

    # ─── Cooldown Management ───

    @staticmethod
    def get_cooldown(user_id: int, cooldown_type: str):
        """Get cooldown expiry for a user"""
        with get_db() as db:
            cd = db.query(Cooldown).filter(
                Cooldown.user_id == user_id,
                Cooldown.cooldown_type == cooldown_type
            ).first()
            return cd.expires_at if cd else None

    @staticmethod
    def set_cooldown(user_id: int, cooldown_type: str, minutes: int):
        """Set cooldown for a user"""
        with get_db() as db:
            cd = db.query(Cooldown).filter(
                Cooldown.user_id == user_id,
                Cooldown.cooldown_type == cooldown_type
            ).first()

            expires = datetime.utcnow() + timedelta(minutes=minutes)

            if cd:
                cd.expires_at = expires
            else:
                cd = Cooldown(user_id=user_id, cooldown_type=cooldown_type, expires_at=expires)
                db.add(cd)

            db.commit()

    # ─── Opponent Finding ───

    @staticmethod
    def find_opponents(user_id: int, limit: int = 5):
        """Find suitable opponents for a user"""
        with get_db() as db:
            viewer = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if not viewer:
                return []

            # Get kingdoms excluding user and with shields expired
            from sqlalchemy import or_
            candidates = db.query(Kingdom).options(
                joinedload(Kingdom.army)
            ).filter(
                Kingdom.user_id != user_id,
                or_(
                    Kingdom.shield_expires.is_(None),
                    Kingdom.shield_expires <= datetime.utcnow()
                )
            ).all()

            # Calculate power and distance for each
            from bot.services.economy import EconomyService
            results = []
            for k in candidates:
                if k.user_id == user_id:
                    continue
                power = EconomyService.calculate_kingdom_power(k)
                distance = abs(viewer.map_x - k.map_x) + abs(viewer.map_y - k.map_y)
                results.append((k, power, distance))

            # Sort by power similarity (closest to viewer's power first)
            viewer_power = EconomyService.calculate_kingdom_power(viewer)
            results.sort(key=lambda x: abs(x[1] - viewer_power))

            return results[:limit]

    # ─── Leaderboard ───

    @staticmethod
    def get_leaderboard(limit: int = 50):
        """Get kingdoms sorted by power"""
        with get_db() as db:
            kingdoms = db.query(Kingdom).options(
                joinedload(Kingdom.army)
            ).all()

            from bot.services.economy import EconomyService
            results = []
            for k in kingdoms:
                power = EconomyService.calculate_kingdom_power(k)
                results.append((k, power))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    # ─── Notification Preferences ───

    @staticmethod
    def get_notification_prefs(user_id: int) -> NotificationPref:
        """Get notification preferences for a user"""
        with get_db() as db:
            prefs = db.query(NotificationPref).filter(
                NotificationPref.user_id == user_id
            ).first()

            if not prefs:
                prefs = NotificationPref(user_id=user_id)
                db.add(prefs)
                db.commit()
                db.refresh(prefs)

            return prefs

    # ─── World Events ───

    @staticmethod
    def get_active_world_events():
        """Get all active world events"""
        with get_db() as db:
            from bot.models import WorldEvent
            return db.query(WorldEvent).filter(
                WorldEvent.ends_at > datetime.utcnow()
            ).all()

    # ─── Kingdom Existence Check ───

    @staticmethod
    def kingdom_exists(user_id: int) -> bool:
        """Check if a kingdom exists for user"""
        with get_db() as db:
            return db.query(Kingdom).filter(Kingdom.user_id == user_id).first() is not None
