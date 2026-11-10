"""Névoa de guerra com bordas suaves e luz que cai com a distância.

A névoa é guardada numa superfície minúscula, com 1 pixel por tile, onde
o alpha de cada pixel diz o quanto o tile está escuro. Na hora de desenhar,
só o pedaço que aparece na tela é ampliado com smoothscale: a interpolação
bilinear cria degradês entre os tiles em vez de quadrados duros.
"""
import random

import pygame

import settings as S

UNEXPLORED = 255


class FogLayer:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.small = pygame.Surface((width, height), pygame.SRCALPHA)
        self.small.fill((*S.COLOR_UNEXPLORED, UNEXPLORED))
        self.visible = set()

    def alpha_at(self, tx, ty):
        return self.small.get_at((tx, ty)).a

    def update(self, visible):
        """Tiles que saíram da visão ficam "escurecidos"; os visíveis, claros."""
        dim = (*S.COLOR_UNEXPLORED, S.FOG_EXPLORED_ALPHA)
        for t in self.visible - visible:
            self.small.set_at(t, dim)
        for t in visible - self.visible:
            self.small.set_at(t, (*S.COLOR_UNEXPLORED, 0))
        self.visible = set(visible)

    def render(self, cam, view_size, tile=S.TILE):
        """Superfície da névoa (ampliada e suavizada) para a área da tela e a
        posição (em pixels da tela) onde ela deve ser desenhada."""
        cx, cy = cam
        vw, vh = view_size
        tx0 = max(0, cx // tile - 1)
        ty0 = max(0, cy // tile - 1)
        tx1 = min(self.width, (cx + vw) // tile + 2)
        ty1 = min(self.height, (cy + vh) // tile + 2)
        part = self.small.subsurface((tx0, ty0, tx1 - tx0, ty1 - ty0))
        big = pygame.transform.smoothscale(part, ((tx1 - tx0) * tile, (ty1 - ty0) * tile))
        return big, (tx0 * tile - cx, ty0 * tile - cy)


def build_light_mask(radius_px, edge_alpha, base_alpha=0, margin_px=2 * S.TILE):
    """Degradê radial de escuridão: base_alpha no centro, edge_alpha na borda
    do raio e além dela (até margin_px fora do raio)."""
    half = radius_px + margin_px
    surf = pygame.Surface((2 * half, 2 * half), pygame.SRCALPHA)
    surf.fill((0, 0, 0, edge_alpha))
    center = (half, half)
    # círculos de fora para dentro; draw.circle substitui os pixels
    for r in range(radius_px, 0, -2):
        p = (r / radius_px) ** 1.6          # mais claro no meio, cai perto da borda
        alpha = round(base_alpha + (edge_alpha - base_alpha) * p)
        pygame.draw.circle(surf, (0, 0, 0, alpha), center, r)
    return surf


class Light:
    """Luz em volta do personagem, com tremulação opcional."""

    LEVELS = (0, 12, 24, 40)        # escuridão extra no centro (tremulação)

    def __init__(self, radius_px):
        edge = S.LIGHT_EDGE_ALPHA
        self.masks = [build_light_mask(radius_px, min(255, edge + base), base)
                      for base in self.LEVELS]
        self.level = 0
        self.timer = 0.0
        self.rng = random.Random()

    def update(self, dt):
        if not S.LIGHT_FLICKER:
            self.level = 0
            return
        self.timer -= dt
        if self.timer > 0:
            return
        self.timer = 0.08
        r = self.rng.random()
        # quase sempre estável; de vez em quando uma piscada rápida
        self.level = 3 if r < 0.03 else 2 if r < 0.08 else 1 if r < 0.25 else 0

    def draw(self, surf, center):
        """Escurece em volta do personagem. Fora do quadrado da máscara (que
        já passa 2 tiles além do raio de visão) quem escurece é a névoa."""
        mask = self.masks[self.level]
        surf.blit(mask, mask.get_rect(center=center))
