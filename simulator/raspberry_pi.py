"""
raspberry_pi.py - Emulates the Raspberry Pi consumer node.

Responsibilities:
  - Receive structured data packets from the Master
  - Maintain game state (current round, scores, history)
  - Determine and announce the winner
  - Provide data to the GUI layer
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RaspberryPi:
    """
    Emulates the Raspberry Pi that receives data from the Master.

    Parameters
    ----------
    num_bocce : int
        Total number of bocce in play.
    """

    def __init__(self, num_bocce: int):
        self.num_bocce = num_bocce
        self._current_data: Dict = {}
        self._game_state: str = "waiting"   # waiting | playing | finished
        self._round: int = 0
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def receive(self, packet: Dict) -> None:
        """
        Accept a processed data packet from the Master and update state.

        Parameters
        ----------
        packet : dict
            Output of Master.process().
        """
        self._current_data = packet

        all_stopped = all(not b["is_moving"] for b in packet.get("bocce", []))

        if self._game_state == "playing" and all_stopped:
            self._game_state = "finished"
            self._history.append(
                {
                    "round": self._round,
                    "winner_id": packet.get("winner_id"),
                    "bocce_snapshot": packet.get("bocce", []),
                }
            )
            logger.info(
                "Round %d finished. Winner: Boccia %s",
                self._round,
                packet.get("winner_id"),
            )

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def start_round(self) -> None:
        """Signal that a new round has started."""
        self._round += 1
        self._game_state = "playing"
        logger.info("Round %d started.", self._round)

    def reset(self) -> None:
        """Reset state for a new game."""
        self._current_data = {}
        self._game_state = "waiting"
        self._round = 0
        self._history.clear()
        logger.info("Game reset.")

    # ------------------------------------------------------------------
    # Accessors used by the GUI
    # ------------------------------------------------------------------

    @property
    def game_state(self) -> str:
        return self._game_state

    @property
    def round(self) -> int:
        return self._round

    @property
    def current_data(self) -> Dict:
        return self._current_data

    @property
    def winner_id(self) -> Optional[int]:
        return self._current_data.get("winner_id")

    def get_bocce_sorted(self) -> List[Dict]:
        """Return bocce sorted by distance to the pallino (closest first)."""
        return self._current_data.get("bocce", [])

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def log(self) -> None:
        """Print current game state to the console."""
        print(
            f"[RPi] State={self._game_state} | Round={self._round} | "
            f"Winner={self.winner_id}"
        )
        for i, b in enumerate(self.get_bocce_sorted()):
            rank = i + 1
            print(
                f"  #{rank} Boccia {b['player_id']:2d} | "
                f"dist={b['dist_to_pallino_true']:.3f}m | "
                f"RSSI={b['rssi_to_pallino']:.1f}dBm"
            )

    def __repr__(self) -> str:
        return f"RaspberryPi(state={self._game_state}, round={self._round})"
