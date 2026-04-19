from sqlalchemy import Column, Integer, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kingdom_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    season = Column(Integer, default=1)
    power = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    
    battles_won = Column(Integer, default=0)
    total_gold = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    kingdom = relationship("Kingdom", back_populates="leaderboard_entries")
