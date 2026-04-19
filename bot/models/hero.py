"""
King-Maker Bot — Elite Edition
Hero Model — Fixed bonus calculations for locked heroes.
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from bot.models.database import Base


class Hero(Base):
    """Elite Hero model with proper bonus calculations."""

    __tablename__ = "heroes"

    id = Column(Integer, primary_key=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.user_id"))
    hero_type = Column(String, default="commander")
    display_name = Column(String, default="Unknown")
    unlocked = Column(Boolean, default=False)
    level = Column(Integer, default=0)
    skill_points = Column(Integer, default=0)
    skill_tree = Column(String, default="{}")  # JSON string of unlocked skills

    # FIXED: Store base stats directly instead of relying on formula
    attack_stat = Column(Float, default=0.0)
    defense_stat = Column(Float, default=0.0)
    economy_stat = Column(Float, default=0.0)

    kingdom = relationship("Kingdom", back_populates="heroes")

    @property
    def attack_bonus(self) -> float:
        """Return attack bonus — FIXED: Returns 0 for locked heroes."""
        if not self.unlocked:
            return 0.0
        # Level 1 = base 5.0, each level adds 2.5
        return 5.0 + ((self.level - 1) * 2.5)

    @property
    def defense_bonus(self) -> float:
        """Return defense bonus — FIXED: Returns 0 for locked heroes."""
        if not self.unlocked:
            return 0.0
        return 5.0 + ((self.level - 1) * 2.5)

    @property
    def economy_bonus(self) -> float:
        """Return economy bonus — FIXED: Returns 0 for locked heroes."""
        if not self.unlocked:
            return 0.0
        return 3.0 + ((self.level - 1) * 1.5)

    @property
    def xp_needed(self) -> int:
        """XP needed for next level."""
        if not self.unlocked:
            return 50
        return int(50 * (self.level ** 1.5))

    @property
    def upgrade_cost(self) -> int:
        """Gold cost to upgrade hero."""
        if not self.unlocked:
            return 100
        return 50 * self.level

    def get_skill_tree_data(self):
        """Parse skill tree JSON."""
        import json
        try:
            return json.loads(self.skill_tree) if self.skill_tree else {}
        except Exception:
            return {}

    def unlock_skill(self, skill_name: str):
        """Unlock a skill in the skill tree."""
        import json
        skills = self.get_skill_tree_data()
        skills[skill_name] = True
        self.skill_tree = json.dumps(skills)

    def __repr__(self):
        return f"<Hero {self.display_name} Lv.{self.level} {'✅' if self.unlocked else '🔒'}>"
