from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), default="en")
    
    # Game state
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(String(500), nullable=True)
    ban_expires = Column(DateTime, nullable=True)
    warning_count = Column(Integer, default=0)
    
    # Tutorial
    tutorial_step = Column(Integer, default=0)  # 0=not started, 3=completed
    
    # Admin
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    kingdom = relationship("Kingdom", back_populates="user", uselist=False)
    achievements = relationship("UserAchievement", back_populates="user")
    notification_prefs = relationship("NotificationPref", back_populates="user", uselist=False)
