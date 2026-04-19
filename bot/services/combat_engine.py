import random
from bot.utils.constants import (
    RANDOM_FACTOR_RANGE, WALL_DEFENSE_REDUCTION_PER_LEVEL,
    PROXIMITY_ATTACK_BONUS, KINGDOM_TRAITS
)


class CombatEngine:
    """Deterministic + RNG battle simulation engine"""
    
    def __init__(self, attacker, defender, is_revenge=False, is_raid=False, is_tutorial=False):
        self.attacker = attacker
        self.defender = defender
        self.is_revenge = is_revenge
        self.is_raid = is_raid
        self.is_tutorial = is_tutorial
        self.rounds = []
        self.winner = None
        self.attacker_losses = {"infantry": 0, "archers": 0, "cavalry": 0}
        self.defender_losses = {"infantry": 0, "archers": 0, "cavalry": 0}
        self.gold_loot = 0
        self.xp_gain = 0
    
    def calculate_distance(self):
        """Manhattan distance between kingdoms on map"""
        return abs(self.attacker.map_x - self.defender.map_x) + abs(self.attacker.map_y - self.defender.map_y)
    
    def calculate_army_power(self, kingdom, is_attacker):
        """Total army power with all modifiers"""
        if not kingdom.army:
            return 0
        
        infantry_power = kingdom.army.infantry * 10
        archer_power = kingdom.army.archers * 12 * 1.1  # Range bonus
        cavalry_power = kingdom.army.cavalry * 18 * 1.2  # Charge bonus
        
        base_power = infantry_power + archer_power + cavalry_power
        
        # Hero bonuses
        hero_bonus = 0.0
        for h in kingdom.heroes:
            if h.unlocked:
                if h.hero_type == "sir_aldric":
                    hero_bonus += (0.15 + 0.03 * (h.level - 1)) * (kingdom.army.infantry / max(kingdom.army.total, 1))
                elif h.hero_type == "lyra":
                    hero_bonus += (0.20 + 0.04 * (h.level - 1)) * (kingdom.army.archers / max(kingdom.army.total, 1))
                elif h.hero_type == "kael":
                    hero_bonus += (0.25 + 0.05 * (h.level - 1)) * (kingdom.army.cavalry / max(kingdom.army.total, 1))
                elif h.hero_type == "morgana":
                    hero_bonus += 0.10  # AoE
                elif h.hero_type == "shadow":
                    hero_bonus += 0.30  # First strike
        
        base_power *= (1 + hero_bonus)
        
        # Kingdom trait bonus
        trait = KINGDOM_TRAITS.get(kingdom.trait, {})
        if is_attacker:
            base_power *= (1 + trait.get("attack_bonus", 0))
            base_power *= (1 + trait.get("attack_penalty", 0))
        else:
            base_power *= (1 + trait.get("defense_bonus", 0))
            base_power *= (1 + trait.get("attack_penalty", 0))
        
        # Revenge bonus
        if self.is_revenge and is_attacker:
            base_power *= 1.10
        
        # Proximity bonus
        distance = self.calculate_distance()
        if distance <= 2:
            base_power *= 1.10
        elif distance <= 4:
            base_power *= 1.05
        
        # Tutorial: attacker gets huge bonus
        if self.is_tutorial and is_attacker:
            base_power *= 3.0
        
        # RNG factor
        rng = random.uniform(*RANDOM_FACTOR_RANGE)
        base_power *= rng
        
        return int(base_power)
    
    def calculate_defense_power(self):
        """Defender's effective defense"""
        if not self.defender.army:
            return {"total_defense": 0, "damage_reduction": 0, "wall_level": self.defender.wall_level}
        
        wall_reduction = self.defender.wall_level * WALL_DEFENSE_REDUCTION_PER_LEVEL
        wall_multiplier = 1 + (self.defender.wall_level * 0.05)
        
        army_defense = (self.defender.army.infantry * 8 +
                       self.defender.army.archers * 5 +
                       self.defender.army.cavalry * 12)
        
        total_defense = army_defense * wall_multiplier
        
        # Damage reduction cap at 75%
        damage_reduction = min(wall_reduction, 0.75)
        
        # Defender trait
        trait = KINGDOM_TRAITS.get(self.defender.trait, {})
        damage_reduction += trait.get("wall_bonus", 0)
        damage_reduction = min(damage_reduction, 0.80)  # Hard cap
        
        # Hero defense bonuses
        hero_defense = 0.0
        for h in self.defender.heroes:
            if h.unlocked:
                hero_defense += 0.05 * h.level
        total_defense *= (1 + hero_defense)
        
        return {
            "total_defense": int(total_defense),
            "damage_reduction": damage_reduction,
            "wall_level": self.defender.wall_level,
        }
    
    def generate_attack_action(self, round_num):
        """Generate flavor text for attack actions"""
        actions = [
            f"Round {round_num} → 🗡 Infantry charges! ⚔️",
            f"Round {round_num} → 🏹 Archers unleash volley! 🎯",
            f"Round {round_num} → 🐎 Cavalry charge! 💨",
            f"Round {round_num} → ⚔️ Combined assault! 🔥",
            f"Round {round_num} → 🗡 Hero leads the charge! 👑",
        ]
        return actions[round_num % len(actions)]
    
    def generate_defense_action(self, round_num):
        """Generate flavor text for defense actions"""
        actions = [
            f"Round {round_num} → 🛡 Wall holds strong! 🧱",
            f"Round {round_num} → 🏹 Defenders counter-attack! ⚔️",
            f"Round {round_num} → 🐎 Cavalry intercepts! 🛡",
            f"Round {round_num} → ⚔️ Desperate stand! 🔥",
        ]
        return actions[round_num % len(actions)]
    
    def calculate_losses(self, kingdom, remaining_hp_ratio):
        """Calculate army losses based on HP ratio"""
        if not kingdom.army:
            return {"infantry": 0, "archers": 0, "cavalry": 0}
        
        loss_ratio = max(0, min(1, 1 - remaining_hp_ratio))
        
        return {
            "infantry": int(kingdom.army.infantry * loss_ratio * random.uniform(0.8, 1.0)),
            "archers": int(kingdom.army.archers * loss_ratio * random.uniform(0.8, 1.0)),
            "cavalry": int(kingdom.army.cavalry * loss_ratio * random.uniform(0.8, 1.0)),
        }
    
    def simulate_battle(self):
        """Generate round-by-round battle log"""
        attack_power = self.calculate_army_power(self.attacker, True)
        defense_data = self.calculate_defense_power()
        defense_power = defense_data["total_defense"]
        damage_reduction = defense_data["damage_reduction"]
        
        effective_attack = int(attack_power * (1 - damage_reduction))
        
        # HP pools
        attack_hp_total = self.attacker.army.total * 10 if self.attacker.army else 0
        defense_hp_total = self.defender.army.total * 10 if self.defender.army else 0
        
        if attack_hp_total <= 0:
            self.winner = "defender"
            self._finalize_results(0, 0)
            return self.generate_battle_report()
        
        if defense_hp_total <= 0:
            self.winner = "attacker"
            self._finalize_results(attack_hp_total, 0)
            return self.generate_battle_report()
        
        attack_hp = attack_hp_total
        defense_hp = defense_hp_total
        
        round_count = random.randint(3, 5)
        
        for round_num in range(1, round_count + 1):
            # Attacker strikes
            atk_damage = max(1, int(effective_attack / round_count * random.uniform(0.8, 1.2)))
            defense_hp -= atk_damage
            
            self.rounds.append({
                "round": round_num,
                "action": self.generate_attack_action(round_num),
                "damage": atk_damage,
                "attacker_remaining": max(attack_hp, 0),
                "defender_remaining": max(defense_hp, 0),
            })
            
            if defense_hp <= 0:
                break
            
            # Defender counter-strikes
            def_damage = max(1, int(defense_power / round_count * random.uniform(0.7, 1.1)))
            attack_hp -= def_damage
            
            self.rounds.append({
                "round": round_num,
                "action": self.generate_defense_action(round_num),
                "damage": def_damage,
                "attacker_remaining": max(attack_hp, 0),
                "defender_remaining": max(defense_hp, 0),
            })
            
            if attack_hp <= 0:
                break
        
        # Determine winner
        if defense_hp <= 0 or (attack_hp > 0 and attack_hp > defense_hp):
            self.winner = "attacker"
        else:
            self.winner = "defender"
        
        # Calculate losses
        attack_hp_ratio = max(0, attack_hp) / attack_hp_total if attack_hp_total > 0 else 0
        defense_hp_ratio = max(0, defense_hp) / defense_hp_total if defense_hp_total > 0 else 0
        
        self.attacker_losses = self.calculate_losses(self.attacker, attack_hp_ratio)
        self.defender_losses = self.calculate_losses(self.defender, defense_hp_ratio)
        
        return self.generate_battle_report()
    
    def _finalize_results(self, attack_hp, defense_hp):
        """Finalize results when one side has no army"""
        attack_hp_total = max(1, self.attacker.army.total * 10) if self.attacker.army else 1
        defense_hp_total = max(1, self.defender.army.total * 10) if self.defender.army else 1
        
        attack_ratio = max(0, attack_hp) / attack_hp_total
        defense_ratio = max(0, defense_hp) / defense_hp_total
        
        self.attacker_losses = self.calculate_losses(self.attacker, attack_ratio)
        self.defender_losses = self.calculate_losses(self.defender, defense_ratio)
    
    def generate_battle_report(self):
        """Format final battle report message"""
        if self.winner == "attacker":
            result_emoji = "🏆 VICTORY!"
            self.gold_loot = int(self.defender.gold * 0.20)  # 20% gold stolen
            self.xp_gain = 100 + (self.defender.level * 20)
        else:
            result_emoji = "💀 DEFEAT!"
            self.gold_loot = 0
            self.xp_gain = 25  # Participation XP
        
        rounds_text = "\n".join(
            f"{r['action']}\n💥 {r['damage']} damage | ⚔️ {r['attacker_remaining']} vs 🛡 {r['defender_remaining']}"
            for r in self.rounds
        ) if self.rounds else "⚡ Instant battle!"
        
        report = f"""⚔️ BATTLE REPORT
━━━━━━━━━━━━━━
{result_emoji}

{self.attacker.name} ⚔️ vs 🛡 {self.defender.name}

⚔️ Rounds:
{rounds_text}

💀 Losses:
Attacker: 🗡-{self.attacker_losses['infantry']} 🏹-{self.attacker_losses['archers']} 🐎-{self.attacker_losses['cavalry']}
Defender: 🗡-{self.defender_losses['infantry']} 🏹-{self.defender_losses['archers']} 🐎-{self.defender_losses['cavalry']}

🏆 Rewards:
💰 +{self.gold_loot:,} Gold
⭐ +{self.xp_gain} XP
━━━━━━━━━━━━━━"""
        
        return {
            "message": report,
            "winner": self.winner,
            "gold_loot": self.gold_loot,
            "xp_gain": self.xp_gain,
            "rounds": self.rounds,
            "attacker_losses": self.attacker_losses,
            "defender_losses": self.defender_losses,
        }
    
    def simulate_raid(self):
        """Quick raid calculation (no rounds)"""
        raid_power = self.attacker.army.total * 5 if self.attacker.army else 0
        defense_power = self.defender.wall_level * 20 + (self.defender.army.total * 3 if self.defender.army else 0)
        
        success_chance = min(0.9, raid_power / (raid_power + defense_power)) if (raid_power + defense_power) > 0 else 0.5
        
        if self.is_tutorial:
            success_chance = 1.0
        
        success = random.random() < success_chance
        
        if success:
            gold_stolen = int(self.defender.gold * 0.15)
            food_stolen = int(self.defender.food * 0.15)
            army_loss = int(self.attacker.army.total * 0.05) if self.attacker.army else 0
            
            report = f"""🏃 RAID SUCCESS!
━━━━━━━━━━━━━━
💰 +{gold_stolen:,} Gold stolen!
🍖 +{food_stolen:,} Food stolen!
💀 Army lost: {army_loss}
━━━━━━━━━━━━━━"""
            
            return {
                "message": report,
                "success": True,
                "gold_stolen": gold_stolen,
                "food_stolen": food_stolen,
                "army_loss": army_loss,
            }
        else:
            army_loss = int(self.attacker.army.total * 0.10) if self.attacker.army else 0
            report = f"""❌ RAID FAIL!
━━━━━━━━━━━━━━
Guard ne pakad liya!
💀 Army lost: {army_loss}
━━━━━━━━━━━━━━"""
            return {
                "message": report,
                "success": False,
                "gold_stolen": 0,
                "food_stolen": 0,
                "army_loss": army_loss,
            }
    
    def simulate_npc_battle(self):
        """Simulate battle against NPC (weaker)"""
        self.is_tutorial = True
        return self.simulate_battle()
