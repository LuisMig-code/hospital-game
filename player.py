"""Jogador: movimento tile a tile no grid, corrida com estamina e animação."""
import pygame

import settings as S

DIRS = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),
    "down": (0, 1),
}


def _read_direction(keys):
    """Uma direção por vez (sem diagonal); horizontal tem prioridade."""
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        return "right"
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        return "left"
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        return "up"
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        return "down"
    return None


def tile_center(tile):
    return (tile[0] * S.TILE + S.TILE / 2, tile[1] * S.TILE + S.TILE / 2)


class Player:
    def __init__(self, anims, tile_pos):
        self.anims = anims
        self.tile = tuple(tile_pos)        # tile onde o jogador está (ou de onde saiu)
        self.target = None                 # tile para onde está indo
        self.x, self.y = tile_center(self.tile)
        self.facing = "down"
        self.moving = False
        self.running = False
        self.stamina = float(S.STAMINA_MAX)
        self.exhausted = False             # zerou a estamina: não corre até recuperar
        self.anim = "idle"
        self.frame_time = 0.0
        self.frame = 0

    # ------------------------------------------------------------------ input
    def _try_start_step(self, keys, dungeon, blocked=frozenset()):
        """Se uma direção está pressionada, vira para ela e, se o tile vizinho
        é chão, começa a andar até ele."""
        d = _read_direction(keys)
        if d is None:
            return
        self.facing = d
        dx, dy = DIRS[d]
        nxt = (self.tile[0] + dx, self.tile[1] + dy)
        if dungeon.is_walkable(*nxt) and nxt not in blocked:
            self.target = nxt

    def _wants_run(self, keys):
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if self.exhausted and self.stamina >= S.STAMINA_RECOVER_TO_RUN:
            self.exhausted = False
        return shift and not self.exhausted and self.stamina > 0

    # ----------------------------------------------------------------- update
    def update(self, dt, keys, dungeon, blocked=frozenset()):
        """blocked: tiles ocupados por outros (zumbis) — não dá para entrar."""
        budget = dt
        self.moving = False

        if self.target is None:
            self._try_start_step(keys, dungeon, blocked)

        # Consome o tempo do frame andando; ao chegar num tile, encaixa
        # exatamente nele e (se a tecla continua pressionada) segue para o próximo.
        while self.target is not None and budget > 1e-9:
            self.moving = True
            self.running = self._wants_run(keys)
            speed = S.PLAYER_SPEED * (S.RUN_MULT if self.running else 1.0)
            tx, ty = tile_center(self.target)
            dist = abs(tx - self.x) + abs(ty - self.y)   # movimento é sempre em 1 eixo
            t = min(budget, dist / speed)
            self._spend_stamina(t)
            budget -= t
            if t * speed >= dist - 1e-6:
                self.x, self.y = tx, ty
                self.tile, self.target = self.target, None
                self._try_start_step(keys, dungeon, blocked)
            else:
                step = speed * t
                self.x += step * (1 if tx > self.x else -1 if tx < self.x else 0)
                self.y += step * (1 if ty > self.y else -1 if ty < self.y else 0)

        if self.target is None:
            self.running = False
            if budget > 0:  # tempo do frame em que ficou parado
                self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_IDLE * budget)

        self._animate(dt)

    def _spend_stamina(self, t):
        if self.running:
            self.stamina = max(0.0, self.stamina - S.STAMINA_DRAIN * t)
            if self.stamina <= 0:
                self.exhausted = True
        else:
            self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_WALK * t)

    def _animate(self, dt):
        anim = f"walk_{self.facing}" if self.moving else "idle"
        if anim != self.anim:
            self.anim, self.frame_time = anim, 0.0
        self.frame_time += dt * (S.RUN_MULT if self.running else 1.0)
        frames = self.anims[self.anim]
        self.frame = int(self.frame_time * S.ANIM_FPS) % len(frames)

    # ------------------------------------------------------------------- draw
    def feet(self):
        """Ponto dos pés em pixels do mundo (base do sprite)."""
        return (self.x, self.y + S.TILE / 2 - 4)

    def sprite_rect(self):
        """Retângulo do sprite atual em pixels do mundo."""
        img = self.anims[self.anim][self.frame]
        fx, fy = self.feet()
        return img.get_rect(midbottom=(round(fx), round(fy)))

    _shadow = None

    @classmethod
    def shadow(cls):
        """Elipse escura e suave sob os pés (criada uma vez)."""
        if cls._shadow is None:
            w, h = 28, 10
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            # elipses concêntricas: mais escuro no centro, borda suave
            for i in range(4):
                a = round(S.PLAYER_SHADOW_ALPHA * (i + 1) / 4)
                pygame.draw.ellipse(surf, (0, 0, 0, a), (i * 2, i, w - i * 4, h - i * 2))
            cls._shadow = surf
        return cls._shadow

    def draw(self, surf, camera):
        img = self.anims[self.anim][self.frame]
        fx, fy = self.feet()
        feet = (round(fx - camera[0]), round(fy - camera[1]))
        shadow = self.shadow()
        surf.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] + 1)))
        surf.blit(img, img.get_rect(midbottom=feet))
