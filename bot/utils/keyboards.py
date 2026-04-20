"""
Keyboards Module - All Telegram inline keyboards
Complete version with all menu keyboards.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ─── Main Menu Keyboards ───

def start_menu_keyboard() -> InlineKeyboardMarkup:
    """Start menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Start Game", callback_data="start_game")],
        [InlineKeyboardButton("📖 How to Play", callback_data="how_to_play")],
    ])


def trait_selection_keyboard() -> InlineKeyboardMarkup:
    """Kingdom trait selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Aggressive (+25% Attack)", callback_data="trait_aggressive")],
        [InlineKeyboardButton("🛡 Defensive (+30% Defense)", callback_data="trait_defensive")],
        [InlineKeyboardButton("💰 Rich (+50% Gold)", callback_data="trait_rich")],
        [InlineKeyboardButton("⚖️ Balanced (+8% All)", callback_data="trait_balanced")],
    ])


def dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main dashboard keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Attack", callback_data="menu_attack"),
         InlineKeyboardButton("🏗 Buildings", callback_data="menu_build")],
        [InlineKeyboardButton("🗺 Map", callback_data="menu_map"),
         InlineKeyboardButton("🤝 Alliance", callback_data="menu_alliance")],
        [InlineKeyboardButton("🧙 Heroes", callback_data="menu_heroes"),
         InlineKeyboardButton("🕵️ Spy", callback_data="menu_spy")],
        [InlineKeyboardButton("🎯 Quests", callback_data="menu_quests"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard")],
        [InlineKeyboardButton("🎮 Mini-Games", callback_data="menu_games"),
         InlineKeyboardButton("📊 Stats", callback_data="menu_stats")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
    ])


def back_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Back to dashboard keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Dashboard", callback_data="back_dashboard")],
    ])


# ─── Attack Menu Keyboards ───

def attack_menu_keyboard() -> InlineKeyboardMarkup:
    """Attack mode menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find Opponent", callback_data="attack_find")],
        [InlineKeyboardButton("🔥 Revenge", callback_data="attack_revenge")],
        [InlineKeyboardButton("🏃 Quick Raid", callback_data="attack_raid")],
        [InlineKeyboardButton("🗺 Map View", callback_data="attack_map")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def opponent_keyboard(target_id: int) -> InlineKeyboardMarkup:
    """Opponent action keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Attack!", callback_data=f"attack_player:{target_id}")],
        [InlineKeyboardButton("🕵️ Spy First", callback_data=f"spy_opponent:{target_id}")],
        [InlineKeyboardButton("⏭ Next Opponent", callback_data="attack_next")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_attack")],
    ])


def battle_response_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Battle response (accept/decline) keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept Battle", callback_data=f"battle_accept:{request_id}")],
        [InlineKeyboardButton("❌ Decline", callback_data=f"battle_decline:{request_id}")],
    ])


def raid_menu_keyboard() -> InlineKeyboardMarkup:
    """Raid menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find Target", callback_data="raid_find")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_attack")],
    ])


# ─── Building Menu Keyboards ───

def building_menu_keyboard(buildings) -> InlineKeyboardMarkup:
    """Building selection menu"""
    buttons = []
    for b in buildings:
        status = "⬆️" if getattr(b, 'is_upgrading', False) else f"Lv.{getattr(b, 'level', 1)}"
        buttons.append([InlineKeyboardButton(
            f"{getattr(b, 'emoji', '🏗')} {getattr(b, 'display_name', b.building_type)} — {status}",
            callback_data=f"building_select:{b.building_type}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")])
    return InlineKeyboardMarkup(buttons)


def building_action_keyboard(building_type: str, level: int, is_upgrading: bool) -> InlineKeyboardMarkup:
    """Building action keyboard"""
    if is_upgrading:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ Upgrading...", callback_data="noop")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_build")],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬆️ Upgrade", callback_data=f"building_upgrade:{building_type}")],
        [InlineKeyboardButton("📥 Collect", callback_data=f"building_collect:{building_type}")],
        [InlineKeyboardButton("ℹ️ Info", callback_data=f"building_info:{building_type}")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_build")],
    ])


# ─── Hero Menu Keyboards ───

