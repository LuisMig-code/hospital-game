"""Zumbis: nascem enterrados nas salas, saem do chão quando o jogador os vê
e depois ficam vagando pela sala (andam alguns tiles numa das 8 direções,
retas ou diagonais, param um pouco...).
Têm vida: levam dano dos golpes do personagem e, ao morrer, afundam de
volta no chão (a animação de surgir ao contrário).

A lógica não desenha nada e não precisa de janela; só `Zombie.draw` usa as
superfícies das animações.
"""
import math
import random

import pygame

import settings as S
from player import Player, tile_center
from sprites import ZOMBIE_ROWS

DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}
# 8 direções de caminhada (retas e diagonais)
MOVES = [(1, 0), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 1), (-1, 1), (-1, -1)]


def facing_for(dx, dy):
    """Sprite para um movimento (só há 4 direções; na diagonal vale a horizontal)."""
    if dx:
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"
FRAMES = {name: count for _, name, count in ZOMBIE_ROWS}

UNDERGROUND, EMERGING, IDLE, WALK = "underground", "emerging", "idle", "walk"
DYING, DEAD = "dying", "dead"
SOLID_STATES = (EMERGING, IDLE, WALK)      # bloqueiam e podem levar dano


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
        self.move = (0, 1)                     # direção da caminhada atual (pode ser diagonal)
        self.timer = 0.0
        self.steps_left = 0
        self.anim = "emerge"
        self.frame = 0
        self.frame_time = 0.0
        self.time_in = {IDLE: 0.0, WALK: 0.0}   # estatística (usada nos testes)
        self.hp = S.ZOMBIE_HP
        self.flash = 0.0        # tempo restante piscando (levou dano)
        self.hp_bar = 0.0       # tempo restante mostrando a barra de vida

    @property
    def active(self):
        """Fora do chão e ainda na tela (inclusive morrendo): é desenhado."""
        return self.state not in (UNDERGROUND, DEAD)

    @property
    def solid(self):
        """Ocupa o tile: bloqueia o personagem/outros zumbis e leva dano."""
        return self.state in SOLID_STATES

    def occupied(self):
        """Tiles que o zumbi ocupa (o atual e, andando, o de destino)."""
        return {self.tile} if self.target is None else {self.tile, self.target}

    def wake(self):
        self.state = EMERGING
        self.anim, self.frame, self.frame_time = "emerge", 0, 0.0

    def hit(self, damage):
        """Leva dano. Devolve True se morreu com este golpe."""
        if not self.solid:
            return False
        self.hp -= damage
        self.flash = S.HIT_FLASH_TIME
        self.hp_bar = S.HP_BAR_TIME
        if self.hp <= 0:
            self.hp = 0
            self.state = DYING
            self.target = None
            self.anim, self.frame, self.frame_time = "emerge", FRAMES["emerge"] - 1, 0.0
            return True
        return False

    # ----------------------------------------------------------------- lógica
    def _can_enter(self, tile, dungeon, blocked):
        return in_room(self.room, tile) and dungeon.is_walkable(*tile) and tile not in blocked

    def _can_step(self, move, dungeon, blocked):
        """Passo reto ou diagonal. A diagonal não corta quina: os dois tiles
        retos que ela atravessa também têm que ser chão da sala."""
        dx, dy = move
        x, y = self.tile
        if not self._can_enter((x + dx, y + dy), dungeon, blocked):
            return False
        if dx and dy:
            for t in ((x + dx, y), (x, y + dy)):
                if not (in_room(self.room, t) and dungeon.is_walkable(*t)):
                    return False
        return True

    def _go_idle(self, rng):
        self.state = IDLE
        self.target = None
        self.timer = rng.uniform(*S.ZOMBIE_IDLE_TIME)

    def _start_walk(self, dungeon, blocked, rng):
        moves = list(MOVES)
        rng.shuffle(moves)
        for move in moves:
            if self._can_step(move, dungeon, blocked):
                self.move = move
                self.facing = facing_for(*move)
                self.steps_left = rng.randint(*S.ZOMBIE_WANDER_STEPS)
                self.state = WALK
                return
        # cercado: espera um pouco e tenta de novo
        self.state = IDLE
        self.timer = rng.uniform(0.1, 0.3)

    def update(self, dt, dungeon, blocked, rng):
        """blocked: tiles ocupados pelo personagem e pelos outros zumbis."""
        if self.state in (UNDERGROUND, DEAD):
            return
        self.flash = max(0.0, self.flash - dt)
        self.hp_bar = max(0.0, self.hp_bar - dt)

        if self.state == DYING:
            # surgir ao contrário: afunda de volta no chão
            self.frame_time += dt
            frame = FRAMES["emerge"] - 1 - int(self.frame_time * S.ZOMBIE_DEATH_FPS)
            if frame < 0:
                self.state = DEAD
            self.frame = max(0, frame)
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
                dx, dy = self.move
                if self.steps_left > 0 and self._can_step(self.move, dungeon, blocked):
                    self.target = (self.tile[0] + dx, self.tile[1] + dy)
                else:
                    self._go_idle(rng)
            if self.target is not None:
                tx, ty = tile_center(self.target)
                step = S.ZOMBIE_SPEED * dt
                dist = math.hypot(tx - self.x, ty - self.y)   # reto ou diagonal: mesma velocidade
                if step >= dist:
                    self.x, self.y = tx, ty
                    self.tile, self.target = self.target, None
                    self.steps_left -= 1
                else:
                    k = step / dist
                    self.x += (tx - self.x) * k
                    self.y += (ty - self.y) * k
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
        sunk = self.state in (EMERGING, DYING) and self.frame < 4
        if not sunk:   # buraco no chão não tem sombra
            shadow = Player.shadow()
            surf.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] - 3)))
        if self.flash > 0:   # pisca claro/avermelhado ao levar dano
            img = img.copy()
            img.fill((150, 70, 60), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(img, img.get_rect(midbottom=feet))
        if self.hp_bar > 0 and self.solid:
            self.draw_hp_bar(surf, feet)

    def draw_hp_bar(self, surf, feet):
        """Barrinha de vida acima da cabeça (some HP_BAR_TIME s após o golpe)."""
        w, h = 26, 4
        x, y = feet[0] - w // 2, feet[1] - S.ZOMBIE_SIZE + 6
        pygame.draw.rect(surf, (15, 10, 10), (x - 1, y - 1, w + 2, h + 2))
        fill = round(w * self.hp / S.ZOMBIE_HP)
        color = (90, 200, 70) if self.hp > S.ZOMBIE_HP / 2 else (230, 170, 40) if self.hp > S.ZOMBIE_HP / 4 else (220, 50, 40)
        pygame.draw.rect(surf, color, (x, y, fill, h))


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
        self.killed = 0

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
                if o is not z and o.solid:
                    others |= o.occupied()
            z.update(dt, self.dungeon, player_occ | others, self.rng)
        # quem terminou de afundar sai do jogo
        dead = [z for z in self.zombies if z.state == DEAD]
        if dead:
            self.killed += len(dead)
            self.zombies = [z for z in self.zombies if z.state != DEAD]

    def blocked_tiles(self):
        """Tiles que o personagem não pode ocupar (zumbis fora do chão e vivos)."""
        tiles = set()
        for z in self.zombies:
            if z.solid:
                tiles |= z.occupied()
        return tiles

    def active(self):
        """Zumbis que aparecem na tela (inclusive os que estão morrendo)."""
        return [z for z in self.zombies if z.active]
