"""
Economy Service - Resource management and calculations
Fixed version with proper formulas and balanced economy.
"""

import logging
from datetime import datetime

from bot.utils.constants import BUILDING_CONFIG, KINGDOM_TRAITS

logger = logging.getLogger(__name__)


class EconomyService:
    """
    Realistic economy system with:
    - Production rates based on building level
    - Trait multipliers
    - Food consumption based on army size
    - Defense rating calculation
    - Kingdom power calculation
    """

    # ─── Production Rates ───

    @staticmethod
    def calculate_production_rate(building_type: str, level: int, trait: str = "balanced") -> int:
        """Calculate hourly production rate for a building"""
        base_rates = {
            "gold_mine": 50,
            "farm": 40,
            "barracks": 5,
        }

        base = base_rates.get(building_type, 0)
        if base == 0:
            return 0

        # Exponential scaling: base * (level ^ 1.5)
        import math
        rate = int(base * math.pow(level, 1.5))

        # Trait bonuses
        trait_data = KINGDOM_TRAITS.get(trait, KINGDOM_TRAITS["balanced"])
        trait_bonus = trait_data.get("economy_multiplier", 1.0)

        if building_type == "gold_mine" and trait == "rich":
            trait_bonus = 1.5  # 50% bonus for rich trait

        rate = int(rate * trait_bonus)

        return max(1, rate)

    @staticmethod
    def calculate_upgrade_cost(building_type: str, current_level: int) -> dict:
        """Calculate upgrade cost for a building"""
        import math

        # Exponential cost scaling
        level_factor = math.pow(current_level, 2.2)

        costs = {
            "town_hall": {"gold": int(500 * level_factor), "food": int(200 * level_factor), "time_minutes": int(30 * current_level)},
            "gold_mine": {"gold": int(200 * level_factor), "food": int(50 * level_factor), "time_minutes": int(15 * current_level)},
            "farm": {"gold": int(150 * level_factor), "food": int(100 * level_factor), "time_minutes": int(12 * current_level)},
            "barracks": {"gold": int(300 * level_factor), "food": int(150 * level_factor), "time_minutes": int(20 * current_level)},
            "wall": {"gold": int(250 * level_factor), "food": int(80 * level_factor), "time_minutes": int(18 * current_level)},
        }

        return costs.get(building_type, {"gold": 100, "food": 50, "time_minutes": 10})

    @staticmethod
    def calculate_collected_resources(building, trait: str = "balanced") -> int:
        """Calculate resources produced since last collection"""
        last_collected = getattr(building, 'last_collected', None)
        level = getattr(building, 'level', 1)
        building_type = getattr(building, 'building_type', '')

        if not last_collected:
            # First collection - give base amount
            return EconomyService.calculate_production_rate(building_type, level, trait)

        # Calculate time elapsed
        elapsed = datetime.utcnow() - last_collected
        hours = elapsed.total_seconds() / 3600

        # Cap at 24 hours (no infinite accumulation)
        hours = min(hours, 24)

        if hours < 0.1:  # Minimum 6 minutes
            return 0

        hourly_rate = EconomyService.calculate_production_rate(building_type, level, trait)
        produced = int(hourly_rate * hours)

        return max(1, produced)

    # ─── Army Management ───

    @staticmethod
    def calculate_food_consumption(army) -> int:
        """Calculate hourly food consumption for an army"""
        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)

        # Different units consume different amounts
        consumption = (
            infantry * 1 +  # 1 food per infantry
            archers * 1 +   # 1 food per archer
            cavalry * 2     # 2 food per cavalry (horses eat more)
        )

        return consumption

    @staticmethod
    def calculate_training_cost(unit_type: str, amount: int) -> dict:
        """Calculate cost to train units"""
        costs = {
            "infantry": {"gold": 10, "food": 5, "time": 1},   # 1 min per unit
            "archers": {"gold": 20, "food": 8, "time": 2},     # 2 min per unit
            "cavalry": {"gold": 50, "food": 20, "time": 5},    # 5 min per unit
        }

        unit_cost = costs.get(unit_type, {"gold": 10, "food": 5, "time": 1})
        return {
            "gold": unit_cost["gold"] * amount,
            "food": unit_cost["food"] * amount,
            "time_minutes": unit_cost["time"] * amount,
        }

    # ─── Defense Rating ───

    @staticmethod
    def calculate_defense_rating(kingdom) -> int:
        """Calculate defense rating for a kingdom"""
        if not kingdom:
            return 0

        army = getattr(kingdom, 'army', None)
        if not army:
            return 0

        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)

        wall_level = getattr(kingdom, 'wall_level', 1)

        # Defense formula
        unit_defense = infantry * 12 + archers * 5 + cavalry * 8
        wall_bonus = int(unit_defense * (wall_level * 0.05))

        # Trait bonus
        trait = getattr(kingdom, 'trait', 'balanced')
        trait_multiplier = 1.0
        if trait == 'defensive':
            trait_multiplier = 1.25
        elif trait == 'balanced':
            trait_multiplier = 1.08

        total_defense = int((unit_defense + wall_bonus) * trait_multiplier)

        return max(1, total_defense)

    # ─── Kingdom Power ───

    @staticmethod
    def calculate_kingdom_power(kingdom) -> int:
        """Calculate total kingdom power (for leaderboard)"""
        if not kingdom:
            return 0

        army = getattr(kingdom, 'army', None)
        if not army:
            return 0

        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)

        level = getattr(kingdom, 'level', 1)
        buildings = getattr(kingdom, 'buildings', [])
        total_building_levels = sum(getattr(b, 'level', 1) for b in buildings)

        # Power formula
        army_power = infantry * 8 + archers * 15 + cavalry * 12
        level_bonus = level * 100
        building_bonus = total_building_levels * 50

        total_power = army_power + level_bonus + building_bonus

        return max(1, total_power)

    # ─── Training Center ───

    @staticmethod
    def get_max_trainable(kingdom, unit_type: str) -> int:
        """Get maximum units that can be trained with current resources"""
        if not kingdom:
            return 0

        cost = EconomyService.calculate_training_cost(unit_type, 1)

        gold_limit = getattr(kingdom, 'gold', 0) // max(cost['gold'], 1)
        food_limit = getattr(kingdom, 'food', 0) // max(cost['food'], 1)

        return min(gold_limit, food_limit, 1000)  # Max 1000 at a time

    # ─── Trade System ───

    @staticmethod
    def calculate_trade_rate(resource_from: str, resource_to: str) -> float:
        """Calculate trade conversion rate"""
        # Base rates (how much of resource_to per unit of resource_from)
        rates = {
            ("gold", "food"): 2.0,      # 1 gold = 2 food
            ("food", "gold"): 0.35,     # 1 food = 0.35 gold
            ("gems", "gold"): 500.0,    # 1 gem = 500 gold
            ("gold", "gems"): 0.0015,   # 1000 gold = 1.5 gems
        }

        return rates.get((resource_from, resource_to), 1.0)
