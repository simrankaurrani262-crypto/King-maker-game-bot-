import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models import get_db, SpyReport, Kingdom
from bot.services.game_data import GameData
from bot.utils.formatters import format_number
from bot.utils.keyboards import spy_menu_keyboard, back_dashboard_keyboard
from bot.utils.constants import SPY_COST_GOLD, SPY_SUCCESS_BASE_CHANCE, SPY_TRAP_CHANCE, SPY_COOLDOWN_MINUTES


async def show_spy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, target_id: int = None):
    """Show spy menu - if target_id provided, shows spy options for that target"""
    query = update.callback_query
    
    kingdom = GameData.get_kingdom_with_relations(user_id)
    
    # Check cooldown
    cooldown = GameData.get_cooldown(user_id, "spy")
    cooldown_text = ""
    if cooldown:
        remaining = cooldown - datetime.utcnow()
        mins = max(0, int(remaining.total_seconds() // 60))
        cooldown_text = f"\n⏳ Cooldown: {mins}m left\n"
    
    text = "🕵️ **SPY MENU**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"💰 Spy Cost: {SPY_COST_GOLD} Gold\n"
    text += cooldown_text
    text += f"\n🕵️ Dusre kingdoms par spy bhejo!\n"
    text += f"Intel quality: Basic → Detailed → Full\n"
    text += f"⚠️ Trap mein pakde jaane ka khatra!"
    
    await query.edit_message_text(text, reply_markup=spy_menu_keyboard())


# ═══════════════════════════════════════════
# ROUTER COMPATIBILITY WRAPPERS
# ═══════════════════════════════════════════

async def show_spy_hub(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Wrapper for spy hub menu"""
    await show_spy_menu(update, context, user_id)


async def find_spy_target(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Find a random target to spy on"""
    query = update.callback_query

    kingdom = GameData.get_kingdom_with_relations(user_id)
    if not kingdom:
        return

    # Find a random opponent
    from bot.models import Kingdom as KingdomModel
    with get_db() as db:
        opponents = db.query(KingdomModel).filter(KingdomModel.user_id != user_id).all()
        if not opponents:
            await query.answer("❌ No opponents found!", show_alert=True)
            return
        target = random.choice(opponents)

    # Execute spy mission directly
    await execute_spy(update, context, user_id, target.user_id)


async def handle_spy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle spy callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_spy":
        await show_spy_menu(update, context, user_id)
    
    elif data == "spy_send":
        await start_spy_mission(update, context, user_id)
    
    elif data == "spy_history":
        await show_spy_history(update, context, user_id)
    
    elif data.startswith("spy_target:"):
        target_id = int(data.split(":")[1])
        await execute_spy(update, context, user_id, target_id)


async def start_spy_mission(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start spy mission - show targets"""
    query = update.callback_query
    
    # Check cooldown
    cooldown = GameData.get_cooldown(user_id, "spy")
    if cooldown and cooldown > datetime.utcnow():
        remaining = cooldown - datetime.utcnow()
        mins = int(remaining.total_seconds() // 60)
        await query.answer(f"⏳ {mins}m cooldown left!")
        return
    
    # Find targets
    targets = GameData.find_opponents(user_id, limit=5)
    if not targets:
        await query.edit_message_text(
            "❌ Koi spy target nahi mila!",
            reply_markup=spy_menu_keyboard()
        )
        return
    
    text = "🕵️ **SELECT TARGET**\n"
    text += f"━━━━━━━━━━━━━━\n"
    text += f"💰 Cost: {SPY_COST_GOLD} Gold\n\n"
    
    buttons = []
    for target, power, distance in targets:
        text += f"👑 {target.name} {target.flag} — Lv.{target.level}\n"
        buttons.append([InlineKeyboardButton(
            f"🕵️ Spy on {target.name}",
            callback_data=f"spy_target:{target.user_id}"
        )])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_spy")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def execute_spy(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, target_id: int):
    """Execute spy mission"""
    query = update.callback_query
    
    with get_db() as db:
        spy_kingdom = db.query(Kingdom).filter(Kingdom.user_id == user_id).first()
        target = db.query(Kingdom).filter(Kingdom.user_id == target_id).first()
        
        if not spy_kingdom or not target:
            await query.answer("❌ Error!")
            return
        
        if spy_kingdom.gold < SPY_COST_GOLD:
            await query.answer(f"❌ {SPY_COST_GOLD} Gold chahiye!")
            return
        
        # Deduct cost
        spy_kingdom.gold -= SPY_COST_GOLD
        spy_kingdom.spy_missions += 1
        
        # Set cooldown
        GameData.set_cooldown(user_id, "spy", SPY_COOLDOWN_MINUTES)
        
        # Check for trap (simplified - 15% chance)
        if random.random() < SPY_TRAP_CHANCE:
            spy_kingdom.successful_spies += 0  # Failed
            db.commit()
            
            await query.edit_message_text(
                "💀 **SPY CAUGHT!**\n"
                "━━━━━━━━━━━━━━\n\n"
                f"Aapka spy {target.name} ke trap mein pakda gaya!\n"
                "💰 Gold lost!\n"
                "⏳ 1 hour cooldown!",
                reply_markup=spy_menu_keyboard()
            )
            
            # Notify target
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"🕵️ **Spy Caught!**\n@{spy_kingdom.name} ne jaasoosi ki koshish ki!\nAapka trap kaam kar gaya! 🎉"
                )
            except Exception:
                pass
            return
        
        # Success chance
        if random.random() > SPY_SUCCESS_BASE_CHANCE:
            db.commit()
            await query.edit_message_text(
                "🕵️ **Spy Mission Failed!**\n"
                "━━━━━━━━━━━━━━\n\n"
                "Koi intel haasil nahi hua!\n"
                "Target ka defense zyada tha!",
                reply_markup=spy_menu_keyboard()
            )
            return
        
        # Successful spy
        spy_kingdom.successful_spies += 1
        
        intel_level = random.choice(["basic", "detailed", "full"])
        
        report = f"🕵️ **SPY REPORT: {target.name} {target.flag}**\n"
        report += "━━━━━━━━━━━━━━\n"
        
        if intel_level in ["basic", "detailed", "full"]:
            report += f"⚔️ Army: ~{target.army.total if target.army else 0}\n"
            report += f"🛡 Wall Level: {target.wall_level}\n"
        
        if intel_level in ["detailed", "full"]:
            report += f"💰 Gold: ~{target.gold:,}\n"
            report += f"🍖 Food: ~{target.food:,}\n"
            report += f"⚡ Energy: {target.energy}/10\n"
        
        if intel_level == "full":
            if target.army:
                report += f"🗡 Infantry: {target.army.infantry}\n"
                report += f"🏹 Archers: {target.army.archers}\n"
                report += f"🐎 Cavalry: {target.army.cavalry}\n"
            report += f"🛡 Shield: {target.shield_time_remaining}\n"
        
        report += "━━━━━━━━━━━━━━\n"
        report += f"📊 Intel Quality: **{intel_level.upper()}**"
        
        # Save report
        spy_report = SpyReport(
            spy_id=user_id,
            target_id=target_id,
            intel_level=intel_level,
            report_text=report,
            success=1,
        )
        db.add(spy_report)
        db.commit()
    
    await query.edit_message_text(report, reply_markup=spy_menu_keyboard())


async def show_spy_history(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show spy report history"""
    query = update.callback_query
    
    with get_db() as db:
        reports = db.query(SpyReport).filter(SpyReport.spy_id == user_id).order_by(SpyReport.created_at.desc()).limit(5).all()
    
    if not reports:
        await query.edit_message_text(
            "📜 **No Spy History**\n\nAbhi tak koi spy mission nahi!",
            reply_markup=spy_menu_keyboard()
        )
        return
    
    text = "📜 **SPY HISTORY**\n━━━━━━━━━━━━━━\n\n"
    for r in reports:
        status = "✅" if r.success else "❌"
        text += f"{status} Target: {r.target_id} — {r.intel_level.upper()}\n"
        text += f"   {r.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await query.edit_message_text(text, reply_markup=spy_menu_keyboard())
