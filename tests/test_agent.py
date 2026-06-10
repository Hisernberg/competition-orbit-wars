"""
Unit tests for Orbit Wars agent.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbit_strategy.utils import (
    distance, angle_to, get_fleet_speed, 
    check_sun_collision, can_reach_without_sun,
    PlanetWrapper, FleetWrapper
)
from orbit_strategy.combat import CombatCalculator
from orbit_strategy.movement import FleetManager
from orbit_strategy.planner import StrategicPlanner


def test_distance():
    """Test distance calculation."""
    assert abs(distance(0, 0, 3, 4) - 5.0) < 0.001
    assert abs(distance(50, 50, 50, 50) - 0.0) < 0.001
    print("✓ Distance tests passed")


def test_angle_to():
    """Test angle calculation."""
    import math
    # Right: 0 radians
    assert abs(angle_to(0, 0, 1, 0) - 0.0) < 0.001
    # Down: π/2 radians
    assert abs(angle_to(0, 0, 0, 1) - math.pi/2) < 0.001
    # Left: π radians
    assert abs(abs(angle_to(0, 0, -1, 0)) - math.pi) < 0.001
    print("✓ Angle tests passed")


def test_fleet_speed():
    """Test fleet speed calculation."""
    # Single ship = speed 1.0
    assert abs(get_fleet_speed(1) - 1.0) < 0.001
    
    # Larger fleets are faster
    assert get_fleet_speed(100) > get_fleet_speed(10)
    assert get_fleet_speed(1000) >= get_fleet_speed(100)
    
    # Max speed cap
    speed_1000 = get_fleet_speed(1000)
    assert speed_1000 <= 6.0
    print("✓ Fleet speed tests passed")


def test_sun_collision():
    """Test sun collision detection."""
    # Path that clearly misses sun (sun is at 50,50 with radius 10)
    assert not check_sun_collision(0, 0, 10, 10)
    
    # Path well away from sun
    assert not check_sun_collision(0, 0, 20, 20)
    
    # Path directly through center (50,50) - should collide
    # From (50, 35) to (50, 65) passes through sun at (50,50)
    result = check_sun_collision(50, 35, 50, 65)
    assert result, f"Expected collision for path through center, got {result}"
    
    print("✓ Sun collision tests passed")


def test_combat_simulation():
    """Test combat resolution."""
    calc = CombatCalculator()
    
    # Simple 1v1 attack
    planet = PlanetWrapper(0, 1, 50, 50, 2, 10, 3)  # Owner 1, 10 ships
    attackers = [(0, 15)]  # Player 0 attacks with 15 ships
    
    winner, remaining = calc.simulate_combat(planet, attackers)
    assert winner == 0  # Attacker wins
    assert remaining == 5  # 15 - 10 = 5 survivors
    print("✓ Combat simulation tests passed")


def test_threat_assessment():
    """Test threat level assessment."""
    calc = CombatCalculator()
    
    planet = PlanetWrapper(0, 0, 50, 50, 2, 20, 3)
    
    # No incoming fleets = no threat
    threat = calc.assess_threat_level(planet, [], 0)
    assert threat['threat_level'] == 'none'
    
    # Weak incoming fleet = low threat
    weak_fleet = FleetWrapper(0, 1, 60, 50, 3.14, 1, 5)
    threat = calc.assess_threat_level(planet, [weak_fleet], 0)
    assert threat['threat_level'] in ['none', 'low']
    
    print("✓ Threat assessment tests passed")


def test_planner_initialization():
    """Test strategic planner initialization."""
    planner = StrategicPlanner()
    assert planner is not None
    assert planner.combat_calc is not None
    assert planner.fleet_manager is not None
    print("✓ Planner initialization tests passed")


def test_agent_function():
    """Test main agent function."""
    from main import agent
    
    mock_obs = {
        "player": 0,
        "planets": [
            [0, 0, 25.0, 25.0, 2.0, 10, 3],
            [1, -1, 75.0, 25.0, 1.5, 5, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
        "remainingOverageTime": 60.0
    }
    
    actions = agent(mock_obs)
    assert isinstance(actions, list)
    
    # Validate action format
    for action in actions:
        assert len(action) == 3
        assert isinstance(action[0], int)  # planet_id
        assert isinstance(action[1], float)  # angle
        assert isinstance(action[2], int)  # ships
        assert action[2] > 0  # Must send positive ships
    
    print("✓ Agent function tests passed")


def run_all_tests():
    """Run all unit tests."""
    print("=" * 50)
    print("Running Orbit Wars Agent Tests")
    print("=" * 50)
    
    test_distance()
    test_angle_to()
    test_fleet_speed()
    test_sun_collision()
    test_combat_simulation()
    test_threat_assessment()
    test_planner_initialization()
    test_agent_function()
    
    print("=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
