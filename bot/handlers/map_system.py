from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.services.game_data import GameData
from bot.utils.constants import MAP_SIZE
from bot.utils.keyboards import map_menu_keyboard, map_tile_keyboard


async def show_map_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show map menu"""
    query = update.callback_query
    
    text = "🗺 **KINGDOM MAP**\n"
    text += "━━━━━━━━━━━━━━\n\n"
    text += "Full map dekhne ke liye button dabao!\n"
    text += "Ya apne aas-paas ke kingdoms scout karo!"
    
    await query.edit_message_text(text, reply_markup=map_menu_keyboard())


async def handle_map_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle map menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_map":
        await show_map_menu(update, context, user_id)
    
    elif data == "map_view":
        await render_full_map(update, context, user_id)
    
    elif data.startswith("map_tile:"):
        parts = data.split(":")
        x, y = int(parts[1]), int(parts[2])
        await show_tile_detail(update, context, user_id, x, y)


async def render_full_map(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Render the 10x10 grid map"""
    query = update.callback_query
    
    viewer = GameData.get_kingdom_with_relations(user_id)
    if not viewer:
        return
    
    all_kingdoms = GameData.get_all_kingdoms()
    
    # Get alliances
    with get_db() as db:
        from bot.models import AllianceMember
        my_alliance = db.query(AllianceMember).filter(AllianceMember.kingdom_id == user_id).first()
        ally_ids = []
        if my_alliance:
            ally_ids = [m.kingdom_id for m in db.query(AllianceMember).filter(
                AllianceMember.alliance_id == my_alliance.alliance_id
            ).all() if m.kingdom_id != user_id]
    
    # Build grid
    grid = "🗺 **KINGDOM MAP**\n"
    grid += "```\n   1  2  3  4  5  6  7  8  9  10\n"
    
    for y in range(1, MAP_SIZE + 1):
        row = f"{y:2d} "
        for x in range(1, MAP_SIZE + 1):
            occupant = None
            for k in all_kingdoms:
                if k.map_x == x and k.map_y == y:
                    occupant = k
                    break
            
            if not occupant:
                row += "⬜ "
            elif occupant.user_id == user_id:
                row += "🟩 "
            elif occupant.user_id in ally_ids:
                row += "🟦 "
            else:
                row += "🟥 "
        grid += row + "\n"
    
    grid += "```\n"
    grid += "🟩 You | 🟦 Ally | 🟥 Enemy | ⬜ Empty\n"
    grid += f"\n📍 Your position: ({viewer.map_x}, {viewer.map_y})"
    
    # Create tile selection keyboard
    keyboard = []
    for y in range(1, MAP_SIZE + 1, 2):
        row_buttons = []
        for x in range(1, MAP_SIZE + 1, 5):
            row_buttons.append(InlineKeyboardButton(
                f"({x},{y})",
                callback_data=f"map_tile:{x}:{y}"
            ))
        if row_buttons:
            keyboard.append(row_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_map")])
    
    try:
        await query.edit_message_text(grid, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
        # Try without markdown formatting
        grid_plain = grid.replace("```", "").replace("**", "")
        await query.edit_message_text(grid_plain, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_tile_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, x: int, y: int):
    """Show details for a specific tile"""
    query = update.callback_query
    
    occupant = None
    for k in GameData.get_all_kingdoms():
        if k.map_x == x and k.map_y == y:
            occupant = k
            break
    
    if not occupant:
        await query.edit_message_text(
            f"📍 **({x},{y})**\n━━━━━━━━━━━━━━\n\nKhali jagah!\nYahan koi kingdom nahi hai.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Map", callback_data="map_view")],
            ])
        )
        return
    
    viewer = GameData.get_kingdom_with_relations(user_id)
    distance = abs(viewer.map_x - occupant.map_x) + abs(viewer.map_y - occupant.map_y)
    
    from bot.services.economy import EconomyService
    from bot.utils.formatters import get_defense_rating_label
    
    defense_power = EconomyService.calculate_defense_rating(occupant)
    
    text = f"""👑 **{occupant.name}** {occupant.flag}
━━━━━━━━━━━━━━
🏆 Level: {occupant.level}
⚔️ Army: ~{occupant.army.total if occupant.army else 0} (estimated)
🛡 Defense: {get_defense_rating_label(defense_power)}
🟢 Status: {'Online' if occupant.is_online else 'Offline'}
📍 Distance: {distance} tiles
━━━━━━━━━━━━━━"""
    
    is_self = occupant.user_id == user_id
    keyboard = map_tile_keyboard(x, y, occupant.user_id, is_self)
    
    await query.edit_message_text(text, reply_markup=keyboard)


async def render_full_map_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Render map directly from command handler (without callback query)"""
    viewer = GameData.get_kingdom_with_relations(user_id)
    if not viewer:
        await update.message.reply_text("❌ Kingdom not found!")
        return
    
    all_kingdoms = GameData.get_all_kingdoms()
    
    with get_db() as db:
        from bot.models import AllianceMember
        my_alliance = db.query(AllianceMember).filter(AllianceMember.kingdom_id == user_id).first()
        ally_ids = []
        if my_alliance:
            ally_ids = [m.kingdom_id for m in db.query(AllianceMember).filter(
                AllianceMember.alliance_id == my_alliance.alliance_id
            ).all() if m.kingdom_id != user_id]
    
    grid = "🗺 **KINGDOM MAP**\n"
    grid += "```\n   1  2  3  4  5  6  7  8  9  10\n"
    
    for y in range(1, MAP_SIZE + 1):
        row = f"{y:2d} "
        for x in range(1, MAP_SIZE + 1):
            occupant = None
            for k in all_kingdoms:
                if k.map_x == x and k.map_y == y:
                    occupant = k
                    break
            
            if not occupant:
                row += "⬜ "
            elif occupant.user_id == user_id:
                row += "🟩 "
            elif occupant.user_id in ally_ids:
                row += "🟦 "
            else:
                row += "🟥 "
        grid += row + "\n"
    
    grid += "```\n"
    grid += "🟩 You | 🟦 Ally | 🟥 Enemy | ⬜ Empty\n"
    grid += f"\n📍 Your position: ({viewer.map_x}, {viewer.map_y})"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_dashboard")],
    ])
    
    try:
        await update.message.reply_text(grid, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        grid_plain = grid.replace("```", "").replace("**", "")
        await update.message.reply_text(grid_plain, reply_markup=keyboard)


# Need get_db import
from bot.models import get_db
