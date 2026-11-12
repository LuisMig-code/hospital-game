"""Zumbis: nascem enterrados nas salas, saem do chão quando o jogador os vê
e depois ficam vagando pela sala (andam alguns tiles numa das 8 direções,
retas ou diagonais, param um pouco...).
Com o personagem a até ZOMBIE_CHASE_RADIUS tiles, vão atrás dele (podem
sair da sala por portas abertas) e, colados nele, preparam e dão o golpe.
Têm vida: levam dano dos golpes do personagem e, ao morrer, afundam de
volta no chão (a animação de surgir ao contrário).

A lógica não desenha nada e não precisa de janela; só `Zombie.draw` usa as
superfícies das animações.
"""
import math
import random
from collections import deque

import pygame

import settings as S
from player import Player, tile_center
from sprites import zombie_frames, zombie_low_frame

DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}
# 8 direções de caminhada (retas e diagonais)
MOVES = [(1, 0), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 1), (-1, 1), (-1, -1)]


def facing_for(dx, dy):
    """Sprite para um movimento (só há 4 direções; na diagonal vale a horizontal)."""
    if dx:
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


FRAMES = zombie_frames("classic")           # quadros do zumbi clássico (cada tipo: zombie_frames)

UNDERGROUND, EMERGING, IDLE, WALK, CHASE = "underground", "emerging", "idle", "walk", "chase"
DYING, DEAD = "dying", "dead"
SOLID_STATES = (EMERGING, IDLE, WALK, CHASE)      # bloqueiam e podem levar dano


def in_room(room, tile):
    x, y = tile
    return room.x <= x < room.x + room.w and room.y <= y < room.y + room.h


