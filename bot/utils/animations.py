"""
Animations & Visual Effects Utility
Text-based animations, loading sequences, battle effects,
and visual enhancements for immersive gameplay.
"""

import random
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ─── ASCII Art Assets ───

class ASCIIArt:
    """Collection of ASCII art for different game elements"""
    
    CROWN = """
        👑
       ╱╲
      ╱👑╲
     ╱ ╱╲ ╲
    ╱ ╱  ╲ ╲
    ─────────
    """
    
    CASTLE = """
       🏰
      /||\\
     / || \\
    |  ||  |
    |__||__|
    |  ||  |
    |__||__|
    """
    
    SWORD = """
      ⚔️
      |\
      | \
      |  \
      |   \
      |    \
    ──┘     \
    """
    
    SHIELD = """
     🛡
    /\\
   /  \\
  | ⚔ |
  |___|
    """
    
    VICTORY = """
    🎉 VICTORY! 🎉
    
    ⭐  ⭐  ⭐
    
    🏆  👑  🏆
    
    ⭐  ⭐  ⭐
    """
    
    DEFEAT = """
    💀 DEFEAT 💀
    
    ⚫  ⚫  ⚫
    
    ☠️  💀  ☠️
    
    ⚫  ⚫  ⚫
    """
    
    TREASURE = """
      💎
     /  \\
    💰💰💰
   💰💰💰💰💰
  💰💰💰💰💰💰💰
    ─────────
    """
    
    BATTLE_BANNER = """
╔══════════════════════════════════════╗
║           ⚔️  BATTLE  ⚔️             ║
╚══════════════════════════════════════╝
    """
    
    LEVEL_UP = """
    ⬆️⬆️⬆️⬆️⬆️
    
    🎊 LEVEL UP! 🎊
    
    ⭐⭐⭐⭐⭐
    
    ⬆️⬆️⬆️⬆️⬆️
    """


# ─── Loading Animations ───

class LoadingAnimation:
    """Animated loading sequences"""
    
    FRAMES = ["⏳", "⌛", "⏳", "⌛"]
    SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]
    DOTS_FRAMES = [".", "..", "...", "...."]
    SWORD_FRAMES = ["🗡", "⚔️", "🗡", "⚔️"]
    
    @classmethod
    def get_loading_text(cls, message: str = "Loading", style: str = "dots") -> str:
        """Get a loading text with animation frame"""
        frames_map = {
            "dots": cls.DOTS_FRAMES,
            "spinner": cls.SPINNER_FRAMES,
            "sword": cls.SWORD_FRAMES,
            "default": cls.FRAMES,
        }
        frames = frames_map.get(style, cls.FRAMES)
        frame = random.choice(frames)
        return f"{frame} {message}..."
    
    @classmethod
    def battle_preparation(cls) -> str:
        """Battle preparation sequence"""
        sequences = [
            "⚔️ Army mobilizing...",
            "🗡 Weapons sharpening...",
            "🛡 Shields raising...",
            "📡 Scouts reporting...",
            "🔥 War drums beating...",
        ]
        return random.choice(sequences)
    
    @classmethod
    def spy_mission(cls) -> str:
        """Spy mission sequence"""
        sequences = [
            "🕵️ Spy sneaking into enemy territory...",
            "📜 Gathering intelligence...",
            "🔍 Analyzing defenses...",
            "✉️ Sending report...",
        ]
        return random.choice(sequences)


# ─── Battle Animation Sequences ───

