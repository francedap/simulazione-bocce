"""
boccia.py - Emulates a single boccia (ESP32-C3 BLE node).

Each Boccia has:
  - A unique BLE UUID
  - A (x, y) position on the field (metres)
  - A velocity vector (vx, vy) in m/s
  - Transmit power used to derive RSSI towards other nodes

RSSI model (free-space path-loss approximation):
  RSSI = TX_POWER - 20 * log10(distance_m)
  TX_POWER is chosen so that RSSI = -40 dBm at 1 m.
"""

import math
import uuid
import random

# Field dimensions (metres)
FIELD_WIDTH = 4.0
FIELD_HEIGHT = 1.5

# Physics
FRICTION = 0.98            # velocity multiplier per update step
WALL_RESTITUTION = 0.75    # energy kept after wall bounce
MIN_SPEED = 0.001          # m/s below which the ball is considered stopped

# RSSI model
TX_POWER = -40.0           # dBm at 1 m
RSSI_NOISE_STD = 2.5       # dBm standard deviation of Gaussian noise
RSSI_MIN = -100.0          # dBm minimum (noise floor)
BOCCIA_RADIUS = 0.04       # metres (4 cm diameter → 2 cm radius)


class Boccia:
    """
    Emulates an ESP32-C3 BLE node acting as a boccia.

    Parameters
    ----------
    player_id : int
        Numeric identifier for the player/boccia (0-based).
    x : float
        Initial x position in metres (0 … FIELD_WIDTH).
    y : float
        Initial y position in metres (0 … FIELD_HEIGHT).
    color : tuple[int, int, int]
        RGB colour used by the GUI.
    """

    def __init__(self, player_id: int, x: float, y: float, color: tuple):
        self.player_id = player_id
        self.ble_uuid = str(uuid.uuid4())
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.is_moving = False
        self.tx_power = TX_POWER

    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------

    def launch(self, vx: float, vy: float) -> None:
        """Set an initial velocity (launch the boccia)."""
        self.vx = float(vx)
        self.vy = float(vy)
        self.is_moving = True

    def update(self, dt: float) -> None:
        """
        Advance physics by *dt* seconds.

        Applies friction and bounces off field walls.
        """
        if not self.is_moving:
            return

        # Apply friction
        self.vx *= FRICTION
        self.vy *= FRICTION

        # Move
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Wall collisions (left/right)
        if self.x - BOCCIA_RADIUS < 0:
            self.x = BOCCIA_RADIUS
            self.vx = abs(self.vx) * WALL_RESTITUTION
        elif self.x + BOCCIA_RADIUS > FIELD_WIDTH:
            self.x = FIELD_WIDTH - BOCCIA_RADIUS
            self.vx = -abs(self.vx) * WALL_RESTITUTION

        # Wall collisions (top/bottom)
        if self.y - BOCCIA_RADIUS < 0:
            self.y = BOCCIA_RADIUS
            self.vy = abs(self.vy) * WALL_RESTITUTION
        elif self.y + BOCCIA_RADIUS > FIELD_HEIGHT:
            self.y = FIELD_HEIGHT - BOCCIA_RADIUS
            self.vy = -abs(self.vy) * WALL_RESTITUTION

        # Stop if very slow
        speed = math.hypot(self.vx, self.vy)
        if speed < MIN_SPEED:
            self.vx = 0.0
            self.vy = 0.0
            self.is_moving = False

    # ------------------------------------------------------------------
    # RSSI / distance
    # ------------------------------------------------------------------

    def distance_to(self, other: "Boccia") -> float:
        """Euclidean distance in metres to *other* Boccia."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_to_point(self, px: float, py: float) -> float:
        """Euclidean distance in metres to an arbitrary point."""
        return math.hypot(self.x - px, self.y - py)

    def rssi_to(self, other: "Boccia") -> float:
        """
        Simulated RSSI (dBm) towards *other* Boccia.

        Includes Gaussian noise to mimic real-world BLE measurements.
        """
        dist = self.distance_to(other)
        if dist < 0.01:
            dist = 0.01  # avoid log(0)
        rssi = self.tx_power - 20.0 * math.log10(dist)
        rssi += random.gauss(0, RSSI_NOISE_STD)
        return max(RSSI_MIN, rssi)

    def rssi_to_point(self, px: float, py: float) -> float:
        """Simulated RSSI towards an arbitrary point (e.g., the pallino)."""
        dist = self.distance_to_point(px, py)
        if dist < 0.01:
            dist = 0.01
        rssi = self.tx_power - 20.0 * math.log10(dist)
        rssi += random.gauss(0, RSSI_NOISE_STD)
        return max(RSSI_MIN, rssi)

    # ------------------------------------------------------------------
    # Serialisation (sent from ESP32 → Master over BLE)
    # ------------------------------------------------------------------

    def to_ble_packet(self) -> dict:
        """Return a minimal BLE advertisement packet."""
        return {
            "uuid": self.ble_uuid,
            "player_id": self.player_id,
            "tx_power": self.tx_power,
        }

    def __repr__(self) -> str:
        return (
            f"Boccia(id={self.player_id}, "
            f"pos=({self.x:.3f}, {self.y:.3f}), "
            f"v=({self.vx:.3f}, {self.vy:.3f}))"
        )
