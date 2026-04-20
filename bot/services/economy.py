"""
Economy Service - Resource Production, Costs & Calculations
Fixed version with corrected property references and enhanced safety.
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from bot.utils.constants import (
    GOLD_MINE_BASE_RATE, FARM_BASE_RATE, BARRACKS_TRAIN_RATE,
    BASE_UPGRADE_COST_GOLD, UPGRADE_COST_MULTIPLIER,
    BASE_UPGRADE_TIME_MINUTES, UPGRADE_TIME_MULTIPLIER,
    BUILDING_CONFIG, KINGDOM_TRAITS
)

logger = logging.getLogger(__name__)


class EconomyService:
    """Resource production, upgrade costs, and collection calculations"""
    
    @staticmethod
    def calculate_upgrade_cost(building_type: str, current_level: int) -> Dict[str, int]:
        """Exponential cost scaling for building upgrades"""
        base = BASE_UPGRADE_COST_GOLD
        multiplier = UPGRADE_COST_MULTIPLIER ** current_level
        config = BUILDING_CONFIG.get(building_type, {})
        
        gold_cost = int(base * multiplier * config.get("cost_gold_mult", 1.0))
        food_cost = int(base * multiplier * config.get("cost_food_mult", 0))
        
        time_minutes = int(config.get("time_mult", 5) * (UPGRADE_TIME_MULTIPLIER ** current_level))
        
        return {
            "gold": max(0, gold_cost),
            "food": max(0, food_cost),
            "time_minutes": max(1, time_minutes),
        }
    
    @staticmethod
    def calculate_production_rate(building_type: str, level: int, kingdom_trait: str = "balanced") -> int:
        """Linear + exponential hybrid production scaling"""
        bases = {
            "gold_mine": GOLD_MINE_BASE_RATE,
            "farm": FARM_BASE_RATE,
            "barracks": BARRACKS_TRAIN_RATE,
        }
        base_rate = bases.get(building_type, 0)
        if base_rate == 0 or level <= 0:
            return 0
        
        rate = int(base_rate * (level ** 1.2))
        
        # Apply trait bonuses
        trait = KINGDOM_TRAITS.get(kingdom_trait, {})
        if building_type == "gold_mine":
            rate = int(rate * (1 + trait.get("gold_bonus", 0)))
        elif building_type == "farm":
            rate = int(rate * (1 + trait.get("food_bonus", 0)))
        
        return max(0, rate)
    
    @staticmethod
    def calculate_collected_resources(building, kingdom_trait: str = "balanced") -> int:
        """Calculate resources produced since last collection"""
        now = datetime.utcnow()
        last_collected = getattr(building, 'last_collected', None)
        
        if not last_collected:
            return 0
        
        elapsed_hours = (now - last_collected).total_seconds() / 3600
        
        if elapsed_hours <= 0:
            return 0
        
        rate = EconomyService.calculate_production_rate(
            building.building_type, building.level, kingdom_trait
        )
        max_storage = rate * 24  # 24 hours max storage
        
        produced = min(rate * elapsed_hours, max_storage)
        return max(0, int(produced))
    
    @staticmethod
    def calculate_food_consumption(army) -> int:
        """Calculate food consumption per hour"""
        if not army:
            return 0
        
        # Use getattr to safely access attributes
        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)
        
        return max(0, (infantry * 2) + (archers * 3) + (cavalry * 5))
    
    @staticmethod
    def calculate_xp_needed(level: int) -> int:
        """Calculate XP needed for next level"""
        if level <= 0:
            level = 1
        return int(100 * (1.5 ** (level - 1)))
    
    @staticmethod
    def calculate_kingdom_power(kingdom) -> int:
        """Calculate total kingdom power - FIXED: uses proper attribute access"""
        power = 0
        
        # Army power - FIXED: use total_army property or calculate manually
        army = getattr(kingdom, 'army', None)
        if army:
            # Try total_army property first, then calculate manually
            total = getattr(army, 'total_army', None)
            if total is None:
                total = (getattr(army, 'infantry', 0) + 
                        getattr(army, 'archers', 0) + 
                        getattr(army, 'cavalry', 0))
            power += total * 10
        
        # Building power
        buildings = getattr(kingdom, 'buildings', [])
        for b in buildings:
            power += getattr(b, 'level', 1) * 100
        
        # Level power
        power += getattr(kingdom, 'level', 1) * 500
        
        # Hero power
        heroes = getattr(kingdom, 'heroes', [])
        for h in heroes:
            if getattr(h, 'unlocked', False):
                power += getattr(h, 'level', 0) * 200
        
        # Battle experience
        power += getattr(kingdom, 'battles_won', 0) * 50
        
        return max(0, power)
    
    @staticmethod
    def calculate_defense_rating(kingdom) -> int:
        """Calculate defense rating value"""
        wall_level = getattr(kingdom, 'wall_level', 1)
        base = wall_level * 10
        
        army = getattr(kingdom, 'army', None)
        if army:
            infantry = getattr(army, 'infantry', 0)
            archers = getattr(army, 'archers', 0)
            cavalry = getattr(army, 'cavalry', 0)
            
            army_defense = (infantry * 1 + archers * 1.5 + cavalry * 2)
        else:
            army_defense = 0
        
        hero_bonus = 0.0
        heroes = getattr(kingdom, 'heroes', [])
        for h in heroes:
            if getattr(h, 'unlocked', False):
                hero_bonus += 0.05 * getattr(h, 'level', 0)
        
        total = (base + army_defense) * (1 + hero_bonus)
        
        # Trait bonus
        trait = KINGDOM_TRAITS.get(getattr(kingdom, 'trait', 'balanced'), {})
        total *= (1 + trait.get("defense_bonus", 0))
        total *= (1 + trait.get("wall_bonus", 0))
        
        return max(0, int(total))
    
    @staticmethod
    def process_food_consumption(db, kingdom, hours: int = 1) -> tuple:
        """Process food consumption, handle starvation - FIXED with proper attribute access"""
        army = getattr(kingdom, 'army', None)
        
        if not army:
            return 0, False
        
        # Calculate total army safely
        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)
        total_army = infantry + archers + cavalry
        
        if total_army == 0:
            return 0, False
        
        consumption = EconomyService.calculate_food_consumption(army) * hours
        food = getattr(kingdom, 'food', 0)
        
        if food >= consumption:
            kingdom.food = food - consumption
            return consumption, False
        else:
            # Starvation
            desertion_rate = 0.10 * hours
            
            army.infantry = max(0, int(infantry * (1 - desertion_rate)))
            army.archers = max(0, int(archers * (1 - desertion_rate)))
            army.cavalry = max(0, int(cavalry * (1 - desertion_rate)))
            kingdom.food = 0
            
            return consumption, True
    
    @staticmethod
    def calculate_training_cost(unit_type: str, amount: int = 5) -> Dict[str, int]:
        """Calculate training cost for units"""
        base_costs = {
            "infantry": {"gold": 50, "food": 20},
            "archers": {"gold": 80, "food": 30},
            "cavalry": {"gold": 150, "food": 50},
        }
        
        cost = base_costs.get(unit_type, {"gold": 50, "food": 20})
        return {
            "gold": cost["gold"] * amount // 5,
            "food": cost["food"] * amount // 5,
        }
    
    @staticmethod
    def calculate_attack_power(army, hero_bonus: float = 0.0, trait_bonus: float = 0.0) -> int:
        """Calculate attack power of an army"""
        if not army:
            return 0
        
        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)
        
        infantry_power = infantry * 10
        archer_power = archers * 12 * 1.1  # Range bonus
        cavalry_power = cavalry * 18 * 1.2  # Charge bonus
        
        base_power = infantry_power + archer_power + cavalry_power
        
        # Apply bonuses
        base_power *= (1 + hero_bonus)
        base_power *= (1 + trait_bonus)
        
        return max(0, int(base_power))
    
    @staticmethod
    def calculate_net_worth(kingdom) -> int:
        """Calculate total net worth of a kingdom"""
        gold = getattr(kingdom, 'gold', 0)
        gems = getattr(kingdom, 'gems', 0)
        food = getattr(kingdom, 'food', 0)
        
        # Gem value = 1000 gold each, food value = 1 gold each
        return gold + (gems * 1000) + food
