"""
Animations Module - Realistic battle animations, progress bars, and visual effects
Complete version with ASCII art battle scenes and animated sequences.
"""

import random


class BattleAnimator:
    """Create realistic battle animations and visual effects"""

    BATTLE_FRAMES = [
        [
            "    ⚔️ BATTLE BEGINS! ⚔️    ",
            "                           ",
            "   🗡️    🏹    🐎         ",
            "      💥💥💥💥💥          ",
            "         💥💥💥           ",
            "      💥💥💥💥💥          ",
        ],
        [
            "    ⚔️ CLASH OF ARMIES! ⚔️ ",
            "                           ",
            "  🗡️🗡️   🏹🏹   🐎🐎      ",
            "      💥🔥💥🔥💥          ",
            "       ⚡💥⚡💥⚡          ",
            "      🔥💥🔥💥🔥          ",
        ],
        [
            "    ⚔️ FIERCE COMBAT! ⚔️   ",
            "                           ",
            " 🗡️⚡🗡️ 🏹🔥🏹 🐎💥🐎     ",
            "      🔥💥⚡💥🔥          ",
            "       💥⚡🔥⚡💥          ",
            "      ⚡🔥💥🔥⚡          ",
        ],
        [
            "    ⚔️ BATTLE RAGES! ⚔️    ",
            "                           ",
            "  🗡️💀🗡️ 🏹💀🏹 🐎💀🐎    ",
            "      💀💥💀💥💀          ",
            "       🔥💀🔥💀🔥         ",
            "      ⚡💥💀💥⚡          ",
        ],
    ]

    VICTORY_FRAMES = [
        "🎉🏆🎉 VICTORY! 🎉🏆🎉",
        "                      ",
        "  👑 The kingdom is yours! 👑  ",
        "                      ",
        "  💰💰💰 LOOT SECURED 💰💰💰  ",
    ]

    DEFEAT_FRAMES = [
        "💀💔💀 DEFEAT! 💀💔💀",
        "                      ",
        "  😔 Your forces have fallen...  ",
        "                      ",
        "  ⚔️ Train more and try again! ⚔️  ",
    ]

    def create_battle_animation(self, attacker, defender, winner, rounds=None):
        """Create a complete battle animation sequence"""
        atk_name = getattr(attacker, 'name', 'Unknown')[:12]
        def_name = getattr(defender, 'name', 'Unknown')[:12]
        atk_flag = getattr(attacker, 'flag', '⚔️')
        def_flag = getattr(defender, 'flag', '🛡️')

        lines = []
        lines.append("=" * 42)
        lines.append(f"  {atk_flag} {atk_name:^12} VS {def_name:^12} {def_flag}")
        lines.append("=" * 42)
        lines.append("")

        # Battle scene
        for frame in self.BATTLE_FRAMES[:min(len(self.BATTLE_FRAMES), 3)]:
            for line in frame:
                lines.append(f"  {line}")
            lines.append("")

        # Result
        if winner == "attacker":
            for line in self.VICTORY_FRAMES:
                lines.append(f"  {line}")
        else:
            for line in self.DEFEAT_FRAMES:
                lines.append(f"  {line}")

        lines.append("")
        lines.append("=" * 42)

        return "\n".join(lines)

    def create_raid_animation(self, attacker, defender, success):
        """Create raid animation"""
        if success:
            return (
                "🏃‍♂️ RAID SUCCESS! 🏃‍♂️\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "  🌙 Under cover of darkness...\n"
                "  🏃 Sneaking past defenses...\n"
                "  💰 Grabbing resources...\n"
                "  🏃‍♂️ Escaping with loot!\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            return (
                "❌ RAID FAILED! ❌\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "  🏃‍♂️ Approaching target...\n"
                "  🛡️ Spotted by sentries!\n"
                "  ⚔️ Forced to retreat!\n"
                "  💀 Lost some soldiers...\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )

    def create_spy_animation(self, success, caught=False):
        """Create spy mission animation"""
        if caught:
            return (
                "🕵️ SPY MISSION...\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "  🕵️ Entering enemy territory...\n"
                "  ⚠️ Trap detected too late!\n"
                "  💀 SPY CAPTURED!\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
        elif success:
            return (
                "🕵️ SPY MISSION SUCCESS! 🕵️\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "  🕵️ Infiltrating enemy castle...\n"
                "  📜 Gathering intelligence...\n"
                "  📨 Report delivered!\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            return (
                "🕵️ SPY MISSION FAILED 🕵️\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "  🕵️ Approaching target...\n"
                "  🚪 Couldn't breach defenses...\n"
                "  🏃 Returning empty-handed...\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )


class ProgressBar:
    """Create text-based progress bars"""

    @staticmethod
    def create(percent: int, length: int = 15, fill_char: str = "█", empty_char: str = "░") -> str:
        """Create a simple progress bar"""
        filled = int(length * min(100, max(0, percent)) / 100)
        empty = length - filled
        return f"{fill_char * filled}{empty_char * empty}"

    @staticmethod
    def create_colored(percent: int, length: int = 15) -> str:
        """Create a colored progress bar using emoji"""
        filled = int(length * min(100, max(0, percent)) / 100)
        empty = length - filled

        if percent >= 70:
            fill = "🟩"
        elif percent >= 40:
            fill = "🟨"
        else:
            fill = "🟥"

        return f"{fill * filled}⬜{empty * length}"[:length*2] + f" {percent}%"

    @staticmethod
    def create_with_label(percent: int, label: str, length: int = 12) -> str:
        """Create a progress bar with label"""
        bar = ProgressBar.create(percent, length)
        return f"{label}: {bar} {percent}%"


class KingdomCreationAnimator:
    """Kingdom creation animation"""

    FRAMES = [
        "🏰 Generating land...      ",
        "🏰 Building castle...      ",
        "⛏ Digging gold mines...   ",
        "🌾 Planting farms...       ",
        "🏹 Setting up barracks...  ",
        "🛡 Constructing walls...   ",
        "🧙 Summoning advisors...   ",
        "✅ Kingdom ready!          ",
    ]

    @classmethod
    def get_frame(cls, step: int) -> str:
        """Get animation frame for step"""
        if 0 <= step < len(cls.FRAMES):
            return cls.FRAMES[step]
        return cls.FRAMES[-1]


class LoadingAnimation:
    """Loading spinner animation"""

    SPINNER = ["⏳", "⌛", "⏳", "⌛"]

    @classmethod
    def get_frame(cls, step: int) -> str:
        """Get spinner frame"""
        return cls.SPINNER[step % len(cls.SPINNER)]


class DashboardAnimator:
    """Dashboard visual effects"""

    @staticmethod
    def create_resource_bar(current: int, maximum: int, emoji: str = "⚡") -> str:
        """Create a resource bar"""
        if maximum <= 0:
            return f"{emoji} 0/0"

        percent = min(100, int((current / maximum) * 100))
        bar = ProgressBar.create(percent, 10)
        return f"{emoji} {bar} {current}/{maximum}"

    @staticmethod
    def create_shield_indicator(expires=None) -> str:
        """Create shield status indicator"""
        from datetime import datetime
        if expires and datetime.utcnow() < expires:
            remaining = expires - datetime.utcnow()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            if hours > 0:
                return f"🛡 Active ({hours}h {minutes}m)"
            return f"🛡 Active ({minutes}m)"
        return "🚫 No Shield"

    @staticmethod
    def create_army_display(infantry: int, archers: int, cavalry: int) -> str:
        """Create formatted army display"""
        total = infantry + archers + cavalry
        if total == 0:
            return "⚔️ No Army"

        inf_pct = int(infantry / total * 100) if total > 0 else 0
        arc_pct = int(archers / total * 100) if total > 0 else 0
        cav_pct = int(cavalry / total * 100) if total > 0 else 0

        return (
            f"⚔️ Total: {total:,}\n"
            f"  🗡 Infantry: {infantry:,} ({inf_pct}%)\n"
            f"  🏹 Archers:  {archers:,} ({arc_pct}%)\n"
            f"  🐎 Cavalry:  {cavalry:,} ({cav_pct}%)"
        )


def text_bar(ratio: float, emoji: str = "█", length: int = 15) -> str:
    """Simple text bar function"""
    percent = min(100, max(0, int(ratio * 100)))
    filled = int(length * percent / 100)
    empty = length - filled
    return f"{emoji * filled}{'░' * empty} {percent}%"
