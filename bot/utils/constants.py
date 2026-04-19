# Game Balance Constants
STARTER_GOLD = 1000
STARTER_FOOD = 500
STARTER_ENERGY = 10
STARTER_ARMY = 50

MAX_ENERGY = 10
ENERGY_COST_ATTACK = 1
ENERGY_REGEN_MINUTES = 30

NEWBIE_SHIELD_HOURS = 24

MAP_SIZE = 10

BATTLE_REQUEST_TIMEOUT = 30

BUILDING_MAX_LEVEL = 25
BASE_UPGRADE_COST_GOLD = 500
UPGRADE_COST_MULTIPLIER = 1.6
BASE_UPGRADE_TIME_MINUTES = 5
UPGRADE_TIME_MULTIPLIER = 1.4

FOOD_PER_INFANTRY_PER_HOUR = 2
FOOD_PER_ARCHER_PER_HOUR = 3
FOOD_PER_CAVALRY_PER_HOUR = 5
ARMY_STARVATION_THRESHOLD = 0

RANDOM_FACTOR_RANGE = (0.85, 1.15)
WALL_DEFENSE_REDUCTION_PER_LEVEL = 0.03
HERO_BONUS_PERCENT_PER_LEVEL = 0.05
PROXIMITY_ATTACK_BONUS = 0.10

GOLD_MINE_BASE_RATE = 100
FARM_BASE_RATE = 50
BARRACKS_TRAIN_RATE = 10

LEADERBOARD_RESET_DAYS = 14

DICE_COOLDOWN_HOURS = 4
SPIN_COOLDOWN_HOURS = 8
QUIZ_COOLDOWN_HOURS = 6

SPY_COST_GOLD = 300
SPY_SUCCESS_BASE_CHANCE = 0.75
SPY_TRAP_CHANCE = 0.15
SPY_COOLDOWN_MINUTES = 60

RAID_ENERGY_COST = 1
RAID_LOOT_PERCENT = 0.15
RAID_ARMY_LOSS_PERCENT = 0.05

BLACK_MARKET_REFRESH_HOURS = 6
BLACK_MARKET_SLOTS = 4

ALLIANCE_CREATION_COST = 10000
ALLIANCE_MAX_MEMBERS = 20

XP_PER_LEVEL_BASE = 100
XP_LEVEL_MULTIPLIER = 1.5

# Building Config
BUILDING_CONFIG = {
    "town_hall": {
        "emoji": "🏰",
        "name": "Town Hall",
        "description": "Unlocks buildings, sets max level",
        "cost_gold_mult": 1.5,
        "cost_food_mult": 0.5,
        "time_mult": 10,
    },
    "gold_mine": {
        "emoji": "⛏",
        "name": "Gold Mine",
        "description": "Generates Gold per hour",
        "cost_gold_mult": 1.0,
        "cost_food_mult": 0,
        "time_mult": 5,
    },
    "farm": {
        "emoji": "🌾",
        "name": "Farm",
        "description": "Generates Food per hour",
        "cost_gold_mult": 0.8,
        "cost_food_mult": 0,
        "time_mult": 5,
    },
    "barracks": {
        "emoji": "🏹",
        "name": "Barracks",
        "description": "Trains soldiers per hour",
        "cost_gold_mult": 1.0,
        "cost_food_mult": 0.3,
        "time_mult": 8,
    },
    "wall": {
        "emoji": "🛡",
        "name": "Wall",
        "description": "Reduces incoming damage",
        "cost_gold_mult": 1.2,
        "cost_food_mult": 0.4,
        "time_mult": 7,
    },
}

# Army Config
ARMY_CONFIG = {
    "infantry": {
        "emoji": "🗡",
        "name": "Infantry",
        "attack": 10,
        "defense": 8,
        "speed": "Slow",
        "food_cost": 2,
        "train_gold": 50,
        "train_food": 20,
        "unlock": "Starter",
    },
    "archers": {
        "emoji": "🏹",
        "name": "Archers",
        "attack": 12,
        "defense": 5,
        "speed": "Medium",
        "food_cost": 3,
        "train_gold": 80,
        "train_food": 30,
        "unlock": "Barracks Lv.2",
    },
    "cavalry": {
        "emoji": "🐎",
        "name": "Cavalry",
        "attack": 18,
        "defense": 12,
        "speed": "Fast",
        "food_cost": 5,
        "train_gold": 150,
        "train_food": 50,
        "unlock": "Barracks Lv.4",
    },
}

