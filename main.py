"""Dungeon procedural — ponto de entrada.

Uso:
    venv\\Scripts\\python.exe main.py            # seed aleatória
    venv\\Scripts\\python.exe main.py 12345      # seed específica (número ou texto)

Controles: WASD/setas movem, Shift corre, +/- zoom, R gera nova dungeon,
G liga/desliga o grid, V liga/desliga a névoa, ESC sai.
"""
import math
import random
import sys

import pygame

import settings as S
from dungeon import FLOOR, generate
from fov import Vision
from player import Player
from sprites import load_animations
from tileset import Tileset, render_map


def build_map_surface(dungeon, tiles=None):
    """Pré-renderiza o mapa inteiro (tiles não mudam). Usa a arte do tileset;
    sem tileset, desenha com cores sólidas (verde/cinza)."""
    if tiles is not None:
        return render_map(dungeon, tiles)
    surf = pygame.Surface((dungeon.width * S.TILE, dungeon.height * S.TILE))
    for y, row in enumerate(dungeon.grid):
        for x, cell in enumerate(row):
            color = S.COLOR_FLOOR if cell == FLOOR else S.COLOR_WALL
            surf.fill(color, (x * S.TILE, y * S.TILE, S.TILE, S.TILE))
    return surf


def build_grid_surface(dungeon):
    """Linhas do grid só sobre o piso (não cortam a arte das paredes)."""
    t = S.TILE
    surf = pygame.Surface((dungeon.width * t, dungeon.height * t), pygame.SRCALPHA)
    for y, row in enumerate(dungeon.grid):
        for x, cell in enumerate(row):
            if cell == FLOOR:
                pygame.draw.rect(surf, S.COLOR_GRID, (x * t, y * t, t + 1, t + 1), 1)
    return surf


def build_vision_circle():
    """Contorno semitransparente do alcance da visão. O raio acompanha o
    critério de fov.in_radius (dx² + dy² <= r² + r), medido em pixels."""
    r = S.VISION_RADIUS
    radius = round(math.sqrt(r * r + r) * S.TILE)
    size = 2 * radius + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, S.COLOR_VISION_CIRCLE, (size // 2, size // 2), radius,
                       S.VISION_CIRCLE_WIDTH)
    return surf


