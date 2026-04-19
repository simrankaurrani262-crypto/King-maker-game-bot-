from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quest_type = Column(String(20), nullable=False)  # daily, milestone
    quest_key = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    requirement_value = Column(Integer, default=1)
    reward_gold = Column(Integer, default=0)
    reward_food = Column(Integer, default=0)
    reward_gems = Column(Integer, default=0)
    reward_xp = Column(Integer, default=0)
    reward_title = Column(String(50), nullable=True)


class UserQuest(Base):
    __tablename__ = "user_quests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kingdom_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    quest_id = Column(Integer, ForeignKey("quests.id"), nullable=False)
    
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    claimed = Column(Boolean, default=False)
    reset_at = Column(DateTime, nullable=True)  # For daily quests
    
    # Relationships
    kingdom = relationship("Kingdom", back_populates="quests")
    quest = relationship("Quest")
