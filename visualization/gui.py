"""
gui.py - Matplotlib-based GUI for the Bocce simulation.

Displays:
  - The bocce field (4 m × 1.5 m)
  - Coloured circles for each boccia
  - The pallino (orange dot at centre)
  - Distance lines and labels
  - Stats panel (right) with ranking and RSSI

Controls:
  Click  – Launch bocce (when not in motion)
  R      – Restart game
  Q      – Quit
"""

import sys
import logging

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation

from simulator.boccia import FIELD_WIDTH, FIELD_HEIGHT, BOCCIA_RADIUS
from simulator.master import PALLINO_X, PALLINO_Y

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette (Matplotlib-compatible hex strings)
# Same ordering as game_engine.BOCCIA_COLORS
# ---------------------------------------------------------------------------
BOCCIA_COLORS_MPL = [
    "#DC3232",  # red
    "#3264DC",  # blue
    "#32B432",  # green
    "#DCB432",  # yellow/gold
    "#A032B4",  # purple
    "#32BEBE",  # cyan
    "#DC6E32",  # orange
    "#B43274",  # pink/rose
]


class BocceGUI:
    """
    Matplotlib-based GUI for the Bocce simulation.

    Parameters
    ----------
    engine : GameEngine
        Running game engine instance.
    fps : int
        Target frames per second.
    """

    def __init__(self, engine, fps: int = 60):
        self.engine = engine
        self.fps = fps
        self._last_packet: dict = {}
        self._running = True

        # Figure: two axes side-by-side (70 % field | 30 % stats)
        self.fig = plt.figure("Bocce BLE/RSSI Simulation", figsize=(14, 6))
        self.fig.patch.set_facecolor("#1e1e1e")

        self.ax_field = self.fig.add_axes([0.03, 0.12, 0.63, 0.78])
        self.ax_stats = self.fig.add_axes([0.70, 0.12, 0.28, 0.78])

        self._setup_field_axes()
        self._setup_stats_axes()

        # Event connections
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("close_event", self._on_close)

        # Animation – interval in ms
        interval_ms = max(1, int(1000 / fps))
        self._anim = FuncAnimation(
            self.fig,
            self._update,
            interval=interval_ms,
            blit=False,
            cache_frame_data=False,
        )

    # ------------------------------------------------------------------
    # Axes setup helpers
    # ------------------------------------------------------------------

    def _setup_field_axes(self) -> None:
        """Configure the bocce field axes."""
        ax = self.ax_field
        ax.set_facecolor("#1a5c1a")
        ax.set_xlim(-0.1, FIELD_WIDTH + 0.1)
        ax.set_ylim(-0.1, FIELD_HEIGHT + 0.1)
        ax.set_aspect("equal")
        ax.set_xlabel("m", color="#aaaaaa")
        ax.set_ylabel("m", color="#aaaaaa")
        ax.tick_params(colors="#aaaaaa")
        for spine in ax.spines.values():
            spine.set_edgecolor("#b48c50")
            spine.set_linewidth(3)
        ax.grid(True, color="#2a7a2a", linewidth=0.5, alpha=0.7)
        ax.set_title(
            "Campo Bocce", color="#64b4ff", fontsize=13, fontweight="bold", pad=6
        )

    def _setup_stats_axes(self) -> None:
        """Configure the stats panel axes."""
        ax = self.ax_stats
        ax.set_facecolor("#2d2d37")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(
            "📡 Bocce Status", color="#64b4ff", fontsize=12, fontweight="bold", pad=6
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the GUI event loop (blocking via plt.show)."""
        plt.show()

    # ------------------------------------------------------------------
    # Animation callback
    # ------------------------------------------------------------------

    def _update(self, frame) -> None:
        """FuncAnimation callback: advance simulation and redraw."""
        if not self._running:
            return

        self._last_packet = self.engine.update()
        self._redraw_field()
        self._redraw_stats()

        state = self.engine.raspberry_pi.game_state
        self.fig.suptitle(
            f"Bocce BLE/RSSI Simulation – ESP32-C3 + Raspberry Pi  |  {state.upper()}",
            color="#64b4ff",
            fontsize=11,
            fontweight="bold",
            y=0.98,
        )

    # ------------------------------------------------------------------
    # Drawing – field
    # ------------------------------------------------------------------

    def _redraw_field(self) -> None:
        """Clear and redraw the bocce field subplot."""
        ax = self.ax_field
        ax.cla()
        self._setup_field_axes()

        # Field border rectangle
        ax.add_patch(
            patches.Rectangle(
                (0, 0),
                FIELD_WIDTH,
                FIELD_HEIGHT,
                linewidth=3,
                edgecolor="#b48c50",
                facecolor="none",
            )
        )

        # Pallino
        ax.add_patch(
            patches.Circle((PALLINO_X, PALLINO_Y), 0.04, color="#ffa500", zorder=5)
        )
        ax.text(
            PALLINO_X,
            PALLINO_Y + 0.07,
            "P",
            ha="center",
            va="bottom",
            color="white",
            fontsize=8,
            fontweight="bold",
            zorder=6,
        )

        bocce_data = self._last_packet.get("bocce", [])
        winner_id = self._last_packet.get("winner_id")

        for boccia in self.engine.bocce:
            color = self._boccia_mpl_color(boccia)

            # Dashed distance line to pallino
            ax.plot(
                [boccia.x, PALLINO_X],
                [boccia.y, PALLINO_Y],
                color=color,
                alpha=0.4,
                linewidth=0.8,
                linestyle="--",
                zorder=2,
            )

            # Winner glow ring
            if boccia.player_id == winner_id and self.engine.all_stopped:
                ax.add_patch(
                    patches.Circle(
                        (boccia.x, boccia.y),
                        BOCCIA_RADIUS + 0.015,
                        color="#ffd700",
                        linewidth=2,
                        fill=False,
                        zorder=3,
                    )
                )

            # Boccia circle
            ax.add_patch(
                patches.Circle((boccia.x, boccia.y), BOCCIA_RADIUS, color=color, zorder=4)
            )

            # ID label
            ax.text(
                boccia.x,
                boccia.y,
                str(boccia.player_id + 1),
                ha="center",
                va="center",
                color="white",
                fontsize=7,
                fontweight="bold",
                zorder=5,
            )

        # Distance labels at midpoints
        for b in bocce_data:
            pid = b["player_id"]
            boccia_obj = next(
                (bo for bo in self.engine.bocce if bo.player_id == pid), None
            )
            if boccia_obj is None:
                continue
            dist = b["dist_to_pallino_true"]
            mid_x = (boccia_obj.x + PALLINO_X) / 2
            mid_y = (boccia_obj.y + PALLINO_Y) / 2
            ax.text(
                mid_x,
                mid_y,
                f"{dist:.2f}m",
                ha="center",
                va="center",
                color="#aaaaaa",
                fontsize=6,
                zorder=6,
            )

        # Instructions footer
        self.fig.text(
            0.03,
            0.02,
            "Click: launch bocce  |  R: restart  |  Q: quit",
            color="#888888",
            fontsize=8,
            transform=self.fig.transFigure,
        )

    # ------------------------------------------------------------------
    # Drawing – stats panel
    # ------------------------------------------------------------------

    def _redraw_stats(self) -> None:
        """Clear and redraw the stats panel subplot."""
        ax = self.ax_stats
        ax.cla()
        self._setup_stats_axes()

        bocce_data = self._last_packet.get("bocce", [])
        winner_id = self._last_packet.get("winner_id")
        state = self.engine.raspberry_pi.game_state
        rnd = self.engine.raspberry_pi.round

        y = 0.96
        line_h = 0.055

        def _txt(yy, s, color="#e6e6e6", size=9, bold=False):
            ax.text(
                0.05,
                yy,
                s,
                color=color,
                fontsize=size,
                fontweight="bold" if bold else "normal",
                transform=ax.transAxes,
                va="top",
            )

        _txt(y, f"State: {state.upper()}", color="#64b4ff", bold=True)
        y -= line_h
        _txt(y, f"Round: {rnd}")
        y -= line_h
        _txt(y, f"Active bocce: {len(self.engine.bocce)}")
        y -= line_h
        _txt(y, f"Frame: {self.engine.frame}", color="#888888", size=8)
        y -= line_h * 1.3
        ax.axhline(y=y, color="#505064", linewidth=1, xmin=0.05, xmax=0.95)
        y -= line_h * 0.6

        _txt(y, "Ranking (closest first):", color="#64b4ff", bold=True)
        y -= line_h

        for rank, b in enumerate(bocce_data):
            pid = b["player_id"]
            boccia_obj = next(
                (bo for bo in self.engine.bocce if bo.player_id == pid), None
            )
            color = self._boccia_mpl_color(boccia_obj) if boccia_obj else "#e6e6e6"
            is_winner = pid == winner_id and self.engine.all_stopped
            prefix = "★" if is_winner else f"#{rank + 1}"
            dist = b["dist_to_pallino_true"]
            rssi = b["rssi_to_pallino"]
            moving = "●" if b["is_moving"] else "■"
            _txt(
                y,
                f"{prefix} B{pid + 1}  {dist:.3f}m  {rssi:.0f}dBm {moving}",
                color=color,
                size=8,
            )
            y -= line_h
            if y < 0.08:
                break

        if y > 0.12:
            ax.axhline(y=y, color="#505064", linewidth=1, xmin=0.05, xmax=0.95)
            y -= line_h * 0.6
            _txt(y, "RSSI between bocce:", color="#64b4ff", bold=True, size=8)
            y -= line_h

            for b in bocce_data:
                pid = b["player_id"]
                for other_id, rssi_val in b.get("rssi_to_others", {}).items():
                    if other_id > pid:
                        _txt(
                            y,
                            f"  {pid + 1}↔{other_id + 1}: {rssi_val:.0f} dBm",
                            color="#888888",
                            size=7,
                        )
                        y -= line_h * 0.9
                        if y < 0.02:
                            break
                if y < 0.02:
                    break

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _boccia_mpl_color(self, boccia) -> str:
        """Return a Matplotlib hex color for the given boccia."""
        if boccia is None:
            return "#e6e6e6"
        return BOCCIA_COLORS_MPL[boccia.player_id % len(BOCCIA_COLORS_MPL)]

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_key(self, event) -> None:
        if event.key == "r":
            self.engine.reset()
            logger.info("Game reset via keyboard.")
        elif event.key == "q" or event.key == "escape":
            self._running = False
            plt.close(self.fig)
            sys.exit(0)

    def _on_click(self, event) -> None:
        if event.inaxes == self.ax_field:
            if not self.engine.game_started or self.engine.all_stopped:
                self.engine.launch_bocce()
                logger.info("Bocce launched via click.")

    def _on_close(self, event) -> None:
        self._running = False
        sys.exit(0)
