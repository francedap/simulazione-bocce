"""
gui.py - Pygame-based GUI for the Bocce simulation.

Displays:
  - The bocce field (4 m × 1.5 m scaled to window)
  - Coloured circles for each boccia
  - The pallino (white dot at centre)
  - Distance lines and labels
  - Ranking panel (closest → furthest)
  - RSSI information per boccia
  - On-screen instructions

Controls:
  SPACE  – Launch bocce
  R      – Restart game
  ESC/Q  – Quit
"""

import sys
import math
import pygame

from simulator.boccia import FIELD_WIDTH, FIELD_HEIGHT, BOCCIA_RADIUS
from simulator.master import PALLINO_X, PALLINO_Y

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
WINDOW_W = 1100
WINDOW_H = 700

FIELD_MARGIN_X = 40
FIELD_MARGIN_Y = 80
FIELD_DISPLAY_W = 700
FIELD_DISPLAY_H = int(FIELD_DISPLAY_W * (FIELD_HEIGHT / FIELD_WIDTH))

PANEL_X = FIELD_MARGIN_X + FIELD_DISPLAY_W + 20
PANEL_Y = FIELD_MARGIN_Y
PANEL_W = WINDOW_W - PANEL_X - 10
PANEL_H = FIELD_DISPLAY_H

# Colours
C_BG = (30, 30, 30)
C_FIELD = (34, 85, 34)          # grass green
C_FIELD_BORDER = (180, 140, 80) # sand/clay border
C_PALLINO = (255, 255, 255)
C_PALLINO_OUTLINE = (200, 200, 0)
C_TEXT = (230, 230, 230)
C_TEXT_DIM = (140, 140, 140)
C_WINNER_GLOW = (255, 215, 0)   # gold
C_PANEL_BG = (45, 45, 55)
C_PANEL_BORDER = (80, 80, 100)
C_DISTANCE_LINE = (200, 200, 200, 80)
C_HEADER = (100, 180, 255)


def _scale_pos(mx: float, my: float) -> tuple:
    """Convert field metres to pixel coordinates."""
    px = FIELD_MARGIN_X + int(mx / FIELD_WIDTH * FIELD_DISPLAY_W)
    py = FIELD_MARGIN_Y + int(my / FIELD_HEIGHT * FIELD_DISPLAY_H)
    return (px, py)


def _scale_radius(r_m: float) -> int:
    """Convert a radius in metres to pixels."""
    return max(4, int(r_m / FIELD_WIDTH * FIELD_DISPLAY_W))


