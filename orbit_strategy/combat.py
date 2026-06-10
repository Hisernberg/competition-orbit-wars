"""
Combat calculations for Orbit Wars.
Handles combat resolution, threat assessment, and attack planning.
"""
import math
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from .utils import (
    PlanetWrapper, FleetWrapper, distance, angle_to,
    estimate_arrival_turns, get_fleet_speed
)


class CombatCalculator:
    """
    Handles all combat-related calculations.
    
    Combat Rules:
    1. All arriving fleets are grouped by owner
    2. Largest attacker fights second largest (difference survives)
    3. Surviving attackers fight planet garrison
    4. If attackers win, planet changes ownership with surplus as garrison
    """
    
    def __init__(self):
        self.combat_cache = {}
    
    def simulate_combat(
        self,
        planet: PlanetWrapper,
        attacking_fleets: List[Tuple[int, int]]  # List of (owner_id, ship_count)
    ) -> Tuple[int, int]:
        """
        Simulate combat between multiple attackers and a planet.
        
        Args:
            planet: Target planet
            attacking_fleets: List of (owner_id, ship_count) tuples
        
        Returns:
            Tuple of (winning_owner, remaining_ships)
            winning_owner = -1 if no one wins (tie), otherwise owner ID
        """
        if not attacking_fleets:
            return planet.owner, planet.ships
        
        # Group ships by owner
        owner_forces = defaultdict(int)
        for owner_id, ships in attacking_fleets:
            owner_forces[owner_id] += ships
        
        # Sort by strength (descending)
        sorted_forces = sorted(owner_forces.items(), key=lambda x: -x[1])
        
        # If only one attacker
        if len(sorted_forces) == 1:
            attacker_owner, attacker_ships = sorted_forces[0]
            
            if attacker_owner == planet.owner:
                # Reinforcement - add to garrison
                return planet.owner, planet.ships + attacker_ships
            else:
                # Attack planet
                if attacker_ships > planet.ships:
                    # Attacker wins
                    surplus = attacker_ships - planet.ships
                    return attacker_owner, surplus
                elif attacker_ships == planet.ships:
                    # Mutual destruction
                    return -1, 0
                else:
                    # Defender wins
                    remaining = planet.ships - attacker_ships
                    return planet.owner, remaining
        
        # Multiple attackers - largest fights second largest
        while len(sorted_forces) >= 2:
            # Get top two attackers
            owner1, ships1 = sorted_forces[0]
            owner2, ships2 = sorted_forces[1]
            
            # Calculate survivor
            if ships1 > ships2:
                survivor_ships = ships1 - ships2
                survivor_owner = owner1
            elif ships2 > ships1:
                survivor_ships = ships2 - ships1
                survivor_owner = owner2
            else:
                # Tie - both eliminated
                survivor_ships = 0
                survivor_owner = None
            
            # Remove the two fighters
            sorted_forces = sorted_forces[2:]
            
            # Add survivor back if any
            if survivor_ships > 0 and survivor_owner is not None:
                sorted_forces.append((survivor_owner, survivor_ships))
                sorted_forces.sort(key=lambda x: -x[1])
        
        # Now handle final attacker vs planet
        if not sorted_forces:
            # All attackers destroyed each other
            return planet.owner, planet.ships
        
        final_attacker_owner, final_attacker_ships = sorted_forces[0]
        
        if final_attacker_owner == planet.owner:
            # Friendly reinforcement
            return planet.owner, planet.ships + final_attacker_ships
        else:
            # Final assault on planet
            if final_attacker_ships > planet.ships:
                surplus = final_attacker_ships - planet.ships
                return final_attacker_owner, surplus
            elif final_attacker_ships == planet.ships:
                return -1, 0
            else:
                remaining = planet.ships - final_attacker_ships
                return planet.owner, remaining
    
    def calculate_attack_force_needed(
        self,
        planet: PlanetWrapper,
        existing_attackers: List[Tuple[int, int]] = None,
        safety_margin: float = 1.2
    ) -> int:
        """
        Calculate minimum ships needed to capture a planet.
        
        Args:
            planet: Target planet
            existing_attackers: Other fleets already attacking (owner, ships)
            safety_margin: Multiplier for safety buffer (default 1.2 = 20% extra)
        
        Returns:
            Minimum ships needed to guarantee capture
        """
        if existing_attackers is None:
            existing_attackers = []
        
        # Simple case: direct attack
        if not existing_attackers:
            return int(planet.ships * safety_margin) + 1
        
        # Complex case: need to be strongest attacker
        total_enemy_ships = sum(
            ships for owner, ships in existing_attackers 
            if owner != -1  # Assuming -1 is "us" or current player
        )
        
        # Need to beat both enemy attackers and planet
        worst_case = planet.ships + total_enemy_ships
        return int(worst_case * safety_margin) + 1
    
    def assess_threat_level(
        self,
        planet: PlanetWrapper,
        incoming_fleets: List[FleetWrapper],
        my_player_id: int
    ) -> Dict:
        """
        Assess threat level to a planet from incoming fleets.
        
        Args:
            planet: Planet to defend
            incoming_fleets: All fleets heading toward this planet
            my_player_id: My player ID
        
        Returns:
            Dict with threat assessment:
            - threat_level: 'none', 'low', 'medium', 'high', 'critical'
            - enemy_ships: Total enemy ships arriving
            - friendly_ships: Total friendly ships arriving
            - net_deficit: Ships needed to defend
            - arrival_turns: Earliest enemy arrival
        """
        enemy_ships = 0
        friendly_ships = 0
        earliest_enemy_arrival = float('inf')
        
        for fleet in incoming_fleets:
            turns = estimate_arrival_turns(
                fleet.x, fleet.y,
                planet.x, planet.y,
                fleet.ships
            )
            
            if fleet.owner == my_player_id or fleet.owner == planet.owner:
                friendly_ships += fleet.ships
            else:
                enemy_ships += fleet.ships
                earliest_enemy_arrival = min(earliest_enemy_arrival, turns)
        
        # Calculate net situation
        total_defense = planet.ships + friendly_ships
        net_deficit = enemy_ships - total_defense
        
        # Determine threat level
        if enemy_ships == 0:
            threat_level = 'none'
        elif net_deficit <= 0:
            threat_level = 'low'
        elif net_deficit < planet.ships * 0.5:
            threat_level = 'medium'
        elif net_deficit < planet.ships:
            threat_level = 'high'
        else:
            threat_level = 'critical'
        
        return {
            'threat_level': threat_level,
            'enemy_ships': enemy_ships,
            'friendly_ships': friendly_ships,
            'net_deficit': max(0, net_deficit),
            'arrival_turns': earliest_enemy_arrival if earliest_enemy_arrival != float('inf') else -1,
            'can_defend': net_deficit <= 0
        }
    
    def find_weakest_point(
        self,
        enemy_planets: List[PlanetWrapper],
        my_fleets: List[FleetWrapper],
        all_fleets: List[FleetWrapper]
    ) -> Optional[PlanetWrapper]:
        """
        Find the most vulnerable enemy planet to attack.
        
        Considers:
        - Current garrison size
        - Incoming reinforcements (both friendly and enemy)
        - Distance from my planets
        
        Args:
            enemy_planets: List of enemy-owned planets
            my_fleets: My active fleets
            all_fleets: All active fleets
        
        Returns:
            Best target planet or None if no good targets
        """
        best_target = None
        best_score = float('-inf')
        
        for planet in enemy_planets:
            # Find all fleets heading to this planet
            incoming = [
                f for f in all_fleets
                if self._fleet_heading_to(f, planet)
            ]
            
            # Calculate effective defense
            enemy_reinforcements = sum(
                f.ships for f in incoming if f.owner == planet.owner
            )
            enemy_interceptors = sum(
                f.ships for f in incoming 
                if f.owner != planet.owner and f.owner != -1
            )
            
            effective_garrison = planet.ships + enemy_reinforcements
            
            # Score based on vulnerability
            # Lower garrison = better target
            # Closer to my planets = better target
            vulnerability_score = 1000 / (effective_garrison + 1)
            
            # Adjust for interceptor risk
            if enemy_interceptors > 0:
                vulnerability_score *= 0.7  # Penalize contested targets
            
            if vulnerability_score > best_score:
                best_score = vulnerability_score
                best_target = planet
        
        return best_target
    
    def _fleet_heading_to(self, fleet: FleetWrapper, planet: PlanetWrapper) -> bool:
        """Check if a fleet is heading toward a specific planet."""
        # Calculate expected direction to planet
        expected_angle = angle_to(fleet.x, fleet.y, planet.x, planet.y)
        
        # Check if fleet angle matches (with some tolerance)
        angle_diff = abs(fleet.angle - expected_angle)
        angle_diff = min(angle_diff, 2 * math.pi - angle_diff)  # Normalize
        
        return angle_diff < 0.3  # ~17 degree tolerance
    
    def calculate_wave_attack(
        self,
        source_planet: PlanetWrapper,
        target_planet: PlanetWrapper,
        total_ships_available: int,
        waves: int = 2
    ) -> List[Tuple[int, int]]:
        """
        Plan a wave attack to maximize speed and effectiveness.
        
        Smaller fleets move slower but arrive together can overwhelm.
        Split into waves for faster initial impact.
        
        Args:
            source_planet: Launching planet
            target_planet: Target planet
            total_ships_available: Total ships to send
            waves: Number of waves to split into
        
        Returns:
            List of (ship_count, launch_delay) for each wave
        """
        if total_ships_available <= 0:
            return []
        
        # Optimal split: first wave larger for impact, subsequent smaller for speed
        wave_sizes = []
        remaining = total_ships_available
        
        for i in range(waves):
            if i == waves - 1:
                # Last wave gets remainder
                wave_sizes.append(remaining)
            else:
                # Earlier waves get larger portion
                portion = remaining // (waves - i)
                wave_sizes.append(portion)
                remaining -= portion
        
        return [(ships, i * 2) for i, ships in enumerate(wave_sizes)]
