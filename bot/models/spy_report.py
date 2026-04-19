from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class SpyReport(Base):
    __tablename__ = "spy_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spy_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    target_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), nullable=False)
    
    intel_level = Column(String(20), default="basic")  # basic, detailed, full
    report_text = Column(Text, nullable=True)
    success = Column(Integer, default=1)  # 0=caught/failed, 1=success
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    spy_kingdom = relationship("Kingdom", foreign_keys=[spy_id], back_populates="spy_reports_sent")
    target_kingdom = relationship("Kingdom", foreign_keys=[target_id], back_populates="spy_reports_received")
