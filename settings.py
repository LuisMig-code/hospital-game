"""Configurações globais do jogo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CHARACTER_SHEET = ASSETS / "personagem" / "Chibi Character Animation Sprite Sheet.png"

# Tela / grid
TILE = 32
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

# Zoom da câmera (teclas + e -): 3 níveis
ZOOM_LEVELS = (0.5, 1.0, 2.0)   # afastado, normal, aproximado
ZOOM_DEFAULT = 1                # índice em ZOOM_LEVELS (começa no normal)

# Mapa (em tiles)
MAP_W, MAP_H = 80, 60

# Cores
COLOR_FLOOR = (60, 170, 80)     # verde: dá para andar
COLOR_WALL = (90, 90, 90)       # cinza: não dá para andar
COLOR_GRID = (0, 0, 0, 40)      # linhas do grid (com transparência)
COLOR_BG = (20, 20, 20)
COLOR_TEXT = (255, 255, 255)

# Visão (névoa de guerra)
VISION_RADIUS = 5               # raio de visão em tiles
FOG_EXPLORED_ALPHA = 160        # escurecimento do já descoberto fora da visão (0-255)
COLOR_UNEXPLORED = (0, 0, 0)

# Jogador
PLAYER_SPEED = 150 * 1.3        # pixels por segundo (andando) — 195 px/s
RUN_MULT = 2.0                  # correndo (Shift) anda 2x mais rápido
PLAYER_SPRITE_HEIGHT = 48       # altura do sprite na tela (1.5 tile)
ANIM_FPS = 13                   # frames de animação por segundo (2x correndo)

# Estamina
STAMINA_MAX = 100
STAMINA_DRAIN = 25              # gasto por segundo correndo (100 -> 0 em 4 s)
STAMINA_REGEN_IDLE = 10         # recuperação por segundo parado
STAMINA_REGEN_WALK = 5          # recuperação por segundo andando normal
STAMINA_RECOVER_TO_RUN = 20     # ao zerar, fica "cansado" até recuperar isso
