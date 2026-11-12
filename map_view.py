"""Mapa do andar (tecla M): o que já foi descoberto, desenhado sobre o
quadro de prancheta (`settings.MAP_BOARD`).

- Salas com zumbi vivo que nasceu nelas: vermelho claro; salas limpas e
  corredores: a "cor normal" (azul-claro de planta).
- Portas: verde se já foram abertas alguma vez, carmesim se nunca.
- Elevadores, kits vistos e o personagem (ponto piscando).

O quadro com o mapa é montado uma vez ao abrir (`render`) — o jogo fica
pausado enquanto o mapa está aberto —, e `draw` só cola o quadro pronto e
desenha o ponto do personagem.
"""
import pygame

import settings as S

# Áreas do quadro original (1448x1086), em pixels do quadro (medidas no PNG)
BOARD_GRID = pygame.Rect(61, 211, 1042, 768)       # área quadriculada (o mapa)
BOARD_TITLE = pygame.Rect(107, 84, 1252, 91)       # faixa de cima
BOARD_CIRCLE = ((1262, 345), 78)                   # círculo do painel (centro, raio interno)
BOARD_BOXES = [pygame.Rect(1157, y0, 42, y1 - y0)  # caixinhas da legenda
               for y0, y1 in ((511, 552), (593, 633), (676, 715), (758, 798), (840, 881))]
BOARD_LINE_X = (1213, 1395)                        # onde vai o texto de cada linha da legenda
BOARD_BOTTOM = pygame.Rect(52, 1011, 1346, 27)     # faixa de baixo

C = S.MAP_COLORS
LEGEND = (
    ("enemies", "Com zumbis"),
    ("floor", "Sala limpa"),
    ("door_opened", "Porta aberta"),
    ("door_new", "Nunca aberta"),
    ("elevator_out", "Saída"),
)


def room_status(dungeon, zombies):
    """{sala: "enemies" | "clear"}: a sala ainda tem inimigo se algum zumbi
    vivo nasceu nela (`Zombie.home`), mesmo enterrado ou fora dela
    perseguindo o personagem. Quem termina de morrer sai da Horde."""
    alive = {id(z.home) for z in zombies if z.home is not None and z.state != "dead"}
    return {id(r): ("enemies" if id(r) in alive else "clear") for r in dungeon.rooms}


def discovered_rooms(dungeon, explored):
    """Salas com algum chão já descoberto."""
    return [r for r in dungeon.rooms
            if any((x, y) in explored for y in range(r.y, r.y + r.h) for x in range(r.x, r.x + r.w))]


