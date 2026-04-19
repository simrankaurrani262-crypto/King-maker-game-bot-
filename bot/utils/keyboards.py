from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ─── MAIN DASHBOARD ───
def dashboard_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Attack", callback_data="menu_attack"),
         InlineKeyboardButton("🏗 Build", callback_data="menu_build")],
        [InlineKeyboardButton("🗺 Map", callback_data="menu_map"),
         InlineKeyboardButton("🤝 Alliance", callback_data="menu_alliance")],
        [InlineKeyboardButton("🧙 Heroes", callback_data="menu_heroes"),
         InlineKeyboardButton("🕵️ Spy", callback_data="menu_spy")],
        [InlineKeyboardButton("🎯 Quests", callback_data="menu_quests"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard")],
        [InlineKeyboardButton("🎲 Mini-Games", callback_data="menu_games"),
         InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
    ])


# ─── ATTACK MENU ───
def attack_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Find Opponent", callback_data="attack_find")],
        [InlineKeyboardButton("🔥 Revenge", callback_data="attack_revenge")],
        [InlineKeyboardButton("🗺 Map Select", callback_data="attack_map")],
        [InlineKeyboardButton("🏃 Quick Raid", callback_data="attack_raid")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def opponent_keyboard(candidate_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Attack", callback_data=f"attack_player:{candidate_id}"),
         InlineKeyboardButton("⏭️ Next", callback_data="attack_next")],
        [InlineKeyboardButton("🕵️ Spy", callback_data=f"spy_player:{candidate_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_attack")],
    ])


def battle_response_keyboard(request_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept Fight", callback_data=f"battle_accept:{request_id}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"battle_decline:{request_id}")],
    ])


# ─── BUILDING MENU ───
def building_menu_keyboard(buildings):
    buttons = []
    for b in buildings:
        buttons.append([
            InlineKeyboardButton(f"{b.emoji} {b.display_name} — Lv.{b.level}", callback_data=f"building_select:{b.building_type}"),
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")])
    return InlineKeyboardMarkup(buttons)


def building_action_keyboard(building_type, level, is_upgrading):
    if is_upgrading:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ Upgrading...", callback_data="noop")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_build")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬆️ Upgrade", callback_data=f"building_upgrade:{building_type}"),
         InlineKeyboardButton("📥 Collect", callback_data=f"building_collect:{building_type}")],
        [InlineKeyboardButton("ℹ️ Info", callback_data=f"building_info:{building_type}")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_build")],
    ])


# ─── ARMY MENU ───
def army_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡 Train Infantry (+5)", callback_data="train_infantry")],
        [InlineKeyboardButton("🏹 Train Archers (+5)", callback_data="train_archers")],
        [InlineKeyboardButton("🐎 Train Cavalry (+5)", callback_data="train_cavalry")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── MAP MENU ───
def map_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 View Full Map", callback_data="map_view")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def map_tile_keyboard(x, y, occupant_id=None, is_self=False):
    if is_self or not occupant_id:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_map")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Attack", callback_data=f"attack_player:{occupant_id}"),
         InlineKeyboardButton("🕵️ Spy", callback_data=f"spy_player:{occupant_id}")],
        [InlineKeyboardButton("🤝 Invite Alliance", callback_data=f"alliance_invite:{occupant_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="map_view")],
    ])


# ─── ALLIANCE MENU ───
def alliance_hub_no_alliance_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏰 Create Alliance", callback_data="alliance_create")],
        [InlineKeyboardButton("🔍 Join Alliance", callback_data="alliance_join")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def alliance_hub_keyboard(alliance_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Members", callback_data=f"alliance_members:{alliance_id}"),
         InlineKeyboardButton("💰 Donate", callback_data=f"alliance_donate:{alliance_id}")],
        [InlineKeyboardButton("🚪 Leave", callback_data=f"alliance_leave:{alliance_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── HERO MENU ───
def heroes_keyboard(heroes):
    buttons = []
    for h in heroes:
        status = "✅" if h.unlocked else "🔒"
        buttons.append([
            InlineKeyboardButton(f"{status} {h.display_name} Lv.{h.level}", callback_data=f"hero_select:{h.hero_type}"),
        ])
    buttons.append([
        InlineKeyboardButton("⚔️ Attack Tree", callback_data="skill_attack"),
        InlineKeyboardButton("🛡 Defense Tree", callback_data="skill_defense"),
    ])
    buttons.append([
        InlineKeyboardButton("💰 Economy Tree", callback_data="skill_economy"),
        InlineKeyboardButton("🔙 Back", callback_data="back_dashboard"),
    ])
    return InlineKeyboardMarkup(buttons)


def hero_action_keyboard(hero_type, unlocked, level, can_upgrade=False):
    if not unlocked:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔓 Unlock", callback_data=f"hero_unlock:{hero_type}")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_heroes")],
        ])
    buttons = []
    if can_upgrade:
        buttons.append([InlineKeyboardButton("⬆️ Level Up", callback_data=f"hero_upgrade:{hero_type}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_heroes")])
    return InlineKeyboardMarkup(buttons)


