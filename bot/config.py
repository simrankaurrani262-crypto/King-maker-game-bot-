import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Advanced Game Configuration with full customization"""
    
    # ─── Telegram ───
    TELEGRAM_BOT_TOKEN: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    WEBHOOK_URL: str = field(default_factory=lambda: os.getenv("WEBHOOK_URL", ""))
    WEBHOOK_PORT: int = field(default_factory=lambda: int(os.getenv("WEBHOOK_PORT", "8443")))
    USE_WEBHOOK: bool = field(default_factory=lambda: os.getenv("USE_WEBHOOK", "false").lower() == "true")
    
    # ─── Database ───
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///kingdom_game.db"))
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # ─── Admin ───
    ADMIN_TELEGRAM_ID: int = field(default_factory=lambda: int(os.getenv("ADMIN_TELEGRAM_ID", "0")))
    ADMIN_COMMAND_PREFIX: str = "/admin"
    
    # ─── Game Balance ───
    STARTER_GOLD: int = 1000
    STARTER_FOOD: int = 500
    STARTER_GEMS: int = 0
    STARTER_ENERGY: int = 10
    STARTER_ARMY: int = 50
    
    MAX_ENERGY: int = 10
    ENERGY_COST_ATTACK: int = 1
    ENERGY_COST_RAID: int = 1
    ENERGY_COST_SPY: int = 0
    ENERGY_REGEN_MINUTES: int = 30
    
    NEWBIE_SHIELD_HOURS: int = 24
    SHIELD_BREAK_ON_ATTACK: bool = True
    SHIELD_EXTEND_HOURS: int = 24
    
    # ─── Map System ───
    MAP_SIZE: int = 15
    MAP_SECTORS: int = 9  # 3x3 grid view
    
    # ─── Battle System ───
    BATTLE_REQUEST_TIMEOUT: int = 30
    BATTLE_ROUNDS_MIN: int = 3
    BATTLE_ROUNDS_MAX: int = 7
    MAX_BATTLE_LOG_ENTRIES: int = 50
    
    # ─── Building System ───
    BUILDING_MAX_LEVEL: int = 25
    BASE_UPGRADE_COST_GOLD: int = 500
    UPGRADE_COST_MULTIPLIER: float = 1.6
    BASE_UPGRADE_TIME_MINUTES: int = 5
    UPGRADE_TIME_MULTIPLIER: float = 1.4
    MAX_OFFLINE_COLLECTION_HOURS: int = 24
    
    # ─── Army System ───
    FOOD_PER_INFANTRY_PER_HOUR: int = 2
    FOOD_PER_ARCHER_PER_HOUR: int = 3
    FOOD_PER_CAVALRY_PER_HOUR: int = 5
    ARMY_STARVATION_THRESHOLD: int = 0
    ARMY_STARVATION_DESERTION_RATE: float = 0.10
    
    # ─── Combat Formulas ───
    RANDOM_FACTOR_RANGE: tuple = (0.85, 1.15)
    WALL_DEFENSE_REDUCTION_PER_LEVEL: float = 0.03
    HERO_BONUS_PERCENT_PER_LEVEL: float = 0.05
    PROXIMITY_ATTACK_BONUS: float = 0.10
    PROXIMITY_BONUS_CLOSE: float = 1.10  # Distance <= 2
    PROXIMITY_BONUS_MEDIUM: float = 1.05  # Distance <= 4
    RAID_LOOT_PERCENT: float = 0.15
    RAID_ARMY_LOSS_PERCENT: float = 0.05
    RAID_FAIL_ARMY_LOSS_PERCENT: float = 0.10
    ATTACK_GOLD_LOOT_PERCENT: float = 0.20
    DEFEAT_XP_PARTICIPATION: int = 25
    VICTORY_XP_BASE: int = 100
    
    # ─── Production Rates ───
    GOLD_MINE_BASE_RATE: int = 100
    FARM_BASE_RATE: int = 50
    BARRACKS_TRAIN_RATE: int = 10
    
    # ─── Leaderboard ───
    LEADERBOARD_RESET_DAYS: int = 14
    LEADERBOARD_TOP_LIMIT: int = 50
    
    # ─── Mini-games ───
    DICE_COOLDOWN_HOURS: int = 4
    SPIN_COOLDOWN_HOURS: int = 8
    QUIZ_COOLDOWN_HOURS: int = 6
    SURVIVAL_MAX_WAVES: int = 5
    
    # ─── Spy System ───
    SPY_COST_GOLD: int = 300
    SPY_SUCCESS_BASE_CHANCE: float = 0.75
    SPY_TRAP_CHANCE: float = 0.15
    SPY_COOLDOWN_MINUTES: int = 60
    
    # ─── Black Market ───
    BLACK_MARKET_REFRESH_HOURS: int = 6
    BLACK_MARKET_SLOTS: int = 4
    
    # ─── XP System ───
    XP_PER_LEVEL_BASE: int = 100
    XP_LEVEL_MULTIPLIER: float = 1.5
    
    # ─── Alliance System ───
    ALLIANCE_CREATION_COST: int = 10000
    ALLIANCE_MAX_MEMBERS: int = 20
    ALLIANCE_DONATION_MULTIPLIER: float = 1.5
    
    # ─── World Events ───
    WORLD_EVENT_INTERVAL_MINUTES: int = 15
    WORLD_EVENT_CHANCE: float = 0.30
    WORLD_EVENT_DURATION_HOURS: int = 6
    
    # ─── NPC System ───
    NPC_ATTACK_INTERVAL_MINUTES: int = 20
    NPC_ATTACK_MAX_LEVEL: int = 5
    NPC_ATTACK_CHANCE: float = 0.25
    NPC_NAMES: list = field(default_factory=lambda: [
        "Shadow King", "Dark Emperor", "Crimson Lord", 
        "Ice Queen", "Fire Tyrant", "Nightmare Lord",
        "Bone Collector", "Storm Bringer", "Plague Master"
    ])
    
    # ─── Decision Events ───
    DECISION_EVENT_INTERVAL_HOURS: int = 6
    DECISION_EVENT_CHANCE: float = 0.10
    DECISION_EVENT_PLAYER_CHANCE: float = 0.05
    
    # ─── Bot Settings ───
    MAINTENANCE_MODE: bool = False
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_BURST: int = 10
    COMMAND_COOLDOWN_SECONDS: int = 2
    
    # ─── Graphics Settings ───
    ENABLE_GRAPHICS: bool = True
    CHART_STYLE: str = "dark_background"
    CHART_DPI: int = 150
    CHART_FIGURE_SIZE: tuple = (10, 6)
    ENABLE_BATTLE_ANIMATION: bool = True
    BATTLE_ANIMATION_FRAMES: int = 5
    
    # ─── Notification Settings ───
    NOTIFICATION_BATCH_SIZE: int = 50
    NOTIFICATION_RETRY_ATTEMPTS: int = 3
    
    # ─── Cleanup Settings ───
    INACTIVE_PLAYER_SHIELD_HOURS: int = 48
    INACTIVE_PLAYER_DAYS: int = 7
    BATTLE_LOG_RETENTION_DAYS: int = 30
    
    # ─── Feature Flags ───
    FEATURE_WORLD_EVENTS: bool = True
    FEATURE_NPC_ATTACKS: bool = True
    FEATURE_DECISION_EVENTS: bool = True
    FEATURE_BLACK_MARKET: bool = True
    FEATURE_SURVIVAL_MODE: bool = True
    FEATURE_ALLIANCE_WARS: bool = False  # Coming in v2.1
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return any errors"""
        errors = {}
        
        if not self.TELEGRAM_BOT_TOKEN:
            errors["TELEGRAM_BOT_TOKEN"] = "Telegram bot token is required"
        
        if self.MAP_SIZE < 5 or self.MAP_SIZE > 50:
            errors["MAP_SIZE"] = "Map size must be between 5 and 50"
        
        if self.MAX_ENERGY < 1 or self.MAX_ENERGY > 100:
            errors["MAX_ENERGY"] = "Max energy must be between 1 and 100"
        
        if self.BUILDING_MAX_LEVEL < 1 or self.BUILDING_MAX_LEVEL > 100:
            errors["BUILDING_MAX_LEVEL"] = "Building max level must be between 1 and 100"
        
        if self.RATE_LIMIT_PER_MINUTE < 1:
            errors["RATE_LIMIT_PER_MINUTE"] = "Rate limit must be at least 1"
        
        if self.STARTER_GOLD < 0 or self.STARTER_FOOD < 0:
            errors["STARTER_RESOURCES"] = "Starter resources cannot be negative"
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for display"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }


# Global config instance
config = Config()
