"""Itens no chão: por enquanto o kit médico.

Cada sala tem MEDKIT_ROOM_CHANCE de ter um kit flutuando num tile de chão.
O personagem coleta com Espaço em cima dele (veja `Game.action`) e usa com
H (`Player.request_heal`). Itens não bloqueiam ninguém.

A lógica não precisa de janela; só `MedKit.draw` usa as superfícies.
"""
import math
import random

import pygame

import settings as S
from player import tile_center


class MedKit:
    def __init__(self, tile):
        self.tile = tuple(tile)
        self.x, self.y = tile_center(self.tile)
        self.phase = random.Random(hash(self.tile)).uniform(0, 2 * math.pi)   # kits fora de sincronia

    def frame(self, t, count):
        return int(t * S.MEDKIT_ANIM_FPS) % count

    def bob(self, t):
        """Altura do flutuar (0..1)."""
        return 0.5 + 0.5 * math.sin(t * 2.4 + self.phase)

    def feet_y(self):
        return self.y + S.TILE / 2 - 6

    _shadows = {}

    @classmethod
    def shadow(cls, k):
        """Sombra no chão; menor e mais clara quando o kit sobe (k 0..1)."""
        key = round(k * 4)
        if key not in cls._shadows:
            w, h = 20 - key, 6
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (0, 0, 0, 110 - key * 12), surf.get_rect())
            cls._shadows[key] = surf
        return cls._shadows[key]

    def draw(self, surf, camera, frames, t):
        k = self.bob(t)
        ground = (round(self.x - camera[0]), round(self.feet_y() - camera[1]))
        sh = self.shadow(k)
        surf.blit(sh, sh.get_rect(center=ground))
        img = frames[self.frame(t, len(frames))]
        lift = 5 + S.MEDKIT_BOB * 2 * k
        surf.blit(img, img.get_rect(midbottom=(ground[0], round(ground[1] - lift))))


def spawn_medkits(dungeon, avoid=(), taken=(), avoid_radius=2):
    """No máximo 1 kit por sala (chance MEDKIT_ROOM_CHANCE), num tile de chão
    da sala sem encostar em porta, longe do spawn (`avoid`) e fora dos tiles
    em `taken` (onde nascem zumbis). Determinístico pela seed."""
    rng = random.Random(dungeon.seed ^ 0x3D1C)
    door_near = {(x + dx, y + dy) for (x, y) in dungeon.door_at
                 for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    taken = set(taken)
    kits = []
    for room in dungeon.rooms:
        if rng.random() >= S.MEDKIT_ROOM_CHANCE:
            continue
        cands = [(x, y) for y in range(room.y, room.y + room.h)
                 for x in range(room.x, room.x + room.w)
                 if dungeon.is_walkable(x, y) and (x, y) not in door_near and (x, y) not in taken
                 and all(max(abs(x - ax), abs(y - ay)) > avoid_radius for ax, ay in avoid)]
        if cands:
            kits.append(MedKit(rng.choice(cands)))
    return kits
