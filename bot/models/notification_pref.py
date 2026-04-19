from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class NotificationPref(Base):
    __tablename__ = "notification_prefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    
    battle_alerts = Column(Boolean, default=True)
    energy_full = Column(Boolean, default=True)
    resource_full = Column(Boolean, default=True)
    building_complete = Column(Boolean, default=True)
    alliance_events = Column(Boolean, default=True)
    bounty_alerts = Column(Boolean, default=True)
    promotions = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="notification_prefs")
