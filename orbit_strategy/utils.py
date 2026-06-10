"""
Utility functions for Orbit Wars agent.
"""
import math
from typing import Tuple, List, Optional, NamedTuple

# Constants
SUN_CENTER = (50.0, 50.0)
SUN_RADIUS = 10.0
BOARD_SIZE = 100.0
MAX_FLEET_SPEED = 6.0


class PlanetWrapper(NamedTuple):
    """Named tuple for easier planet field access."""
    id: int
    owner: int
    x: float
    y: float
    radius: float
    ships: int
    production: int


class FleetWrapper(NamedTuple):
    """Named tuple for easier fleet field access."""
    id: int
    owner: int
    x: float
    y: float
    angle: float
    from_planet_id: int
    ships: int


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points."""
    return math.hypot(x2 - x1, y2 - y1)


def angle_to(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate angle from point 1 to point 2 in radians."""
    return math.atan2(y2 - y1, x2 - x1)


def get_fleet_speed(ships: int, max_speed: float = MAX_FLEET_SPEED) -> float:
    """
    Calculate fleet speed based on ship count.
    
    Speed formula: speed = 1.0 + (maxSpeed - 1.0) * (log(ships)/log(1000)) ^ 1.5
    
    Args:
        ships: Number of ships in fleet
        max_speed: Maximum fleet speed (default 6.0)
    
    Returns:
        Fleet speed in units per turn
    """
    if ships <= 1:
        return 1.0
    
    speed_factor = (math.log(ships) / math.log(1000)) ** 1.5
    speed_factor = min(1.0, max(0.0, speed_factor))
    
    return 1.0 + (max_speed - 1.0) * speed_factor


def predict_planet_position(
    initial_x: float,
    initial_y: float,
    angular_velocity: float,
    current_step: int,
    is_orbiting: bool = True
) -> Tuple[float, float]:
    """
    Predict position of an orbiting planet at a given step.
    
    Args:
        initial_x: Initial x position
        initial_y: Initial y position  
        angular_velocity: Rotation speed in radians/turn
        current_step: Current game step
        is_orbiting: Whether planet orbits (False for static planets)
    
    Returns:
        (x, y) predicted position
    """
    if not is_orbiting:
        return initial_x, initial_y
    
    # Calculate orbital radius from center
    dx = initial_x - SUN_CENTER[0]
    dy = initial_y - SUN_CENTER[1]
    orbital_radius = math.hypot(dx, dy)
    
    # Calculate initial angle
    initial_angle = math.atan2(dy, dx)
    
    # Calculate new angle after rotation
    current_angle = initial_angle + angular_velocity * current_step
    
    # Calculate new position
    new_x = SUN_CENTER[0] + orbital_radius * math.cos(current_angle)
    new_y = SUN_CENTER[1] + orbital_radius * math.sin(current_angle)
    
    return new_x, new_y


def check_sun_collision(
    x1: float, y1: float, 
    x2: float, y2: float,
    sun_radius: float = SUN_RADIUS
) -> bool:
    """
    Check if line segment from (x1,y1) to (x2,y2) intersects the sun.
    
    Uses point-to-line-segment distance calculation.
    
    Args:
        x1, y1: Start point of segment
        x2, y2: End point of segment
        sun_radius: Radius of the sun (default 10.0)
    
    Returns:
        True if segment intersects sun, False otherwise
    """
    # Vector from start to end
    dx = x2 - x1
    dy = y2 - y1
    
    length_sq = dx * dx + dy * dy
    
    if length_sq == 0:
        # Single point - check if it's in sun
        return distance(x1, y1, *SUN_CENTER) < sun_radius
    
    # Vector from start to sun center
    sx = SUN_CENTER[0] - x1
    sy = SUN_CENTER[1] - y1
    
    # Project sun onto line, normalized by length squared
    t = max(0, min(1, (sx * dx + sy * dy) / length_sq))
    
    # Closest point on segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Check distance to sun
    return distance(closest_x, closest_y, *SUN_CENTER) < sun_radius


def is_out_of_bounds(x: float, y: float, board_size: float = BOARD_SIZE) -> bool:
    """Check if a point is outside the board boundaries."""
    return x < 0 or x >= board_size or y < 0 or y >= board_size


def estimate_arrival_turns(
    start_x: float, start_y: float,
    target_x: float, target_y: float,
    fleet_ships: int
) -> int:
    """
    Estimate number of turns for fleet to reach target.
    
    Args:
        start_x, start_y: Starting position
        target_x, target_y: Target position
        fleet_ships: Number of ships (affects speed)
    
    Returns:
        Estimated turns to reach target
    """
    dist = distance(start_x, start_y, target_x, target_y)
    speed = get_fleet_speed(fleet_ships)
    
    if speed <= 0:
        return float('inf')
    
    return math.ceil(dist / speed)


def normalize_angle(angle: float) -> float:
    """Normalize angle to range [0, 2*pi)."""
    two_pi = 2 * math.pi
    angle = angle % two_pi
    return angle if angle >= 0 else angle + two_pi


def can_reach_without_sun(
    from_x: float, from_y: float,
    to_x: float, to_y: float
) -> bool:
    """
    Check if fleet can travel from source to target without hitting sun.
    
    Args:
        from_x, from_y: Source position
        to_x, to_y: Target position
    
    Returns:
        True if path is clear, False if sun blocks it
    """
    return not check_sun_collision(from_x, from_y, to_x, to_y)


def calculate_production_value(production: int) -> float:
    """
    Calculate the strategic value of a planet's production.
    
    Higher production planets are exponentially more valuable.
    
    Args:
        production: Planet production rate (1-5)
    
    Returns:
        Strategic value score
    """
    # Exponential weighting for high production
    return production ** 1.5


def get_quadrant(x: float, y: float) -> int:
    """
    Determine which quadrant a point is in.
    
    Quadrants:
        1: Top-right (Q1)
        2: Top-left (Q2)  
        3: Bottom-left (Q3)
        4: Bottom-right (Q4)
    
    Args:
        x, y: Point coordinates
    
    Returns:
        Quadrant number (1-4)
    """
    if x >= 50:
        return 1 if y < 50 else 4
    else:
        return 2 if y < 50 else 3


def parse_observation(obs) -> Tuple[List[PlanetWrapper], List[FleetWrapper], int]:
    """
    Parse observation into structured data.
    
    Handles both dict and object-style observations.
    
    Args:
        obs: Game observation
    
    Returns:
        Tuple of (planets, fleets, player_id)
    """
    if isinstance(obs, dict):
        raw_planets = obs.get("planets", [])
        raw_fleets = obs.get("fleets", [])
        player = obs.get("player", 0)
    else:
        raw_planets = obs.planets if hasattr(obs, 'planets') else []
        raw_fleets = obs.fleets if hasattr(obs, 'fleets') else []
        player = obs.player if hasattr(obs, 'player') else 0
    
    planets = [PlanetWrapper(*p) for p in raw_planets]
    fleets = [FleetWrapper(*f) for f in raw_fleets]
    
    return planets, fleets, player
