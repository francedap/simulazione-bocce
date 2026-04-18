# Bocce BLE/RSSI Simulation System

A complete software simulation of a **Bocce** (Italian lawn bowls) game system built on top of an IoT architecture:

- **ESP32-C3 nodes** – each boccia advertises its position via BLE
- **Master ESP32-C3** – aggregates RSSI readings, estimates distances
- **Raspberry Pi** – displays the field in real-time and announces the winner

---

## Architecture

```
┌─────────────┐   BLE/RSSI   ┌────────────────┐   Serial/WiFi   ┌──────────────────┐
│ Boccia Node │ ────────────► │ Master ESP32-C3│ ──────────────► │  Raspberry Pi    │
│ (ESP32-C3)  │              │  (aggregator)  │                 │  (GUI + ranking) │
└─────────────┘              └────────────────┘                 └──────────────────┘
```

### Project Structure

```
simulazione-bocce/
├── simulator/
│   ├── __init__.py
│   ├── boccia.py          # Emulates ESP32-C3 BLE node (boccia)
│   ├── master.py          # Emulates Master ESP32-C3
│   ├── raspberry_pi.py    # Emulates Raspberry Pi consumer
│   └── game_engine.py     # Central simulation engine
├── visualization/
│   ├── __init__.py
│   └── gui.py             # Matplotlib-based GUI
├── main.py                # Entry point (CLI)
├── requirements.txt       # Python dependencies
└── README.md
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/francedap/simulazione-bocce.git
cd simulazione-bocce

# Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
# Default: 4 bocce at 60 FPS
python main.py

# Custom: 6 bocce at 30 FPS with debug logging
python main.py --bocce 6 --fps 30 --debug
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--bocce N` | `4` | Number of bocce (2–8) |
| `--fps FPS` | `60` | Target frames per second |
| `--debug` | off | Verbose debug logging |

### Keyboard Controls (in GUI)

| Key | Action |
|-----|--------|
| `Click` (on field) | Launch bocce (or re-launch when all stopped) |
| `R` | Restart game (new positions) |
| `Q` | Quit |

---

## Technical Specifications

### RSSI Model

```
RSSI = TX_POWER − 20 × log₁₀(distance_m)
```

- **TX_POWER** = −40 dBm at 1 m
- **Range**: −40 dBm (very close) to −100 dBm (noise floor)
- **Noise**: Gaussian ± 2.5 dBm to simulate real BLE variability
- **Max range**: ~20 m

### Field Dimensions

| Property | Value |
|----------|-------|
| Width | 4 m |
| Height | 1.5 m |
| Pallino | (2.0 m, 0.75 m) |
| Boccia radius | 2 cm (0.02 m radius, 0.04 m diameter) |

### Physics

- **Friction**: velocity × 0.98 per frame
- **Wall restitution**: 0.75 (energy kept on bounce)
- **Boccia collisions**: elastic with 0.75 damping

---

## Console Output

Every 2 seconds the simulation prints a summary:

```
[Master] t=12.345 | Pallino @ (2.00, 0.75)
  Boccia  0 | pos=(1.234, 0.512) | dist_true=0.831m | dist_est=0.847m | RSSI_pallino=-49.3dBm
  Boccia  1 | pos=(2.891, 1.103) | dist_true=1.019m | dist_est=1.031m | RSSI_pallino=-52.1dBm
  *** Winner (closest): Boccia 0 ***
[RPi] State=playing | Round=1 | Winner=0
  #1 Boccia  0 | dist=0.831m | RSSI=-49.3dBm
  #2 Boccia  1 | dist=1.019m | RSSI=-52.1dBm
```

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or suggestions.

---

## License

This project is licensed under the MIT License.