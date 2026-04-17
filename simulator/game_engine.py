"""
game_engine.py - Central simulation engine.

Coordinates:
  - Boccia physics updates
  - Master data processing
  - Raspberry Pi state management
  - Realistic launch trajectories
"""

import math
import random
import logging
from typing import List, Optional

from simulator.boccia import Boccia, FIELD_WIDTH, FIELD_HEIGHT
from simulator.master import Master
from simulator.raspberry_pi import RaspberryPi

logger = logging.getLogger(__name__)

# Colour palette for bocce (RGB)
BOCCIA_COLORS = [
    (220, 50, 50),    # red
    (50, 100, 220),   # blue
    (50, 180, 50),    # green
    (220, 160, 50),   # yellow/gold
    (160, 50, 180),   # purple
    (50, 190, 190),   # cyan
    (220, 110, 50),   # orange
    (180, 50, 110),   # pink/rose
]

# Launch parameters
MIN_SPEED = 0.5   # m/s
MAX_SPEED = 3.0   # m/s


class GameEngine:
    """
    Main engine that ties together all simulation components.

    Parameters
    ----------
    num_bocce : int
        Number of bocce to simulate (2–8).
    fps : int
        Target frames per second (used to compute dt).
    """

    def __init__(self, num_bocce: int = 4, fps: int = 60):
        self.num_bocce = max(2, min(8, num_bocce))
        self.fps = fps
        self.dt = 1.0 / fps

        self.bocce: List[Boccia] = []
        self.master: Optional[Master] = None
        self.raspberry_pi: Optional[RaspberryPi] = None

        self._frame: int = 0
        self._game_started: bool = False

        self._init_components()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_components(self) -> None:
        """Create bocce, master, and raspberry-pi objects."""
        self.bocce = [
            Boccia(
                player_id=i,
                x=random.uniform(0.1, FIELD_WIDTH - 0.1),
                y=random.uniform(0.1, FIELD_HEIGHT - 0.1),
                color=BOCCIA_COLORS[i % len(BOCCIA_COLORS)],
            )
            for i in range(self.num_bocce)
        ]
        self.master = Master(self.bocce)
        self.raspberry_pi = RaspberryPi(self.num_bocce)
        self._frame = 0
        self._game_started = False
        logger.info("GameEngine initialised with %d bocce.", self.num_bocce)

    # ------------------------------------------------------------------
    # Game control
    # ------------------------------------------------------------------

    def launch_bocce(self) -> None:
        """
        Give each boccia a random initial velocity (realistic launch).

        Velocities are directed towards the centre of the field with
        some angular spread to make the trajectories interesting.
        """
        cx = FIELD_WIDTH / 2
        cy = FIELD_HEIGHT / 2

        for boccia in self.bocce:
            # Angle roughly towards the centre with ±45° spread
            angle_to_centre = math.atan2(cy - boccia.y, cx - boccia.x)
            spread = math.radians(random.uniform(-45, 45))
            angle = angle_to_centre + spread

            speed = random.uniform(MIN_SPEED, MAX_SPEED)
            boccia.launch(speed * math.cos(angle), speed * math.sin(angle))

        self._game_started = True
        self.raspberry_pi.start_round()
        logger.info("Bocce launched!")

    def reset(self) -> None:
        """Reset the entire simulation (new positions, no velocity)."""
        self._init_components()
        logger.info("Game reset.")

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(self) -> dict:
        """
        Advance one simulation frame.

        Returns the latest data packet from the Master (via Raspberry Pi).
        """
        self._frame += 1

        # 1. Update physics for each boccia
        for boccia in self.bocce:
            boccia.update(self.dt)

        # 2. Simple boccia-to-boccia collision detection
        self._resolve_collisions()

        # 3. Master collects and processes RSSI
        packet = self.master.process()

        # 4. Raspberry Pi receives the packet
        self.raspberry_pi.receive(packet)

        # 5. Periodic console log
        if self._frame % (self.fps * 2) == 0:   # every 2 seconds
            self.master.log()
            self.raspberry_pi.log()

        return packet

    # ------------------------------------------------------------------
    # Collision resolution (boccia ↔ boccia)
    # ------------------------------------------------------------------

    def _resolve_collisions(self) -> None:
        """
        Detect and resolve pairwise collisions between bocce.

        Uses a simple elastic collision model with energy loss.
        """
        from simulator.boccia import BOCCIA_RADIUS, WALL_RESTITUTION

        min_dist = 2 * BOCCIA_RADIUS

        for i in range(len(self.bocce)):
            for j in range(i + 1, len(self.bocce)):
                a = self.bocce[i]
                b = self.bocce[j]

                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy)

                if dist < min_dist and dist > 0:
                    # Normalised collision axis
                    nx = dx / dist
                    ny = dy / dist

                    # Separate overlapping balls
                    overlap = min_dist - dist
                    a.x -= nx * overlap / 2
                    a.y -= ny * overlap / 2
                    b.x += nx * overlap / 2
                    b.y += ny * overlap / 2

                    # Project velocities onto collision axis
                    dv_along = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny

                    if dv_along > 0:   # only if approaching
                        # Equal-mass elastic collision impulse with damping
                        impulse = dv_along * WALL_RESTITUTION
                        a.vx -= impulse * nx
                        a.vy -= impulse * ny
                        b.vx += impulse * nx
                        b.vy += impulse * ny

                        a.is_moving = True
                        b.is_moving = True

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def all_stopped(self) -> bool:
        return all(not b.is_moving for b in self.bocce)

    @property
    def game_started(self) -> bool:
        return self._game_started

    @property
    def frame(self) -> int:
        return self._frame

    def __repr__(self) -> str:
        return f"GameEngine(bocce={self.num_bocce}, fps={self.fps}, frame={self._frame})"
