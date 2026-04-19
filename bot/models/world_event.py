from sqlalchemy import Column, Integer, String, DateTime, Text
from .database import Base
from datetime import datetime


class WorldEvent(Base):
    __tablename__ = "world_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)  # treasure, plague, festival, invasion
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    effect_data = Column(Text, nullable=True)  # JSON string
    
    started_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=True)
    
    is_active = Column(Integer, default=1)  # 1=active, 0=ended
