from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from .database import Base
from datetime import datetime


class Cooldown(Base):
    __tablename__ = "cooldowns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(50), nullable=False)  # dice, spin, quiz, spy, attack, etc.
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
