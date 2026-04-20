from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from .database import Base


class Hero(Base):
    __tablename__ = "heroes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kingdom_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    
    hero_type = Column(String(30), nullable=False)  # sir_aldric, lyra, kael, morgana, shadow
    level = Column(Integer, default=0)
    unlocked = Column(Boolean, default=False)
    
    # Skill tree points spent
    attack_points = Column(Integer, default=0)
    defense_points = Column(Integer, default=0)
    economy_points = Column(Integer, default=0)
    
    # Relationships
    kingdom = relationship("Kingdom", back_populates="heroes")
    
    @property
    def display_name(self):
        names = {
            "sir_aldric": "⚔️ Sir Aldric",
            "lyra": "🏹 Lyra",
            "kael": "🐎 Kael",
            "morgana": "🧙 Morgana",
            "shadow": "🗡 Shadow"
        }
        return names.get(self.hero_type, self.hero_type)
    
    @property
    def attack_bonus(self):
        if not self.unlocked:
            return 0.0
        bonuses = {
            "sir_aldric": 0.15,
            "lyra": 0.0,
            "kael": 0.0,
            "morgana": 0.10,
            "shadow": 0.30
        }
        base = bonuses.get(self.hero_type, 0)
        # Level scaling: each level adds 3% to base
        base_per_level = {
            "sir_aldric": 0.03,
            "lyra": 0.04,
            "kael": 0.05,
            "morgana": 0.02,
            "shadow": 0.05
        }
        return base + (base_per_level.get(self.hero_type, 0) * (self.level - 1))
    
    @property
    def defense_bonus(self):
        if not self.unlocked:
            return 0.0
        # Same pattern for defense
        return 0.0
    
    @property
    def skill_description(self):
        descs = {
            "sir_aldric": f"+{int(self.attack_bonus * 100)}% Infantry ⚔️",
            "lyra": f"+{int(self.attack_bonus * 100)}% Archer 🏹" if self.unlocked else "+20% Archer 🏹",
            "kael": f"+{int(self.attack_bonus * 100)}% Cavalry 🐎" if self.unlocked else "+25% Cavalry 🐎",
            "morgana": "Fireball: 10% AoE damage 🔥",
            "shadow": "First strike: +30% round 1 ⚡"
        }
        return descs.get(self.hero_type, "Unknown")
    
    @property
    def unlock_cost(self):
        costs = {
            "sir_aldric": 0,
            "lyra": 2000,
            "kael": 5000,
            "morgana": 50,  # gems
            "shadow": 75    # gems
        }
        return costs.get(self.hero_type, 0)
    
    @property
    def unlock_requirement(self):
        reqs = {
            "sir_aldric": "Barracks Lv.3",
            "lyra": "Barracks Lv.5",
            "kael": "Barracks Lv.7",
            "morgana": "Premium (50 Gems)",
            "shadow": "Premium (75 Gems)"
        }
        return reqs.get(self.hero_type, "")
