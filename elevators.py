"""Elevadores: chegada (onde o personagem começa o andar) e saída (que leva
ao próximo andar). Sem pygame.

Cada elevador ocupa 2 tiles da parede de cima de uma sala (parede alta, com
chão embaixo) e tem 2 tiles de "frente" (o chão logo abaixo), onde o
personagem fica para usar a saída. `place_elevators` é chamado por
`dungeon.generate` depois das portas e antes dos móveis.
"""
from collections import deque
from dataclasses import dataclass

# Quadros de cada animação (iguais aos de sprites.ELEVATOR_ANIMS)
FRAMES = {"arrive": 8, "close": 8, "idle": 6, "open_exit": 8, "closed": 1}


@dataclass(eq=False)
class Elevator:
    wall: list          # 2 tiles de parede (esquerda, direita)
    room: object

    @property
    def front(self):
        """Os 2 tiles de chão logo abaixo do elevador."""
        return [(x, y + 1) for x, y in self.wall]

    @property
    def base_y(self):
        """Linha (em tiles) logo abaixo da parede: a base do desenho."""
        return self.wall[0][1] + 1


def corner_floor(dungeon):
    """Chão (não porta) mais perto do canto de cima à esquerda."""
    best = None
    for y, row in enumerate(dungeon.grid):
        for x in range(len(row)):
            if dungeon.is_floor(x, y) and (x, y) not in dungeon.door_at:
                key = (x * x + y * y, y, x)
                if best is None or key < best:
                    best = key
    return (best[2], best[1])


def positions(dungeon, room):
    """Posições x válidas para um elevador na parede de cima da sala."""
    y = room.y - 1
    floor = dungeon.is_floor
    out = []
    for x in range(room.x, room.x + room.w - 1):
        ok = True
        for i in (0, 1):
            wx = x + i
            # parede alta (parede em cima também) com chão da sala embaixo, sem porta
            if floor(wx, y) or not floor(wx, y + 1) or floor(wx, y - 1) or (wx, y + 1) in dungeon.door_at:
                ok = False
                break
        if not ok:
            continue
        # nenhuma abertura/porta na parede a menos de 2 tiles
        if any(floor(x + dx, y) or (x + dx, y) in dungeon.door_at for dx in range(-2, 4)):
            continue
        if any((x + dx, y + 1) in dungeon.door_at for dx in range(-2, 4)):
            continue
        out.append(x)
    return out


def path_distances(dungeon, start):
    """Distância (em passos) de `start` até cada chão, com as portas abertas."""
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in dist and dungeon.is_floor(*n):
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    return dist


def _room_distance(room, dist):
    tiles = [dist[(x, y)] for y in range(room.y, room.y + room.h)
             for x in range(room.x, room.x + room.w) if (x, y) in dist]
    return min(tiles) if tiles else 10 ** 9


def place_elevators(dungeon, rng):
    """Põe o elevador de chegada na sala mais perto do canto de cima à
    esquerda (o spawn passa a ser a frente dele) e o de saída numa sala
    sorteada entre a metade mais longe (pelo caminho)."""
    corner = corner_floor(dungeon)
    dist = path_distances(dungeon, corner)
    by_near = sorted(dungeon.rooms, key=lambda r: (_room_distance(r, dist), r.y, r.x))
    for room in by_near:                               # chegada
        xs = positions(dungeon, room)
        if xs:
            x = min(xs, key=lambda x: (abs(x - corner[0]), x))
            dungeon.elevator_in = Elevator([(x, room.y - 1), (x + 1, room.y - 1)], room)
            break
    start = dungeon.elevator_in.front[0]
    dist = path_distances(dungeon, start)
    others = [r for r in dungeon.rooms if r is not dungeon.elevator_in.room]
    others.sort(key=lambda r: (_room_distance(r, dist), r.y, r.x))
    far = others[len(others) // 2:]
    near = others[:len(others) // 2]
    rng.shuffle(far)
    for room in far + near[::-1]:                      # saída: longe primeiro
        xs = positions(dungeon, room)
        if xs:
            x = rng.choice(xs)
            dungeon.elevator_out = Elevator([(x, room.y - 1), (x + 1, room.y - 1)], room)
            break


class ElevatorActor:
    """Estado da animação de um elevador no jogo."""

    def __init__(self, elevator, anim="closed"):
        self.elevator = elevator
        self.play(anim)

    def play(self, anim, reverse=False, loop=False):
        self.anim, self.reverse, self.loop = anim, reverse, loop
        self.time = 0.0
        self.done = False

    def update(self, dt, fps):
        self.time += dt
        n = FRAMES[self.anim]
        if not self.loop and self.time * fps >= n:
            self.done = True

    def frame(self, fps):
        n = FRAMES[self.anim]
        i = int(self.time * fps)
        i = i % n if self.loop else min(i, n - 1)
        return n - 1 - i if self.reverse else i