def chebyshev(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def can_step(dungeon, tile, move):
    """Passo de `tile` em `move` sem cortar quina: na diagonal, os dois
    tiles retos atravessados também têm que ser andáveis."""
    (x, y), (dx, dy) = tile, move
    if not dungeon.is_walkable(x + dx, y + dy):
        return False
    return not (dx and dy) or (dungeon.is_walkable(x + dx, y) and dungeon.is_walkable(x, y + dy))


def touching(dungeon, a, b):
    """`a` e `b` são vizinhos (reto ou diagonal sem quina de parede no meio):
    dá para o zumbi em `a` acertar quem está em `b`."""
    if chebyshev(a, b) != 1:
        return False
    return can_step(dungeon, a, (b[0] - a[0], b[1] - a[1]))


def chase_step(dungeon, start, goal, blocked, limit):
    """Primeiro passo do caminho mais curto (8 direções, sem cortar quina,
    sem passar por `blocked`) de `start` até um tile colado em `goal`.
    Só procura tiles a até `limit` de `goal`. None se não há caminho."""
    if touching(dungeon, start, goal):
        return None
    first = {start: None}
    queue = deque([start])
    while queue:
        tile = queue.popleft()
        for move in MOVES:                       # retos primeiro: caminho mais "reto"
            nxt = (tile[0] + move[0], tile[1] + move[1])
            if nxt in first or nxt in blocked or nxt == goal or chebyshev(nxt, goal) > limit:
                continue
            if not can_step(dungeon, tile, move):
                continue
            first[nxt] = first[tile] or move
            if touching(dungeon, nxt, goal):
                return first[nxt]
            queue.append(nxt)
    return None


def room_at(dungeon, tile):
    return next((r for r in dungeon.rooms if in_room(r, tile)), None)


class Zombie:
    def __init__(self, tile, room, kind="classic"):
        self.kind = kind                       # tipo (settings.ZOMBIE_KINDS): aparência e atributos
        self.stats = S.ZOMBIE_KINDS[kind]
        self.frames = zombie_frames(kind)
        self.tile = tuple(tile)
        self.target = None
        self.room = room                       # onde vaga (muda depois de uma perseguição)
        self.home = room                       # sala onde nasceu (não muda; mapa: sala com inimigos)
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
        self.hp = self.max_hp = self.stats["hp"]
        self.damage = self.stats["damage"]
        self.fade = 1.0         # opacidade (o corpo some depois de cair)
        self.flash = 0.0        # tempo restante piscando (levou dano)
        self.hp_bar = 0.0       # tempo restante mostrando a barra de vida
        self.windup = None      # preparando o golpe: segundos que faltam
        self.cooldown = 0.0     # espera depois de um golpe
        self.lunge = 0.0        # avanço visual do golpe (0..1)
        self.lunge_dir = (0, 1)
        self.knock_from = None  # (x, y) de onde começou o empurrão (levou golpe)
        self.knock_time = 0.0

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
            self.windup, self.lunge = None, 0.0
            self.knock_from = None             # morre onde estiver (afunda ali)
            self.anim, self.frame, self.frame_time = "death", 0, 0.0
            return True
        return False

    KNOCKABLE = (IDLE, WALK, CHASE)

    def knock_back(self, source, dungeon, blocked=frozenset()):
        """Levou golpe vindo de `source` (tile do personagem) e sobreviveu:
        é lançado 1 tile para o lado oposto (8 direções). Diagonal bloqueada
        tenta os eixos; parede, porta fechada, quina ou alguém atrás: fica.
        Cancela o passo e o preparo do golpe. Devolve True se foi lançado."""
        if self.state not in self.KNOCKABLE or self.knock_from is not None:
            return False
        x, y = self.tile = self.pixel_tile()      # no meio de um passo: o tile desenhado
        self.target = None
        self.windup = None
        self.steps_left = 0
        dx = (x > source[0]) - (x < source[0])
        dy = (y > source[1]) - (y < source[1])
        if not (dx or dy):
            return False
        cands = ([(dx, dy)] if dx and dy else []) + ([(dx, 0)] if dx else []) + ([(0, dy)] if dy else [])
        for move in cands:
            dest = (x + move[0], y + move[1])
            if dest not in blocked and can_step(dungeon, (x, y), move):
                self.target = dest
                self.knock_from, self.knock_time = (self.x, self.y), 0.0
                return True
        # não foi lançado: encaixa no centro do tile (estava no meio de um passo)
        self.x, self.y = tile_center(self.tile)
        return False

    def _update_knock(self, dt, dungeon):
        """Voo do empurrão (desacelerando). Ao cair, passa a vagar/perseguir
        a partir dali; se caiu fora da sala, a "sala" dele é onde está."""
        self.knock_time += dt
        p = min(1.0, self.knock_time / S.ZOMBIE_KNOCKBACK_TIME)
        ease = 1 - (1 - p) ** 2
        (x0, y0), (tx, ty) = self.knock_from, tile_center(self.target)
        self.x, self.y = x0 + (tx - x0) * ease, y0 + (ty - y0) * ease
        if p >= 1:
            self.x, self.y = tx, ty
            self.tile, self.target = self.target, None
            self.knock_from = None
            if self.room is None or not in_room(self.room, self.tile):
                self.room = room_at(dungeon, self.tile)

    # ----------------------------------------------------------------- lógica
    def _in_area(self, tile, dungeon):
        """Onde o zumbi vaga: a sala dele; fora de sala (depois de uma
        perseguição), o corredor — qualquer chão menos as portas."""
        if self.room is None:
            return tile not in dungeon.door_at
        return in_room(self.room, tile)

    def _can_enter(self, tile, dungeon, blocked):
        return self._in_area(tile, dungeon) and dungeon.is_walkable(*tile) and tile not in blocked

    def _can_step(self, move, dungeon, blocked):
        """Passo reto ou diagonal. A diagonal não corta quina: os dois tiles
        retos que ela atravessa também têm que ser chão da área."""
        dx, dy = move
        x, y = self.tile
        if not self._can_enter((x + dx, y + dy), dungeon, blocked):
            return False
        if dx and dy:
            for t in ((x + dx, y), (x, y + dy)):
                if not (self._in_area(t, dungeon) and dungeon.is_walkable(*t)):
                    return False
        return True

    def _start_chase(self):
        self.state = CHASE
        self.windup = None

    def _end_chase(self, dungeon, rng):
        """Personagem longe: volta a vagar na sala (ou corredor) onde está."""
        self.windup = None
        self.room = room_at(dungeon, self.tile)
        self._go_idle(rng)

    def _update_chase(self, dt, dungeon, blocked, player_tile):
        """Parado num tile: colado no personagem prepara/dá o golpe; senão
        dá o próximo passo do caminho até ele. Devolve True no golpe."""
        px, py = player_tile
        if touching(dungeon, self.tile, player_tile):
            dx, dy = px - self.tile[0], py - self.tile[1]
            self.facing = facing_for(dx, dy)
            self.lunge_dir = (dx, dy)
            if self.windup is None:
                if self.cooldown <= 0:
                    self.windup = S.ZOMBIE_ATTACK_WINDUP
                return False
            self.windup -= dt
            if self.windup <= 0:
                self.windup = None
                self.cooldown = S.ZOMBIE_ATTACK_COOLDOWN
                self.lunge = 1.0
                return True
            return False
        self.windup = None                     # o personagem saiu de perto
        step = chase_step(dungeon, self.tile, player_tile, blocked,
                          S.ZOMBIE_CHASE_RADIUS + S.ZOMBIE_CHASE_SEARCH)
        if step is None:                       # sem caminho: espera virado para ele
            self.facing = facing_for(px - self.tile[0], py - self.tile[1])
        else:
            self.move = step
            self.facing = facing_for(*step)
            self.target = (self.tile[0] + step[0], self.tile[1] + step[1])
        return False

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

    def update(self, dt, dungeon, blocked, rng, player_tile=None):
        """blocked: tiles ocupados pelo personagem e pelos outros zumbis.
        player_tile: onde o personagem está (None: morto/ausente, não persegue).
        Devolve True quando o golpe do zumbi acerta neste quadro."""
        if self.state in (UNDERGROUND, DEAD):
            return False
        self.flash = max(0.0, self.flash - dt)
        self.hp_bar = max(0.0, self.hp_bar - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.lunge = max(0.0, self.lunge - dt / 0.2)

        if self.state == DYING:
            # clássico: afunda de volta no buraco; os outros caem e o corpo some
            self.frame_time += dt
            n = self.frames["death"]
            fall = n / self.stats["death_fps"]
            self.frame = min(n - 1, int(self.frame_time * self.stats["death_fps"]))
            corpse = self.stats["corpse_time"]
            if corpse > 0:
                self.fade = max(0.0, min(1.0, 1 - (self.frame_time - fall) / corpse))
            if self.frame_time >= fall + corpse:
                self.state = DEAD
            return False
        if self.state == EMERGING:
            self.frame_time += dt
            if self.frame_time * self.stats["rise_fps"] >= self.frames["emerge"]:
                self._go_idle(rng)
            self._animate(0)
            return False
        if self.knock_from is not None:        # sendo lançado pelo golpe
            self._update_knock(dt, dungeon)
            self._animate(dt)
            return False

        # Perto do personagem persegue; longe, volta a vagar. A troca só
        # acontece parado num tile (nunca no meio de um passo).
        hit = False
        if self.target is None:
            near = player_tile is not None and chebyshev(self.tile, player_tile) <= S.ZOMBIE_CHASE_RADIUS
            if near and self.state != CHASE:
                self._start_chase()
            elif not near and self.state == CHASE:
                self._end_chase(dungeon, rng)
            elif self.state != CHASE and self.room is None and room_at(dungeon, self.tile):
                self.room = room_at(dungeon, self.tile)   # do corredor entrou numa sala: vaga nela

        if self.state == CHASE:
            if self.target is None:
                hit = self._update_chase(dt, dungeon, blocked, player_tile)
        elif self.state == IDLE:
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
            if self.state == CHASE:
                self.time_in[WALK] += dt
            tx, ty = tile_center(self.target)
            speed = self.stats["chase_speed"] if self.state == CHASE else self.stats["speed"]
            if self.target[0] != self.tile[0] and self.target[1] != self.tile[1]:   # passo diagonal
                # (cadeira de rodas: mais lenta na diagonal)
                speed *= self.stats["diagonal"]
            step = speed * dt
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
        return hit

    def _animate(self, dt):
        if self.state == EMERGING:
            anim = "emerge"
            frame = min(self.frames["emerge"] - 1, int(self.frame_time * self.stats["rise_fps"]))
        else:
            walking = self.state == WALK or (self.state == CHASE and self.target is not None)
            anim = f"walk_{self.facing}" if walking else "idle"
            if not walking and self.facing != "down" and f"idle_{self.facing}" in self.frames:
                anim = f"idle_{self.facing}"         # parado virado para o lado/costas
            if anim != self.anim:
                self.anim, self.frame_time = anim, 0.0
            self.frame_time += dt
            frame = int(self.frame_time * self.stats["anim_fps"]) % self.frames[anim]
        self.anim, self.frame = anim, frame

    # ---------------------------------------------------------------- desenho
    def pixel_tile(self):
        """Tile onde o zumbi está desenhado agora (muda no meio do passo)."""
        return (int(self.x // S.TILE), int(self.y // S.TILE))

    def feet_y(self):
        return self.y + S.TILE / 2

    def attack_offset(self):
        """Deslocamento visual do golpe (o sheet não tem animação de ataque):
        preparando, recua um pouco; no golpe, avança para o personagem."""
        dx, dy = self.lunge_dir
        n = math.hypot(dx, dy) or 1.0
        if self.windup is not None:
            k = -2.5 * (1 - self.windup / S.ZOMBIE_ATTACK_WINDUP)
        else:
            k = S.ZOMBIE_LUNGE * self.lunge
        return dx / n * k, dy / n * k

    def draw(self, surf, camera, anims):
        img = anims[self.anim][self.frame]
        ox, oy = self.attack_offset()
        feet = (round(self.x + ox - camera[0]), round(self.feet_y() + oy - camera[1]))
        sunk = self.state in (EMERGING, DYING) and zombie_low_frame(self.kind, self.anim, self.frame)
        if not sunk:   # buraco no chão (ou corpo caído) não tem sombra
            shadow = Player.shadow()
            surf.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] - 3)))
        if self.flash > 0:   # pisca claro/avermelhado ao levar dano
            img = img.copy()
            img.fill((150, 70, 60), special_flags=pygame.BLEND_RGB_ADD)
        if self.fade < 1.0:   # corpo sumindo
            img = img.copy()
            img.set_alpha(round(255 * self.fade))
        surf.blit(img, img.get_rect(midbottom=feet))
        if self.hp_bar > 0 and self.solid:
            self.draw_hp_bar(surf, feet)

    def draw_hp_bar(self, surf, feet):
        """Barrinha de vida acima da cabeça (some HP_BAR_TIME s após o golpe)."""
        w, h = 26, 4
        x, y = feet[0] - w // 2, feet[1] - S.ZOMBIE_SIZE + 6
        pygame.draw.rect(surf, (15, 10, 10), (x - 1, y - 1, w + 2, h + 2))
        ratio = self.hp / self.max_hp
        fill = round(w * ratio)
        color = (90, 200, 70) if ratio > 1 / 2 else (230, 170, 40) if ratio > 1 / 4 else (220, 50, 40)
        pygame.draw.rect(surf, color, (x, y, fill, h))


