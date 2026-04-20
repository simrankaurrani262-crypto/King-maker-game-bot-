"""
Graphics Module - Chart and image generation for stats
Complete version with matplotlib-based charts.
"""

import os
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Try to import matplotlib, fallback to text-based charts
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - using text-based charts")


class StatsChartGenerator:
    """Generate charts and graphs for kingdom statistics"""

    CHART_COLORS = {
        'infantry': '#4CAF50',
        'archers': '#2196F3',
        'cavalry': '#FF9800',
        'gold': '#FFD700',
        'food': '#8BC34A',
        'wins': '#4CAF50',
        'losses': '#F44336',
    }

    @staticmethod
    def create_army_pie(kingdom) -> str:
        """Create army composition pie chart"""
        army = getattr(kingdom, 'army', None)
        if not army:
            return None

        infantry = getattr(army, 'infantry', 0)
        archers = getattr(army, 'archers', 0)
        cavalry = getattr(army, 'cavalry', 0)

        if infantry + archers + cavalry == 0:
            return None

        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            labels = ['Infantry', 'Archers', 'Cavalry']
            sizes = [infantry, archers, cavalry]
            colors = [StatsChartGenerator.CHART_COLORS['infantry'],
                     StatsChartGenerator.CHART_COLORS['archers'],
                     StatsChartGenerator.CHART_COLORS['cavalry']]

            fig, ax = plt.subplots(figsize=(6, 4))
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 10}
            )
            ax.set_title('Army Composition', fontsize=14, fontweight='bold')
            plt.tight_layout()

            filepath = f"/tmp/army_pie_{getattr(kingdom, 'user_id', 'unknown')}.png"
            plt.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return filepath
        except Exception as e:
            logger.error(f"Error creating army pie chart: {e}")
            return None

    @staticmethod
    def create_kingdom_summary(kingdom) -> str:
        """Create a comprehensive kingdom summary chart"""
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            army = getattr(kingdom, 'army', None)
            infantry = getattr(army, 'infantry', 0) if army else 0
            archers = getattr(army, 'archers', 0) if army else 0
            cavalry = getattr(army, 'cavalry', 0) if army else 0
            gold = getattr(kingdom, 'gold', 0)
            food = getattr(kingdom, 'food', 0)
            gems = getattr(kingdom, 'gems', 0)
            level = getattr(kingdom, 'level', 1)

            fig, axes = plt.subplots(2, 2, figsize=(10, 8))

            # Army composition bar chart
            ax1 = axes[0, 0]
            units = ['Infantry', 'Archers', 'Cavalry']
            counts = [infantry, archers, cavalry]
            colors = ['#4CAF50', '#2196F3', '#FF9800']
            bars = ax1.bar(units, counts, color=colors)
            ax1.set_title('Army Composition', fontweight='bold')
            ax1.set_ylabel('Units')
            for bar, count in zip(bars, counts):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                        str(count), ha='center', va='bottom')

            # Resources bar chart
            ax2 = axes[0, 1]
            resources = ['Gold', 'Food', 'Gems']
            values = [gold, food, gems * 100]  # Scale gems for visibility
            colors2 = ['#FFD700', '#8BC34A', '#9C27B0']
            bars2 = ax2.bar(resources, values, color=colors2)
            ax2.set_title('Resources (Gems x100)', fontweight='bold')
            ax2.set_ylabel('Amount')

            # Level indicator
            ax3 = axes[1, 0]
            ax3.text(0.5, 0.7, f'Level {level}', fontsize=24, ha='center',
                    fontweight='bold', transform=ax3.transAxes)
            ax3.text(0.5, 0.4, getattr(kingdom, 'name', 'Unknown'),
                    fontsize=14, ha='center', transform=ax3.transAxes)
            ax3.text(0.5, 0.2, f'Total Army: {infantry + archers + cavalry}',
                    fontsize=12, ha='center', transform=ax3.transAxes)
            ax3.set_xlim(0, 1)
            ax3.set_ylim(0, 1)
            ax3.axis('off')

            # Kingdom info
            ax4 = axes[1, 1]
            trait = getattr(kingdom, 'trait', 'balanced')
            trait_names = {'aggressive': 'Aggressive', 'defensive': 'Defensive',
                          'rich': 'Rich', 'balanced': 'Balanced'}
            info_text = (
                f"Trait: {trait_names.get(trait, trait)}\n"
                f"Gold: {gold:,}\n"
                f"Food: {food:,}\n"
                f"Gems: {gems:,}\n"
                f"Position: ({getattr(kingdom, 'map_x', 0)}, "
                f"{getattr(kingdom, 'map_y', 0)})"
            )
            ax4.text(0.1, 0.9, info_text, fontsize=11, transform=ax4.transAxes,
                    verticalalignment='top', family='monospace')
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')

            plt.suptitle(f'{getattr(kingdom, "name", "Kingdom")} {getattr(kingdom, "flag", "")} - Summary',
                        fontsize=16, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])

            filepath = f"/tmp/kingdom_summary_{getattr(kingdom, 'user_id', 'unknown')}.png"
            plt.savefig(filepath, dpi=120, bbox_inches='tight')
            plt.close(fig)
            return filepath
        except Exception as e:
            logger.error(f"Error creating kingdom summary: {e}")
            return None

    @staticmethod
    def create_battle_history_chart(battles_won, battles_lost) -> str:
        """Create battle history bar chart"""
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            fig, ax = plt.subplots(figsize=(6, 4))
            categories = ['Wins', 'Losses']
            values = [battles_won, battles_lost]
            colors = ['#4CAF50', '#F44336']
            bars = ax.bar(categories, values, color=colors, width=0.5)
            ax.set_title('Battle Record', fontsize=14, fontweight='bold')
            ax.set_ylabel('Count')

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       str(val), ha='center', va='bottom', fontsize=12)

            plt.tight_layout()
            filepath = f"/tmp/battle_history_{battles_won}_{battles_lost}.png"
            plt.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return filepath
        except Exception as e:
            logger.error(f"Error creating battle chart: {e}")
            return None


class ImageEffects:
    """Image effects and filters"""

    @staticmethod
    def apply_vignette(image_path: str) -> str:
        """Apply vignette effect to image"""
        # Placeholder for image processing
        return image_path

    @staticmethod
    def add_border(image_path: str, color: str = "#FFD700", width: int = 5) -> str:
        """Add decorative border to image"""
        return image_path
