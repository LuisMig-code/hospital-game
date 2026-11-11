"""Geração procedural de dungeon (BSP: salas + corredores) a partir de uma seed,
com portas e salas temáticas mobiliadas (`furnish.py`)."""
import random
import zlib
from dataclasses import dataclass, field

WALL = 0
FLOOR = 1

MIN_LEAF = 14     # tamanho mínimo de uma folha da BSP (tiles)
MIN_ROOM = 6      # tamanho mínimo de uma sala (tiles)
CORRIDOR_WIDTHS = (2, 3)  # larguras possíveis dos corredores (mínimo 2)


def normalize_seed(seed):
    """Aceita int ou string. Strings numéricas viram int; outras usam crc32
    (estável entre execuções, ao contrário de hash())."""
    if isinstance(seed, int):
        return seed
    s = str(seed).strip()
    try:
        return int(s)
    except ValueError:
        return zlib.crc32(s.encode("utf-8"))


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int
    theme: str = ""      # chave de themes.THEMES (escolhida em furnish.py)
    floor: str = ""      # piso base da sala (um dos pisos do tema)

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)


@dataclass
class Dungeon:
    seed: int
    width: int
    height: int
    grid: list = field(default_factory=list)   # grid[y][x]
    rooms: list = field(default_factory=list)
    doors: list = field(default_factory=list)      # lista de doors.Door
    door_at: dict = field(default_factory=dict)    # (tx, ty) -> Door
    props: list = field(default_factory=list)      # furnish.PlacedProp com colisão
    blocked: set = field(default_factory=set)      # tiles ocupados por móveis
    decals: list = field(default_factory=list)     # furnish.PlacedProp sem colisão (no chão)
    elevator_in: object = None                     # elevators.Elevator de chegada
    elevator_out: object = None                    # elevators.Elevator de saída

    def is_floor(self, tx, ty):
        """Chão no grid (ignora o estado das portas)."""
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.grid[ty][tx] == FLOOR
        return False

    def is_transparent(self, tx, ty):
        """Dá para ver através: chão que não seja porta fechada (móveis não
        bloqueiam a visão)."""
        if not self.is_floor(tx, ty):
            return False
        door = self.door_at.get((tx, ty))
        return door is None or door.open

    def is_walkable(self, tx, ty):
        """Dá para andar: dá para ver através e não tem móvel."""
        return self.is_transparent(tx, ty) and (tx, ty) not in self.blocked

    def room_at(self, tile):
        """Sala cujo retângulo contém o tile (None em corredores e paredes)."""
        x, y = tile
        return next((r for r in self.rooms if r.x <= x < r.x + r.w and r.y <= y < r.y + r.h), None)

    @property
    def spawn(self):
        """Onde o personagem começa: na frente do elevador de chegada (sem
        elevador, o chão mais perto do canto de cima à esquerda)."""
        if self.elevator_in is not None:
            return self.elevator_in.front[0]
        from elevators import corner_floor
        return corner_floor(self)


class _Leaf:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.left = self.right = None
        self.room = None

    def split(self, rng):
        if self.left or self.right:
            return False
        # Decide orientação: corta a dimensão maior; se parecidas, aleatório
        if self.w > self.h and self.w / self.h >= 1.25:
            horizontal = False
        elif self.h > self.w and self.h / self.w >= 1.25:
            horizontal = True
        else:
            horizontal = rng.random() < 0.5
        size = self.h if horizontal else self.w
        if size < MIN_LEAF * 2:
            return False
        cut = rng.randint(MIN_LEAF, size - MIN_LEAF)
        if horizontal:
            self.left = _Leaf(self.x, self.y, self.w, cut)
            self.right = _Leaf(self.x, self.y + cut, self.w, self.h - cut)
        else:
            self.left = _Leaf(self.x, self.y, cut, self.h)
            self.right = _Leaf(self.x + cut, self.y, self.w - cut, self.h)
        return True

    def leaves(self):
        if not self.left and not self.right:
            yield self
        else:
            for c in (self.left, self.right):
                if c:
                    yield from c.leaves()

    def any_room(self, rng):
        """Uma sala qualquer dentro deste ramo (usada para ligar ramos)."""
        if self.room:
            return self.room
        rooms = [l.room for l in self.leaves() if l.room]
        return rng.choice(rooms)


def generate(seed, width=80, height=60):
    seed = normalize_seed(seed)
    rng = random.Random(seed)
    grid = [[WALL] * width for _ in range(height)]
    d = Dungeon(seed, width, height, grid)

    # 1) Particiona o mapa (deixando 1 tile de borda de parede)
    root = _Leaf(1, 1, width - 2, height - 2)
    pending = [root]
    while pending:
        leaf = pending.pop()
        # folhas grandes sempre dividem; médias dividem com 75% de chance
        big = leaf.w > MIN_LEAF * 3 or leaf.h > MIN_LEAF * 3
        if (big or rng.random() < 0.75) and leaf.split(rng):
            pending.extend([leaf.left, leaf.right])

    # 2) Cria uma sala dentro de cada folha
    for leaf in root.leaves():
        rw = rng.randint(MIN_ROOM, leaf.w - 2)
        rh = rng.randint(MIN_ROOM, leaf.h - 2)
        rx = rng.randint(leaf.x + 1, leaf.x + leaf.w - rw - 1)
        ry = rng.randint(leaf.y + 1, leaf.y + leaf.h - rh - 1)
        leaf.room = Room(rx, ry, rw, rh)
        d.rooms.append(leaf.room)
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                grid[y][x] = FLOOR

    # 3) Liga ramos irmãos com corredores (garante conectividade total)
    def connect(node):
        if not node.left or not node.right:
            return
        connect(node.left)
        connect(node.right)
        _corridor(grid, rng, node.left.any_room(rng).center, node.right.any_room(rng).center)

    connect(root)

    # 4) Portas nas entradas das salas
    from doors import place_doors  # import local: doors usa tipos deste módulo
    place_doors(d, rng)

    # 5) Elevadores de chegada (o spawn) e de saída
    from elevators import place_elevators
    place_elevators(d, random.Random(seed ^ 0xE1E7))

    # 6) Temas e móveis (rng próprio: não muda o resto da geração)
    from furnish import furnish
    furnish(d, random.Random(seed ^ 0xF0E1))
    return d


def _carve(grid, x, y, thick):
    for dy in range(thick):
        for dx in range(thick):
            yy, xx = y + dy, x + dx
            if 0 < yy < len(grid) - 1 and 0 < xx < len(grid[0]) - 1:
                grid[yy][xx] = FLOOR


def _corridor(grid, rng, a, b):
    """Corredor em L entre os pontos a e b, com largura de CORRIDOR_WIDTHS."""
    (x1, y1), (x2, y2) = a, b
    thick = rng.choice(CORRIDOR_WIDTHS)
    if rng.random() < 0.5:
        corner = (x2, y1)
    else:
        corner = (x1, y2)
    for (sx, sy), (ex, ey) in (((x1, y1), corner), (corner, (x2, y2))):
        if sx == ex:
            for y in range(min(sy, ey), max(sy, ey) + 1):
                _carve(grid, sx, y, thick)
        else:
            for x in range(min(sx, ex), max(sx, ex) + 1):
                _carve(grid, x, sy, thick)
