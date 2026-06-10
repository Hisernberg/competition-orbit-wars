"""
Orbit Wars Strategy Module
Advanced AI agent for the Orbit Wars competition.
"""

from .planner import StrategicPlanner
from .combat import CombatCalculator
from .movement import FleetManager
from .utils import (
    distance,
    angle_to,
    predict_planet_position,
    get_fleet_speed,
    check_sun_collision,
    PlanetWrapper,
    FleetWrapper
)

__version__ = "1.0.0"
__all__ = [
    "StrategicPlanner",
    "CombatCalculator", 
    "FleetManager",
    "distance",
    "angle_to",
    "predict_planet_position",
    "get_fleet_speed",
    "check_sun_collision",
    "PlanetWrapper",
    "FleetWrapper"
]
