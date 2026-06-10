"""
Orbit Wars Agent - Main Entry Point

This is the main submission file for the Orbit Wars competition.
The agent function receives game observations and returns actions.
"""
import sys
import os

# Add the strategy module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orbit_strategy.planner import StrategicPlanner

# Global planner instance (persists across turns)
_planner = None


def agent(obs):
    """
    Main agent function called each turn.
    
    Args:
        obs: Game observation containing:
            - player: Your player ID (0-3)
            - planets: List of [id, owner, x, y, radius, ships, production]
            - fleets: List of [id, owner, x, y, angle, from_planet_id, ships]
            - angular_velocity: Planet rotation speed
            - initial_planets: Starting planet positions
            - comets: Comet group data
            - comet_planet_ids: IDs of comet planets
            - remainingOverageTime: Time budget remaining
    
    Returns:
        List of moves: [[from_planet_id, angle, num_ships], ...]
        
        Example:
            [[0, 1.57, 10], [2, 3.14, 5]]
            - Send 10 ships from planet 0 at angle π/2 (down)
            - Send 5 ships from planet 2 at angle π (left)
    """
    global _planner
    
    # Initialize planner on first call
    if _planner is None:
        _planner = StrategicPlanner()
    
    # Get actions from strategic planner
    try:
        actions = _planner.decide_actions(obs)
        return actions
    except Exception as e:
        # Fallback: return empty list on error
        # This prevents crashes but plays passively
        print(f"Agent error: {e}")
        return []


# For local testing
if __name__ == "__main__":
    # Simple test with mock observation
    mock_obs = {
        "player": 0,
        "planets": [
            [0, 0, 25.0, 25.0, 2.0, 10, 3],  # My home planet
            [1, -1, 75.0, 25.0, 1.5, 5, 2],  # Neutral planet
            [2, -1, 25.0, 75.0, 2.5, 8, 4],  # Another neutral
            [3, -1, 75.0, 75.0, 1.0, 3, 1],  # Low value neutral
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
        "remainingOverageTime": 60.0
    }
    
    print("Testing agent with mock observation...")
    actions = agent(mock_obs)
    
    print(f"Generated {len(actions)} actions:")
    for action in actions:
        print(f"  Planet {action[0]}: send {action[2]} ships at angle {action[1]:.2f} rad")
    
    print("\nTest complete!")
