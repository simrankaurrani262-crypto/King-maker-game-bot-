from datetime import datetime, timedelta


def format_number(n):
    """Format large numbers with commas"""
    return f"{n:,}"


def format_time_remaining(expires_at):
    """Format time remaining until expiry"""
    if not expires_at:
        return "No active timer"
    
    now = datetime.utcnow()
    if now >= expires_at:
        return "Ready ✅"
    
    remaining = expires_at - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_duration(minutes):
    """Format duration in minutes to readable string"""
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"
    return f"{minutes}m"


def format_building_status(building):
    """Format building display for building menu"""
    if building.is_upgrading:
        return f"Lv.{building.level} ⬆️ {format_time_remaining(building.upgrade_completes)}"
    return f"Lv.{building.level}"


def get_defense_rating_label(power):
    """Get defense rating label based on power"""
    if power < 100:
        return "Weak 🟡"
    elif power < 300:
        return "Moderate 🟠"
    elif power < 600:
        return "Strong 🔴"
    else:
        return "Unbreakable ⚫"


def calculate_xp_needed(level):
    """Calculate XP needed for next level"""
    return int(100 * (1.5 ** (level - 1)))


def get_level_from_xp(xp):
    """Calculate level from total XP"""
    level = 1
    total_xp = 0
    while True:
        needed = calculate_xp_needed(level)
        if total_xp + needed > xp:
            break
        total_xp += needed
        level += 1
    return level, xp - total_xp, calculate_xp_needed(level)
