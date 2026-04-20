import random
import json
from datetime import datetime, timedelta
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


class GameData:
    """Central game data access layer"""
    
    # ─── USER OPERATIONS ───
    
    @staticmethod
    def get_or_create_user(telegram_id, username=None, first_name=None, last_name=None, language_code="en"):
        """Get existing user or create new one"""
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
                prefs = NotificationPref(user_id=telegram_id)
                db.add(prefs)
                db.commit()
            else:
                # Update last active
                user.last_active = datetime.utcnow()
                if username:
                    user.username = username
                db.commit()
            db.expunge(user)
            return user
    
    @staticmethod
    def get_user(telegram_id):
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                db.expunge(user)
            return user
    
    # ─── KINGDOM OPERATIONS ───
    
    @staticmethod
    def create_kingdom(user_id, name, flag, trait="balanced"):
        """Create a new kingdom with all defaults"""
        with get_db() as db:
            # Find empty map position
            existing_positions = [(k.map_x, k.map_y) for k in db.query(Kingdom).all()]
            
            max_attempts = 100
            for _ in range(max_attempts):
                x = random.randint(1, MAP_SIZE)
                y = random.randint(1, MAP_SIZE)
                if (x, y) not in existing_positions:
                    break
            else:
                x, y = random.randint(1, MAP_SIZE), random.randint(1, MAP_SIZE)
            
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
            
            # Create army
            army = Army(kingdom_id=user_id, infantry=STARTER_ARMY)
            db.add(army)
            
            # Create default hero (Sir Aldric locked)
            heroes = [
                Hero(kingdom_id=user_id, hero_type="sir_aldric", level=1, unlocked=True),
                Hero(kingdom_id=user_id, hero_type="lyra", level=0, unlocked=False),
                Hero(kingdom_id=user_id, hero_type="kael", level=0, unlocked=False),
                Hero(kingdom_id=user_id, hero_type="morgana", level=0, unlocked=False),
                Hero(kingdom_id=user_id, hero_type="shadow", level=0, unlocked=False),
            ]
            for h in heroes:
                db.add(h)
            
            # Create default quests
            GameData._create_default_quests(db, user_id)
            
            # Create default achievements
            GameData._create_default_achievements(db, user_id)
            
            db.commit()
            db.refresh(kingdom)
            db.expunge(kingdom)
            return kingdom
    
    @staticmethod
    def _create_default_quests(db, kingdom_id):
        """Create default quests for a new kingdom"""
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
            
            # Create user quest entry
            user_quest = UserQuest(kingdom_id=kingdom_id, quest_id=quest.id)
            if qd["quest_type"] == "daily":
                user_quest.reset_at = datetime.utcnow() + timedelta(days=1)
            db.add(user_quest)
        
        db.commit()
    
    @staticmethod
    def _create_default_achievements(db, user_id):
        """Create default achievements"""
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
    
    @staticmethod
    def get_kingdom(user_id, db_session=None):
        """Get kingdom by user ID"""
        if db_session:
            return db_session.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                db.expunge(kingdom)
            return kingdom
    
    @staticmethod
    def get_kingdom_with_relations(user_id):
        """Get kingdom with all related objects loaded"""
        with get_db() as db:
            kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
            if kingdom:
                # Force load relationships within session
                _ = kingdom.buildings
                _ = kingdom.army
                _ = kingdom.heroes
                db.expunge(kingdom)
            return kingdom
    
    @staticmethod
    def get_all_kingdoms():
        """Get all kingdoms"""
        with get_db() as db:
            kingdoms = db.query(Kingdom).all()
            for k in kingdoms:
                db.expunge(k)
            return kingdoms
    
    @staticmethod
    def get_buildings(user_id):
        """Get all buildings for a kingdom"""
        with get_db() as db:
            buildings = db.query(Building).filter(Building.kingdom_id == user_id).all()
            for b in buildings:
                db.expunge(b)
            return buildings
    
    @staticmethod
    def get_building(user_id, building_type):
        """Get specific building"""
        with get_db() as db:
            building = db.query(Building).filter(
                Building.kingdom_id == user_id,
                Building.building_type == building_type
            ).first()
            if building:
                db.expunge(building)
            return building
    
    @staticmethod
    def get_army(user_id):
        """Get army for a kingdom"""
        with get_db() as db:
            army = db.query(Army).filter(Army.kingdom_id == user_id).first()
            if army:
                db.expunge(army)
            return army
    
    @staticmethod
    def get_heroes(user_id):
        """Get all heroes for a kingdom"""
        with get_db() as db:
            heroes = db.query(Hero).filter(Hero.kingdom_id == user_id).all()
            for h in heroes:
                db.expunge(h)
            return heroes
    
    @staticmethod
    def get_hero(user_id, hero_type):
        """Get specific hero"""
        with get_db() as db:
            hero = db.query(Hero).filter(
                Hero.kingdom_id == user_id,
                Hero.hero_type == hero_type
            ).first()
            if hero:
                db.expunge(hero)
            return hero
    
    @staticmethod
    def find_opponents(attacker_id, limit=3):
        """Find suitable attack opponents"""
        with get_db() as db:
            attacker = db.query(Kingdom).filter(Kingdom.user_id == attacker_id).first()
            if not attacker:
                return []
            db.expunge(attacker)
            
            # Get attacker's alliance
            attacker_alliance = db.query(AllianceMember).filter(
                AllianceMember.kingdom_id == attacker_id
            ).first()
            alliance_ids = []
            if attacker_alliance:
                alliance_ids = [m.kingdom_id for m in db.query(AllianceMember).filter(
                    AllianceMember.alliance_id == attacker_alliance.alliance_id
                ).all()]
            
            candidates = db.query(Kingdom).filter(
                Kingdom.user_id != attacker_id,
                Kingdom.level.between(attacker.level - 2, attacker.level + 2),
                ~Kingdom.user_id.in_(alliance_ids) if alliance_ids else True,
            ).all()
            
            # Filter out shielded players and sort by proximity
            from bot.services.economy import EconomyService
            results = []
            for c in candidates:
                db.expunge(c)
                if c.has_shield:
                    continue
                power = EconomyService.calculate_kingdom_power(c)
                attacker_power = EconomyService.calculate_kingdom_power(attacker)
                if attacker_power * 0.5 <= power <= attacker_power * 1.5:
                    distance = abs(attacker.map_x - c.map_x) + abs(attacker.map_y - c.map_y)
                    results.append((c, power, distance))
            
            results.sort(key=lambda x: x[2])  # Sort by distance
            return results[:limit]
    
    @staticmethod
    def get_leaderboard(limit=50):
        """Get top players by power"""
        with get_db() as db:
            from bot.services.economy import EconomyService
            kingdoms = db.query(Kingdom).all()
            ranked = []
            for k in kingdoms:
                db.expunge(k)
                power = EconomyService.calculate_kingdom_power(k)
                ranked.append((k, power))
            ranked.sort(key=lambda x: x[1], reverse=True)
            return ranked[:limit]
    
    @staticmethod
    def get_cooldown(user_id, action):
        """Get cooldown expiry for an action"""
        with get_db() as db:
            cd = db.query(Cooldown).filter(
                Cooldown.user_id == user_id,
                Cooldown.action == action
            ).order_by(Cooldown.expires_at.desc()).first()
            
            if cd and cd.expires_at > datetime.utcnow():
                db.expunge(cd)
                return cd.expires_at
            return None
    
    @staticmethod
    def set_cooldown(user_id, action, duration_minutes):
        """Set a cooldown"""
        with get_db() as db:
            cd = Cooldown(
                user_id=user_id,
                action=action,
                expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes),
            )
            db.add(cd)
            db.commit()
    
    @staticmethod
    def get_user_quests(kingdom_id):
        """Get all user quests"""
        with get_db() as db:
            quests = db.query(UserQuest).filter(UserQuest.kingdom_id == kingdom_id).all()
            for q in quests:
                db.expunge(q)
            return quests
    
    @staticmethod
    def get_active_bounties(limit=20):
        """Get active bounties"""
        with get_db() as db:
            bounties = db.query(Bounty).filter(
                Bounty.active == True,
                Bounty.claimed_by == None
            ).order_by(Bounty.reward_gold.desc()).limit(limit).all()
            for b in bounties:
                db.expunge(b)
            return bounties
    
    @staticmethod
    def get_notification_prefs(user_id):
        """Get notification preferences"""
        with get_db() as db:
            prefs = db.query(NotificationPref).filter(NotificationPref.user_id == user_id).first()
            if not prefs:
                prefs = NotificationPref(user_id=user_id)
                db.add(prefs)
                db.commit()
                db.refresh(prefs)
            db.expunge(prefs)
            return prefs
    
    @staticmethod
    def get_active_world_events():
        """Get currently active world events"""
        with get_db() as db:
            events = db.query(WorldEvent).filter(
                WorldEvent.is_active == 1,
                WorldEvent.ends_at > datetime.utcnow()
            ).all()
            for e in events:
                db.expunge(e)
            return events
