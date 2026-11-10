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


def explored_fog_alpha():
    """Alpha da névoa nos tiles já descobertos.

    A luz escurece a tela inteira com pelo menos LIGHT_EDGE_ALPHA fora do raio
    de visão, e a névoa é desenhada por cima. Para o resultado final dos tiles
    descobertos continuar sendo FOG_EXPLORED_ALPHA, a névoa usa só o que falta:
    1 - (1 - alvo) / (1 - luz).
    """
    target = S.FOG_EXPLORED_ALPHA / 255
    light = S.LIGHT_EDGE_ALPHA / 255
    if light >= target:
        return 0
    return round(255 * (1 - (1 - target) / (1 - light)))


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
        dim = (*S.COLOR_UNEXPLORED, explored_fog_alpha())
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
        self.edges = [min(255, edge + base) for base in self.LEVELS]
        self.masks = [build_light_mask(radius_px, e, base)
                      for e, base in zip(self.edges, self.LEVELS)]
        self.level = 0
        self.timer = 0.0
        self.rng = random.Random()
        self._solids = {}   # (nível, tamanho da tela) -> superfície sólida da escuridão da borda

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

    def _solid(self, size):
        key = (self.level, size)
        if key not in self._solids:
            solid = pygame.Surface(size, pygame.SRCALPHA)
            solid.fill((0, 0, 0, self.edges[self.level]))
            self._solids[key] = solid
        return self._solids[key]

    def draw(self, surf, center):
        """Escurece a tela: degradê em volta do personagem e, fora do quadrado
        da máscara, a mesma escuridão da borda — sem emenda entre as duas."""
        mask = self.masks[self.level]
        rect = mask.get_rect(center=center)
        surf.blit(mask, rect)
        if self.edges[self.level] == 0:
            return
        w, h = surf.get_size()
        solid = self._solid((w, h))
        top = max(0, min(h, rect.top))
        bottom = max(0, min(h, rect.bottom))
        left = max(0, min(w, rect.left))
        right = max(0, min(w, rect.right))
        # 4 faixas ao redor do quadrado (a superfície sólida é reaproveitada)
        for r in (pygame.Rect(0, 0, w, top),
                  pygame.Rect(0, bottom, w, h - bottom),
                  pygame.Rect(0, top, left, bottom - top),
                  pygame.Rect(right, top, w - right, bottom - top)):
            if r.w > 0 and r.h > 0:
                surf.blit(solid, r.topleft, r)
