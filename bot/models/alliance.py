from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Alliance(Base):
    __tablename__ = "alliances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    tag = Column(String(10), nullable=True)
    description = Column(String(500), nullable=True)
    
    leader_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    
    # Treasury
    gold_treasury = Column(Integer, default=0)
    
    # Stats
    total_power = Column(Integer, default=0)
    wars_won = Column(Integer, default=0)
    wars_lost = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    members = relationship("AllianceMember", back_populates="alliance")


class AllianceMember(Base):
    __tablename__ = "alliance_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alliance_id = Column(Integer, ForeignKey("alliances.id"), nullable=False)
    kingdom_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), unique=True, nullable=False)
    
    role = Column(String(20), default="member")  # leader, officer, member
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alliance = relationship("Alliance", back_populates="members")
    kingdom = relationship("Kingdom", back_populates="alliance_member")