def heroes_keyboard(heroes) -> InlineKeyboardMarkup:
    """Hero selection menu"""
    buttons = []
    for h in heroes:
        status = "✅" if getattr(h, 'unlocked', False) else "🔒"
        buttons.append([InlineKeyboardButton(
            f"{status} {getattr(h, 'display_name', h.hero_type)} — Lv.{getattr(h, 'level', 0)}",
            callback_data=f"hero_select:{h.hero_type}"
        )])

    # Skill tree buttons
    buttons.append([
        InlineKeyboardButton("⚔️ Attack Skills", callback_data="skill_attack"),
        InlineKeyboardButton("🛡 Defense Skills", callback_data="skill_defense"),
    ])
    buttons.append([
        InlineKeyboardButton("💰 Economy Skills", callback_data="skill_economy"),
    ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")])
    return InlineKeyboardMarkup(buttons)


def hero_action_keyboard(hero_type: str, unlocked: bool, level: int, can_upgrade: bool) -> InlineKeyboardMarkup:
    """Hero action keyboard"""
    buttons = []

    if not unlocked:
        buttons.append([InlineKeyboardButton("🔓 Unlock", callback_data=f"hero_unlock:{hero_type}")])
    elif can_upgrade:
        buttons.append([InlineKeyboardButton("⬆️ Level Up", callback_data=f"hero_upgrade:{hero_type}")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_heroes")])
    return InlineKeyboardMarkup(buttons)


# ─── Spy Menu Keyboards ───

def spy_menu_keyboard() -> InlineKeyboardMarkup:
    """Spy menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕵️ Send Spy", callback_data="spy_send")],
        [InlineKeyboardButton("📜 History", callback_data="spy_history")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── Quest Menu Keyboards ───

def quests_keyboard() -> InlineKeyboardMarkup:
    """Quest menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim Rewards", callback_data="quests_claim")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── Leaderboard Menu Keyboards ───

def leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Leaderboard menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Players", callback_data="lb_players"),
         InlineKeyboardButton("🏰 Alliances", callback_data="lb_alliances")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── Games Menu Keyboards ───

def games_menu_keyboard() -> InlineKeyboardMarkup:
    """Mini-games menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Dice Game", callback_data="game_dice")],
        [InlineKeyboardButton("🎰 Lucky Spin", callback_data="game_spin")],
        [InlineKeyboardButton("🧠 Kingdom Quiz", callback_data="game_quiz")],
        [InlineKeyboardButton("⚔️ Survival Mode", callback_data="game_survival")],
        [InlineKeyboardButton("🏪 Black Market", callback_data="game_market")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def dice_keyboard() -> InlineKeyboardMarkup:
    """Dice game keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Roll (100 Gold)", callback_data="dice_bet:100")],
        [InlineKeyboardButton("🎲 Roll (500 Gold)", callback_data="dice_bet:500")],
        [InlineKeyboardButton("🎲 Roll (1000 Gold)", callback_data="dice_bet:1000")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])


def spin_keyboard() -> InlineKeyboardMarkup:
    """Lucky spin keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 SPIN!", callback_data="spin_wheel")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])


def quiz_keyboard(q_idx: int, options: list) -> InlineKeyboardMarkup:
    """Quiz answer keyboard"""
    buttons = []
    for i, option in enumerate(options):
        buttons.append([InlineKeyboardButton(
            option, callback_data=f"quiz_answer:{q_idx}:{i}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_games")])
    return InlineKeyboardMarkup(buttons)


def black_market_keyboard() -> InlineKeyboardMarkup:
    """Black market keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Item", callback_data="market_buy")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])


def decision_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Decision event choice keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes", callback_data=f"decision:{event_id}:yes")],
        [InlineKeyboardButton("❌ No", callback_data=f"decision:{event_id}:no")],
    ])


# ─── Alliance Menu Keyboards ───

def alliance_hub_no_alliance_keyboard() -> InlineKeyboardMarkup:
    """Alliance hub when not in alliance"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏰 Create Alliance", callback_data="alliance_create")],
        [InlineKeyboardButton("🔍 Join Alliance", callback_data="alliance_join")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def alliance_hub_keyboard(alliance_id: int) -> InlineKeyboardMarkup:
    """Alliance hub when in alliance"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Members", callback_data=f"alliance_members:{alliance_id}")],
        [InlineKeyboardButton("💰 Donate", callback_data=f"alliance_donate:{alliance_id}")],
        [InlineKeyboardButton("🚪 Leave", callback_data=f"alliance_leave:{alliance_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── Settings Menu Keyboards ───

def settings_keyboard() -> InlineKeyboardMarkup:
    """Settings menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notif")],
        [InlineKeyboardButton("🏷 Title", callback_data="settings_title")],
        [InlineKeyboardButton("🌐 Language", callback_data="settings_lang")],
        [InlineKeyboardButton("❓ Help", callback_data="settings_help")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def notification_settings_keyboard(prefs=None) -> InlineKeyboardMarkup:
    """Notification toggle keyboard"""
    if not prefs:
        prefs = {}

    def get_emoji(value):
        return "✅" if value else "❌"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji(getattr(prefs, 'battle_alerts', True))} Battle Alerts",
                              callback_data="toggle_battle")],
        [InlineKeyboardButton(f"{get_emoji(getattr(prefs, 'energy_full', True))} Energy Full",
                              callback_data="toggle_energy")],
        [InlineKeyboardButton(f"{get_emoji(getattr(prefs, 'resource_full', True))} Resource Full",
                              callback_data="toggle_resource")],
        [InlineKeyboardButton(f"{get_emoji(getattr(prefs, 'building_complete', True))} Building Complete",
                              callback_data="toggle_building")],
        [InlineKeyboardButton(f"{get_emoji(getattr(prefs, 'alliance_events', True))} Alliance Events",
                              callback_data="toggle_alliance")],
        [InlineKeyboardButton(f"{get_emoji(getattr(prefs, 'bounty_alerts', True))} Bounty Alerts",
                              callback_data="toggle_bounty")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")],
    ])


# ─── Map Menu Keyboards ───

def map_menu_keyboard() -> InlineKeyboardMarkup:
    """Map menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗺 View Full Map", callback_data="map_view")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def map_tile_keyboard(x: int, y: int, occupant_id: int, is_self: bool) -> InlineKeyboardMarkup:
    """Map tile detail keyboard"""
    if is_self:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Map", callback_data="map_view")],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Attack", callback_data=f"attack_player:{occupant_id}")],
        [InlineKeyboardButton("🕵️ Spy", callback_data=f"spy_target:{occupant_id}")],
        [InlineKeyboardButton("🔙 Back to Map", callback_data="map_view")],
    ])


