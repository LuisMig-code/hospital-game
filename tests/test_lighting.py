"""Testes da névoa suave e da máscara de luz."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from lighting import UNEXPLORED, FogLayer, Light, build_light_mask, explored_fog_alpha  # noqa: E402


class FogLayerTests(unittest.TestCase):
    def test_states(self):
        fog = FogLayer(10, 8)
        self.assertEqual(fog.alpha_at(3, 3), UNEXPLORED)          # começa toda preta
        fog.update({(3, 3), (4, 3)})
        self.assertEqual(fog.alpha_at(3, 3), 0)                   # visível
        self.assertEqual(fog.alpha_at(5, 5), UNEXPLORED)
        fog.update({(4, 3), (5, 3)})
        self.assertEqual(fog.alpha_at(3, 3), explored_fog_alpha())  # saiu da visão: escurecido
        self.assertEqual(fog.alpha_at(5, 3), 0)
        fog.update(set())
        for t in ((3, 3), (4, 3), (5, 3)):
            self.assertEqual(fog.alpha_at(*t), explored_fog_alpha())  # nunca volta a preto

    def test_render_covers_view_and_is_smooth(self):
        fog = FogLayer(40, 30)
        fog.update({(x, y) for x in range(10, 20) for y in range(10, 20)})
        t = S.TILE
        cam, view = (5 * t, 5 * t), (20 * t, 15 * t)
        big, pos = fog.render(cam, view)
        # cobre a área inteira da tela
        self.assertLessEqual(pos[0], 0)
        self.assertLessEqual(pos[1], 0)
        self.assertGreaterEqual(pos[0] + big.get_width(), view[0])
        self.assertGreaterEqual(pos[1] + big.get_height(), view[1])
        # no centro de um tile visível é transparente, no centro de um não
        # descoberto é opaco, e na fronteira há valores intermediários
        def alpha(tx, ty, ox=t // 2):
            return big.get_at((tx * t + ox - cam[0] - pos[0], ty * t + t // 2 - cam[1] - pos[1])).a
        self.assertEqual(alpha(15, 15), 0)
        self.assertEqual(alpha(5 + 1, 15), UNEXPLORED)
        edge = alpha(9, 15, ox=t - 1)    # borda entre não descoberto (9) e visível (10)
        self.assertTrue(0 < edge < UNEXPLORED, edge)


class LightTests(unittest.TestCase):
    def test_no_seam_outside_mask(self):
        """A escuridão fora do quadrado da máscara é igual à da borda dela
        (antes havia um corte reto ~12 tiles longe do personagem)."""
        light = Light(150)
        surf = pygame.Surface((1280, 720))
        surf.fill((200, 200, 200))
        center = (1000, 120)                  # personagem perto do canto: máscara cortada
        light.draw(surf, center)
        rect = light.masks[0].get_rect(center=center)
        y = center[1] + 30
        inside = surf.get_at((rect.left + 2, y))
        outside = surf.get_at((rect.left - 2, y))
        self.assertEqual(inside[:3], outside[:3])
        below_in = surf.get_at((center[0], rect.bottom - 2))
        below_out = surf.get_at((center[0], rect.bottom + 2))
        self.assertEqual(below_in[:3], below_out[:3])
        far = surf.get_at((10, 700))
        self.assertLess(far.r, 200)          # longe do personagem também escurece

    def test_explored_final_darkness_matches_setting(self):
        """Luz da borda + névoa compensada = FOG_EXPLORED_ALPHA no resultado."""
        a = 1 - (1 - S.LIGHT_EDGE_ALPHA / 255) * (1 - explored_fog_alpha() / 255)
        self.assertAlmostEqual(a * 255, S.FOG_EXPLORED_ALPHA, delta=1.5)

    def test_mask_gradient(self):
        r = 200
        mask = build_light_mask(r, 120)
        c = mask.get_width() // 2
        self.assertEqual(mask.get_at((c, c)).a, 0)                # centro claro
        self.assertEqual(mask.get_at((0, 0)).a, 120)              # canto: escuridão da borda
        alphas = [mask.get_at((c + d, c)).a for d in range(0, r, 20)]
        self.assertEqual(alphas, sorted(alphas))                  # escurece para fora
        self.assertLess(alphas[1], alphas[-1])

    def test_flicker_levels(self):
        light = Light(100)
        self.assertEqual(len(light.masks), len(Light.LEVELS))
        old = S.LIGHT_FLICKER
        try:
            S.LIGHT_FLICKER = False
            for _ in range(50):
                light.update(0.1)
                self.assertEqual(light.level, 0)
            S.LIGHT_FLICKER = True
            seen = set()
            for _ in range(2000):
                light.update(0.1)
                seen.add(light.level)
            self.assertIn(0, seen)
            self.assertGreater(len(seen), 1)
        finally:
            S.LIGHT_FLICKER = old


if __name__ == "__main__":
    unittest.main()
