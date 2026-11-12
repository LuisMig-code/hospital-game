"""Testes do zoom suave pela roda do mouse."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import main  # noqa: E402
import settings as S  # noqa: E402

DT = 1 / 60


class ZoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = main.Game(42)
        cls.initial = (cls.game.zoom, cls.game.zoom_target)

    def setUp(self):
        self.game.zoom = self.game.zoom_target = S.ZOOM_MIN

    def settle(self, seconds=2.0):
        zs = []
        for _ in range(round(seconds / DT)):
            self.game.update_zoom(DT)
            zs.append(self.game.zoom)
        return zs

    def test_starts_at_1x_and_limits(self):
        self.assertEqual(self.initial, (1.0, 1.0))
        self.assertEqual((S.ZOOM_MIN, S.ZOOM_MAX), (1.0, 2.0))

    def test_wheel_changes_target_and_clamps(self):
        g = self.game
        g.change_zoom(+3)
        self.assertAlmostEqual(g.zoom_target, 1.0 + 3 * S.ZOOM_STEP)
        g.change_zoom(+100)
        self.assertEqual(g.zoom_target, S.ZOOM_MAX)          # não passa de 2x
        g.change_zoom(-100)
        self.assertEqual(g.zoom_target, S.ZOOM_MIN)          # não passa de 1x
        g.change_zoom(0.25)                                  # touchpad: fração de clique
        self.assertAlmostEqual(g.zoom_target, 1.0 + 0.25 * S.ZOOM_STEP)

    def test_ten_clicks_reach_exactly_2x(self):
        g = self.game
        for _ in range(10):
            g.change_zoom(+1)
        self.assertEqual(g.zoom_target, 2.0)                 # sem 1.9999999
        self.settle()
        self.assertEqual(g.zoom, 2.0)

    def test_transition_is_smooth(self):
        g = self.game
        g.change_zoom(+10)
        zs = self.settle(1.0)
        self.assertGreater(zs[0], 1.0)                       # já começa a mudar
        self.assertLess(zs[0], 1.5)                          # mas não pula de uma vez
        self.assertEqual(zs, sorted(zs))                     # só aumenta, sem passar do alvo
        self.assertTrue(all(z <= 2.0 for z in zs))
        steps = [b - a for a, b in zip(zs, zs[1:])]
        self.assertLess(max(steps), 0.25)                    # nenhum salto grande
        self.assertEqual(zs[-1], 2.0)

    def test_mousewheel_event(self):
        g = self.game
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=2, precise_x=0.0, precise_y=2.0, flipped=False))
        for e in pygame.event.get():
            if e.type == pygame.MOUSEWHEEL:
                g.change_zoom(getattr(e, "precise_y", e.y))
        self.assertAlmostEqual(g.zoom_target, 1.0 + 2 * S.ZOOM_STEP)

    def test_draw_at_fractional_zoom(self):
        g = self.game
        for z in (1.0, 1.37, 1.5, 2.0):
            g.zoom = g.zoom_target = z
            vw, vh = g.view_size()
            self.assertAlmostEqual(vw, S.SCREEN_W / z, delta=1)
            self.assertAlmostEqual(vh, (S.SCREEN_H - S.HUD_BAR_H) / z, delta=1)   # abaixo da tarja
            g.draw_world()                                   # não pode quebrar em zoom fracionário
            self.assertEqual(g.screen.get_size(), (S.SCREEN_W, S.SCREEN_H))

    def test_hud_bar_on_top_and_world_below(self):
        """A tarja preta ocupa o topo e o mundo é desenhado só abaixo dela."""
        g = self.game
        g.zoom = g.zoom_target = 1.0
        g.show_message("Recepção", 2.0)
        g.screen.fill((255, 0, 255))
        g.draw_world()
        g.draw_hud()
        black = tuple(S.COLOR_HUD_BAR)
        for x in (S.SCREEN_W // 2 - 300, S.SCREEN_W // 2 + 150, S.SCREEN_W - 3):   # fora dos textos/barras
            for y in (1, S.HUD_BAR_H - 4):
                self.assertEqual(tuple(g.screen.get_at((x, y)))[:3], black, (x, y))
        # nada do mundo (nem o fundo magenta) sobra embaixo da tarja
        for x in range(0, S.SCREEN_W, 97):
            self.assertNotEqual(tuple(g.screen.get_at((x, S.HUD_BAR_H + 2)))[:3], (255, 0, 255))

    def test_camera_centers_player_in_world_area(self):
        g = self.game
        g.zoom = g.zoom_target = 2.0
        vw, vh = g.view_size()
        cam = g.camera()
        mw, mh = g.map_surf.get_size()
        if vh / 2 <= g.player.y <= mh - vh / 2:          # longe da borda do mapa
            self.assertAlmostEqual(g.player.y - cam[1], vh / 2, delta=1)
        if vw / 2 <= g.player.x <= mw - vw / 2:
            self.assertAlmostEqual(g.player.x - cam[0], vw / 2, delta=1)


if __name__ == "__main__":
    unittest.main()
