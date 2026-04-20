"""
Handlers Package - All Telegram bot command and callback handlers
Version: 2.0.0
"""

from . import (
    start,           # Kingdom creation & tutorial
    dashboard,       # Main HUD
    attack,          # Battle system
    build,           # Building management
    map_system,      # World map
    alliance,        # Alliance system
    quests,          # Quest board
    heroes,          # Hero management
    spy,             # Spy missions
    games,           # Mini-games
    leaderboard,     # Rankings
    settings,        # Preferences
    admin,           # Admin commands
    stats,           # NEW: Statistics & Charts (v2.0)
)

__all__ = [
    'start',
    'dashboard',
    'attack',
    'build',
    'map_system',
    'alliance',
    'quests',
    'heroes',
    'spy',
    'games',
    'leaderboard',
    'settings',
    'admin',
    'stats',  # NEW
]
