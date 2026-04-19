from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, Building
from bot.services.game_data import GameData
from bot.services.economy import EconomyService
from bot.utils.formatters import format_number, format_duration
from bot.utils.keyboards import building_menu_keyboard, building_action_keyboard, back_dashboard_keyboard
from bot.utils.constants import BUILDING_CONFIG


async def show_building_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show the building management menu"""
    query = update.callback_query
    
    buildings = GameData.get_buildings(user_id)
    
    text = "🏗 **BUILDING MENU**\n━━━━━━━━━━━━━━\n\n"
    
    for b in buildings:
        status = "⬆️ Upgrading" if b.is_upgrading else f"Lv.{b.level}"
        text += f"{b.emoji} {b.display_name} — {status}\n"
    
    text += "\n━━━━━━━━━━━━━━\nSelect a building:"
    
    keyboard = building_menu_keyboard(buildings)
    
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except Exception:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)


async def handle_build_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle building-related callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_build":
        await show_building_menu(update, context, user_id)
        return
    
    if data.startswith("building_select:"):
        building_type = data.split(":")[1]
        await show_building_detail(update, context, user_id, building_type)
    
    elif data.startswith("building_upgrade:"):
        building_type = data.split(":")[1]
        await upgrade_building(update, context, user_id, building_type)
    
    elif data.startswith("building_collect:"):
        building_type = data.split(":")[1]
        await collect_resources(update, context, user_id, building_type)
    
    elif data.startswith("building_info:"):
        building_type = data.split(":")[1]
        await show_building_info(update, context, user_id, building_type)


async def show_building_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Show detail for a specific building"""
    query = update.callback_query
    
    building = GameData.get_building(user_id, building_type)
    if not building:
        await query.edit_message_text("❌ Building not found!", reply_markup=back_dashboard_keyboard())
        return
    
    kingdom = GameData.get_kingdom(user_id)
    
    # Calculate upgrade cost
    cost = EconomyService.calculate_upgrade_cost(building_type, building.level)
    
    # Calculate production
    production = EconomyService.calculate_production_rate(building_type, building.level, kingdom.trait)
    next_production = EconomyService.calculate_production_rate(building_type, building.level + 1, kingdom.trait)
    
    text = f"{building.emoji} **{building.display_name}**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"📊 Level: {building.level}\n"
    
    if production > 0:
        text += f"⚡ Production: {production:,}/hr\n"
        text += f"⬆️ Next: {next_production:,}/hr\n"
    
    if building.is_upgrading:
        remaining = building.upgrade_completes - datetime.utcnow()
        minutes = max(0, int(remaining.total_seconds() / 60))
        text += f"\n⏳ Upgrading... {minutes}m left\n"
    else:
        text += f"\n💰 Cost: {cost['gold']:,} Gold"
        if cost['food'] > 0:
            text += f", {cost['food']:,} Food"
        text += f"\n⏱ Time: {format_duration(cost['time_minutes'])}\n"
    
    text += "\n━━━━━━━━━━━━━━"
    
    keyboard = building_action_keyboard(building_type, building.level, building.is_upgrading)
    await query.edit_message_text(text, reply_markup=keyboard)


