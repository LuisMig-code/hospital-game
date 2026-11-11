"""Mobília das salas temáticas (sem pygame).

Chamado por `dungeon.generate` depois das portas. Cada sala recebe um tema
(a do spawn é sempre a Recepção) e móveis do tema:
1. encostados na parede de cima (a parede que aparece) e nas laterais;
2. nas salas grandes, 1–2 grupos no meio (mesa de cirurgia com foco...);
3. alguns soltos pela sala e detalhes no chão (sem colisão).

Regras de cada móvel: pegada inteira no chão da sala; longe das portas,
das aberturas e do spawn; e o chão livre da sala (com as aberturas)
continua conectado — nenhum móvel fecha passagem.
"""
from collections import deque
from dataclasses import dataclass

import settings as S
from themes import PROPS, SPAWN_THEME, THEMES


@dataclass(frozen=True)
class PlacedProp:
    name: str
    tile: tuple          # canto de cima à esquerda da pegada
    fw: int
    fh: int

    @property
    def tiles(self):
        x, y = self.tile
        return [(x + i, y + j) for j in range(self.fh) for i in range(self.fw)]

    @property
    def base_y(self):
        """Linha (em tiles) logo abaixo da pegada: a "base" para ordenar o desenho."""
        return self.tile[1] + self.fh


def _in_room(room, t):
    return room.x <= t[0] < room.x + room.w and room.y <= t[1] < room.y + room.h


class _RoomFurnisher:
    def __init__(self, dungeon, room, theme, rng, forbidden):
        self.d, self.room, self.theme, self.rng = dungeon, room, theme, rng
        self.forbidden = forbidden
        self.area = room.w * room.h
        self.budget = int(self.area * S.FURNITURE_DENSITY)
        self.used = 0
        r = room
        self.region = {(x, y) for y in range(r.y - 1, r.y + r.h + 1) for x in range(r.x - 1, r.x + r.w + 1)
                       if dungeon.is_floor(x, y)}

    # ------------------------------------------------------------ verificação
    def _splits(self, tiles):
        """Com `tiles` já bloqueados: os vizinhos livres deles ficaram
        separados (o móvel fechou uma passagem)? Busca em largura no chão
        livre da sala (com as aberturas), parando assim que acha todos."""
        blocked, region = self.d.blocked, self.region
        need = {nb for (x, y) in tiles for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if nb in region and nb not in blocked}
        if len(need) <= 1:
            return False
        start = need.pop()
        seen = {start}
        q = deque([start])
        while q:
            x, y = q.popleft()
            for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nb in region and nb not in seen and nb not in blocked:
                    seen.add(nb)
                    need.discard(nb)
                    if not need:
                        return False
                    q.append(nb)
        return True

    def _fits(self, tiles, gap=False):
        d = self.d
        for t in tiles:
            if (not _in_room(self.room, t) or not d.is_floor(*t) or t in d.door_at
                    or t in d.blocked or t in self.forbidden):
                return False
        if gap:   # no meio da sala: 1 tile livre em volta (não encosta em outro móvel)
            own = set(tiles)
            for x, y in tiles:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        n = (x + dx, y + dy)
                        if n not in own and n in d.blocked:
                            return False
        return True

    def place(self, name, tile, gap=False):
        """Tenta pôr o prop com o canto em `tile`. Devolve o PlacedProp ou None."""
        p = PROPS[name]
        pp = PlacedProp(name, tile, p.fw, p.fh)
        tiles = pp.tiles
        if self.used + len(tiles) > self.budget or not self._fits(tiles, gap):
            return None
        self.d.blocked.update(tiles)
        if self._splits(tiles):                      # fechou passagem: desfaz
            self.d.blocked.difference_update(tiles)
            return None
        self.used += len(tiles)
        self.d.props.append(pp)
        return pp

    # ------------------------------------------------------------- etapas
    def along_top(self):
        r, rng = self.room, self.rng
        x = r.x + rng.randint(0, 1)
        while x < r.x + r.w and self.used < self.budget * 0.55:
            name = rng.choice(self.theme.top)
            pp = self.place(name, (x, r.y))
            x += (pp.fw if pp else 1) + rng.choice((0, 0, 1, 1, 2))

    def along_sides(self):
        r, rng = self.room, self.rng
        for x in (r.x, r.x + r.w - 1):
            y = r.y + 2 + rng.randint(0, 1)
            while y < r.y + r.h - 1 and self.used < self.budget * 0.8:
                name = rng.choice(self.theme.side)
                p = PROPS[name]
                if p.fw != 1:
                    y += 1
                    continue
                pp = self.place(name, (x, y))
                y += (pp.fh if pp else 1) + rng.choice((1, 1, 2, 3))

    def center(self):
        r, rng = self.room, self.rng
        if r.w < 8 or r.h < 7 or not self.theme.center:
            return
        groups = 2 if self.area >= 110 else 1
        for _ in range(groups):
            group = rng.choice(self.theme.center)
            for _try in range(25):
                gx = rng.randint(r.x + 2, r.x + r.w - 4)
                gy = rng.randint(r.y + 2, r.y + r.h - 3)
                placed = []
                for name, dx, dy in group:
                    pp = self.place(name, (gx + dx, gy + dy), gap=not placed)
                    if pp is None:
                        break
                    placed.append(pp)
                if len(placed) == len(group):
                    break
                for pp in placed:                            # grupo incompleto: desfaz
                    self.remove(pp)

    def remove(self, pp):
        self.d.props.remove(pp)
        self.d.blocked.difference_update(pp.tiles)
        self.used -= len(pp.tiles)

    def loose(self):
        r, rng = self.room, self.rng
        if not self.theme.loose:
            return
        for _ in range(rng.randint(0, 2)):
            for _try in range(10):
                t = (rng.randint(r.x + 1, r.x + r.w - 2), rng.randint(r.y + 1, r.y + r.h - 2))
                if self.place(rng.choice(self.theme.loose), t, gap=True):
                    break

    def scatter(self):
        r, rng = self.room, self.rng
        if not self.theme.scatter:
            return
        taken = set(self.d.blocked) | {t for dec in self.d.decals for t in dec.tiles}
        for _ in range(rng.randint(1, 3)):
            name = rng.choice(self.theme.scatter)
            p = PROPS[name]
            for _try in range(10):
                t = (rng.randint(r.x, r.x + r.w - p.fw), rng.randint(r.y + 1, r.y + r.h - p.fh))
                dec = PlacedProp(name, t, p.fw, p.fh)
                if all(_in_room(r, u) and self.d.is_floor(*u) and u not in taken for u in dec.tiles):
                    self.d.decals.append(dec)
                    taken.update(dec.tiles)
                    break


