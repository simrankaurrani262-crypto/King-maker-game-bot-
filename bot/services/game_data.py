"""
Game Data Service - Central Data Access Layer
Fixed version with proper session handling, transaction safety,
and corrected attribute access patterns.
"""

import random
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import func

from bot.models import (
    get_db, User, Kingdom, Building, Army, Hero, Battle,
    Alliance, AllianceMember, Quest, UserQuest, SpyReport,
    Bounty, Cooldown, Achievement, UserAchievement,
    LeaderboardEntry, WorldEvent, NotificationPref
)
from bot.utils.constants import (
    STARTER_GOLD, STARTER_FOOD, STARTER_ENERGY, STARTER_ARMY,
    MAP_SIZE, XP_PER_LEVEL_BASE, XP_LEVEL_MULTIPLIER,
    ACHIEVEMENTS, FLAGS
)

logger = logging.getLogger(__name__)


class GameData:
    """Central game data access layer with transaction safety"""
    
    # ─── USER OPERATIONS ───
    
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None, 
                          last_name: str = None, language_code: str = "en") -> Optional[User]:
        """Get existing user or create new one"""
        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if not user:
                    user = User(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        language_code=language_code,
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    
                    # Create default notification prefs
                    try:
                        prefs = NotificationPref(user_id=telegram_id)
                        db.add(prefs)
                        db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to create notification prefs: {e}")
                else:
                    # Update last active
                    user.last_active = datetime.utcnow()
                    if username:
                        user.username = username
                    db.commit()
                
                return user
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return None
    
    @staticmethod
    def get_user(telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        try:
            with get_db() as db:
                return db.query(User).filter(User.telegram_id == telegram_id).first()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    # ─── KINGDOM OPERATIONS ───
    
    @staticmethod
    def create_kingdom(user_id: int, name: str, flag: str, trait: str = "balanced") -> Optional[Kingdom]:
        """Create a new kingdom with all defaults - FIXED with transaction safety"""
        try:
            with get_db() as db:
                # Find empty map position
                existing_positions = []
                try:
                    existing = db.query(Kingdom.map_x, Kingdom.map_y).all()
                    existing_positions = [(x, y) for x, y in existing]
                except Exception:
                    pass
                
                max_attempts = 100
                x, y = 1, 1
                for _ in range(max_attempts):
                    cx = random.randint(1, MAP_SIZE)
                    cy = random.randint(1, MAP_SIZE)
                    if (cx, cy) not in existing_positions:
                        x, y = cx, cy
                        break
                
                kingdom = Kingdom(
                    user_id=user_id,
                    name=name,
                    flag=flag,
                    trait=trait,
                    gold=STARTER_GOLD,
                    food=STARTER_FOOD,
                    energy=STARTER_ENERGY,
                    map_x=x,
                    map_y=y,
                    shield_expires=datetime.utcnow() + timedelta(hours=24),
                )
                db.add(kingdom)
                db.commit()
                db.refresh(kingdom)
                
                # Create default buildings
                buildings = [
                    Building(kingdom_id=user_id, building_type="town_hall", level=1),
                    Building(kingdom_id=user_id, building_type="gold_mine", level=1),
                    Building(kingdom_id=user_id, building_type="farm", level=1),
                    Building(kingdom_id=user_id, building_type="barracks", level=1),
                    Building(kingdom_id=user_id, building_type="wall", level=1),
                ]
                for b in buildings:
                    db.add(b)
                db.commit()
                
                # Create army
                army = Army(kingdom_id=user_id, infantry=STARTER_ARMY, archers=0, cavalry=0)
                db.add(army)
                db.commit()
                
                # Create default heroes
                heroes = [
                    Hero(kingdom_id=user_id, hero_type="sir_aldric", level=1, unlocked=True),
                    Hero(kingdom_id=user_id, hero_type="lyra", level=0, unlocked=False),
                    Hero(kingdom_id=user_id, hero_type="kael", level=0, unlocked=False),
                    Hero(kingdom_id=user_id, hero_type="morgana", level=0, unlocked=False),
                    Hero(kingdom_id=user_id, hero_type="shadow", level=0, unlocked=False),
                ]
                for h in heroes:
                    db.add(h)
                db.commit()
                
                # Create default quests
                GameData._create_default_quests(db, user_id)
                
                # Create default achievements
                GameData._create_default_achievements(db, user_id)
                
                db.refresh(kingdom)
                return kingdom
        
        except Exception as e:
            logger.error(f"Error creating kingdom: {e}")
            return None
    
    @staticmethod
    def _create_default_quests(db, kingdom_id: int):
        """Create default quests for a new kingdom"""
        try:
            quest_data = [
                # Daily quests
                {"quest_type": "daily", "quest_key": "daily_battler", "name": "Daily Battler",
                 "description": "Win 2 PvP battles", "requirement_value": 2,
                 "reward_gold": 500, "reward_xp": 50},
                {"quest_type": "daily", "quest_key": "daily_collector", "name": "Resource Collector",
                 "description": "Collect 5,000 total resources", "requirement_value": 5000,
                 "reward_gold": 300, "reward_gems": 1},
                {"quest_type": "daily", "quest_key": "daily_builder", "name": "Builder",
                 "description": "Complete 3 building upgrades", "requirement_value": 3,
                 "reward_gold": 400, "reward_food": 100},
                {"quest_type": "daily", "quest_key": "daily_trainer", "name": "Army Trainer",
                 "description": "Train 50 soldiers", "requirement_value": 50,
                 "reward_gold": 200, "reward_food": 50},
                {"quest_type": "daily", "quest_key": "daily_spy", "name": "Spy Master",
                 "description": "Send 2 spy missions", "requirement_value": 2,
                 "reward_gold": 250},
                # Milestone quests
                {"quest_type": "milestone", "quest_key": "first_blood", "name": "First Blood",
                 "description": "Win first battle", "requirement_value": 1,
                 "reward_gold": 1000, "reward_title": "⚔️ Warrior"},
                {"quest_type": "milestone", "quest_key": "wealthy_king", "name": "Wealthy King",
                 "description": "Accumulate 100,000 Gold", "requirement_value": 100000,
                 "reward_gems": 10, "reward_title": "💰 Rich King"},
                {"quest_type": "milestone", "quest_key": "master_builder", "name": "Master Builder",
                 "description": "Max all buildings to Lv.10", "requirement_value": 10,
                 "reward_gold": 5000, "reward_gems": 5},
                {"quest_type": "milestone", "quest_key": "war_lord", "name": "War Lord",
                 "description": "Win 50 battles", "requirement_value": 50,
                 "reward_gold": 5000, "reward_title": "👑 War Lord"},
            ]
            
            for qd in quest_data:
                quest = db.query(Quest).filter(Quest.quest_key == qd["quest_key"]).first()
                if not quest:
                    quest = Quest(**qd)
                    db.add(quest)
                    db.commit()
                    db.refresh(quest)
                
                # Check if user quest already exists
                existing = db.query(UserQuest).filter(
                    UserQuest.kingdom_id == kingdom_id,
                    UserQuest.quest_id == quest.id
                ).first()
                
                if not existing:
                    user_quest = UserQuest(kingdom_id=kingdom_id, quest_id=quest.id)
                    if qd["quest_type"] == "daily":
                        user_quest.reset_at = datetime.utcnow() + timedelta(days=1)
                    db.add(user_quest)
            
            db.commit()
        
        except Exception as e:
            logger.error(f"Error creating default quests: {e}")
            db.rollback()
    
    @staticmethod
    def _create_default_achievements(db, user_id: int):
        """Create default achievements"""
        try:
            for key, data in ACHIEVEMENTS.items():
                existing = db.query(Achievement).filter(Achievement.achievement_key == key).first()
                if not existing:
                    ach = Achievement(
                        achievement_key=key,
                        name=data["name"],
                        description=data["desc"],
                        title_reward=data.get("title"),
                    )
                    db.add(ach)
                    db.commit()
                    db.refresh(ach)
                    
                    user_ach = UserAchievement(user_id=user_id, achievement_id=ach.id)
                    db.add(user_ach)
            db.commit()
        
        except Exception as e:
            logger.error(f"Error creating default achievements: {e}")
            db.rollback()
    
    @staticmethod
    def get_kingdom(user_id: int, db_session=None) -> Optional[Kingdom]:
        """Get kingdom by user ID - no expunge to keep relationships alive"""
        try:
            if db_session:
                return db_session.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            with get_db() as db:
                return db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting kingdom: {e}")
            return None
    
    @staticmethod
    def get_kingdom_with_relations(user_id: int) -> Optional[Kingdom]:
        """Get kingdom with all related objects loaded within session"""
        try:
            with get_db() as db:
                kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
                if kingdom:
                    # Force load relationships within session
                    _ = getattr(kingdom, 'buildings', [])
                    _ = getattr(kingdom, 'army', None)
                    _ = getattr(kingdom, 'heroes', [])
                return kingdom
        except Exception as e:
            logger.error(f"Error getting kingdom with relations: {e}")
            return None
    
    @staticmethod
    def get_all_kingdoms() -> List[Kingdom]:
        """Get all kingdoms"""
        try:
            with get_db() as db:
                return db.query(Kingdom).all()
        except Exception as e:
            logger.error(f"Error getting all kingdoms: {e}")
            return []
    
    @staticmethod
    def get_buildings(user_id: int) -> List[Building]:
        """Get all buildings for a kingdom"""
        try:
            with get_db() as db:
                return db.query(Building).filter(Building.kingdom_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting buildings: {e}")
            return []
    
    @staticmethod
    def get_building(user_id: int, building_type: str) -> Optional[Building]:
        """Get specific building"""
        try:
            with get_db() as db:
                return db.query(Building).filter(
                    Building.kingdom_id == user_id,
                    Building.building_type == building_type
                ).first()
        except Exception as e:
            logger.error(f"Error getting building: {e}")
            return None
    
    @staticmethod
    def get_army(user_id: int) -> Optional[Army]:
        """Get army for a kingdom"""
        try:
            with get_db() as db:
                return db.query(Army).filter(Army.kingdom_id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting army: {e}")
            return None
    
    @staticmethod
    def get_heroes(user_id: int) -> List[Hero]:
        """Get all heroes for a kingdom"""
        try:
            with get_db() as db:
                return db.query(Hero).filter(Hero.kingdom_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting heroes: {e}")
            return []
    
    @staticmethod
    def get_hero(user_id: int, hero_type: str) -> Optional[Hero]:
        """Get specific hero"""
        try:
            with get_db() as db:
                return db.query(Hero).filter(
                    Hero.kingdom_id == user_id,
                    Hero.hero_type == hero_type
                ).first()
        except Exception as e:
            logger.error(f"Error getting hero: {e}")
            return None
    
    # ─── FIND OPPONENTS ───
    
    @staticmethod
    def find_opponents(attacker_id: int, limit: int = 3) -> List[tuple]:
        """Find suitable attack opponents - FIXED with safe attribute access"""
        try:
            from bot.services.economy import EconomyService
            
            with get_db() as db:
                attacker = db.query(Kingdom).filter(Kingdom.user_id == attacker_id).first()
                if not attacker:
                    return []
                
                attacker_level = getattr(attacker, 'level', 1)
                
                # Get attacker's alliance
                attacker_alliance = db.query(AllianceMember).filter(
                    AllianceMember.kingdom_id == attacker_id
                ).first()
                
                alliance_ids = []
                if attacker_alliance:
                    alliance_members = db.query(AllianceMember).filter(
                        AllianceMember.alliance_id == attacker_alliance.alliance_id
                    ).all()
                    alliance_ids = [m.kingdom_id for m in alliance_members]
                
                # Build query
                query = db.query(Kingdom).filter(
                    Kingdom.user_id != attacker_id,
                    Kingdom.level.between(attacker_level - 2, attacker_level + 2)
                )
                
                # Exclude alliance members if any
                if alliance_ids:
                    query = query.filter(~Kingdom.user_id.in_(alliance_ids))
                
                candidates = query.all()
                
                # Filter and sort
                results = []
                for c in candidates:
                    # Check shield
                    shield_expires = getattr(c, 'shield_expires', None)
                    if shield_expires and datetime.utcnow() < shield_expires:
                        continue
                    
                    # Check power range
                    try:
                        power = EconomyService.calculate_kingdom_power(c)
                        attacker_power = EconomyService.calculate_kingdom_power(attacker)
                        
                        if attacker_power * 0.3 <= power <= attacker_power * 2.0:
                            attacker_x = getattr(attacker, 'map_x', 0)
                            attacker_y = getattr(attacker, 'map_y', 0)
                            c_x = getattr(c, 'map_x', 0)
                            c_y = getattr(c, 'map_y', 0)
                            distance = abs(attacker_x - c_x) + abs(attacker_y - c_y)
                            results.append((c, power, distance))
                    except Exception:
                        continue
                
                # Sort by distance
                results.sort(key=lambda x: x[2])
                return results[:limit]
        
        except Exception as e:
            logger.error(f"Error finding opponents: {e}")
            return []
    
    # ─── LEADERBOARD ───
    
    @staticmethod
    def get_leaderboard(limit: int = 50) -> List[tuple]:
        """Get top players by power"""
        try:
            from bot.services.economy import EconomyService
            
            with get_db() as db:
                kingdoms = db.query(Kingdom).all()
                ranked = []
                
                for k in kingdoms:
                    try:
                        power = EconomyService.calculate_kingdom_power(k)
                        ranked.append((k, power))
                    except Exception:
                        continue
                
                ranked.sort(key=lambda x: x[1], reverse=True)
                return ranked[:limit]
        
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    # ─── COOLDOWNS ───
    
    @staticmethod
    def get_cooldown(user_id: int, action: str) -> Optional[datetime]:
        """Get cooldown expiry for an action"""
        try:
            with get_db() as db:
                cd = db.query(Cooldown).filter(
                    Cooldown.user_id == user_id,
                    Cooldown.action == action
                ).order_by(Cooldown.expires_at.desc()).first()
                
                if cd and cd.expires_at > datetime.utcnow():
                    return cd.expires_at
                return None
        except Exception as e:
            logger.error(f"Error getting cooldown: {e}")
            return None
    
    @staticmethod
    def set_cooldown(user_id: int, action: str, duration_minutes: int):
        """Set a cooldown"""
        try:
            with get_db() as db:
                cd = Cooldown(
                    user_id=user_id,
                    action=action,
                    expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes),
                )
                db.add(cd)
                db.commit()
        except Exception as e:
            logger.error(f"Error setting cooldown: {e}")
    
    # ─── QUESTS ───
    
    @staticmethod
    def get_user_quests(kingdom_id: int) -> List[UserQuest]:
        """Get all user quests"""
        try:
            with get_db() as db:
                return db.query(UserQuest).filter(UserQuest.kingdom_id == kingdom_id).all()
        except Exception as e:
            logger.error(f"Error getting user quests: {e}")
            return []
    
    @staticmethod
    def get_active_bounties(limit: int = 20) -> List[Bounty]:
        """Get active bounties"""
        try:
            with get_db() as db:
                return db.query(Bounty).filter(
                    Bounty.active == True,
                    Bounty.claimed_by == None
                ).order_by(Bounty.reward_gold.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting bounties: {e}")
            return []
    
    # ─── NOTIFICATIONS ───
    
    @staticmethod
    def get_notification_prefs(user_id: int) -> Optional[NotificationPref]:
        """Get notification preferences"""
        try:
            with get_db() as db:
                prefs = db.query(NotificationPref).filter(NotificationPref.user_id == user_id).first()
                if not prefs:
                    prefs = NotificationPref(user_id=user_id)
                    db.add(prefs)
                    db.commit()
                    db.refresh(prefs)
                return prefs
        except Exception as e:
            logger.error(f"Error getting notification prefs: {e}")
            return None
    
    # ─── WORLD EVENTS ───
    
    @staticmethod
    def get_active_world_events() -> List[WorldEvent]:
        """Get currently active world events"""
        try:
            with get_db() as db:
                return db.query(WorldEvent).filter(
                    WorldEvent.is_active == True,
                    WorldEvent.ends_at > datetime.utcnow()
                ).all()
        except Exception as e:
            logger.error(f"Error getting world events: {e}")
            return []
    
    # ─── ACHIEVEMENTS ───
    
    @staticmethod
    def get_user_achievements(user_id: int) -> List[UserAchievement]:
        """Get user achievements"""
        try:
            with get_db() as db:
                return db.query(UserAchievement).filter(UserAchievement.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            return []
    
    # ─── STATISTICS ───
    
    @staticmethod
    def get_kingdom_stats(user_id: int) -> Dict[str, Any]:
        """Get comprehensive kingdom statistics"""
        try:
            from bot.services.economy import EconomyService
            
            kingdom = GameData.get_kingdom_with_relations(user_id)
            if not kingdom:
                return {}
            
            total_power = EconomyService.calculate_kingdom_power(kingdom)
            defense = EconomyService.calculate_defense_rating(kingdom)
            
            army = getattr(kingdom, 'army', None)
            infantry = getattr(army, 'infantry', 0) if army else 0
            archers = getattr(army, 'archers', 0) if army else 0
            cavalry = getattr(army, 'cavalry', 0) if army else 0
            
            buildings = getattr(kingdom, 'buildings', [])
            total_building_levels = sum(getattr(b, 'level', 1) for b in buildings)
            
            return {
                'kingdom_name': getattr(kingdom, 'name', 'Unknown'),
                'flag': getattr(kingdom, 'flag', ''),
                'level': getattr(kingdom, 'level', 1),
                'xp': getattr(kingdom, 'xp', 0),
                'total_power': total_power,
                'defense_rating': defense,
                'gold': getattr(kingdom, 'gold', 0),
                'food': getattr(kingdom, 'food', 0),
                'gems': getattr(kingdom, 'gems', 0),
                'infantry': infantry,
                'archers': archers,
                'cavalry': cavalry,
                'total_army': infantry + archers + cavalry,
                'battles_won': getattr(kingdom, 'battles_won', 0),
                'battles_lost': getattr(kingdom, 'battles_lost', 0),
                'total_gold_earned': getattr(kingdom, 'total_gold_earned', 0),
                'total_gold_looted': getattr(kingdom, 'total_gold_looted', 0),
                'buildings_upgraded': getattr(kingdom, 'buildings_upgraded', 0),
                'soldiers_trained': getattr(kingdom, 'soldiers_trained', 0),
                'spy_missions': getattr(kingdom, 'spy_missions', 0),
                'successful_spies': getattr(kingdom, 'successful_spies', 0),
                'total_building_levels': total_building_levels,
                'building_count': len(buildings),
                'map_x': getattr(kingdom, 'map_x', 0),
                'map_y': getattr(kingdom, 'map_y', 0),
                'trait': getattr(kingdom, 'trait', 'balanced'),
            }
        except Exception as e:
            logger.error(f"Error getting kingdom stats: {e}")
            return {}
