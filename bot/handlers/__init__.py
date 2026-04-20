"""
Handlers Package - All Telegram bot command and callback handlers
Version: 2.0.0 - Advanced Edition with all features
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
    stats,           # Statistics & Charts
    training,        # NEW: Training center
    trade,           # NEW: Trade system
    bounty,          # NEW: Bounty system
    achievements,    # NEW: Achievement system
    world_events,    # NEW: World events
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
    'stats',
    'training',
    'trade',
    'bounty',
    'achievements',
    'world_events',
]
