"""Zumbis: nascem enterrados nas salas, saem do chão quando o jogador os vê
e depois ficam vagando pela sala (andam alguns tiles, param um pouco...).

A lógica não desenha nada e não precisa de janela; só `Zombie.draw` usa as
superfícies das animações.
"""
import random

import settings as S
from player import Player, tile_center
from sprites import ZOMBIE_ROWS

DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}
FRAMES = {name: count for _, name, count in ZOMBIE_ROWS}

UNDERGROUND, EMERGING, IDLE, WALK = "underground", "emerging", "idle", "walk"


def in_room(room, tile):
    x, y = tile
    return room.x <= x < room.x + room.w and room.y <= y < room.y + room.h


class Zombie:
    def __init__(self, tile, room):
        self.tile = tuple(tile)
        self.target = None
        self.room = room
        self.x, self.y = tile_center(self.tile)
        self.state = UNDERGROUND
        self.facing = "down"
        self.timer = 0.0
        self.steps_left = 0
        self.anim = "emerge"
        self.frame = 0
        self.frame_time = 0.0
        self.time_in = {IDLE: 0.0, WALK: 0.0}   # estatística (usada nos testes)

    @property
    def active(self):
        """Fora do chão: aparece, bloqueia e se move."""
        return self.state != UNDERGROUND

    def occupied(self):
        """Tiles que o zumbi ocupa (o atual e, andando, o de destino)."""
        return {self.tile} if self.target is None else {self.tile, self.target}

    def wake(self):
        self.state = EMERGING
        self.anim, self.frame, self.frame_time = "emerge", 0, 0.0

    # ----------------------------------------------------------------- lógica
    def _can_enter(self, tile, dungeon, blocked):
        return in_room(self.room, tile) and dungeon.is_walkable(*tile) and tile not in blocked

    def _go_idle(self, rng):
        self.state = IDLE
        self.target = None
        self.timer = rng.uniform(*S.ZOMBIE_IDLE_TIME)

    def _start_walk(self, dungeon, blocked, rng):
        dirs = list(DIRS)
        rng.shuffle(dirs)
        for d in dirs:
            dx, dy = DIRS[d]
            if self._can_enter((self.tile[0] + dx, self.tile[1] + dy), dungeon, blocked):
                self.facing = d
                self.steps_left = rng.randint(*S.ZOMBIE_WANDER_STEPS)
                self.state = WALK
                return
        # cercado: espera um pouco e tenta de novo
        self.state = IDLE
        self.timer = rng.uniform(0.3, 1.0)

    def update(self, dt, dungeon, blocked, rng):
        """blocked: tiles ocupados pelo personagem e pelos outros zumbis."""
        if self.state == UNDERGROUND:
            return
        if self.state == EMERGING:
            self.frame_time += dt
            if self.frame_time * S.ZOMBIE_EMERGE_FPS >= FRAMES["emerge"]:
                self._go_idle(rng)
            self._animate(0)
            return

        if self.state == IDLE:
            self.time_in[IDLE] += dt
            self.timer -= dt
            if self.timer <= 0:
                self._start_walk(dungeon, blocked, rng)
        elif self.state == WALK:
            self.time_in[WALK] += dt
            if self.target is None:
                dx, dy = DIRS[self.facing]
                nxt = (self.tile[0] + dx, self.tile[1] + dy)
                if self.steps_left > 0 and self._can_enter(nxt, dungeon, blocked):
                    self.target = nxt
                else:
                    self._go_idle(rng)
            if self.target is not None:
                tx, ty = tile_center(self.target)
                step = S.ZOMBIE_SPEED * dt
                dist = abs(tx - self.x) + abs(ty - self.y)
                if step >= dist:
                    self.x, self.y = tx, ty
                    self.tile, self.target = self.target, None
                    self.steps_left -= 1
                else:
                    self.x += step * ((tx > self.x) - (tx < self.x))
                    self.y += step * ((ty > self.y) - (ty < self.y))
        self._animate(dt)

    def _animate(self, dt):
        if self.state == EMERGING:
            anim = "emerge"
            frame = min(FRAMES["emerge"] - 1, int(self.frame_time * S.ZOMBIE_EMERGE_FPS))
        else:
            anim = f"walk_{self.facing}" if self.state == WALK else "idle"
            if anim != self.anim:
                self.anim, self.frame_time = anim, 0.0
            self.frame_time += dt
            frame = int(self.frame_time * S.ZOMBIE_ANIM_FPS) % FRAMES[anim]
        self.anim, self.frame = anim, frame

    # ---------------------------------------------------------------- desenho
    def pixel_tile(self):
        """Tile onde o zumbi está desenhado agora (muda no meio do passo)."""
        return (int(self.x // S.TILE), int(self.y // S.TILE))

    def feet_y(self):
        return self.y + S.TILE / 2

    def draw(self, surf, camera, anims):
        img = anims[self.anim][self.frame]
        feet = (round(self.x - camera[0]), round(self.feet_y() - camera[1]))
        if self.state != EMERGING or self.frame >= 4:   # buraco no chão não tem sombra
            shadow = Player.shadow()
            surf.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] - 3)))
        surf.blit(img, img.get_rect(midbottom=feet))


def spawn_zombies(dungeon, avoid=(), avoid_radius=2):
    """3–5 zumbis enterrados por sala, em tiles de chão distintos, longe do
    spawn do personagem (`avoid`) e sem encostar em portas. Determinístico
    pela seed."""
    rng = random.Random(dungeon.seed ^ 0x2B1E)
    door_near = {(x + dx, y + dy) for (x, y) in dungeon.door_at
                 for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    zombies = []
    for room in dungeon.rooms:
        cands = [(x, y) for y in range(room.y, room.y + room.h)
                 for x in range(room.x, room.x + room.w)
                 if dungeon.is_walkable(x, y) and (x, y) not in door_near
                 and all(max(abs(x - ax), abs(y - ay)) > avoid_radius for ax, ay in avoid)]
        n = min(rng.randint(*S.ZOMBIES_PER_ROOM), len(cands))
        for tile in rng.sample(cands, n):
            zombies.append(Zombie(tile, room))
    return zombies


class Horde:
    """Todos os zumbis da dungeon."""

    def __init__(self, dungeon, avoid=()):
        self.dungeon = dungeon
        self.zombies = spawn_zombies(dungeon, avoid)
        self.rng = random.Random(dungeon.seed ^ 0x5A5A)

    def update(self, dt, player, visible):
        player_occ = {player.tile} if player.target is None else {player.tile, player.target}
        # acorda os que o jogador está vendo (se ele não estiver em cima)
        for z in self.zombies:
            if z.state == UNDERGROUND and z.tile in visible and z.tile not in player_occ:
                z.wake()
        for z in self.zombies:
            if not z.active:
                continue
            others = set()
            for o in self.zombies:
                if o is not z and o.active:
                    others |= o.occupied()
            z.update(dt, self.dungeon, player_occ | others, self.rng)

    def blocked_tiles(self):
        """Tiles que o personagem não pode ocupar (zumbis fora do chão)."""
        tiles = set()
        for z in self.zombies:
            if z.active:
                tiles |= z.occupied()
        return tiles

    def active(self):
        return [z for z in self.zombies if z.active]
