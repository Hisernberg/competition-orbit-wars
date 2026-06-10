# 🚀 Orbit Wars AI Agent

A competitive AI bot for the [Orbit Wars](https://www.kaggle.com/competitions/orbit-wars) competition on Kaggle. This agent uses advanced strategic planning, threat assessment, and multi-agent coordination to dominate the galaxy.

## 🎮 Game Overview

Orbit Wars is a real-time strategy game where players:
- Command fleets of ships across a 100x100 continuous space
- Capture planets orbiting a central sun
- Compete in 1v1 or 4-player free-for-all matches
- Aim to control the most ships after 500 turns

## 🏆 Agent Strategy

### Core Features

1. **Dynamic Planet Valuation**
   - Scores planets based on production, distance, and strategic importance
   - Prioritizes high-production planets and defensive positions

2. **Fleet Management**
   - Optimal fleet sizing using logarithmic speed curves
   - Wave attacks for sustained pressure
   - Reinforcement routing for defended planets

3. **Threat Assessment**
   - Tracks enemy fleet trajectories
   - Predicts collision courses and arrival times
   - Implements defensive counter-measures

4. **Comet Exploitation**
   - Early capture of comets at steps 50, 150, 250, 350, 450
   - Quick extraction before comet departure

5. **Multi-Agent Awareness (4-player)**
   - Leader detection and balancing
   - Opportunistic strikes on weakened opponents
   - Avoid over-extension when leading

### Strategic Layers

| Layer | Description |
|-------|-------------|
| **Expansion** | Rapid early-game planet capture |
| **Economy** | Maximize production through smart captures |
| **Military** | Build overwhelming fleet advantages |
| **Defense** | Protect high-value assets |
| **Endgame** | Maximize ship count for victory |

## 📁 Repository Structure

```
orbit-wars-agent/
├── main.py                 # Entry point with agent function
├── orbit_strategy/         # Core strategy module
│   ├── __init__.py
│   ├── planner.py          # Strategic decision making
│   ├── combat.py           # Combat calculations
│   ├── movement.py         # Fleet movement optimization
│   └── utils.py            # Helper functions
├── notebooks/              # Jupyter notebooks for analysis
│   └── strategy_analysis.ipynb
├── tests/                  # Unit tests
│   └── test_agent.py
├── requirements.txt        # Python dependencies
├── submission.tar.gz       # Competition submission archive
└── README.md               # This file
```

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/orbit-wars-agent.git
cd orbit-wars-agent

# Install dependencies
pip install -r requirements.txt

# Install kaggle-environments (required for local testing)
pip install "kaggle-environments>=1.28.0"
```

## 🎯 Quick Start

### Local Testing

```python
from kaggle_environments import make

# Create environment
env = make("orbit_wars", configuration={"seed": 42}, debug=True)

# Run a match against random agent
env.run(["main.py", "random"])

# View results
final = env.steps[-1]
for i, state in enumerate(final):
    print(f"Player {i}: reward={state.reward}, status={state.status}")

# Render the game (in Jupyter)
env.render(mode="ipython", width=800, height=600)
```

### Run Multiple Games

```bash
python tests/test_agent.py
```

## 📤 Submission to Kaggle

### Option 1: Single File

```bash
kaggle competitions submit orbit-wars -f main.py -m "Orbit Strategy v1.0"
```

### Option 2: Multi-File Archive (Recommended)

```bash
# Create submission archive
tar -czf submission.tar.gz main.py orbit_strategy/

# Submit
kaggle competitions submit orbit-wars -f submission.tar.gz -m "Orbit Strategy v1.0"
```

### Option 3: From Notebook

```bash
kaggle competitions submit orbit-wars \
  -k YOUR_USERNAME/orbit-wars-notebook \
  -f submission.tar.gz \
  -v 1 \
  -m "Notebook-based submission"
```

## 🔍 Monitor Progress

```bash
# Check submissions
kaggle competitions submissions orbit-wars

# View episodes for a submission
kaggle competitions episodes <SUBMISSION_ID> -v

# Download replay
kaggle competitions replay <EPISODE_ID> -p ./replays

# Download logs for debugging
kaggle competitions logs <EPISODE_ID> 0 -p ./logs

# Check leaderboard
kaggle competitions leaderboard orbit-wars -s
```

## 🧠 Strategy Deep Dive

### Planet Scoring Algorithm

Planets are scored using a weighted combination of:
- **Production value** (weight: 3.0) - Higher production = more ships
- **Distance cost** (weight: -1.0) - Closer planets preferred
- **Strategic position** (weight: 2.0) - Central/control positions
- **Current ownership** (weight: -5.0) - Avoid attacking own planets
- **Enemy threat level** (weight: -2.0) - Avoid heavily defended targets

### Fleet Speed Optimization

Fleet speed follows: `speed = 1.0 + (maxSpeed - 1.0) * (log(ships)/log(1000))^1.5`

Strategy implications:
- Small fleets (1-50 ships): Send in waves for faster arrival
- Medium fleets (50-500 ships): Good balance of speed and power
- Large fleets (500+ ships): Maximum speed but vulnerable to split attacks

### Combat Resolution

When multiple fleets attack a planet:
1. Group fleets by owner
2. Largest attacker fights second largest (both eliminated, difference survives)
3. Surviving attackers fight planet garrison
4. If attackers win, planet changes ownership

## 📊 Performance Metrics

Track these metrics to evaluate agent performance:
- **Win rate** against various opponents
- **Average ship count** at game end
- **Planet capture rate** per game phase
- **Fleet efficiency** (ships lost vs ships destroyed)
- **Comet capture success rate**

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Machine learning-based opponent prediction
- Advanced comet trajectory optimization
- Coalition detection in 4-player games
- Endgame optimization algorithms

## 📄 License

Apache 2.0 - See LICENSE file for details.

## 🙏 Acknowledgments

- [Kaggle Orbit Wars Competition](https://www.kaggle.com/competitions/orbit-wars)
- Original Planet Wars challenge (2010)
- Kaggle community for strategy discussions

## 📞 Contact

For questions or collaboration opportunities, please open an issue or contact via Kaggle.

---

**Good luck conquering the galaxy! 🌌🚀**