class BattleAnimator:
    """Generate animated battle sequences"""
    
    ATTACK_EMOTES = ["🔥", "💥", "⚔️", "🗡", "💀", "👊", "💢"]
    DEFENSE_EMOTES = ["🛡", "💪", "🧱", "✋", "🛡️", "🔄"]
    CRITICAL_EMOTES = ["💥💥💥", "🔥🔥🔥", "⚡⚡⚡", "💀💀💀"]
    
    @classmethod
    def generate_attack_sequence(cls, attacker_name: str, defender_name: str) -> List[str]:
        """Generate attack sequence frames"""
        return [
            f"⚔️ **{attacker_name}** attacks **{defender_name}!**",
            f"🗡 {random.choice(cls.ATTACK_EMOTES)} Infantry charging!",
            f"🏹 {random.choice(cls.ATTACK_EMOTES)} Archers firing!",
            f"🐎 {random.choice(cls.ATTACK_EMOTES)} Cavalry rushing!",
        ]
    
    @classmethod
    def generate_defense_sequence(cls, defender_name: str) -> List[str]:
        """Generate defense sequence frames"""
        return [
            f"🛡 **{defender_name}** defends!",
            f"🏰 {random.choice(cls.DEFENSE_EMOTES)} Walls holding!",
            f"⚔️ {random.choice(cls.DEFENSE_EMOTES)} Counter-attack!",
        ]
    
    @classmethod
    def generate_critical_hit(cls) -> str:
        """Generate critical hit message"""
        emote = random.choice(cls.CRITICAL_EMOTES)
        messages = [
            f"{emote} **CRITICAL HIT!** {emote}",
            f"{emote} **DEVASTATING STRIKE!** {emote}",
            f"{emote} **MASSIVE DAMAGE!** {emote}",
        ]
        return random.choice(messages)
    
    @classmethod
    def generate_battle_round(cls, round_num: int, attacker_action: str, 
                             damage: int, is_critical: bool = False) -> str:
        """Generate a battle round description"""
        if is_critical:
            return (
                f"🔥 **Round {round_num}** 🔥\n"
                f"{cls.generate_critical_hit()}\n"
                f"💥 {damage} damage dealt!"
            )
        
        emote = random.choice(cls.ATTACK_EMOTES)
        return (
            f"⚔️ **Round {round_num}** ⚔️\n"
            f"{emote} {attacker_action}\n"
            f"💥 {damage} damage!"
        )
    
    @classmethod
    def generate_victory_animation(cls) -> str:
        """Generate victory celebration animation"""
        victory_frames = [
            "🏆 **VICTORY!** 🏆",
            "⭐ The enemy retreats! ⭐",
            "💰 Looting enemy base...",
            "🎉 Celebrating with troops!",
        ]
        return "\n\n".join(victory_frames)
    
    @classmethod
    def generate_defeat_animation(cls) -> str:
        """Generate defeat animation"""
        defeat_frames = [
            "💀 **DEFEAT!** 💀",
            "⚫ Forces overwhelmed...",
            "🏃 Retreating to base...",
            "🛡 Rebuilding defenses...",
        ]
        return "\n\n".join(defeat_frames)


# ─── Kingdom Creation Animator ───

class KingdomCreationAnimator:
    """Animated kingdom creation sequence"""
    
    @classmethod
    def generate_creation_sequence(cls, kingdom_name: str, flag: str, trait: str) -> List[str]:
        """Generate kingdom creation animation frames"""
        return [
            f"🏰 **Founding {kingdom_name}** {flag}...",
            "📜 Writing royal decree...",
            "🗺 Surveying the lands...",
            "🏗 Constructing buildings...",
            "🗡 Training the militia...",
            f"⚡ Blessing with **{trait.title()}** trait...",
            "🎊 **Kingdom Established!**",
        ]
    
    @classmethod
    def generate_building_frame(cls, building_name: str, level: int) -> str:
        """Generate building upgrade frame"""
        emotes = {"town_hall": "🏰", "gold_mine": "⛏", "farm": "🌾", 
                 "barracks": "🏹", "wall": "🛡"}
        emote = emotes.get(building_name, "🏗")
        
        progress = "█" * level + "░" * (25 - level)
        return (
            f"{emote} **{building_name.replace('_', ' ').title()}**\n"
            f"Level: {level}/25\n"
            f"`{progress}`"
        )


# ─── Progress Bar Generator ───

