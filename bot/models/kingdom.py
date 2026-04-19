from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime, timedelta


class Kingdom(Base):
    __tablename__ = "kingdoms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    flag = Column(String(10), default="🏰")
    
    # Kingdom level & XP
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    
    # Resources
    gold = Column(Integer, default=1000)
    food = Column(Integer, default=500)
    gems = Column(Integer, default=0)
    energy = Column(Integer, default=10)
    max_energy = Column(Integer, default=10)
    last_energy_regen = Column(DateTime, default=datetime.utcnow)
    
    # Map position
    map_x = Column(Integer, default=1)
    map_y = Column(Integer, default=1)
    
    # Shield
    shield_expires = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    
    # Kingdom trait
    trait = Column(String(20), default="balanced")  # aggressive, defensive, rich, balanced
    
    # Stats
    battles_won = Column(Integer, default=0)
    battles_lost = Column(Integer, default=0)
    total_gold_earned = Column(Integer, default=0)
    total_gold_looted = Column(Integer, default=0)
    soldiers_trained = Column(Integer, default=0)
    buildings_upgraded = Column(Integer, default=0)
    spy_missions = Column(Integer, default=0)
    successful_spies = Column(Integer, default=0)
    
    # Title
    current_title = Column(String(50), nullable=True)
    
    # Decision event cooldown
    last_decision_event = Column(DateTime, nullable=True)
    
    # Online status
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Creation
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="kingdom")
    buildings = relationship("Building", back_populates="kingdom")
    army = relationship("Army", back_populates="kingdom", uselist=False)
    heroes = relationship("Hero", back_populates="kingdom")
    battles_attacker = relationship("Battle", foreign_keys="Battle.attacker_id", back_populates="attacker_kingdom")
    battles_defender = relationship("Battle", foreign_keys="Battle.defender_id", back_populates="defender_kingdom")
    alliance_member = relationship("AllianceMember", back_populates="kingdom", uselist=False)
    quests = relationship("UserQuest", back_populates="kingdom")
    spy_reports_sent = relationship("SpyReport", foreign_keys="SpyReport.spy_id", back_populates="spy_kingdom")
    spy_reports_received = relationship("SpyReport", foreign_keys="SpyReport.target_id", back_populates="target_kingdom")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="kingdom")
    
    @property
    def total_army(self):
        if self.army:
            return self.army.infantry + self.army.archers + self.army.cavalry
        return 0
    
    @property
    def is_online(self):
        now = datetime.utcnow()
        return (now - self.last_active).total_seconds() < 300  # 5 min
    
    @property
    def has_shield(self):
        if self.shield_expires:
            return datetime.utcnow() < self.shield_expires
        return False
    
    @property
    def shield_time_remaining(self):
        if self.has_shield:
            remaining = self.shield_expires - datetime.utcnow()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
        return "No Shield"
    
    @property
    def power(self):
        """Calculate total kingdom power for leaderboard"""
        power = 0
        power += self.total_army * 10 if self.army else 0
        
        for b in self.buildings:
            power += b.level * 100
        
        power += self.level * 500
        
        for h in self.heroes:
            if h.unlocked:
                power += h.level * 200
        
        power += self.battles_won * 50
        return power
    
    @property
    def wall_level(self):
        for b in self.buildings:
            if b.building_type == "wall":
                return b.level
        return 1
    
    @property
    def town_hall_level(self):
        for b in self.buildings:
            if b.building_type == "town_hall":
                return b.level
        return 1