# Kingdom Traits
KINGDOM_TRAITS = {
    "aggressive": {
        "name": "⚔️ Aggressive",
        "description": "+10% attack power, -5% defense & economy",
        "attack_bonus": 0.10,
        "defense_penalty": -0.05,
        "economy_penalty": -0.05,
    },
    "defensive": {
        "name": "🛡 Defensive",
        "description": "+15% defense, +10% wall strength, -5% attack",
        "attack_penalty": -0.05,
        "defense_bonus": 0.15,
        "wall_bonus": 0.10,
    },
    "rich": {
        "name": "💰 Rich",
        "description": "+20% gold production, -5% attack",
        "gold_bonus": 0.20,
        "attack_penalty": -0.05,
    },
    "balanced": {
        "name": "⚖️ Balanced",
        "description": "+5% all stats",
        "attack_bonus": 0.05,
        "defense_bonus": 0.05,
        "gold_bonus": 0.05,
    },
}

# Flags for kingdom creation
FLAGS = [
    "🔥", "⚡", "🌊", "🌪", "❄️", "☀️", "🌙", "⭐",
    "🐉", "🦁", "🦅", "🐺", "🐻", "🦊", "🐍", "🦌",
    "🌹", "🍁", "🌵", "🌲", "💀", "👑", "💎", "🧿",
]

# Skill Tree
SKILL_TREE = {
    "attack": {
        "tier_1": {"name": "Sharp Blades", "effect": 0.05, "cost": 1, "desc": "+5% all damage"},
        "tier_2": {"name": "Cavalry Mastery", "effect": 0.10, "cost": 2, "desc": "+10% cavalry damage", "requires": "tier_1"},
        "tier_3": {"name": "War Cry", "effect": 0.15, "cost": 3, "desc": "+15% attack all", "requires": "tier_2"},
    },
    "defense": {
        "tier_1": {"name": "Sturdy Walls", "effect": 0.05, "cost": 1, "desc": "+5% wall defense"},
        "tier_2": {"name": "Archer Towers", "effect": 0.10, "cost": 2, "desc": "+10% archer defense", "requires": "tier_1"},
        "tier_3": {"name": "Fortress", "effect": 0.15, "cost": 3, "desc": "+15% all defense", "requires": "tier_2"},
    },
    "economy": {
        "tier_1": {"name": "Efficient Mining", "effect": 0.10, "cost": 1, "desc": "+10% gold production"},
        "tier_2": {"name": "Bountiful Harvest", "effect": 0.15, "cost": 2, "desc": "+15% food production", "requires": "tier_1"},
        "tier_3": {"name": "Trade Routes", "effect": 0.20, "cost": 3, "desc": "+20% all production", "requires": "tier_2"},
    },
}

# Decision Events
DECISION_EVENTS = [
    {
        "id": "merchant_offer",
        "message": """🧙 एक mysterious merchant aaya hai!

💰 Option A: 1000 Gold do, 2000 Gold return guarantee
⚔️ Option B: 500 Gold aur 50 Army do, secret weapon milega
🚪 Option C: Ignore karo, kuch nahi hoga""",
        "outcomes": {
            "A": {"gold": 1000, "message": "Merchant ne double return diya! +1000 Gold! 🎉"},
            "B": {"message": "Aapko Dragon Sword mila! +20% attack boost! 🔥"},
            "C": {"message": "Merchant chala gaya..."},
        },
    },
    {
        "id": "wandering_soldier",
        "message": """🗡 Ek bhatakta soldier mila hai!

⚔️ Option A: Apni army mein shamil karo (50 soldiers free)
💰 Option B: Bech do slave market mein (300 Gold)
🛡 Option C: Apne base ka guard banao (+defense boost)""",
        "outcomes": {
            "A": {"infantry": 50, "message": "50 Infantry join kar gaye! ⚔️"},
            "B": {"gold": 300, "message": "300 Gold mila! 💰"},
            "C": {"message": "Base guard mazboot hua! +5% defense! 🛡"},
        },
    },
    {
        "id": "hidden_treasure",
        "message": """🗺 Map par ek hidden location mark hai!

⛏ Option A: Khodo! (Resources mil sakte hain)
🚪 Option B: Ignore karo (khatra ho sakta hai)
🕵️ Option C: Spy bhejo pehle (100 Gold)""",
        "outcomes": {
            "A": {"gold": 500, "food": 200, "message": "Khazana mila! +500 Gold, +200 Food! 💎"},
            "B": {"message": "Kuch nahi hua..."},
            "C": {"gold": 300, "message": "Spy ne 300 Gold ka treasure dhoondha! 💰"},
        },
    },
]