def spawn_zombies(dungeon, avoid=(), avoid_radius=2):
    """3–5 zumbis enterrados por sala, em tiles de chão distintos, longe do
    spawn do personagem (`avoid`) e sem encostar em portas. Determinístico
    pela seed. O tipo de cada um é sorteado pelos pesos do tema da sala
    (themes.Theme.zombies), com outro rng: as posições não dependem dos tipos."""
    rng = random.Random(dungeon.seed ^ 0x2B1E)
    kind_rng = random.Random(dungeon.seed ^ 0x7C1D)
    door_near = {(x + dx, y + dy) for (x, y) in dungeon.door_at
                 for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    zombies = []
    for room in dungeon.rooms:
        cands = [(x, y) for y in range(room.y, room.y + room.h)
                 for x in range(room.x, room.x + room.w)
                 if dungeon.is_walkable(x, y) and (x, y) not in door_near
                 and all(max(abs(x - ax), abs(y - ay)) > avoid_radius for ax, ay in avoid)]
        n = min(rng.randint(*S.ZOMBIES_PER_ROOM), len(cands))
        kinds, weights = zip(*zombie_weights(getattr(room, "theme", None)))
        for tile in rng.sample(cands, n):
            zombies.append(Zombie(tile, room, kind_rng.choices(kinds, weights)[0]))
    return zombies


def zombie_weights(theme):
    """[(tipo, peso), ...] do tema da sala (sem tema: todos iguais)."""
    from themes import THEMES
    t = THEMES.get(theme)
    if t is None or not t.zombies:
        return [(k, 1) for k in S.ZOMBIE_KINDS]
    return list(t.zombies)


class Horde:
    """Todos os zumbis da dungeon."""

    def __init__(self, dungeon, avoid=()):
        self.dungeon = dungeon
        self.zombies = spawn_zombies(dungeon, avoid)
        self.rng = random.Random(dungeon.seed ^ 0x5A5A)
        self.killed = 0

    def update(self, dt, player, visible):
        """Atualiza todos. Devolve os zumbis cujo golpe acertou o personagem
        neste quadro (main aplica o dano)."""
        player_occ = {player.tile} if player.target is None else {player.tile, player.target}
        alive = not getattr(player, "dead", False)
        player_tile = player.pixel_tile() if alive else None
        hits = []
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
            if z.update(dt, self.dungeon, player_occ | others, self.rng, player_tile):
                hits.append(z)
        # quem terminou de afundar sai do jogo
        dead = [z for z in self.zombies if z.state == DEAD]
        if dead:
            self.killed += len(dead)
            self.zombies = [z for z in self.zombies if z.state != DEAD]
        return hits

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