# ─── QUEST MENU ───
def quests_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Claim All", callback_data="quests_claim")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── SPY MENU ───
def spy_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕵️ Send Spy", callback_data="spy_send")],
        [InlineKeyboardButton("📜 Spy History", callback_data="spy_history")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── RAID MENU ───
def raid_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Find Target", callback_data="raid_find")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_attack")],
    ])


# ─── GAMES MENU ───
def games_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Dice Game", callback_data="game_dice")],
        [InlineKeyboardButton("🎰 Lucky Spin", callback_data="game_spin")],
        [InlineKeyboardButton("🧠 Kingdom Quiz", callback_data="game_quiz")],
        [InlineKeyboardButton("⚔️ Survival Mode", callback_data="game_survival")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def dice_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Bet 100", callback_data="dice_bet:100"),
         InlineKeyboardButton("💰 Bet 500", callback_data="dice_bet:500")],
        [InlineKeyboardButton("💰 Bet 1000", callback_data="dice_bet:1000")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])


def spin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 SPIN!", callback_data="spin_wheel")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])


def quiz_keyboard(question_idx, options):
    buttons = []
    for i, opt in enumerate(options):
        buttons.append([InlineKeyboardButton(opt, callback_data=f"quiz_answer:{question_idx}:{i}")])
    return InlineKeyboardMarkup(buttons)


# ─── LEADERBOARD ───
def leaderboard_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Players", callback_data="lb_players"),
         InlineKeyboardButton("🤝 Alliances", callback_data="lb_alliances")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


# ─── BLACK MARKET ───
def black_market_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Item", callback_data="market_buy")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_games")],
    ])


# ─── SETTINGS ───
def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notif")],
        [InlineKeyboardButton("🏷 Change Title", callback_data="settings_title")],
        [InlineKeyboardButton("🌐 Language", callback_data="settings_lang")],
        [InlineKeyboardButton("❓ Help / How to Play", callback_data="settings_help")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def notification_settings_keyboard(prefs):
    ba = "✅" if prefs.battle_alerts else "❌"
    ef = "✅" if prefs.energy_full else "❌"
    rf = "✅" if prefs.resource_full else "❌"
    bc = "✅" if prefs.building_complete else "❌"
    ae = "✅" if prefs.alliance_events else "❌"
    bo = "✅" if prefs.bounty_alerts else "❌"
    pr = "✅" if prefs.promotions else "❌"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{ba} Battle Alerts", callback_data="toggle_battle")],
        [InlineKeyboardButton(f"{ef} Energy Full", callback_data="toggle_energy")],
        [InlineKeyboardButton(f"{rf} Resource Full", callback_data="toggle_resource")],
        [InlineKeyboardButton(f"{bc} Building Complete", callback_data="toggle_building")],
        [InlineKeyboardButton(f"{ae} Alliance Events", callback_data="toggle_alliance")],
        [InlineKeyboardButton(f"{bo} Bounty Alerts", callback_data="toggle_bounty")],
        [InlineKeyboardButton(f"{pr} Promotions", callback_data="toggle_promo")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")],
    ])


# ─── DECISION EVENT ───
def decision_keyboard(event_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Option A", callback_data=f"decision:{event_id}:A"),
         InlineKeyboardButton("⚔️ Option B", callback_data=f"decision:{event_id}:B")],
        [InlineKeyboardButton("🚪 Option C", callback_data=f"decision:{event_id}:C")],
    ])


# ─── BACK TO DASHBOARD ───
def back_dashboard_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_dashboard")],
    ])


# ─── START MENU ───
def start_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Start Game", callback_data="start_game")],
        [InlineKeyboardButton("📖 How to Play", callback_data="how_to_play")],
    ])


# ─── TRAIT SELECTION ───
def trait_selection_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Aggressive", callback_data="trait:aggressive")],
        [InlineKeyboardButton("🛡 Defensive", callback_data="trait:defensive")],
        [InlineKeyboardButton("💰 Rich", callback_data="trait:rich")],
        [InlineKeyboardButton("⚖️ Balanced", callback_data="trait:balanced")],
    ])


# ─── CONFIRM ───
def confirm_keyboard(confirm_data, cancel_data="back_dashboard"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
         InlineKeyboardButton("❌ Cancel", callback_data=cancel_data)],
    ])


# ─── BOUNTY ───
def bounty_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Place Bounty", callback_data="bounty_place")],
        [InlineKeyboardButton("⚔️ Accept Bounty", callback_data="bounty_accept")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")],
    ])


def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
    ])
