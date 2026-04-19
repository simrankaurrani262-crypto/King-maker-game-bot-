from sqlalchemy import Column, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Army(Base):
    __tablename__ = "armies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kingdom_id = Column(BigInteger, ForeignKey("kingdoms.user_id"), unique=True, nullable=False)
    
    infantry = Column(Integer, default=50)
    archers = Column(Integer, default=0)
    cavalry = Column(Integer, default=0)
    
    # Training queue
    training_infantry = Column(Integer, default=0)
    training_archers = Column(Integer, default=0)
    training_cavalry = Column(Integer, default=0)
    training_complete_at = Column(Integer, nullable=True)  # timestamp
    
    # Relationships
    kingdom = relationship("Kingdom", back_populates="army")
    
    @property
    def total(self):
        return self.infantry + self.archers + self.cavalry
    
    @property
    def food_consumption_per_hour(self):
        return (self.infantry * 2) + (self.archers * 3) + (self.cavalry * 5)
