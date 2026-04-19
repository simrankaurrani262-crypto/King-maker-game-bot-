import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Game configuration loaded from environment variables"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8443"))
    USE_WEBHOOK: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///kingdom_game.db")
    
    # Admin
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
    
    # Game Balance
    STARTER_GOLD: int = 1000
    STARTER_FOOD: int = 500
    STARTER_ENERGY: int = 10
    STARTER_ARMY: int = 50
    
    MAX_ENERGY: int = 10
    ENERGY_COST_ATTACK: int = 1
    ENERGY_REGEN_MINUTES: int = 30
    
    NEWBIE_SHIELD_HOURS: int = 24
    SHIELD_BREAK_ON_ATTACK: bool = True
    
    MAP_SIZE: int = 10
    
    BATTLE_REQUEST_TIMEOUT: int = 30
    
    BUILDING_MAX_LEVEL: int = 25
    BASE_UPGRADE_TIME_MINUTES: int = 5
    UPGRADE_TIME_MULTIPLIER: float = 1.4
    BASE_UPGRADE_COST_GOLD: int = 500
    UPGRADE_COST_MULTIPLIER: float = 1.6
    
    FOOD_PER_ARMY_PER_HOUR: int = 2
    ARMY_STARVATION_THRESHOLD: int = 0
    
    RANDOM_FACTOR_RANGE: tuple = (0.85, 1.15)
    WALL_DEFENSE_REDUCTION_PER_LEVEL: float = 0.03
    HERO_BONUS_PERCENT_PER_LEVEL: float = 0.05
    PROXIMITY_ATTACK_BONUS: float = 0.10
    
    GOLD_MINE_BASE_RATE: int = 100
    FARM_BASE_RATE: int = 50
    BARRACKS_TRAIN_RATE: int = 10
    
    LEADERBOARD_RESET_DAYS: int = 14
    
    DICE_COOLDOWN_HOURS: int = 4
    SPIN_COOLDOWN_HOURS: int = 8
    QUIZ_COOLDOWN_HOURS: int = 6
    
    SPY_COST_GOLD: int = 300
    SPY_SUCCESS_BASE_CHANCE: float = 0.75
    SPY_TRAP_CHANCE: float = 0.15
    SPY_COOLDOWN_MINUTES: int = 60
    
    RAID_ENERGY_COST: int = 1
    RAID_LOOT_PERCENT: float = 0.15
    RAID_ARMY_LOSS_PERCENT: float = 0.05
    
    BLACK_MARKET_REFRESH_HOURS: int = 6
    BLACK_MARKET_SLOTS: int = 4
    
    # XP System
    XP_PER_LEVEL_BASE: int = 100
    XP_LEVEL_MULTIPLIER: float = 1.5
    
    # Alliance
    ALLIANCE_CREATION_COST: int = 10000
    ALLIANCE_MAX_MEMBERS: int = 20
    
    # Bot settings
    MAINTENANCE_MODE: bool = False


# Global config instance
config = Config()
