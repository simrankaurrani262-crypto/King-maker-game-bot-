import math
from datetime import datetime, timedelta
from bot.utils.constants import (
    GOLD_MINE_BASE_RATE, FARM_BASE_RATE, BARRACKS_TRAIN_RATE,
    BASE_UPGRADE_COST_GOLD, UPGRADE_COST_MULTIPLIER,
    BASE_UPGRADE_TIME_MINUTES, UPGRADE_TIME_MULTIPLIER,
    BUILDING_CONFIG, KINGDOM_TRAITS
)


class EconomyService:
    """Resource production, upgrade costs, and collection calculations"""
    
    @staticmethod
    def calculate_upgrade_cost(building_type, current_level):
        """Exponential cost scaling for building upgrades"""
        base = BASE_UPGRADE_COST_GOLD
        multiplier = UPGRADE_COST_MULTIPLIER ** current_level
        config = BUILDING_CONFIG.get(building_type, {})
        
        gold_cost = int(base * multiplier * config.get("cost_gold_mult", 1.0))
        food_cost = int(base * multiplier * config.get("cost_food_mult", 0))
        
        time_minutes = int(config.get("time_mult", 5) * (UPGRADE_TIME_MULTIPLIER ** current_level))
        
        return {
            "gold": gold_cost,
            "food": food_cost,
            "time_minutes": time_minutes,
        }
    
    @staticmethod
    def calculate_production_rate(building_type, level, kingdom_trait="balanced"):
        """Linear + exponential hybrid production scaling"""
        bases = {
            "gold_mine": GOLD_MINE_BASE_RATE,
            "farm": FARM_BASE_RATE,
            "barracks": BARRACKS_TRAIN_RATE,
        }
        base_rate = bases.get(building_type, 0)
        if base_rate == 0:
            return 0
        
        rate = int(base_rate * (level ** 1.2))
        
        # Apply trait bonuses
        trait = KINGDOM_TRAITS.get(kingdom_trait, {})
        if building_type == "gold_mine":
            rate = int(rate * (1 + trait.get("gold_bonus", 0)))
        
        return rate
    
    @staticmethod
    def calculate_collected_resources(building, kingdom_trait="balanced"):
        """Calculate resources produced since last collection"""
        now = datetime.utcnow()
        elapsed_hours = (now - building.last_collected).total_seconds() / 3600
        
        if elapsed_hours <= 0:
            return 0
        
        rate = EconomyService.calculate_production_rate(
            building.building_type, building.level, kingdom_trait
        )
        max_storage = rate * 24  # 24 hours max storage
        
        produced = min(rate * elapsed_hours, max_storage)
        return int(produced)
    
    @staticmethod
    def calculate_food_consumption(army):
        """Calculate food consumption per hour"""
        if not army:
            return 0
        return (army.infantry * 2) + (army.archers * 3) + (army.cavalry * 5)
    
    @staticmethod
    def calculate_xp_needed(level):
        """Calculate XP needed for next level"""
        return int(100 * (1.5 ** (level - 1)))
    
    @staticmethod
    def calculate_kingdom_power(kingdom):
        """Calculate total kingdom power"""
        power = 0
        if kingdom.army:
            power += kingdom.army.total * 10
        
        for b in kingdom.buildings:
            power += b.level * 100
        
        power += kingdom.level * 500
        
        for h in kingdom.heroes:
            if h.unlocked:
                power += h.level * 200
        
        power += kingdom.battles_won * 50
        return power
    
    @staticmethod
    def calculate_defense_rating(kingdom):
        """Calculate defense rating value"""
        base = kingdom.wall_level * 10
        
        if kingdom.army:
            army_defense = (kingdom.army.infantry * 1 +
                          kingdom.army.archers * 1.5 +
                          kingdom.army.cavalry * 2)
        else:
            army_defense = 0
        
        hero_bonus = 0.0
        for h in kingdom.heroes:
            if h.unlocked:
                hero_bonus += 0.05 * h.level
        
        total = (base + army_defense) * (1 + hero_bonus)
        
        # Trait bonus
        trait = KINGDOM_TRAITS.get(kingdom.trait, {})
        total *= (1 + trait.get("defense_bonus", 0))
        total *= (1 + trait.get("wall_bonus", 0))
        
        return int(total)
    
    @staticmethod
    def process_food_consumption(db, kingdom, hours=1):
        """Process food consumption, handle starvation"""
        if not kingdom.army or kingdom.army.total == 0:
            return 0, False
        
        consumption = EconomyService.calculate_food_consumption(kingdom.army) * hours
        
        if kingdom.food >= consumption:
            kingdom.food -= consumption
            return consumption, False
        else:
            # Starvation
            deficit = consumption - kingdom.food
            desertion_rate = 0.10 * hours
            
            kingdom.army.infantry = int(kingdom.army.infantry * (1 - desertion_rate))
            kingdom.army.archers = int(kingdom.army.archers * (1 - desertion_rate))
            kingdom.army.cavalry = int(kingdom.army.cavalry * (1 - desertion_rate))
            kingdom.food = 0
            
            return consumption, True