class BocceGUI:
    """
    Main Pygame GUI class.

    Parameters
    ----------
    engine : GameEngine
        Running game engine instance.
    fps : int
        Target frame rate.
    """

    def __init__(self, engine, fps: int = 60):
        self.engine = engine
        self.fps = fps

        pygame.init()
        pygame.display.set_caption("Bocce Simulation – BLE/RSSI")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        # Font sizes
        self.font_lg = pygame.font.SysFont("DejaVuSans", 18, bold=True)
        self.font_md = pygame.font.SysFont("DejaVuSans", 15)
        self.font_sm = pygame.font.SysFont("DejaVuSans", 12)

        self._last_packet: dict = {}
        self._running = True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the GUI event loop (blocking)."""
        while self._running:
            self._handle_events()
            self._last_packet = self.engine.update()
            self._draw()
            self.clock.tick(self.fps)

        pygame.quit()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self._running = False
                elif event.key == pygame.K_SPACE:
                    if not self.engine.game_started or self.engine.all_stopped:
                        self.engine.launch_bocce()
                elif event.key == pygame.K_r:
                    self.engine.reset()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        self.screen.fill(C_BG)
        self._draw_field()
        self._draw_bocce()
        self._draw_pallino()
        self._draw_distance_lines()
        self._draw_panel()
        self._draw_instructions()
        pygame.display.flip()

    def _draw_field(self) -> None:
        """Draw the bocce field rectangle."""
        field_rect = pygame.Rect(
            FIELD_MARGIN_X, FIELD_MARGIN_Y, FIELD_DISPLAY_W, FIELD_DISPLAY_H
        )
        pygame.draw.rect(self.screen, C_FIELD, field_rect)
        pygame.draw.rect(self.screen, C_FIELD_BORDER, field_rect, 4)

        # Grid lines every 1 m
        for gx in range(1, int(FIELD_WIDTH)):
            px = FIELD_MARGIN_X + int(gx / FIELD_WIDTH * FIELD_DISPLAY_W)
            pygame.draw.line(
                self.screen,
                (50, 110, 50),
                (px, FIELD_MARGIN_Y),
                (px, FIELD_MARGIN_Y + FIELD_DISPLAY_H),
                1,
            )
        for gy_cm in range(50, int(FIELD_HEIGHT * 100), 50):
            py = FIELD_MARGIN_Y + int((gy_cm / 100) / FIELD_HEIGHT * FIELD_DISPLAY_H)
            pygame.draw.line(
                self.screen,
                (50, 110, 50),
                (FIELD_MARGIN_X, py),
                (FIELD_MARGIN_X + FIELD_DISPLAY_W, py),
                1,
            )

        # Axis labels
        for m in range(int(FIELD_WIDTH) + 1):
            px = FIELD_MARGIN_X + int(m / FIELD_WIDTH * FIELD_DISPLAY_W)
            lbl = self.font_sm.render(f"{m}m", True, C_TEXT_DIM)
            self.screen.blit(lbl, (px - 8, FIELD_MARGIN_Y + FIELD_DISPLAY_H + 4))

    def _draw_bocce(self) -> None:
        """Draw each boccia as a filled circle with ID label."""
        r_px = _scale_radius(BOCCIA_RADIUS)
        winner_id = self._last_packet.get("winner_id")

        for boccia in self.engine.bocce:
            px, py = _scale_pos(boccia.x, boccia.y)

            # Winner glow ring
            if boccia.player_id == winner_id and self.engine.all_stopped:
                pygame.draw.circle(self.screen, C_WINNER_GLOW, (px, py), r_px + 5, 3)

            # Shadow
            pygame.draw.circle(self.screen, (0, 0, 0, 100), (px + 2, py + 2), r_px)
            # Fill
            pygame.draw.circle(self.screen, boccia.color, (px, py), r_px)
            # Outline
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), r_px, 1)

            # ID number
            lbl = self.font_sm.render(str(boccia.player_id + 1), True, (255, 255, 255))
            self.screen.blit(lbl, (px - 4, py - 6))

    def _draw_pallino(self) -> None:
        """Draw the pallino (jack) at its fixed position."""
        px, py = _scale_pos(PALLINO_X, PALLINO_Y)
        pygame.draw.circle(self.screen, C_PALLINO_OUTLINE, (px, py), 9)
        pygame.draw.circle(self.screen, C_PALLINO, (px, py), 7)
        lbl = self.font_sm.render("P", True, (0, 0, 0))
        self.screen.blit(lbl, (px - 4, py - 6))

    def _draw_distance_lines(self) -> None:
        """Draw lines from each boccia to the pallino with distance label."""
        pallino_px, pallino_py = _scale_pos(PALLINO_X, PALLINO_Y)
        bocce_data = self._last_packet.get("bocce", [])

        for b in bocce_data:
            pid = b["player_id"]
            boccia_obj = next(
                (bo for bo in self.engine.bocce if bo.player_id == pid), None
            )
            if boccia_obj is None:
                continue

            bx, by = _scale_pos(boccia_obj.x, boccia_obj.y)
            dist = b["dist_to_pallino_true"]

            # Dashed-style line (draw alternating segments)
            n_segs = 12
            for seg in range(n_segs):
                if seg % 2 == 0:
                    t0 = seg / n_segs
                    t1 = (seg + 1) / n_segs
                    x0 = int(bx + (pallino_px - bx) * t0)
                    y0 = int(by + (pallino_py - by) * t0)
                    x1 = int(bx + (pallino_px - bx) * t1)
                    y1 = int(by + (pallino_py - by) * t1)
                    pygame.draw.line(
                        self.screen, (*boccia_obj.color, 120), (x0, y0), (x1, y1), 1
                    )

            # Midpoint label
            mid_x = (bx + pallino_px) // 2
            mid_y = (by + pallino_py) // 2
            lbl = self.font_sm.render(f"{dist:.2f}m", True, C_TEXT_DIM)
            self.screen.blit(lbl, (mid_x + 2, mid_y - 8))

    def _draw_panel(self) -> None:
        """Draw the info panel on the right side."""
        panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
        pygame.draw.rect(self.screen, C_PANEL_BG, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, C_PANEL_BORDER, panel_rect, 2, border_radius=8)

        y = PANEL_Y + 10
        line_h = 20

        # Header
        hdr = self.font_lg.render("📡 Bocce Status", True, C_HEADER)
        self.screen.blit(hdr, (PANEL_X + 10, y))
        y += line_h + 6

        # Game state
        state = self.engine.raspberry_pi.game_state
        rnd = self.engine.raspberry_pi.round
        state_lbl = self.font_md.render(
            f"State: {state.upper()}  Round: {rnd}", True, C_TEXT
        )
        self.screen.blit(state_lbl, (PANEL_X + 10, y))
        y += line_h + 4

        # Divider
        pygame.draw.line(
            self.screen,
            C_PANEL_BORDER,
            (PANEL_X + 10, y),
            (PANEL_X + PANEL_W - 10, y),
            1,
        )
        y += 8

        # Ranking header
        rank_hdr = self.font_md.render("Ranking (closest first):", True, C_HEADER)
        self.screen.blit(rank_hdr, (PANEL_X + 10, y))
        y += line_h + 2

        bocce_data = self._last_packet.get("bocce", [])
        winner_id = self._last_packet.get("winner_id")

        for rank, b in enumerate(bocce_data):
            pid = b["player_id"]
            boccia_obj = next(
                (bo for bo in self.engine.bocce if bo.player_id == pid), None
            )
            color = boccia_obj.color if boccia_obj else C_TEXT

            prefix = "🏆" if pid == winner_id else f"#{rank + 1}"
            dist = b["dist_to_pallino_true"]
            rssi = b["rssi_to_pallino"]
            moving = "●" if b["is_moving"] else "■"

            text = f"{prefix} Boccia {pid + 1}  {dist:.3f}m  {rssi:.1f}dBm {moving}"
            lbl = self.font_md.render(text, True, color)
            self.screen.blit(lbl, (PANEL_X + 10, y))
            y += line_h

        # Divider
        y += 4
        pygame.draw.line(
            self.screen,
            C_PANEL_BORDER,
            (PANEL_X + 10, y),
            (PANEL_X + PANEL_W - 10, y),
            1,
        )
        y += 8

        # RSSI pairwise section
        rssi_hdr = self.font_md.render("RSSI between bocce:", True, C_HEADER)
        self.screen.blit(rssi_hdr, (PANEL_X + 10, y))
        y += line_h + 2

        for b in bocce_data:
            pid = b["player_id"]
            for other_id, rssi_val in b.get("rssi_to_others", {}).items():
                if other_id > pid:   # show each pair once
                    text = (
                        f"  {pid + 1}↔{other_id + 1}: {rssi_val:.1f} dBm"
                    )
                    lbl = self.font_sm.render(text, True, C_TEXT_DIM)
                    self.screen.blit(lbl, (PANEL_X + 10, y))
                    y += 16
                    if y > PANEL_Y + PANEL_H - 20:
                        break
            if y > PANEL_Y + PANEL_H - 20:
                break

    def _draw_instructions(self) -> None:
        """Draw control instructions at the bottom of the screen."""
        instructions = [
            "SPACE: launch bocce",
            "R: restart",
            "ESC/Q: quit",
        ]
        y = FIELD_MARGIN_Y + FIELD_DISPLAY_H + 20
        for i, txt in enumerate(instructions):
            lbl = self.font_sm.render(txt, True, C_TEXT_DIM)
            self.screen.blit(lbl, (FIELD_MARGIN_X + i * 220, y))

        # Frame counter
        frame_lbl = self.font_sm.render(
            f"Frame: {self.engine.frame}", True, C_TEXT_DIM
        )
        self.screen.blit(frame_lbl, (FIELD_MARGIN_X, y + 20))

        # Title
        title = self.font_lg.render(
            "Bocce BLE/RSSI Simulation – ESP32-C3 + Raspberry Pi",
            True,
            C_HEADER,
        )
        self.screen.blit(title, (FIELD_MARGIN_X, 10))
