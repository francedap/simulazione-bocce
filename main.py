#!/usr/bin/env python3
"""
main.py – Entry point for the Bocce BLE/RSSI simulation.

Usage:
    python main.py [--bocce N] [--fps FPS] [--debug]

Options:
    --bocce N     Number of bocce to simulate (default: 4, range: 2–8)
    --fps FPS     Target frames per second (default: 60)
    --debug       Enable verbose debug logging
"""

import argparse
import logging
import sys

from simulator.game_engine import GameEngine
from visualization.gui import BocceGUI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bocce BLE/RSSI Simulation (ESP32-C3 + Raspberry Pi)"
    )
    parser.add_argument(
        "--bocce",
        type=int,
        default=4,
        metavar="N",
        help="Number of bocce (2–8, default: 4)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        metavar="FPS",
        help="Target frames per second (default: 60)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    num_bocce = max(2, min(8, args.bocce))
    if num_bocce != args.bocce:
        logger.warning(
            "Number of bocce clamped to %d (allowed range: 2–8).", num_bocce
        )

    logger.info(
        "Starting Bocce simulation with %d bocce at %d FPS.", num_bocce, args.fps
    )

    try:
        engine = GameEngine(num_bocce=num_bocce, fps=args.fps)
        gui = BocceGUI(engine=engine, fps=args.fps)
        gui.run()
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
