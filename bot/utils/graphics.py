"""
Graphics Utility - Chart & Graph Generation for Kingdom Statistics
Uses matplotlib and PIL to create beautiful visualizations.
"""

import os
import io
import logging
import tempfile
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, Circle
    import numpy as np
    GRAPHICS_AVAILABLE = True
except ImportError:
    GRAPHICS_AVAILABLE = False
    logging.warning("matplotlib/numpy not available. Charts disabled.")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Image effects disabled.")

from bot.config import config

logger = logging.getLogger(__name__)


class StatsChartGenerator:
    """Generate beautiful charts and graphs for kingdom statistics"""
    
    def __init__(self):
        self.style = config.CHART_STYLE if hasattr(config, 'CHART_STYLE') else 'dark_background'
        self.dpi = config.CHART_DPI if hasattr(config, 'CHART_DPI') else 150
        self.figsize = config.CHART_FIGURE_SIZE if hasattr(config, 'CHART_FIGURE_SIZE') else (10, 6)
        self.output_dir = tempfile.gettempdir()
        
        if GRAPHICS_AVAILABLE:
            plt.style.use(self.style)
    
    def _get_save_path(self, prefix: str = "chart") -> str:
        """Generate unique save path"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"kingdom_{prefix}_{timestamp}.png")
    
    def _setup_figure(self, title: str, figsize: Optional[Tuple] = None) -> Tuple:
        """Setup matplotlib figure with styling"""
        fig, ax = plt.subplots(figsize=figsize or self.figsize, dpi=self.dpi)
        ax.set_facecolor('#1a1a2e')
        fig.patch.set_facecolor('#16213e')
        ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=20)
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('#4a4a6a')
        return fig, ax
    
    # ─── Kingdom Summary Chart ───
    
    def create_kingdom_summary(self, kingdom) -> Optional[str]:
        """Create a comprehensive kingdom summary chart"""
        if not GRAPHICS_AVAILABLE:
            return None
        
        try:
            fig = plt.figure(figsize=(12, 10), dpi=self.dpi)
            fig.patch.set_facecolor('#16213e')
            
            # Title
            fig.suptitle(
                f"{getattr(kingdom, 'name', 'Unknown')} {getattr(kingdom, 'flag', '')} - Kingdom Report",
                color='gold', fontsize=16, fontweight='bold', y=0.98
            )
            
            # Grid layout: 2x2
            gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
            
            # 1. Resource Distribution (Pie Chart)
            ax1 = fig.add_subplot(gs[0, 0])
            ax1.set_facecolor('#1a1a2e')
            self._draw_resource_pie(ax1, kingdom)
            
            # 2. Army Composition (Horizontal Bar)
            ax2 = fig.add_subplot(gs[0, 1])
            ax2.set_facecolor('#1a1a2e')
            self._draw_army_bar(ax2, kingdom)
            
            # 3. Building Levels (Vertical Bar)
            ax3 = fig.add_subplot(gs[1, 0])
            ax3.set_facecolor('#1a1a2e')
            self._draw_building_levels(ax3, kingdom)
            
            # 4. Stats Overview (Text)
            ax4 = fig.add_subplot(gs[1, 1])
            ax4.set_facecolor('#1a1a2e')
            self._draw_stats_text(ax4, kingdom)
            
            save_path = self._get_save_path("summary")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#16213e', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating kingdom summary: {e}")
            return None
    
    def _draw_resource_pie(self, ax, kingdom):
        """Draw resource distribution pie chart"""
        gold = getattr(kingdom, 'gold', 0)
        food = getattr(kingdom, 'food', 0)
        gems = getattr(kingdom, 'gems', 0) * 100  # Scale gems for visibility
        
        if gold + food + gems == 0:
            ax.text(0.5, 0.5, 'No Resources', ha='center', va='center', 
                   transform=ax.transAxes, color='white', fontsize=12)
            ax.set_title('Resources', color='white', fontsize=11)
            ax.axis('off')
            return
        
        sizes = [gold, food, gems]
        labels = [f'Gold\n{gold:,}', f'Food\n{food:,}', f'Gems\n{getattr(kingdom, "gems", 0):,}']
        colors = ['#FFD700', '#FF6B6B', '#4ECDC4']
        explode = (0.05, 0.05, 0.1)
        
        wedges, texts = ax.pie(
            sizes, labels=labels, colors=colors, explode=explode,
            startangle=90, textprops={'color': 'white', 'fontsize': 8}
        )
        ax.set_title('Resource Distribution', color='white', fontsize=11, fontweight='bold')
    
    def _draw_army_bar(self, ax, kingdom):
        """Draw army composition horizontal bar chart"""
        army = getattr(kingdom, 'army', None)
        infantry = getattr(army, 'infantry', 0) if army else 0
        archers = getattr(army, 'archers', 0) if army else 0
        cavalry = getattr(army, 'cavalry', 0) if army else 0
        
        units = ['Infantry', 'Archers', 'Cavalry']
        values = [infantry, archers, cavalry]
        colors = ['#3498db', '#2ecc71', '#e74c3c']
        
        bars = ax.barh(units, values, color=colors, edgecolor='white', linewidth=0.5)
        ax.set_xlabel('Count', color='white', fontsize=9)
        ax.set_title('Army Composition', color='white', fontsize=11, fontweight='bold')
        
        for bar, val in zip(bars, values):
            ax.text(val + max(values) * 0.02, bar.get_y() + bar.get_height()/2, 
                   f'{val:,}', va='center', color='white', fontsize=9, fontweight='bold')
        
        ax.set_xlim(0, max(values) * 1.2 if values else 10)
    
    def _draw_building_levels(self, ax, kingdom):
        """Draw building levels vertical bar chart"""
        buildings = getattr(kingdom, 'buildings', [])
        
        names = []
        levels = []
        colors_list = []
        
        color_map = {
            'town_hall': '#FFD700',
            'gold_mine': '#FFA500',
            'farm': '#2ecc71',
            'barracks': '#e74c3c',
            'wall': '#9b59b6'
        }
        
        for b in buildings:
            btype = getattr(b, 'building_type', 'unknown')
            blevel = getattr(b, 'level', 1)
            bconfig = getattr(b, 'config', None)
            
            if bconfig:
                name = bconfig.get('name', btype)
            else:
                name = btype.replace('_', ' ').title()
            
            names.append(name)
            levels.append(blevel)
            colors_list.append(color_map.get(btype, '#3498db'))
        
        if not names:
            ax.text(0.5, 0.5, 'No Buildings', ha='center', va='center',
                   transform=ax.transAxes, color='white', fontsize=12)
            ax.set_title('Building Levels', color='white', fontsize=11)
            ax.axis('off')
            return
        
        bars = ax.bar(names, levels, color=colors_list, edgecolor='white', linewidth=0.5)
        ax.set_ylabel('Level', color='white', fontsize=9)
        ax.set_title('Building Levels', color='white', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        
        for bar, val in zip(bars, levels):
            ax.text(bar.get_x() + bar.get_width()/2, val + 0.3,
                   f'Lv.{val}', ha='center', color='white', fontsize=8, fontweight='bold')
        
        ax.set_ylim(0, max(levels) * 1.3 if levels else 5)
    
    def _draw_stats_text(self, ax, kingdom):
        """Draw statistics text panel"""
        from bot.services.economy import EconomyService
        
        total_power = EconomyService.calculate_kingdom_power(kingdom)
        defense = EconomyService.calculate_defense_rating(kingdom)
        
        battles_won = getattr(kingdom, 'battles_won', 0)
        battles_lost = getattr(kingdom, 'battles_lost', 0)
        total_battles = battles_won + battles_lost
        win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0
        
        stats_text = (
            f"⚡ Total Power: {total_power:,}\n"
            f"🛡 Defense: {defense:,}\n"
            f"\n"
            f"📈 Battle Record\n"
            f"  ✅ Wins: {battles_won}\n"
            f"  ❌ Losses: {battles_lost}\n"
            f"  📊 Win Rate: {win_rate:.1f}%\n"
            f"\n"
            f"🏗 Buildings: {len(getattr(kingdom, 'buildings', []))}\n"
            f"👥 Level: {getattr(kingdom, 'level', 1)}\n"
            f"📍 Position: ({getattr(kingdom, 'map_x', 0)}, {getattr(kingdom, 'map_y', 0)})\n"
            f"🧬 Trait: {getattr(kingdom, 'trait', 'balanced').title()}"
        )
        
        ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
               color='white', fontsize=10, verticalalignment='top',
               family='monospace', bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))
        ax.set_title('Statistics', color='white', fontsize=11, fontweight='bold')
        ax.axis('off')
    
    # ─── Resource History Chart ───
    
    def create_resource_chart(self, resource_history: List[Dict]) -> Optional[str]:
        """Create a line chart showing resource history over time"""
        if not GRAPHICS_AVAILABLE or not resource_history:
            return None
        
        try:
            fig, ax = self._setup_figure("📊 Resource History (Last 7 Days)", (12, 6))
            
            times = [datetime.fromisoformat(r['timestamp']) for r in resource_history]
            gold_values = [r.get('gold', 0) for r in resource_history]
            food_values = [r.get('food', 0) for r in resource_history]
            
            ax.plot(times, gold_values, color='#FFD700', linewidth=2, marker='o', 
                   markersize=4, label='Gold')
            ax.plot(times, food_values, color='#FF6B6B', linewidth=2, marker='s',
                   markersize=4, label='Food')
            
            ax.set_xlabel('Time', color='white', fontsize=10)
            ax.set_ylabel('Amount', color='white', fontsize=10)
            ax.legend(loc='upper left', facecolor='#1a1a2e', edgecolor='white', labelcolor='white')
            ax.grid(True, alpha=0.3, color='#4a4a6a')
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            save_path = self._get_save_path("resources")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#16213e', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating resource chart: {e}")
            return None
    
    # ─── Battle Performance Chart ───
    
    def create_battle_chart(self, battle_history: List[Dict]) -> Optional[str]:
        """Create battle performance visualization"""
        if not GRAPHICS_AVAILABLE or not battle_history:
            return None
        
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=self.dpi)
            fig.patch.set_facecolor('#16213e')
            
            # Win/Loss pie chart
            wins = sum(1 for b in battle_history if b.get('won'))
            losses = len(battle_history) - wins
            
            ax1.set_facecolor('#1a1a2e')
            if wins + losses > 0:
                sizes = [wins, losses]
                colors = ['#2ecc71', '#e74c3c']
                labels = [f'Wins\n{wins}', f'Losses\n{losses}']
                ax1.pie(sizes, labels=labels, colors=colors, startangle=90,
                       textprops={'color': 'white', 'fontsize': 10})
            ax1.set_title('Win/Loss Ratio', color='white', fontsize=12, fontweight='bold')
            
            # Battle timeline
            ax2.set_facecolor('#1a1a2e')
            battle_nums = list(range(1, len(battle_history) + 1))
            gold_looted = [b.get('gold_looted', 0) for b in battle_history]
            
            colors = ['#2ecc71' if b.get('won') else '#e74c3c' for b in battle_history]
            ax2.bar(battle_nums, gold_looted, color=colors, edgecolor='white', linewidth=0.5)
            ax2.set_xlabel('Battle #', color='white', fontsize=9)
            ax2.set_ylabel('Gold Looted', color='white', fontsize=9)
            ax2.set_title('Battle History', color='white', fontsize=12, fontweight='bold')
            ax2.tick_params(colors='white')
            for spine in ax2.spines.values():
                spine.set_color('#4a4a6a')
            
            plt.tight_layout()
            save_path = self._get_save_path("battles")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#16213e', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating battle chart: {e}")
            return None
    
    # ─── Army Composition Pie Chart ───
    
    def create_army_pie(self, kingdom) -> Optional[str]:
        """Create army composition pie chart"""
        if not GRAPHICS_AVAILABLE:
            return None
        
        try:
            army = getattr(kingdom, 'army', None)
            infantry = getattr(army, 'infantry', 0) if army else 0
            archers = getattr(army, 'archers', 0) if army else 0
            cavalry = getattr(army, 'cavalry', 0) if army else 0
            
            if infantry + archers + cavalry == 0:
                return None
            
            fig, ax = self._setup_figure("⚔️ Army Composition", (8, 8))
            
            sizes = [infantry, archers, cavalry]
            labels = [f'Infantry\n{infantry:,}', f'Archers\n{archers:,}', f'Cavalry\n{cavalry:,}']
            colors = ['#3498db', '#2ecc71', '#e74c3c']
            explode = (0.05, 0.05, 0.1)
            
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors, explode=explode,
                autopct='%1.1f%%', startangle=90,
                textprops={'color': 'white', 'fontsize': 11},
                wedgeprops={'edgecolor': 'white', 'linewidth': 2}
            )
            
            for autotext in autotexts:
                autotext.set_fontweight('bold')
                autotext.set_fontsize(12)
            
            plt.tight_layout()
            save_path = self._get_save_path("army")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#16213e', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating army pie chart: {e}")
            return None
    
    # ─── Power Comparison Chart ───
    
    def create_power_comparison(self, kingdoms_data: List[Dict]) -> Optional[str]:
        """Create power comparison bar chart between kingdoms"""
        if not GRAPHICS_AVAILABLE or not kingdoms_data:
            return None
        
        try:
            fig, ax = self._setup_figure("⚡ Power Rankings", (12, 6))
            
            names = [k.get('name', 'Unknown')[:12] for k in kingdoms_data]
            powers = [k.get('power', 0) for k in kingdoms_data]
            flags = [k.get('flag', '') for k in kingdoms_data]
            
            labels = [f"{f} {n}" for f, n in zip(flags, names)]
            colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(kingdoms_data)))
            
            bars = ax.barh(labels, powers, color=colors, edgecolor='white', linewidth=0.5)
            ax.set_xlabel('Power', color='white', fontsize=10)
            ax.set_title('Kingdom Power Comparison', color='white', fontsize=14, fontweight='bold')
            ax.invert_yaxis()
            
            for bar, val in zip(bars, powers):
                ax.text(val + max(powers) * 0.02, bar.get_y() + bar.get_height()/2,
                       f'{val:,}', va='center', color='white', fontsize=9, fontweight='bold')
            
            plt.tight_layout()
            save_path = self._get_save_path("power")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#16213e', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating power comparison: {e}")
            return None
    
    # ─── Growth Timeline Chart ───
    
    def create_growth_timeline(self, growth_data: List[Dict]) -> Optional[str]:
        """Create kingdom growth timeline chart"""
        if not GRAPHICS_AVAILABLE or not growth_data:
            return None
        
        try:
            fig, ax = self._setup_figure("📈 Kingdom Growth Timeline", (12, 6))
            
            dates = [datetime.fromisoformat(d['date']) for d in growth_data]
            levels = [d.get('level', 1) for d in growth_data]
            power = [d.get('power', 0) for d in growth_data]
            
            # Level line
            line1 = ax.plot(dates, levels, color='#FFD700', linewidth=2.5, 
                          marker='o', markersize=6, label='Level')[0]
            ax.set_ylabel('Level', color='#FFD700', fontsize=10)
            ax.tick_params(axis='y', labelcolor='#FFD700')
            
            # Power line on secondary axis
            ax2 = ax.twinx()
            ax2.set_facecolor('#1a1a2e')
            line2 = ax2.plot(dates, power, color='#3498db', linewidth=2.5,
                           marker='s', markersize=6, label='Power')[0]
            ax2.set_ylabel('Power', color='#3498db', fontsize=10)
            ax2.tick_params(axis='y', labelcolor='#3498db')
            ax2.tick_params(colors='white')
            for spine in ax2.spines.values():
                spine.set_color('#4a4a6a')
            
            ax.set_xlabel('Date', color='white', fontsize=10)
            ax.grid(True, alpha=0.3, color='#4a4a6a')
            plt.xticks(rotation=45)
            
            # Combined legend
            lines = [line1, line2]
            labels = [l.get_label() for l in lines]
            ax.legend(lines, labels, loc='upper left', facecolor='#1a1a2e',
                     edgecolor='white', labelcolor='white')
            
            plt.tight_layout()
            save_path = self._get_save_path("growth")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#16213e', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating growth timeline: {e}")
            return None


# ─── Battle Animation Frames ───

class BattleAnimator:
    """Generate animated battle sequence frames"""
    
    def __init__(self):
        self.style = config.CHART_STYLE if hasattr(config, 'CHART_STYLE') else 'dark_background'
        self.dpi = config.CHART_DPI if hasattr(config, 'CHART_DPI') else 150
    
    def create_battle_frame(self, round_num: int, total_rounds: int, 
                           attacker_hp: int, defender_hp: int,
                           attacker_name: str, defender_name: str,
                           attacker_flag: str, defender_flag: str,
                           action_text: str, damage: int) -> Optional[str]:
        """Create a single battle frame"""
        if not GRAPHICS_AVAILABLE:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6), dpi=self.dpi)
            fig.patch.set_facecolor('#0d0d1a')
            ax.set_facecolor('#0d0d1a')
            ax.axis('off')
            
            # Round indicator
            ax.text(0.5, 0.95, f"⚔️ ROUND {round_num}/{total_rounds}",
                   ha='center', va='top', transform=ax.transAxes,
                   color='gold', fontsize=16, fontweight='bold')
            
            # Attacker side
            atk_ratio = attacker_hp / 100 if attacker_hp <= 100 else 1.0
            atk_color = plt.cm.Reds(1 - atk_ratio * 0.5)
            ax.add_patch(FancyBboxPatch((0.05, 0.3), 0.35, 0.4,
                                        boxstyle="round,pad=0.02",
                                        facecolor=atk_color, edgecolor='red', linewidth=2))
            ax.text(0.225, 0.65, f"{attacker_flag} {attacker_name}",
                   ha='center', va='center', transform=ax.transAxes,
                   color='white', fontsize=12, fontweight='bold')
            ax.text(0.225, 0.45, f"HP: {attacker_hp}",
                   ha='center', va='center', transform=ax.transAxes,
                   color='white', fontsize=14, fontweight='bold')
            
            # VS
            ax.text(0.5, 0.5, "VS",
                   ha='center', va='center', transform=ax.transAxes,
                   color='gold', fontsize=20, fontweight='bold')
            
            # Defender side
            def_ratio = defender_hp / 100 if defender_hp <= 100 else 1.0
            def_color = plt.cm.Blues(1 - def_ratio * 0.5)
            ax.add_patch(FancyBboxPatch((0.6, 0.3), 0.35, 0.4,
                                        boxstyle="round,pad=0.02",
                                        facecolor=def_color, edgecolor='blue', linewidth=2))
            ax.text(0.775, 0.65, f"{defender_flag} {defender_name}",
                   ha='center', va='center', transform=ax.transAxes,
                   color='white', fontsize=12, fontweight='bold')
            ax.text(0.775, 0.45, f"HP: {defender_hp}",
                   ha='center', va='center', transform=ax.transAxes,
                   color='white', fontsize=14, fontweight='bold')
            
            # Action text
            ax.text(0.5, 0.15, action_text,
                   ha='center', va='center', transform=ax.transAxes,
                   color='yellow', fontsize=11, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))
            
            # Damage
            ax.text(0.5, 0.05, f"💥 {damage} DAMAGE!",
                   ha='center', va='center', transform=ax.transAxes,
                   color='red', fontsize=13, fontweight='bold')
            
            plt.tight_layout()
            save_path = os.path.join(tempfile.gettempdir(), f"battle_frame_{round_num}.png")
            plt.savefig(save_path, bbox_inches='tight', facecolor='#0d0d1a', edgecolor='none')
            plt.close(fig)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating battle frame: {e}")
            return None


# ─── Image Effects ───

class ImageEffects:
    """Visual effects using PIL"""
    
    @staticmethod
    def create_progress_bar_image(percent: int, width: int = 400, height: int = 40) -> Optional[str]:
        """Create a visual progress bar image"""
        if not PIL_AVAILABLE:
            return None
        
        try:
            img = Image.new('RGBA', (width, height), (22, 22, 46, 255))
            draw = ImageDraw.Draw(img)
            
            # Background bar
            draw.rounded_rectangle([2, 2, width-2, height-2], radius=height//2, 
                                  fill=(40, 40, 60, 255), outline=(100, 100, 140, 255), width=2)
            
            # Filled portion
            fill_width = int((width - 8) * percent / 100)
            if fill_width > 0:
                # Gradient fill
                for x in range(4, 4 + fill_width):
                    ratio = x / width
                    r = int(100 + 155 * ratio)
                    g = int(200 - 100 * ratio)
                    b = int(100 + 50 * (1 - ratio))
                    draw.line([(x, 6), (x, height-6)], fill=(r, g, b, 255))
            
            # Percentage text
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            except:
                font = ImageFont.load_default()
            
            text = f"{percent}%"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text(((width - text_w) // 2, (height - text_h) // 2 - 2),
                     text, fill=(255, 255, 255, 255), font=font)
            
            save_path = os.path.join(tempfile.gettempdir(), f"progress_{percent}.png")
            img.save(save_path)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating progress bar: {e}")
            return None
    
    @staticmethod
    def create_resource_card(resources: Dict[str, int]) -> Optional[str]:
        """Create a resource card image"""
        if not PIL_AVAILABLE:
            return None
        
        try:
            width, height = 500, 300
            img = Image.new('RGBA', (width, height), (13, 21, 38, 255))
            draw = ImageDraw.Draw(img)
            
            # Header
            draw.rounded_rectangle([10, 10, width-10, 60], radius=10, fill=(26, 26, 46, 255))
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            draw.text((width//2, 35), "💰 RESOURCES", fill=(255, 215, 0, 255), 
                     font=font, anchor="mm")
            
            # Resource items
            resource_items = [
                ("Gold", resources.get('gold', 0), '#FFD700', 80),
                ("Food", resources.get('food', 0), '#FF6B6B', 140),
                ("Gems", resources.get('gems', 0), '#4ECDC4', 200),
                ("Energy", resources.get('energy', 0), '#45B7D1', 260),
            ]
            
            for name, value, color, y in resource_items:
                draw.rounded_rectangle([30, y-20, width-30, y+20], radius=10, 
                                      fill=(26, 26, 46, 255))
                draw.text((50, y), name, fill=color, font=font_small, anchor="lm")
                draw.text((width-50, y), f"{value:,}", fill=(255, 255, 255, 255), 
                         font=font_small, anchor="rm")
            
            save_path = os.path.join(tempfile.gettempdir(), f"resources_{datetime.utcnow().strftime('%s')}.png")
            img.save(save_path)
            return save_path
        
        except Exception as e:
            logger.error(f"Error creating resource card: {e}")
            return None
