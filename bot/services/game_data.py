"""
King-Maker Bot — Elite Edition
Game Data Service
Safe database queries with eager loading — no DetachedInstanceError.
"""

import random
from sqlalchemy.orm import selectinload

from bot.models import get_db, Kingdom, User, Alliance
from bot.services.economy import EconomyService


class GameData:
    """Provides safe, efficient game data queries with eager relationship loading."""

    @staticmethod
    def get_or_create_user(telegram_id: int, username: str, first_name: str):
        """Get or create a user record."""
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            return user

    @staticmethod
    def get_user(user_id: int):
        """Get user with eagerly loaded kingdom and army."""
        with get_db() as db:
            user = db.query(User).options(
                selectinload(User.kingdom).selectinload(Kingdom.army)
            ).filter(User.telegram_id == user_id).first()
            # Return a detached copy with data already loaded
            if user and user.kingdom and user.kingdom.army:
                _ = user.kingdom.army.total  # Ensure relationship is loaded
            return user

    @staticmethod
    def find_opponents(kingdom, db=None):
        """Find suitable attack opponents — FIXED: Proper eager loading.

        Args:
            kingdom: The attacking kingdom
            db: Optional existing DB session (pass None to create new)

        Returns:
            List of Kingdom objects with loaded army data
        """
        should_close = False
        if db is None:
            db = next(get_db())
            should_close = True

        try:
            my_power = EconomyService.calculate_kingdom_power(kingdom) if kingdom.army else 0

            # Fetch candidates with eagerly loaded army
            candidates = db.query(Kingdom).options(
                selectinload(Kingdom.army)
            ).filter(
                Kingdom.user_id != kingdom.user_id,
                Kingdom.level.between(max(1, kingdom.level - 3), kingdom.level + 3),
            ).all()

            # Python-side filtering for shield and power
            filtered = []
            for c in candidates:
                # Ensure army is loaded before power calculation
                _ = c.army.total if c.army else 0
                if c.has_shield:
                    continue
                c_power = EconomyService.calculate_kingdom_power(c) if c.army else 0
                power_ratio = c_power / max(my_power, 1)
                if 0.3 <= power_ratio <= 3.0:
                    filtered.append(c)

            random.shuffle(filtered)
            return filtered[:10]

        finally:
            if should_close:
                db.close()

    @staticmethod
    def get_leaderboard(limit: int = 10):
        """Get top kingdoms with eagerly loaded data."""
        with get_db() as db:
            kingdoms = db.query(Kingdom).options(
                selectinload(Kingdom.army)
            ).all()

            sorted_kingdoms = sorted(
                kingdoms,
                key=lambda k: EconomyService.calculate_kingdom_power(k),
                reverse=True,
            )

            # Pre-load all relationship data before returning
            for k in sorted_kingdoms[:limit]:
                if k.army:
                    _ = k.army.total

            return sorted_kingdoms[:limit]

    @staticmethod
    def get_alliance_rankings(limit: int = 10):
        """Get alliance rankings with member counts."""
        with get_db() as db:
            alliances = db.query(Alliance).all()
            ranked = []
            for a in alliances:
                members = db.query(Kingdom).filter(Kingdom.alliance_id == a.id).all()
                total_power = sum(
                    EconomyService.calculate_kingdom_power(m) if m.army else 0
                    for m in members
                )
                ranked.append({
                    "alliance": a,
                    "members": len(members),
                    "total_power": total_power,
                })
            ranked.sort(key=lambda x: x["total_power"], reverse=True)
            return ranked[:limit]

    @staticmethod
    def get_recent_battles(user_id: int, limit: int = 5):
        """Get recent battles for a user."""
        with get_db() as db:
            from bot.models import Battle
            battles = db.query(Battle).filter(
                (Battle.attacker_id == user_id) | (Battle.defender_id == user_id)
            ).order_by(Battle.timestamp.desc()).limit(limit).all()
            return battles

    @staticmethod
    def get_kingdom_stats(user_id: int):
        """Get comprehensive kingdom stats with all data loaded."""
        with get_db() as db:
            kingdom = db.query(Kingdom).options(
                selectinload(Kingdom.army)
            ).filter(Kingdom.user_id == user_id).first()

            if not kingdom:
                return None

            # Pre-load all data
            power = EconomyService.calculate_kingdom_power(kingdom) if kingdom.army else 0
            gold_prod = EconomyService.calculate_gold_production(kingdom)
            food_prod = EconomyService.calculate_food_production(kingdom)
            army_total = kingdom.army.total if kingdom.army else 0

            return {
                "kingdom": kingdom,
                "power": power,
                "gold_production": gold_prod,
                "food_production": food_prod,
                "army_total": army_total,
                "has_shield": kingdom.has_shield,
            }
