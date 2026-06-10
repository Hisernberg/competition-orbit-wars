"""
Strategic planner for Orbit Wars.
Main decision-making engine that coordinates all game strategies.
"""
import math
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from .utils import (
    PlanetWrapper, FleetWrapper, distance, angle_to,
    parse_observation, get_quadrant, calculate_production_value,
    estimate_arrival_turns, can_reach_without_sun
)
from .combat import CombatCalculator
from .movement import FleetManager


class StrategicPlanner:
    """
    Main strategic decision-making engine.
    
    Coordinates:
    - Expansion strategy
    - Attack planning
    - Defense allocation
    - Resource management
    - Comet exploitation
    - Endgame optimization
    """
    
    # Game phase thresholds
    EARLY_GAME = 100
    MID_GAME = 300
    LATE_GAME = 450
    
    # Comet spawn steps
    COMET_SPAWN_STEPS = {50, 150, 250, 350, 450}
    
    def __init__(self):
        self.combat_calc = CombatCalculator()
        self.fleet_manager = FleetManager()
        self.game_step = 0
        self.my_player_id = 0
        self.previous_observations = []
        
    def decide_actions(self, obs) -> List[List]:
        """
        Main decision function - returns list of moves.
        
        Args:
            obs: Game observation
        
        Returns:
            List of [from_planet_id, angle, num_ships] moves
        """
        # Parse observation
        planets, fleets, player = parse_observation(obs)
        
        # Update state
        self.game_step = len(self.previous_observations)
        self.my_player_id = player
        self.previous_observations.append(obs)
        
        # Categorize planets
        my_planets = [p for p in planets if p.owner == player]
        enemy_planets = [p for p in planets if p.owner != -1 and p.owner != player]
        neutral_planets = [p for p in planets if p.owner == -1]
        
        # Check for comet spawns
        is_comet_spawn = self.game_step in self.COMET_SPAWN_STEPS
        
        # Identify comets
        comet_ids = set()
        if hasattr(obs, 'comet_planet_ids'):
            comet_ids = set(obs.comet_planet_ids)
        elif isinstance(obs, dict) and 'comet_planet_ids' in obs:
            comet_ids = set(obs.get('comet_planet_ids', []))
        
        comets = [p for p in planets if p.id in comet_ids]
        
        # Determine game phase
        game_phase = self._get_game_phase()
        
        # Generate actions based on phase and situation
        moves = []
        
        # Phase-specific strategies
        if game_phase == 'early':
            moves.extend(self._early_game_strategy(
                my_planets, enemy_planets, neutral_planets, 
                comets, fleets, is_comet_spawn
            ))
        elif game_phase == 'mid':
            moves.extend(self._mid_game_strategy(
                my_planets, enemy_planets, neutral_planets,
                comets, fleets
            ))
        else:  # late
            moves.extend(self._late_game_strategy(
                my_planets, enemy_planets, fleets
            ))
        
        # Always check for defensive needs
        defensive_moves = self._handle_defensive_needs(
            my_planets, fleets, enemy_planets
        )
        moves.extend(defensive_moves)
        
        # Validate and deduplicate moves
        moves = self._validate_moves(moves, my_planets)
        
        return moves
    
    def _get_game_phase(self) -> str:
        """Determine current game phase."""
        if self.game_step < self.EARLY_GAME:
            return 'early'
        elif self.game_step < self.MID_GAME:
            return 'mid'
        else:
            return 'late'
    
    def _early_game_strategy(
        self,
        my_planets: List[PlanetWrapper],
        enemy_planets: List[PlanetWrapper],
        neutral_planets: List[PlanetWrapper],
        comets: List[PlanetWrapper],
        fleets: List[FleetWrapper],
        is_comet_spawn: bool
    ) -> List[List]:
        """
        Early game: Focus on expansion and economy.
        
        Priorities:
        1. Capture nearby neutral planets (especially high production)
        2. Grab comets if spawning
        3. Build economic base
        4. Avoid over-extension
        """
        moves = []
        used_ships = defaultdict(int)  # Track ships allocated this turn
        
        # Priority 1: Comets (if spawning)
        if is_comet_spawn and comets:
            comet_moves = self._capture_comets(my_planets, comets, used_ships)
            moves.extend(comet_moves)
        
        # Priority 2: High-value neutral planets
        targets = self.fleet_manager.prioritize_targets(
            my_planets, enemy_planets, neutral_planets,
            self.game_step, is_comet_spawn
        )
        
        # Take top targets based on available forces
        for planet, score in targets[:5]:  # Top 5 targets
            if planet.owner == -1:  # Neutral
                capture_moves = self._plan_capture(
                    planet, my_planets, used_ships
                )
                moves.extend(capture_moves)
        
        return moves
    
    def _mid_game_strategy(
        self,
        my_planets: List[PlanetWrapper],
        enemy_planets: List[PlanetWrapper],
        neutral_planets: List[PlanetWrapper],
        comets: List[PlanetWrapper],
        fleets: List[FleetWrapper]
    ) -> List[List]:
        """
        Mid game: Balance expansion and aggression.
        
        Priorities:
        1. Consolidate position
        2. Attack weak enemies
        3. Continue economic growth
        4. Defend key assets
        """
        moves = []
        used_ships = defaultdict(int)
        
        # Find vulnerable enemy planets
        for enemy_planet in enemy_planets:
            threat = self.combat_calc.assess_threat_level(
                enemy_planet, fleets, self.my_player_id
            )
            
            if threat['threat_level'] in ['low', 'medium']:
                # Good attack opportunity
                attack_moves = self._plan_attack(
                    enemy_planet, my_planets, fleets, used_ships
                )
                moves.extend(attack_moves)
        
        # Still grab valuable neutrals
        for neutral in neutral_planets:
            if neutral.production >= 3:  # Only high production
                if neutral not in [m[0] for m in moves]:  # Not already targeted
                    capture_moves = self._plan_capture(
                        neutral, my_planets, used_ships
                    )
                    moves.extend(capture_moves)
        
        return moves
    
    def _late_game_strategy(
        self,
        my_planets: List[PlanetWrapper],
        enemy_planets: List[PlanetWrapper],
        fleets: List[FleetWrapper]
    ) -> List[List]:
        """
        Late game: Maximize ship count and eliminate enemies.
        
        Priorities:
        1. Eliminate remaining opponents
        2. Maximize total ship production
        3. Defend leading position
        4. Risk-appropriate aggression
        """
        moves = []
        used_ships = defaultdict(int)
        
        # Calculate total ships for each player
        my_total_ships = sum(p.ships for p in my_planets)
        my_total_ships += sum(f.ships for f in fleets if f.owner == self.my_player_id)
        
        enemy_totals = {}
        for enemy_planet in enemy_planets:
            owner = enemy_planet.owner
            if owner not in enemy_totals:
                enemy_totals[owner] = 0
            enemy_totals[owner] += enemy_planet.ships
        
        # Add fleet ships
        for fleet in fleets:
            if fleet.owner != self.my_player_id and fleet.owner != -1:
                if fleet.owner not in enemy_totals:
                    enemy_totals[fleet.owner] = 0
                enemy_totals[fleet.owner] += fleet.ships
        
        # If leading, play defensively
        am_i_leading = all(
            my_total_ships > enemy_ships 
            for enemy_ships in enemy_totals.values()
        )
        
        if am_i_leading:
            # Defensive posture - consolidate and defend
            moves.extend(self._defensive_consolidation(
                my_planets, enemy_planets, fleets, used_ships
            ))
        else:
            # Aggressive posture - attack to catch up
            moves.extend(self._aggressive_push(
                my_planets, enemy_planets, fleets, used_ships
            ))
        
        return moves
    
    def _capture_comets(
        self,
        my_planets: List[PlanetWrapper],
        comets: List[PlanetWrapper],
        used_ships: Dict[int, int]
    ) -> List[List]:
        """Plan comet captures."""
        moves = []
        
        for comet in comets:
            # Find closest planet with enough ships
            best_source = None
            best_distance = float('inf')
            
            for planet in my_planets:
                available = planet.ships - used_ships[planet.id] - 5  # Keep 5 for defense
                if available < 5:  # Need at least 5 ships
                    continue
                
                dist = distance(planet.x, planet.y, comet.x, comet.y)
                
                # Check if path is clear
                if not can_reach_without_sun(planet.x, planet.y, comet.x, comet.y):
                    continue
                
                if dist < best_distance:
                    best_distance = dist
                    best_source = planet
            
            if best_source:
                available = best_source.ships - used_ships[best_source.id] - 5
                ships_to_send = min(available, 15)  # Don't overcommit
                
                if ships_to_send >= 5:
                    angle = angle_to(best_source.x, best_source.y, comet.x, comet.y)
                    moves.append([best_source.id, angle, ships_to_send])
                    used_ships[best_source.id] += ships_to_send
        
        return moves
    
    def _plan_capture(
        self,
        target: PlanetWrapper,
        my_planets: List[PlanetWrapper],
        used_ships: Dict[int, int]
    ) -> List[List]:
        """Plan capture of a neutral planet."""
        moves = []
        
        # Find best source planet
        best_source = None
        best_score = float('-inf')
        
        for planet in my_planets:
            available = planet.ships - used_ships[planet.id] - 3  # Keep minimum defense
            if available <= 0:
                continue
            
            dist = distance(planet.x, planet.y, target.x, target.y)
            
            # Check path
            if not can_reach_without_sun(planet.x, planet.y, target.x, target.y):
                continue
            
            # Score: closer is better, more ships is better
            score = available / (dist + 1)
            
            if score > best_score:
                best_score = score
                best_source = planet
        
        if best_source:
            available = best_source.ships - used_ships[best_source.id] - 3
            
            # Send enough to guarantee capture with buffer
            ships_needed = target.ships + 5
            ships_to_send = min(available, max(ships_needed, 10))
            
            if ships_to_send >= 3:
                angle = angle_to(best_source.x, best_source.y, target.x, target.y)
                moves.append([best_source.id, angle, ships_to_send])
                used_ships[best_source.id] += ships_to_send
        
        return moves
    
    def _plan_attack(
        self,
        target: PlanetWrapper,
        my_planets: List[PlanetWrapper],
        fleets: List[FleetWrapper],
        used_ships: Dict[int, int]
    ) -> List[List]:
        """Plan attack on enemy planet."""
        moves = []
        
        # Calculate force needed
        existing_attackers = [
            (f.owner, f.ships) for f in fleets
            if self._fleet_heading_to(f, target)
        ]
        
        force_needed = self.combat_calc.calculate_attack_force_needed(
            target, existing_attackers, safety_margin=1.3
        )
        
        # Gather forces from multiple planets if needed
        total_committed = 0
        attackers = []
        
        # Sort by distance
        sorted_planets = sorted(
            my_planets,
            key=lambda p: distance(p.x, p.y, target.x, target.y)
        )
        
        for planet in sorted_planets:
            if total_committed >= force_needed:
                break
            
            available = planet.ships - used_ships[planet.id] - 5  # Keep defense
            if available <= 0:
                continue
            
            # Check path
            if not can_reach_without_sun(planet.x, planet.y, target.x, target.y):
                continue
            
            # Commit ships
            to_commit = min(available, force_needed - total_committed + 10)
            if to_commit > 0:
                attackers.append((planet, to_commit))
                total_committed += to_commit
                used_ships[planet.id] += to_commit
        
        # Create attack moves
        for planet, ships in attackers:
            angle = angle_to(planet.x, planet.y, target.x, target.y)
            moves.append([planet.id, angle, ships])
        
        return moves
    
    def _handle_defensive_needs(
        self,
        my_planets: List[PlanetWrapper],
        fleets: List[FleetWrapper],
        enemy_planets: List[PlanetWrapper]
    ) -> List[List]:
        """Handle defensive reinforcement needs."""
        moves = []
        used_ships = defaultdict(int)
        
        for my_planet in my_planets:
            # Check if under threat
            threat = self.combat_calc.assess_threat_level(
                my_planet, fleets, self.my_player_id
            )
            
            if threat['threat_level'] in ['high', 'critical']:
                # Need reinforcements
                ships_needed = threat['net_deficit'] + 10
                
                # Find sources
                for source in my_planets:
                    if source.id == my_planet.id:
                        continue
                    
                    available = source.ships - used_ships[source.id] - 5
                    if available <= 0:
                        continue
                    
                    to_send = min(available, ships_needed)
                    if to_send > 0:
                        angle = angle_to(source.x, source.y, my_planet.x, my_planet.y)
                        moves.append([source.id, angle, to_send])
                        used_ships[source.id] += to_send
                        ships_needed -= to_send
                        
                        if ships_needed <= 0:
                            break
        
        return moves
    
    def _defensive_consolidation(
        self,
        my_planets: List[PlanetWrapper],
        enemy_planets: List[PlanetWrapper],
        fleets: List[FleetWrapper],
        used_ships: Dict[int, int]
    ) -> List[List]:
        """Consolidate forces when leading."""
        moves = []
        
        # Pull back from exposed positions
        # Reinforce key planets
        # Focus on high-production worlds
        
        # Identify key planets to defend (high production)
        key_planets = sorted(my_planets, key=lambda p: -p.production)[:3]
        
        for key_planet in key_planets:
            # Ensure adequate defense
            if key_planet.ships < 20:
                ships_needed = 20 - key_planet.ships
                
                for source in my_planets:
                    if source.id == key_planet.id:
                        continue
                    
                    available = source.ships - used_ships[source.id] - 5
                    if available <= 0:
                        continue
                    
                    to_send = min(available, ships_needed)
                    if to_send > 0:
                        angle = angle_to(source.x, source.y, key_planet.x, key_planet.y)
                        moves.append([source.id, angle, to_send])
                        used_ships[source.id] += to_send
                        ships_needed -= to_send
                        
                        if ships_needed <= 0:
                            break
        
        return moves
    
    def _aggressive_push(
        self,
        my_planets: List[PlanetWrapper],
        enemy_planets: List[PlanetWrapper],
        fleets: List[FleetWrapper],
        used_ships: Dict[int, int]
    ) -> List[List]:
        """All-out attack when behind."""
        moves = []
        
        # Find weakest enemy target
        best_target = self.combat_calc.find_weakest_point(
            enemy_planets,
            [f for f in fleets if f.owner == self.my_player_id],
            fleets
        )
        
        if best_target:
            # Commit significant forces
            attack_moves = self._plan_attack(
                best_target, my_planets, fleets, used_ships
            )
            moves.extend(attack_moves)
        
        return moves
    
    def _fleet_heading_to(self, fleet: FleetWrapper, planet: PlanetWrapper) -> bool:
        """Check if fleet is heading toward a planet."""
        expected_angle = angle_to(fleet.x, fleet.y, planet.x, planet.y)
        angle_diff = abs(fleet.angle - expected_angle)
        angle_diff = min(angle_diff, 2 * math.pi - angle_diff)
        return angle_diff < 0.3
    
    def _validate_moves(
        self,
        moves: List[List],
        my_planets: List[PlanetWrapper]
    ) -> List[List]:
        """Validate and clean up moves."""
        if not moves:
            return []
        
        # Create planet lookup
        planet_dict = {p.id: p for p in my_planets}
        
        # Track ships launched per planet
        launched = defaultdict(int)
        valid_moves = []
        
        for move in moves:
            if len(move) != 3:
                continue
            
            planet_id, angle, ships = move
            
            # Check planet exists and is ours
            if planet_id not in planet_dict:
                continue
            
            planet = planet_dict[planet_id]
            
            # Check we have enough ships
            available = planet.ships - launched[planet_id]
            if ships > available or ships <= 0:
                continue
            
            # Check ships doesn't exceed planet total
            if ships > planet.ships:
                ships = planet.ships
            
            if ships > 0:
                valid_moves.append([planet_id, angle, ships])
                launched[planet_id] += ships
        
        return valid_moves
