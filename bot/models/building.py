from sqlalchemy import Column, Integer, String, DateTime, BigInteger, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kingdom_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    building_type = Column(String(30), nullable=False)  # town_hall, gold_mine, farm, barracks, wall
    level = Column(Integer, default=1)
    
    # Upgrade tracking
    is_upgrading = Column(Boolean, default=False)
    upgrade_started = Column(DateTime, nullable=True)
    upgrade_completes = Column(DateTime, nullable=True)
    
    # Resource collection
    last_collected = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    kingdom = relationship("Kingdom", back_populates="buildings")
    
    @property
    def display_name(self):
        names = {
            "town_hall": "🏰 Town Hall",
            "gold_mine": "⛏ Gold Mine",
            "farm": "🌾 Farm",
            "barracks": "🏹 Barracks",
            "wall": "🛡 Wall"
        }
        return names.get(self.building_type, self.building_type)
    
    @property
    def emoji(self):
        emojis = {
            "town_hall": "🏰",
            "gold_mine": "⛏",
            "farm": "🌾",
            "barracks": "🏹",
            "wall": "🛡"
        }
        return emojis.get(self.building_type, "🏗")
