"""
Combat Engine - Realistic battle simulation with proper formulas
Fixed version with correct trait bonus application and balanced combat.
"""

import random
import logging
from datetime import datetime

from bot.utils.animations import BattleAnimator

logger = logging.getLogger(__name__)


class CombatEngine:
    """
    Realistic combat engine with:
    - Rock-paper-scissors unit type advantages
    - Trait bonuses properly applied
    - Wall defense reduction
    - Hero skill bonuses
    - Critical hit system
    - Morale system
    - Detailed battle logs
    """

    # Unit stats (attack, defense, health, speed)
    UNIT_STATS = {
        "infantry": {"attack": 8, "defense": 12, "health": 15, "speed": 5},
        "archers": {"attack": 15, "defense": 5, "health": 8, "speed": 8},
        "cavalry": {"attack": 12, "defense": 8, "health": 12, "speed": 12},
    }

    # Type advantages: attacker -> defender modifier
    TYPE_ADVANTAGES = {
        "infantry": {"infantry": 1.0, "archers": 1.3, "cavalry": 0.7},
        "archers": {"infantry": 0.8, "archers": 1.0, "cavalry": 1.4},
        "cavalry": {"infantry": 1.3, "archers": 0.7, "cavalry": 1.0},
    }

    # Wall damage reduction per level
    WALL_REDUCTION_PER_LEVEL = 0.03  # 3% per level

    def __init__(self, attacker, defender, is_tutorial=False, is_revenge=False, is_raid=False):
        self.attacker = attacker
        self.defender = defender
        self.is_tutorial = is_tutorial
        self.is_revenge = is_revenge
        self.is_raid = is_raid
        self.rounds = []
        self.animator = BattleAnimator()

    def simulate_battle(self):
        """Run full battle simulation"""
        # Get armies safely
        atk_army = self._get_army_dict(self.attacker)
        def_army = self._get_army_dict(self.defender)

        # Calculate total army sizes
        atk_total = sum(atk_army.values())
        def_total = sum(def_army.values())

        if atk_total == 0:
            return self._create_result("defender", 0, 0, atk_army, def_army, "Attacker has no army!")
        if def_total == 0:
            return self._create_result("attacker", 100, 50, atk_army, def_army, "Defender has no army! Easy win!")

        # Get trait bonuses
        atk_trait = self._get_trait(self.attacker)
        def_trait = self._get_trait(self.defender)

        atk_bonuses = self._calculate_trait_bonuses(atk_trait, "attacker")
        def_bonuses = self._calculate_trait_bonuses(def_trait, "defender")

        # Get wall defense
        wall_level = getattr(self.defender, 'wall_level', 1)
        wall_reduction = wall_level * self.WALL_REDUCTION_PER_LEVEL

        # Get hero bonuses
        atk_hero_bonus = self._calculate_hero_bonus(self.attacker, "attack")
        def_hero_bonus = self._calculate_hero_bonus(self.defender, "defense")

        # Calculate base power
        atk_power = self._calculate_army_power(atk_army, atk_bonuses, atk_hero_bonus, is_attacker=True)
        def_power = self._calculate_army_power(def_army, def_bonuses, def_hero_bonus, is_attacker=False)

        # Apply wall to defender
        def_power = int(def_power * (1 + wall_reduction))

        # Simulate rounds (up to 10 rounds)
        current_atk = dict(atk_army)
        current_def = dict(def_army)
        max_rounds = 5 if self.is_raid else 10

        for round_num in range(1, max_rounds + 1):
            if sum(current_atk.values()) <= 0 or sum(current_def.values()) <= 0:
                break

            round_result = self._simulate_round(
                round_num, current_atk, current_def,
                atk_power, def_power, atk_bonuses, def_bonuses
            )
            self.rounds.append(round_result)

            current_atk = round_result["attacker_remaining"]
            current_def = round_result["defender_remaining"]

        # Determine winner
        atk_remaining_total = sum(current_atk.values())
        def_remaining_total = sum(current_def.values())

        if atk_remaining_total > def_remaining_total:
            winner = "attacker"
        elif def_remaining_total > atk_remaining_total:
            winner = "defender"
        else:
            winner = "defender"  # Defender wins ties (home advantage)

        # Calculate losses
        atk_losses = self._calculate_losses(atk_army, current_atk)
        def_losses = self._calculate_losses(def_army, current_def)

        # Calculate rewards
        gold_loot, xp_gain = self._calculate_rewards(winner, def_army, def_losses)

        # Generate battle message
        message = self._generate_battle_message(
            winner, gold_loot, xp_gain, atk_losses, def_losses,
            self.attacker, self.defender
        )

        # Generate battle animation
        battle_animation = self.animator.create_battle_animation(
            self.attacker, self.defender, winner, self.rounds
        )

        return self._create_result(
            winner, gold_loot, xp_gain, atk_losses, def_losses,
            message, battle_animation
        )

    def simulate_raid(self):
        """Quick raid simulation (simplified, 1 round)"""
        atk_army = self._get_army_dict(self.attacker)
        def_army = self._get_army_dict(self.defender)

        atk_total = sum(atk_army.values())
        def_total = sum(def_army.values())

        # Quick power comparison
        atk_trait = self._get_trait(self.attacker)
        def_trait = self._get_trait(self.defender)

        atk_power = self._calculate_quick_power(atk_army, atk_trait)
        def_power = self._calculate_quick_power(def_army, def_trait)

        # Raid: max 15% resources stolen
        success = atk_power > def_power * 0.6

        defender_gold = getattr(self.defender, 'gold', 0)
        defender_food = getattr(self.defender, 'food', 0)

        if success:
            gold_stolen = int(defender_gold * 0.15)
            food_stolen = int(defender_food * 0.10)
            army_loss = max(1, int(atk_total * 0.05))
        else:
            gold_stolen = 0
            food_stolen = 0
            army_loss = max(1, int(atk_total * 0.15))

        # Generate raid message
        if success:
            message = (
                f"🏃 **RAID SUCCESSFUL!**\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"💰 +{gold_stolen:,} Gold stolen!\n"
                f"🍖 +{food_stolen:,} Food stolen!\n"
                f"💀 Army loss: {army_loss} units\n\n"
                f"@{getattr(self.defender, 'name', 'Unknown')} ka thoda maal chura liya!"
            )
        else:
            message = (
                f"❌ **RAID FAILED!**\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"Defender zyada strong tha!\n"
                f"💀 Army loss: {army_loss} units\n\n"
                f"Agli baar zyada army leke jao!"
            )

        return {
            "success": success,
            "gold_stolen": gold_stolen,
            "food_stolen": food_stolen,
            "army_loss": army_loss,
            "message": message,
        }

    def _get_army_dict(self, kingdom):
        """Safely get army as a dictionary"""
        army = getattr(kingdom, 'army', None)
        if army:
            return {
                "infantry": getattr(army, 'infantry', 0),
                "archers": getattr(army, 'archers', 0),
                "cavalry": getattr(army, 'cavalry', 0),
            }
        return {"infantry": 0, "archers": 0, "cavalry": 0}

    def _get_trait(self, kingdom):
        """Safely get kingdom trait"""
        return getattr(kingdom, 'trait', 'balanced')

    def _calculate_trait_bonuses(self, trait, role):
        """Calculate combat bonuses from traits"""
        bonuses = {"attack": 1.0, "defense": 1.0, "morale": 1.0}

        if trait == "aggressive":
            if role == "attacker":
                bonuses["attack"] = 1.25
                bonuses["morale"] = 1.15
            else:
                bonuses["attack"] = 1.10
        elif trait == "defensive":
            if role == "defender":
                bonuses["defense"] = 1.30
                bonuses["morale"] = 1.10
            else:
                bonuses["defense"] = 1.15
        elif trait == "rich":
            bonuses["morale"] = 1.10  # Rich kingdoms have better equipped soldiers
        elif trait == "balanced":
            bonuses["attack"] = 1.08
            bonuses["defense"] = 1.08

        return bonuses

    def _calculate_hero_bonus(self, kingdom, bonus_type):
        """Calculate hero skill bonus"""
        heroes = getattr(kingdom, 'heroes', [])
        if not heroes:
            return 1.0

        bonus = 1.0
        for hero in heroes:
            if getattr(hero, 'unlocked', False):
                level = getattr(hero, 'level', 0)
                hero_type = getattr(hero, 'hero_type', '')

                if bonus_type == "attack" and hero_type in ['arthur', 'lancelot']:
                    bonus += 0.05 * level
                elif bonus_type == "defense" and hero_type in ['merlin', 'guinevere']:
                    bonus += 0.05 * level
                elif bonus_type == "attack" and hero_type == 'morgana':
                    bonus += 0.08 * level

        return bonus

    def _calculate_army_power(self, army_dict, bonuses, hero_bonus, is_attacker=True):
        """Calculate total army power with all modifiers"""
        total = 0
        for unit_type, count in army_dict.items():
            if count <= 0:
                continue
            stats = self.UNIT_STATS.get(unit_type, {"attack": 10, "defense": 10, "health": 10})

            if is_attacker:
                unit_power = stats["attack"] * stats["speed"] * count
            else:
                unit_power = stats["defense"] * stats["health"] * count

            total += unit_power

        # Apply bonuses
        if is_attacker:
            total = int(total * bonuses["attack"] * hero_bonus)
        else:
            total = int(total * bonuses["defense"] * hero_bonus)

        return total

    def _calculate_quick_power(self, army_dict, trait):
        """Quick power calculation for raids"""
        total = 0
        for unit_type, count in army_dict.items():
            stats = self.UNIT_STATS.get(unit_type, {"attack": 10, "defense": 10, "health": 10})
            total += (stats["attack"] + stats["defense"]) * count

        # Apply simple trait bonus
        trait_multipliers = {"aggressive": 1.15, "defensive": 1.10, "rich": 1.05, "balanced": 1.08}
        total = int(total * trait_multipliers.get(trait, 1.0))

        return total

    def _simulate_round(self, round_num, atk_army, def_army, atk_power, def_power, atk_bonuses, def_bonuses):
        """Simulate a single combat round"""
        atk_total = sum(atk_army.values())
        def_total = sum(def_army.values())

        if atk_total == 0 or def_total == 0:
            return {
                "round": round_num,
                "attacker_remaining": dict(atk_army),
                "defender_remaining": dict(def_army),
                "description": "Battle over!"
            }

        # Calculate casualties based on power ratio
        power_ratio = atk_power / (def_power + 1)  # +1 to avoid division by zero

        # Attacker casualties (defender fighting back)
        def_casualty_rate = min(0.35, 0.15 * (1 / max(power_ratio, 0.5)))
        atk_casualty_rate = min(0.35, 0.15 * power_ratio)

        # Apply morale
        def_casualty_rate *= atk_bonuses.get("morale", 1.0)
        atk_casualty_rate *= def_bonuses.get("morale", 1.0)

        # Random variation (+-20%)
        def_casualty_rate *= random.uniform(0.8, 1.2)
        atk_casualty_rate *= random.uniform(0.8, 1.2)

        # Critical hit chance (10%)
        if random.random() < 0.1:
            def_casualty_rate *= 1.5  # 50% more damage

        # Apply type advantages
        def_remaining = {}
        for unit_type in def_army:
            advantage = self.TYPE_ADVANTAGES.get("infantry", {}).get(unit_type, 1.0)
            loss = int(def_army[unit_type] * def_casualty_rate * advantage)
            def_remaining[unit_type] = max(0, def_army[unit_type] - loss)

        atk_remaining = {}
        for unit_type in atk_army:
            loss = int(atk_army[unit_type] * atk_casualty_rate)
            atk_remaining[unit_type] = max(0, atk_army[unit_type] - loss)

        description = f"Round {round_num}: Both sides exchange blows!"
        if random.random() < 0.1:
            description = f"Round {round_num}: Critical hit! Heavy damage!"

        return {
            "round": round_num,
            "attacker_remaining": atk_remaining,
            "defender_remaining": def_remaining,
            "description": description,
        }

    def _calculate_losses(self, original, remaining):
        """Calculate unit losses"""
        return {
            "infantry": max(0, original.get("infantry", 0) - remaining.get("infantry", 0)),
            "archers": max(0, original.get("archers", 0) - remaining.get("archers", 0)),
            "cavalry": max(0, original.get("cavalry", 0) - remaining.get("cavalry", 0)),
        }

    def _calculate_rewards(self, winner, def_army, def_losses):
        """Calculate gold loot and XP gain"""
        if winner != "attacker":
            return 0, 10  # Participation XP

        def_total = sum(def_army.values())
        total_losses = sum(def_losses.values())

        # Gold loot based on defender's total army
        gold_loot = min(5000, max(100, def_total * 10 + total_losses * 5))

        # Tutorial bonus
        if self.is_tutorial:
            gold_loot = min(gold_loot, 500)

        # Revenge bonus
        if self.is_revenge:
            gold_loot = int(gold_loot * 1.5)

        # XP gain
        xp_gain = min(500, max(25, total_losses * 2 + 50))
        if self.is_tutorial:
            xp_gain = min(xp_gain, 100)

        return gold_loot, xp_gain

    def _generate_battle_message(self, winner, gold_loot, xp_gain, atk_losses, def_losses, attacker, defender):
        """Generate formatted battle result message"""
        atk_name = getattr(attacker, 'name', 'Unknown')
        def_name = getattr(defender, 'name', 'Unknown')
        atk_flag = getattr(attacker, 'flag', '')
        def_flag = getattr(defender, 'flag', '')

        # Battle animation frames
        animation_frames = [
            "⚔️", "🔥", "💥", "⚡", "🗡",
        ]
        battle_anim = " ".join(animation_frames)

        if winner == "attacker":
            title = f"🏆 **VICTORY!** {battle_anim}"
            result_text = (
                f"✅ {atk_name} {atk_flag} ne {def_name} {def_flag} ko hara diya!\n"
                f"💰 +{gold_loot:,} Gold looted!\n"
                f"⭐ +{xp_gain} XP gained!"
            )
        else:
            title = f"💀 **DEFEAT!** {battle_anim}"
            result_text = (
                f"❌ {atk_name} {atk_flag} ka hamla fail ho gaya!\n"
                f"{def_name} {def_flag} ne successfully defend kiya!\n"
                f"⭐ +{xp_gain} XP (participation)"
            )

        losses_text = (
            f"\n\n📊 **Battle Report:**\n"
            f"━━━━━━━━━━━━━━\n"
            f"⚔️ Attacker Losses:\n"
            f"   🗡 Infantry: -{atk_losses.get('infantry', 0)}\n"
            f"   🏹 Archers: -{atk_losses.get('archers', 0)}\n"
            f"   🐎 Cavalry: -{atk_losses.get('cavalry', 0)}\n\n"
            f"🛡 Defender Losses:\n"
            f"   🗡 Infantry: -{def_losses.get('infantry', 0)}\n"
            f"   🏹 Archers: -{def_losses.get('archers', 0)}\n"
            f"   🐎 Cavalry: -{def_losses.get('cavalry', 0)}"
        )

        message = f"{title}\n━━━━━━━━━━━━━━\n\n{result_text}{losses_text}"

        if self.is_revenge:
            message += "\n\n🔥 **REVENGE BONUS!** 1.5x loot!"

        return message

    def _create_result(self, winner, gold_loot, xp_gain, atk_losses, def_losses, message, animation=""):
        """Create standardized battle result"""
        return {
            "winner": winner,
            "gold_loot": gold_loot,
            "xp_gain": xp_gain,
            "attacker_losses": atk_losses,
            "defender_losses": def_losses,
            "message": message,
            "animation": animation,
            "rounds": self.rounds,
        }
