"""
Fleet management and movement optimization for Orbit Wars.
Handles fleet routing, path planning, and collision avoidance.
"""
import math
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from .utils import (
    PlanetWrapper, FleetWrapper, distance, angle_to,
    get_fleet_speed, check_sun_collision, can_reach_without_sun,
    estimate_arrival_turns, SUN_CENTER, SUN_RADIUS
)


class FleetManager:
    """
    Manages fleet movements, routing, and logistics.
    
    Responsibilities:
    - Calculate optimal launch angles
    - Plan multi-planet attacks
    - Manage reinforcement routes
    - Avoid sun collisions
    - Optimize fleet sizes for speed
    """
    
    def __init__(self):
        self.active_routes = {}  # route_id -> route_info
        self.pending_launches = []  # Planned launches for this turn
    
    def calculate_optimal_angle(
        self,
        from_planet: PlanetWrapper,
        target_position: Tuple[float, float],
        avoid_sun: bool = True
    ) -> Optional[float]:
        """
        Calculate optimal launch angle to reach target.
        
        Args:
            from_planet: Source planet
            target_position: (x, y) target coordinates
            avoid_sun: Whether to avoid sun collision
        
        Returns:
            Optimal angle in radians, or None if no valid path
        """
        base_angle = angle_to(from_planet.x, from_planet.y, *target_position)
        
        if not avoid_sun:
            return base_angle
        
        # Check if direct path hits sun
        if can_reach_without_sun(from_planet.x, from_planet.y, *target_position):
            return base_angle
        
        # Need to route around sun - try angled paths
        best_angle = None
        best_distance = float('inf')
        
        # Try angles offset from direct path
        for offset in [0.3, -0.3, 0.5, -0.5, 0.8, -0.8]:
            test_angle = base_angle + offset
            
            # Calculate endpoint at same distance as target
            dist_to_target = distance(from_planet.x, from_planet.y, *target_position)
            test_x = from_planet.x + dist_to_target * math.cos(test_angle)
            test_y = from_planet.y + dist_to_target * math.sin(test_angle)
            
            # Check if this path avoids sun
            if can_reach_without_sun(from_planet.x, from_planet.y, test_x, test_y):
                # Calculate how close this gets us to target
                endpoint_dist = distance(test_x, test_y, *target_position)
                if endpoint_dist < best_distance:
                    best_distance = endpoint_dist
                    best_angle = test_angle
        
        return best_angle
    
    def plan_reinforcement(
        self,
        source_planets: List[PlanetWrapper],
        target_planet: PlanetWrapper,
        min_ships_needed: int,
        max_ships_per_fleet: int = 50
    ) -> List[Tuple[int, float, int]]:
        """
        Plan reinforcement fleet(s) to defend a planet.
        
        Args:
            source_planets: Available friendly planets to send from
            target_planet: Planet to reinforce
            min_ships_needed: Minimum total ships to send
            max_ships_per_fleet: Maximum ships per fleet for speed
        
        Returns:
            List of (planet_id, angle, ship_count) moves
        """
        moves = []
        ships_remaining = min_ships_needed
        
        # Sort by distance (closest first for faster arrival)
        sorted_sources = sorted(
            source_planets,
            key=lambda p: distance(p.x, p.y, target_planet.x, target_planet.y)
        )
        
        for planet in sorted_sources:
            if ships_remaining <= 0:
                break
            
            # Can only send what we have minus minimum defense
            available = max(0, planet.ships - 5)  # Keep 5 for defense
            if available <= 0:
                continue
            
            # Calculate how many to send
            to_send = min(available, ships_remaining, max_ships_per_fleet)
            if to_send <= 0:
                continue
            
            # Calculate angle
            angle = angle_to(planet.x, planet.y, target_planet.x, target_planet.y)
            
            moves.append((planet.id, angle, to_send))
            ships_remaining -= to_send
        
        return moves
    
    def optimize_fleet_size(
        self,
        total_ships: int,
        target_distance: float,
        urgency: str = 'normal'
    ) -> List[int]:
        """
        Determine optimal fleet size split for a mission.
        
        Larger fleets are faster but less flexible.
        Split into multiple fleets for:
        - Faster initial impact (smaller fleets can be sent immediately)
        - Redundancy (if one fleet is intercepted)
        - Wave attacks
        
        Args:
            total_ships: Total ships available
            target_distance: Distance to target
            urgency: 'low', 'normal', 'high', 'critical'
        
        Returns:
            List of fleet sizes
        """
        if total_ships <= 0:
            return []
        
        # Urgency affects split strategy
        urgency_multipliers = {
            'low': 0.5,      # Fewer, larger fleets
            'normal': 1.0,   # Balanced
            'high': 1.5,     # More splits
            'critical': 2.0  # Maximum splits for speed
        }
        
        split_factor = urgency_multipliers.get(urgency, 1.0)
        
        # Determine number of fleets
        if total_ships <= 20:
            num_fleets = 1
        elif total_ships <= 50:
            num_fleets = min(2, int(1 * split_factor))
        elif total_ships <= 100:
            num_fleets = min(3, int(2 * split_factor))
        elif total_ships <= 200:
            num_fleets = min(4, int(2 * split_factor))
        else:
            num_fleets = min(5, int(3 * split_factor))
        
        num_fleets = max(1, num_fleets)
        
        # Split ships
        fleet_sizes = []
        remaining = total_ships
        
        for i in range(num_fleets):
            if i == num_fleets - 1:
                fleet_sizes.append(remaining)
            else:
                size = remaining // (num_fleets - i)
                fleet_sizes.append(size)
                remaining -= size
        
        return fleet_sizes
    
    def calculate_intercept_course(
        self,
        interceptor_planet: PlanetWrapper,
        target_fleet: FleetWrapper,
        intercept_point: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, int]]:
        """
        Calculate intercept course for enemy fleet.
        
        Args:
            interceptor_planet: Planet to launch from
            target_fleet: Enemy fleet to intercept
            intercept_point: Optional specific point to intercept at
        
        Returns:
            Tuple of (angle, ships_needed) or None if impossible
        """
        # Predict where target fleet will be
        if intercept_point:
            target_x, target_y = intercept_point
        else:
            # Intercept along target's current trajectory
            # Simple prediction: assume constant velocity
            speed = get_fleet_speed(target_fleet.ships)
            turns_to_intercept = 10  # Assume 10 turns for now
            
            target_x = target_fleet.x + speed * turns_to_intercept * math.cos(target_fleet.angle)
            target_y = target_fleet.y + speed * turns_to_intercept * math.sin(target_fleet.angle)
        
        # Check if we can reach without hitting sun
        if not can_reach_without_sun(
            interceptor_planet.x, interceptor_planet.y,
            target_x, target_y
        ):
            return None
        
        # Calculate angle
        angle = angle_to(interceptor_planet.x, interceptor_planet.y, target_x, target_y)
        
        # Estimate ships needed (at least match target fleet)
        ships_needed = target_fleet.ships + 5  # Small buffer
        
        if ships_needed > interceptor_planet.ships:
            return None  # Don't have enough ships
        
        return (angle, ships_needed)
    
    def find_valid_launch_positions(
        self,
        planet: PlanetWrapper,
        all_planets: List[PlanetWrapper],
        all_fleets: List[FleetWrapper]
    ) -> Set[Tuple[float, float]]:
        """
        Find valid positions to launch fleets that won't immediately collide.
        
        Args:
            planet: Launch planet
            all_planets: All planets on board
            all_fleets: All active fleets
        
        Returns:
            Set of (angle, distance) tuples for safe launch vectors
        """
        safe_angles = set()
        
        # Sample angles around the planet
        for angle_step in range(0, 360, 15):  # Every 15 degrees
            angle = math.radians(angle_step)
            
            # Check if this direction hits any nearby planet
            test_distance = planet.radius + 5  # Just outside planet
            test_x = planet.x + test_distance * math.cos(angle)
            test_y = planet.y + test_distance * math.sin(angle)
            
            is_safe = True
            
            # Check collision with other planets
            for other in all_planets:
                if other.id == planet.id:
                    continue
                
                if distance(test_x, test_y, other.x, other.y) < other.radius:
                    is_safe = False
                    break
            
            # Check collision with sun
            if distance(test_x, test_y, *SUN_CENTER) < SUN_RADIUS:
                is_safe = False
            
            if is_safe:
                safe_angles.add(angle)
        
        return safe_angles
    
    def calculate_supply_line_efficiency(
        self,
        source: PlanetWrapper,
        target: PlanetWrapper,
        all_planets: List[PlanetWrapper]
    ) -> float:
        """
        Calculate efficiency of a supply line between two planets.
        
        Considers:
        - Direct distance
        - Alternative routes via intermediate planets
        - Sun obstruction
        
        Args:
            source: Starting planet
            target: Destination planet
            all_planets: All planets for potential waypoints
        
        Returns:
            Efficiency score (higher = better route)
        """
        direct_dist = distance(source.x, source.y, target.x, target.y)
        
        # Base efficiency inversely proportional to distance
        base_efficiency = 1000 / (direct_dist + 1)
        
        # Penalty if sun blocks direct route
        if not can_reach_without_sun(source.x, source.y, target.x, target.y):
            base_efficiency *= 0.6  # 40% penalty
        
        # Bonus if there are friendly waypoints
        midpoint_x = (source.x + target.x) / 2
        midpoint_y = (source.y + target.y) / 2
        
        waypoint_bonus = 0
        for planet in all_planets:
            if planet.owner == source.owner:
                dist_to_midpoint = distance(planet.x, planet.y, midpoint_x, midpoint_y)
                if dist_to_midpoint < 20:  # Within 20 units of midpoint
                    waypoint_bonus += 0.1
        
        return base_efficiency * (1 + waypoint_bonus)
    
    def prioritize_targets(
        self,
        my_planets: List[PlanetWrapper],
        enemy_planets: List[PlanetWrapper],
        neutral_planets: List[PlanetWrapper],
        game_step: int,
        is_comet_spawn_step: bool
    ) -> List[Tuple[PlanetWrapper, float]]:
        """
        Prioritize all potential targets by strategic value.
        
        Args:
            my_planets: My owned planets
            enemy_planets: Enemy owned planets
            neutral_planets: Neutral planets
            game_step: Current game step
            is_comet_spawn_step: Whether comets are spawning this turn
        
        Returns:
            List of (planet, priority_score) sorted by priority
        """
        targets = []
        
        # Score neutral planets (expansion priority)
        for planet in neutral_planets:
            score = self._score_neutral_planet(
                planet, my_planets, game_step, is_comet_spawn_step
            )
            targets.append((planet, score))
        
        # Score enemy planets (attack priority)
        for planet in enemy_planets:
            score = self._score_enemy_planet(planet, my_planets)
            targets.append((planet, score))
        
        # Sort by score descending
        targets.sort(key=lambda x: -x[1])
        
        return targets
    
    def _score_neutral_planet(
        self,
        planet: PlanetWrapper,
        my_planets: List[PlanetWrapper],
        game_step: int,
        is_comet_spawn_step: bool
    ) -> float:
        """Score a neutral planet for capture priority."""
        # Production value (most important)
        production_value = planet.production * 10
        
        # Distance penalty (average distance to my planets)
        if my_planets:
            avg_distance = sum(
                distance(planet.x, planet.y, p.x, p.y)
                for p in my_planets
            ) / len(my_planets)
            distance_penalty = avg_distance * 0.3
        else:
            distance_penalty = 0
        
        # Comet bonus (if this is a comet and spawn step)
        comet_bonus = 0
        if is_comet_spawn_step and planet.radius < 2:  # Comets have radius 1
            comet_bonus = 15  # High priority for early capture
        
        # Current ships (less ships = easier capture)
        capture_ease = (50 - planet.ships) * 0.2  # Bonus for low garrison
        
        return production_value - distance_penalty + comet_bonus + capture_ease
    
    def _score_enemy_planet(
        self,
        planet: PlanetWrapper,
        my_planets: List[PlanetWrapper]
    ) -> float:
        """Score an enemy planet for attack priority."""
        # Production value (denied to enemy)
        production_value = planet.production * 8
        
        # Distance from my planets
        if my_planets:
            min_distance = min(
                distance(planet.x, planet.y, p.x, p.y)
                for p in my_planets
            )
            distance_penalty = min_distance * 0.4
        else:
            distance_penalty = 100  # Very hard to attack without bases
        
        # Garrison weakness
        weakness_bonus = (30 - planet.ships) * 0.3
        
        # Strategic position (closer to center = more valuable)
        dist_to_center = distance(planet.x, planet.y, *SUN_CENTER)
        position_bonus = max(0, (30 - dist_to_center)) * 0.2
        
        return production_value - distance_penalty + weakness_bonus + position_bonus