# ─── Stats Menu Keyboards ───

def stats_menu_keyboard() -> InlineKeyboardMarkup:
    """Stats menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Full Summary", callback_data="stats_summary")],
        [InlineKeyboardButton("⚔️ Army Chart", callback_data="stats_army"),
         InlineKeyboardButton("📈 Battles", callback_data="stats_battles")],
        [InlineKeyboardButton("🏰 Buildings", callback_data="stats_buildings"),
         InlineKeyboardButton("💰 Resources", callback_data="stats_resources")],
        [InlineKeyboardButton("🔙 Dashboard", callback_data="back_dashboard")],
    ])


# ─── Training Menu Keyboards ───

def training_menu_keyboard() -> InlineKeyboardMarkup:
    """Training center menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡 Train Infantry", callback_data="train_infantry")],
        [InlineKeyboardButton("🏹 Train Archers", callback_data="train_archers")],
        [InlineKeyboardButton("🐎 Train Cavalry", callback_data="train_cavalry")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def train_amount_keyboard(unit_type: str) -> InlineKeyboardMarkup:
    """Train amount selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10", callback_data=f"train_amount:{unit_type}:10"),
         InlineKeyboardButton("50", callback_data=f"train_amount:{unit_type}:50")],
        [InlineKeyboardButton("100", callback_data=f"train_amount:{unit_type}:100"),
         InlineKeyboardButton("500", callback_data=f"train_amount:{unit_type}:500")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_training")],
    ])


# ─── Trade Menu Keyboards ───

def trade_menu_keyboard() -> InlineKeyboardMarkup:
    """Trade system menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Gold → Food", callback_data="trade_gold_food")],
        [InlineKeyboardButton("🍖 Food → Gold", callback_data="trade_food_gold")],
        [InlineKeyboardButton("💎 Gems → Gold", callback_data="trade_gems_gold")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def trade_amount_keyboard(resource_from: str, resource_to: str, rates: list) -> InlineKeyboardMarkup:
    """Trade amount selection keyboard"""
    buttons = []
    for rate in rates:
        buttons.append([InlineKeyboardButton(
            f"{rate['from']:,} {rate['from_emoji']} → {rate['to']:,} {rate['to_emoji']}",
            callback_data=f"trade_execute:{resource_from}:{resource_to}:{rate['from']}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_trade")])
    return InlineKeyboardMarkup(buttons)


# ─── Bounty Menu Keyboards ───

def bounty_menu_keyboard() -> InlineKeyboardMarkup:
    """Bounty system menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 View Bounties", callback_data="bounty_view")],
        [InlineKeyboardButton("🎯 Place Bounty", callback_data="bounty_place")],
        [InlineKeyboardButton("🏆 My Bounties", callback_data="bounty_my")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── Achievements Menu Keyboards ───

def achievements_keyboard() -> InlineKeyboardMarkup:
    """Achievements menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏅 View Achievements", callback_data="achievements_view")],
        [InlineKeyboardButton("🏆 Claim Rewards", callback_data="achievements_claim")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── World Events Keyboard ───

def world_events_keyboard() -> InlineKeyboardMarkup:
    """World events menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Active Events", callback_data="events_active")],
        [InlineKeyboardButton("📜 Event History", callback_data="events_history")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── Admin Keyboard ───

def admin_keyboard() -> InlineKeyboardMarkup:
    """Admin menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])
