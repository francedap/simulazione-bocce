"""
master.py - Emulates the Master ESP32-C3 node.

Responsibilities:
  - Receive RSSI readings from all bocce nodes
  - Calculate pairwise distances using the inverse RSSI formula
  - Estimate positions relative to the pallino
  - Serialise a structured data packet for the Raspberry Pi
"""

import math
import time
from typing import List, Dict

from simulator.boccia import Boccia, RSSI_MIN, TX_POWER

# Pallino (jack) fixed position
PALLINO_X = 2.0   # metres
PALLINO_Y = 0.75  # metres


def rssi_to_distance(rssi: float, tx_power: float = TX_POWER) -> float:
    """
    Estimate distance from an RSSI reading.

    Inverse of: RSSI = tx_power - 20*log10(d)
    → d = 10^((tx_power - RSSI) / 20)
    """
    if rssi <= RSSI_MIN:
        return float("inf")
    return 10 ** ((tx_power - rssi) / 20.0)


class Master:
    """
    Emulates the Master ESP32-C3 that aggregates BLE data.

    Parameters
    ----------
    bocce : list[Boccia]
        List of boccia nodes the master listens to.
    """

    def __init__(self, bocce: List[Boccia]):
        self.bocce = bocce
        self.pallino_x = PALLINO_X
        self.pallino_y = PALLINO_Y
        self._last_packet: Dict = {}
        self._timestamp: float = 0.0

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def collect_rssi(self) -> Dict:
        """
        Collect RSSI readings between all pairs of bocce and to the pallino.

        Returns a dictionary keyed by player_id with:
          - rssi_to_others: {other_id: rssi_dBm}
          - rssi_to_pallino: float (simulated, assumes fixed BLE beacon)
          - position: (x, y) true position (known only in simulation)
        """
        data = {}
        for boccia in self.bocce:
            rssi_others = {}
            for other in self.bocce:
                if other.player_id != boccia.player_id:
                    rssi_others[other.player_id] = boccia.rssi_to(other)

            # Simulated RSSI to a fixed pallino BLE beacon
            rssi_pallino = boccia.rssi_to_point(self.pallino_x, self.pallino_y)

            data[boccia.player_id] = {
                "uuid": boccia.ble_uuid,
                "rssi_to_others": rssi_others,
                "rssi_to_pallino": rssi_pallino,
                "position": (boccia.x, boccia.y),   # ground-truth for simulation
                "is_moving": boccia.is_moving,
            }
        return data

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self) -> Dict:
        """
        Collect data, compute estimated distances, build output packet.

        Returns the packet dict (also stored in self._last_packet).
        """
        raw = self.collect_rssi()
        self._timestamp = time.time()

        bocce_info = []
        for player_id, info in raw.items():
            dist_to_pallino_rssi = rssi_to_distance(info["rssi_to_pallino"])
            dist_to_pallino_true = math.hypot(
                info["position"][0] - self.pallino_x,
                info["position"][1] - self.pallino_y,
            )
            pairwise = {
                other_id: rssi_to_distance(rssi)
                for other_id, rssi in info["rssi_to_others"].items()
            }
            bocce_info.append(
                {
                    "player_id": player_id,
                    "uuid": info["uuid"],
                    "position_true": info["position"],
                    "rssi_to_pallino": info["rssi_to_pallino"],
                    "dist_to_pallino_estimated": dist_to_pallino_rssi,
                    "dist_to_pallino_true": dist_to_pallino_true,
                    "pairwise_distances_estimated": pairwise,
                    "rssi_to_others": info["rssi_to_others"],
                    "is_moving": info["is_moving"],
                }
            )

        # Sort by true distance (closest first)
        bocce_info.sort(key=lambda b: b["dist_to_pallino_true"])

        self._last_packet = {
            "timestamp": self._timestamp,
            "pallino": {"x": self.pallino_x, "y": self.pallino_y},
            "bocce": bocce_info,
            "winner_id": bocce_info[0]["player_id"] if bocce_info else None,
        }
        return self._last_packet

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def log(self) -> None:
        """Print a human-readable summary of the last processed packet."""
        pkt = self._last_packet
        if not pkt:
            print("[Master] No data yet.")
            return

        print(
            f"[Master] t={pkt['timestamp']:.3f} | "
            f"Pallino @ ({pkt['pallino']['x']:.2f}, {pkt['pallino']['y']:.2f})"
        )
        for b in pkt["bocce"]:
            print(
                f"  Boccia {b['player_id']:2d} | "
                f"pos=({b['position_true'][0]:.3f}, {b['position_true'][1]:.3f}) | "
                f"dist_true={b['dist_to_pallino_true']:.3f}m | "
                f"dist_est={b['dist_to_pallino_estimated']:.3f}m | "
                f"RSSI_pallino={b['rssi_to_pallino']:.1f}dBm"
            )
        if pkt["winner_id"] is not None:
            print(f"  *** Winner (closest): Boccia {pkt['winner_id']} ***")

    def __repr__(self) -> str:
        return f"Master(bocce={len(self.bocce)}, pallino=({self.pallino_x}, {self.pallino_y}))"