def _forbidden(dungeon):
    """Tiles onde não vai móvel: até 2 tiles de uma porta, colado em qualquer
    abertura da sala (chão na linha da parede) e até 2 tiles do spawn."""
    out = set()
    for (x, y) in dungeon.door_at:
        out.update((x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3))
    for room in dungeon.rooms:
        ring = ([(x, room.y - 1) for x in range(room.x - 1, room.x + room.w + 1)]
                + [(x, room.y + room.h) for x in range(room.x - 1, room.x + room.w + 1)]
                + [(room.x - 1, y) for y in range(room.y, room.y + room.h)]
                + [(room.x + room.w, y) for y in range(room.y, room.y + room.h)])
        for (x, y) in ring:
            if dungeon.is_floor(x, y):
                out.update((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    sx, sy = dungeon.spawn
    out.update((sx + dx, sy + dy) for dx in range(-2, 3) for dy in range(-2, 3))
    for el in (dungeon.elevator_in, dungeon.elevator_out):   # frente dos elevadores livre
        if el is not None:
            for fx, fy in el.front:
                out.update((fx + dx, fy + dy) for dx in range(-2, 3) for dy in range(0, 3))
    return out


def spawn_room(dungeon):
    """Sala onde o personagem começa (ou a mais perto, se o spawn cair num corredor)."""
    sx, sy = dungeon.spawn
    return dungeon.room_at((sx, sy)) or min(
        dungeon.rooms, key=lambda r: (max(r.x - sx, 0, sx - (r.x + r.w - 1)) ** 2
                                      + max(r.y - sy, 0, sy - (r.y + r.h - 1)) ** 2))


def choose_themes(dungeon, rng):
    keys = sorted(THEMES)
    weights = [THEMES[k].weight for k in keys]
    first = spawn_room(dungeon)
    for room in dungeon.rooms:
        room.theme = SPAWN_THEME if room is first else rng.choices(keys, weights)[0]
        room.floor = rng.choice(THEMES[room.theme].floors)


def furnish(dungeon, rng):
    """Escolhe o tema de cada sala e coloca os móveis (preenche
    dungeon.props, dungeon.blocked e dungeon.decals)."""
    choose_themes(dungeon, rng)
    forbidden = _forbidden(dungeon)
    for room in dungeon.rooms:
        f = _RoomFurnisher(dungeon, room, THEMES[room.theme], rng, forbidden)
        f.along_top()
        f.center()
        f.along_sides()
        f.loose()
        f.scatter()
