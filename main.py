"""Dungeon procedural — ponto de entrada.

Uso:
    venv\\Scripts\\python.exe main.py            # seed aleatória
    venv\\Scripts\\python.exe main.py 12345      # seed específica (número ou texto)

Controles: WASD/setas movem, Shift corre, clique esquerdo/J ataca, roda do mouse dá zoom, R gera nova dungeon,
G liga/desliga o grid, V liga/desliga a névoa, Espaço abre/fecha portas, ESC sai.
"""
import math
import random
import sys

import pygame

import settings as S
from dungeon import FLOOR, generate
from fov import Vision
from lighting import FogLayer, Light
from player import Player
from combat import apply_attack, texts_for
from sprites import load_animations, load_attack_animations, load_zombie_animations
from zombies import Horde
from doors import try_toggle
from tileset import Tileset, bake_wall_shadows, door_rect, draw_door, init_doors, render_map


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
    bake_wall_shadows(surf, dungeon)
    init_doors(surf, dungeon, None)
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


class Game:
    def __init__(self, seed):
        pygame.init()
        pygame.display.set_caption("Dungeon")
        self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.anims = load_animations()
        # ataque: mesma altura do personagem parado (o desenho do sheet é menor)
        self.anims.update(load_attack_animations(target_height=self.anims["idle"][0].get_height()))
        self.zombie_anims = load_zombie_animations()
        self.small_font = pygame.font.SysFont("consolas", 15)
        self.dmg_font = pygame.font.SysFont("consolas", 15, bold=True)
        self._dmg_cache = {}
        r = S.VISION_RADIUS
        self.light = Light(round(math.sqrt(r * r + r) * S.TILE))   # mesmo raio de fov.in_radius
        try:
            self.tiles = Tileset()
        except (pygame.error, FileNotFoundError, ValueError) as err:
            print(f"Tileset não carregado ({err}); usando cores sólidas.")
            self.tiles = None
        self.show_grid = True
        self.show_fog = True
        self.message, self.message_until = "", 0
        self.zoom = S.ZOOM_MIN             # zoom atual (vai suavemente até o alvo)
        self.zoom_target = S.ZOOM_MIN      # zoom pedido pela roda do mouse
        self.new_level(seed)

    def new_level(self, seed):
        self.dungeon = generate(seed, S.MAP_W, S.MAP_H)
        self.map_surf = build_map_surface(self.dungeon, self.tiles)
        self.grid_surf = build_grid_surface(self.dungeon)
        self.player = Player(self.anims, self.dungeon.spawn)
        # Zumbis enterrados nas salas (longe do spawn); saem do chão quando vistos
        self.horde = Horde(self.dungeon, avoid=[self.dungeon.spawn])
        self.texts = []                    # números de dano flutuando
        self.seed_label = str(seed)
        # Névoa: começa toda preta; tiles descobertos viram "escurecidos"
        self.vision = Vision(self.dungeon, S.VISION_RADIUS)
        self.fog = FogLayer(self.dungeon.width, self.dungeon.height)
        self.update_vision()
        print(f"Seed: {seed} -> {len(self.dungeon.rooms)} salas")

    def toggle_door(self):
        """Espaço: abre/fecha a porta à frente do personagem."""
        result, door = try_toggle(self.dungeon, self.player)
        if result in ("abriu", "fechou"):
            draw_door(self.map_surf, door, self.tiles)
            self.update_vision(force=True)   # a porta muda o que dá para ver
        elif result == "bloqueada":
            self.show_message("Saia da porta para fechá-la")
        return result

    def update_vision(self, force=False):
        # Tile onde o personagem está desenhado (avança no meio do passo)
        origin = (int(self.player.x // S.TILE), int(self.player.y // S.TILE))
        self.vision.update(origin, force)
        if self.vision.visible != self.fog.visible:
            self.fog.update(self.vision.visible)

    def change_zoom(self, notches):
        """Roda do mouse: cada "clique" muda o alvo em ZOOM_STEP (para cima
        aproxima). O zoom de verdade chega lá aos poucos em update_zoom."""
        target = self.zoom_target + notches * S.ZOOM_STEP
        # arredonda: somar 0.1 dez vezes dá 1.9999999, e 2.0 exato usa escala nítida
        self.zoom_target = round(max(S.ZOOM_MIN, min(S.ZOOM_MAX, target)), 3)

    def update_zoom(self, dt):
        """Aproxima o zoom do alvo com amortecimento exponencial (suave e
        independente do FPS); encaixa no alvo quando a diferença é mínima."""
        diff = self.zoom_target - self.zoom
        if abs(diff) < 0.002:
            self.zoom = self.zoom_target
        else:
            self.zoom += diff * (1 - math.exp(-S.ZOOM_SMOOTHING * dt))

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
        self.draw_actors(view, cam)          # personagem e zumbis, com sombra
        self.draw_door_overlap(view, cam)
        if self.show_fog:
            center = (round(self.player.x - cam[0]), round(self.player.y - cam[1]))
            self.light.draw(view, center)
            fog, pos = self.fog.render(cam, view.get_size())
            view.blit(fog, pos)
        self.draw_damage_texts(view, cam)    # por cima da névoa, para ler bem
        size = (S.SCREEN_W, S.SCREEN_H)
        if view.get_size() == size:
            self.screen.blit(view, (0, 0))
        elif float(self.zoom).is_integer():   # 2x exato: pixels nítidos
            pygame.transform.scale(view, size, self.screen)
        else:                                 # zoom fracionário: suavizado, sem serrilhar
            pygame.transform.smoothscale(view, size, self.screen)

    def draw_actors(self, view, cam):
        """Personagem e zumbis ordenados pela altura dos pés: quem está mais
        embaixo na tela é desenhado por último (fica na frente). Com a névoa
        ligada, só aparecem os zumbis que o personagem está vendo."""
        actors = [(self.player.feet()[1], lambda: self.player.draw(view, cam))]
        for z in self.horde.active():
            if self.show_fog and z.pixel_tile() not in self.vision.visible:
                continue
            actors.append((z.feet_y(), lambda z=z: z.draw(view, cam, self.zombie_anims)))
        for _, draw in sorted(actors, key=lambda a: a[0]):
            draw()

    def _damage_surface(self, text, color):
        """Número de dano com contorno escuro (cacheado)."""
        key = (text, color)
        if key not in self._dmg_cache:
            fg = self.dmg_font.render(text, True, color)
            bg = self.dmg_font.render(text, True, (20, 10, 10))
            w, h = fg.get_size()
            surf = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            for ox, oy in ((0, 1), (2, 1), (1, 0), (1, 2)):
                surf.blit(bg, (ox, oy))
            surf.blit(fg, (1, 1))
            self._dmg_cache[key] = surf
        return self._dmg_cache[key]

    def draw_damage_texts(self, view, cam):
        for t in self.texts:
            img = self._damage_surface(t.text, t.color)
            img.set_alpha(t.alpha)
            view.blit(img, img.get_rect(midbottom=(round(t.x - cam[0]), round(t.y - cam[1]))))

    def draw_door_overlap(self, view, cam):
        """Profundidade: portas da parede de cima ocupam 2 tiles de altura, e
        a metade de cima fica sobre o corredor. Se o personagem está nesse
        corredor (ao norte da porta), a porta é redesenhada por cima dele,
        semitransparente, para ele continuar visível "através" dela."""
        t = S.TILE
        sprite = self.player.sprite_rect()
        for door in self.dungeon.doors:
            if door.side != "top":
                continue
            rect = door_rect(door)
            upper = pygame.Rect(rect.x, rect.y, rect.w, t)   # metade de cima (tile do corredor)
            door_row_top = rect.y + t
            if self.player.y < door_row_top and upper.colliderect(sprite):
                part = self.map_surf.subsurface(upper).copy()
                part.set_alpha(S.OCCLUDER_ALPHA)
                view.blit(part, (upper.x - cam[0], upper.y - cam[1]))

    def _text(self, text, pos, color=S.COLOR_TEXT):
        """Texto com sombra de 1 px (legível sobre qualquer fundo)."""
        self.screen.blit(self.font.render(text, True, (0, 0, 0)), (pos[0] + 1, pos[1] + 1))
        self.screen.blit(self.font.render(text, True, color), pos)

    def draw_hud(self):
        p = self.player
        tx, ty = p.tile
        hud = (f"Seed: {self.seed_label}   Tile: ({tx}, {ty})   Zoom: {self.zoom:.1f}x   "
               f"Abatidos: {self.horde.killed}")
        showing_msg = self.message and pygame.time.get_ticks() < self.message_until

        # Painel semitransparente atrás do HUD
        text_w = self.font.size(hud)[0]
        panel = pygame.Rect(4, 4, text_w + 14, 78 if showing_msg else 54)
        self.hud_panel(panel)

        self._text(hud, (10, 8))

        # Barra de estamina
        x, y, w, h = 10, 34, 200, 14
        ratio = p.stamina / S.STAMINA_MAX
        color = (220, 60, 50) if ratio < 0.25 else (240, 200, 40)
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, w, h), border_radius=4)
        if ratio > 0:
            pygame.draw.rect(self.screen, color, (x, y, max(4, round(w * ratio)), h), border_radius=4)
        pygame.draw.rect(self.screen, (230, 230, 230), (x, y, w, h), 1, border_radius=4)
        label = f"Estamina: {int(p.stamina)}/{S.STAMINA_MAX}" + ("  CORRENDO" if p.running else "")
        self._text(label, (x + w + 10, y - 2))

        # Mensagem temporária (ex.: porta bloqueada)
        if showing_msg:
            self._text(self.message, (10, 56), (255, 200, 120))

        self.draw_controls()

    CONTROLS = ("[WASD] andar  [Shift] correr  [Clique/J] atacar  [Espaço] porta  "
                "[Roda] zoom  [R] nova  [G] grid  [V] névoa  [ESC] sair")

    def draw_controls(self):
        """Ajuda dos controles num painel pequeno no rodapé."""
        img = self.small_font.render(self.CONTROLS, True, (220, 220, 220))
        rect = img.get_rect(bottomleft=(10, S.SCREEN_H - 8))
        if getattr(self, "_controls_panel", None) is None:
            panel = pygame.Surface((rect.w + 12, rect.h + 8), pygame.SRCALPHA)
            pygame.draw.rect(panel, (10, 12, 14, S.HUD_PANEL_ALPHA), panel.get_rect(), border_radius=6)
            self._controls_panel = panel
        self.screen.blit(self._controls_panel, (rect.x - 6, rect.y - 4))
        self.screen.blit(img, rect)

    def hud_panel(self, rect):
        if getattr(self, "_panel_size", None) != rect.size:
            self._panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(self._panel, (10, 12, 14, S.HUD_PANEL_ALPHA),
                             self._panel.get_rect(), border_radius=8)
            pygame.draw.rect(self._panel, (255, 255, 255, 40),
                             self._panel.get_rect(), 1, border_radius=8)
            self._panel_size = rect.size
        self.screen.blit(self._panel, rect.topleft)

    def show_message(self, text, seconds=1.5):
        self.message = text
        self.message_until = pygame.time.get_ticks() + int(seconds * 1000)

    def step(self, dt, keys):
        """Um quadro da lógica do jogo (sem desenhar)."""
        self.horde.update(dt, self.player, self.vision.visible)
        impact = self.player.update(dt, keys, self.dungeon, blocked=self.horde.blocked_tiles())
        if impact is not None:   # quadro do golpe: dano em área nos zumbis
            hits = apply_attack(self.horde, impact, self.player.tile, self.vision.visible)
            self.texts.extend(texts_for(hits))
        for t in self.texts:
            t.update(dt)
        self.texts = [t for t in self.texts if not t.done]
        self.light.update(dt)
        self.update_zoom(dt)
        self.update_vision()

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
                if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                    self.toggle_door()
                if e.type == pygame.MOUSEWHEEL:
                    # precise_y: frações de "clique" em touchpads (scroll contínuo)
                    self.change_zoom(getattr(e, "precise_y", e.y))
                if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or                         (e.type == pygame.KEYDOWN and e.key == pygame.K_j):
                    self.player.request_attack()

            self.step(dt, pygame.key.get_pressed())
            self.draw_world()
            self.draw_hud()
            pygame.display.flip()


def main():
    seed = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else random.randrange(1_000_000)
    Game(seed).run()
    pygame.quit()


if __name__ == "__main__":
    main()