class MapBoard:
    def __init__(self, screen_h=S.MAP_SCREEN_H):
        board = pygame.image.load(str(S.MAP_BOARD))
        if pygame.display.get_surface() is not None:
            board = board.convert()
        w, h = board.get_size()
        self.scale = screen_h / h
        self.size = (round(w * self.scale), screen_h)
        self.board = pygame.transform.smoothscale(board, self.size)
        self.title_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.big_font = pygame.font.SysFont("consolas", 26, bold=True)
        self.font = pygame.font.SysFont("consolas", 13, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 12)
        self.surface = None
        self.rect = pygame.Rect((0, 0), self.size)
        self.player_tile = None

    # --------------------------------------------------------------- geometria
    def _r(self, rect):
        """Retângulo do quadro original -> quadro na escala da tela."""
        s = self.scale
        return pygame.Rect(round(rect.x * s), round(rect.y * s), round(rect.w * s), round(rect.h * s))

    def layout(self, dungeon):
        """Tamanho do tile e canto do mapa dentro da grade do quadro."""
        grid = self._r(BOARD_GRID)
        ts = min(grid.w / dungeon.width, grid.h / dungeon.height)
        ox = grid.x + (grid.w - ts * dungeon.width) / 2
        oy = grid.y + (grid.h - ts * dungeon.height) / 2
        return ts, ox, oy

    def tile_rect(self, tile, layout):
        ts, ox, oy = layout
        x, y = tile
        x0, y0 = int(ox + x * ts), int(oy + y * ts)
        return pygame.Rect(x0, y0, int(ox + (x + 1) * ts) - x0, int(oy + (y + 1) * ts) - y0)

    # ---------------------------------------------------------------- desenho
    def render(self, dungeon, explored, zombies, medkits, floor):
        """Monta o quadro com o mapa do que foi descoberto, a legenda e o resumo."""
        surf = self.board.copy()
        lay = self.layout(dungeon)
        self._layout = lay
        status = room_status(dungeon, zombies)
        room_of = {}
        for r in dungeon.rooms:
            for y in range(r.y, r.y + r.h):
                for x in range(r.x, r.x + r.w):
                    room_of[(x, y)] = r
        for t in explored:
            if not (0 <= t[0] < dungeon.width and 0 <= t[1] < dungeon.height):
                continue
            if t in dungeon.door_at:
                continue                       # portas por cima, depois
            if dungeon.is_floor(*t):
                room = room_of.get(t)
                key = "corridor" if room is None else ("enemies" if status[id(room)] == "enemies" else "floor")
            else:
                key = "wall"
            surf.fill(C[key], self.tile_rect(t, lay))
        for door in dungeon.doors:
            seen = [t for t in door.tiles if t in explored]
            for t in seen:
                surf.fill(C["door_opened" if door.opened else "door_new"], self.tile_rect(t, lay))
        for ev, key in ((dungeon.elevator_in, "elevator_in"), (dungeon.elevator_out, "elevator_out")):
            if ev is not None and any(t in explored for t in ev.wall):
                for t in ev.wall:
                    surf.fill(C[key], self.tile_rect(t, lay))
        for kit in medkits:
            if kit.tile in explored:
                self._cross(surf, self.tile_rect(kit.tile, lay))
        self._panel(surf, dungeon, explored, status, floor)
        self.surface = surf
        return surf

    def _cross(self, surf, r):
        cx, cy = r.center
        a = max(2, r.w // 2 + 1)
        t = max(2, r.w // 3)
        pygame.draw.rect(surf, (20, 40, 20), (cx - a - 1, cy - t // 2 - 1, 2 * a + 2, t + 2))
        pygame.draw.rect(surf, (20, 40, 20), (cx - t // 2 - 1, cy - a - 1, t + 2, 2 * a + 2))
        pygame.draw.rect(surf, C["medkit"], (cx - a, cy - t // 2, 2 * a, t))
        pygame.draw.rect(surf, C["medkit"], (cx - t // 2, cy - a, t, 2 * a))

    def _text(self, surf, font, text, color, **anchor):
        img = font.render(text, True, color)
        rect = img.get_rect(**anchor)
        surf.blit(img, rect)
        return rect

    def _panel(self, surf, dungeon, explored, status, floor):
        ink = C["ink"]
        s = self.scale
        self._text(surf, self.title_font, f"MAPA  —  ANDAR {floor}", ink, center=self._r(BOARD_TITLE).center)
        # círculo: salas limpas / descobertas
        rooms = discovered_rooms(dungeon, explored)
        clear = sum(1 for r in rooms if status[id(r)] == "clear")
        (cx, cy), _ = BOARD_CIRCLE
        center = (round(cx * s), round(cy * s))
        self._text(surf, self.small_font, "Salas limpas", ink, midbottom=(center[0], center[1] - 8))
        self._text(surf, self.big_font, f"{clear}/{len(rooms)}", ink, midtop=(center[0], center[1] - 6))
        # legenda: caixinha pintada + texto na linha
        for box, (key, label) in zip(BOARD_BOXES, LEGEND):
            b = self._r(box).inflate(-6, -6)
            surf.fill(C[key], b)
            pygame.draw.rect(surf, ink, b, 1)
            x = round(BOARD_LINE_X[0] * s)
            self._text(surf, self.font, label, ink, bottomleft=(x, b.bottom))
        self._text(surf, self.small_font, "[M] fechar", ink, center=self._r(BOARD_BOTTOM).center)

    def draw(self, screen, player_tile, time, area=None):
        """Escurece o jogo, cola o quadro pronto (centralizado em `area`) e
        desenha o personagem piscando."""
        area = area or screen.get_rect()
        shade = pygame.Surface(area.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, S.MAP_SHADE))
        screen.blit(shade, area.topleft)
        self.rect = self.surface.get_rect(center=area.center)
        screen.blit(self.surface, self.rect)
        if int(time / S.MAP_BLINK) % 2 == 0:
            r = self.tile_rect(player_tile, self._layout).move(self.rect.topleft)
            radius = max(3, round(r.w * 0.75))
            pygame.draw.circle(screen, (10, 10, 10), r.center, radius + 1)
            pygame.draw.circle(screen, C["player"], r.center, radius)