# Black Market Items
BLACK_MARKET_ITEMS = [
    {"name": "🔥 Instant Build", "effect": "skip_build_time", "price_gems": 10, "stock": 3},
    {"name": "⚡ Energy Refill", "effect": "refill_energy", "price_gems": 5, "stock": 5},
    {"name": "🛡 24h Shield", "effect": "extend_shield", "price_gems": 15, "stock": 2},
    {"name": "📜 Spy Intel Pack", "effect": "full_spy_report", "price_gems": 8, "stock": 3},
    {"name": "💰 Gold Bag (10K)", "effect": "add_gold", "price_gems": 20, "stock": 2},
    {"name": "🎲 Lucky Dice", "effect": "extra_dice_roll", "price_gems": 3, "stock": 10},
]

# Mini-game: Spin Wheel
SPIN_WHEEL_ITEMS = [
    {"name": "💎 50 Gems", "gems": 50, "chance": 0.05},
    {"name": "💰 5000 Gold", "gold": 5000, "chance": 0.15},
    {"name": "🍖 2000 Food", "food": 2000, "chance": 0.20},
    {"name": "⚡ Full Energy", "energy": 10, "chance": 0.20},
    {"name": "🛡 12h Shield", "shield_hours": 12, "chance": 0.15},
    {"name": "🎁 Mystery Box", "mystery": True, "chance": 0.10},
    {"name": "❌ Nothing", "nothing": True, "chance": 0.15},
]

# Mini-game: Quiz Questions
QUIZ_QUESTIONS = [
    {
        "question": "Kaunsi army sabse tez hoti hai?",
        "options": ["Infantry", "Archers", "Cavalry", "Mages"],
        "correct": 2,  # Cavalry
    },
    {
        "question": "Gold Mine kya produce karti hai?",
        "options": ["Food", "Gold", "Soldiers", "Gems"],
        "correct": 1,
    },
    {
        "question": "Wall ka kaam kya hai?",
        "options": ["Attack boost", "Damage reduction", "Food production", "Train army"],
        "correct": 1,
    },
    {
        "question": "Kitni Energy max ho sakti hai?",
        "options": ["5", "10", "15", "Unlimited"],
        "correct": 1,
    },
    {
        "question": "New player ko kitne hours ki shield milti hai?",
        "options": ["12h", "24h", "48h", "72h"],
        "correct": 1,
    },
    {
        "question": "Cavalry ka attack power kitna hai?",
        "options": ["10", "12", "18", "20"],
        "correct": 2,
    },
    {
        "question": "Alliance banane mein kitna Gold lagta hai?",
        "options": ["1000", "5000", "10000", "50000"],
        "correct": 2,
    },
]

# Achievements
ACHIEVEMENTS = {
    "first_blood": {"name": "First Blood", "desc": "First battle win", "title": "⚔️ Warrior"},
    "war_lord": {"name": "War Lord", "desc": "Win 50 battles", "title": "👑 War Lord"},
    "rich_king": {"name": "Rich King", "desc": "Have 100K gold", "title": "💰 Rich King"},
    "master_builder": {"name": "Master Builder", "desc": "Max all buildings Lv.10", "title": "🏗 Architect"},
    "spy_master": {"name": "Spy Master", "desc": "100 successful spy missions", "title": "🕵️ Shadow"},
    "survivor": {"name": "Survivor", "desc": "Survive 10 revenge attacks", "title": "🛡 Unbreakable"},
    "diplomat": {"name": "Diplomat", "desc": "Create top 10 alliance", "title": "🤝 Diplomat"},
    "treasure_hunter": {"name": "Treasure Hunter", "desc": "Find 10 hidden treasures", "title": "🗺 Explorer"},
}

# Survival Waves
SURVIVAL_WAVES = [
    {"wave": 1, "enemies": 50, "type": "🧟 Skeletons", "reward_gold": 500},
    {"wave": 2, "enemies": 100, "type": "👹 Goblins", "reward_gold": 1000},
    {"wave": 3, "enemies": 200, "type": "🐺 Werewolves", "reward_gold": 2000},
    {"wave": 4, "enemies": 350, "type": "🐉 Dragons", "reward_gold": 5000},
    {"wave": 5, "enemies": 500, "type": "💀 Demon Lord", "reward_gold": 10000},
]

# Battle Emotes
BATTLE_EMOTES = {
    "attack": ["😈", "🔥", "💀", "⚔️", "👊"],
    "defense": ["🛡", "💪", "😤", "🧱", "✋"],
    "taunt": ["😂", "🤣", "😜", "🙃", "😏"],
    "respect": ["🫡", "👏", "💯", "🔥", "👑"],
}