class ProgressBar:
    """Generate visual progress bars"""
    
    @staticmethod
    def create(percent: int, length: int = 20, filled_char: str = "█", 
               empty_char: str = "░") -> str:
        """Create a text-based progress bar"""
        if percent < 0:
            percent = 0
        if percent > 100:
            percent = 100
        
        filled = int(length * percent / 100)
        empty = length - filled
        
        bar = filled_char * filled + empty_char * empty
        return f"`{bar}` {percent}%"
    
    @staticmethod
    def create_colored(percent: int, length: int = 20) -> str:
        """Create a colored progress bar"""
        if percent < 30:
            color = "🔴"
        elif percent < 60:
            color = "🟡"
        elif percent < 90:
            color = "🟢"
        else:
            color = "🔵"
        
        filled = int(length * percent / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"{color} `{bar}` {percent}%"
    
    @staticmethod
    def health_bar(current: int, maximum: int, length: int = 15) -> str:
        """Create a health bar"""
        if maximum <= 0:
            return "`███████████████` 0%"
        
        percent = int((current / maximum) * 100)
        filled = int(length * current / maximum)
        
        if percent > 60:
            color_emoji = "🟢"
        elif percent > 30:
            color_emoji = "🟡"
        else:
            color_emoji = "🔴"
        
        bar = "█" * filled + "░" * (length - filled)
        return f"{color_emoji} HP: `{bar}` {current}/{maximum}"


# ─── Dashboard Animator ───

class DashboardAnimator:
    """Dashboard visual enhancements"""
    
    @staticmethod
    def generate_welcome_back(kingdom_name: str, offline_hours: int) -> str:
        """Generate welcome back message"""
        if offline_hours < 1:
            return f"👑 Welcome back, **{kingdom_name}**!"
        elif offline_hours < 24:
            return (
                f"👑 Welcome back, **{kingdom_name}**!\n"
                f"⏰ Aap {offline_hours} hours se offline the.\n"
                f"📥 Resources collect kar lo!"
            )
        else:
            days = offline_hours // 24
            return (
                f"👑 Welcome back, **{kingdom_name}**!\n"
                f"⏰ Aap {days} din se offline the!\n"
                f"🛡 Shield automatically extended!"
            )
    
    @staticmethod
    def get_status_indicator(value: int, maximum: int) -> str:
        """Get status indicator emoji"""
        ratio = value / maximum if maximum > 0 else 0
        if ratio >= 0.9:
            return "✅"
        elif ratio >= 0.5:
            return "🟢"
        elif ratio >= 0.25:
            return "🟡"
        else:
            return "🔴"
    
    @staticmethod
    def format_resource_with_trend(current: int, previous: int) -> str:
        """Format resource with trend indicator"""
        if previous == 0:
            trend = "➡️"
        elif current > previous:
            diff = current - previous
            trend = f"📈 +{diff:,}"
        elif current < previous:
            diff = previous - current
            trend = f"📉 -{diff:,}"
        else:
            trend = "➡️ 0"
        
        return f"{current:,} ({trend})"


# ─── Effect Generators ───

class VisualEffects:
    """Generate visual effects for various game events"""
    
    @staticmethod
    def level_up_celebration(level: int) -> str:
        """Generate level up celebration text"""
        stars = "⭐" * min(level, 10)
        return (
            f"🎊 **LEVEL UP!** 🎊\n"
            f"━━━━━━━━━━━━━━\n"
            f"⬆️ Level **{level}** reached!\n"
            f"{stars}\n"
            f"New features unlocked!"
        )
    
    @staticmethod
    def resource_collection(resources: Dict[str, int]) -> str:
        """Generate resource collection visual"""
        lines = ["📥 **Resources Collected!**", "━━━━━━━━━━━━━━"]
        
        if resources.get('gold'):
            lines.append(f"💰 +{resources['gold']:,} Gold")
        if resources.get('food'):
            lines.append(f"🍖 +{resources['food']:,} Food")
        if resources.get('gems'):
            lines.append(f"💎 +{resources['gems']:,} Gems")
        if resources.get('xp'):
            lines.append(f"⭐ +{resources['xp']} XP")
        
        return "\n".join(lines)
    
    @staticmethod
    def building_upgrade_complete(building_name: str, new_level: int) -> str:
        """Generate building upgrade completion visual"""
        emotes = {"town_hall": "🏰", "gold_mine": "⛏", "farm": "🌾",
                 "barracks": "🏹", "wall": "🛡"}
        emote = emotes.get(building_name, "🏗")
        
        return (
            f"✅ **Upgrade Complete!**\n"
            f"━━━━━━━━━━━━━━\n"
            f"{emote} {building_name.replace('_', ' ').title()}\n"
            f"⬆️ Level {new_level} reached!\n"
            f"📈 Production increased!"
        )
    
    @staticmethod
    def quest_complete(quest_name: str, rewards: Dict[str, Any]) -> str:
        """Generate quest completion visual"""
        lines = [
            f"🎯 **Quest Complete!**",
            f"━━━━━━━━━━━━━━",
            f"✅ {quest_name}",
            f"",
            f"🎁 **Rewards:**",
        ]
        
        if rewards.get('gold'):
            lines.append(f"💰 +{rewards['gold']:,} Gold")
        if rewards.get('food'):
            lines.append(f"🍖 +{rewards['food']:,} Food")
        if rewards.get('gems'):
            lines.append(f"💎 +{rewards['gems']:,} Gems")
        if rewards.get('xp'):
            lines.append(f"⭐ +{rewards['xp']} XP")
        if rewards.get('title'):
            lines.append(f"🏷 New Title: {rewards['title']}")
        
        return "\n".join(lines)
    
    @staticmethod
    def spy_report_visual(report_data: Dict[str, Any]) -> str:
        """Generate spy report visual"""
        if report_data.get('trapped'):
            return (
                f"🕵️ **Spy Mission Failed!**\n"
                f"━━━━━━━━━━━━━━\n"
                f"💀 Spy pakda gaya!\n"
                f"🛡 Enemy traps were active!"
            )
        
        return (
            f"📜 **Spy Report**\n"
            f"━━━━━━━━━━━━━━\n"
            f"🎯 Target: {report_data.get('target_name', 'Unknown')}\n"
            f"📊 Kingdom Level: {report_data.get('level', '?')}\n"
            f"💰 Gold: {report_data.get('gold', '?'):,}\n"
            f"🍖 Food: {report_data.get('food', '?'):,}\n"
            f"⚔️ Army: {report_data.get('army_total', '?')}\n"
            f"🛡 Wall Level: {report_data.get('wall_level', '?')}\n"
            f"🛡 Shield: {report_data.get('shield_status', '?')}\n"
            f"━━━━━━━━━━━━━━"
        )
    
    @staticmethod
    def alliance_event_visual(event_type: str, data: Dict[str, Any]) -> str:
        """Generate alliance event visual"""
        events = {
            "member_joined": (
                f"🤝 **New Member!**\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 {data.get('username', 'Unknown')} joined!\n"
                f"💪 Alliance growing stronger!"
            ),
            "donation": (
                f"💰 **Donation Received!**\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 {data.get('username', 'Unknown')}\n"
                f"💰 +{data.get('amount', 0):,} Gold donated!"
            ),
            "war_declared": (
                f"⚔️ **WAR DECLARED!**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🎯 Enemy: {data.get('enemy_name', 'Unknown')}\n"
                f"📅 Starts in: {data.get('time_remaining', 'Soon')}\n"
                f"💪 Prepare your armies!"
            ),
        }
        return events.get(event_type, "🤝 Alliance Event")


# ─── World Event Visuals ───

class WorldEventVisuals:
    """Visual representations of world events"""
    
    @staticmethod
    def treasure_event() -> str:
        return (
            "💎 **WORLD EVENT: HIDDEN TREASURE!**\n"
            "━━━━━━━━━━━━━━\n"
            "🗺 A mysterious treasure has been discovered!\n"
            "💰 All kingdoms receive +500 Gold!\n"
            "🎉 Happy hunting!"
        )
    
    @staticmethod
    def plague_event() -> str:
        return (
            "😷 **WORLD EVENT: PLAGUE!**\n"
            "━━━━━━━━━━━━━━\n"
            "🦠 Disease spreads across the lands!\n"
            "🍖 Food production reduced by 50%!\n"
            "⏰ Duration: 6 hours\n"
            "🛡 Protect your people!"
        )
    
    @staticmethod
    def festival_event() -> str:
        return (
            "🎉 **WORLD EVENT: MAHOTSAV!**\n"
            "━━━━━━━━━━━━━━\n"
            "🎊 Festival season begins!\n"
            "⚡ Training speed doubled!\n"
            "⏰ Duration: 12 hours\n"
            "💪 Train your armies now!"
        )
    
    @staticmethod
    def dragon_invasion_event() -> str:
        return (
            "🐉 **WORLD EVENT: DRAGON INVASION!**\n"
            "━━━━━━━━━━━━━━\n"
            "🔥 Ancient dragon awakens!\n"
            "⚔️ Survival mode activated!\n"
            "🏆 Defeat dragon for legendary rewards!\n"
            "💪 Alliances, unite!"
        )


# ─── Helper for async animations ───

async def send_animated_message(update, context, frames: List[str], 
                                delay: float = 0.8, reply_markup=None):
    """Send an animated message that cycles through frames"""
    try:
        message = await update.effective_message.reply_text(
            frames[0], reply_markup=reply_markup
        )
        
        for frame in frames[1:]:
            await asyncio.sleep(delay)
            try:
                await message.edit_text(frame, reply_markup=reply_markup)
            except Exception:
                break
        
        return message
    except Exception as e:
        logger.error(f"Animation error: {e}")
        return None