class Game:
    def __init__(self, seed):
        pygame.init()
        pygame.display.set_caption("Dungeon")
        self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.anims = load_animations()
        try:
            self.tiles = Tileset()
        except (pygame.error, FileNotFoundError, ValueError) as err:
            print(f"Tileset não carregado ({err}); usando cores sólidas.")
            self.tiles = None
        self.show_grid = True
        self.show_fog = True
        self.vision_circle = build_vision_circle()
        self.zoom_index = S.ZOOM_DEFAULT
        self.new_level(seed)

    def new_level(self, seed):
        self.dungeon = generate(seed, S.MAP_W, S.MAP_H)
        self.map_surf = build_map_surface(self.dungeon, self.tiles)
        self.grid_surf = build_grid_surface(self.dungeon)
        self.player = Player(self.anims, self.dungeon.spawn)
        self.seed_label = str(seed)
        # Névoa: começa toda preta; tiles descobertos viram "escurecidos"
        self.vision = Vision(self.dungeon, S.VISION_RADIUS)
        self.fog_surf = pygame.Surface(self.map_surf.get_size(), pygame.SRCALPHA)
        self.fog_surf.fill((*S.COLOR_UNEXPLORED, 255))
        self.update_vision()
        print(f"Seed: {seed} -> {len(self.dungeon.rooms)} salas")

    def update_vision(self):
        # Tile onde o personagem está desenhado (avança no meio do passo)
        origin = (int(self.player.x // S.TILE), int(self.player.y // S.TILE))
        for tx, ty in self.vision.update(origin):
            self.fog_surf.fill((*S.COLOR_UNEXPLORED, S.FOG_EXPLORED_ALPHA),
                               (tx * S.TILE, ty * S.TILE, S.TILE, S.TILE))

    @property
    def zoom(self):
        return S.ZOOM_LEVELS[self.zoom_index]

    def change_zoom(self, step):
        self.zoom_index = max(0, min(len(S.ZOOM_LEVELS) - 1, self.zoom_index + step))

    def view_size(self):
        """Tamanho (em pixels do mundo) da área visível com o zoom atual."""
        return round(S.SCREEN_W / self.zoom), round(S.SCREEN_H / self.zoom)

    def camera(self):
        vw, vh = self.view_size()
        mw, mh = self.map_surf.get_size()
        cx = self.player.x - vw / 2
        cy = self.player.y - vh / 2
        cx = max(0, min(cx, mw - vw)) if mw > vw else (mw - vw) / 2
        cy = max(0, min(cy, mh - vh)) if mh > vh else (mh - vh) / 2
        return round(cx), round(cy)

    def draw_world(self):
        """Desenha o mundo numa superfície do tamanho da área visível e
        escala para a tela de acordo com o zoom."""
        cam = self.camera()
        view = pygame.Surface(self.view_size())
        view.fill(S.COLOR_BG)
        view.blit(self.map_surf, (-cam[0], -cam[1]))
        if self.show_grid:
            view.blit(self.grid_surf, (-cam[0], -cam[1]))
        if self.show_fog:
            view.blit(self.fog_surf, (-cam[0], -cam[1]))
            # Tiles dentro da visão: redesenha por cima da névoa com cores normais
            for tx, ty in self.vision.visible:
                area = pygame.Rect(tx * S.TILE, ty * S.TILE, S.TILE, S.TILE)
                pos = (area.x - cam[0], area.y - cam[1])
                view.blit(self.map_surf, pos, area)
                if self.show_grid:
                    view.blit(self.grid_surf, pos, area)
        if self.show_fog:
            c = self.vision_circle
            view.blit(c, c.get_rect(center=(round(self.player.x - cam[0]),
                                            round(self.player.y - cam[1]))))
        self.player.draw(view, cam)
        size = (S.SCREEN_W, S.SCREEN_H)
        if self.zoom == 1:
            self.screen.blit(view, (0, 0))
        elif self.zoom > 1:   # aproximar: pixels nítidos
            pygame.transform.scale(view, size, self.screen)
        else:                 # afastar: suavizado para não serrilhar
            pygame.transform.smoothscale(view, size, self.screen)

    def draw_hud(self):
        p = self.player
        tx, ty = p.tile
        hud = (f"Seed: {self.seed_label}   Tile: ({tx}, {ty})   Zoom: {self.zoom:g}x   "
               "[Shift] correr  [+/-] zoom  [R] nova  [G] grid  [V] névoa  [ESC] sair")
        self.screen.blit(self.font.render(hud, True, S.COLOR_TEXT), (10, 8))

        # Barra de estamina
        x, y, w, h = 10, 34, 200, 14
        ratio = p.stamina / S.STAMINA_MAX
        color = (220, 60, 50) if ratio < 0.25 else (240, 200, 40)
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, w, h))
        pygame.draw.rect(self.screen, color, (x, y, round(w * ratio), h))
        pygame.draw.rect(self.screen, (230, 230, 230), (x, y, w, h), 1)
        label = f"Estamina: {int(p.stamina)}/{S.STAMINA_MAX}" + ("  CORRENDO" if p.running else "")
        self.screen.blit(self.font.render(label, True, S.COLOR_TEXT), (x + w + 10, y - 2))

    def run(self):
        while True:
            dt = min(self.clock.tick(S.FPS) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    return
                if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                    self.new_level(random.randrange(1_000_000))
                if e.type == pygame.KEYDOWN and e.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                if e.type == pygame.KEYDOWN and e.key == pygame.K_v:
                    self.show_fog = not self.show_fog
                if e.type == pygame.KEYDOWN:
                    # "+" pode vir da tecla "=" (com ou sem Shift) ou do teclado numérico
                    if e.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS) or e.unicode == "+":
                        self.change_zoom(+1)
                    elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS) or e.unicode == "-":
                        self.change_zoom(-1)

            self.player.update(dt, pygame.key.get_pressed(), self.dungeon)
            self.update_vision()

            self.draw_world()
            self.draw_hud()
            pygame.display.flip()


def main():
    seed = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else random.randrange(1_000_000)
    Game(seed).run()
    pygame.quit()


if __name__ == "__main__":
    main()
