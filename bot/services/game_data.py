"""
Game Data Service - Central data operations with safe attribute access.
Version: 2.0.0 - Added get_all_kingdoms().
"""

import random
import logging
from datetime import datetime

from bot.models import get_db, User, Kingdom, Army, Building, Cooldown

logger = logging.getLogger(__name__)


class GameData:
    """Centralized game data access with lazy loading and caching"""

    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None):
        """Get or create a user by Telegram ID"""
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username or str(telegram_id),
                    first_name=first_name or "Player",
                    last_active=datetime.utcnow(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                user.last_active = datetime.utcnow()
                if username and not user.username:
                    user.username = username
                if first_name and not user.first_name:
                    user.first_name = first_name
                db.commit()
            return user

    @staticmethod
    def get_kingdom(user_id: int):
        """Get a kingdom by user ID"""
        with get_db() as db:
            return db.query(Kingdom).filter(Kingdom.user_id == user_id).first()

    @staticmethod
    def get_kingdom_with_relations(user_id: int):
        """Get kingdom with all related data loaded safely"""
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if not kingdom:
                return None

            # Lazy load relationships with safe attribute access
            try:
                kingdom.army = db.query(Army).filter(Army.kingdom_id == user_id).first()
            except Exception:
                kingdom.army = None

            try:
                kingdom.buildings = db.query(Building).filter(Building.kingdom_id == user_id).all()
            except Exception:
                kingdom.buildings = []

            return kingdom

    @staticmethod
    def get_all_kingdoms():
        """Get all kingdoms with relations loaded - FIXED: now properly implemented."""
        with get_db() as db:
            kingdoms = db.query(Kingdom).all()
            for k in kingdoms:
                try:
                    k.army = db.query(Army).filter(Army.kingdom_id == k.user_id).first()
                except Exception:
                    k.army = None
            return kingdoms

    @staticmethod
    def get_random_opponent(user_id: int, exclude_recent: int = 5):
        """Get a random opponent for battle"""
        with get_db() as db:
            opponents = db.query(Kingdom).filter(Kingdom.user_id != user_id).all()
            if not opponents:
                return None
            return random.choice(opponents)

    @staticmethod
    def get_nearby_opponents(user_id: int, radius: int = 3):
        """Get opponents near the user on the map"""
        kingdom = GameData.get_kingdom(user_id)
        if not kingdom:
            return []

        x = getattr(kingdom, 'map_x', 5)
        y = getattr(kingdom, 'map_y', 5)

        with get_db() as db:
            all_kingdoms = db.query(Kingdom).filter(Kingdom.user_id != user_id).all()
            nearby = []
            for k in all_kingdoms:
                kx = getattr(k, 'map_x', 5)
                ky = getattr(k, 'map_y', 5)
                distance = abs(x - kx) + abs(y - ky)
                if distance <= radius:
                    nearby.append((k, distance))

            nearby.sort(key=lambda x: x[1])
            return nearby

    @staticmethod
    def can_attack(user_id: int) -> bool:
        """Check if user can attack (has energy)"""
        kingdom = GameData.get_kingdom(user_id)
        if not kingdom:
            return False
        return getattr(kingdom, 'energy', 0) > 0

    @staticmethod
    def is_online(kingdom) -> bool:
        """Check if a kingdom's player is online"""
        if not kingdom:
            return False
        last_active = getattr(kingdom, 'last_active', None)
        if not last_active:
            return False
        elapsed = (datetime.utcnow() - last_active).total_seconds()
        return elapsed < 300  # 5 minutes

    @staticmethod
    def get_active_world_events():
        """Get currently active world events"""
        from bot.models import WorldEvent
        with get_db() as db:
            return db.query(WorldEvent).filter(WorldEvent.ends_at > datetime.utcnow()).all()

    @staticmethod
    def get_cooldown(user_id: int, action: str):
        """Get cooldown timestamp for an action"""
        with get_db() as db:
            cd = db.query(Cooldown).filter(
                Cooldown.user_id == user_id,
                Cooldown.action == action
            ).first()
            if cd and cd.expires_at and cd.expires_at > datetime.utcnow():
                return cd.expires_at
            return None

    @staticmethod
    def set_cooldown(user_id: int, action: str, hours: int = None):
        """Set cooldown for an action"""
        from bot.config import config

        # Default cooldowns
        cooldown_map = {
            "dice": getattr(config, 'DICE_COOLDOWN_HOURS', 4),
            "spin": getattr(config, 'SPIN_COOLDOWN_HOURS', 8),
            "quiz": getattr(config, 'QUIZ_COOLDOWN_HOURS', 6),
        }

        if hours is None:
            hours = cooldown_map.get(action, 1)

        with get_db() as db:
            cd = db.query(Cooldown).filter(
                Cooldown.user_id == user_id,
                Cooldown.action == action
            ).first()

            if not cd:
                cd = Cooldown(user_id=user_id, action=action)
                db.add(cd)

            cd.expires_at = datetime.utcnow() + __import__('datetime').timedelta(hours=hours)
            db.commit()

    @staticmethod
    def clear_cooldown(user_id: int, action: str):
        """Clear a cooldown"""
        with get_db() as db:
            db.query(Cooldown).filter(
                Cooldown.user_id == user_id,
                Cooldown.action == action
            ).delete()
            db.commit()

    @staticmethod
    def has_active_shield(user_id: int) -> bool:
        """Check if user has an active shield"""
        kingdom = GameData.get_kingdom(user_id)
        if not kingdom:
            return False
        shield = getattr(kingdom, 'shield_expires', None)
        return shield is not None and shield > datetime.utcnow()

    @staticmethod
    def create_kingdom(user_id: int, name: str, flag: str, trait: str):
        """Create a new kingdom with starter resources"""
        from bot.config import config

        with get_db() as db:
            # Check if kingdom already exists
            existing = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if existing:
                return existing

            map_x = random.randint(1, getattr(config, 'MAP_SIZE', 10))
            map_y = random.randint(1, getattr(config, 'MAP_SIZE', 10))

            kingdom = Kingdom(
                user_id=user_id,
                name=name,
                flag=flag,
                trait=trait,
                level=1,
                gold=getattr(config, 'STARTER_GOLD', 1000),
                food=getattr(config, 'STARTER_FOOD', 500),
                gems=0,
                energy=getattr(config, 'STARTER_ENERGY', 10),
                map_x=map_x,
                map_y=map_y,
                shield_expires=datetime.utcnow() + __import__('datetime').timedelta(
                    hours=getattr(config, 'NEWBIE_SHIELD_HOURS', 24)
                ),
            )
            db.add(kingdom)
            db.commit()
            db.refresh(kingdom)

            # Create starter army
            army = Army(
                kingdom_id=user_id,
                infantry=getattr(config, 'STARTER_ARMY', 50),
                archers=0,
                cavalry=0,
            )
            db.add(army)

            # Create starter buildings
            building_types = ["town_hall", "gold_mine", "farm", "barracks", "wall"]
            for btype in building_types:
                building = Building(
                    kingdom_id=user_id,
                    building_type=btype,
                    level=1,
                    is_upgrading=False,
                )
                db.add(building)

            db.commit()
            return kingdom

    @staticmethod
    def delete_kingdom(user_id: int):
        """Delete a kingdom and all related data"""
        with get_db() as db:
            # Delete army
            db.query(Army).filter(Army.kingdom_id == user_id).delete()
            # Delete buildings
            db.query(Building).filter(Building.kingdom_id == user_id).delete()
            # Delete cooldowns
            db.query(Cooldown).filter(Cooldown.user_id == user_id).delete()
            # Delete kingdom
            db.query(Kingdom).filter(Kingdom.user_id == user_id).delete()
            db.commit()

    @staticmethod
    def is_on_cooldown(user_id: int, action: str) -> bool:
        """Quick check if an action is on cooldown"""
        return GameData.get_cooldown(user_id, action) is not None

    @staticmethod
    def get_online_players():
        """Get all currently online players"""
        with get_db() as db:
            cutoff = datetime.utcnow() - __import__('datetime').timedelta(minutes=5)
            return db.query(Kingdom).filter(Kingdom.last_active > cutoff).all()

    @staticmethod
    def get_kingdom_count() -> int:
        """Get total kingdom count"""
        with get_db() as db:
            return db.query(Kingdom).count()

    @staticmethod
    def get_user_count() -> int:
        """Get total user count"""
        with get_db() as db:
            return db.query(User).count()