async def upgrade_building(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Start building upgrade"""
    query = update.callback_query
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()
        
        if not kingdom or not building:
            await query.edit_message_text("❌ Error!", reply_markup=back_dashboard_keyboard())
            return
        
        if building.is_upgrading:
            await query.answer("⏳ Already upgrading!")
            return
        
        cost = EconomyService.calculate_upgrade_cost(building_type, building.level)
        
        if kingdom.gold < cost['gold']:
            await query.answer(f"❌ {cost['gold'] - kingdom.gold:,} Gold aur chahiye!")
            return
        
        if kingdom.food < cost['food']:
            await query.answer(f"❌ {cost['food'] - kingdom.food:,} Food aur chahiye!")
            return
        
        # Deduct resources
        kingdom.gold -= cost['gold']
        kingdom.food -= cost['food']
        
        # Set upgrade
        building.is_upgrading = True
        building.upgrade_started = datetime.utcnow()
        building.upgrade_completes = datetime.utcnow() + timedelta(minutes=cost['time_minutes'])
        
        kingdom.buildings_upgraded += 1
        
        db.commit()
    
    await query.answer("⬆️ Upgrade started!")
    
    # Show updated detail
    await show_building_detail(update, context, user_id, building_type)
    
    # Schedule completion check
    context.job_queue.run_once(
        complete_building_upgrade,
        when=cost['time_minutes'] * 60,
        data={'user_id': user_id, 'building_type': building_type},
        name=f"upgrade_{user_id}_{building_type}"
    )


async def complete_building_upgrade(context: ContextTypes.DEFAULT_TYPE):
    """Callback when building upgrade completes"""
    job_data = context.job.data
    user_id = job_data['user_id']
    building_type = job_data['building_type']
    
    with get_db() as db:
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()
        
        if building and building.is_upgrading:
            building.level += 1
            building.is_upgrading = False
            building.upgrade_started = None
            building.upgrade_completes = None
            db.commit()
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ **{building.display_name}** is now **Level {building.level}**!"
                )
            except Exception:
                pass


async def collect_resources(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Collect resources from a building"""
    query = update.callback_query
    
    with get_db() as db:
        kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        building = db.query(Building).filter(
            Building.kingdom_id == user_id,
            Building.building_type == building_type
        ).first()
        
        if not kingdom or not building:
            await query.answer("❌ Error!")
            return
        
        produced = EconomyService.calculate_collected_resources(building, kingdom.trait)
        
        if produced < 1:
            await query.answer("❌ Koi resource taiyaar nahi! Thodi der baad aao!")
            return
        
        # Add resources
        if building_type == "gold_mine":
            kingdom.gold += produced
            resource_emoji = "💰"
        elif building_type == "farm":
            kingdom.food += produced
            resource_emoji = "🍖"
        elif building_type == "barracks":
            # Barracks produces soldiers
            if kingdom.army:
                kingdom.army.infantry += produced
                kingdom.soldiers_trained += produced
            resource_emoji = "🗡"
        else:
            await query.answer("❌ Is building se collect nahi ho sakta!")
            return
        
        building.last_collected = datetime.utcnow()
        db.commit()
    
    await query.answer(f"{resource_emoji} +{produced:,} collected!")
    
    # Show updated detail
    await show_building_detail(update, context, user_id, building_type)


async def show_building_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, building_type: str):
    """Show building information"""
    query = update.callback_query
    
    config = BUILDING_CONFIG.get(building_type, {})
    building = GameData.get_building(user_id, building_type)
    
    text = f"ℹ️ **{config.get('name', building_type)}** Info\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"{config.get('description', '')}\n\n"
    text += f"Max Level: 25\n"
    text += f"Current: Lv.{building.level if building else 1}\n"
    
    if building_type == "town_hall":
        text += "\n🏰 Har level par naye buildings unlock hote hain!"
    elif building_type == "gold_mine":
        text += f"\n⛏ Gold production scales with level"
    elif building_type == "farm":
        text += f"\n🌾 Food production scales with level"
    elif building_type == "barracks":
        text += f"\n🏹 Training speed scales with level\n"
        text += "Lv.2 → 🏹 Archers unlock\n"
        text += "Lv.4 → 🐎 Cavalry unlock"
    elif building_type == "wall":
        text += f"\n🛡 Each level: +3% damage reduction"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"building_select:{building_type}")],
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)


async def process_all_building_upgrades(context: ContextTypes.DEFAULT_TYPE):
    """Background task: check and complete all building upgrades"""
    with get_db() as db:
        upgrading = db.query(Building).filter(
            Building.is_upgrading == True,
            Building.upgrade_completes <= datetime.utcnow()
        ).all()
        
        for building in upgrading:
            building.level += 1
            building.is_upgrading = False
            building.upgrade_started = None
            building.upgrade_completes = None
            
            try:
                await context.bot.send_message(
                    chat_id=building.kingdom_id,
                    text=f"✅ **{building.display_name}** is now **Level {building.level}**!"
                )
            except Exception:
                pass
        
        db.commit()
