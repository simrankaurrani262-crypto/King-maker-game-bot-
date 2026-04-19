from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Battle(Base):
    __tablename__ = "battles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attacker_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    defender_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    
    winner_id = Column(BigInteger, nullable=True)  # null = draw
    
    # Battle data (JSON string of rounds)
    battle_log = Column(Text, nullable=True)
    
    # Results
    gold_looted = Column(Integer, default=0)
    xp_gained = Column(Integer, default=0)
    
    # Losses
    attacker_infantry_lost = Column(Integer, default=0)
    attacker_archers_lost = Column(Integer, default=0)
    attacker_cavalry_lost = Column(Integer, default=0)
    
    defender_infantry_lost = Column(Integer, default=0)
    defender_archers_lost = Column(Integer, default=0)
    defender_cavalry_lost = Column(Integer, default=0)
    
    # Metadata
    is_revenge = Column(Integer, default=0)  # 0 or 1
    is_raid = Column(Integer, default=0)  # 0 or 1
    is_tutorial = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    attacker_kingdom = relationship("Kingdom", foreign_keys=[attacker_id], back_populates="battles_attacker")
    defender_kingdom = relationship("Kingdom", foreign_keys=[defender_id], back_populates="battles_defender")
