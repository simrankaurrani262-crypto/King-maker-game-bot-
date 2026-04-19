from sqlalchemy import Column, Integer, BigInteger, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Bounty(Base):
    __tablename__ = "bounties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    placer_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    target_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    reward_gold = Column(Integer, default=0)
    
    claimed_by = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
